# ⚖️ Verdict Watch — AI Governance Edition

**AI-powered bias detection and governance for automated decisions.**  
Paste any rejection letter, loan denial, medical triage, or university rejection — Verdict Watch runs a full 6-step AI governance pipeline to detect bias, audit fairness, generate an explainability trace, and produce the fair outcome the applicant deserved.

> Built for **Solution Challenge 2026 — Unbiased AI Decision** · Powered by **Google Gemini + Vertex AI**

---

## Quick Start

```bash
# 1. Clone and set up environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Add your API keys
cp env.example .env
# Edit .env — add GEMINI_API_KEY, GROQ_API_KEY, GOOGLE_CLOUD_PROJECT

# 3. Start the API (Terminal 1)
uvicorn api:app --reload

# 4. Start the UI (Terminal 2)
streamlit run streamlit_app.py
```

Open **http://localhost:8501** in your browser.

---

## The 6-Step AI Governance Pipeline

```
Decision text input
      ↓
STEP 0 — Pre-decision scan  [Gemini]
  → Which protected characteristics are present?
  → Assign influence weights (0–100%) to each
      ↓
STEP 1 — Criteria extraction  [Gemini]
  → What factors drove this decision?
      ↓
STEP 2 — Bias detection — 7 dimensions  [Gemini]
  → Gender, Age, Racial, Geographic, Socioeconomic, Language, Insurance
      ↓
STEP 3 — Fair outcome + legal frameworks  [Gemini]
  → What should the outcome have been?
  → Which laws were violated? (Title VII, Fair Housing Act, ADEA…)
      ↓
STEP 4 — Fairness audit — counterfactual parity  [Vertex AI]
  → Would this decision have changed for a different gender / age / name?
  → Demographic parity score per characteristic (0–100)
  → Overall fairness score + verdict
      ↓
STEP 5 — Explainability trace  [Vertex AI]
  → Phrase-by-phrase reasoning chain
  → Each phrase mapped to the characteristic it triggers and the law it violates
  → Retroactive correction: how to fix this specific decision now
      ↓
Full report: bias verdict, fairness score, appeal letter, next steps
```

