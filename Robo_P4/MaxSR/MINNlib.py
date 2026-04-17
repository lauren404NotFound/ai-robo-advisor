"""
MIT License

Copyright (c) 2025 William Smyth and Lauren McBurney

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND...
"""

"""
Name     : MINNlib.py [Markowitz-Informed Neural Networks]
Contact  : w.smyth@ulster.ac.uk
Date     : 11/10/2025
Desc     : Python library for DeepAtomicIQ project
"""
import logging
import math
import os
import pickle
import random
import time
import torch
import numpy as np
import pandas as pd
import project_hyperparameters as cfg 
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from numpy import diag,inf,copy,dot
from numpy.linalg import norm
from sklearn.neighbors import KernelDensity 

seed = 260370
torch.manual_seed(seed)
np.random.seed(seed)
random.seed(seed)

# risk-free rate helpers
def _load_csv_series(csv_path, column=None):
    """load a dated series (index=Date) from CSV."""
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    if isinstance(df, pd.DataFrame):
        ser = df.iloc[:, 0] if column is None else df[column]
    else:
        ser = df
    ser = pd.to_numeric(ser, errors="coerce").dropna()
    ser.index = pd.to_datetime(ser.index)
    return ser.sort_index().rename("rf")

def _asof_align(series, idx, method="ffill"):
    """as-of align a series to a target DatetimeIndex."""
    union = series.index.union(idx).sort_values()
    s = series.reindex(union)
    if method == "ffill":
        s = s.ffill()
    elif method == "bfill":
        s = s.bfill()
    return s.reindex(idx).rename(series.name)

def load_rfr_aligned_to_returns(csv_path, returns_index,
                                frequency="M",
                                column=None,
                                align_method="ffill",
                                interpretation="monthly_effective"):        
    """read risk-free rate CSV and align to returns index as per cfg.rf_config."""
    rf = _load_csv_series(csv_path, column)
    if interpretation == "annualized_yield":
        y = rf / 100.0
        ppy = 12 if str(frequency).upper().startswith("M") else 252
        rf = (1.0 + y) ** (1.0 / ppy) - 1.0
    rf_aligned = _asof_align(rf, returns_index, method=align_method)
    return rf_aligned.rename("rf")

def geom_mean_of_returns(r):
    """geometric mean of simple returns over the period."""
    s = pd.Series(r).dropna()
    if len(s) == 0:
        return 0.0
    return float((1.0 + s).prod() ** (1.0 / len(s)) - 1.0)

# atomic-IQ utilities
def _temporal_factors(T, gamma, epsil, device, dtype,
                      mode="signed",         # {"raw", "signed"}
                      gamma_max=None,        # optional re-cap
                      eps_floor=0.0,         # tiny floor e.g. 1e-3 if desired
                      schur_safe=False):     # set True in off-diagonal temporal scaling

    gamma = torch.as_tensor(gamma, device=device, dtype=dtype).squeeze()
    epsil = torch.as_tensor(epsil, device=device, dtype=dtype).squeeze()

    if gamma_max is not None and gamma_max > 0:
        gamma = torch.clamp(gamma, min=-gamma_max, max=gamma_max)

    g_abs = torch.abs(gamma)  # rate in [0, gamma_max]
    t     = torch.arange(T, device=device, dtype=dtype)

    if mode == "raw":
        # age from recent edge + delay at recent edge
        age = (T - 1 - t)
        age = torch.clamp(age - epsil, min=0)
        a   = torch.exp(-gamma * age) # may exceed 1 if gamma < 0

    elif mode == "signed":
        # direction from sign of gamma (recent-edge if gamma>=0 else oldest-edge)
        is_recent = (gamma >= 0).to(dtype)
        age_recent = (T - 1 - t)
        age_oldest = t
        age = is_recent * age_recent + (1 - is_recent) * age_oldest
        # delay always at the chosen reference edge
        age = torch.clamp(age - epsil, min=0)
        a = torch.exp(-g_abs * age) # in (0, 1]

    else:
        raise ValueError("gamma mode must be 'raw' or 'signed'")

    # Schur-safety: needed in off-diagonal temporal scaling to ensure a_t <= 1, if mode == "raw"
    if schur_safe:
        a = a / (a.max() + torch.finfo(dtype).eps)  # now max(a) == 1

    # optional tiny floor to avoid zero weights
    if eps_floor and eps_floor > 0:
        a = eps_floor + (1.0 - eps_floor) * a

    return a

def _channel_weights_from_logits(alpha_logits: torch.Tensor, wI_floor: float = 0.0) -> torch.Tensor:
    """map 3 or 4 logits to (wB,wW,wT,wI) via softmax."""
    if alpha_logits.dim() == 1:
        alpha_logits = alpha_logits.unsqueeze(0)   # (1, K)

    K = alpha_logits.size(1)
    if K == 3:
        z4 = torch.cat([alpha_logits, torch.zeros_like(alpha_logits[:, :1])], dim=1)  # (1,4)
    elif K == 4:
        z4 = alpha_logits  # B,W,T,I
    else:
        raise ValueError(f"_channel_weights_from_logits expects 3 or 4 logits, got {K}")

    w4 = torch.softmax(z4, dim=1)  # (1,4)

    if wI_floor > 0.0:
        wI   = wI_floor + (1.0 - wI_floor) * w4[:, 3:4] 
        wBWT = (1.0 - wI_floor) * w4[:, 0:3]
        w4   = torch.cat([wBWT, wI], dim=1)

    return w4.squeeze(0)

