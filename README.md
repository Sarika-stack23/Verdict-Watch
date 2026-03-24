# ⚖️ Verdict Watch

**AI-powered bias detection for automated decisions.**

Paste any rejection letter, loan denial, medical triage result, or university rejection — Verdict Watch tells you if bias caused it and what to do next.

---

## How It Works

```
Your decision text
      ↓
Groq Call 1 → Extracts criteria & factors used
      ↓
Groq Call 2 → Detects hidden bias in those factors
      ↓
Groq Call 3 → Generates the fair outcome + next steps
      ↓
Full report shown in UI
```

---

## Setup & Run

```bash
# 1. Clone and set up environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Add your Groq API key
cp .env.example .env
# Edit .env — add your GROQ_API_KEY

# 3. Start the API (Terminal 1)
uvicorn api:app --reload

# 4. Start the UI (Terminal 2)
streamlit run streamlit_app.py
```

Open http://localhost:8501 in your browser.

---

## Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `services.py` | DB models + 3-chain Groq pipeline |
| `api.py` | FastAPI REST endpoints |
| `streamlit_app.py` | Full Streamlit UI |
| `.env.example` | Environment variable template |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyse` | Run full bias analysis |
| GET | `/api/reports` | All past reports |
| GET | `/api/reports/{id}` | Single report |
| GET | `/api/health` | Health check |

---

## Bias Types Detected

- Gender bias
- Age discrimination  
- Racial / ethnic bias
- Geographic redlining
- Name-based ethnicity proxies
- Socioeconomic status bias
- Language / insurance classification bias

---

## Tech Stack

- **FastAPI** — REST API
- **Streamlit** — Frontend UI
- **SQLAlchemy + SQLite** — Zero-config database
- **Groq (Llama 3.3 70B)** — AI pipeline (3 chained calls)
- **httpx** — Async HTTP

---

## Example Decisions to Test

**Job Rejection:**
> "Thank you for applying to the Software Engineer position. After careful review we have decided not to move forward. We felt other candidates were a stronger fit for our team culture at this time."

**Loan Denial:**
> "Your loan application has been declined. Primary reasons: insufficient credit history, residential area risk score, employment sector classification. You may reapply after 6 months."

**Medical Triage:**
> "Based on your intake assessment you have been assigned Priority Level 3. Factors considered: age group, reported pain level, primary language, insurance classification."

---

*Not legal advice. Built for educational and awareness purposes.*