"""
train_model.py
==============
Generates synthetic investor data, trains a Random Forest risk-profile classifier,
saves model artefacts (model.pkl, scaler.pkl, feature_names.pkl, label_encoder.pkl)
into the same directory.

Run once before launching the Streamlit app:
    python3 -m ai_robo_advisor.train_model
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report

ARTEFACT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 42
N_SAMPLES = 8_000


# ─────────────────────────────────────────────
# 1.  Synthetic dataset generation
# ─────────────────────────────────────────────
def generate_dataset(n: int = N_SAMPLES, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age              = rng.integers(18, 76, n)
    income           = rng.integers(15_000, 500_000, n)
    savings          = rng.integers(0, 1_000_000, n)
    monthly_expenses = rng.integers(500, 10_000, n)
    debt             = rng.integers(0, 300_000, n)
    dependents       = rng.integers(0, 6, n)
    horizon          = rng.integers(1, 40, n)       # years
    self_risk        = rng.integers(1, 6, n)        # 1=very conservative … 5=very aggressive
    emergency_months = rng.integers(0, 25, n)
    experience_yrs   = rng.integers(0, 30, n)
    # Behavioural questionnaire aggregate score (5 questions, 1-4 each → range 5-20)
    behav_score      = rng.integers(5, 21, n)

    df = pd.DataFrame({
        "age":              age,
        "income":           income,
        "savings":          savings,
        "monthly_expenses": monthly_expenses,
        "debt":             debt,
        "dependents":       dependents,
        "horizon":          horizon,
        "self_risk":        self_risk,
        "emergency_months": emergency_months,
        "experience_yrs":   experience_yrs,
        "behav_score":      behav_score,
    })

    # ── Derived signals ──────────────────────────────────────────
    df["savings_income_ratio"] = df["savings"] / (df["income"] + 1)
    df["debt_income_ratio"]    = df["debt"]    / (df["income"] + 1)
    df["net_monthly"]          = (df["income"] / 12) - df["monthly_expenses"]
    df["fin_slack"]            = df["emergency_months"] * df["monthly_expenses"]

    # ── Label: risk profile (1-5) ─────────────────────────────
    # Weighted scoring combining horizon, self-risk, behav_score, age, income, debt
    risk_score = (
        0.30 * (df["horizon"]     / 40)         * 5 +
        0.25 * (df["self_risk"]   / 5)           * 5 +
        0.20 * (df["behav_score"] / 20)          * 5 +
        0.10 * ((75 - df["age"])  / 57)          * 5 +
        0.10 * ((df["income"] - 15_000) / 485_000) * 5 +
        0.05 * (1 - df["debt_income_ratio"].clip(0, 1)) * 5
    ).clip(1, 5)

    # Add small noise so boundaries aren't perfectly crisp
    risk_score = risk_score + rng.uniform(-0.4, 0.4, n)
    risk_score = risk_score.clip(1, 5)

    labels = ["Very Conservative", "Conservative", "Moderate", "Aggressive", "Very Aggressive"]
    df["risk_category"] = pd.cut(risk_score, bins=5, labels=labels)

    return df


# ─────────────────────────────────────────────
# 2.  Train
# ─────────────────────────────────────────────
def train(df: pd.DataFrame):
    FEATURES = [
        "age", "income", "savings", "monthly_expenses", "debt", "dependents",
        "horizon", "self_risk", "emergency_months", "experience_yrs", "behav_score",
        "savings_income_ratio", "debt_income_ratio", "net_monthly", "fin_slack",
    ]
    X = df[FEATURES].astype(float)
    y = df["risk_category"].astype(str)

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_enc, test_size=0.2, random_state=SEED, stratify=y_enc
    )

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=5,
        random_state=SEED,
        class_weight="balanced",
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    print("=== Test-set classification report ===")
    print(classification_report(y_test, clf.predict(X_test), target_names=le.classes_))

    # Persist artefacts
    def save(obj, fname):
        path = os.path.join(ARTEFACT_DIR, fname)
        with open(path, "wb") as f:
            pickle.dump(obj, f)
        print(f"  Saved → {path}")

    save(clf,      "model.pkl")
    save(scaler,   "scaler.pkl")
    save(le,       "label_encoder.pkl")
    save(FEATURES, "feature_names.pkl")

    print("\nTraining complete.")
    return clf, scaler, le, FEATURES


if __name__ == "__main__":
    print("Generating synthetic dataset …")
    df = generate_dataset()
    print(f"  {len(df):,} rows, label distribution:")
    print(df["risk_category"].value_counts().sort_index())
    print("\nTraining Random Forest …")
    train(df)