def to_corr(G: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
    """convert a symmetric accumulator G to correlation C with safe diagonal handling."""
    if G.ndim != 2 or G.shape[0] != G.shape[1]:
        raise ValueError("to_corr expects a square 2D tensor")

    G = 0.5 * (G + G.T)
    d = torch.diag(G).clone()
    mask = d <= eps
    d_safe = d.clone()
    d_safe[mask] = 1.0 # avoid division by zero; will zero rows/cols below

    inv_sqrt = torch.rsqrt(d_safe)
    Dm12 = torch.diag(inv_sqrt)
    C    = Dm12 @ G @ Dm12

    if mask.any():
        idx = torch.nonzero(mask, as_tuple=False).flatten()
        C[idx, :] = 0.0
        C[:, idx] = 0.0
        C[idx, idx] = 1.0

    C = 0.5 * (C + C.T)
    C.fill_diagonal_(1.0)
    C = torch.clamp(C, min=-1.0, max=1.0)

    return C

_to_corr = to_corr

def IQ_dispatch(*args, **kwargs):
    if cfg.iq_method == "iq1":
        return IQ1(*args, **kwargs)
    elif cfg.iq_method == "iq2":
        return IQ2(*args, **kwargs)
    else:
        raise ValueError(f"Invalid iq_method: {cfg.iq_method}. Must be 'iq1' or 'iq2'.")

def create_rolling_batches(returns):
    """create rolling, stratified batches of asset returns."""
    r         = cfg.r
    m         = cfg.m
    b         = cfg.b
    f         = cfg.f
    n_strata  = cfg.n_strata

    if r % n_strata != 0:
        raise ValueError("r must be a multiple of n_strata")
    if m % n_strata != 0 or m > r:
        raise ValueError("m must be a multiple of n_strata and less than or equal to r")

    section_size     = r // n_strata 
    rows_per_section = m // n_strata  

    iterations_list   = []
    total_data_points = len(returns)
    max_iterations    = total_data_points - (r + m) + 1

    for start in range(0, max_iterations, f):
        segment  = returns.iloc[start:start + r]  
        sections = [segment.iloc[i*section_size:(i+1)*section_size] for i in range(n_strata)]

        iteration_batches = []
        for _ in range(b):
            batch = pd.DataFrame()
            for section in sections:
                sampled_rows = section.sample(n=rows_per_section, replace=False)
                batch = pd.concat([batch, sampled_rows])
            batch = batch.sort_index()
            iteration_batches.append(batch)

        iterations_list.append(iteration_batches)

    return iterations_list

class DeepIQNetPortfolio(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        # scalars (delta, gamma, epsilon) + logits (B,W,T,I) + n_assets weights
        self.output_dim = 7 + cfg.n_assets

        self.fc1     = nn.Linear(input_dim, 128)
        self.fc2     = nn.Linear(128, 64)
        self.fc3     = nn.Linear(64, 32)
        self.fc4     = nn.Linear(32, self.output_dim)
        self.dropout = nn.Dropout(p=cfg.dropout_rate)

        # initialisation
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity='relu')
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity='relu')
        nn.init.kaiming_normal_(self.fc3.weight, nonlinearity='relu')
        nn.init.xavier_normal_(self.fc4.weight)

        # bias epsilon-initialisation to a small value eps_init (e.g., 2 steps)
        eps_init = min(max(cfg.eps_init, cfg.l_eps), cfg.u_eps - 1e-6)  
        eps_raw0 = math.log((eps_init - cfg.l_eps) / max(1e-8, (cfg.u_eps - eps_init)))

        with torch.no_grad():
            self.fc4.bias[2] = torch.tensor(
                eps_raw0, dtype=self.fc4.bias.dtype, device=self.fc4.bias.device
            )

    def forward(self, x):
        x = torch.relu(self.fc1(x)); x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = torch.relu(self.fc3(x))

        output = self.fc4(x)  

        delta_raw  = output[:, 0:1]
        gamma_raw  = output[:, 1:2]
        eps_raw    = output[:, 2:3]
        ch_logits  = output[:, 3:7] 
        w_logits   = output[:, 7:]       

        # rescale the scalars
        delta = cfg.l_delta + (cfg.u_delta - cfg.l_delta) * torch.sigmoid(delta_raw)
        gamma = cfg.u_gamma * torch.tanh(gamma_raw)
        epsil = cfg.l_eps + (cfg.u_eps - cfg.l_eps) * torch.sigmoid(eps_raw)

        # portfolio weights (per-row)
        weights = torch.softmax(w_logits, dim=1)  

        # average across rows (batch items)
        delta     = delta.mean(dim=0, keepdim=True)    
        gamma     = gamma.mean(dim=0, keepdim=True)    
        epsil     = epsil.mean(dim=0, keepdim=True)    
        ch_logits = ch_logits.mean(dim=0, keepdim=True) 
        weights   = weights.mean(dim=0, keepdim=True)  

        iq_parameters = torch.cat([delta, gamma, epsil], dim=1) 

        return iq_parameters, ch_logits, weights

def reinitialise_weights(model): # NN weights
    model.apply(lambda m: m.reset_parameters() if hasattr(m, 'reset_parameters') else None)

