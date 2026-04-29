"""
ui/page_insights.py
===================
"Why DeepAtomicIQ" / insights page.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go

from ui.styles import ACCENT, ACCENT2, MUTED, PANEL, BORDER, get_svg, POS, NEG

def page_insights():
    st.markdown("""
<style>
.why-section { margin-bottom: 40px; }
.why-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 18px; padding: 28px 32px; margin-bottom: 16px; }
.why-card h3 { font-size: 15px; font-weight: 800; color: #6D5EFC; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 10px 0; }
.why-card p { font-size: 14px; color: #C5D3EC; line-height: 1.75; margin: 0; }
.param-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }
.param-chip { background: rgba(109,94,252,0.1); border: 1px solid rgba(109,94,252,0.25); border-radius: 10px; padding: 10px 14px; }
.param-sym { font-size: 18px; font-weight: 900; color: #fff; }
.param-name { font-size: 10px; color: #8BA6D3; font-weight: 700; text-transform: uppercase; }
.phase-tag { display: inline-block; background: rgba(142,246,209,0.1); border: 1px solid rgba(142,246,209,0.3); color: #8EF6D1; font-size: 10px; font-weight: 800; padding: 3px 10px; border-radius: 20px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="padding:4px 0 8px;">
  <div style="font-size:11px;font-weight:800;color:#6D5EFC;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px;">About the System</div>
  <div style="font-size:38px;font-weight:900;color:#ffffff;letter-spacing:-0.03em;margin-bottom:12px;">Why DeepAtomicIQ?</div>
  <div style="font-size:16px;color:#8BA6D3;max-width:720px;line-height:1.6;">A Markowitz-Informed Neural Network that learns how markets move together and builds portfolios that maximise the Sharpe Ratio — intelligently, transparently, and in real time.</div>
</div>
""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["How It Works", "Phase 2: Out-of-Sample Evaluation"])

    with tab1:
        sections = [
            (
                "1. Purpose and Overview",
                "This project implements a Markowitz-Informed Neural Network (MINN) to learn how to build investment portfolios that balance risk and return intelligently. It combines ideas from finance (portfolio theory) and machine learning (deep neural networks). The model learns how assets move together — their co-movements or correlations — and finds portfolio weights that maximize the Sharpe Ratio, a measure of performance defined as average return divided by risk. In plain terms: the network learns how to distribute money across several assets so that the overall portfolio performs well relative to its volatility."
            ),
            (
                "2. Main Files and Their Roles",
                "MainSR.py — the entry-point script. It loads data, builds batches, and controls the training of neural networks (SR = Sharpe Ratio). MINNlib.py — contains all core functions: computing correlations, building the neural network, and training the loss function. project_hyperparameters.py — defines all project settings and constants such as number of assets, training epochs, and loss penalties."
            ),
            (
                "3. The Neural Network (DeepIQNetPortfolio)",
                "The neural network takes asset returns as input and outputs three things: (1) IQ Parameters — delta (threshold between normal and extreme moves), gamma (temporal decay), and epsilon (delay term). (2) Channel logits B, W, T, I — representing Body, Wing, Tail, and Identity correlation structures. (3) Portfolio weights — allocations to each asset, normalized to sum to one."
            ),
            (
                "4. The IQ Model: Measuring Co-movement",
                "Traditional finance uses a correlation matrix. The IQ model constructs this matrix from standardized returns, distinguishing three movement regimes: Body (normal), Wing (asymmetric), and Tail (extreme). Each is weighted by temporal decay factors. The combined correlation matrix is: C_IQ = wB·C_B + wW·C_W + wT·C_T + wI·I. This is then converted into a covariance matrix using asset volatilities."
            ),
            (
                "5. The Loss Function",
                "The objective combines: Sharpe Ratio (main target), Volatility Control (maintain target volatility), Condition Number (numerical stability), Entropy (encourages diversification), Risk Parity (balances risk contributions), Top-Weight Constraints (limits dominance), and Turnover (discourages large weight changes). All lambda coefficients are defined in project_hyperparameters.py."
            ),
            (
                "6. Project Summary",
                "This system learns interpretable parameters (δ, γ, ε, wB, wW, wT, wI) that describe how markets move and relate to one another. It produces evolving portfolio allocations designed to maximize the Sharpe Ratio across time. The method ensures mathematical validity (positive semi-definite correlations) and produces transparent, analyzable results. The DeepAtomicIQ framework merges financial reasoning with explainable machine learning, bridging traditional optimization and modern neural inference."
            ),
        ]
        for title, body in sections:
            st.markdown(f"""
            <div class="why-card">
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:8px;padding:24px 32px;background:rgba(109,94,252,0.06);border:1px solid rgba(109,94,252,0.2);border-radius:18px;">
          <h3 style="font-size:13px;font-weight:800;color:#6D5EFC;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 16px;">Key IQ Parameters</h3>
          <div class="param-grid">
            <div class="param-chip"><div class="param-sym">δ (delta)</div><div class="param-name">Threshold between normal and extreme moves</div></div>
            <div class="param-chip"><div class="param-sym">γ (gamma)</div><div class="param-name">Temporal decay weighting</div></div>
            <div class="param-chip"><div class="param-sym">ε (epsilon)</div><div class="param-name">Delay term in regime detection</div></div>
            <div class="param-chip"><div class="param-sym">wB</div><div class="param-name">Body weight — normal co-movement</div></div>
            <div class="param-chip"><div class="param-sym">wW</div><div class="param-name">Wing weight — asymmetric moves</div></div>
            <div class="param-chip"><div class="param-sym">wT</div><div class="param-name">Tail weight — extreme market events</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="phase-tag">Phase 2: Out-of-Sample</div>', unsafe_allow_html=True)
        phase2_sections = [
            (
                "What Phase 2 Does",
                "This phase evaluates the DeepAtomicIQ neural network weights using out-of-sample (OOS) testing against a range of alternative covariance estimators and portfolio construction baselines. The purpose is to compare performance, turnover, and transaction cost behaviour of DeepAtomicIQ portfolios relative to established techniques."
            ),
            (
                "Pipeline Overview",
                "Step 1: Build DIQ Special Portfolios (DIQ1–DIQ5) from first-phase model outputs, aligned to the invest month and adjusted for the validation horizon. Step 2: Run OOS Mean–Variance Optimization using Max-Sharpe portfolio optimization with several covariance estimators including Ledoit–Wolf and RMT. Step 3: Summarize Performance into a single table reporting annualized return, risk, Sharpe ratio, turnover, drawdown, and VaR. Step 4 (Optional): Analyse learned parameter evolution and dynamic weight changes through time."
            ),
            (
                "Output Files",
                "DIQ1–DIQ5 CSV files in portfolios/special_portfolios/. OOS backtest results in OOS_results/ folder (cumulative value, returns, transaction costs, turnover). A consolidated performance summary in CSV and LaTeX formats. Optional: parameter trajectory and dynamic weight plots saved as PNG files."
            ),
            (
                "Important Notes",
                "DeepAtomicIQ weights are shifted forward by (m + 1) months before testing to represent realistic deployment. All scripts automatically align asset universes using the canonical price slice. Transaction costs are applied as a self-financing drag before portfolio returns are realized. The process is idempotent — re-running will overwrite existing results without duplication."
            ),
        ]
        for title, body in phase2_sections:
            st.markdown(f"""
            <div class="why-card">
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
            """, unsafe_allow_html=True)


# ── MARKET ────────────────────────────────────────────────────────────────────
import yfinance as yf
