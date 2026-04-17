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
Name    : diq_hyperparameters.py
Contact : drwss.academy@gmail.com
Date    : 11/10/25
Desc    : aggregate & visualise DeepIQ hyperparameters for MaxSR.

- aggregates per-model CSVs in ./portfolios into a mean time series per parameter.
- plots grouped time series (delta; eta, gamma, epsilon, etc.) from the aggregated 
- mean, and median, and plots middle percentile bands (default 45–55%) across 
- models per iteration/date from the raw per-model files.
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def detect_label() -> str:
    
    base_dir = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
    if os.path.isdir(os.path.join(base_dir, 'MaxSR')):  
        return 'maxsr'
    raise RuntimeError(
        "Could not detect objective. Create a 'MaxSR' folder next to this script."
    )

LABEL         = detect_label()         
LABEL_UP      = 'MaxSR'
MODEL_KEYWORD = LABEL                             

HP_DIR = os.path.join('portfolios', 'hyperparameters')
os.makedirs(HP_DIR, exist_ok=True)



def aggregate_model_outputs(file_pattern: str, output_file: str, columns_to_aggregate: list[str]) -> None:
    """
    read all per-model CSVs that match pattern and compute the mean time 
    series for the requested columns. Saves a single aggregated CSV. 
    assumes first column in each file is the index (date/iteration).
    """
    files = glob.glob(file_pattern)
    if not files:
        print(f"No files found matching: {file_pattern}")
        return

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, index_col=0)
        except Exception as e:
            print(f"Skipping unreadable file {f}: {e}")
            continue
        selected = [c for c in columns_to_aggregate if c in df.columns]
        if not selected:
            print(f"File {f} has none of the required columns: {columns_to_aggregate}")
            continue
        dfs.append(df.loc[:, selected])

    if not dfs:
        print("No usable dataframes to aggregate. Exiting.")
        return

    stacked = pd.concat(dfs, axis=1, keys=range(len(dfs)))  # columns MultiIndex: (model_id, param)
    mean_df = stacked.T.groupby(level=1).mean().T           # mean across models, per param

    mean_df = mean_df[[c for c in columns_to_aggregate if c in mean_df.columns]]

    mean_df.to_csv(output_file)
    print(f"Aggregated results saved to {output_file}")

columns_to_aggregate = ['validation_loss', 'delta', 'gamma', 'epsilon', 'wB', 'wW', 'wT', 'wI']

aggregate_model_outputs(
    file_pattern=os.path.join('portfolios', f'*{MODEL_KEYWORD}*.csv'),
    output_file=os.path.join(HP_DIR, f'aggregate_{LABEL}.csv'),
    columns_to_aggregate=columns_to_aggregate
)

def plot_aggregated_metrics_grouped(csv_file: str, title_prefix: str = '', save_path: str | None = None) -> None:
    
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)

    top_cols      = ['delta']
    top_labels    = [r'$\delta$']  
    bottom_cols   = ['gamma', 'wB', 'wW', 'wT', 'wI']
    bottom_labels = [r'$\gamma$', r'$w_{B}$', r'$w_{W}$', r'$w_{T}$',r'$w_{I}$']
    all_labels    = top_labels + bottom_labels

    colour_cycle  = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown']

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 2]})
    lines = []

    # top row: delta
    for idx, (col, label) in enumerate(zip(top_cols, top_labels)):
        if col in df.columns:
            line, = axes[0].plot(df.index, df[col], label=label, color=colour_cycle[idx % len(colour_cycle)])
            lines.append(line)
    axes[0].set_ylabel('Aggregated (mean across models)')
    axes[0].set_title(f'[{title_prefix} strategy]: DeepIQ hyperparameters')

    # bottom row: eta, gamma, alphas
    for idx, (col, label) in enumerate(zip(bottom_cols, bottom_labels), start=1):
        if col in df.columns:
            line, = axes[1].plot(df.index, df[col], label=label, color=colour_cycle[idx % len(colour_cycle)])
            lines.append(line)
    axes[1].set_xlabel('Date / Iteration')
    axes[1].set_ylabel('Aggregated (mean across models)')
    axes[1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    plt.setp(axes[1].get_xticklabels(), rotation=45)

    if lines:  
        fig.legend(lines, all_labels, loc='upper center', ncol=6, frameon=False, bbox_to_anchor=(0.5, 1.02))

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

plot_aggregated_metrics_grouped(
    os.path.join(HP_DIR, f'aggregate_{LABEL}.csv'),
    title_prefix=LABEL_UP,
    save_path=os.path.join(HP_DIR, f'hyperparameters_{LABEL}.png')
)

def plot_middle_percentile(
    raw_folder: str,
    model_keyword: str,
    columns_to_plot: list[str],
    lower: int = 45,
    upper: int = 55,
    title_prefix: str = ''
) -> None:
    
    files = glob.glob(os.path.join(raw_folder, f'*{model_keyword}*.csv'))
    if not files:
        print(f"No files found for {model_keyword} in {raw_folder}")
        return

    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_csv(f, index_col=0))
        except Exception as e:
            print(f"Skipping unreadable file {f}: {e}")

    if not dfs:
        print("No usable raw files for percentile plotting.")
        return

    common_index = dfs[0].index

    for col in columns_to_plot:
        data_matrix = []
        for idx in common_index:
            vals = [df.loc[idx, col] for df in dfs if (idx in df.index) and (col in df.columns)]
            data_matrix.append(vals)

        lowers  = [np.percentile(vals, lower) if len(vals) > 0 else np.nan for vals in data_matrix]
        uppers  = [np.percentile(vals, upper) if len(vals) > 0 else np.nan for vals in data_matrix]
        medians = [np.median(vals)            if len(vals) > 0 else np.nan for vals in data_matrix]
        means   = [np.mean(vals)              if len(vals) > 0 else np.nan for vals in data_matrix]

        fig, ax = plt.subplots(figsize=(18, 6))

        x = np.arange(len(common_index))
        for i in range(len(common_index)):
            if not np.isnan(lowers[i]) and not np.isnan(uppers[i]):
                ax.add_patch(plt.Rectangle((i - 0.4, lowers[i]), 0.8, uppers[i] - lowers[i],
                                           color='lightgrey', alpha=0.7))

        ax.plot(x, medians, color='navy', label='Median', linewidth=2)
        ax.plot(x, means,   color='red',  label='Mean',   linewidth=2, linestyle='--')

        ax.set_title(f"[{title_prefix}] Distribution of {col} (Middle {upper - lower}% Only)")
        ax.set_xlabel('Iteration / Date index')
        ax.set_ylabel(col)

        if len(common_index) < 30:
            plt.xticks(x, common_index, rotation=45)
        else:
            step = max(1, len(common_index) // 20)
            plt.xticks(x[::step], [common_index[i] for i in range(0, len(common_index), step)], rotation=45)

        plt.tight_layout()
        plt.legend()

        out_path = os.path.join(HP_DIR, f"DeepIQ_{model_keyword}_{col}_middle_{upper - lower}_percent.png")
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {out_path}")

columns_to_plot = ['delta', 'gamma', 'epsilon', 'wB', 'wW', 'wT', 'wI']
plot_middle_percentile('portfolios', MODEL_KEYWORD, columns_to_plot, lower=40, upper=60, title_prefix=LABEL_UP)
