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
Name    : diq_mvo.py
Contact : drwss.academy@gmail.com
Date    : 11/10/2025
Desc    : run DeepIQ against MVO for MaxSR.
"""

import os
import pickle
import re
import sys
import numpy as np
import pandas as pd
from diq_mvo_optimizer import calc_assets_moments
from diq_mvo_optimizer import portfolio_optimizer
from diq_mvo_trans_cost import TransCost
from tqdm import tqdm

BASE_DIR = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
CFG_DIR  = os.path.join(BASE_DIR, 'MaxSR')
if CFG_DIR not in sys.path:
    sys.path.insert(0, CFG_DIR)

import project_hyperparameters as cfg  

def _load_csv_series(csv_path, column=None):
    """load a dated series (index=Date) from CSV and return a sorted numeric Series."""
    df  = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    ser = df.iloc[:, 0] if column is None else df[column]
    ser = pd.to_numeric(ser, errors="coerce").dropna()
    ser.index = pd.to_datetime(ser.index)
    return ser.sort_index().rename("rf")

def _asof_align(series, idx, method="ffill"):
    """as-of align a series to the target DatetimeIndex."""
    union = series.index.union(idx).sort_values()
    s     = series.reindex(union)
    if method == "ffill":
        s = s.ffill()
    elif method == "bfill":
        s = s.bfill()
    return s.reindex(idx).rename(series.name)

def _load_rfr_aligned_to_returns(csv_path, returns_index,
                                 frequency      ="M",
                                 column         =None,
                                 align_method   ="ffill",
                                 interpretation ="monthly_effective"):
    """
    read risk-free rate CSV and align to returns index.
    - interpretation='monthly_effective'  -> values are already monthly returns
    - interpretation='annualized_yield'   -> convert annual yield to monthly effective return
    """
    rf = _load_csv_series(csv_path, column)
    if interpretation == "annualized_yield":
        y   = rf / 100.0
        ppy = 12 if str(frequency).upper().startswith("M") else 252
        rf  = (1.0 + y) ** (1.0 / ppy) - 1.0
    rf_aligned = _asof_align(rf, returns_index, method=align_method)
    return rf_aligned.rename("rf")

def _load_rf_aligned(index):
    """wrapper that uses cfg.rf_config and returns a monthly Series aligned to `index` or None on failure."""
    try:
        rf_cfg = cfg.rf_config
        if not rf_cfg.get('enabled', True):
            return None
        rf = _load_rfr_aligned_to_returns(
            rf_cfg['csv_path'], index,
            frequency      = rf_cfg.get('frequency','M'),
            column         = rf_cfg.get('column', None),
            align_method   = rf_cfg.get('align_method','ffill'),
            interpretation = rf_cfg.get('interpretation','monthly_effective')
        )
        return rf
    except Exception as e:
        print(f"[diq_mvo] WARNING: could not load risk-free from cfg.rf_config; proceeding without RF. ({e})")
        return None

def detect_label() -> str:
    maxsr_dir  = os.path.join(BASE_DIR, 'MaxSR')
    if os.path.isdir(maxsr_dir):
        return 'maxsr'
    raise RuntimeError("Could not detect objective. Create a 'MaxSR' folder next to this script.")

LABEL          = detect_label()      
STRATEGY_LABEL = 'maxSharpe'
SPECIAL_DIR    = os.path.join('portfolios', 'special_portfolios')

def _load_mvo_prices():
    path = os.path.join(cfg.price_dir, cfg.mvo_filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"MVO price slice not found at expected path: {path}\n"
            f"(Ensure MainSR wrote slices to cfg.price_dir and cfg.mvo_filename is set.)"
        )
    df = pd.read_csv(path, parse_dates=['Date'], dayfirst=True).set_index(['Date'])
    if df.empty:
        raise ValueError(f"MVO price slice at {path} is empty.")
    return df, path

def load_special_portfolios(label: str) -> dict:
    """
    read DIQ1..DIQ5 special portfolios from SPECIAL_DIR and intersect columns with MVO symbols
    (so both 9- and 10-asset runs are supported without any change).
    """
    weights = {}
    for k in range(1, 6):
        path = os.path.join(SPECIAL_DIR, f"diq{k}_{label}.csv")
        df   = pd.read_csv(path, parse_dates=['Date'], dayfirst=True).set_index(['Date'])
        keep = [c for c in prcs.columns if c in df.columns]  # keep MVO order
        weights[k] = df[keep]
    return weights

cash_start        = 100000.0
lookback_win_size = int(cfg.m)     # MVO lookback duration = DeepIQ batch duration
optimization_cost = 10             # bps
transaction_cost  = 10             # bps

# instantiate self-financing transaction cost calculator (bps)
tc = TransCost(c=transaction_cost)
prcs, prcs_path = _load_mvo_prices()
print(f"[diq_mvo] Using MVO price file: {prcs_path}")

rets = prcs.pct_change().dropna(axis=0)
prcs = prcs.iloc[1:]  

rf_series   = _load_rf_aligned(rets.index)
rets_excess = rets.sub(rf_series, axis=0) if rf_series is not None else rets

nT, p   = prcs.shape
symbols = prcs.columns.to_list()

weights_sp = load_special_portfolios(LABEL)
n_specials = len(weights_sp)

obj_function_list = [STRATEGY_LABEL]
cov_function_list = [
    "HC", "DIQ", "GS1", "GS2", "GS3",
    "LS1", "LS2", "LS3", "LS4", "LS5",
    "NLS6", "NLS7", "NLS8", "CRE", "SRE"
]

savepath = "OOS_results"
os.makedirs(savepath, exist_ok=True)

account_dict = {}
for cov_function in cov_function_list:
    account_dict[cov_function] = {}
    if cov_function == "DIQ":
        for strategy in [STRATEGY_LABEL]:
            account_dict["DIQ"][strategy] = {k: [] for k in range(1, len(weights_sp) + 1)}
            for k in range(1, len(weights_sp) + 1):
                account_dict["DIQ"][strategy][k].append(
                    {
                        "date"       : prcs.index[lookback_win_size - 1].strftime("%Y-%m-%d"),
                        "weights"    : np.array([0] * p),
                        "shares"     : np.array([0] * p),
                        "values"     : np.array([0] * p),
                        "portReturn" : 0,
                        "transCost"  : 0,
                        "weightDelta": 0,
                        "portValue"  : cash_start
                    }
                )
    else:
        for port_name in obj_function_list:
            account_dict[cov_function][port_name] = []
            account_dict[cov_function][port_name].append(
                {
                    "date"       : prcs.index[lookback_win_size - 1].strftime("%Y-%m-%d"),
                    "weights"    : np.array([0] * p),
                    "shares"     : np.array([0] * p),
                    "values"     : np.array([0] * p),
                    "portReturn" : 0,
                    "transCost"  : 0,
                    "weightDelta": 0,
                    "portValue"  : cash_start
                }
            )

def get_mean_variance_space(
    returns_df: pd.DataFrame,
    obj_function_list: list,
    cov_function: str = "HC",
    freq: str = "monthly",
    prev_port_weights: dict | None = None,
    simulations: int = 0,
    cost: float | None = None,
) -> dict:
    port_opt = portfolio_optimizer(min_weight=0, max_weight=1, cov_function=cov_function, freq=freq)
    port_opt.set_returns(returns_df)
    result_dict = {"port_opt": {}, "asset": {}}
    for obj_fun_str in obj_function_list:
        if prev_port_weights is not None and cost is not None:
            weights = port_opt.optimize(obj_fun_str, prev_weights=prev_port_weights[obj_fun_str]["weights"], cost=cost)
        else:
            weights = port_opt.optimize(obj_fun_str)
        ret, std = port_opt.calc_annualized_portfolio_moments(weights=weights)
        result_dict["port_opt"][obj_fun_str] = {"ret_std": (ret, std), "weights": weights}
    for ticker in returns_df:
        _dat = returns_df[ticker]
        ret, std = calc_assets_moments(_dat, freq=freq)
        result_dict["asset"][ticker] = (ret, std)
    return result_dict

prev_port_weights_dict = {key: None for key in cov_function_list}
for t in tqdm(range(lookback_win_size, nT)):
    bgn_date    = rets.index[t - lookback_win_size]
    end_date    = rets.index[t - 1]
    end_date_p1 = rets.index[t]

    sub_rets        = rets.iloc[t - lookback_win_size : t]
    sub_rets_excess = rets_excess.iloc[t - lookback_win_size : t]

    prcs_t   = prcs.iloc[t - 1 : t].values[0]
    prcs_tp1 = prcs.iloc[t : t + 1].values[0]
    rets_tp1 = rets.iloc[t : t + 1].values[0]

    opt_ports_dict = {}
    for cov_function in cov_function_list:
        if cov_function == "DIQ":
            for k in range(1, len(weights_sp) + 1):
                for strategy, weights_data in [(STRATEGY_LABEL, weights_sp[k])]:
                    if end_date_p1.strftime("%Y-%m-%d") in weights_data.index:
                        deepiq_weights_t = weights_data.loc[end_date_p1.strftime("%Y-%m-%d")].values
                        port_tm1 = account_dict["DIQ"][strategy][k][-1]
                        port_t = {
                            "date"       : end_date_p1.strftime("%Y-%m-%d"),
                            "weights"    : deepiq_weights_t,
                            "shares"     : None,
                            "values"     : None,
                            "portReturn" : None,
                            "transCost"  : None,
                            "weightDelta": None,
                            "portValue"  : None
                        }
                        # self-financing transaction costs (uses diq_mvo_trans_cost.TransCost)
                        # compute portfolio return on weights (unchanged by cost accounting):
                        port_t["portReturn"] = (port_t["weights"] * rets_tp1).sum()

                        # drag is the fraction of pre-cost wealth lost to trading costs.
                        old_w = dict(zip(symbols, port_tm1["weights"]))
                        new_w = dict(zip(symbols, port_t["weights"]))
                        drag  = tc.get_cost(new_weights=new_w, old_weights=old_w)
                        port_t["transCost"] = port_tm1["portValue"] * float(drag)

                        # rebalance after paying costs so target weights are met on the post-cost base.
                        V_after_cost = port_tm1["portValue"] - port_t["transCost"]
                        port_t["shares"] = V_after_cost * port_t["weights"] / prcs_t
                        port_t["values"] = V_after_cost * port_t["weights"]
                        port_t["weightDelta"] = np.sum(np.abs(port_t["weights"] - port_tm1["weights"]))

                        # apply market returns to the post-cost base.
                        port_t["portValue"] = V_after_cost * (1 + port_t["portReturn"])
                        account_dict["DIQ"][strategy][k].append(port_t)

        else:
            # optimise on excess returns
            opt_ports_dict[cov_function] = get_mean_variance_space(
                sub_rets_excess, obj_function_list,
                cov_function,
                prev_port_weights=prev_port_weights_dict[cov_function],
                cost=optimization_cost,
            )
            prev_port_weights_dict[cov_function] = opt_ports_dict[cov_function]["port_opt"]

            for port_name in obj_function_list:
                port_tm1 = account_dict[cov_function][port_name][-1]

                port_t = {
                    "date": end_date_p1.strftime("%Y-%m-%d"),
                    "weights"    : opt_ports_dict[cov_function]["port_opt"][port_name]["weights"],
                    "shares"     : None,
                    "values"     : None,
                    "portReturn" : None,
                    "transCost"  : None,
                    "weightDelta": None,
                    "portValue"  : None,
                }

                # self-financing transaction costs (uses diq_mvo_trans_cost.TransCost)
                # compute portfolio return on weights (unchanged by cost accounting):
                port_t["portReturn"] = (port_t["weights"] * rets_tp1).sum()
                
                # drag is the fraction of pre-cost wealth lost to trading costs.
                old_w = dict(zip(symbols, port_tm1["weights"]))
                new_w = dict(zip(symbols, port_t["weights"]))
                drag  = tc.get_cost(new_weights=new_w, old_weights=old_w)  
                port_t["transCost"] = port_tm1["portValue"] * float(drag)
                
                # rebalance after paying costs so target weights are met on the post-cost base.
                V_after_cost     = port_tm1["portValue"] - port_t["transCost"]
                port_t["shares"] = V_after_cost * port_t["weights"] / prcs_t
                port_t["values"] = V_after_cost * port_t["weights"]
                port_t["weightDelta"] = np.sum(np.abs(port_t["weights"] - port_tm1["weights"]))
                
                # apply market returns to the post-cost base.
                port_t["portValue"] = V_after_cost * (1 + port_t["portReturn"])
                account_dict[cov_function][port_name].append(port_t)

with open(f"{savepath}/result.pickle", "wb") as f:
    pickle.dump(account_dict, f)

for cov_func in cov_function_list:
    for k in range(1, len(weights_sp) + 1) if cov_func == "DIQ" else [None]:
        suffix = f"_{k}" if k else ""
        portAccountDF = pd.DataFrame.from_dict(
            {
                (port_name, account["date"]): {
                    "value"   : account["portValue"],
                    "return"  : account["portReturn"],
                    "trans"   : account["transCost"],
                    "turnover": account["weightDelta"]
                }
                for port_name in account_dict[cov_func].keys()
                for account in (
                    account_dict[cov_func][port_name][k]
                    if k
                    else account_dict[cov_func][port_name]
                )
            },
            orient="index",
        )

        portAccountDF.reset_index(inplace=True)
        portAccountDF.columns = ["port", "date", "value", "return", "trans", "turnover"]
        portAccountDF.pivot(index="date", columns="port", values="value").to_csv(
            f"{savepath}/{cov_func}{suffix}_value.csv"
        )
        portAccountDF.pivot(index="date", columns="port", values="return").to_csv(
            f"{savepath}/{cov_func}{suffix}_return.csv"
        )
        portAccountDF.pivot(index="date", columns="port", values="trans").to_csv(
            f"{savepath}/{cov_func}{suffix}_trans.csv"
        )
        portAccountDF.pivot(index="date", columns="port", values="turnover").to_csv(
            f"{savepath}/{cov_func}{suffix}_turnover.csv"
        )

print(f"Detected objective: {LABEL} -> strategy '{STRATEGY_LABEL}'.")
print("Run complete. Outputs saved under:", savepath)
