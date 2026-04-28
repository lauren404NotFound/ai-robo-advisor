"""
test_backend_api_integration.py
================================
Integration tests for backend_api.py FastAPI endpoints.

Uses FastAPI's built-in TestClient (httpx) to fire real HTTP requests
against the live router — no mocking of the API layer itself.

Database and portfolio_engine calls ARE real (or mocked where a live
MongoDB URI is absent), so these tests verify end-to-end request →
engine → response contracts.

Coverage:
  - POST /api/survey/calculate      — risk profile + portfolio response shape
  - GET  /api/survey/suitability    — FCA eligibility logic
  - POST /api/simulation/project    — Monte Carlo endpoint contracts
  - GET  /api/portfolio/weights     — ETF weight structure
  - GET  /api/market/intelligence   — sentiment derivation
  - GET  /api/user/profile          — 404 on unknown user
  - POST /api/auth/session/refresh  — token rotation
  - POST /api/support/ticket        — ticket creation

Run:
    pip install httpx
    python -m pytest ai_robo_advisor/tests/test_backend_api_integration.py -v
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Patch database init_db before any import touches it
with patch("pymongo.MongoClient"):
    from fastapi.testclient import TestClient
    import ai_robo_advisor.backend_api as api
    client = TestClient(api.app)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

TYPICAL_SURVEY = {
    "user_email":        "test@lemstratiq.com",
    "age":               35,
    "income":            55000.0,
    "savings":           20000.0,
    "monthly_expenses":  1800.0,
    "debt":              5000.0,
    "dependents":        0,
    "horizon":           15,
    "self_risk":         3,
    "emergency_months":  4.0,
    "experience_yrs":    5.0,
    "behav_score":       13,
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /api/survey/calculate
# ─────────────────────────────────────────────────────────────────────────────

class TestSurveyCalculateEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Mock DB calls triggered inside the endpoint
        cls._db_patch = patch("ai_robo_advisor.backend_api.database.get_latest_assessment",
                              return_value=None)
        cls._audit_patch = patch("ai_robo_advisor.backend_api.log_audit_action")
        cls._db_patch.start()
        cls._audit_patch.start()
        cls.resp = client.post("/api/survey/calculate", json=TYPICAL_SURVEY)

    @classmethod
    def tearDownClass(cls):
        cls._db_patch.stop()
        cls._audit_patch.stop()

    def test_status_200(self):
        self.assertEqual(self.resp.status_code, 200)

    def test_response_has_status_success(self):
        self.assertEqual(self.resp.json()["status"], "success")

    def test_response_has_risk_category(self):
        body = self.resp.json()
        self.assertIn("risk_category", body)
        self.assertIsInstance(body["risk_category"], int)

    def test_risk_category_in_valid_range(self):
        rc = self.resp.json()["risk_category"]
        self.assertGreaterEqual(rc, 1)
        self.assertLessEqual(rc, 6)

    def test_response_has_confidence(self):
        body = self.resp.json()
        self.assertIn("confidence", body)
        c = body["confidence"]
        self.assertGreaterEqual(c, 0.0)
        self.assertLessEqual(c, 1.0)

    def test_response_has_portfolio(self):
        body = self.resp.json()
        self.assertIn("portfolio", body)
        self.assertIsInstance(body["portfolio"], dict)

    def test_portfolio_has_allocation_pct(self):
        port = self.resp.json()["portfolio"]
        self.assertIn("allocation_pct", port)
        self.assertIsInstance(port["allocation_pct"], dict)

    def test_portfolio_has_stats(self):
        port = self.resp.json()["portfolio"]
        self.assertIn("stats", port)

    def test_model_used_field_present(self):
        self.assertIn("model_used", self.resp.json())

    def test_age_below_18_rejected(self):
        bad = {**TYPICAL_SURVEY, "age": 15}
        r = client.post("/api/survey/calculate", json=bad)
        self.assertEqual(r.status_code, 422)

    def test_negative_income_rejected(self):
        bad = {**TYPICAL_SURVEY, "income": -1000}
        r = client.post("/api/survey/calculate", json=bad)
        self.assertEqual(r.status_code, 422)

    def test_missing_email_rejected(self):
        bad = {k: v for k, v in TYPICAL_SURVEY.items() if k != "user_email"}
        r = client.post("/api/survey/calculate", json=bad)
        self.assertEqual(r.status_code, 422)


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /api/survey/suitability
# ─────────────────────────────────────────────────────────────────────────────

class TestSuitabilityEndpoint(unittest.TestCase):

    def test_eligible_adult_with_income(self):
        r = client.get("/api/survey/suitability",
                       params={"user_email": "a@b.com", "age": 30, "income": 40000})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["eligible_for_high_risk"])

    def test_underage_is_ineligible(self):
        r = client.get("/api/survey/suitability",
                       params={"user_email": "a@b.com", "age": 17, "income": 40000})
        self.assertFalse(r.json()["eligible_for_high_risk"])

    def test_low_income_is_ineligible(self):
        r = client.get("/api/survey/suitability",
                       params={"user_email": "a@b.com", "age": 25, "income": 10000})
        self.assertFalse(r.json()["eligible_for_high_risk"])

    def test_response_has_reason_string(self):
        r = client.get("/api/survey/suitability",
                       params={"user_email": "a@b.com", "age": 30, "income": 40000})
        self.assertIsInstance(r.json()["reason"], str)
        self.assertGreater(len(r.json()["reason"]), 0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. POST /api/simulation/project
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationEndpoint(unittest.TestCase):

    BASE = {
        "initial_investment":   10000.0,
        "monthly_contribution": 300.0,
        "time_horizon_years":   10,
        "risk_category":        3,
        "n_paths":              200,   # keep fast for tests
    }

    def test_status_200(self):
        r = client.post("/api/simulation/project", json=self.BASE)
        self.assertEqual(r.status_code, 200)

    def test_response_has_all_percentile_keys(self):
        body = client.post("/api/simulation/project", json=self.BASE).json()
        for key in ("p10_worst_case", "p25", "median_projection", "p75", "p90_best_case"):
            self.assertIn(key, body, f"Missing key: {key}")

    def test_percentiles_ordered(self):
        body = client.post("/api/simulation/project", json=self.BASE).json()
        self.assertLessEqual(body["p10_worst_case"], body["p25"])
        self.assertLessEqual(body["p25"],            body["median_projection"])
        self.assertLessEqual(body["median_projection"], body["p75"])
        self.assertLessEqual(body["p75"],            body["p90_best_case"])

    def test_median_positive(self):
        body = client.post("/api/simulation/project", json=self.BASE).json()
        self.assertGreater(body["median_projection"], 0)

    def test_risk_free_benchmark_present(self):
        body = client.post("/api/simulation/project", json=self.BASE).json()
        self.assertIn("risk_free_benchmark", body)

    def test_higher_risk_gives_higher_return_pct(self):
        low  = client.post("/api/simulation/project", json={**self.BASE, "risk_category": 1}).json()
        high = client.post("/api/simulation/project", json={**self.BASE, "risk_category": 6}).json()
        self.assertGreater(high["annual_return_pct"], low["annual_return_pct"])

    def test_invalid_risk_category_rejected(self):
        r = client.post("/api/simulation/project", json={**self.BASE, "risk_category": 0})
        self.assertEqual(r.status_code, 422)

    def test_zero_investment_does_not_crash(self):
        r = client.post("/api/simulation/project",
                        json={**self.BASE, "initial_investment": 0.0, "monthly_contribution": 0.0})
        self.assertEqual(r.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /api/portfolio/weights
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioWeightsEndpoint(unittest.TestCase):

    def test_status_200_for_valid_profile(self):
        r = client.get("/api/portfolio/weights", params={"risk_category": 3})
        self.assertEqual(r.status_code, 200)

    def test_response_has_weights_dict(self):
        body = client.get("/api/portfolio/weights", params={"risk_category": 3}).json()
        self.assertIn("weights", body)
        self.assertIsInstance(body["weights"], dict)

    def test_weights_non_empty(self):
        body = client.get("/api/portfolio/weights", params={"risk_category": 3}).json()
        self.assertGreater(len(body["weights"]), 0)

    def test_all_weights_between_0_and_1(self):
        body = client.get("/api/portfolio/weights", params={"risk_category": 4}).json()
        for ticker, w in body["weights"].items():
            self.assertGreaterEqual(w, 0.0, f"{ticker} weight negative")
            self.assertLessEqual(w, 1.0, f"{ticker} weight > 1")

    def test_invalid_risk_category_returns_400(self):
        r = client.get("/api/portfolio/weights", params={"risk_category": 9})
        self.assertEqual(r.status_code, 400)

    def test_all_six_profiles_return_200(self):
        for p in range(1, 7):
            r = client.get("/api/portfolio/weights", params={"risk_category": p})
            self.assertEqual(r.status_code, 200, f"Profile {p} returned {r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /api/market/intelligence
# ─────────────────────────────────────────────────────────────────────────────

class TestMarketIntelligenceEndpoint(unittest.TestCase):

    def test_status_200(self):
        r = client.get("/api/market/intelligence")
        self.assertEqual(r.status_code, 200)

    def test_has_sentiment_string(self):
        body = client.get("/api/market/intelligence").json()
        self.assertIsInstance(body["sentiment"], str)
        self.assertGreater(len(body["sentiment"]), 0)

    def test_has_signal_string(self):
        body = client.get("/api/market/intelligence").json()
        self.assertIn(body["signal"], ("defensive", "cautious", "neutral"))

    def test_has_regime_weights(self):
        body = client.get("/api/market/intelligence").json()
        self.assertIn("regime_weights", body)


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET /api/user/profile
# ─────────────────────────────────────────────────────────────────────────────

class TestUserProfileEndpoint(unittest.TestCase):

    def test_unknown_user_returns_404(self):
        with patch("ai_robo_advisor.backend_api.database.get_user", return_value=None):
            r = client.get("/api/user/profile", params={"user_email": "ghost@x.com"})
        self.assertEqual(r.status_code, 404)

    def test_known_user_returns_200(self):
        mock_user = {
            "email": "real@x.com", "name": "Real User",
            "dob": "1990-01-01", "provider": "email", "preferences_json": "{}",
        }
        with patch("ai_robo_advisor.backend_api.database.get_user", return_value=mock_user):
            r = client.get("/api/user/profile", params={"user_email": "real@x.com"})
        self.assertEqual(r.status_code, 200)

    def test_profile_quality_pct_in_0_to_100(self):
        mock_user = {
            "email": "real@x.com", "name": "Real User",
            "dob": "1990-01-01", "provider": "email", "preferences_json": "{}",
        }
        with patch("ai_robo_advisor.backend_api.database.get_user", return_value=mock_user):
            body = client.get("/api/user/profile",
                              params={"user_email": "real@x.com"}).json()
        self.assertGreaterEqual(body["profile_quality_pct"], 0)
        self.assertLessEqual(body["profile_quality_pct"], 100)

    def test_tier_is_string(self):
        mock_user = {
            "email": "real@x.com", "name": "Real User",
            "dob": "1990-01-01", "provider": "email", "preferences_json": "{}",
        }
        with patch("ai_robo_advisor.backend_api.database.get_user", return_value=mock_user):
            body = client.get("/api/user/profile",
                              params={"user_email": "real@x.com"}).json()
        self.assertIn(body["tier"], ("Pro", "Basic"))


# ─────────────────────────────────────────────────────────────────────────────
# 7. POST /api/auth/session/refresh
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionRefreshEndpoint(unittest.TestCase):

    def test_status_200(self):
        with patch("ai_robo_advisor.backend_api.log_audit_action"):
            r = client.post("/api/auth/session/refresh",
                            params={"current_token": "old-token-abc"})
        self.assertEqual(r.status_code, 200)

    def test_returns_new_token(self):
        with patch("ai_robo_advisor.backend_api.log_audit_action"):
            body = client.post("/api/auth/session/refresh",
                               params={"current_token": "old-token-abc"}).json()
        self.assertIn("new_token", body)
        self.assertIsInstance(body["new_token"], str)
        self.assertGreater(len(body["new_token"]), 10)

    def test_new_token_differs_from_old(self):
        old = "old-token-xyz"
        with patch("ai_robo_advisor.backend_api.log_audit_action"):
            body = client.post("/api/auth/session/refresh",
                               params={"current_token": old}).json()
        self.assertNotEqual(body["new_token"], old)

    def test_expires_in_is_30_days_in_seconds(self):
        with patch("ai_robo_advisor.backend_api.log_audit_action"):
            body = client.post("/api/auth/session/refresh",
                               params={"current_token": "tok"}).json()
        self.assertEqual(body["expires_in"], 2_592_000)


# ─────────────────────────────────────────────────────────────────────────────
# 8. POST /api/support/ticket
# ─────────────────────────────────────────────────────────────────────────────

class TestSupportTicketEndpoint(unittest.TestCase):

    TICKET = {"subject": "Login issue", "message": "Cannot log in with Google."}

    def test_status_200(self):
        with patch("ai_robo_advisor.backend_api.database.save_support_ticket"), \
             patch("ai_robo_advisor.backend_api.log_audit_action"):
            r = client.post("/api/support/ticket",
                            params={"user_email": "u@t.com"}, json=self.TICKET)
        self.assertEqual(r.status_code, 200)

    def test_returns_ticket_id_uuid(self):
        import re
        with patch("ai_robo_advisor.backend_api.database.save_support_ticket"), \
             patch("ai_robo_advisor.backend_api.log_audit_action"):
            body = client.post("/api/support/ticket",
                               params={"user_email": "u@t.com"}, json=self.TICKET).json()
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        self.assertRegex(body["ticket_id"], uuid_pattern)

    def test_status_field_is_success(self):
        with patch("ai_robo_advisor.backend_api.database.save_support_ticket"), \
             patch("ai_robo_advisor.backend_api.log_audit_action"):
            body = client.post("/api/support/ticket",
                               params={"user_email": "u@t.com"}, json=self.TICKET).json()
        self.assertEqual(body["status"], "success")


if __name__ == "__main__":
    unittest.main()