# save 'best' portfolio weights and 'optimum' IQ parameters values
def save_weights_to_csv(weights, iteration_date, project_type, group_number, model_number,
                        best_val_loss, best_params_dict, best_epoch_index, asset_names=None):

    base_dir   = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    folder_name = os.path.join(base_dir, "portfolios")
    os.makedirs(folder_name, exist_ok=True)

    # derive column names for weights from provided asset_names; fallback to A1..AN
    N = weights.shape[1] if weights.dim() > 1 else weights.numel()
    if asset_names is not None and len(asset_names) == N:
        tickers = list(asset_names)
    else:
        tickers = [f"A{i+1}" for i in range(N)]
    df_weights = pd.DataFrame(weights.cpu().numpy(), columns=tickers)

    bp = best_params_dict or {}
    df_weights["validation_loss"]  = best_val_loss
    df_weights["delta"]            = bp.get('delta',   float('nan'))
    df_weights["gamma"]            = bp.get('gamma',   float('nan'))
    df_weights["epsilon"]          = bp.get('epsilon', float('nan'))
    df_weights["wB"]               = bp.get('wB',      float('nan'))
    df_weights["wW"]               = bp.get('wW',      float('nan'))
    df_weights["wT"]               = bp.get('wT',      float('nan'))
    df_weights["wI"]               = bp.get('wI',      float('nan'))
    df_weights["cn_CIQ"]           = bp.get('cn_CIQ',  float('nan'))
    df_weights["ann_port_vol_val"] = bp.get('ann_port_vol_val', float('nan'))
    df_weights["best_epoch"]       = best_epoch_index
    df_weights["iq_method"]        = cfg.iq_method

    column_order = (
        tickers +
        ["validation_loss",
         "delta", "gamma", "epsilon", "wB", "wW", "wT", "wI", "cn_CIQ", "ann_port_vol_val", "iq_method",
         "best_epoch"]
    )
    df_weights = df_weights[column_order]
    df_weights.insert(0, "Date", iteration_date)
    df_weights = df_weights.round(6)

    file_name = f'shdiq_wgts_{project_type.lower()}_G{group_number}_M{model_number}.csv'
    file_path = os.path.join(folder_name, file_name)

    if os.path.exists(file_path):
        try:
            existing = pd.read_csv(file_path)
            for col in df_weights.columns:
                if col not in existing.columns:
                    existing[col] = np.nan
            existing = existing[df_weights.columns]
            combined = pd.concat([existing, df_weights], ignore_index=True)
            combined.to_csv(file_path, index=False)
        except Exception:
            df_weights.to_csv(file_path, mode='a', header=False, index=False)
    else:
        df_weights.to_csv(file_path, mode='w', header=True, index=False) 

