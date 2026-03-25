"""
streamlit_app.py — Verdict Watch V5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Google-quality enterprise upgrade over V3.

V5 New Features:
  • API key strictly from .env — no inline key input (security)
  • File upload (.txt / .pdf) in Analyse tab
  • 3-step animated progress with live step labels
  • Bias phrase highlighting from AI (not regex)
  • Legal frameworks panel (relevant laws cited per case)
  • Confidence breakdown visual (severity matrix)
  • Smart duplicate detection — warns before re-running
  • Feedback / helpfulness rating per report
  • Date-range filter in History
  • CSV file upload in Batch tab
  • Trend chart (daily bias rate) in Dashboard
  • Session analytics counter in sidebar
  • Improved empty states with guided onboarding
  • Settings tab (model info, DB stats, feedback stats)

Run:
  streamlit run streamlit_app.py
"""

import streamlit as st
import services
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import re
import os
import io
import json
from datetime import datetime, date, timedelta
from collections import Counter

# ── optional PDF support
try:
    import fitz as pymupdf  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

services.init_db()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch V5",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# DESIGN SYSTEM — V5
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

:root {
    --bg-base:      #070a10;
    --bg-surface:   #0c1018;
    --bg-elevated:  #111520;
    --bg-card:      #161c28;
    --bg-card-alt:  #1c2230;
    --border:       rgba(255,255,255,0.055);
    --border-med:   rgba(255,255,255,0.10);
    --accent:       #e8ff47;
    --accent-dim:   rgba(232,255,71,0.10);
    --accent-glow:  rgba(232,255,71,0.04);
    --red:          #ff4d4d;
    --red-dim:      rgba(255,77,77,0.10);
    --green:        #3dffa0;
    --green-dim:    rgba(61,255,160,0.09);
    --blue:         #4da6ff;
    --blue-dim:     rgba(77,166,255,0.09);
    --amber:        #ffb84d;
    --amber-dim:    rgba(255,184,77,0.09);
    --purple:       #b084fc;
    --purple-dim:   rgba(176,132,252,0.09);
    --teal:         #3dffe0;
    --teal-dim:     rgba(61,255,224,0.09);
    --text-primary:   #e8ecf4;
    --text-secondary: #7a8599;
    --text-muted:     #3d4558;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 18px;
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: var(--bg-base) !important;
    color: var(--text-primary);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    padding: 4px;
    gap: 2px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 0.85rem;
    color: var(--text-secondary);
    background: transparent;
    border-radius: var(--radius-sm);
    padding: 7px 14px;
    border: none;
    transition: all 0.15s ease;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #070a10 !important;
    font-weight: 700;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* ── Buttons ── */
.stButton > button {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 0.87rem;
    background: var(--accent);
    color: #070a10;
    border: none;
    border-radius: var(--radius-sm);
    padding: 0.58rem 1.5rem;
    width: 100%;
    transition: all 0.18s ease;
    letter-spacing: 0.2px;
}
.stButton > button:hover { opacity: 0.88; transform: translateY(-1px); }
.stButton > button:active { transform: translateY(0); }

/* ── Inputs ── */
.stTextArea textarea {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    line-height: 1.7 !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
}
.stSelectbox > div > div,
.stTextInput > div > div > input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.87rem !important;
}
.stDateInput > div > div > input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 1px dashed var(--border-med) !important;
    border-radius: var(--radius-md) !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
    background: var(--accent-glow) !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1.1rem 1.3rem;
}
[data-testid="metric-container"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.62rem !important;
    letter-spacing: 2.5px !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.9rem !important;
    color: var(--text-primary) !important;
}

/* ── Progress ── */
.stProgress > div > div { background: var(--accent) !important; border-radius: 4px; }

/* ── Download buttons ── */
.stDownloadButton > button {
    background: var(--bg-card) !important;
    color: var(--accent) !important;
    border: 1px solid rgba(232,255,71,0.3) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600;
    border-radius: var(--radius-sm) !important;
    width: 100%;
}
.stDownloadButton > button:hover {
    background: var(--accent-dim) !important;
    border-color: var(--accent) !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    background: var(--bg-card) !important;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
}

/* ═══════════════════════════
   V5 CUSTOM COMPONENTS
══════════════════════════ */

/* Wordmark */
.vw-wordmark {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: -1.5px;
    color: var(--text-primary);
    line-height: 1;
}
.vw-tagline {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-top: 0.4rem;
}
.vw-v5-badge {
    display: inline-block;
    background: linear-gradient(135deg, #e8ff47, #aacc00);
    color: #070a10;
    font-family: 'DM Mono', monospace;
    font-size: 0.57rem;
    font-weight: 600;
    letter-spacing: 2px;
    padding: 3px 8px;
    border-radius: 5px;
    vertical-align: middle;
    margin-left: 10px;
    position: relative;
    top: -6px;
}

/* Verdict banners */
.verdict-bias {
    background: var(--red-dim);
    border: 1px solid var(--red);
    border-radius: var(--radius-lg);
    padding: 1.2rem 2rem;
    text-align: center;
    box-shadow: 0 0 60px rgba(255,77,77,0.08);
}
.verdict-clean {
    background: var(--green-dim);
    border: 1px solid var(--green);
    border-radius: var(--radius-lg);
    padding: 1.2rem 2rem;
    text-align: center;
    box-shadow: 0 0 60px rgba(61,255,160,0.06);
}
.v-icon { font-size: 1.8rem; }
.v-label {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-top: 0.2rem;
}
.verdict-bias .v-label  { color: var(--red); }
.verdict-clean .v-label { color: var(--green); }
.v-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-top: 0.2rem;
    opacity: 0.55;
}
.verdict-bias .v-sub  { color: var(--red); }
.verdict-clean .v-sub { color: var(--green); }

/* Severity badges */
.sev-high   { color: var(--red);   background: var(--red-dim);   border: 1px solid rgba(255,77,77,0.28);   border-radius: 5px; padding: 2px 9px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.sev-medium { color: var(--amber); background: var(--amber-dim); border: 1px solid rgba(255,184,77,0.28); border-radius: 5px; padding: 2px 9px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.sev-low    { color: var(--green); background: var(--green-dim); border: 1px solid rgba(61,255,160,0.28);  border-radius: 5px; padding: 2px 9px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }

/* Info cards */
.info-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem 1.3rem;
    margin-bottom: 0.5rem;
}
.info-card.red    { border-left: 3px solid var(--red); }
.info-card.green  { border-left: 3px solid var(--green); }
.info-card.amber  { border-left: 3px solid var(--amber); }
.info-card.blue   { border-left: 3px solid var(--blue); }
.info-card.purple { border-left: 3px solid var(--purple); }
.info-card.teal   { border-left: 3px solid var(--teal); }
.ic-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.45rem;
}
.ic-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.92rem;
    color: var(--text-primary);
    line-height: 1.6;
}
.ic-value.mono {
    font-family: 'DM Mono', monospace;
    font-size: 0.95rem;
    font-weight: 500;
}

