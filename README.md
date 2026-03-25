# ⚖️ Verdict Watch V7 — Enterprise Edition

**AI-powered bias detection for automated decisions.**  
Paste any rejection letter, loan denial, medical triage, or university rejection — Verdict Watch tells you if bias caused it and what to do next.

> V7 brings a full **Google Material Design 3** enterprise aesthetic and fixes the `text_hash` schema migration error from V5→V6 upgrades.

---

## Quick Start

```bash
# 1. Clone and set up environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Add your Groq API key
cp .env.example .env
# Edit .env — add GROQ_API_KEY=gsk_...

# 3. Start the API (Terminal 1)
uvicorn api:app --reload

# 4. Start the UI (Terminal 2)
streamlit run streamlit_app.py
```

Open **http://localhost:8501** in your browser.

---

## What's New in V7

| Fix / Feature | Details |
|---|---|
| 🔧 **Schema Migration Fix** | `text_hash` column auto-added via `PRAGMA table_info` — no more `OperationalError` |
| 🎨 **Material Design 3** | Full Google enterprise token system (surface, container, tonal) |
| ⭕ **SVG Confidence Ring** | Animated arc ring with MD3 colour tokens |
| 📱 **Google Top App Bar** | Sticky header with logo mark and version chip |
| 🃏 **MD3 Card Elevation** | `filled-error`, `filled-success`, `tonal`, `outlined` card variants |
| 🔵 **Google Typography** | Google Sans Display / Google Sans / Google Sans Mono |
| 📊 **MD3 Plotly Charts** | All charts re-styled with Google colour ramp |

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

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies |
| `services.py` | DB models + 3-chain Groq pipeline + V7 migration |
| `api.py` | FastAPI REST endpoints |
| `streamlit_app.py` | Full Streamlit UI — Material Design 3 |
| `.env.example` | Environment variable template |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyse` | Run full bias analysis |
| GET | `/api/reports` | All past reports |
| GET | `/api/reports/{id}` | Single report |
| GET | `/api/health` | Health check |

---

## Bias Types Detected

- Gender bias & parental status
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
- **Material Design 3** — Google enterprise design system
- **Plotly** — Interactive charts

---

*Not legal advice. Built for educational and awareness purposes.*