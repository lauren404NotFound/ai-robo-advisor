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
Name     : MainSR.py  
Contact  : drwss.academy@gmail.com
Date     : 11/10/2025
Desc     : Runner for DeepAtomicIQ MaxSR project and multi-asset-class portfolio
"""

import os
import pickle
import random
import sys
import time
import torch
import MINNlib as mb
import numpy as np
import pandas as pd
import project_hyperparameters as cfg
import torch.optim as optim
from datetime import datetime
from calendar import monthrange

print()
print('tanh-limit for temporal discounting     : ', cfg.u_gamma)
print('target annualised portfolio volatility  : ', cfg.ann_target_vol,'%')
print('coefficient for ceiling volatility loss : ', round(cfg.lambda_vol_target,2))
print()
print('which multi-asset-class portfolio : ', cfg.n_assets)
print('OOS-period start date             : ', cfg.dates['start']) 
print('OOS-period end date               : ', cfg.dates['end']) 
print('running dynamic risk-free rate    : ', cfg.rf_config["enabled"] )
print()
print('coefficient for volatility loss            : ', round(cfg.lambda_vol,2))
print('coefficient for CN regularisation          : ', round(cfg.lambda_cn,2))
print('coefficient for entropy regularisation     : ', round(cfg.lambda_entropy,2))
print('coefficient for risk parity regularisation : ', round(cfg.lambda_rp,2))
print('coefficient largest pfolio weight penalty  : ', round(cfg.lambda_tw,2))
print('coefficient largest top-3 weights penalty  : ', round(cfg.lambda_t3w,2))
print('coefficient for Sharpe ratio loss          : ', round(cfg.lambda_sharpe,2))
print('coefficient for turnover regularisation    : ', round(cfg.lambda_turnover,2))
print()
print('method of co-movement centering            : ', cfg.center_method)
print('method of co-movement scaling              : ', cfg.scale_method)
print()
print(f"Using Atomic IQ: {cfg.iq_method} ({cfg.iq_method_description})")
print()

# CLI: group_number + project_type
if len(sys.argv) != 3:
    print("Usage: python MainSR.py <group_number> <project_type>")
    print("<project_type> should be 'MaxSR'")
    sys.exit(1)

group_number = int(sys.argv[1])
project_type = sys.argv[2]

if project_type != 'MaxSR':
    print("Error: Invalid project_type. It should be 'MaxSR'.")
    sys.exit(1)

print(f"Group_{group_number} model(s) working on {project_type} project.")
print()

seed = 260370
torch.manual_seed(seed)
np.random.seed(seed)
random.seed(seed)

timestamp = datetime.now().strftime("%H%M_%d-%m-%y")
os.makedirs('saved_settings', exist_ok=True)

# price slicing logic
def _parse_month_string_to_bounds(s: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    accept inputs like 'Dec 2003', '2003-12', 'December 2003', etc.
    returns (month_start, month_end) as timestamps on the first/last calendar day.
    """
    ts          = pd.to_datetime(s)
    month_start = pd.Timestamp(year=ts.year, month=ts.month, day=1)
    last_day    = monthrange(ts.year, ts.month)[1]
    month_end   = pd.Timestamp(year=ts.year, month=ts.month, day=last_day)
    return month_start, month_end

def _ceil_to_existing(df: pd.DataFrame, date_col: str, target: pd.Timestamp) -> pd.Timestamp:
    """smallest available date >= target."""
    s = df[date_col]
    choices = s[s >= target]
    if choices.empty:
        raise ValueError(f"No available date >= {target.date()} in master data.")
    return pd.Timestamp(choices.min())

def _floor_to_existing(df: pd.DataFrame, date_col: str, target: pd.Timestamp) -> pd.Timestamp:
    """greatest available date <= target."""
    s = df[date_col]
    choices = s[s <= target]
    if choices.empty:
        raise ValueError(f"No available date <= {target.date()} in master data.")
    return pd.Timestamp(choices.max())

