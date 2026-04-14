# Verdict Watch — AI Bias Detection & Legal Aid

Got a rejection you think was unfair? Paste it here. In 25 seconds you'll know if it was discriminatory, which laws were violated, and have a formal appeal letter ready to send.

Built for the **Google Solution Challenge 2026 India** — using Gemini 2.5 Pro, Vertex AI, and a 10-step AI governance pipeline.

---

## What it does

- Detects bias across **9 dimensions**: gender, age, race, geography, name-based proxies, disability, language, insurance classification, socioeconomic status
- Produces a **formal appeal letter** citing exact discriminatory phrases and applicable law
- Calculates **legal filing deadlines** and jurisdiction
- Retrieves **matching case-law precedents**
- Generates a **downloadable PDF report** for lawyers and advocacy organisations
- Works on job rejections, loan denials, medical triage decisions, and university admissions

---

## Quick start

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Add API keys to .env
GEMINI_API_KEY=your_key_here       # Primary — free at aistudio.google.com
GROQ_API_KEY=your_key_here         # Fallback — free at console.groq.com
GOOGLE_CLOUD_PROJECT=your_project  # Optional — Vertex AI governance steps
ANTHROPIC_API_KEY=your_key_here    # Optional — 4th-tier fallback

# 3. Run
streamlit run streamlit_app.py
```

No API key? The **Try it now** tab works in demo mode — showing a realistic pre-built result.

---

## Architecture

```
streamlit_app.py   — UI layer (Streamlit)
api.py             — REST API (FastAPI) for external integrations
services.py        — All logic: 10-step pipeline, AI providers, database
```

**10-step pipeline:**

| Step | What it does | Model |
|------|-------------|-------|
| 0 | Pre-scan protected characteristics | Gemini 2.5 Pro |
| 1 | Extract decision criteria | Gemini 2.0 Flash |
| 2 | Detect bias (9 dimensions) | Gemini 2.0 Flash |
| 3 | Determine fair outcome + laws | Gemini 2.0 Flash |
| 4 | Counterfactual fairness audit | Vertex AI |
| 5 | Explainability trace | Vertex AI |
| 6 | Risk scoring (0–100) | Gemini 2.0 Flash |
| 7 | Auto-generate appeal letter | Gemini 2.5 Pro |
| 8 | Legal timeline + deadlines | Gemini 2.5 Pro |
| 9 | Case-law precedent retrieval | Gemini 2.5 Pro |

**AI fallback chain:** Vertex AI → Gemini → Groq → Claude

---

## Google technologies used

- **Gemini 2.5 Pro** — legal reasoning, appeal letter drafting, precedent retrieval
- **Gemini 2.0 Flash** — fast bias detection, criteria extraction, risk scoring
- **Vertex AI** — counterfactual fairness auditing (Steps 4–5)
- **Gemini Search Grounding** — real case-law retrieval in Step 9

---

## Deployment (Cloud Run)

```bash
gcloud run deploy verdict-watch \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key
```

---

## Not legal advice

This tool is for educational awareness and AI governance research. Consult a qualified solicitor for legal proceedings.