/* Chips */
.chip { display: inline-block; padding: 2px 9px; border-radius: 5px; font-family: 'DM Mono', monospace; font-size: 0.68rem; margin: 2px 2px 2px 0; letter-spacing: 0.5px; }
.chip-red    { background: var(--red-dim);    color: #ff9090; border: 1px solid rgba(255,77,77,0.25); }
.chip-green  { background: var(--green-dim);  color: #80ffd0; border: 1px solid rgba(61,255,160,0.25); }
.chip-blue   { background: var(--blue-dim);   color: #80c4ff; border: 1px solid rgba(77,166,255,0.25); }
.chip-amber  { background: var(--amber-dim);  color: #ffd480; border: 1px solid rgba(255,184,77,0.25); }
.chip-purple { background: var(--purple-dim); color: #d0a8ff; border: 1px solid rgba(176,132,252,0.25); }
.chip-teal   { background: var(--teal-dim);   color: #80fff0; border: 1px solid rgba(61,255,224,0.25); }
.chip-muted  { background: rgba(255,255,255,0.04); color: var(--text-secondary); border: 1px solid var(--border); }

/* Recommendation items */
.rec-item {
    display: flex; gap: 0.85rem; align-items: flex-start;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 0.85rem 1.1rem; margin-bottom: 0.5rem;
}
.rec-num {
    background: var(--accent); color: #070a10;
    border-radius: 5px; min-width: 20px; height: 20px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 600;
    flex-shrink: 0; margin-top: 2px;
}
.rec-text { font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: var(--text-secondary); line-height: 1.55; }

/* Progress steps */
.step-bar { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.step-item {
    flex: 1; background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0.6rem 0.8rem; text-align: center;
}
.step-item.active { border-color: var(--accent); background: var(--accent-dim); }
.step-item.done   { border-color: var(--green);  background: var(--green-dim); }
.step-num { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 2px; }
.step-label { font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: var(--text-secondary); }
.step-item.active .step-label { color: var(--accent); }
.step-item.done   .step-label { color: var(--green); }

/* Duplicate warning */
.dup-warn {
    background: var(--amber-dim); border: 1px solid var(--amber);
    border-radius: var(--radius-md); padding: 0.8rem 1.2rem;
    font-family: 'DM Sans', sans-serif; font-size: 0.87rem; color: var(--amber);
}

/* API key error */
.key-error {
    background: var(--red-dim); border: 1px solid var(--red);
    border-radius: var(--radius-md); padding: 1rem 1.4rem;
    font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: var(--red);
    margin-bottom: 1.2rem;
}
.key-error code {
    background: rgba(255,77,77,0.15); padding: 1px 5px;
    border-radius: 4px; font-family: 'DM Mono', monospace; font-size: 0.82rem;
}

/* Phrase highlight box */
.highlight-box {
    font-family: 'DM Sans', sans-serif; font-size: 0.9rem; line-height: 1.8;
    color: var(--text-secondary); background: var(--bg-card);
    border: 1px solid var(--border); border-radius: var(--radius-md);
    padding: 1.1rem 1.4rem;
}
.highlight-box mark {
    background: rgba(255,77,77,0.2); color: #ff9090;
    border-radius: 3px; padding: 1px 4px;
}

/* Appeal letter */
.appeal-box {
    background: var(--bg-card); border: 1px solid var(--purple);
    border-radius: var(--radius-md); padding: 1.4rem 1.8rem;
    font-family: 'DM Mono', monospace; font-size: 0.8rem;
    line-height: 1.9; color: var(--text-secondary);
    white-space: pre-wrap; box-shadow: 0 0 40px rgba(176,132,252,0.06);
}

/* Feedback bar */
.fb-bar {
    display: flex; gap: 0.6rem; align-items: center;
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 0.7rem 1rem;
}
.fb-label { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 2px; color: var(--text-muted); text-transform: uppercase; margin-right: 0.5rem; }

/* Status pills */
.pill-ok   { display: inline-flex; align-items: center; gap: 5px; background: var(--green-dim); border: 1px solid rgba(61,255,160,0.25); color: var(--green);  border-radius: 99px; padding: 4px 12px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.pill-warn { display: inline-flex; align-items: center; gap: 5px; background: var(--amber-dim); border: 1px solid rgba(255,184,77,0.25); color: var(--amber); border-radius: 99px; padding: 4px 12px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.pill-err  { display: inline-flex; align-items: center; gap: 5px; background: var(--red-dim);   border: 1px solid rgba(255,77,77,0.25);  color: var(--red);   border-radius: 99px; padding: 4px 12px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }

/* Onboarding empty state */
.empty-state {
    text-align: center; padding: 3rem 2rem;
    font-family: 'DM Sans', sans-serif; color: var(--text-muted);
}
.empty-icon  { font-size: 2.5rem; margin-bottom: 0.8rem; }
.empty-title { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.4rem; }
.empty-sub   { font-size: 0.85rem; line-height: 1.6; }

/* Misc */
.sec-label { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.65rem; }
.divider   { border: none; border-top: 1px solid var(--border); margin: 1.4rem 0; }
.compare-header { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.4rem; }
.footer-bar { text-align: center; font-family: 'DM Mono', monospace; font-size: 0.63rem; letter-spacing: 1.5px; color: var(--text-muted); margin-top: 3rem; padding-top: 1.4rem; border-top: 1px solid var(--border); text-transform: uppercase; }

/* Confidence breakdown bar */
.conf-track { background: var(--bg-elevated); border-radius: 4px; height: 6px; overflow: hidden; margin: 4px 0 10px; }
.conf-fill  { height: 100%; border-radius: 4px; transition: width 0.4s ease; }

/* Legal framework item */
.law-item { display: flex; gap: 0.6rem; align-items: flex-start; padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: var(--text-secondary); }
.law-icon { color: var(--teal); flex-shrink: 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

EXAMPLES = [
    {"tag": "Job Application", "emoji": "💼", "type": "job",
     "text": ("Thank you for applying to the Software Engineer position. "
              "After careful review we have decided not to move forward. "
              "We felt other candidates were a stronger fit for our team culture at this time.")},
    {"tag": "Bank Loan",       "emoji": "🏦", "type": "loan",
     "text": ("Your loan application has been declined. Primary reasons: insufficient credit history, "
              "residential area risk score, employment sector classification. "
              "You may reapply after 6 months.")},
    {"tag": "Medical Triage",  "emoji": "🏥", "type": "medical",
     "text": ("Based on your intake assessment you have been assigned Priority Level 3. "
              "Factors considered: age group, reported pain level, primary language, insurance classification.")},
    {"tag": "University",      "emoji": "🎓", "type": "university",
     "text": ("We regret to inform you that your application for admission has not been successful. "
              "Our admissions committee considered zip code region diversity metrics, legacy status, "
              "and extracurricular profile alignment when making this decision.")},
    {"tag": "Housing Rental",  "emoji": "🏠", "type": "other",
     "text": ("After reviewing your rental application we are unable to proceed. "
              "Factors reviewed include your neighbourhood of origin, employment sector, "
              "and family size relative to unit capacity.")},
]

TYPE_LABELS = {
    "job":        "💼 Job Application",
    "loan":       "🏦 Bank Loan",
    "medical":    "🏥 Medical / Triage",
    "university": "🎓 University Admission",
    "other":      "📄 Other",
}

CHIP_CYCLE = ["chip-red", "chip-amber", "chip-blue", "chip-green", "chip-purple", "chip-teal"]
BIAS_DIMS  = ["Gender", "Age", "Racial", "Geographic", "Socioeconomic", "Language", "Insurance"]

BIAS_KW = {
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|housewife|mrs|mr|he|she)\b",
    "Age":           r"\b(age group|senior|junior|young|old|millennial|boomer|retirement|elderly|youth)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|name|surname)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|occupation|class|status)\b",
    "Language":      r"\b(primary language|language|accent|english|bilingual|native speaker)\b",
    "Insurance":     r"\b(insurance|coverage|uninsured|medicaid|medicare|policy|insurance classification)\b",
}

# ─────────────────────────────────────────────
# API KEY GUARD
# ─────────────────────────────────────────────

def _api_key_ok() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())

def _api_key_banner():
    st.markdown(
        '<div class="key-error">⚠️ <strong>GROQ_API_KEY not found.</strong> '
        'Add it to your <code>.env</code> file:<br>'
        '<code style="display:block; margin-top:6px; font-size:0.85rem;">'
        'GROQ_API_KEY=gsk_your_key_here</code><br>'
        'Get a free key at <strong>console.groq.com</strong> then restart the app.</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────

for _k, _v in {
    "session_count":   0,
    "prefill_text":    "",
    "prefill_type":    "job",
    "last_report":     None,
    "last_text":       "",
    "appeal_letter":   None,
    "analysis_step":   0,
    "analysis_label":  "",
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────
# HELPERS — ANALYSIS
# ─────────────────────────────────────────────

def run_analysis(text: str, dtype: str):
    """Run pipeline with step-based progress update."""
    step_placeholder = st.empty()

    def update_step(step: int, label: str):
        st.session_state["analysis_step"]  = step
        st.session_state["analysis_label"] = label
        _render_progress(step_placeholder, step, label)

    try:
        report = services.run_full_pipeline(
            decision_text=text,
            decision_type=dtype,
            progress_callback=update_step,
        )
        st.session_state["session_count"] += 1
        step_placeholder.empty()
        return report, None
    except ValueError as e:
        step_placeholder.empty()
        return None, str(e)
    except Exception as e:
        step_placeholder.empty()
        return None, f"Pipeline error: {str(e)}"


def _render_progress(placeholder, current_step: int, label: str):
    steps = [
        (1, "Extract Criteria"),
        (2, "Detect Bias"),
        (3, "Fair Outcome"),
    ]
    parts = []
    for s_num, s_label in steps:
        if s_num < current_step:
            cls = "done"; icon = "✓"
        elif s_num == current_step:
            cls = "active"; icon = "⟳"
        else:
            cls = ""; icon = str(s_num)
        parts.append(
            f'<div class="step-item {cls}">'
            f'<div class="step-num">STEP {icon}</div>'
            f'<div class="step-label">{s_label}</div></div>'
        )

    placeholder.markdown(
        f'<div class="step-bar">{"".join(parts)}</div>'
        f'<div style="font-family:DM Mono,monospace; font-size:0.72rem; '
        f'color:var(--accent); letter-spacing:1px; margin-bottom:0.5rem;">'
        f'● {label}</div>',
        unsafe_allow_html=True,
    )


def extract_text_from_file(uploaded) -> str | None:
    """Extract text from .txt or .pdf upload."""
    name = uploaded.name.lower()
    if name.endswith(".txt"):
        return uploaded.read().decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        if not PDF_SUPPORT:
            st.warning("PDF support requires PyMuPDF. Run: pip install PyMuPDF")
            return None
        raw = uploaded.read()
        doc = pymupdf.open(stream=raw, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip()
    st.warning(f"Unsupported file type: {uploaded.name}")
    return None

# ─────────────────────────────────────────────
# HELPERS — DISPLAY
# ─────────────────────────────────────────────

def chips_html(items, style="auto"):
    if not items:
        return '<span class="chip chip-muted">None detected</span>'
    return "".join(
        f'<span class="chip {CHIP_CYCLE[i % len(CHIP_CYCLE)] if style == "auto" else style}">{item}</span>'
        for i, item in enumerate(items)
    )


def highlight_text(text: str, bias_phrases: list, bias_types: list) -> str:
    """Highlight AI-identified bias phrases first, then regex fallback."""
    out = text
    # AI phrases (high precision)
    for phrase in bias_phrases:
        if phrase and len(phrase) > 2:
            out = re.sub(
                re.escape(phrase),
                lambda m: f"<mark>{m.group()}</mark>",
                out, flags=re.IGNORECASE,
            )
    # Regex fallback for any bias types not caught by AI phrases
    for bias in bias_types:
        for key, pat in BIAS_KW.items():
            if key.lower() in bias.lower() or bias.lower() in key.lower():
                out = re.sub(pat, lambda m: f"<mark>{m.group()}</mark>",
                             out, flags=re.IGNORECASE)
    return out


def severity_badge(conf: float, bias_found: bool) -> str:
    if not bias_found:
        return '<span class="sev-low">LOW RISK</span>'
    if conf >= 0.75:
        return '<span class="sev-high">HIGH SEVERITY</span>'
    if conf >= 0.45:
        return '<span class="sev-medium">MEDIUM SEVERITY</span>'
    return '<span class="sev-low">LOW SEVERITY</span>'


def confidence_breakdown_html(conf: float, bias_found: bool) -> str:
    pct   = int(conf * 100)
    color = "#ff4d4d" if bias_found else "#3dffa0" if conf < 0.45 else "#ffb84d"
    return (
        f'<div style="font-family:DM Mono,monospace; font-size:0.62rem; '
        f'letter-spacing:2px; color:var(--text-muted); margin-bottom:4px;">CONFIDENCE SCORE</div>'
        f'<div style="font-family:Syne,sans-serif; font-size:2.2rem; font-weight:800; color:{color};">'
        f'{pct}%</div>'
        f'<div class="conf-track"><div class="conf-fill" '
        f'style="width:{pct}%; background:{color};"></div></div>'
        f'<div style="font-family:DM Sans,sans-serif; font-size:0.78rem; color:var(--text-muted);">'
        f'{"High confidence — strong discriminatory signal" if pct >= 75 else "Moderate confidence — possible bias patterns" if pct >= 45 else "Low confidence — limited bias indicators"}'
        f'</div>'
    )


def get_all_reports():
    try:
        return services.get_all_reports()
    except Exception:
        return []

# ─────────────────────────────────────────────
# HELPERS — CHARTS
# ─────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono"),
    margin=dict(l=10, r=10, t=10, b=10),
)


def gauge_chart(value, bias_found):
    color = "#ff4d4d" if bias_found else "#3dffa0"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(value * 100),
        number={"suffix": "%", "font": {"family": "Syne", "size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "transparent",
                     "tickfont": {"color": "#3d4558", "size": 8}},
            "bar": {"color": color, "thickness": 0.2},
            "bgcolor": "#161c28",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  33],  "color": "rgba(61,255,160,0.04)"},
                {"range": [33, 66],  "color": "rgba(255,184,77,0.04)"},
                {"range": [66, 100], "color": "rgba(255,77,77,0.04)"},
            ],
            "threshold": {"line": {"color": color, "width": 2},
                          "thickness": 0.7, "value": value * 100},
        },
    ))
    fig.update_layout(height=170, **CHART_LAYOUT)
    return fig


def radar_chart(all_reports: list):
    dim_counts = {d: 0 for d in BIAS_DIMS}
    for r in all_reports:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower():
                    dim_counts[dim] += 1
    vals   = [dim_counts[d] for d in BIAS_DIMS]
    labels = BIAS_DIMS
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=labels + [labels[0]],
        fill="toself", fillcolor="rgba(232,255,71,0.06)",
        line=dict(color="#e8ff47", width=2),
        marker=dict(color="#e8ff47", size=5),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, color="#3d4558",
                            gridcolor="rgba(255,255,255,0.04)",
                            tickfont=dict(family="DM Mono", size=8, color="#3d4558")),
            angularaxis=dict(color="#7a8599", gridcolor="rgba(255,255,255,0.04)",
                             tickfont=dict(family="DM Mono", size=9, color="#7a8599")),
        ),
        height=300, showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        **{k: v for k, v in CHART_LAYOUT.items() if k not in ("margin",)},
    )
    return fig


def pie_chart(bias_count, clean_count):
    total = bias_count + clean_count or 2
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias Found"],
        values=[max(bias_count, 1), max(clean_count, 1)],
        hole=0.7,
        marker=dict(colors=["#ff4d4d", "#3dffa0"],
                    line=dict(color="#070a10", width=3)),
        textfont=dict(family="DM Mono", size=10), textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:9px'>TOTAL</span>",
        x=0.5, y=0.5,
        font=dict(family="Syne", size=18, color="#e8ecf4"),
        showarrow=False,
    )
    fig.update_layout(
        height=250,
        showlegend=True,
        legend=dict(font=dict(family="DM Mono", size=10, color="#7a8599"),
                    bgcolor="rgba(0,0,0,0)", orientation="h",
                    x=0.5, xanchor="center", y=-0.08),
        **CHART_LAYOUT,
    )
    return fig


def bar_chart(all_types):
    counts = Counter(all_types)
    if not counts:
        counts = {"No data": 1}
    labels, values = zip(*counts.most_common())
    colors = ["#ff4d4d", "#ffb84d", "#4da6ff", "#3dffa0", "#b084fc", "#3dffe0", "#f87171"]
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=colors[:len(labels)], line=dict(width=0)),
        text=list(values), textfont=dict(family="DM Mono", size=10, color="#e8ecf4"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(180, len(labels) * 44 + 50),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                   tickfont=dict(family="DM Mono", size=9, color="#3d4558"), zeroline=False),
        yaxis=dict(tickfont=dict(family="DM Mono", size=9, color="#7a8599"),
                   gridcolor="rgba(0,0,0,0)"),
        bargap=0.4, **CHART_LAYOUT,
    )
    return fig