Steps 4 and 5 use **Vertex AI** (Google's enterprise AI SDK). All steps fall back to Groq automatically if any Google service is unavailable.

---

## Features

| Feature | Details |
|---|---|
| ◈ **Vertex AI governance** | Steps 4+5 run on `google-cloud-aiplatform` — enterprise Google AI stack |
| ◈ **Pre-decision scan** | Scans text before analysis — identifies protected characteristics and influence weights |
| ◈ **Fairness audit** | Counterfactual parity testing — overall fairness score (0–100) with per-characteristic breakdown |
| ◈ **Explainability trace** | Phrase-level reasoning chain — every biased phrase mapped to characteristic + law violated |
| ◈ **Retroactive correction** | Specific, actionable correction for the exact decision analysed |
| ◈ **Fairness Metrics dashboard** | Aggregate governance view — parity scores, verdict distribution, trend, severity breakdown |
| ◈ **Sample dataset** | 10 realistic past decisions as CSV — download and run batch audit live in demo |
| ◈ **3-tier fallback** | Vertex AI → Gemini API → Groq — auto-fallback at every step |
| ◈ **Governance API** | `/api/fairness`, `/api/audit/batch`, `/api/governance/report`, `/api/sample-dataset` |
| ◈ **Cloud Run deployment** | Vertex AI activates automatically when deployed — no extra keys needed |

---

## AI Governance Layer

The governance layer combines Steps 0, 4, and 5:

**Pre-model data audit (Step 0)** — Before any decision is made, identify which protected characteristics are embedded in the decision text and how heavily each was weighted. This answers: *was the data itself biased?*

**Post-decision audit (Steps 4+5)** — After the decision, run counterfactual fairness testing via Vertex AI and generate a phrase-level explainability trace. This answers: *was this specific decision applied fairly, and can we prove it — phrase by phrase?*

**Retroactive correction** — Every report includes a specific correction for the exact decision analysed, plus the legal frameworks that were violated and three actionable next steps for the affected person.

---

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies including `google-cloud-aiplatform` |
| `services.py` | DB models + 6-step pipeline — Gemini (Steps 0–3) + Vertex AI (Steps 4–5) |
| `api.py` | FastAPI REST endpoints — analysis, governance, sample dataset |
| `streamlit_app.py` | Full Streamlit UI — governance panels, Fairness Metrics, Vertex AI badge |
| `Dockerfile` | Container for Google Cloud Run |
| `cloudbuild.yaml` | One-command Google Cloud Build + Cloud Run deployment |
| `env.example` | Environment variable template |
| `DEMO_SCRIPT.txt` | 3-minute demo script for submission video |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyse` | Run full 6-step governance pipeline |
| GET | `/api/fairness` | Aggregate fairness metrics + trend across all reports |
| GET | `/api/fairness/{id}` | Fairness audit data for a single report |
| POST | `/api/audit/batch` | Batch governance audit on up to 10 decisions |
| GET | `/api/sample-dataset` | Download 10 sample decisions as CSV |
| GET | `/api/governance/report` | Full AI governance summary |
| GET | `/api/reports` | All past reports |
| GET | `/api/reports/{id}` | Single report with full governance data |
| GET | `/api/providers` | Vertex AI / Gemini / Groq provider status |
| GET | `/api/health` | Health check — shows `vertex_ai: true` when enabled |

---

## Deploy to Google Cloud Run

```bash
# One command — deploys to Mumbai region (asia-south1)
# GOOGLE_CLOUD_PROJECT is injected automatically, enabling Vertex AI
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY="your_key",_GROQ_API_KEY="your_key"
```

Vertex AI activates automatically inside Cloud Run — no extra API key needed beyond your GCP project ID.

---

## Bias Dimensions Detected

| Dimension | What it looks for |
|---|---|
| Gender | Gender, name, parental status references |
| Age | Age group, generational terms, seniority proxies |
| Racial / Ethnic | Name-based origin proxies, nationality, ethnicity |
| Geographic | Zip code, postcode, residential area as discriminatory proxy |
| Socioeconomic | Employment sector, occupation category, income class |
| Language | Primary language used against applicants |
| Insurance | Insurance tier or classification used as risk proxy |

---

## Tech Stack

| Component | Role |
|---|---|
| **Google Vertex AI** | Enterprise AI — Fairness Audit + Explainability Trace (Steps 4–5) |
| **Google Gemini** | Primary AI — Pre-scan, Extraction, Detection, Fair Outcome (Steps 0–3) |
| **Groq / Llama 3.3 70B** | Fallback AI — all steps |
| **FastAPI** | REST API |
| **Streamlit** | Web UI |
| **SQLAlchemy + SQLite** | Zero-config database |
| **Google Cloud Run** | Deployment |
| **Plotly** | Interactive charts |

---

## Challenges We Faced

**Challenge: Gemini API returning malformed JSON under load**

During development, we found that Gemini's `gemini-1.5-flash` would occasionally return responses wrapped in markdown code fences (` ```json `) instead of clean JSON, especially when prompts were long. This caused silent parse failures that were hard to debug.

**How we solved it:** We built a response sanitiser that strips markdown fences before parsing, combined with a 3-attempt retry loop with exponential backoff. When all Gemini retries fail, the pipeline automatically falls back to Groq (Llama 3.3 70B), which has more consistent JSON output. This dual-provider architecture turned a reliability problem into a resilience feature — the app now handles API failures gracefully without the user ever seeing an error.

**Technical decision:** We separated the AI provider layer (`_ai_call_json`, `_ai_call_text`) from the pipeline steps so each step can independently choose Gemini, Vertex AI, or Groq. This made the 3-tier fallback chain (Vertex AI → Gemini → Groq) easy to implement and test.

---

## Future Plans

The current build is a working MVP. Here is how we plan to scale it to a larger audience:

| Phase | Plan |
|---|---|
| **Mobile app** | Flutter app so individuals can scan rejection letters from their phone camera and get instant bias analysis |
| **Organisation dashboard** | Multi-user portal for HR teams, banks, and hospitals to audit their AI decision systems at scale across thousands of decisions |
| **Real dataset integration** | Connect to live HR and loan datasets (with consent) to detect systemic bias patterns across an organisation's historical decisions, not just individual cases |
| **Multi-language support** | Extend bias detection to Hindi, Tamil, and other Indian languages so the tool is accessible to non-English speakers affected by automated decisions |
| **Legal integration** | Partner with legal aid organisations to automatically route high-confidence bias cases to pro bono lawyers with the appeal letter pre-generated |
| **Regulatory reporting** | Generate compliance reports in the format required by India's upcoming Digital Personal Data Protection Act and EU AI Act |

The API-first architecture (FastAPI + REST) and Cloud Run deployment mean the core engine can be embedded into any existing HR, banking, or healthcare platform with minimal integration effort.

---

*Not legal advice. Built for educational awareness and AI governance research.*  
*Solution Challenge 2026 · Build with AI · Unbiased AI Decision*