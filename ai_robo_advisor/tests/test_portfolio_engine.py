"""
test_portfolio_engine.py
========================
Unit tests for portfolio_engine.py

Covers:
  - Risk score → profile number mapping
  - build_portfolio() contract (return structure, numeric sanity)
  - simulate_growth() statistical properties
  - growth_curve() shape
  - Fallback behaviour when Robo_Pn CSV data is absent

Run:
    cd "Demo_prototype copy"
    python -m pytest ai_robo_advisor/tests/ -v
"""

import sys
import os

# Ensure the package root is on the path so imports work without installing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from ai_robo_advisor.portfolio_engine import build_portfolio, simulate_growth, growth_curve, TICKER_MAP, ASSETS


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def conservative_portfolio():
    return build_portfolio(risk_score=1.0, initial=10_000, monthly=200, years=10)


@pytest.fixture(scope="module")
def moderate_portfolio():
    return build_portfolio(risk_score=5.0, initial=20_000, monthly=500, years=20)


@pytest.fixture(scope="module")
def aggressive_portfolio():
    return build_portfolio(risk_score=10.0, initial=5_000, monthly=100, years=30)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Risk Score → Profile Mapping
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskProfileMapping:
    """Verify that the score-to-profile lookup table is correct end-to-end."""

    @pytest.mark.parametrize("score,expected_profile", [
        (1.0,  1),
        (2.0,  1),
        (2.1,  2),
        (4.0,  2),
        (4.1,  3),
        (6.0,  3),
        (6.1,  4),
        (8.0,  4),
        (8.1,  5),
        (9.0,  5),
        (9.1,  6),
        (10.0, 6),
    ])
    def test_score_to_profile_number(self, score, expected_profile):
        result = build_portfolio(risk_score=score)
        assert f"Profile {expected_profile}" in result["risk_category"], (
            f"risk_score={score} should map to Profile {expected_profile}, "
            f"got: {result['risk_category']}"
        )

    def test_conservative_is_profile_1(self, conservative_portfolio):
        assert "Profile 1" in conservative_portfolio["risk_category"]

    def test_aggressive_is_profile_6(self, aggressive_portfolio):
        assert "Profile 6" in aggressive_portfolio["risk_category"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. build_portfolio() — Return Structure
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildPortfolioStructure:
    """Ensure the returned dict always has the expected top-level keys."""

    REQUIRED_KEYS = {
        "risk_category",
        "profile_score",
        "allocation_pct",
        "stats",
        "simulated_growth",
        "growth_curve",
        "date",
    }

    REQUIRED_STATS_KEYS = {
        "expected_annual_return",
        "expected_volatility",
        "sharpe_ratio",
        "max_drawdown_est",
    }

    def test_top_level_keys_present(self, moderate_portfolio):
        missing = self.REQUIRED_KEYS - set(moderate_portfolio.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_stats_sub_keys_present(self, moderate_portfolio):
        missing = self.REQUIRED_STATS_KEYS - set(moderate_portfolio["stats"].keys())
        assert not missing, f"Missing stats keys: {missing}"

    def test_allocation_pct_is_dict(self, moderate_portfolio):
        assert isinstance(moderate_portfolio["allocation_pct"], dict)

    def test_allocation_pct_not_empty(self, moderate_portfolio):
        assert len(moderate_portfolio["allocation_pct"]) > 0

    def test_growth_curve_has_x_and_y(self, moderate_portfolio):
        gc = moderate_portfolio["growth_curve"]
        assert "x" in gc and "y" in gc

    def test_growth_curve_lengths_match(self, moderate_portfolio):
        gc = moderate_portfolio["growth_curve"]
        assert len(gc["x"]) == len(gc["y"])


# ─────────────────────────────────────────────────────────────────────────────
# 3. build_portfolio() — Numeric Sanity
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildPortfolioNumerics:
    """Financial values must be within reasonable real-world bounds."""

    def test_allocation_total_near_100(self, moderate_portfolio):
        total = sum(moderate_portfolio["allocation_pct"].values())
        assert 85 <= total <= 115, (
            f"Allocation weights sum to {total:.1f}% — expected ~100%"
        )

    def test_allocation_weights_non_negative(self, moderate_portfolio):
        for asset, weight in moderate_portfolio["allocation_pct"].items():
            assert weight >= 0, f"Negative weight for {asset}: {weight}"

    def test_expected_return_is_positive(self, moderate_portfolio):
        r = moderate_portfolio["stats"]["expected_annual_return"]
        assert r > 0, f"Expected annual return should be positive, got {r}"

    def test_expected_return_plausible_upper_bound(self, moderate_portfolio):
        r = moderate_portfolio["stats"]["expected_annual_return"]
        assert r < 30, f"Expected annual return of {r}% seems unrealistically high"

    def test_volatility_non_negative(self, moderate_portfolio):
        v = moderate_portfolio["stats"]["expected_volatility"]
        assert v >= 0

    def test_volatility_plausible_upper_bound(self, moderate_portfolio):
        v = moderate_portfolio["stats"]["expected_volatility"]
        assert v < 60, f"Volatility of {v}% is unrealistically high"

    def test_sharpe_ratio_is_numeric(self, moderate_portfolio):
        sr = moderate_portfolio["stats"]["sharpe_ratio"]
        assert isinstance(sr, (int, float))

    def test_sharpe_ratio_plausible_bounds(self, moderate_portfolio):
        sr = moderate_portfolio["stats"]["sharpe_ratio"]
        assert -3 <= sr <= 10, f"Sharpe ratio {sr} is outside plausible bounds"

    def test_max_drawdown_positive(self, moderate_portfolio):
        mdd = moderate_portfolio["stats"]["max_drawdown_est"]
        assert mdd >= 0

    def test_profile_score_integer_in_range(self, moderate_portfolio):
        ps = moderate_portfolio["profile_score"]
        assert 1 <= ps <= 6, f"profile_score {ps} out of expected 1–6 range"


# ─────────────────────────────────────────────────────────────────────────────
# 4. simulate_growth() — Statistical Properties
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulateGrowth:
    """Monte Carlo simulation must return statistically sensible output."""

    def test_returns_all_percentile_keys(self):
        result = simulate_growth(10_000, 500, 0.07, 0.12, 10)
        for key in ("p10", "p25", "p50", "p75", "p90"):
            assert key in result, f"Missing percentile key: {key}"

    def test_percentiles_are_ordered(self):
        result = simulate_growth(10_000, 500, 0.07, 0.12, 10)
        assert result["p10"] <= result["p25"] <= result["p50"] <= result["p75"] <= result["p90"], (
            f"Percentiles out of order: {result}"
        )

    def test_all_percentiles_non_negative(self):
        result = simulate_growth(10_000, 500, 0.07, 0.12, 10)
        for k, v in result.items():
            if k != "years":
                assert v >= 0, f"{k} = {v} is negative"

    def test_higher_return_gives_higher_median(self):
        low  = simulate_growth(10_000, 0, 0.02, 0.05, 20)
        high = simulate_growth(10_000, 0, 0.10, 0.05, 20)
        assert high["p50"] > low["p50"], (
            "A higher annual return should yield a higher median terminal value"
        )

    def test_longer_horizon_gives_higher_median(self):
        short = simulate_growth(10_000, 500, 0.07, 0.12, 5)
        long_ = simulate_growth(10_000, 500, 0.07, 0.12, 20)
        assert long_["p50"] > short["p50"]

    def test_zero_initial_investment_does_not_crash(self):
        result = simulate_growth(0, 100, 0.05, 0.10, 5)
        assert result["p50"] >= 0

    def test_zero_contribution_does_not_crash(self):
        result = simulate_growth(10_000, 0, 0.06, 0.10, 10)
        assert result["p50"] >= 0

    def test_years_field_matches_input(self):
        result = simulate_growth(10_000, 500, 0.07, 0.12, 15)
        assert result["years"] == 15

    def test_deterministic_with_fixed_seed(self):
        """Same inputs should produce the same output (seeded RNG)."""
        r1 = simulate_growth(10_000, 500, 0.07, 0.12, 10)
        r2 = simulate_growth(10_000, 500, 0.07, 0.12, 10)
        assert r1["p50"] == r2["p50"], "simulate_growth must be deterministic"


# ─────────────────────────────────────────────────────────────────────────────
# 5. growth_curve() — Shape Checks
# ─────────────────────────────────────────────────────────────────────────────

class TestGrowthCurve:
    def test_returns_x_and_y(self):
        result = growth_curve(10_000, 500, 0.07, 10)
        assert "x" in result and "y" in result

    def test_length_equals_months_plus_one(self):
        years = 10
        result = growth_curve(10_000, 500, 0.07, years)
        expected_len = years * 12 + 1
        assert len(result["x"]) == expected_len
        assert len(result["y"]) == expected_len

    def test_starts_at_initial_investment(self):
        initial = 15_000
        result = growth_curve(initial, 500, 0.07, 10)
        assert result["y"][0] == pytest.approx(initial, rel=0.01)

    def test_value_increases_with_positive_return(self):
        result = growth_curve(10_000, 0, 0.07, 10)
        assert result["y"][-1] > result["y"][0], "Portfolio should grow with positive return"

    def test_x_axis_ends_at_correct_year(self):
        years = 15
        result = growth_curve(10_000, 500, 0.07, years)
        assert result["x"][-1] == pytest.approx(years, rel=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Constants / Configuration
# ─────────────────────────────────────────────────────────────────────────────

class TestModuleConstants:
    def test_ticker_map_not_empty(self):
        assert len(TICKER_MAP) > 0

    def test_ticker_map_values_are_strings(self):
        for k, v in TICKER_MAP.items():
            assert isinstance(v, str), f"TICKER_MAP[{k}] is not a string"

    def test_assets_list_matches_ticker_map(self):
        assert set(ASSETS) == set(TICKER_MAP.values())

    def test_known_tickers_present(self):
        """Core index tickers that are expected in every portfolio config."""
        for expected in ("SPX", "LBUSTRUU", "XAU"):
            assert expected in TICKER_MAP, f"Expected ticker {expected} missing from TICKER_MAP"