def DIQ_train_network(model, optimizer, train_loader, validation_loader, project_type,
                      iteration_date, group_number, model_number, prev_weights=None,
                      train_rf_scalar=None, val_rf_scalar=None, asset_names=None):

    model.train()

    _lambda_wI_cap         = getattr(cfg, "lambda_wI_cap", 0.0)         # strength of soft cap penalty (>=0)
    _wI_cap_start          = getattr(cfg, "wI_cap_start", 1.0)          # cap at epoch 0 (no penalty if 1.0)
    _wI_cap_end            = getattr(cfg, "wI_cap_end",   1.0)          # cap at final epoch
    _wI_cap_schedule       = getattr(cfg, "wI_cap_schedule", "linear")  # {'linear','cosine'}
    _wI_cap_warmup_epochs  = getattr(cfg, "wI_cap_warmup_epochs", 0)    # keep start cap for first W epochs

    def _wI_cap_for_epoch(epoch_idx: int, total_epochs: int) -> float:
        """return the annealed cap for w_I at a given epoch index [0..total_epochs-1]."""
        if total_epochs <= 1:
            return float(_wI_cap_end)
        if epoch_idx < int(_wI_cap_warmup_epochs):
            return float(_wI_cap_start)
        denom = max(1, (total_epochs - int(_wI_cap_warmup_epochs) - 1))
        t = min(1.0, max(0.0, (epoch_idx - int(_wI_cap_warmup_epochs)) / denom))
        if _wI_cap_schedule.lower() == "cosine":
            # cosine anneal (smooth start & end)
            import math as _math
            t = 0.5 * (1.0 - _math.cos(_math.pi * t))
        # linear fallback
        return float(_wI_cap_start + ( _wI_cap_end - _wI_cap_start ) * t)
        
    epoch_metrics = {
        'losses'  : [],
        'gamma'   : [],
        'delta'   : [],
        'epsilon' : [],
        'wB'      : [],
        'wW'      : [],
        'wT'      : [],
        'wI'      : [],
        'weights' : [] 
    }
    saved_outputs     = []
    validation_losses = []

    total_start_time = time.time()
    cumulative_time  = 0

    scaler = torch.cuda.amp.GradScaler() if cfg.USE_GPU else None

    N = model.fc1.in_features 
    initial_weights = torch.rand((1, N)).to(cfg.device)
    initial_weights /= initial_weights.sum()

    prev_weights    = prev_weights if prev_weights is not None else initial_weights.clone()
    best_weights    = initial_weights.clone()
    min_val_loss    = float('inf')
    best_val_loss   = None 

    best_epoch_index  = -1
    best_epoch_params = {}

    for epoch in range(cfg.stp):
        epoch_start_time = time.time()
        total_loss = 0.0

        wB_epoch = []; wW_epoch = []; wT_epoch = []; wI_epoch = []
        gamma_epoch = []; delta_epoch = []; epsilon_epoch = []
        weights_epoch = []  

        vol_terms_batch  = []
        tvol_terms_batch = []
        cn_terms_batch   = []
        ent_terms_batch  = []
        rp_terms_batch   = []
        tw_terms_batch   = []
        t3w_terms_batch  = []
        sr_terms_batch   = []
        to_terms_batch   = []

        for batch in train_loader:
            rets_batch = batch.clone().detach().requires_grad_(True).to(cfg.device)
            optimizer.zero_grad()

            try:
                iq_parameters, channel_logits, weights = model(rets_batch)
                delta   = iq_parameters[0,0]
                gamma   = iq_parameters[0,1]
                epsilon = iq_parameters[0,2]

                # atomic IQ
                C = IQ_dispatch(rets_batch, gamma, delta, epsilon, channel_logits)

                expected_returns = compute_expected_returns(rets_batch)
                rf_scalar = train_rf_scalar if (cfg.rf_config.get('use_in_loss', True) and train_rf_scalar is not None) else 0.0
                loss, _, vol_term, tvol_term, cn_term, ent_term, rp_term, tw_term, t3w_term, sr_term, to_term = diq_loss(
                    C, weights,
                    prev_weights      = prev_weights,
                    expected_returns  = expected_returns,
                    target_vol        = cfg.target_vol,
                    lambda_vol        = cfg.lambda_vol,
                    lambda_target_vol = cfg.lambda_vol_target,
                    lambda_sharpe     = cfg.lambda_sharpe,       
                    lambda_turnover   = cfg.lambda_turnover,
                    lambda_cn         = cfg.lambda_cn,
                    lambda_entropy    = cfg.lambda_entropy,
                    lambda_rp         = cfg.lambda_rp,
                    lambda_tw         = cfg.lambda_tw,
                    max_tw            = cfg.max_tw,
                    lambda_t3w        = cfg.lambda_t3w,
                    max_t3w           = cfg.max_t3w,
                    kappa_anchor      = None,
                    risk_free_rate    = rf_scalar
                )


                # Add soft cap penalty on identity weight w_I with epoch-annealed cap.
                if _lambda_wI_cap != 0.0:
                    # Map logits -> (wB,wW,wT,wI) using the same helper as the mixers.
                    _w4  = _channel_weights_from_logits(channel_logits)
                    _wI  = _w4[3]
                    _cap = _wI_cap_for_epoch(epoch_idx=epoch, total_epochs=cfg.stp)
                    # Smooth hinge: penalize only when wI exceeds the cap; squared for gentle gradients.
                    loss = loss + float(_lambda_wI_cap) * F.relu(_wI - _cap) ** 2
                vol_terms_batch .append(vol_term)
                tvol_terms_batch.append(tvol_term)
                cn_terms_batch  .append(cn_term)
                ent_terms_batch .append(ent_term)
                rp_terms_batch  .append(rp_term)
                tw_terms_batch  .append(tw_term)
                t3w_terms_batch .append(t3w_term)
                sr_terms_batch  .append(sr_term)
                to_terms_batch  .append(to_term)

                if cfg.USE_GPU:
                    scaler.scale(loss).backward()
                    scaler.unscale_(optimizer)  # unscale grads before clipping
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()

                total_loss += float(loss.item())

                # record batch-level scalars
                w_soft = torch.softmax(channel_logits, dim=1).squeeze(0)
                wB, wW, wT, wI = [float(w_soft[i].item()) for i in range(4)]

                gamma_epoch.append(float(gamma.item()))
                delta_epoch.append(float(delta.item()))
                epsilon_epoch.append(float(epsilon.item()))
                wB_epoch.append(wB); wW_epoch.append(wW); wT_epoch.append(wT); wI_epoch.append(wI)
                weights_epoch.append(weights.cpu().detach().numpy().tolist()) 

            except torch._C._LinAlgError as e:
                print(f"Skipping batch due to LinAlgError: {e}")
                continue  

        def _avg(x): 
            import numpy as _np
            return float(_np.mean(x)) if len(x) else float('nan')

        avg_vol_term  = _avg(vol_terms_batch)
        avg_tvol_term = _avg(tvol_terms_batch)
        avg_cn_term   = _avg(cn_terms_batch)
        avg_ent_term  = _avg(ent_terms_batch)
        avg_rp_term   = _avg(rp_terms_batch)
        avg_tw_term   = _avg(tw_terms_batch)
        avg_t3w_term  = _avg(t3w_terms_batch)
        avg_sr_term   = _avg(sr_terms_batch)
        avg_to_term   = _avg(to_terms_batch)

        log_row = {
            'iteration_date': iteration_date,
            'model_number': model_number,
            'epoch'       : epoch+1,
            'phase'       : 'train',
            'vol'         : avg_vol_term,
            'tvol'        : avg_tvol_term,
            'cn'          : avg_cn_term,
            'ent'         : avg_ent_term,
            'rp'          : avg_rp_term,
            'tw'          : avg_tw_term,
            't3w'         : avg_t3w_term,
            'sr'          : avg_sr_term,
            'to'          : avg_to_term
        }
        pd.DataFrame([log_row]).to_csv("master_loss_log.csv", mode='a', header=not os.path.exists("master_loss_log.csv"), index=False)

        epoch_metrics['losses'] .append(total_loss/len(train_loader) if len(train_loader) else float('nan'))  
        epoch_metrics['gamma']  .append(_avg(gamma_epoch))
        epoch_metrics['delta']  .append(_avg(delta_epoch))
        epoch_metrics['epsilon'].append(_avg(epsilon_epoch))
        epoch_metrics['wB']     .append(_avg(wB_epoch))
        epoch_metrics['wW']     .append(_avg(wW_epoch))
        epoch_metrics['wT']     .append(_avg(wT_epoch))
        epoch_metrics['wI']     .append(_avg(wI_epoch))
        epoch_metrics['weights'].append(np.mean(weights_epoch,axis=0) if weights_epoch else [float('nan')])

        # validation
        val_vol_terms  = []
        val_tvol_terms = []
        val_cn_terms   = []
        val_ent_terms  = []
        val_rp_terms   = []
        val_tw_terms   = []
        val_t3w_terms  = []
        val_sr_terms   = []
        val_to_terms   = []

        model.eval()
        with torch.no_grad():
            validation_loss = 0.0
            for val_batch in validation_loader:
                val_rets_batch = val_batch.clone().detach().to(cfg.device)
                try:
                    val_iq_parameters, val_channel_logits, val_weights = model(val_rets_batch)
                    val_delta   = val_iq_parameters[0,0]
                    val_gamma   = val_iq_parameters[0,1]
                    val_epsilon = val_iq_parameters[0,2]

                    val_C = IQ_dispatch(val_rets_batch, val_gamma, val_delta, val_epsilon, val_channel_logits)

                    val_expected_returns = compute_expected_returns(val_rets_batch)
                    rf_val_scalar = val_rf_scalar if (cfg.rf_config.get('use_in_loss', True) and val_rf_scalar is not None) else 0.0
                    val_loss, ann_port_volatility, val_vol_term, val_tvol_term, val_cn_term, val_entropy_term, val_rp_term, val_tw_term, val_t3w_term, val_sr_term, val_to_term = diq_loss(
                        val_C, val_weights,
                        prev_weights      = prev_weights,
                        expected_returns  = val_expected_returns,
                        target_vol        = cfg.target_vol,
                        lambda_vol        = cfg.lambda_vol,
                        lambda_target_vol = cfg.lambda_vol_target,
                        lambda_sharpe     = cfg.lambda_sharpe,
                        lambda_turnover   = cfg.lambda_turnover,
                        lambda_cn         = cfg.lambda_cn,
                        lambda_entropy    = cfg.lambda_entropy,
                        lambda_rp         = cfg.lambda_rp,
                        lambda_tw         = cfg.lambda_tw,
                        max_tw            = cfg.max_tw,
                        lambda_t3w        = cfg.lambda_t3w,
                        max_t3w           = cfg.max_t3w,
                        kappa_anchor      = None,
                        risk_free_rate    = rf_val_scalar
                    )


                    # Validation: apply the same soft cap penalty so selection honours the cap.
                    if _lambda_wI_cap != 0.0:
                        _vw4  = _channel_weights_from_logits(val_channel_logits)
                        _vwI  = _vw4[3]
                        _vcap = _wI_cap_for_epoch(epoch_idx=epoch, total_epochs=cfg.stp)
                        val_loss = val_loss + float(_lambda_wI_cap) * F.relu(_vwI - _vcap) ** 2
                    val_vol_terms .append(val_vol_term)
                    val_tvol_terms.append(val_tvol_term)
                    val_cn_terms  .append(val_cn_term)
                    val_ent_terms .append(val_entropy_term)
                    val_rp_terms  .append(val_rp_term)
                    val_tw_terms  .append(val_tw_term)
                    val_t3w_terms .append(val_t3w_term)
                    val_sr_terms  .append(val_sr_term)
                    val_to_terms  .append(val_to_term)

                    validation_loss += float(val_loss.item())
                    if val_loss.item() < min_val_loss:
                        min_val_loss      = val_loss.item()
                        best_weights      = val_weights.clone().detach()
                        best_val_loss     = min_val_loss
                        best_epoch_index  = epoch

                        # compute CN of implied correlation (for logging only)
                        try:
                            stds_v = val_rets_batch.std(dim=0) + 1e-12
                            inv_stds = 1.0 / stds_v
                            D_inv = torch.diag(inv_stds)
                            C_IQ_v = D_inv @ val_C @ D_inv
                            C_IQ_v = 0.5 * (C_IQ_v + C_IQ_v.T)
                            C_IQ_v.fill_diagonal_(1.0)
                            C_IQ_v = torch.clamp(C_IQ_v, min=-1.0, max=1.0)
                            eigvals_C = torch.linalg.eigvalsh(C_IQ_v).real
                            lam_min = torch.clamp(torch.min(eigvals_C), min=torch.tensor(1e-12, device=eigvals_C.device, dtype=eigvals_C.dtype))
                            lam_max = torch.max(eigvals_C)
                            cn_corr_val = (lam_max / lam_min).item()
                        except Exception:
                            cn_corr_val = float('nan')
                        best_epoch_params = {
                            'delta'  : _avg(delta_epoch),
                            'gamma'  : _avg(gamma_epoch),
                            'epsilon': _avg(epsilon_epoch),
                            'wB'     : _avg(wB_epoch),
                            'wW'     : _avg(wW_epoch),
                            'wT'     : _avg(wT_epoch),
                            'wI'     : _avg(wI_epoch),
                            'cn_CIQ' : cn_corr_val,
                            'ann_port_vol_val': float(ann_port_volatility)
                        }

                except torch._C._LinAlgError as e:
                    print(f"Skipping validation batch due to LinAlgError: {e}")
                    continue  

            def _vavg(x): 
                import numpy as _np
                return float(_np.mean(x)) if len(x) else float('nan')

            avg_val_vol  = _vavg(val_vol_terms)
            avg_val_tvol = _vavg(val_tvol_terms)
            avg_val_cn   = _vavg(val_cn_terms)
            avg_val_ent  = _vavg(val_ent_terms)
            avg_val_rp   = _vavg(val_rp_terms)
            avg_val_tw   = _vavg(val_tw_terms)
            avg_val_t3w  = _vavg(val_t3w_terms)
            avg_val_sr   = _vavg(val_sr_terms)
            avg_val_to   = _vavg(val_to_terms)

            avg_validation_loss = validation_loss / len(validation_loader) if validation_loader else float('nan')
            validation_losses.append(avg_validation_loss)

            log_row = {
                'iteration_date': iteration_date,
                'model_number': model_number,
                'epoch': epoch+1,
                'phase': 'val',
                'vol'  : avg_val_vol,
                'tvol' : avg_val_tvol,
                'cn'   : avg_val_cn,
                'ent'  : avg_val_ent,
                'rp'   : avg_val_rp,
                'tw'   : avg_val_tw,
                't3w'  : avg_val_t3w,
                'sr'   : avg_val_sr,
                'to'   : avg_val_to
            }
            pd.DataFrame([log_row]).to_csv("master_loss_log.csv", mode='a', header=not os.path.exists("master_loss_log.csv"), index=False)

        epoch_duration = time.time() - epoch_start_time
        cumulative_time += epoch_duration

        if (epoch + 1) == int(cfg.stp / 2):
            print(f'half-way through {cfg.stp} epochs: {round(cumulative_time)} seconds')

    # save best validation weights for current iteration
    if not torch.isnan(best_weights).any():
        save_weights_to_csv(
            best_weights, iteration_date, project_type, group_number, model_number, 
            best_val_loss, best_epoch_params, best_epoch_index, asset_names=asset_names
        )
    else:
        print("Warning: NaN values detected in best_weights. Skipping save for this iteration.")

    outputs_at_final_epoch = {
        'epoch'   : cfg.stp,
        'gamma'   : _avg(gamma_epoch),
        'delta'   : _avg(delta_epoch),
        'epsilon' : _avg(epsilon_epoch),
        'wB'      : _avg(wB_epoch),
        'wW'      : _avg(wW_epoch),
        'wT'      : _avg(wT_epoch),
        'wI'      : _avg(wI_epoch),
        'weights' : np.mean(weights_epoch, axis=0) if weights_epoch else [float('nan')]
    }

    saved_outputs.append(outputs_at_final_epoch)
    total_duration = time.time() - total_start_time

    return saved_outputs, epoch_metrics, validation_losses, best_weights

