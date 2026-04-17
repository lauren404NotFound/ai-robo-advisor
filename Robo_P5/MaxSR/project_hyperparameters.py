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
Name     : project_hyperparameters.py 
Contact  : drwss.academy@gmail.com
Date     : 11/10/25
Desc     : parameters for DeepAtomicIQ project and multi-asset-class portfolio

NB: one iteration involves 'stp' epochs of 'b' batches per epoch, amounting to stp*b*m
forward & stp*b backward passes of the network. Each row in a batch gets forward-passed. 
When all rows have been forward-passed, each generating an output, these outputs are 
averaged to produce a batch output vector [output_dim,1]. Backpropogation is performed 
on this vector providing updates. Validation has been incorporated using data from the 
next m rows into the iteration's future.
"""

import os
import torch
import numpy as np
import pandas as pd

# compute device
USE_GPU = False
device  = torch.device("cuda" if USE_GPU and torch.cuda.is_available() else "cpu")

# choose from 9-asset or 10-asset portfolio
n_assets = 9

# batch/iteration geometry
n_strata = 6  # number of strata in stratified parent (mapped to same in child batch to preserve time-ordering)

# r must be multiple of n_strata, and m must be a multiple of n_strata and <= r.
r   = 48  # parent rows, from which b time-ordered training batches are extracted
m   = 24  # each child (batch) rows [and validation window]
b   =  5  # number of batches (child collective)
f   =  1  # step-forward in 'rows' between iterations
stp = 14  # stop after this many epochs
dropout_rate = 0.5  # dropout for DeepAtomicIQ

# memory-reset cadence (in iterations)
m_memory    = r
new_weights = int(m_memory / f)

# dates can be month strings like "Dec 2003" or "2023-12".
dates = {"start":"Dec 2003", "end":"Dec 2023"}
  
# file locations relative to this module
base_dir   = os.path.dirname(__file__)
price_dir  = os.path.join(base_dir, "price_data")

# master prices CSV (10 assets; columns after 'Date' are assets)
master_prices_csv = os.path.join(price_dir, "prices_multi_asset_master.csv")

# derived slice outputs (both written to ./price_data/)
deep_filename = "prcs_diq_slice.csv"
mvo_filename  = "prcs_mvo_slice.csv"

# risk-free rate configuration (sourced from ./price_data/)
rf_config = {
    "enabled"       : True,
    "csv_path"      : os.path.join(price_dir, "DGS3MO_monthly_rf.csv"),
    "frequency"     : "M",              
    "column"        : None,            
    "align_method"  : "ffill",         
    "interpretation": "monthly_effective", # {"monthly_effective","annualized_yield"}
    "use_in_sharpe" : True,
    "use_in_loss"   : True
}

# legacy constant rfr (not used if rf_config['use_in_loss'] is True)
risk_free_rate = 0.0

# IQ parameters and network output sizing
# portfolio weights dimension follows n_assets toggle
output_dim_1 = 7 # delta,gamma,epsilon,[B,W,T,I; learned weights for channels and identity]
output_dim_2 = output_dim_1 + n_assets 

# total number of models = n_groups*n_models
n_groups = 4 # number of command line windows (groups) running in parallel (manual parallelisation on my desktop)
n_models = 6 # number of models/group for manual parallelisation, we have [n_models*n_groups] staggered-start models in total.

# scaling/constraints for IQ parameters
l_delta    = 1.00 # lower limit of delta range
u_delta    = 2.00 # upper limit of delta range
u_gamma    = 0.10 # gamma is now u_gamma* tanh(z)
gamma_mode = "signed" # {"raw", "signed"}  
a_floor    = 1e-3 # floor for temporal weights [set to 0 to disable]
l_eps      = 0.00 # lower limit of epsilon range
u_eps      = m-1  # upper limit of epsilon range
eps_init   = 2.00 # bias epsilon-learning to start at this value 
threshold  = 0.05 # noise exclusion threshold [half-]width
assert threshold < l_delta, f"threshold ({threshold}) must be less than l_delta ({l_delta})"
PSD_hard = True # check/report any non-PSD (at -1e-08 tolerance)

# parameters/coefficients for DeepIQ loss function
ann_target_vol    = 3    # annualised portfolio volatility target (%)
target_vol        = ann_target_vol/(100*np.sqrt(12))
lambda_vol        = 0.0  # raw portfolio volatility loss
lambda_vol_target = 0.0  # ReLU(ceiling) portfolio volatility loss
lambda_cn         = 0.0  # ReLU (ceiling) condition number loss
lambda_entropy    = 0.1  # entropy loss for portfolio weights
lambda_rp         = 0.1  # risk-parity loss for portfolio weights
lambda_tw         = 0.1  # loss associated with excessive largest portfolio weight
lambda_t3w        = 0.1  # loss associated with excessive sum of three largest portfolio weights
lambda_sharpe     = 1.0  # Sharpe Ratio loss 
lambda_turnover   = 0.5  # turnover loss
max_tw            = 0.7  # upper limit for a penalty-free largest weight
max_t3w           = 1.0  # upper limit for a penalty-free sum of largest three weights 

# IQ centering and scaling options
center_method = "mean"   # {"mean", "median", "zero"}
scale_method  = "vols"   # {"vols", "vols_min", "vols_max", "vols_avg"}

iq_method = "iq1"
iq_method_description = {
    "iq1": "atomic IQ1 - whole-atom temporal scaling",  # temporal distinction between occurance and co-occurance (No)
    "iq2": "atomic IQ2 - off-diagonal temporal scaling" # temporal distinction between occurance and co-occurance (Yes)
}[iq_method]

# w_I [annealing] soft cap [set lambda_wI_cap == 0.0 to disable]
lambda_wI_cap        = 0.5       # strength of penalty on w_I above the cap (>= 0)
wI_cap_start         = 1.00      # cap at epoch 0 (1.00 = no penalty initially)
wI_cap_end           = 0.40      # cap at final epoch (discourage >wI_cap_end identity by end)
wI_cap_warmup_epochs = 0         # hold cap at wI_cap_start for the first wI_cap_warmup_epochs epochs
wI_cap_schedule      = "cosine"  # {"linear","cosine"}  (cosine is smoother)

# flags for computing style used in averaging retirns
exp_ret_style = 'arithmetic' #'geometric'
rf_style      = 'arithmetic' #'geometric' 