def trend_chart(trend_data: list):
    if not trend_data:
        return None
    dates      = [d["date"] for d in trend_data]
    bias_rates = [d["bias_rate"] for d in trend_data]
    totals     = [d["total"]     for d in trend_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=totals, name="Total",
        marker=dict(color="rgba(77,166,255,0.15)", line=dict(width=0)),
        hovertemplate="%{x}: %{y} analyses<extra></extra>",
        yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=bias_rates, name="Bias Rate %",
        mode="lines+markers",
        line=dict(color="#e8ff47", width=2),
        marker=dict(color="#e8ff47", size=6, line=dict(color="#070a10", width=1.5)),
        hovertemplate="%{x}: %{y}% bias<extra></extra>",
    ))
    fig.update_layout(
        height=240,
        yaxis=dict(title="Bias %", range=[0, 105],
                   tickfont=dict(family="DM Mono", size=8, color="#3d4558"),
                   gridcolor="rgba(255,255,255,0.03)", zeroline=False),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(family="DM Mono", size=8, color="#3d4558")),
        xaxis=dict(tickfont=dict(family="DM Mono", size=8, color="#3d4558")),
        legend=dict(font=dict(family="DM Mono", size=9, color="#7a8599"),
                    bgcolor="rgba(0,0,0,0)", x=0, y=1.1, orientation="h"),
        **CHART_LAYOUT,
    )
    return fig