def _safe_slice(df: pd.DataFrame, date_col: str,
                start: pd.Timestamp, end: pd.Timestamp, include_end: bool) -> pd.DataFrame:
    if include_end:
        mask = (df[date_col] >= start) & (df[date_col] <= end)
    else:
        mask = (df[date_col] >= start) & (df[date_col] < end)
    out = df.loc[mask].copy()
    if out.empty:
        raise ValueError(f"Empty slice for start={start.date()}, end={end.date()}, include_end={include_end}.")
    return out

def build_price_slices_from_master(master_csv: str,
                                   date_col: str,
                                   n_assets: int,
                                   start_str: str,
                                   end_str: str,
                                   M_months: int,
                                   R_months: int):
    """
    returns (deep_df, mvo_df, meta)
      Deep: [ start_aligned - (M+R), end_aligned )
      MVO : [ start_aligned - M, end_aligned ]   
    assets: first n_assets columns after date.
    dates: month strings interpreted as month-start/month-end, then aligned to existing rows.
    """
    df = pd.read_csv(master_csv)
    if "Date" not in df.columns:
        raise ValueError(f"'Date' column not found in {master_csv}.")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    asset_cols = [c for c in df.columns if c != "Date"]
    if n_assets not in (9, 10):
        raise ValueError("n_assets must be 9 or 10.")
    if len(asset_cols) < n_assets:
        raise ValueError(f"Requested n_assets={n_assets}, but only {len(asset_cols)} assets present.")
    selected_assets = asset_cols[:n_assets]

    start_month_start, _ = _parse_month_string_to_bounds(start_str)
    _, end_month_end = _parse_month_string_to_bounds(end_str)

    start_aligned = _ceil_to_existing(df, "Date", start_month_start)
    end_aligned = _floor_to_existing(df, "Date", end_month_end)

    deep_start = start_aligned - pd.DateOffset(months=(M_months + R_months))
    deep_start_aligned = _ceil_to_existing(df, "Date", deep_start)
    deep_df = _safe_slice(df[["Date"] + selected_assets], "Date", deep_start_aligned, end_aligned, include_end=False)

    mvo_start = start_aligned - pd.DateOffset(months=M_months)
    mvo_start_aligned = _ceil_to_existing(df, "Date", mvo_start)
    mvo_df = _safe_slice(df[["Date"] + selected_assets], "Date", mvo_start_aligned, end_aligned, include_end=True)

    meta = {
        "selected_assets": selected_assets,
        "anchors": {
            "requested": {
                "start_month_start": str(start_month_start.date()),
                "end_month_end":     str(end_month_end.date()),
            },
            "aligned": {
                "start_aligned":     str(start_aligned.date()),
                "end_aligned":       str(end_aligned.date()),
                "deep_start_aligned":str(deep_start_aligned.date()),
                "mvo_start_aligned": str(mvo_start_aligned.date()),
            }
        },
        "shapes": {
            "deep_rows": len(deep_df),
            "mvo_rows":  len(mvo_df),
        }
    }
    return deep_df, mvo_df, meta

def write_slice_csvs(deep_df: pd.DataFrame, mvo_df: pd.DataFrame, meta: dict,
                     out_dir: str, deep_filename: str | None, mvo_filename: str | None):
    os.makedirs(out_dir, exist_ok=True)

    n_assets      = len(meta["selected_assets"])
    start_aligned = meta["anchors"]["aligned"]["start_aligned"]
    end_aligned   = meta["anchors"]["aligned"]["end_aligned"]

    deep_fname = deep_filename or f"deep_prices_{n_assets}_{start_aligned}_{end_aligned}.csv"
    mvo_fname  = mvo_filename  or f"mvo_prices_{n_assets}_{start_aligned}_{end_aligned}.csv"

    deep_path = os.path.join(out_dir, deep_fname)
    mvo_path  = os.path.join(out_dir, mvo_fname)

    deep_df.to_csv(deep_path, index=False)
    mvo_df.to_csv(mvo_path, index=False)
    return {"deep_path": deep_path, "mvo_path": mvo_path}

