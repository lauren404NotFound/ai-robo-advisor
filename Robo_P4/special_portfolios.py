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
Name     : special_portfolios.py (clean, explicit-path version)
Contact  : drwss.academy@gmail.com
Date     : 11/10/2025
Desc     : Derive DIQ special portfolios (DIQ1..5) aligned to the *invest/deploy* month
           required by the MVO phase, using the fixed project structure.
"""

import glob
import os
import re
import shutil
import sys
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

# import project config from ./MaxSR
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
CFG_DIR  = os.path.join(BASE_DIR, 'MaxSR')
if CFG_DIR not in sys.path:
    sys.path.insert(0, CFG_DIR)

import project_hyperparameters as cfg  

PORTFOLIOS_DIR       = os.path.join(BASE_DIR, 'portfolios')
SPECIAL_DIR          = os.path.join(PORTFOLIOS_DIR, 'special_portfolios')
PROCESSED_MODELS_DIR = os.path.join(PORTFOLIOS_DIR, 'store_processed_models')

os.makedirs(PORTFOLIOS_DIR, exist_ok=True)
os.makedirs(SPECIAL_DIR, exist_ok=True)

# canonical MVO prices and tickers (defines 9 vs 10 asset universe)
def load_mvo_prices_from_cfg():
    mvo_path = os.path.join(cfg.price_dir, cfg.mvo_filename)
    if not os.path.exists(mvo_path):
        raise FileNotFoundError(f"MVO price slice not found at: {mvo_path}. "
                                "Run MaxSR/MainSR.py first to produce the slices.")
    df = pd.read_csv(mvo_path, parse_dates=['Date'], dayfirst=True)
    if 'Date' not in df.columns or df.empty:
        raise ValueError(f"Malformed or empty MVO price file: {mvo_path}")
    df = df.set_index('Date')
    tickers = [c for c in df.columns if c != 'Date']
    if len(tickers) < 9 or len(tickers) > 10:
        raise ValueError(f"Unexpected number of asset columns in {mvo_path} (found {len(tickers)}).")
    return df.index, tickers, mvo_path

INVEST_SHIFT_MONTHS = int(cfg.m) + 1  # deploy one month after the m-month validation

# utilities
def detect_label() -> str:
    """return 'maxsr' if ./MaxSR exists."""
    if os.path.isdir(os.path.join(BASE_DIR, 'MaxSR')):
        return 'maxsr'
    raise RuntimeError("Could not detect objective. Create a 'MaxSR' folder next to this script.")

def parse_date_series(s: pd.Series) -> pd.Series:
    """robust parser for 'YYYY-MM-DD' or 'DD/MM/YYYY' strings."""
    return pd.to_datetime(s, dayfirst=True, errors='coerce')

def align_dates_to_mvo(df: pd.DataFrame, tickers: list[str], invest_index: pd.DatetimeIndex, date_col: str = 'Date') -> pd.DataFrame:
    """
    map training-end 'Date' to the invest month by:
      1) adding INVEST_SHIFT_MONTHS months, then
      2) snapping to the exact month present in MVO prices (using month-period map).
    """
    if date_col not in df.columns:
        raise ValueError(f"'{date_col}' not found in columns: {df.columns.tolist()}")

    out = df.copy()
    out[date_col] = parse_date_series(out[date_col])

    # keep only intersection with the MVO asset universe, in the same order
    keep = [c for c in tickers if c in out.columns]
    out = out[[date_col] + keep]
    if not keep:
        raise ValueError("No asset columns found to align (intersection with MVO tickers is empty).")

    # step 1: shift
    shifted = out[date_col] + pd.DateOffset(months=INVEST_SHIFT_MONTHS)

    # step 2: snap to MVO month index
    month_map = {}
    for ts in invest_index:
        month_map[ts.to_period('M')] = ts 

    mapped = shifted.apply(lambda d: month_map.get(d.to_period('M')) if pd.notna(d) else pd.NaT)
    out[date_col] = mapped
    before = len(out)
    out = out.dropna(subset=[date_col])
    dropped = before - len(out)
    print(f"[special_portfolios] Date mapping: +{INVEST_SHIFT_MONTHS}M and snapped to MVO index. Dropped {dropped} row(s).")

    out.sort_values(by=[date_col], inplace=True)
    out = out[~out[date_col].duplicated(keep='last')]
    wsum = out[keep].sum(axis=1).replace(0, np.nan)
    out.loc[:, keep] = out[keep].div(wsum, axis=0)

    return out

def write_csv_iso(df: pd.DataFrame, path: str):
    df_to_write = df.copy()
    if 'Date' in df_to_write.columns:
        df_to_write['Date'] = pd.to_datetime(df_to_write['Date']).dt.strftime('%Y-%m-%d')
    df_to_write.to_csv(path, index=False)
    print(f"Saved: {path} ({len(df_to_write)} rows)")

# Step 1: build aligned Model_* files from raw per-model CSVs
def find_raw_files_for_label(label: str) -> list[str]:
    """list raw per-model CSVs in ./portfolios that contain 'label' in filename (e.g., 'maxsr')."""
    csv_files = [f for f in os.listdir(PORTFOLIOS_DIR) if f.lower().endswith('.csv')]
    return [f for f in csv_files if label in f.lower()]

def prepare_models_from_raw(files: list[str], label: str, tickers: list[str]):
    if not files:
        print(f"No raw CSVs with label '{label}' found in '{PORTFOLIOS_DIR}'. Skipping Step 1.")
        return

    # group files by (G#, M#)
    file_groups: dict[str, list[tuple[int, str]]] = {}
    pattern = r"(G\d+)_M(\d+)"
    for file in files:
        m = re.search(pattern, file)
        if not m:
            continue
        group     = m.group(1)           # e.g., G1
        model_num = int(m.group(2))      # e.g., 1
        file_groups.setdefault(group, []).append((model_num, file))

    if not file_groups:
        print("No files matching '(G#)_M#'. Skipping Step 1.")
        return

    for g in list(file_groups.keys()):
        file_groups[g] = sorted(file_groups[g], key=lambda x: x[0])

    all_files_sorted = [fname for g in sorted(file_groups) for _, fname in file_groups[g]]
    reference_path   = os.path.join(PORTFOLIOS_DIR, all_files_sorted[0])
    df_ref = pd.read_csv(reference_path)
    if 'Date' not in df_ref.columns:
        raise ValueError(f"Reference file {reference_path} lacks a 'Date' column.")
    reference_dates = parse_date_series(df_ref['Date']).drop_duplicates().sort_values().reset_index(drop=True)

    current_model_num      = 1
    current_rows_remaining = len(reference_dates)

    for _, group_files in sorted(file_groups.items()):
        for _, file in group_files:
            df = pd.read_csv(os.path.join(PORTFOLIOS_DIR, file))
            if 'Date' not in df.columns:
                continue
            df['Date'] = parse_date_series(df['Date'])
            df.set_index('Date', inplace=True)

            # keep only relevant tickers (supports 9 or 10)
            keep_cols = [t for t in tickers if t in df.columns]
            df = df[keep_cols]

            df = df.iloc[:current_rows_remaining]
            reindexed = df.reindex(reference_dates)
            reindexed.fillna(0, inplace=True)

            # row_exists flag
            reindexed['row_exists'] = (reindexed.index.isin(df.index)).astype(int)

            # rolling memory up to 24, reset on gaps (assumes 24 models)
            memory = []
            mem = 0
            for exists in reindexed['row_exists']:
                if exists == 1:
                    mem += 1
                    if mem > 24:
                        mem = 1
                    memory.append(mem)
                else:
                    memory.append(0)
            reindexed['memory'] = memory

            reindexed.reset_index(inplace=True)
            out_path = os.path.join(PORTFOLIOS_DIR, f'Model_{current_model_num}_{label}.csv')
            reindexed.to_csv(out_path, index=False)
            print(f"Saved {out_path} with {len(reindexed)} rows (source: {file})")

            current_model_num      += 1
            current_rows_remaining -= 1

    print(f"All files for {label} have been processed and reindexed. (Step 1)")

# Step 2: DIQ4/5 young vs old clusters (long/short memory partition)
def diq45_long_short_clusters(label: str, tickers: list[str], invest_index: pd.DatetimeIndex):
    model_paths = sorted(
        glob.glob(os.path.join(PORTFOLIOS_DIR, f'Model_*_{label}.csv')),
        key=lambda p: int(re.search(r'Model_(\d+)_', os.path.basename(p)).group(1))
    )
    if not model_paths:
        print("No Model_* files found for DIQ4/5. Skipping Step 2.")
        return

    models = [pd.read_csv(p) for p in model_paths]

    start_row = 0
    young_results = []
    old_results   = []

    for date_idx in range(start_row, len(models[0])):
        # collect live weights for this date_idx
        if date_idx < 23:
            live = []
            for mdf in models:
                if date_idx < len(mdf) and mdf.iloc[date_idx].get('row_exists', 0) == 1:
                    live.append(mdf.iloc[date_idx][tickers].to_numpy())
            if live:
                centroid = np.mean(live, axis=0)
                s = np.sum(centroid)
                if s != 0:
                    centroid = centroid / s
                dt = models[0].iloc[date_idx]['Date']
                young_results.append({'Date': dt, **{tickers[i]: centroid[i] for i in range(len(tickers))}, 'partition_memory': None})
                old_results.append(  {'Date': dt, **{tickers[i]: centroid[i] for i in range(len(tickers))}, 'partition_memory': None})
            continue

        usable = []
        for i, mdf in enumerate(models):
            row = mdf.iloc[date_idx]
            if row.get('row_exists', 0) == 1 and row.get('memory', 0) > 0:
                usable.append({
                    'model_index'    : i + 1,
                    'memory'         : row['memory'],
                    'weights'        : row[tickers].to_numpy(),
                    'validation_loss': row.get('validation_loss', np.nan)
                })
        if len(usable) < 3:
            continue

        memories = np.array([u['memory'] for u in usable])
        weights  = np.array([u['weights'] for u in usable])

        best_distance = -np.inf
        best_pm       = None
        best_y        = None
        best_o        = None

        for pm in range(4, len(usable) + 1):
            y_mask = memories < pm
            o_mask = memories >= pm
            if y_mask.sum() >= 3 and o_mask.sum() >= 3:
                y_w = weights[y_mask]
                o_w = weights[o_mask]
                y_c = y_w.mean(axis=0)
                o_c = o_w.mean(axis=0)
                y_c /= np.sum(y_c) if np.sum(y_c) != 0 else 1
                o_c /= np.sum(o_c) if np.sum(o_c) != 0 else 1
                dist = np.linalg.norm(y_c - o_c)
                if dist > best_distance:
                    best_distance, best_pm, best_y, best_o = dist, pm, y_c, o_c

        if best_y is None:
            continue

        dt = models[0].iloc[date_idx]['Date']
        young_results.append({'Date': dt, **{tickers[i]: best_y[i] for i in range(len(tickers))}, 'partition_memory': best_pm})
        old_results.append(  {'Date': dt, **{tickers[i]: best_o[i] for i in range(len(tickers))}, 'partition_memory': best_pm})

    df_young = pd.DataFrame(young_results)
    df_old   = pd.DataFrame(old_results)

    # align to invest dates (shift + snap to MVO)
    df_young = align_dates_to_mvo(df_young, tickers, invest_index, date_col='Date')
    df_old   = align_dates_to_mvo(df_old,   tickers, invest_index, date_col='Date')

    write_csv_iso(df_young, os.path.join(SPECIAL_DIR, f'diq4_{label}.csv'))
    write_csv_iso(df_old,   os.path.join(SPECIAL_DIR, f'diq5_{label}.csv'))
    print(f"Finished DIQ 4/5 for {label}. Saved to {SPECIAL_DIR}. (Step 2)")

# housekeeping: move Model_* out of the way
def move_model_intermediates():
    os.makedirs(PROCESSED_MODELS_DIR, exist_ok=True)
    moved = 0
    for fname in os.listdir(PORTFOLIOS_DIR):
        if fname.startswith('Model_') and fname.endswith('.csv'):
            shutil.move(os.path.join(PORTFOLIOS_DIR, fname), os.path.join(PROCESSED_MODELS_DIR, fname))
            moved += 1
    if moved:
        print(f"Moved {moved} Model_* CSVs to {PROCESSED_MODELS_DIR}. (Post Step 2)")

# Step 3: DIQ2 winner-takes-all
def diq2_winner_takes_all(label: str, tickers: list[str], invest_index: pd.DatetimeIndex):
    file_paths = glob.glob(os.path.join(PORTFOLIOS_DIR, '*.csv'))
    file_paths = [
        p for p in file_paths
        if label in os.path.basename(p).lower()
        and not os.path.basename(p).startswith('Model_')
    ]
    if not file_paths:
        raise ValueError(f"No CSV files for '{label}' found in '{PORTFOLIOS_DIR}' for DIQ2.")

    dataframes = {
        os.path.basename(p): pd.read_csv(p, parse_dates=['Date'], dayfirst=True)
        for p in file_paths
    }
    # master list of training-end dates
    longest = max(dataframes.values(), key=lambda df: len(df.index))
    dates   = pd.to_datetime(longest['Date'], dayfirst=True)

    final_df = pd.DataFrame()
    for dt in dates:
        avail = []
        for fn, df in dataframes.items():
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
            mask = df['Date'] == dt
            if mask.any():
                row = df.loc[mask].iloc[0]
                w_row = row[[t for t in tickers if t in row.index]]
                v = row.get('validation_loss', np.nan)
                avail.append((fn, w_row, v))
        if not avail:
            continue

        temp = pd.DataFrame([row for _, row, _ in avail], index=[fn for fn, _, _ in avail])
        losses = np.array([v for _, _, v in avail], dtype=float)
        if np.isnan(losses).all():
            chosen = temp.iloc[0].copy()
            chosen_name = temp.index[0]
        else:
            losses = np.where(np.isnan(losses), np.nanmax(losses) if not np.isnan(losses).all() else 1.0, losses)
            chosen_name = temp.index[np.argmin(losses)]
            chosen = temp.loc[chosen_name].copy()

        chosen = chosen.to_frame().T
        chosen.insert(0, 'Date', pd.Timestamp(dt))
        chosen['source_file'] = chosen_name

        keep_cols = ['Date'] + tickers + ['source_file']
        existing_keep = [c for c in keep_cols if c in chosen.columns]
        chosen = chosen[existing_keep]

        final_df = pd.concat([final_df, chosen], ignore_index=True)

    # align to invest dates
    final_df = align_dates_to_mvo(final_df, tickers, invest_index, date_col='Date')

    out = os.path.join(SPECIAL_DIR, f'diq2_{label}.csv')
    write_csv_iso(final_df, out)
    print(f"DIQ2 (winner-takes-all) for {label} saved to: {out}. (Step 3)")

# Step 4: DIQ3 inverse-square-loss weighted
def diq3_inverse_square_weighted(label: str, tickers: list[str], invest_index: pd.DatetimeIndex):
    file_paths = glob.glob(os.path.join(PORTFOLIOS_DIR, '*.csv'))
    file_paths = [p for p in file_paths if label in os.path.basename(p).lower() and not os.path.basename(p).startswith('Model_')]
    if not file_paths:
        raise ValueError(f"No CSV files for '{label}' found in '{PORTFOLIOS_DIR}' for DIQ3.")

    dfs = {os.path.basename(p): pd.read_csv(p, parse_dates=['Date'], dayfirst=True) for p in file_paths}
    master = max(dfs.values(), key=lambda df: len(df))
    master_dates = pd.to_datetime(master['Date'], dayfirst=True)

    rows = []
    for dt in master_dates:
        avail = []
        for fn, df in dfs.items():
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
            mask = df['Date'] == dt
            if mask.any():
                row = df.loc[mask].iloc[0]
                w_row = row[[t for t in tickers if t in row.index]]
                v = row.get('validation_loss', np.nan)
                avail.append((fn, w_row, v))
        if not avail:
            continue
        W = np.array([a[1].values for a in avail])
        losses = np.array([a[2] for a in avail], dtype=float)
        if np.isnan(losses).all():
            w_mean = W.mean(axis=0)
        else:
            losses = np.where(np.isnan(losses), np.nanmax(losses) if not np.isnan(losses).all() else 1.0, losses)
            inv2 = 1.0 / (losses ** 2)
            inv2 = inv2 / inv2.sum() if inv2.sum() != 0 else np.ones_like(inv2) / len(inv2)
            w_mean = (W * inv2[:, None]).sum(axis=0)
        s = w_mean.sum()
        w_mean = w_mean / s if s != 0 else w_mean
        rows.append([dt] + list(w_mean))

    out_df = pd.DataFrame(rows, columns=['Date'] + tickers)
    out_df['Date'] = pd.to_datetime(out_df['Date'], dayfirst=True)

    # align to invest dates
    out_df = align_dates_to_mvo(out_df, tickers, invest_index, date_col='Date')

    out = os.path.join(SPECIAL_DIR, f'diq3_{label}.csv')
    write_csv_iso(out_df, out)
    print(f"DIQ3 (inverse-square loss weighted) for {label} saved to: {out}. (Step 4)")

# Step 5: DIQ1 equal-weight mean
def diq1_equal_weighted(label: str, tickers: list[str], invest_index: pd.DatetimeIndex):
    file_paths = glob.glob(os.path.join(PORTFOLIOS_DIR, '*.csv'))
    file_paths = [p for p in file_paths if label in os.path.basename(p).lower() and not os.path.basename(p).startswith('Model_')]
    if not file_paths:
        raise ValueError(f"No CSV files for '{label}' found in '{PORTFOLIOS_DIR}' for DIQ1.")

    dfs = {os.path.basename(p): pd.read_csv(p, parse_dates=['Date'], dayfirst=True) for p in file_paths}
    master = max(dfs.values(), key=lambda df: len(df))
    master_dates = pd.to_datetime(master['Date'], dayfirst=True)

    rows = []
    for dt in master_dates:
        avail = []
        for _, df in dfs.items():
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
            mask = df['Date'] == dt
            if mask.any():
                avail.append(df.loc[mask, tickers].iloc[0].values)
        if not avail:
            continue
        mean_w = np.mean(np.array(avail), axis=0)
        s = mean_w.sum()
        mean_w = mean_w / s if s != 0 else mean_w
        rows.append([dt] + list(mean_w))

    out_df = pd.DataFrame(rows, columns=['Date'] + tickers)
    out_df['Date'] = pd.to_datetime(out_df['Date'], dayfirst=True)

    # align to invest dates
    out_df = align_dates_to_mvo(out_df, tickers, invest_index, date_col='Date')

    out = os.path.join(SPECIAL_DIR, f'diq1_{label}.csv')
    write_csv_iso(out_df, out)
    print(f"DIQ1 (equal-weight mean) for {label} saved to: {out}. (Step 5)")

def main():
    label = detect_label()  
    invest_index, mvo_tickers, mvo_path = load_mvo_prices_from_cfg()
    print(f"Detected objective: {label}")
    print(f"Using MVO prices: {mvo_path}")
    print(f"Asset universe ({len(mvo_tickers)}): {', '.join(mvo_tickers)}")
    print(f"INVEST_SHIFT_MONTHS = {INVEST_SHIFT_MONTHS} (cfg.m={cfg.m} + 1)")

    # Step 1: build aligned Model_* files from raw inputs
    raw_files = find_raw_files_for_label(label)
    if not raw_files:
        print(f"No raw CSVs for '{label}' found under {PORTFOLIOS_DIR}. "
              f"Expected files like shdiq_wgts_{label}_G#_M#.csv")
    else:
        print(f"Found {len(raw_files)} raw CSV(s) for '{label}'.")
    prepare_models_from_raw(raw_files, label, mvo_tickers)

    print("\nStep 1 complete.\n")

    # Step 2: DIQ4/5 from Model_* files (then re-key to invest month)
    diq45_long_short_clusters(label, mvo_tickers, invest_index)

    # move temporary Model_* files out of the way
    move_model_intermediates()

    print("\nStep 2 complete.\n")

    # Steps 3–5 use raw per-model files, then align to invest month
    diq2_winner_takes_all(label, mvo_tickers, invest_index)
    print("\nStep 3 complete.\n")

    diq3_inverse_square_weighted(label, mvo_tickers, invest_index)
    print("\nStep 4 complete.\n")

    diq1_equal_weighted(label, mvo_tickers, invest_index)
    print("\nAll steps complete.\n")

if __name__ == "__main__":
    main()
