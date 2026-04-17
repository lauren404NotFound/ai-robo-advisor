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
Name     : dynamic_special_weights.py 
Contact  : drwss.academy@gmail.com
Date     : 11/10/2025
Desc     : produce stacked area charts of special portfolio compositions over time
           and summary tables of weights (mean±SD and median±semi-IQR) for MaxSR.
"""
import os
import glob
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

SPECIAL_DIR = os.path.join("portfolios", "special_portfolios")
OUT_DIR     = os.path.join(SPECIAL_DIR, "dynamic_weights")
BASE_DIR    = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
CFG_DIR     = os.path.join(BASE_DIR, 'MaxSR')
if CFG_DIR not in sys.path:
    sys.path.insert(0, CFG_DIR)
def _try_import_cfg():
    try:
        import project_hyperparameters as cfg
        return cfg
    except Exception:
        return None

CFG = _try_import_cfg()

def _candidate_mvo_paths():
    if CFG is not None:
        try:
            yield os.path.join(CFG.price_dir, CFG.mvo_filename)
        except Exception:
            pass

def _load_mvo_index_and_tickers():

    for path in _candidate_mvo_paths():
        try:
            if os.path.exists(path):
                df = pd.read_csv(path, parse_dates=['Date'], dayfirst=True)
                if 'Date' in df.columns and len(df) > 0:
                    idx = pd.to_datetime(df['Date'])
                    tickers = [c for c in df.columns if c != 'Date']
                    return idx, tickers, path
        except Exception:
            continue
    return None, None, None

MVO_INDEX, MVO_TICKERS, MVO_PATH = _load_mvo_index_and_tickers()

def detect_label() -> str:
    """detect 'maxsr' via sibling folder or filenames in SPECIAL_DIR."""
    base_dir = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
    if os.path.isdir(os.path.join(base_dir, "MaxSR")):
        return "maxsr"
    raise RuntimeError("Could not detect objective. Create 'MaxSR' folder next to this script.")

def ensure_out_dir() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

def _infer_ticker_columns(df: pd.DataFrame) -> list[str]:
    """infer ticker columns by excluding known metadata and keeping numeric columns."""
    meta = {
        'date', 'Date', 'row_exists', 'memory', 'partition_memory',
        'validation_loss', 'delta', 'eta', 'gamma',
        'alpha1', 'alpha2', 'alpha3',
        'iq_method', 'best_epoch', 'best_epochj', 'epsilon', 'wB', 'wW', 'wT', 'wI',
        'cn_CIQ', 'ann_port_vol_val', 'source_file'
    }
    candidate_cols = [c for c in df.columns if c not in meta]
    num_cols = []
    for c in candidate_cols:
        try:
            pd.to_numeric(df[c], errors='raise')
            num_cols.append(c)
        except Exception:
            continue
    if MVO_TICKERS:
        return [c for c in MVO_TICKERS if c in num_cols]
    return num_cols

def load_special_csv(k: int, label: str) -> pd.DataFrame:
    """load diq{k}_{label}.csv, set Date as index if present, and retain inferred ticker columns."""
    path = os.path.join(SPECIAL_DIR, f"diq{k}_{label}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing: {path}")
    try:
        df = pd.read_csv(path, parse_dates=['Date'], dayfirst=True)
        if 'Date' in df.columns:
            df = df.set_index('Date')
    except Exception:
        df = pd.read_csv(path)
        if 'Date' in df.columns:
            df = df.set_index('Date')
    inferred = _infer_ticker_columns(df)
    if not inferred:
        raise ValueError(f"No asset columns inferred in {path}. Found columns: {list(df.columns)}")
    df = df[inferred].apply(pd.to_numeric, errors='coerce')
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.sort_index()
    return df

def normalize_rows(df: pd.DataFrame) -> pd.DataFrame:
    sums = df.sum(axis=1).replace(0, np.nan)
    norm = df.div(sums, axis=0)
    return norm.fillna(0.0)

def nice_colors(n: int):
    import matplotlib
    base = plt.get_cmap("tab10")
    colors = [base(i % 10) for i in range(n)]
    if n > 10:
        extra = plt.get_cmap("tab20").colors
        i = 0
        while len(colors) < n and i < len(extra):
            colors.append(extra[i]); i += 1
    return colors[:n]

def plot_stacked_area(weights: pd.DataFrame, title: str, out_png: str) -> None:
    colors = nice_colors(len(weights.columns))
    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(weights.index))
    y = [weights[c].values for c in weights.columns]
    ax.stackplot(x, y, labels=weights.columns, colors=colors, linewidth=0.5)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Portfolio weight")
    ax.set_title(title)
    if isinstance(weights.index, pd.DatetimeIndex):
        if len(weights.index) <= 24:
            ax.set_xticks(x)
            ax.set_xticklabels([d.strftime("%Y-%m") for d in weights.index], rotation=45, ha="right")
        else:
            step = max(1, len(weights.index)//12)
            idxs = list(range(0, len(weights.index), step))
            ax.set_xticks(idxs)
            ax.set_xticklabels([weights.index[i].strftime("%Y-%m") for i in idxs], rotation=45, ha="right")
    else:
        if len(x) <= 24:
            ax.set_xticks(x)
        else:
            step = max(1, len(x)//12)
            ax.set_xticks(range(0, len(x), step))
        ax.set_xlabel("Iteration")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v:.0%}"))
    ax.legend(loc='upper center', ncol=min(5, len(weights.columns)), frameon=False, bbox_to_anchor=(0.5, -0.1))
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)

def make_summary_tables(weights_map: dict[int, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """build two tables over time for each special portfolio k."""
    mean_sd_rows = {}
    med_siqr_rows = {}

    for k, df in weights_map.items():
        dfn = normalize_rows(df)
        means = dfn.mean(axis=0)
        sds   = dfn.std(axis=0, ddof=1)
        q1    = dfn.quantile(0.25, axis=0); q3 = dfn.quantile(0.75, axis=0)
        med   = dfn.median(axis=0)
        siqr  = (q3 - q1) / 2.0
        mean_sd_rows[f"DIQ{k}"] = {c: f"{means[c]:.4f} ± {sds[c]:.4f}" for c in dfn.columns}
        med_siqr_rows[f"DIQ{k}"] = {c: f"{med[c]:.4f} ± {siqr[c]:.4f}" for c in dfn.columns}

    mean_sd_df  = pd.DataFrame.from_dict(mean_sd_rows, orient='index').reindex(sorted(mean_sd_rows.keys()))
    med_siqr_df = pd.DataFrame.from_dict(med_siqr_rows, orient='index').reindex(sorted(med_siqr_rows.keys()))

    # establish canonical column order
    if MVO_TICKERS:
        cols = [c for c in MVO_TICKERS if any(c in df.columns for df in weights_map.values())]
    else:
        # union in order of appearance across DIQs
        seen = []
        for _, df in weights_map.items():
            for c in df.columns:
                if c not in seen:
                    seen.append(c)
        cols = seen

    mean_sd_df  = mean_sd_df.reindex(columns=cols)
    med_siqr_df = med_siqr_df.reindex(columns=cols)
    return mean_sd_df, med_siqr_df

def main():
    label = detect_label()
    ensure_out_dir()
    if MVO_PATH:
        print(f"[dynamic_special_weights] Using MVO prices: {MVO_PATH}")
        print(f"[dynamic_special_weights] Detected universe ({len(MVO_TICKERS) if MVO_TICKERS else 0}): {', '.join(MVO_TICKERS) if MVO_TICKERS else 'N/A'}")

    weights_map = {}
    for k in range(1, 6):
        df = load_special_csv(k, label)
        dfn = normalize_rows(df)
        weights_map[k] = dfn

        title = f"DIQ{k} ({'MaxSR'}) — Dynamic Weights"
        out_png = os.path.join(OUT_DIR, f"diq{k}_{label}_stacked.png")
        plot_stacked_area(dfn, title, out_png)

        out_csv = os.path.join(OUT_DIR, f"diq{k}_{label}_normalized.csv")
        dfn.to_csv(out_csv, index=True)

    mean_sd_df, med_siqr_df = make_summary_tables(weights_map)
    mean_sd_df.to_csv(os.path.join(OUT_DIR, f"summary_mean_sd_{label}.csv"))
    med_siqr_df.to_csv(os.path.join(OUT_DIR, f"summary_median_semiIQR_{label}.csv"))

    print(f"Detected label: {label}")
    print(f"Outputs written to: {OUT_DIR}")

if __name__ == "__main__":
    main()