deep_df, mvo_df, slice_meta = build_price_slices_from_master(
    master_csv=cfg.master_prices_csv,
    date_col  ="Date",
    n_assets  =cfg.n_assets,
    start_str =cfg.dates["start"],
    end_str   =cfg.dates["end"],
    M_months  =cfg.m,
    R_months  =cfg.r
)

paths = write_slice_csvs(
    deep_df, mvo_df, slice_meta,
    out_dir=cfg.price_dir,
    deep_filename=cfg.deep_filename,
    mvo_filename=cfg.mvo_filename
)

# train on the Deep slice (prices -> returns)
data      = deep_df.set_index("Date")
cfg.study_price_data = deep_df
returns   = data.pct_change().dropna()
input_dim = returns.shape[1]

# align monthly risk-free series to returns index 
rf_aligned = None
if cfg.rf_config.get('use_in_loss', True):
    rf_aligned = mb.load_rfr_aligned_to_returns(
        cfg.rf_config['csv_path'], returns.index,
        frequency     =cfg.rf_config.get('frequency','M'),
        column        =cfg.rf_config.get('column', None),
        align_method  =cfg.rf_config.get('align_method','ffill'),
        interpretation=cfg.rf_config.get('interpretation','monthly_effective')
    )

# create rolling batches and models
batches_collection = mb.create_rolling_batches(returns)
models             = [mb.DeepIQNetPortfolio(input_dim).to(cfg.device) for _ in range(cfg.n_models)]
optimizers         = [optim.Adam(model.parameters(), lr=0.001) for model in models]
total_iterations   = len(batches_collection)

start_iterations = []
for i in range(cfg.n_models):
    global_model_number = (group_number - 1) * cfg.n_models + (i + 1)
    start_iteration = global_model_number - 1
    start_iterations.append(start_iteration)
print()
print()

# initialise prev_weights for turnover regularisation
prev_weights = [None] * cfg.n_models

for iteration_index, iteration_batches in enumerate(batches_collection):
    start_idx  = iteration_index
    end_idx    = start_idx + cfg.r - 1
    start_date = returns.index[start_idx].strftime('%d/%m/%y')
    end_date   = returns.index[end_idx].strftime('%d/%m/%y')

    print(f'started iteration_{iteration_index + 1} ({start_date}) of {total_iterations}')
    iteration_start_time = time.time()

    # prepare training data
    train_loader = [torch.tensor(batch.values, dtype=torch.float32).to(cfg.device) for batch in iteration_batches]
    print(f'loaded training data from index {start_idx} to {end_idx}')

    # per-iteration risk-free rate scalars
    if rf_aligned is not None:
        train_rf_scalar = (float(rf_aligned.iloc[start_idx:end_idx+1].mean())
                    if str(getattr(cfg, 'rf_style', 'geometric')).lower().startswith('arith')
                    else mb.geom_mean_of_returns(rf_aligned.iloc[start_idx:end_idx+1]))
    else:
        train_rf_scalar = 0.0

    # prepare validation data
    validation_start_idx = end_idx + 1
    validation_end_idx   = validation_start_idx + cfg.m - 1
    if validation_end_idx >= len(returns):
        print("No more data available for validation. Ending training.")
        break

    validation_data   = returns.iloc[validation_start_idx:validation_end_idx + 1]
    validation_loader = [torch.tensor(validation_data.values, dtype=torch.float32).to(cfg.device)]
    print(f'prepared out-of-sample validation data from index {validation_start_idx} to {validation_end_idx}')

    if rf_aligned is not None:
        val_rf_scalar = (float(rf_aligned.iloc[validation_start_idx:validation_end_idx+1].mean())
                  if str(getattr(cfg, 'rf_style', 'geometric')).lower().startswith('arith')
                  else mb.geom_mean_of_returns(rf_aligned.iloc[validation_start_idx:validation_end_idx+1]))
    else:
        val_rf_scalar = 0.0

    for i in range(cfg.n_models):
        model_start_iteration = start_iterations[i]
        if iteration_index >= model_start_iteration:
            model_number = i + 1
            print(f'commenced training Group_{group_number} Model_{model_number}')
            model     = models[i]
            optimizer = optimizers[i]

            if (iteration_index - model_start_iteration) == 0:
                print(f'first initialised Model_{i + 1} weights')

            # reinitialise weights if scheduled
            if (iteration_index - model_start_iteration) % cfg.new_weights == 0 and (iteration_index - model_start_iteration) != 0:
                print(f're-initialised Model_{i + 1} weights')
                mb.reinitialise_weights(model)

            iteration_date = returns.index[end_idx].strftime('%Y-%m-%d')

            saved_outputs, epoch_metrics, validation_losses, best_weights = mb.DIQ_train_network(
                model, optimizer, train_loader, validation_loader,
                project_type, iteration_date, group_number, model_number,
                prev_weights[i],  # best weights from previous iteration for turnover regularisation
                train_rf_scalar=train_rf_scalar,
                val_rf_scalar=val_rf_scalar,
                asset_names=list(returns.columns)
            )

            # update prev_weights[i] with best weights found in this iteration
            prev_weights[i] = best_weights.clone().detach() if best_weights is not None else prev_weights[i]
            print(f'finished training Group_{group_number} Model_{i + 1}')

    iteration_duration = time.time() - iteration_start_time
    print(f'finished Iteration_{iteration_index + 1} ({end_date})')
    print(f"iteration_{iteration_index + 1} took: {round(iteration_duration)} seconds")
    print()