def compute_expected_returns(rets_batch):
    mode = getattr(cfg, 'exp_ret_style', 'geometric')
    if str(mode).lower().startswith('arith'):
        # arithmetic mean across time (batch rows)
        return torch.mean(rets_batch, dim=0)
    else:
        # geometric mean across time (batch rows)
        returns  = rets_batch + 1
        geo_mean = torch.exp(torch.mean(torch.log(returns), dim=0)) - 1
        return geo_mean

def diq_loss(
    cov_matrix, 
    weights, 
    prev_weights      =None, 
    expected_returns  =None, # must be provided if lambda_sharpe > 0
    target_vol        =0.0, 
    lambda_vol        =0.0, 
    lambda_target_vol =0.0, 
    lambda_sharpe     =0.0, 
    lambda_turnover   =0.0, 
    lambda_cn         =0.0,
    lambda_entropy    =0.0,
    lambda_rp         =0.0,
    lambda_tw: float  =0.0, 
    max_tw: float     =1.0,    
    lambda_t3w: float =0.0,  
    max_t3w: float    =1.0,     
    kappa_anchor      =None, # must be provided if lambda_cn > 0
    risk_free_rate    =0.0   # per-period risk-free scalar
):

    total_loss = torch.tensor(0.0, dtype=weights.dtype, device=weights.device)

    portfolio_variance   = torch.matmul(weights, torch.matmul(cov_matrix, weights.T)).squeeze()
    portfolio_variance   = torch.clamp(portfolio_variance, min=0.0)
    portfolio_volatility = torch.sqrt(portfolio_variance)     
    sqrt12               = torch.tensor(12.0, dtype=weights.dtype, device=weights.device).sqrt()
    ann_port_volatility  = 100.0 * sqrt12 * portfolio_volatility    

    eps = torch.tensor(1e-8, device=portfolio_volatility.device)

    # volatility penalty 
    vol_ratio       = portfolio_volatility/(target_vol + eps)
    vol_pen         = vol_ratio
    if lambda_vol  != 0:
        total_loss += lambda_vol * vol_pen

    # target ceiling penalty 
    excess_ratio    = torch.relu(vol_ratio - 1.0)      
    target_vol_pen  = excess_ratio  
    if lambda_target_vol != 0:
        total_loss += lambda_target_vol * target_vol_pen

    # Sharpe ratio penalty
    # denominator uses std of returns from Σ. with scalar 
    # risk_free_rate (constant within the batch), std(R - rf) == std(R),
    # this equals std of excess returns by construction.
    sh_pen = torch.tensor(float('nan'), dtype=weights.dtype, device=weights.device)
    portfolio_return = None

    if expected_returns is not None:
        exp_ret = expected_returns
        if exp_ret.dim() > 1 and exp_ret.size(-1) == 1:
            exp_ret = exp_ret.squeeze(-1)  # allow (N,1) inputs

        portfolio_return = (weights * exp_ret).sum(dim=-1)
        sharpe_ratio = (portfolio_return - risk_free_rate) / (portfolio_volatility + 1e-12)
        sh_pen = -sharpe_ratio.squeeze()

    if lambda_sharpe != 0:
        if expected_returns is None:
            raise ValueError("expected_returns must be provided when lambda_sharpe != 0.")
        total_loss = total_loss + lambda_sharpe * sh_pen

    # turnover penalty
    to_pen = torch.tensor(float('nan'), dtype=weights.dtype, device=weights.device)
    turnover_per_sample = None  

    if prev_weights is not None:
        pw = prev_weights

        if pw.shape != weights.shape:
            if pw.dim() == 1 and weights.dim() > 1 and pw.numel() == weights.size(-1):
                pw = pw.unsqueeze(0).expand_as(weights)  
            else:
                raise ValueError(f"`prev_weights` shape {prev_weights.shape} is not compatible with `weights` {weights.shape}.")

        diff = weights - pw
        if diff.dim() > 1:
            turnover_per_sample = diff.abs().sum(dim=-1)  
            to_pen = turnover_per_sample.mean()          
        else:
            to_pen = diff.abs().sum()            

    if lambda_turnover != 0:
        if prev_weights is None:
            raise ValueError("`prev_weights` must be provided when `lambda_turnover` is non-zero.")
        total_loss = total_loss + lambda_turnover * to_pen

    # condition number penalty
    N = weights.shape[-1]
    cn_pen = torch.tensor(0.0, dtype=weights.dtype, device=weights.device)
    if lambda_cn != 0.0:
        eigvals   = torch.linalg.eigvalsh(cov_matrix).real
        cn        = (eigvals.max() + 1e-12) / (eigvals.min() + 1e-12)
        log_cn    = torch.log(cn)

        sqrtN = torch.sqrt(torch.tensor(float(N), dtype=weights.dtype, device=weights.device))
        log10 = torch.log(torch.tensor(10.0, dtype=weights.dtype, device=weights.device))
        c = 1.0  # tighten/loosen cap by changing c in (0,1]
        log_kappa_cap = c * sqrtN * log10

        r = log_cn / (log_kappa_cap + 1e-12) 
        cn_pen = r / (1.0 + r)              
        total_loss += lambda_cn * cn_pen

    # entropy concentration (0 = diversified, 1 = one-hot)
    logN    = torch.log(torch.tensor(N, dtype=weights.dtype, device=weights.device))
    H       = -torch.sum(weights * torch.clamp(weights, min=eps).log())
    ent_pen = 1.0 - H / (logN + eps)          
    if lambda_entropy != 0.0:
        total_loss += lambda_entropy * ent_pen

    # risk-parity penalty
    rp_pen = torch.tensor(0.0, dtype=weights.dtype, device=weights.device)
    if lambda_rp != 0.0:
        covW        = cov_matrix @ weights.T   
        rc          = weights.T * covW               
        rc          = rc / (rc.sum() + eps)           
        rp_b        = torch.full_like(rc, 1.0 / N)
        rp_raw      = torch.sum((rc - rp_b) ** 2)     
        rp_norm     = rp_raw / ((N - 1.0) / N + eps)   
        rp_pen      = rp_norm / (1.0 + rp_norm)        
        total_loss += lambda_rp * rp_pen

    # specific wgts concentration penalties: top-1 and top-3 (normalised linear hinges)
    w2 = weights if weights.dim() == 2 else weights.unsqueeze(0)

    # top-1
    wmax      = torch.amax(w2, dim=1) 
    tw_pen    = torch.relu(wmax - max_tw) / (1.0 - max_tw + eps)
    tw_pen    = tw_pen.mean()
    if lambda_tw != 0.0:
        total_loss += lambda_tw * tw_pen
    # top-3
    k         = min(3, w2.shape[1])
    sum_topk  = torch.topk(w2, k=k, dim=1).values.sum(dim=1)
    t3w_pen   = torch.relu(sum_topk - max_t3w) / (1.0 - max_t3w + eps)
    t3w_pen   = t3w_pen.mean()
    if lambda_t3w != 0.0:
        total_loss += lambda_t3w * t3w_pen

    return (
        total_loss,
        ann_port_volatility.item(),
        vol_pen.item(),
        target_vol_pen.item(),
        cn_pen.item(),
        ent_pen.item(),
        rp_pen.item(),
        tw_pen.item(),
        t3w_pen.item(),
        sh_pen.item(),
        to_pen.item()
    )