def histogram_chart(scores):
    if not scores:
        scores = [0]
    fig = go.Figure(go.Histogram(
        x=[s * 100 for s in scores], nbinsx=10,
        marker=dict(color="#e8ff47", opacity=0.65, line=dict(color="#070a10", width=1)),
        hovertemplate="~%{x:.0f}%: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=210,
        xaxis=dict(title=dict(text="Confidence %",
                              font=dict(family="DM Mono", size=9, color="#3d4558")),
                   tickfont=dict(family="DM Mono", size=9, color="#3d4558"),
                   gridcolor="rgba(255,255,255,0.03)"),
        yaxis=dict(tickfont=dict(family="DM Mono", size=9, color="#3d4558"),
                   gridcolor="rgba(255,255,255,0.03)"),
        **CHART_LAYOUT,
    )
    return fig

# ─────────────────────────────────────────────
# HELPERS — EXPORT
# ─────────────────────────────────────────────

def build_txt_report(report, text, dtype):
    recs  = report.get("recommendations", [])
    laws  = report.get("legal_frameworks", [])
    lines = [
        "=" * 66, "      VERDICT WATCH V5 — BIAS ANALYSIS REPORT", "=" * 66,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id', 'N/A')}",
        f"Severity   : {report.get('severity', 'N/A').upper()}", "",
        "── ORIGINAL DECISION ──────────────────────────────────────────",
        text, "",
        "── VERDICT ─────────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence : {int(report.get('confidence_score', 0) * 100)}%", "",
        "── BIAS TYPES ───────────────────────────────────────────────────",
        ", ".join(report.get("bias_types", [])) or "None detected", "",
        "── CHARACTERISTIC AFFECTED ─────────────────────────────────────",
        report.get("affected_characteristic", "N/A"), "",
        "── ORIGINAL OUTCOME ─────────────────────────────────────────────",
        report.get("original_outcome", "N/A"), "",
        "── FAIR OUTCOME ─────────────────────────────────────────────────",
        report.get("fair_outcome", "N/A"), "",
        "── EXPLANATION ──────────────────────────────────────────────────",
        report.get("explanation", "N/A"), "",
        "── NEXT STEPS ───────────────────────────────────────────────────",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    if laws:
        lines += ["", "── RELEVANT LEGAL FRAMEWORKS ────────────────────────────────"]
        for law in laws:
            lines.append(f"  • {law}")
    lines += ["", "=" * 66,
              "  Verdict Watch V5  ·  Groq / Llama 3.3 70B  ·  Not legal advice",
              "=" * 66]
    return "\n".join(lines)


def reports_to_csv(reports: list) -> str:
    rows = [{
        "id":                      r.get("id", ""),
        "created_at":              (r.get("created_at") or "")[:16].replace("T", " "),
        "bias_found":              r.get("bias_found", False),
        "severity":                r.get("severity", ""),
        "confidence_pct":          int(r.get("confidence_score", 0) * 100),
        "bias_types":              "; ".join(r.get("bias_types", [])),
        "bias_phrases":            "; ".join(r.get("bias_phrases", [])),
        "affected_characteristic": r.get("affected_characteristic", ""),
        "original_outcome":        r.get("original_outcome", ""),
        "fair_outcome":            r.get("fair_outcome", ""),
        "explanation":             r.get("explanation", ""),
        "legal_frameworks":        "; ".join(r.get("legal_frameworks", [])),
        "recommendations":         " | ".join(r.get("recommendations", [])),
    } for r in reports]
    return pd.DataFrame(rows).to_csv(index=False)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne,sans-serif; font-size:1rem; font-weight:700; '
        'color:#e8ecf4; line-height:1.2;">⚖️ Verdict Watch '
        '<span style="background:linear-gradient(135deg,#e8ff47,#aacc00); color:#070a10; '
        'font-family:DM Mono,monospace; font-size:0.52rem; padding:2px 6px; border-radius:3px; '
        'letter-spacing:1.5px; vertical-align:middle; position:relative; top:-1px;">V5</span></div>'
        '<div style="font-family:DM Sans,sans-serif; font-size:0.76rem; color:#3d4558; '
        'margin-top:0.25rem; margin-bottom:0.9rem; line-height:1.5;">'
        'AI bias detection · Enterprise edition</div>',
        unsafe_allow_html=True,
    )

    # ── API Key Status (read-only — set in .env)
    if _api_key_ok():
        st.markdown('<div class="pill-ok">● GROQ KEY ACTIVE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pill-err">● GROQ KEY MISSING</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-family:DM Mono,monospace; font-size:0.68rem; color:#7a8599; '
            'margin-top:0.5rem; line-height:1.6;">'
            'Set <code style="background:rgba(255,255,255,0.06); padding:1px 4px; border-radius:3px;">'
            'GROQ_API_KEY</code> in your <code style="background:rgba(255,255,255,0.06); padding:1px 4px; border-radius:3px;">.env</code>'
            ' file and restart.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Session counter
    count = st.session_state.get("session_count", 0)
    total = len(get_all_reports())
    sc1, sc2 = st.columns(2)
    sc1.metric("This Session", count)
    sc2.metric("All Time", total)

    st.markdown("---")

    # ── Quick examples
    st.markdown(
        '<div style="font-family:DM Mono,monospace; font-size:0.58rem; letter-spacing:2.5px; '
        'text-transform:uppercase; color:#3d4558; margin-bottom:0.5rem;">Quick Examples</div>',
        unsafe_allow_html=True,
    )
    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"sb_ex_{ex['type']}_{ex['emoji']}"):
            st.session_state["prefill_text"] = ex["text"]
            st.session_state["prefill_type"] = ex["type"]
            st.rerun()

    st.markdown("---")

    # ── How it works
    st.markdown(
        '<div style="font-family:DM Mono,monospace; font-size:0.58rem; letter-spacing:2.5px; '
        'text-transform:uppercase; color:#3d4558; margin-bottom:0.5rem;">How It Works</div>',
        unsafe_allow_html=True,
    )
    for n, t in [
        ("01", "Paste decision text or upload a file"),
        ("02", "Step 1 — AI extracts criteria"),
        ("03", "Step 2 — Scans 7+ bias dimensions"),
        ("04", "Step 3 — Generates fair outcome + laws"),
        ("05", "Review highlighted bias phrases"),
        ("06", "Download report or generate appeal"),
    ]:
        st.markdown(
            f'<div style="display:flex; gap:0.6rem; margin-bottom:0.5rem;">'
            f'<div style="font-family:DM Mono,monospace; font-size:0.65rem; color:#e8ff47; '
            f'min-width:16px;">{n}</div>'
            f'<div style="font-family:DM Sans,sans-serif; font-size:0.76rem; '
            f'color:#3d4558; line-height:1.4;">{t}</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="vw-wordmark">⚖ Verdict Watch'
    '<span class="vw-v5-badge">V5</span></div>'
    '<div class="vw-tagline">Enterprise-grade bias detection for automated decisions</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

(tab_analyse, tab_dashboard, tab_history,
 tab_compare, tab_batch, tab_settings, tab_about) = st.tabs([
    "⚡ Analyse", "📊 Dashboard", "📋 History",
    "⚖️ Compare", "📦 Batch", "⚙️ Settings", "ℹ About",
])


# ═══════════════════════════════════════════════════════
# TAB 1 — ANALYSE
# ═══════════════════════════════════════════════════════

with tab_analyse:
    if not _api_key_ok():
        _api_key_banner()

    prefill_text = st.session_state.get("prefill_text", "")
    prefill_type = st.session_state.get("prefill_type", "job")

    col_form, col_help = st.columns([3, 1])

    with col_form:
        # ── Input method selector
        input_mode = st.radio(
            "Input method", ["✏️ Paste Text", "📄 Upload File"],
            horizontal=True, label_visibility="collapsed",
        )

        st.markdown('<div class="sec-label" style="margin-top:0.6rem;">Decision Letter</div>',
                    unsafe_allow_html=True)

        if input_mode == "✏️ Paste Text":
            decision_text = st.text_area(
                "text", label_visibility="collapsed",
                value=prefill_text, height=195, key="decision_input",
                placeholder=(
                    "Paste any rejection, denial, or triage result here…\n\n"
                    "Examples: job rejection · loan denial · medical triage · university rejection\n"
                    "Tip: Use sidebar examples to start instantly."
                ),
            )
        else:
            uploaded_file = st.file_uploader(
                "Upload a .txt or .pdf decision file",
                type=["txt", "pdf"],
                label_visibility="collapsed",
                key="file_upload",
            )
            decision_text = ""
            if uploaded_file:
                extracted = extract_text_from_file(uploaded_file)
                if extracted:
                    decision_text = extracted
                    st.markdown(
                        f'<div class="pill-ok" style="margin-bottom:0.6rem;">'
                        f'● {len(decision_text)} chars extracted from {uploaded_file.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview extracted text", expanded=False):
                        st.text(decision_text[:600] + ("…" if len(decision_text) > 600 else ""))

        # ── Type + char count row
        tc1, tc2 = st.columns([2, 1])
        with tc1:
            type_opts = ["job", "loan", "medical", "university", "other"]
            decision_type = st.selectbox(
                "type", label_visibility="collapsed",
                options=type_opts, format_func=lambda x: TYPE_LABELS[x],
                index=type_opts.index(prefill_type) if prefill_type in type_opts else 0,
                key="decision_type",
            )
        with tc2:
            n = len(decision_text.strip())
            ok = n > 50
            st.markdown(
                f'<div style="padding-top:0.72rem; font-family:DM Mono,monospace; font-size:0.68rem; '
                f'color:{"var(--green)" if ok else "var(--red)"};">'
                f'{n} chars {"✓" if ok else "— add more"}</div>',
                unsafe_allow_html=True,
            )

        analyse_btn = st.button("⚡ Run Bias Analysis", key="analyse_btn",
                                disabled=not _api_key_ok())

    with col_help:
        st.markdown(
            '<div class="info-card" style="margin-top:0;">'
            '<div class="ic-label">What we detect</div>'
            '<div style="font-family:DM Mono,monospace; font-size:0.7rem; '
            'color:var(--text-muted); line-height:2;">'
            '◈ Gender bias<br>◈ Age discrimination<br>◈ Racial / ethnic bias<br>'
            '◈ Geographic redlining<br>◈ Name-based proxies<br>◈ Socioeconomic bias<br>'
            '◈ Language discrimination<br>◈ Insurance classification</div></div>',
            unsafe_allow_html=True,
        )

    # ── Analysis execution
    if analyse_btn:
        st.session_state.pop("prefill_text", None)
        st.session_state.pop("prefill_type", None)

        if not decision_text.strip():
            st.warning("⚠️ Paste a decision text or upload a file first.")
        else:
            # Duplicate check
            text_hash = services.hash_text(decision_text)
            cached    = services.find_duplicate(text_hash)
            if cached and not st.session_state.get("force_rerun"):
                st.markdown(
                    '<div class="dup-warn">⚠️ <strong>Identical text detected</strong> — '
                    'this exact decision was analysed before. Showing cached result. '
                    'Clear the text and paste a new one, or click <strong>Re-run anyway</strong> below.</div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔄 Re-run anyway", key="force_rerun_btn"):
                    st.session_state["force_rerun"] = True
                    st.rerun()
                report = cached
                err    = None
            else:
                st.session_state.pop("force_rerun", None)
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                with st.spinner(""):
                    report, err = run_analysis(decision_text, decision_type)

            if err:
                st.error(f"❌ {err}")
                if "GROQ_API_KEY" in err:
                    _api_key_banner()
            elif report:
                bias_found  = report.get("bias_found", False)
                confidence  = report.get("confidence_score", 0.0)
                bias_types  = report.get("bias_types", [])
                bias_phrases = report.get("bias_phrases", [])
                affected    = report.get("affected_characteristic", "")
                orig        = report.get("original_outcome", "N/A")
                fair        = report.get("fair_outcome", "N/A")
                explanation = report.get("explanation", "")
                recs        = report.get("recommendations", [])
                laws        = report.get("legal_frameworks", [])
                severity    = report.get("severity", "low")
                evidence    = report.get("bias_evidence", "")

                # Verdict banner
                st.markdown("<br>", unsafe_allow_html=True)
                if bias_found:
                    st.markdown(
                        '<div class="verdict-bias">'
                        '<div class="v-icon">⚠️</div>'
                        '<div class="v-label">BIAS DETECTED</div>'
                        '<div class="v-sub">Decision shows discriminatory patterns</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="verdict-clean">'
                        '<div class="v-icon">✅</div>'
                        '<div class="v-label">NO BIAS FOUND</div>'
                        '<div class="v-sub">Decision appears free of discriminatory factors</div></div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Row 1: Confidence | Bias types | Outcomes
                r1, r2, r3 = st.columns([1.2, 1.5, 1.5])

                with r1:
                    st.markdown(
                        f'<div class="info-card">'
                        f'{confidence_breakdown_html(confidence, bias_found)}<br>'
                        f'{severity_badge(confidence, bias_found)}</div>',
                        unsafe_allow_html=True,
                    )

                with r2:
                    st.markdown(
                        f'<div class="info-card blue">'
                        f'<div class="ic-label">Bias Types Detected</div>'
                        f'<div class="ic-value">'
                        f'{chips_html(bias_types) if bias_types else "<span class=\'chip chip-green\'>None</span>"}'
                        f'</div>'
                        + (f'<div style="margin-top:0.7rem;">'
                           f'<div class="ic-label">Characteristic Affected</div>'
                           f'<div style="font-family:DM Mono,monospace; font-size:0.88rem; '
                           f'color:var(--amber);">{affected}</div></div>' if affected else "")
                        + '</div>',
                        unsafe_allow_html=True,
                    )
                    if laws:
                        st.markdown(
                            '<div class="info-card teal" style="margin-top:0;">'
                            '<div class="ic-label">⚖ Relevant Law / Frameworks</div>',
                            unsafe_allow_html=True,
                        )
                        for law in laws:
                            st.markdown(
                                f'<div class="law-item">'
                                f'<span class="law-icon">§</span>{law}</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('</div>', unsafe_allow_html=True)

                with r3:
                    st.markdown(
                        f'<div class="info-card red">'
                        f'<div class="ic-label">Original Decision</div>'
                        f'<div class="ic-value mono">{orig.upper()}</div></div>'
                        f'<div class="info-card green">'
                        f'<div class="ic-label">Should Have Been</div>'
                        f'<div class="ic-value">{fair}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if evidence:
                        st.markdown(
                            f'<div class="info-card amber">'
                            f'<div class="ic-label">Bias Evidence</div>'
                            f'<div class="ic-value" style="font-size:0.86rem;">{evidence}</div></div>',
                            unsafe_allow_html=True,
                        )

                # ── Phrase Highlighter (V5: uses AI phrases)
                if decision_text.strip() and (bias_types or bias_phrases):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">🔍 Bias Phrase Highlighter</div>',
                                unsafe_allow_html=True)
                    highlighted = highlight_text(decision_text, bias_phrases, bias_types)
                    st.markdown(
                        f'<div class="highlight-box">{highlighted}</div>'
                        f'<div style="font-family:DM Mono,monospace; font-size:0.6rem; '
                        f'color:var(--text-muted); margin-top:0.4rem; letter-spacing:1px;">'
                        f'HIGHLIGHTED WORDS ARE PROXIES FOR PROTECTED CHARACTERISTICS</div>',
                        unsafe_allow_html=True,
                    )

                # ── Explanation
                if explanation:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">What Happened — Plain English</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="info-card amber">'
                        f'<div class="ic-value">{explanation}</div></div>',
                        unsafe_allow_html=True,
                    )

                # ── Recommendations
                if recs:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">Your Next Steps</div>',
                                unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec-item">'
                            f'<div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )

                # ── Feedback bar (V5 new)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">Was This Analysis Helpful?</div>',
                            unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1, 1, 3])
                with fb1:
                    if st.button("👍 Yes, helpful", key="fb_yes"):
                        if services.save_feedback(report.get("id"), 1):
                            st.success("Thanks for your feedback!")
                with fb2:
                    if st.button("👎 Not helpful", key="fb_no"):
                        if services.save_feedback(report.get("id"), 0):
                            st.info("Feedback noted — we'll improve.")

                # ── Appeal letter
                if bias_found:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">✉️ Appeal Letter Generator</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        '<div style="font-family:DM Sans,sans-serif; font-size:0.83rem; '
                        'color:var(--text-muted); margin-bottom:0.7rem;">'
                        'Generate a formal appeal letter citing the specific bias and relevant laws. '
                        'Fill in <code style="background:rgba(255,255,255,0.06); padding:1px 4px; '
                        'border-radius:3px;">[PLACEHOLDERS]</code> before sending.</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("✉️ Generate Appeal Letter", key="appeal_btn"):
                        with st.spinner("Drafting formal appeal…"):
                            try:
                                letter = services.generate_appeal_letter(
                                    report, decision_text, decision_type
                                )
                                st.session_state["appeal_letter"] = letter
                            except Exception as e:
                                st.error(f"❌ {e}")

                    if st.session_state.get("appeal_letter"):
                        letter = st.session_state["appeal_letter"]
                        st.markdown(
                            f'<div class="appeal-box">{letter}</div>',
                            unsafe_allow_html=True,
                        )
                        al1, _ = st.columns([1, 2])
                        with al1:
                            st.download_button(
                                "📥 Download Appeal Letter",
                                data=letter,
                                file_name=f"appeal_{report.get('id','')[:8]}.txt",
                                mime="text/plain", key="dl_appeal",
                            )

                # ── Download report
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Full Report (.txt)",
                        data=build_txt_report(report, decision_text, decision_type),
                        file_name=f"verdict_v5_{report.get('id','report')[:8]}.txt",
                        mime="text/plain", key="dl_report",
                    )

                st.session_state["last_report"] = report
                st.session_state["last_text"]   = decision_text


# ═══════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ═══════════════════════════════════════════════════════

with tab_dashboard:
    hist = get_all_reports()

    if not hist:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">📊</div>'
            '<div class="empty-title">No data yet</div>'
            '<div class="empty-sub">Run your first analysis in the Analyse tab<br>'
            'to populate the dashboard.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        bias_reps  = [r for r in hist if r.get("bias_found")]
        clean_reps = [r for r in hist if not r.get("bias_found")]
        all_types  = [bt for r in hist for bt in r.get("bias_types", [])]
        scores     = [r.get("confidence_score", 0) for r in hist]
        bias_rate  = len(bias_reps) / len(hist) * 100 if hist else 0
        avg_conf   = sum(scores) / len(scores) * 100 if scores else 0
        top_bias   = Counter(all_types).most_common(1)[0][0] if all_types else "N/A"
        fb_stats   = services.get_feedback_stats()

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Analyses", len(hist))
        m2.metric("Bias Rate",      f"{bias_rate:.0f}%")
        m3.metric("Avg Confidence", f"{avg_conf:.0f}%")
        m4.metric("Top Bias Type",  top_bias)
        m5.metric("Helpful Rating", f"{fb_stats['helpful_pct']}%" if fb_stats["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        # Row 1
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sec-label">Verdicts Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps), len(clean_reps)),
                            use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="sec-label">Bias Types Frequency</div>', unsafe_allow_html=True)
            if all_types:
                st.plotly_chart(bar_chart(all_types),
                                use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No bias types detected yet.")

        # Row 2 — V5: Trend chart
        st.markdown("<br>", unsafe_allow_html=True)
        trend_data = services.get_trend_data()
        if trend_data:
            st.markdown('<div class="sec-label">📈 Daily Bias Rate Trend — New in V5</div>',
                        unsafe_allow_html=True)
            tf = trend_chart(trend_data)
            if tf:
                st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        # Row 3
        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="sec-label">Confidence Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(histogram_chart(scores),
                            use_container_width=True, config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="sec-label">🕸 Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist),
                            use_container_width=True, config={"displayModeBar": False})

        # Characteristics table
        st.markdown("<br>", unsafe_allow_html=True)
        chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
        if chars:
            st.markdown('<div class="sec-label">Affected Characteristics</div>', unsafe_allow_html=True)
            cdf = pd.DataFrame([
                {"Characteristic": k, "Cases": v, "% of Total": f"{v/len(hist)*100:.0f}%"}
                for k, v in Counter(chars).most_common()
            ])
            st.dataframe(cdf, use_container_width=True, hide_index=True)

        # CSV export
        st.markdown("<br>", unsafe_allow_html=True)
        exp1, _ = st.columns([1, 3])
        with exp1:
            st.download_button(
                "📥 Export Full Dashboard Data (.csv)",
                data=reports_to_csv(hist),
                file_name=f"verdict_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_csv",
            )


# ═══════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ═══════════════════════════════════════════════════════

with tab_history:
    hist = get_all_reports()

    if not hist:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">📋</div>'
            '<div class="empty-title">No history yet</div>'
            '<div class="empty-sub">All your analyses will appear here<br>'
            'with full filter and export options.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Filters
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_q = st.text_input("search", label_visibility="collapsed",
                                     placeholder="Search by characteristic or bias type…",
                                     key="history_search")
        with f2:
            filt_v = st.selectbox("verdict", ["All", "Bias Detected", "No Bias"],
                                   label_visibility="collapsed", key="hf_verdict")
        with f3:
            sort_by = st.selectbox("sort",
                ["Newest First", "Oldest First", "Highest Confidence", "Lowest Confidence"],
                label_visibility="collapsed", key="hf_sort")

        # V5: date range filter
        dr1, dr2, _ = st.columns([1, 1, 2])
        with dr1:
            d_from = st.date_input("From date", value=None, key="hf_from",
                                    label_visibility="collapsed")
        with dr2:
            d_to   = st.date_input("To date",   value=None, key="hf_to",
                                    label_visibility="collapsed")

        filtered = hist[:]
        if filt_v == "Bias Detected":
            filtered = [r for r in filtered if r.get("bias_found")]
        elif filt_v == "No Bias":
            filtered = [r for r in filtered if not r.get("bias_found")]
        if search_q:
            sq = search_q.lower()
            filtered = [r for r in filtered
                        if sq in (r.get("affected_characteristic") or "").lower()
                        or any(sq in bt.lower() for bt in r.get("bias_types", []))]
        if d_from:
            filtered = [r for r in filtered
                        if r.get("created_at") and r["created_at"][:10] >= str(d_from)]
        if d_to:
            filtered = [r for r in filtered
                        if r.get("created_at") and r["created_at"][:10] <= str(d_to)]
        if sort_by == "Newest First":
            filtered.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sort_by == "Oldest First":
            filtered.sort(key=lambda r: r.get("created_at") or "")
        elif sort_by == "Highest Confidence":
            filtered.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
        else:
            filtered.sort(key=lambda r: r.get("confidence_score", 0))

        hdr1, hdr2 = st.columns([3, 1])
        with hdr1:
            st.markdown(
                f'<div style="font-family:DM Mono,monospace; font-size:0.65rem; '
                f'color:var(--text-muted); margin-bottom:0.9rem; letter-spacing:1px;">'
                f'SHOWING {len(filtered)} OF {len(hist)} REPORTS</div>',
                unsafe_allow_html=True,
            )
        with hdr2:
            st.download_button(
                "📥 Export CSV",
                data=reports_to_csv(filtered),
                file_name=f"verdict_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="csv_export",
            )

        for r in filtered:
            bias     = r.get("bias_found", False)
            conf     = int(r.get("confidence_score", 0) * 100)
            affected = r.get("affected_characteristic") or "—"
            b_types  = r.get("bias_types", [])
            laws     = r.get("legal_frameworks", [])
            severity = r.get("severity", "")
            created  = (r.get("created_at") or "")[:16].replace("T", " ")

            with st.expander(
                f'{"⚠️ BIAS" if bias else "✅ CLEAN"}  ·  {conf}%  ·  {affected}  ·  {created}',
                expanded=False,
            ):
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.markdown(
                        f'<div class="info-card {"red" if bias else "green"}">'
                        f'<div class="ic-label">Verdict</div>'
                        f'<div class="ic-value mono">{"⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"}</div></div>'
                        f'<div class="info-card blue" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Original Outcome</div>'
                        f'<div class="ic-value mono">{(r.get("original_outcome") or "N/A").upper()}</div></div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    st.markdown(
                        f'<div class="info-card amber">'
                        f'<div class="ic-label">Bias Types</div>'
                        f'<div class="ic-value">{chips_html(b_types) if b_types else "None"}</div></div>'
                        f'<div class="info-card green" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Fair Outcome</div>'
                        f'<div class="ic-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="info-card amber" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Explanation</div>'
                        f'<div class="ic-value" style="font-size:0.86rem;">{r["explanation"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                if laws:
                    st.markdown(
                        f'<div class="info-card teal" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Legal Frameworks</div>'
                        f'<div class="ic-value">{chips_html(laws, "chip-teal")}</div></div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations", [])
                if recs:
                    st.markdown('<div class="sec-label" style="margin-top:0.8rem;">Recommendations</div>',
                                unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec-item"><div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )
                st.caption(f"Report ID: {r.get('id', 'N/A')}  ·  Severity: {severity.upper() or 'N/A'}")


# ═══════════════════════════════════════════════════════
# TAB 4 — COMPARE
# ═══════════════════════════════════════════════════════

with tab_compare:
    if not _api_key_ok():
        _api_key_banner()

    st.markdown(
        '<div style="font-family:DM Sans,sans-serif; font-size:0.9rem; '
        'color:var(--text-muted); margin-bottom:1.2rem;">'
        'Analyse two decisions side-by-side. Compare verdicts, confidence, bias types, '
        'and fair outcomes simultaneously.</div>',
        unsafe_allow_html=True,
    )

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown('<div class="compare-header">Decision A</div>', unsafe_allow_html=True)
        cmp_text1 = st.text_area("Text A", height=140, label_visibility="collapsed",
                                  placeholder="Paste first decision…", key="cmp1")
        cmp_type1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div class="compare-header">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=140, label_visibility="collapsed",
                                  placeholder="Paste second decision…", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type2")

    cmp_btn = st.button("⚡ Compare Both Decisions", key="compare_btn",
                        disabled=not _api_key_ok())

    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Paste text for both decisions.")
        else:
            with st.spinner("Analysing both decisions…"):
                r1, e1 = run_analysis(cmp_text1, cmp_type1)
                r2, e2 = run_analysis(cmp_text2, cmp_type2)

            if e1: st.error(f"Decision A: {e1}")
            if e2: st.error(f"Decision B: {e2}")

            if r1 and r2:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                v1c, v2c = st.columns(2)

                for col, r, lbl in [(v1c, r1, "A"), (v2c, r2, "B")]:
                    with col:
                        bias = r.get("bias_found", False)
                        conf = r.get("confidence_score", 0)
                        st.markdown(
                            f'<div class="{"verdict-bias" if bias else "verdict-clean"}">'
                            f'<div class="v-icon">{"⚠️" if bias else "✅"}</div>'
                            f'<div class="v-label">Decision {lbl}</div>'
                            f'<div class="v-sub">{"BIAS DETECTED" if bias else "NO BIAS FOUND"}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.plotly_chart(gauge_chart(conf, bias),
                                        use_container_width=True, config={"displayModeBar": False})
                        st.markdown(
                            chips_html(r.get("bias_types", [])) + " " + severity_badge(conf, bias),
                            unsafe_allow_html=True,
                        )
                        laws = r.get("legal_frameworks", [])
                        if laws:
                            st.markdown(chips_html(laws, "chip-teal"), unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="info-card green" style="margin-top:0.7rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )

                # Summary
                b1, b2   = r1.get("bias_found"), r2.get("bias_found")
                c1v, c2v = r1.get("confidence_score", 0), r2.get("confidence_score", 0)
                if b1 and b2:
                    winner  = "A" if c1v >= c2v else "B"
                    summary = (f"Both decisions contain bias. Decision {winner} has higher "
                               f"confidence ({int(max(c1v,c2v)*100)}%).")
                elif b1:
                    summary = "Decision A contains bias; Decision B appears fair."
                elif b2:
                    summary = "Decision B contains bias; Decision A appears fair."
                else:
                    summary = "Neither decision shows clear discriminatory patterns."

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(
                    f'<div class="info-card blue">'
                    f'<div class="ic-label">Comparison Summary</div>'
                    f'<div class="ic-value">{summary}</div></div>',
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════
# TAB 5 — BATCH
# ═══════════════════════════════════════════════════════

with tab_batch:
    if not _api_key_ok():
        _api_key_banner()

    st.markdown(
        '<div style="font-family:DM Sans,sans-serif; font-size:0.9rem; '
        'color:var(--text-muted); margin-bottom:1.2rem;">'
        'Analyse multiple decisions at once — paste them separated by '
        '<code style="background:rgba(255,255,255,0.05); padding:1px 6px; '
        'border-radius:4px; font-family:DM Mono,monospace;">---</code>, '
        'or upload a CSV file with a <code style="background:rgba(255,255,255,0.05); '
        'padding:1px 6px; border-radius:4px; font-family:DM Mono,monospace;">text</code> '
        'column. Limit: 10 decisions per run.</div>',
        unsafe_allow_html=True,
    )

    # V5: input mode for batch
    batch_mode = st.radio("Batch mode", ["✏️ Paste Text", "📊 Upload CSV"],
                           horizontal=True, label_visibility="collapsed", key="batch_mode")

    if batch_mode == "✏️ Paste Text":
        batch_text = st.text_area(
            "Batch decisions", height=240, label_visibility="collapsed", key="batch_input",
            placeholder=(
                "Paste first decision…\n---\n"
                "Paste second decision…\n---\n"
                "Paste third decision…"
            ),
        )
        raw_blocks = [b.strip() for b in batch_text.split("---") if b.strip()] if batch_text else []
    else:
        batch_csv = st.file_uploader(
            "Upload CSV with a 'text' column",
            type=["csv"], label_visibility="collapsed", key="batch_csv_upload",
        )
        raw_blocks = []
        if batch_csv:
            try:
                df_upload = pd.read_csv(batch_csv)
                if "text" in df_upload.columns:
                    raw_blocks = df_upload["text"].dropna().tolist()
                    st.markdown(
                        f'<div class="pill-ok">● {len(raw_blocks)} rows loaded from CSV</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.error("❌ CSV must have a column named 'text'")
            except Exception as e:
                st.error(f"❌ Could not read CSV: {e}")

    bc1, bc2 = st.columns([1, 1])
    with bc1:
        batch_type = st.selectbox(
            "Type (all)", ["job","loan","medical","university","other"],
            format_func=lambda x: TYPE_LABELS[x],
            label_visibility="collapsed", key="batch_type",
        )
    with bc2:
        batch_btn = st.button("📦 Run Batch Analysis", key="batch_run",
                               disabled=not _api_key_ok())

    if batch_btn:
        if not raw_blocks:
            st.warning("⚠️ No decisions found.")
        elif len(raw_blocks) > 10:
            st.warning("⚠️ Batch limit is 10 decisions. Please split your input.")
        else:
            progress = st.progress(0)
            results  = []
            status   = st.empty()
            for i, block in enumerate(raw_blocks):
                status.markdown(
                    f'<div style="font-family:DM Mono,monospace; font-size:0.72rem; '
                    f'color:var(--accent);">Analysing {i+1}/{len(raw_blocks)}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(block, batch_type)
                results.append({"text": block, "report": rep, "error": err})
                progress.progress((i+1) / len(raw_blocks))
            progress.empty()
            status.empty()

            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            bias_c  = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            clean_c = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            err_c   = sum(1 for r in results if r["error"])

            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Total",          len(results))
            sm2.metric("Bias Detected",  bias_c)
            sm3.metric("No Bias",        clean_c)
            sm4.metric("Errors",         err_c)

            # Results table
            table_rows = []
            for i, res in enumerate(results, 1):
                rep, error = res["report"], res["error"]
                if error:
                    table_rows.append({"#": i, "Verdict": "ERROR", "Confidence": "—",
                                       "Bias Types": error[:60], "Affected": "—", "Laws": "—"})
                elif rep:
                    table_rows.append({
                        "#":           i,
                        "Verdict":     "⚠ BIAS" if rep.get("bias_found") else "✓ CLEAN",
                        "Confidence":  f"{int(rep.get('confidence_score',0)*100)}%",
                        "Bias Types":  ", ".join(rep.get("bias_types",[])) or "None",
                        "Affected":    rep.get("affected_characteristic") or "—",
                        "Laws":        "; ".join(rep.get("legal_frameworks",[])) or "—",
                    })
            if table_rows:
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            all_batch_reports = [r["report"] for r in results if r["report"]]
            if all_batch_reports:
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Batch Results (.csv)",
                        data=reports_to_csv(all_batch_reports),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="batch_csv_dl",
                    )

            # Detail expanders
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep, error = res["report"], res["error"]
                label = f"Decision {i}"
                if error:
                    label += " — ERROR"
                elif rep:
                    label += f" — {'⚠ BIAS' if rep.get('bias_found') else '✓ CLEAN'} ({int(rep.get('confidence_score',0)*100)}%)"
                with st.expander(label, expanded=False):
                    st.markdown(
                        f'<div class="info-card blue"><div class="ic-label">Decision Text (preview)</div>'
                        f'<div class="ic-value" style="font-size:0.84rem;">{res["text"][:300]}{"…" if len(res["text"])>300 else ""}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if error:
                        st.error(error)
                    elif rep:
                        bias  = rep.get("bias_found", False)
                        btyps = rep.get("bias_types", [])
                        laws  = rep.get("legal_frameworks", [])
                        st.markdown(
                            f'<div class="info-card {"red" if bias else "green"}" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Verdict</div>'
                            f'<div class="ic-value mono">{"⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"}</div></div>'
                            f'<div class="info-card amber" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Bias Types</div>'
                            f'<div class="ic-value">{chips_html(btyps) if btyps else "None"}</div></div>'
                            + (f'<div class="info-card teal" style="margin-top:0.5rem;">'
                               f'<div class="ic-label">Legal Frameworks</div>'
                               f'<div class="ic-value">{chips_html(laws,"chip-teal")}</div></div>' if laws else "")
                            + f'<div class="info-card green" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{rep.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )


# ═══════════════════════════════════════════════════════
# TAB 6 — SETTINGS  (V5 New)
# ═══════════════════════════════════════════════════════

with tab_settings:
    st.markdown(
        '<div style="font-family:Syne,sans-serif; font-size:1.2rem; font-weight:800; '
        'color:var(--text-primary); margin-bottom:0.3rem;">Settings & System Info</div>'
        '<div style="font-family:DM Sans,sans-serif; font-size:0.85rem; '
        'color:var(--text-muted); margin-bottom:1.5rem;">'
        'Verdict Watch V5 configuration overview.</div>',
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns(2)

    with s1:
        st.markdown('<div class="sec-label">API Configuration</div>', unsafe_allow_html=True)
        key_set = _api_key_ok()
        st.markdown(
            f'<div class="info-card {"green" if key_set else "red"}">'
            f'<div class="ic-label">Groq API Key</div>'
            f'<div class="ic-value mono">{"● SET (from .env)" if key_set else "● NOT SET — add to .env"}</div></div>'
            f'<div class="info-card blue">'
            f'<div class="ic-label">Model</div>'
            f'<div class="ic-value mono">llama-3.3-70b-versatile</div></div>'
            f'<div class="info-card">'
            f'<div class="ic-label">Temperature</div>'
            f'<div class="ic-value mono">0.1 (deterministic)</div></div>'
            f'<div class="info-card">'
            f'<div class="ic-label">Max Retries</div>'
            f'<div class="ic-value mono">3 × exponential backoff</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-label" style="margin-top:1rem;">PDF Support</div>',
                    unsafe_allow_html=True)
        st.markdown(
            f'<div class="info-card {"green" if PDF_SUPPORT else "amber"}">'
            f'<div class="ic-label">PyMuPDF</div>'
            f'<div class="ic-value mono">{"● INSTALLED" if PDF_SUPPORT else "● NOT INSTALLED — run: pip install PyMuPDF"}</div></div>',
            unsafe_allow_html=True,
        )

    with s2:
        st.markdown('<div class="sec-label">Database Stats</div>', unsafe_allow_html=True)
        all_r = get_all_reports()
        fb    = services.get_feedback_stats()
        st.markdown(
            f'<div class="info-card">'
            f'<div class="ic-label">Total Reports</div>'
            f'<div class="ic-value mono">{len(all_r)}</div></div>'
            f'<div class="info-card">'
            f'<div class="ic-label">Database</div>'
            f'<div class="ic-value mono">{os.getenv("DATABASE_URL", "sqlite:///verdict_watch.db")}</div></div>'
            f'<div class="info-card purple">'
            f'<div class="ic-label">User Feedback Collected</div>'
            f'<div class="ic-value mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-label" style="margin-top:1rem;">V5 Feature Flags</div>',
                    unsafe_allow_html=True)
        flags = [
            ("✅", "Duplicate detection",    "Hash-based, prevents re-analysis"),
            ("✅", "Retry logic",            "3× with exponential backoff"),
            ("✅", "AI bias phrases",        "High-precision phrase extraction"),
            ("✅", "Legal frameworks",       "Relevant laws cited per case"),
            ("✅", "Feedback system",        "Per-report helpfulness ratings"),
            ("✅", "File upload",            ".txt + .pdf (if PyMuPDF installed)"),
            ("✅", "CSV batch upload",       "Batch via CSV file"),
            ("✅", "Trend analytics",        "Daily bias rate over time"),
        ]
        for icon, name, desc in flags:
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:5px 0; border-bottom:1px solid var(--border); '
                f'font-family:DM Mono,monospace; font-size:0.72rem;">'
                f'<span style="color:var(--green);">{icon} {name}</span>'
                f'<span style="color:var(--text-muted);">{desc}</span></div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════
# TAB 7 — ABOUT
# ═══════════════════════════════════════════════════════

with tab_about:
    ab1, ab2 = st.columns([1.6, 1])

    with ab1:
        st.markdown(
            '<div style="font-family:Syne,sans-serif; font-size:1.4rem; font-weight:800; '
            'color:var(--text-primary); margin-bottom:0.5rem;">What is Verdict Watch?</div>'
            '<div style="font-family:DM Sans,sans-serif; font-size:0.9rem; '
            'color:var(--text-muted); line-height:1.85; margin-bottom:1.4rem;">'
            'Verdict Watch V5 is an enterprise-grade AI system that analyses automated decisions — '
            'job rejections, loan denials, medical triage results, university admissions — '
            'for hidden bias against protected characteristics. '
            'A 3-step AI pipeline powered by Groq and Llama 3.3 70B extracts criteria, '
            'detects discriminatory patterns with specific phrase evidence, cites relevant '
            'legal frameworks, and generates the fair outcome the person deserved.'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-label">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        bias_info = [
            ("Gender Bias",              "Decisions influenced by gender, name, or parental status"),
            ("Age Discrimination",        "Unfair weighting of age group or seniority proxies"),
            ("Racial / Ethnic Bias",      "Name-based or national-origin ethnic profiling"),
            ("Geographic Redlining",      "Residential area, zip code, or district used as proxy"),
            ("Socioeconomic Bias",        "Employment sector or credit history over-weighting"),
            ("Language Discrimination",   "Primary language used against applicants"),
            ("Insurance Classification",  "Insurance tier used to rank medical priority"),
        ]
        for name, desc in bias_info:
            st.markdown(
                f'<div class="info-card blue" style="margin-bottom:0.4rem;">'
                f'<div class="ic-label">{name}</div>'
                f'<div class="ic-value" style="font-size:0.86rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="sec-label">V5 Changelog</div>', unsafe_allow_html=True)
        v5_feats = [
            ("🔐", ".env-only API key",       "No inline key input — enterprise security"),
            ("📄", "File upload",             ".txt and .pdf decision letter support"),
            ("⟳",  "Step-by-step progress",  "Live 3-step pipeline progress display"),
            ("🎯", "AI bias phrases",         "Exact phrases flagged by AI, not just regex"),
            ("⚖️", "Legal frameworks",        "Relevant laws cited per case (V5)"),
            ("📐", "Confidence breakdown",    "Visual bar + plain-English explanation"),
            ("🔁", "Duplicate detection",     "SHA-256 hash — skip re-running same text"),
            ("👍", "Feedback rating",         "Per-report helpfulness ratings stored in DB"),
            ("📅", "Date range filter",       "Filter history by date window"),
            ("📊", "CSV batch upload",        "Upload CSV file for bulk analysis"),
            ("📈", "Trend chart",             "Daily bias rate over time in dashboard"),
            ("♻️", "Retry logic",             "3× retries with exponential backoff"),
            ("⚙️", "Settings tab",            "System info, DB stats, feature flags"),
            ("📝", "Structured logging",      "Enterprise-grade log output"),
        ]
        for icon, name, desc in v5_feats:
            st.markdown(
                f'<div class="info-card purple" style="margin-bottom:0.35rem;">'
                f'<div class="ic-label">{icon} {name}</div>'
                f'<div class="ic-value" style="font-size:0.84rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Tech Stack</div>', unsafe_allow_html=True)
        stack = [
            ("⚡ Groq",           "LLM inference engine"),
            ("🦙 Llama 3.3 70B",  "Language model"),
            ("🎈 Streamlit",      "Full-stack UI — no server needed"),
            ("🗄️ SQLAlchemy/SQLite","Persistent local database"),
            ("📊 Plotly",         "Interactive charts"),
            ("📄 PyMuPDF",        "PDF text extraction (optional)"),
        ]
        for name, desc in stack:
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; '
                f'font-family:DM Mono,monospace; font-size:0.72rem; '
                f'padding:5px 0; border-bottom:1px solid var(--border);">'
                f'<span style="color:var(--text-primary);">{name}</span>'
                f'<span style="color:var(--text-muted);">{desc}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="info-card amber">'
            '<div class="ic-label">⚠ Disclaimer</div>'
            '<div class="ic-value" style="font-size:0.84rem;">'
            'Not legal advice. Built for educational and awareness purposes only. '
            'Consult a qualified legal professional for formal discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="footer-bar">'
    'Verdict Watch V5  ·  Groq / Llama 3.3 70B  ·  Enterprise Edition  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)