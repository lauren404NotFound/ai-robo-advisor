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
Name    : diq_mvo_performance.py
Contact : drwss.academy@gmail.com
Date    : 11/10/2025
Desc    : Performance of DeepIQ against MVO for MaxSR
"""

import os
import matplotlib.pyplot as plt
import sys
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
CFG_DIR  = os.path.join(BASE_DIR, 'MaxSR')
if CFG_DIR not in sys.path:
    sys.path.insert(0, CFG_DIR)

import MINNlib as mb
import numpy as np
import pandas as pd
import project_hyperparameters as cfg
from diq_mvo import cov_function_list, n_specials  
from scipy.stats import norm, kurtosis

def detect_label() -> str:
    base_dir = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
    if os.path.isdir(os.path.join(base_dir, 'MaxSR')): 
        return 'maxsr'
    raise RuntimeError("Could not detect objective. Create a 'MaxSR' folder next to this script.")

LABEL          = detect_label() 
STRATEGY_LABEL = 'maxSharpe'
prefix         = "OOS_results"

def calculate_annualized_metrics(ret, freq='M'):
    if freq == 'M':
        return 12 * ret.mean(), np.sqrt(12) * ret.std()
    elif freq == 'D':
        return 252 * ret.mean(), np.sqrt(252) * ret.std()
    else:
        raise ValueError("Unsupported frequency. Use 'M' for monthly or 'D' for daily.")

def evaluate_port_performance(filename: str):
    prcs = pd.read_csv(filename, parse_dates=['date']).set_index(['date']).resample("M", label="right").last()
    rets = prcs.pct_change().dropna()

    rf = mb.load_rfr_aligned_to_returns(
        cfg.rf_config['csv_path'], rets.index,
        frequency      =cfg.rf_config.get('frequency','M'),
        column         =cfg.rf_config.get('column', None),
        align_method   =cfg.rf_config.get('align_method','ffill'),
        interpretation =cfg.rf_config.get('interpretation','monthly_effective')
    )

    df_port_performances = pd.DataFrame(index=[
        'Annualized Return (%)',
        'Cumulative Return (%)',
        'Annualized STD (%)',
        'Maximum Drawdown (%)',
        'Monthly 95% VaR (%)',
        'Sharpe Ratio'
    ])

    for port_name in prcs.columns:
        prc = prcs[port_name]
        ret = rets[port_name]

        # metrics
        ann_ret = 12 * ret.mean() # ann_ret = (1 + ret.mean()) ** 12 - 1
        ann_std = np.sqrt(12) * ret.std()

        # cumulative
        cumulative_ret = (1 + ret).prod() - 1

        # VaR and drawdown (basic monthly)
        VaR2     = ret.quantile(0.05)
        rollmax  = (prc.cummax())
        drawdown = prc / rollmax - 1.0
        max_dd   = drawdown.min()

        # Sharpe using monthly excess returns and monthly std of excess returns
        ex_ret = ret - rf
        ex_std = ex_ret.std()
        sharpe = (ex_ret.mean() / ex_std) * np.sqrt(12) if ex_std != 0 else np.nan

        df_port_performances[port_name] = [
            ann_ret * 100,
            cumulative_ret * 100,
            ann_std * 100,
            max_dd * 100,
            VaR2 * 100,
            sharpe
        ]

    return df_port_performances.round(2)

n_cov_function_list = [f"${key}$" for key in cov_function_list]

ports_dict     = {}
turnovers_dict = {}
for k in range(1, n_specials + 1):
    ports_dict.update({f"$DIQ{k}$": f"{prefix}/DIQ_{k}_value.csv"})
    turnovers_dict.update({f"$DIQ{k}$": f"{prefix}/DIQ_{k}_turnover.csv"})

ports_dict.update({k: v.format(prefix=prefix) for k, v in {
    "$HC$"  : "{prefix}/HC_value.csv"  , "$LS1$" : "{prefix}/LS1_value.csv" , "$LS2$" : "{prefix}/LS2_value.csv" ,
    "$LS3$" : "{prefix}/LS3_value.csv" , "$LS4$" : "{prefix}/LS4_value.csv" , "$LS5$" : "{prefix}/LS5_value.csv" ,
    "$NLS6$": "{prefix}/NLS6_value.csv", "$NLS7$" : "{prefix}/NLS7_value.csv", "$NLS8$" : "{prefix}/NLS8_value.csv",
    "$GS1$" : "{prefix}/GS1_value.csv" , "$GS2$" : "{prefix}/GS2_value.csv" , "$GS3$" : "{prefix}/GS3_value.csv" ,
    "$CRE$" : "{prefix}/CRE_value.csv" , "$SRE$" : "{prefix}/SRE_value.csv"
}.items() if k in n_cov_function_list})

turnovers_dict.update({k: v.format(prefix=prefix) for k, v in {
    "$HC$"  : "{prefix}/HC_turnover.csv"  , "$LS1$" : "{prefix}/LS1_turnover.csv" , "$LS2$" : "{prefix}/LS2_turnover.csv" ,
    "$LS3$" : "{prefix}/LS3_turnover.csv" , "$LS4$" : "{prefix}/LS4_turnover.csv" , "$LS5$" : "{prefix}/LS5_turnover.csv" ,
    "$NLS6$": "{prefix}/NLS6_turnover.csv", "$NLS7$" : "{prefix}/NLS7_turnover.csv", "$NLS8$" : "{prefix}/NLS8_turnover.csv",
    "$GS1$" : "{prefix}/GS1_turnover.csv" , "$GS2$" : "{prefix}/GS2_turnover.csv" , "$GS3$" : "{prefix}/GS3_turnover.csv" ,
    "$CRE$" : "{prefix}/CRE_turnover.csv" , "$SRE$" : "{prefix}/SRE_turnover.csv"
}.items() if k in n_cov_function_list})

df_ports_list = []
for key, value in ports_dict.items():
    print(f"Evaluating {key} performance ...")
    df_port_perform = evaluate_port_performance(value)
    df_port_perform.columns = pd.MultiIndex.from_tuples(
        map(lambda x: (x, key), df_port_perform.columns)
    )
    df_ports_list.append(df_port_perform)

for i, (key, value) in enumerate(turnovers_dict.items()):
    df_turnover = pd.read_csv(value, parse_dates=["date"]).set_index("date")
    df_ports_list[i].loc["Turnover"] = [round(val, 2) for val in df_turnover.mean() * 12]

df_port_performance = pd.concat(df_ports_list, axis=1)

ports_columns = [(port, cov) for port in [STRATEGY_LABEL] for cov in ports_dict.keys()]
os.makedirs(prefix, exist_ok=True)

df_port_performance[ports_columns].to_latex(f"./{prefix}/performance.tex")
df_port_performance[ports_columns].to_csv(f"./{prefix}/performance.csv")

print(f"Detected objective: {LABEL} -> strategy '{STRATEGY_LABEL}'. Exports written under ./{prefix}")