def is_psd_def(cov_mat, tol: float = 1e-8, verbose: bool = False) -> bool:
    """Check if a symmetric matrix is PSD up to tolerance."""
    evals = torch.linalg.eigh(cov_mat)[0].real
    lam_min = float(torch.min(evals))
    lam_max = float(torch.max(evals))
    if verbose:
        print(f"[PSD check] min eig = {lam_min:.3e}, max eig = {lam_max:.3e}")
    return torch.all(evals >= -tol)

# atomic IQ1 (whole-atom scaling)
def IQ1(Rets, gamma, delta, epsil, mix_logits, center_method=None, scale_method=None, threshold=None, PSD_hard=None):

    center_method = cfg.center_method if center_method is None else center_method
    scale_method  = cfg.scale_method  if scale_method  is None else scale_method
    threshold     = cfg.threshold     if threshold     is None else threshold
    PSD_hard      = cfg.PSD_hard      if PSD_hard      is None else PSD_hard

    device, dtype = Rets.device, Rets.dtype
    T, N = Rets.shape

    # center
    if center_method == "mean":
        mean_vec = Rets.mean(dim=0, keepdim=True)
    elif center_method == "median":
        mean_vec = Rets.median(dim=0).values.unsqueeze(0)
    elif center_method == "zero":
        mean_vec = torch.zeros((1,N), dtype=dtype, device=device)
    else:
        raise ValueError("center_method must be 'mean','median','zero'")
    X = Rets - mean_vec

    # scale
    stds = Rets.std(dim=0) + 1e-12
    Xs   = X / stds.unsqueeze(0)
    absX = torch.abs(Xs)
    thr  = torch.as_tensor(threshold, dtype=dtype, device=device)
    delt = torch.as_tensor(delta, dtype=dtype, device=device)

    # temporal
    a = _temporal_factors(
        T, gamma.squeeze(), epsil.squeeze(), device, dtype,
        mode=getattr(cfg, "gamma_mode", "signed"),
        gamma_max=getattr(cfg, "u_gamma", None),
        eps_floor=getattr(cfg, "a_floor", 0.0),
        schur_safe=False
    )

    # accumulators
    G_B = torch.zeros((N,N), dtype=dtype, device=device)
    G_W = torch.zeros((N,N), dtype=dtype, device=device)
    G_T = torch.zeros((N,N), dtype=dtype, device=device)

    for i in range(N):
        xi = Xs[:, i]; axi = absX[:, i]
        for j in range(i, N):
            xj = Xs[:, j]; axj = absX[:, j]
            sgn = torch.sign(xi) * torch.sign(xj)

            black = (axi <= thr) | (axj <= thr)
            body  = (~black) & (axi <= delt) & (axj <= delt)
            wing  = (~black) & ((axi <= delt) ^ (axj <= delt))
            tail  = (~black) & (axi >  delt) & (axj >  delt)

            if body.any():
                w = a[body]; sb = sgn[body]
                G_B[i,i] += w.sum();     G_B[j,j] += (w.sum() if j!=i else 0.0)
                if j!=i: G_B[i,j] += (w*sb).sum(); G_B[j,i] = G_B[i,j]
            if wing.any():
                w = a[wing]; sw = sgn[wing]
                G_W[i,i] += w.sum();     G_W[j,j] += (w.sum() if j!=i else 0.0)
                if j!=i: G_W[i,j] += (w*sw).sum(); G_W[j,i] = G_W[i,j]
            if tail.any():
                w = a[tail]; st = sgn[tail]
                G_T[i,i] += w.sum();     G_T[j,j] += (w.sum() if j!=i else 0.0)
                if j!=i: G_T[i,j] += (w*st).sum(); G_T[j,i] = G_T[i,j]

    C_B, C_W, C_T = _to_corr(G_B), _to_corr(G_W), _to_corr(G_T)

    w = _channel_weights_from_logits(mix_logits) 
    wB, wW, wT, wI = w.unbind(0)                

    C_IQ = wB*C_B + wW*C_W + wT*C_T + wI*torch.eye(N, dtype=dtype, device=device)

    if PSD_hard and not is_psd_def(C_IQ, verbose=False):
        mine = float(torch.min(torch.linalg.eigvalsh(C_IQ)))
        raise RuntimeError(f'Atomic IQ1 produced non-PSD correlation (min eig={mine:.3e})')

    SD = torch.diag(stds)
    Sigma_IQ = SD @ C_IQ @ SD
    return Sigma_IQ

