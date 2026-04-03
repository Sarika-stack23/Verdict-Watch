# ⚖️ Verdict Watch V15 — AI Governance Edition

**AI-powered bias detection and governance for automated decisions.**  
Paste any rejection letter, loan denial, medical triage, or university rejection — Verdict Watch runs a full 5-step AI governance pipeline to detect bias, audit fairness, generate an explainability trace, and produce the fair outcome the applicant deserved.

> Built for **Solution Challenge 2026 — Unbiased AI Decision** · Powered by **Google Gemini**

---

## Quick Start

```bash
# 1. Clone and set up environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Add your API keys
cp env.example .env
# Edit .env — add GEMINI_API_KEY and GROQ_API_KEY

# 3. Start the API (Terminal 1)
uvicorn api:app --reload

# 4. Start the UI (Terminal 2)
streamlit run streamlit_app.py
```

Open **http://localhost:8501** in your browser.

---

## The 5-Step AI Governance Pipeline

```
Decision text input
      ↓
STEP 0 — Pre-decision scan
  → Which protected characteristics are present?
  → Assign influence weights (0–100%) to each
      ↓
STEP 1 — Criteria extraction
  → What factors drove this decision?
      ↓
STEP 2 — Bias detection (7 dimensions)
  → Gender, Age, Racial, Geographic, Socioeconomic, Language, Insurance
      ↓
STEP 3 — Fair outcome + legal frameworks
  → What should the outcome have been?
  → Which laws were violated? (Title VII, Fair Housing Act, ADEA…)
      ↓
STEP 4 — Fairness audit (counterfactual parity)
  → Would this decision have changed for a different gender/age/name?
  → Demographic parity score per characteristic (0–100)
  → Overall fairness score + verdict
      ↓
STEP 5 — Explainability trace
  → Phrase-by-phrase reasoning chain
  → Each phrase mapped to the characteristic it triggers and the law it violates
  → Retroactive correction: how to fix this specific decision now
      ↓
Full report: bias verdict, fairness score, appeal letter, next steps
```

---

## What's New in V15 (AI Governance Edition)

| Feature | Details |
|---|---|
| ◈ **Pre-decision scan** | Scans decision text before analysis — identifies which protected characteristics are present and how strongly each influenced the decision |
| ◈ **Fairness Audit** | Counterfactual parity testing across demographics — overall fairness score (0–100) with demographic breakdown |
| ◈ **Explainability Trace** | Phrase-level reasoning chain — every biased phrase mapped to the characteristic it triggers and the law it violates |
| ◈ **Retroactive Correction** | Specific, actionable correction for the exact decision analysed |
| ◈ **Fairness Metrics Dashboard** | Aggregate governance view across all past decisions — parity scores, verdict distribution, characteristic weights |
| ◈ **Governance API** | New endpoints: `/api/fairness`, `/api/audit/batch`, `/api/governance/report` |
| ◈ **Cloud Run ready** | Dockerfile + cloudbuild.yaml for one-command Google Cloud Run deployment |

---

## AI Governance Layer

The core of V15 is the AI governance layer — the combination of Steps 0, 4, and 5:

- **Pre-model data audit** (Step 0): Before any decision is made, identify which protected characteristics are embedded in the decision text and how heavily they were weighted. This answers: *was the data itself biased?*

- **Post-decision audit** (Steps 4+5): After the decision, run counterfactual fairness testing and generate an explainability trace. This answers: *was this specific decision applied fairly, and can we prove it?*

- **Retroactive correction**: Every report includes a specific correction for the exact decision — not just "this was biased" but "here is what should have happened and how to fix it now."

---

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `services.py` | DB models + 5-step Gemini pipeline + V15 governance |
| `api.py` | FastAPI REST endpoints incl. governance layer |
| `streamlit_app.py` | Full Streamlit UI — governance panels + Fairness Metrics |
| `Dockerfile` | Container for Google Cloud Run |
| `cloudbuild.yaml` | Google Cloud Build + Cloud Run deployment pipeline |
| `env.example` | Environment variable template |
| `DEMO_SCRIPT.txt` | 3-minute demo script for submission video |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyse` | Run full 5-step governance pipeline |
| GET | `/api/fairness` | Aggregate fairness metrics across all reports |
| GET | `/api/fairness/{id}` | Fairness audit for a single report |
| POST | `/api/audit/batch` | Batch fairness audit on multiple decisions |
| GET | `/api/governance/report` | Full governance summary for presentation |
| GET | `/api/reports` | All past reports |
| GET | `/api/reports/{id}` | Single report |
| GET | `/api/providers` | AI provider health check |
| GET | `/api/health` | Health check |

---

## Deploy to Google Cloud Run

```bash
# One command — deploys to Mumbai region (asia-south1)
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY="your_key",_GROQ_API_KEY="your_key"
```

---

## Bias Dimensions Detected

| Dimension | What it looks for |
|---|---|
| Gender | Gender, name, parental status |
| Age | Age group, generational terms |
| Racial / Ethnic | Name-based origin proxies, nationality |
| Geographic | Zip code, postcode, residential area as proxy |
| Socioeconomic | Employment sector, occupation, income class |
| Language | Primary language used against applicants |
| Insurance | Insurance tier or classification as proxy |

---

## Tech Stack

- **Google Gemini** — Primary AI (all 5 pipeline steps)
- **Groq / Llama 3.3 70B** — Fallback AI
- **FastAPI** — REST API
- **Streamlit** — Web UI
- **SQLAlchemy + SQLite** — Zero-config database
- **Google Cloud Run** — Deployment
- **Plotly** — Interactive charts

---

*Not legal advice. Built for educational awareness and AI governance research.*  
*Solution Challenge 2026 · Build with AI · Unbiased AI Decision*