# save run settings
settings_payload = {
    'Group Number': group_number,
    'hyperparameters': {
        'slice.anchors' : slice_meta['anchors'],
        'slice.assets'  : slice_meta['selected_assets'],
        'deep.csv'      : paths['deep_path'],
        'mvo.csv'       : paths['mvo_path'],
        'USE_GPU'       : cfg.USE_GPU,
        'device'        : str(cfg.device),
        'start-finish'  : cfg.dates,
        'n_strata'      : cfg.n_strata,
        'r'             : cfg.r,
        'm'             : cfg.m,
        'b'             : cfg.b,
        'f'             : cfg.f,
        'stp'           : cfg.stp,
        'dropout_rate'  : cfg.dropout_rate,
        'memory(mnths)' : cfg.m_memory,
        'memory(iters)' : cfg.new_weights,
        'n_groups'      : cfg.n_groups,
        'n_models'      : cfg.n_models,
        'l_delta'       : cfg.l_delta,
        'u_delta'       : cfg.u_delta,
        'u_gamma'       : cfg.u_gamma,
        'l_eps'         : cfg.l_eps,
        'u_eps'         : cfg.u_eps,
        'eps_init'      : cfg.eps_init,
        'noise zone'    : cfg.threshold,
        'center_method' : cfg.center_method,
        'scale_method'  : cfg.scale_method,
        'iq_method'     : cfg.iq_method,
        'iq_method_des' : cfg.iq_method_description,
        'PSD enforced'  : cfg.PSD_hard,
        'pfolio size'   : cfg.n_assets,
        'output_dim_1'  : cfg.output_dim_1,
        'output_dim_2'  : cfg.output_dim_2,
        'target.vol'    : cfg.ann_target_vol,
        'reg.vol'       : cfg.lambda_vol,
        'reg.vol.target': cfg.lambda_vol_target,
        'reg.SR'        : cfg.lambda_sharpe,
        'reg.turnover'  : cfg.lambda_turnover,
        'reg.CN'        : cfg.lambda_cn,
        'reg.entropy'   : cfg.lambda_entropy,
        'reg.r_parity'  : cfg.lambda_rp,
        'reg. max wgt'  : cfg.lambda_tw,
        '1wgt threshold': cfg.max_tw,
        'reg.top-3 wgts': cfg.lambda_t3w,
        '3wgt threshold': cfg.max_t3w,
        'risk-free cfg' : cfg.rf_config,
        'legacy rf'     : cfg.risk_free_rate
    }
}

file_name = "saved_settings/saved_settings.pkl"
try:
    with open(file_name, 'wb') as f1:
        pickle.dump(settings_payload, f1)
    print(f"Saved settings to {file_name}")
except IOError as e:
    print(f"Error saving file: {e}")