# atomic IQ2 (off-diagonal-only scaling)
def IQ2(Rets, gamma, delta, epsil, mix_logits, center_method=None, scale_method=None, threshold=None, PSD_hard=None):

    center_method = cfg.center_method if center_method is None else center_method
    scale_method  = cfg.scale_method  if scale_method  is None else scale_method
    threshold     = cfg.threshold     if threshold     is None else threshold
    PSD_hard      = cfg.PSD_hard      if PSD_hard      is None else PSD_hard

    device, dtype = Rets.device, Rets.dtype
    T, N = Rets.shape

    # center
    if center_method == "mean":
        mean_vec = Rets.mean(dim=0, keepdim=True)
    elif center_method == "median":
        mean_vec = Rets.median(dim=0).values.unsqueeze(0)
    elif center_method == "zero":
        mean_vec = torch.zeros((1,N), dtype=dtype, device=device)
    else:
        raise ValueError("center_method must be 'mean','median','zero'")
    X = Rets - mean_vec

    # scale
    stds = Rets.std(dim=0) + 1e-12
    Xs   = X / stds.unsqueeze(0)
    absX = torch.abs(Xs)
    thr  = torch.as_tensor(threshold, dtype=dtype, device=device)
    delt = torch.as_tensor(delta, dtype=dtype, device=device)

    # temporal 
    a = _temporal_factors(
        T, gamma.squeeze(), epsil.squeeze(), device, dtype,
        mode=getattr(cfg, "gamma_mode", "signed"),
        gamma_max=getattr(cfg, "u_gamma", None),
        eps_floor=getattr(cfg, "a_floor", 0.0),
        schur_safe=True   # ensures PSD via a_t <= 1
    )

    # accumulators
    G_B = torch.zeros((N,N), dtype=dtype, device=device)
    G_W = torch.zeros((N,N), dtype=dtype, device=device)
    G_T = torch.zeros((N,N), dtype=dtype, device=device)

    for i in range(N):
        xi = Xs[:, i]; axi = absX[:, i]
        for j in range(i, N):
            xj = Xs[:, j]; axj = absX[:, j]
            sgn = torch.sign(xi) * torch.sign(xj)

            black = (axi <= thr) | (axj <= thr)
            body  = (~black) & (axi <= delt) & (axj <= delt)
            wing  = (~black) & ((axi <= delt) ^ (axj <= delt))
            tail  = (~black) & (axi >  delt) & (axj >  delt)

            if body.any():
                cnt = float(body.sum())
                G_B[i,i] += cnt;  G_B[j,j] += (cnt if j!=i else 0.0)
                if j!=i: G_B[i,j] += (a[body]*sgn[body]).sum(); G_B[j,i] = G_B[i,j]
            if wing.any():
                cnt = float(wing.sum())
                G_W[i,i] += cnt;  G_W[j,j] += (cnt if j!=i else 0.0)
                if j!=i: G_W[i,j] += (a[wing]*sgn[wing]).sum(); G_W[j,i] = G_W[i,j]
            if tail.any():
                cnt = float(tail.sum())
                G_T[i,i] += cnt;  G_T[j,j] += (cnt if j!=i else 0.0)
                if j!=i: G_T[i,j] += (a[tail]*sgn[tail]).sum(); G_T[j,i] = G_T[i,j]

    C_B, C_W, C_T = _to_corr(G_B), _to_corr(G_W), _to_corr(G_T)

    w = _channel_weights_from_logits(mix_logits)  
    wB, wW, wT, wI = w.unbind(0)            

    C_IQ = wB*C_B + wW*C_W + wT*C_T + wI*torch.eye(N, dtype=dtype, device=device)

    if PSD_hard and not is_psd_def(C_IQ, verbose=False):
        mine = float(torch.min(torch.linalg.eigvalsh(C_IQ)))
        raise RuntimeError(f'Atomic IQ2 produced non-PSD correlation (min eig={mine:.3e})')

    SD = torch.diag(stds)
    Sigma_IQ = SD @ C_IQ @ SD
    return Sigma_IQ
