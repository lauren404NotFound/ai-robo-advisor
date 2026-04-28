"""
test_train_model.py
===================
Unit tests for train_model.py

Covers:
  - Dataset generation shape and label distribution
  - Feature engineering (derived columns)
  - Label validity (all values in known set)
  - train() produces a fitted classifier with correct classes
  - Classifier produces valid probability vectors
  - Artefact persistence (model.pkl etc. are written to disk)

Run:
    python -m pytest ai_robo_advisor/tests/test_train_model.py -v
"""

import sys
import os
import unittest
import tempfile
import pickle

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ai_robo_advisor.train_model import generate_dataset, train

EXPECTED_LABELS = {
    "Very Conservative", "Conservative", "Moderate", "Aggressive", "Very Aggressive"
}

EXPECTED_FEATURES = [
    "age", "income", "savings", "monthly_expenses", "debt", "dependents",
    "horizon", "self_risk", "emergency_months", "experience_yrs", "behav_score",
    "savings_income_ratio", "debt_income_ratio", "net_monthly", "fin_slack",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dataset generation
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateDataset(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df = generate_dataset(n=500, seed=0)

    def test_returns_expected_row_count(self):
        self.assertEqual(len(self.df), 500)

    def test_contains_all_expected_raw_columns(self):
        raw_cols = [
            "age", "income", "savings", "monthly_expenses", "debt",
            "dependents", "horizon", "self_risk", "emergency_months",
            "experience_yrs", "behav_score",
        ]
        for col in raw_cols:
            self.assertIn(col, self.df.columns, f"Missing column: {col}")

    def test_contains_derived_feature_columns(self):
        derived = ["savings_income_ratio", "debt_income_ratio", "net_monthly", "fin_slack"]
        for col in derived:
            self.assertIn(col, self.df.columns, f"Missing derived column: {col}")

    def test_contains_label_column(self):
        self.assertIn("risk_category", self.df.columns)

    def test_all_labels_in_expected_set(self):
        unique = set(self.df["risk_category"].astype(str).unique())
        unknown = unique - EXPECTED_LABELS
        self.assertEqual(unknown, set(), f"Unexpected label values: {unknown}")

    def test_all_five_labels_represented(self):
        unique = set(self.df["risk_category"].astype(str).unique())
        self.assertEqual(unique, EXPECTED_LABELS)

    def test_age_range_valid(self):
        self.assertTrue((self.df["age"] >= 18).all())
        self.assertTrue((self.df["age"] <= 75).all())

    def test_income_positive(self):
        self.assertTrue((self.df["income"] > 0).all())

    def test_self_risk_in_1_to_5(self):
        self.assertTrue((self.df["self_risk"] >= 1).all())
        self.assertTrue((self.df["self_risk"] <= 5).all())

    def test_savings_income_ratio_non_negative(self):
        self.assertTrue((self.df["savings_income_ratio"] >= 0).all())

    def test_debt_income_ratio_non_negative(self):
        self.assertTrue((self.df["debt_income_ratio"] >= 0).all())

    def test_deterministic_with_same_seed(self):
        df1 = generate_dataset(n=100, seed=42)
        df2 = generate_dataset(n=100, seed=42)
        self.assertTrue((df1["income"].values == df2["income"].values).all())

    def test_different_seeds_give_different_data(self):
        df1 = generate_dataset(n=100, seed=1)
        df2 = generate_dataset(n=100, seed=2)
        self.assertFalse((df1["income"].values == df2["income"].values).all())


# ─────────────────────────────────────────────────────────────────────────────
# 2. Model training
# ─────────────────────────────────────────────────────────────────────────────

class TestTrainModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Train once on a small sample; redirect artefacts to a temp dir."""
        cls.tmpdir = tempfile.mkdtemp()
        cls.df = generate_dataset(n=800, seed=7)

        # Patch ARTEFACT_DIR so artefacts go to tmpdir, not the real package
        import ai_robo_advisor.train_model as tm
        cls._orig_dir = tm.ARTEFACT_DIR
        tm.ARTEFACT_DIR = cls.tmpdir

        cls.clf, cls.scaler, cls.le, cls.features = train(cls.df)

        tm.ARTEFACT_DIR = cls._orig_dir  # restore

    def test_classifier_has_predict_method(self):
        self.assertTrue(hasattr(self.clf, "predict"))

    def test_classifier_has_predict_proba_method(self):
        self.assertTrue(hasattr(self.clf, "predict_proba"))

    def test_label_encoder_knows_all_five_classes(self):
        classes = set(self.le.classes_)
        self.assertEqual(classes, EXPECTED_LABELS)

    def test_feature_list_matches_expected(self):
        self.assertEqual(self.features, EXPECTED_FEATURES)

    def test_scaler_has_correct_n_features(self):
        self.assertEqual(self.scaler.n_features_in_, len(EXPECTED_FEATURES))

    def test_model_pkl_written(self):
        import ai_robo_advisor.train_model as tm
        path = os.path.join(self.tmpdir, "model.pkl")
        self.assertTrue(os.path.exists(path), "model.pkl not written")

    def test_scaler_pkl_written(self):
        path = os.path.join(self.tmpdir, "scaler.pkl")
        self.assertTrue(os.path.exists(path))

    def test_label_encoder_pkl_written(self):
        path = os.path.join(self.tmpdir, "label_encoder.pkl")
        self.assertTrue(os.path.exists(path))

    def test_feature_names_pkl_written(self):
        path = os.path.join(self.tmpdir, "feature_names.pkl")
        self.assertTrue(os.path.exists(path))

    def test_saved_model_is_loadable(self):
        path = os.path.join(self.tmpdir, "model.pkl")
        with open(path, "rb") as f:
            loaded = pickle.load(f)
        self.assertTrue(hasattr(loaded, "predict"))

    def test_prediction_on_sample_row(self):
        import numpy as np
        # Construct a typical moderate-risk investor feature vector
        row = [35, 50000, 20000, 1500, 5000, 1, 15, 3, 4, 3, 13,
               0.4, 0.1, 2667, 6000]
        x = self.scaler.transform([row])
        pred = self.clf.predict(x)
        self.assertIn(self.le.inverse_transform(pred)[0], EXPECTED_LABELS)

    def test_predict_proba_sums_to_one(self):
        import numpy as np
        row = [30, 40000, 10000, 1200, 0, 0, 20, 4, 6, 2, 16,
               0.25, 0.0, 2133, 7200]
        x = self.scaler.transform([row])
        proba = self.clf.predict_proba(x)[0]
        self.assertAlmostEqual(float(proba.sum()), 1.0, places=5)

    def test_predict_proba_all_non_negative(self):
        import numpy as np
        row = [60, 80000, 100000, 2000, 0, 0, 5, 1, 12, 10, 8,
               1.25, 0.0, 4667, 24000]
        x = self.scaler.transform([row])
        proba = self.clf.predict_proba(x)[0]
        self.assertTrue((proba >= 0).all())


if __name__ == "__main__":
    unittest.main()
