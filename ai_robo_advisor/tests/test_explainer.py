"""
test_explainer.py
=================
Unit tests for explainer.py

Covers:
  - DeepIQInterpreter.get_summary() output correctness
  - explain() integration with portfolio + answers dicts
  - Edge cases: missing params, empty dicts

Run:
    cd "Demo_prototype copy"
    python -m pytest ai_robo_advisor/tests/ -v
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from ai_robo_advisor.explainer import DeepIQInterpreter, explain


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_iq_params():
    return {
        "delta": 1.5,
        "gamma": 0.08,
        "epsilon": 0.01,
        "regimes": {"Body": 0.6, "Wing": 0.2, "Tail": 0.1, "Identity": 0.1},
        "ann_vol": 12.5,
        "date": "2024-01-15",
    }


@pytest.fixture
def sample_portfolio(sample_iq_params):
    return {
        "risk_category": "DeepIQ Profile 3",
        "profile_score": 3,
        "allocation_pct": {
            "S&P 500 (US Equities)": 40.0,
            "Core Fixed Income (AGG)": 35.0,
            "Gold (XAU)": 15.0,
            "Real Estate (REITs)": 10.0,
        },
        "iq_params": sample_iq_params,
        "stats": {
            "expected_annual_return": 7.5,
            "expected_volatility": 12.5,
            "sharpe_ratio": 0.28,
            "max_drawdown_est": 20.6,
        },
        "simulated_growth": {"p10": 18000, "p50": 30000, "p90": 50000, "years": 20},
        "growth_curve": {"x": [0, 1, 2], "y": [10000, 10700, 11449]},
        "date": "2024-01-15",
    }


@pytest.fixture
def sample_answers():
    return {
        "q2_age": "32",
        "q3_horizon": "15 years",
        "q10_reaction": "Stay calm and hold my positions",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. DeepIQInterpreter.get_summary()
# ─────────────────────────────────────────────────────────────────────────────

class TestDeepIQInterpreter:
    def test_returns_string(self, sample_iq_params):
        result = DeepIQInterpreter.get_summary(sample_iq_params)
        assert isinstance(result, str)

    def test_result_non_empty(self, sample_iq_params):
        result = DeepIQInterpreter.get_summary(sample_iq_params)
        assert len(result.strip()) > 0

    def test_contains_strategy_header(self, sample_iq_params):
        result = DeepIQInterpreter.get_summary(sample_iq_params)
        assert "DeepIQ" in result

    def test_high_delta_triggers_high_threshold_message(self, sample_iq_params):
        params = {**sample_iq_params, "delta": 1.5}
        result = DeepIQInterpreter.get_summary(params)
        assert "high threshold" in result.lower() or "significant market" in result.lower()

    def test_medium_delta_triggers_balanced_message(self, sample_iq_params):
        params = {**sample_iq_params, "delta": 0.9}
        result = DeepIQInterpreter.get_summary(params)
        assert "balanced" in result.lower()

    def test_low_delta_triggers_sensitive_message(self, sample_iq_params):
        params = {**sample_iq_params, "delta": 0.3}
        result = DeepIQInterpreter.get_summary(params)
        assert "sensitive" in result.lower()

    def test_positive_gamma_triggers_recency_bias(self, sample_iq_params):
        params = {**sample_iq_params, "gamma": 0.10}
        result = DeepIQInterpreter.get_summary(params)
        assert "recency" in result.lower()

    def test_negative_gamma_triggers_history_bias(self, sample_iq_params):
        params = {**sample_iq_params, "gamma": -0.10}
        result = DeepIQInterpreter.get_summary(params)
        assert "history" in result.lower() or "long-term" in result.lower()

    def test_neutral_gamma_triggers_balanced_message(self, sample_iq_params):
        params = {**sample_iq_params, "gamma": 0.0}
        result = DeepIQInterpreter.get_summary(params)
        assert "neutral" in result.lower()

    def test_tail_regime_detected_when_dominant(self, sample_iq_params):
        params = {**sample_iq_params, "regimes": {"Body": 0.1, "Wing": 0.1, "Tail": 0.7, "Identity": 0.1}}
        result = DeepIQInterpreter.get_summary(params)
        assert "tail" in result.lower()

    def test_wing_regime_detected_when_dominant(self, sample_iq_params):
        params = {**sample_iq_params, "regimes": {"Body": 0.1, "Wing": 0.7, "Tail": 0.1, "Identity": 0.1}}
        result = DeepIQInterpreter.get_summary(params)
        assert "asymmetric" in result.lower() or "wing" in result.lower()

    def test_empty_params_returns_fallback(self):
        result = DeepIQInterpreter.get_summary({})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_none_params_handled_gracefully(self):
        """get_summary should not raise when passed None or empty."""
        result = DeepIQInterpreter.get_summary(None)
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# 2. explain() integration
# ─────────────────────────────────────────────────────────────────────────────

class TestExplainIntegration:
    def test_returns_string(self, sample_portfolio, sample_answers):
        result = explain(sample_portfolio, sample_answers)
        assert isinstance(result, str)

    def test_result_non_empty(self, sample_portfolio, sample_answers):
        result = explain(sample_portfolio, sample_answers)
        assert len(result.strip()) > 0

    def test_contains_risk_category(self, sample_portfolio, sample_answers):
        result = explain(sample_portfolio, sample_answers)
        assert "Profile 3" in result or "Moderate" in result or "DeepIQ" in result

    def test_contains_personal_alignment_section(self, sample_portfolio, sample_answers):
        result = explain(sample_portfolio, sample_answers)
        assert "Personal" in result or "Investor" in result

    def test_empty_answers_does_not_crash(self, sample_portfolio):
        result = explain(sample_portfolio, {})
        assert isinstance(result, str)

    def test_missing_iq_params_does_not_crash(self, sample_answers):
        portfolio_no_iq = {
            "risk_category": "DeepIQ Profile 1",
            "iq_params": None,
            "stats": {"sharpe_ratio": 0.1},
        }
        result = explain(portfolio_no_iq, sample_answers)
        assert isinstance(result, str)
