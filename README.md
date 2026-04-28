# AI Robo-Advisor — LEM StratIQ

An AI-powered investment robo-advisor built with Streamlit, featuring real portfolio optimisation, machine learning risk profiling, and plain-English AI explanations.

## ✨ Key Features

- **10-question risk profiling survey** mapped to a trained Random Forest classifier
- **DeepAtomicIQ portfolio engine** with 6 pre-optimised risk profiles (Robo_P1–P6)
- **Monte Carlo wealth simulation** across 1,000 stochastic paths (10th–90th percentiles)
- **SHAP-based ML explainability** showing which survey answers drove the risk score
- **Claude AI plain-English explanations** translating IQ parameters into investor language
- **Google / LinkedIn OAuth** + email/OTP authentication
- **MongoDB Atlas persistence** for user profiles, assessments, portfolio history, and notifications
- **Real-time market data** via Yahoo Finance with MongoDB caching layer

---

## 🚀 Run Locally

### Prerequisites

- Python 3.10+
- A MongoDB Atlas cluster (free tier is sufficient)
- An Anthropic API key (for Claude explanations)

### Installation

```bash
git clone <repo-url>
cd "Demo_prototype copy"

pip install -r ai_robo_advisor/requirements.txt
```

### Configure Secrets

Copy the example secrets file and fill in your credentials:

```bash
cp ai_robo_advisor/.streamlit/secrets.toml.example ai_robo_advisor/.streamlit/secrets.toml
# Then edit secrets.toml with your real keys
```

### Train the ML Model (first time only)

```bash
python -m ai_robo_advisor.train_model
```

This generates synthetic investor data (8,000 samples) and trains a Random Forest classifier. The resulting artefacts (`model.pkl`, `scaler.pkl`, etc.) are saved to `ai_robo_advisor/`.

### Launch the App

```bash
python -m streamlit run ai_robo_advisor/app.py --server.port 8507
```

Then open [http://localhost:8507](http://localhost:8507) in your browser.

---

## 🧪 Run Tests

```bash
pip install pytest
python -m pytest ai_robo_advisor/tests/ -v
```

The test suite covers:
- **`test_portfolio_engine.py`** — Risk score mapping, Monte Carlo statistics, growth curve shape, numeric sanity checks (35 tests)
- **`test_explainer.py`** — DeepIQ interpretation branches (delta/gamma/regime), AI explanation integration (19 tests)

---

## 🏗️ Architecture

```
Demo_prototype copy/
├── ai_robo_advisor/
│   ├── app.py               ← Streamlit UI layer (navigation, auth, survey, dashboard)
│   ├── portfolio_engine.py  ← DeepAtomicIQ portfolio mapping + Monte Carlo simulation
│   ├── train_model.py       ← Random Forest training on synthetic investor data
│   ├── explainer.py         ← IQ parameter → plain-English translation engine
│   ├── database.py          ← MongoDB Atlas persistence layer
│   ├── backend_api.py       ← FastAPI REST API design blueprint (production architecture)
│   ├── market_updater.py    ← Yahoo Finance market data caching
│   └── tests/
│       ├── test_portfolio_engine.py
│       └── test_explainer.py
├── Robo_P1/ … Robo_P6/     ← Pre-optimised DeepAtomicIQ portfolio weight CSVs
└── requirements.txt
```

### Design Decisions

| Decision | Rationale |
|---|---|
| Streamlit (not React) | Rapid prototyping; Python-native ML/data stack |
| MongoDB Atlas | Schema-flexible for evolving investor profiles; TTL indexes for sessions/OTP |
| Random Forest + SHAP | Interpretable ML — regulators can audit feature importance |
| Monte Carlo simulation | Captures sequence-of-returns risk across 1,000 paths |
| FastAPI `backend_api.py` | Demonstrates production decoupled architecture (REST API layer) |
| bcrypt password hashing | Industry standard; resistant to rainbow table attacks |

### Production Architecture (Intended)

In a production deployment, the Streamlit UI would call the FastAPI service in `backend_api.py`, which would handle ML inference and MongoDB writes independently — decoupling the UI from heavy computation and enabling horizontal scaling.

---

## 🔒 Security

- Passwords hashed with bcrypt (work factor 12)
- OTP codes stored with TTL indexes (auto-expire after 15 minutes)
- Session tokens use `secrets.token_urlsafe()` (cryptographically secure)
- API keys loaded exclusively from `st.secrets` (never hardcoded)
- OAuth state parameter validated to prevent CSRF

---

## 📦 Dependencies

See [`ai_robo_advisor/requirements.txt`](ai_robo_advisor/requirements.txt) for the full list. Core dependencies:

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `anthropic` | Claude AI explanations |
| `pymongo` | MongoDB Atlas client |
| `bcrypt` | Password hashing |
| `scikit-learn` | Random Forest classifier |
| `plotly` | Interactive charts |
| `yfinance` | Real-time market data |
| `streamlit-oauth` | Google / LinkedIn OAuth2 |
