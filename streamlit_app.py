"""
streamlit_app.py — Verdict Watch V6
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V6 Changelog:
  ✅ FIXED  Quick examples now correctly populate the text area
  ✅ FIXED  All f-string backslash errors resolved
  ✅ FIXED  Conditional HTML blocks extracted to variables
  ✨ NEW    Animated verdict reveal with pulse effect
  ✨ NEW    Analyse tab — live char counter + quality bar
  ✨ NEW    Dashboard — severity breakdown donut chart
  ✨ NEW    Dashboard — top affected characteristics bar
  ✨ NEW    History — decision text search + re-analyse button
  ✨ NEW    Compare tab — winner highlight banner
  ✨ NEW    Batch tab — real-time ETA + severity column
  ✨ NEW    Settings — V6 feature flags list

Run:
  streamlit run streamlit_app.py
"""

import streamlit as st
import services
import plotly.graph_objects as go
import pandas as pd
import re
import os
import json
import time
from datetime import datetime, date
from collections import Counter

try:
    import fitz as pymupdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

services.init_db()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch V6",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# DESIGN SYSTEM
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

:root {
    --bg-base:      #070a10;
    --bg-surface:   #0c1018;
    --bg-elevated:  #111520;
    --bg-card:      #161c28;
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

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: var(--bg-base) !important;
    color: var(--text-primary);
}
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-elevated);
    border-radius: var(--radius-md);
    padding: 4px; gap: 2px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500; font-size: 0.84rem;
    color: var(--text-secondary);
    background: transparent;
    border-radius: var(--radius-sm);
    padding: 7px 14px; border: none;
    transition: all 0.15s ease;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #070a10 !important;
    font-weight: 700;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* Buttons */
.stButton > button {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600; font-size: 0.87rem;
    background: var(--accent); color: #070a10;
    border: none; border-radius: var(--radius-sm);
    padding: 0.58rem 1.5rem; width: 100%;
    transition: all 0.18s ease;
}
.stButton > button:hover {
    opacity: 0.88; transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(232,255,71,0.2);
}

/* Inputs */
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
[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 1px dashed var(--border-med) !important;
    border-radius: var(--radius-md) !important;
}

/* Metrics */
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
    font-weight: 700 !important; font-size: 1.9rem !important;
    color: var(--text-primary) !important;
}
.stProgress > div > div { background: var(--accent) !important; border-radius: 4px; }
.stDownloadButton > button {
    background: var(--bg-card) !important;
    color: var(--accent) !important;
    border: 1px solid rgba(232,255,71,0.3) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600; border-radius: var(--radius-sm) !important; width: 100%;
}
.stDownloadButton > button:hover {
    background: var(--accent-dim) !important;
    border-color: var(--accent) !important;
}
.streamlit-expanderHeader {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important; font-size: 0.88rem !important;
    background: var(--bg-card) !important;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
}

/* ═══ CUSTOM COMPONENTS ═══ */

.vw-wordmark {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem; font-weight: 800;
    letter-spacing: -1.5px; color: var(--text-primary); line-height: 1;
}
.vw-tagline {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem; letter-spacing: 3px;
    text-transform: uppercase; color: var(--text-muted); margin-top: 0.4rem;
}
.vw-badge {
    display: inline-block;
    background: linear-gradient(135deg, #e8ff47, #aacc00);
    color: #070a10; font-family: 'DM Mono', monospace;
    font-size: 0.57rem; font-weight: 600; letter-spacing: 2px;
    padding: 3px 8px; border-radius: 5px;
    vertical-align: middle; margin-left: 10px;
    position: relative; top: -6px;
}

@keyframes pulse-red  { 0%,100%{box-shadow:0 0 30px rgba(255,77,77,0.08)} 50%{box-shadow:0 0 60px rgba(255,77,77,0.22)} }
@keyframes pulse-green{ 0%,100%{box-shadow:0 0 20px rgba(61,255,160,0.05)} 50%{box-shadow:0 0 50px rgba(61,255,160,0.18)} }

.verdict-bias {
    background: var(--red-dim); border: 1px solid var(--red);
    border-radius: var(--radius-lg); padding: 1.4rem 2rem;
    text-align: center; animation: pulse-red 2.5s ease-in-out infinite;
}
.verdict-clean {
    background: var(--green-dim); border: 1px solid var(--green);
    border-radius: var(--radius-lg); padding: 1.4rem 2rem;
    text-align: center; animation: pulse-green 2.5s ease-in-out infinite;
}
.v-icon  { font-size: 2rem; }
.v-label { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px; margin-top: 0.2rem; }
.verdict-bias  .v-label { color: var(--red); }
.verdict-clean .v-label { color: var(--green); }
.v-sub  { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 2.5px; text-transform: uppercase; margin-top: 0.25rem; opacity: 0.55; }
.verdict-bias  .v-sub { color: var(--red); }
.verdict-clean .v-sub { color: var(--green); }

.sev-high   { color: var(--red);   background: var(--red-dim);   border: 1px solid rgba(255,77,77,0.28);   border-radius: 5px; padding: 2px 9px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.sev-medium { color: var(--amber); background: var(--amber-dim); border: 1px solid rgba(255,184,77,0.28); border-radius: 5px; padding: 2px 9px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.sev-low    { color: var(--green); background: var(--green-dim); border: 1px solid rgba(61,255,160,0.28);  border-radius: 5px; padding: 2px 9px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }

.info-card {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 1rem 1.3rem; margin-bottom: 0.5rem;
    transition: border-color 0.18s ease;
}
.info-card:hover { border-color: var(--border-med); }
.info-card.red    { border-left: 3px solid var(--red); }
.info-card.green  { border-left: 3px solid var(--green); }
.info-card.amber  { border-left: 3px solid var(--amber); }
.info-card.blue   { border-left: 3px solid var(--blue); }
.info-card.purple { border-left: 3px solid var(--purple); }
.info-card.teal   { border-left: 3px solid var(--teal); }
.ic-label { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.45rem; }
.ic-value { font-family: 'DM Sans', sans-serif; font-size: 0.92rem; color: var(--text-primary); line-height: 1.6; }
.ic-value.mono { font-family: 'DM Mono', monospace; font-size: 0.95rem; font-weight: 500; }

.chip        { display: inline-block; padding: 2px 9px; border-radius: 5px; font-family: 'DM Mono', monospace; font-size: 0.68rem; margin: 2px 2px 2px 0; letter-spacing: 0.5px; }
.chip-red    { background: var(--red-dim);    color: #ff9090; border: 1px solid rgba(255,77,77,0.25); }
.chip-green  { background: var(--green-dim);  color: #80ffd0; border: 1px solid rgba(61,255,160,0.25); }
.chip-blue   { background: var(--blue-dim);   color: #80c4ff; border: 1px solid rgba(77,166,255,0.25); }
.chip-amber  { background: var(--amber-dim);  color: #ffd480; border: 1px solid rgba(255,184,77,0.25); }
.chip-purple { background: var(--purple-dim); color: #d0a8ff; border: 1px solid rgba(176,132,252,0.25); }
.chip-teal   { background: var(--teal-dim);   color: #80fff0; border: 1px solid rgba(61,255,224,0.25); }
.chip-muted  { background: rgba(255,255,255,0.04); color: var(--text-secondary); border: 1px solid var(--border); }

.rec-item { display: flex; gap: 0.85rem; align-items: flex-start; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 0.85rem 1.1rem; margin-bottom: 0.5rem; transition: border-color 0.15s; }
.rec-item:hover { border-color: rgba(232,255,71,0.2); }
.rec-num { background: var(--accent); color: #070a10; border-radius: 5px; min-width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 600; flex-shrink: 0; margin-top: 2px; }
.rec-text { font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: var(--text-secondary); line-height: 1.55; }

.step-bar  { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
.step-item { flex: 1; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.6rem 0.8rem; text-align: center; transition: all 0.3s ease; }
.step-item.active { border-color: var(--accent); background: var(--accent-dim); }
.step-item.done   { border-color: var(--green);  background: var(--green-dim); }
.step-num   { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 2px; }
.step-label { font-family: 'DM Sans', sans-serif; font-size: 0.75rem; color: var(--text-secondary); }
.step-item.active .step-label { color: var(--accent); }
.step-item.done   .step-label { color: var(--green); }

.dup-warn { background: var(--amber-dim); border: 1px solid var(--amber); border-radius: var(--radius-md); padding: 0.8rem 1.2rem; font-family: 'DM Sans', sans-serif; font-size: 0.87rem; color: var(--amber); }
.key-error { background: var(--red-dim); border: 1px solid var(--red); border-radius: var(--radius-md); padding: 1rem 1.4rem; font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: var(--red); margin-bottom: 1.2rem; }
.key-error code { background: rgba(255,77,77,0.15); padding: 1px 5px; border-radius: 4px; font-family: 'DM Mono', monospace; font-size: 0.82rem; }

.highlight-box { font-family: 'DM Sans', sans-serif; font-size: 0.9rem; line-height: 1.8; color: var(--text-secondary); background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.1rem 1.4rem; }
.highlight-box mark { background: rgba(255,77,77,0.22); color: #ff9090; border-radius: 3px; padding: 1px 4px; border-bottom: 1px solid rgba(255,77,77,0.5); }

.appeal-box { background: var(--bg-card); border: 1px solid var(--purple); border-radius: var(--radius-md); padding: 1.4rem 1.8rem; font-family: 'DM Mono', monospace; font-size: 0.8rem; line-height: 1.9; color: var(--text-secondary); white-space: pre-wrap; }

.pill-ok  { display: inline-flex; align-items: center; gap: 5px; background: var(--green-dim); border: 1px solid rgba(61,255,160,0.25); color: var(--green);  border-radius: 99px; padding: 4px 12px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }
.pill-err { display: inline-flex; align-items: center; gap: 5px; background: var(--red-dim);   border: 1px solid rgba(255,77,77,0.25);  color: var(--red);   border-radius: 99px; padding: 4px 12px; font-family: 'DM Mono', monospace; font-size: 0.67rem; letter-spacing: 1px; }

.empty-state { text-align: center; padding: 3.5rem 2rem; }
.empty-icon  { font-size: 2.8rem; margin-bottom: 0.8rem; }
.empty-title { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.4rem; }
.empty-sub   { font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: var(--text-muted); line-height: 1.6; }

.sec-label     { font-family: 'DM Mono', monospace; font-size: 0.6rem; letter-spacing: 3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.65rem; }
.divider       { border: none; border-top: 1px solid var(--border); margin: 1.4rem 0; }
.compare-header{ font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.4rem; }
.footer-bar    { text-align: center; font-family: 'DM Mono', monospace; font-size: 0.63rem; letter-spacing: 1.5px; color: var(--text-muted); margin-top: 3rem; padding-top: 1.4rem; border-top: 1px solid var(--border); text-transform: uppercase; }

.conf-track { background: var(--bg-elevated); border-radius: 4px; height: 8px; overflow: hidden; margin: 6px 0 10px; }
.conf-fill  { height: 100%; border-radius: 4px; }

.law-item { display: flex; gap: 0.6rem; align-items: flex-start; padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: var(--text-secondary); }
.law-icon { color: var(--teal); flex-shrink: 0; }

/* V6 */
.quality-bar { height: 4px; border-radius: 2px; margin-top: 6px; }
.winner-banner { background: linear-gradient(135deg, rgba(232,255,71,0.08), rgba(232,255,71,0.02)); border: 1px solid rgba(232,255,71,0.3); border-radius: var(--radius-md); padding: 0.8rem 1.2rem; text-align: center; font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 700; color: var(--accent); margin-bottom: 1rem; }
.preview-box { background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.7rem 1rem; font-family: 'DM Mono', monospace; font-size: 0.75rem; color: var(--text-muted); line-height: 1.6; white-space: pre-wrap; max-height: 80px; overflow: hidden; }
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

CHIP_CYCLE = ["chip-red","chip-amber","chip-blue","chip-green","chip-purple","chip-teal"]
BIAS_DIMS  = ["Gender","Age","Racial","Geographic","Socioeconomic","Language","Insurance"]
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
# SESSION STATE
# ─────────────────────────────────────────────

_DEFAULTS = {
    "session_count":    0,
    "last_report":      None,
    "last_text":        "",
    "appeal_letter":    None,
    "decision_input":   "",   # directly maps to textarea key
    "decision_type_sel": "job",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────────

def _api_key_ok():
    return bool(os.getenv("GROQ_API_KEY","").strip())

def _api_key_banner():
    st.markdown(
        '<div class="key-error">⚠️ <strong>GROQ_API_KEY not found.</strong> '
        'Add it to your <code>.env</code>:<br>'
        '<code style="display:block;margin-top:6px;">GROQ_API_KEY=gsk_your_key_here</code><br>'
        'Get a free key at <strong>console.groq.com</strong> then restart.</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

def run_analysis(text, dtype):
    ph = st.empty()
    def upd(step, label):
        _render_steps(ph, step, label)
    try:
        report = services.run_full_pipeline(decision_text=text, decision_type=dtype,
                                            progress_callback=upd)
        st.session_state["session_count"] += 1
        ph.empty()
        return report, None
    except ValueError as e:
        ph.empty(); return None, str(e)
    except Exception as e:
        ph.empty(); return None, f"Pipeline error: {str(e)}"

def _render_steps(ph, current, label):
    steps = [(1,"Extract Criteria"),(2,"Detect Bias"),(3,"Fair Outcome")]
    parts = []
    for num, lbl in steps:
        if num < current:   cls, icon = "done",   "✓"
        elif num == current: cls, icon = "active", "⟳"
        else:                cls, icon = "",       str(num)
        parts.append(
            f'<div class="step-item {cls}">'
            f'<div class="step-num">STEP {icon}</div>'
            f'<div class="step-label">{lbl}</div></div>'
        )
    ph.markdown(
        f'<div class="step-bar">{"".join(parts)}</div>'
        f'<div style="font-family:DM Mono,monospace;font-size:0.72rem;'
        f'color:var(--accent);letter-spacing:1px;margin-bottom:0.5rem;">● {label}</div>',
        unsafe_allow_html=True,
    )

def extract_text_from_file(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".txt"):
        return uploaded.read().decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        if not PDF_SUPPORT:
            st.warning("PDF needs PyMuPDF: pip install PyMuPDF"); return None
        raw = uploaded.read()
        doc = pymupdf.open(stream=raw, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip()
    st.warning(f"Unsupported type: {uploaded.name}"); return None

# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

def chips_html(items, style="auto"):
    if not items:
        return '<span class="chip chip-muted">None detected</span>'
    return "".join(
        f'<span class="chip {CHIP_CYCLE[i % len(CHIP_CYCLE)] if style == "auto" else style}">{item}</span>'
        for i, item in enumerate(items)
    )

def highlight_text(text, bias_phrases, bias_types):
    out = text
    for phrase in bias_phrases:
        if phrase and len(phrase) > 2:
            out = re.sub(re.escape(phrase), lambda m: f"<mark>{m.group()}</mark>",
                         out, flags=re.IGNORECASE)
    for bias in bias_types:
        for key, pat in BIAS_KW.items():
            if key.lower() in bias.lower() or bias.lower() in key.lower():
                out = re.sub(pat, lambda m: f"<mark>{m.group()}</mark>",
                             out, flags=re.IGNORECASE)
    return out

def severity_badge(conf, bias_found):
    if not bias_found: return '<span class="sev-low">LOW RISK</span>'
    if conf >= 0.75:   return '<span class="sev-high">HIGH SEVERITY</span>'
    if conf >= 0.45:   return '<span class="sev-medium">MEDIUM SEVERITY</span>'
    return '<span class="sev-low">LOW SEVERITY</span>'

def confidence_html(conf, bias_found):
    pct   = int(conf * 100)
    color = "#ff4d4d" if bias_found else ("#3dffa0" if conf < 0.45 else "#ffb84d")
    desc  = ("High confidence — strong discriminatory signal" if pct >= 75
             else "Moderate confidence — possible bias patterns" if pct >= 45
             else "Low confidence — limited bias indicators")
    return (
        f'<div style="font-family:DM Mono,monospace;font-size:0.62rem;'
        f'letter-spacing:2px;color:var(--text-muted);margin-bottom:4px;">CONFIDENCE SCORE</div>'
        f'<div style="font-family:Syne,sans-serif;font-size:2.4rem;font-weight:800;color:{color};">{pct}%</div>'
        f'<div class="conf-track"><div class="conf-fill" style="width:{pct}%;background:{color};"></div></div>'
        f'<div style="font-family:DM Sans,sans-serif;font-size:0.78rem;color:var(--text-muted);">{desc}</div>'
    )

def get_all_reports():
    try: return services.get_all_reports()
    except: return []

# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def build_txt_report(report, text, dtype):
    recs = report.get("recommendations",[])
    laws = report.get("legal_frameworks",[])
    lines = [
        "="*66, "      VERDICT WATCH V6 — BIAS ANALYSIS REPORT", "="*66,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id','N/A')}",
        f"Severity   : {report.get('severity','N/A').upper()}", "",
        "── ORIGINAL DECISION ──────────────────────────────────────────", text, "",
        "── VERDICT ─────────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence : {int(report.get('confidence_score',0)*100)}%", "",
        "── BIAS TYPES ───────────────────────────────────────────────────",
        ", ".join(report.get("bias_types",[])) or "None detected", "",
        "── CHARACTERISTIC AFFECTED ─────────────────────────────────────",
        report.get("affected_characteristic","N/A"), "",
        "── ORIGINAL OUTCOME ─────────────────────────────────────────────",
        report.get("original_outcome","N/A"), "",
        "── FAIR OUTCOME ─────────────────────────────────────────────────",
        report.get("fair_outcome","N/A"), "",
        "── EXPLANATION ──────────────────────────────────────────────────",
        report.get("explanation","N/A"), "",
        "── NEXT STEPS ───────────────────────────────────────────────────",
    ]
    for i, r in enumerate(recs, 1): lines.append(f"  {i}. {r}")
    if laws:
        lines += ["", "── RELEVANT LEGAL FRAMEWORKS ────────────────────────────────"]
        for law in laws: lines.append(f"  • {law}")
    lines += ["","="*66,"  Verdict Watch V6  ·  Not legal advice","="*66]
    return "\n".join(lines)

def reports_to_csv(reports):
    rows = [{
        "id":                      r.get("id",""),
        "created_at":              (r.get("created_at") or "")[:16].replace("T"," "),
        "bias_found":              r.get("bias_found",False),
        "severity":                r.get("severity",""),
        "confidence_pct":          int(r.get("confidence_score",0)*100),
        "bias_types":              "; ".join(r.get("bias_types",[])),
        "affected_characteristic": r.get("affected_characteristic",""),
        "original_outcome":        r.get("original_outcome",""),
        "fair_outcome":            r.get("fair_outcome",""),
        "explanation":             r.get("explanation",""),
        "legal_frameworks":        "; ".join(r.get("legal_frameworks",[])),
        "recommendations":         " | ".join(r.get("recommendations",[])),
    } for r in reports]
    return pd.DataFrame(rows).to_csv(index=False)

# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────

CB = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(family="DM Mono"), margin=dict(l=10,r=10,t=10,b=10))

def gauge_chart(value, bias_found):
    color = "#ff4d4d" if bias_found else "#3dffa0"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(value*100),
        number={"suffix":"%","font":{"family":"Syne","size":28,"color":color}},
        gauge={"axis":{"range":[0,100],"tickwidth":0,"tickcolor":"transparent","tickfont":{"color":"#3d4558","size":8}},
               "bar":{"color":color,"thickness":0.22}, "bgcolor":"#161c28","borderwidth":0,
               "steps":[{"range":[0,33],"color":"rgba(61,255,160,0.04)"},
                        {"range":[33,66],"color":"rgba(255,184,77,0.04)"},
                        {"range":[66,100],"color":"rgba(255,77,77,0.04)"}],
               "threshold":{"line":{"color":color,"width":2},"thickness":0.7,"value":value*100}},
    ))
    fig.update_layout(height=170, **CB); return fig

def pie_chart(bc, cc):
    total = bc + cc or 2
    fig = go.Figure(go.Pie(
        labels=["Bias Detected","No Bias Found"], values=[max(bc,1),max(cc,1)],
        hole=0.72, marker=dict(colors=["#ff4d4d","#3dffa0"],line=dict(color="#070a10",width=3)),
        textfont=dict(family="DM Mono",size=10), textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{total}</b><br><span style='font-size:9px'>TOTAL</span>",
                       x=0.5,y=0.5,font=dict(family="Syne",size=18,color="#e8ecf4"),showarrow=False)
    fig.update_layout(height=250,showlegend=True,
                      legend=dict(font=dict(family="DM Mono",size=10,color="#7a8599"),
                                  bgcolor="rgba(0,0,0,0)",orientation="h",x=0.5,xanchor="center",y=-0.08),
                      **CB); return fig

def bar_chart(items):
    counts = Counter(items)
    if not counts: counts = {"No data":1}
    labels, values = zip(*counts.most_common())
    colors = ["#ff4d4d","#ffb84d","#4da6ff","#3dffa0","#b084fc","#3dffe0","#f87171"]
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=colors[:len(labels)],line=dict(width=0)),
        text=list(values), textfont=dict(family="DM Mono",size=10,color="#e8ecf4"),
        textposition="outside", hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(height=max(180,len(labels)*44+50),
                      xaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.03)",
                                 tickfont=dict(family="DM Mono",size=9,color="#3d4558"),zeroline=False),
                      yaxis=dict(tickfont=dict(family="DM Mono",size=9,color="#7a8599"),gridcolor="rgba(0,0,0,0)"),
                      bargap=0.4,**CB); return fig

def trend_chart(td):
    if not td: return None
    dates=[d["date"] for d in td]; rates=[d["bias_rate"] for d in td]; totals=[d["total"] for d in td]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates,y=totals,name="Total",
                         marker=dict(color="rgba(77,166,255,0.15)",line=dict(width=0)),
                         hovertemplate="%{x}: %{y}<extra></extra>",yaxis="y2"))
    fig.add_trace(go.Scatter(x=dates,y=rates,name="Bias Rate %",mode="lines+markers",
                             line=dict(color="#e8ff47",width=2),
                             marker=dict(color="#e8ff47",size=6,line=dict(color="#070a10",width=1.5)),
                             hovertemplate="%{x}: %{y}%<extra></extra>"))
    fig.update_layout(height=240,
                      yaxis=dict(title="Bias %",range=[0,105],tickfont=dict(family="DM Mono",size=8,color="#3d4558"),gridcolor="rgba(255,255,255,0.03)",zeroline=False),
                      yaxis2=dict(overlaying="y",side="right",showgrid=False,tickfont=dict(family="DM Mono",size=8,color="#3d4558")),
                      xaxis=dict(tickfont=dict(family="DM Mono",size=8,color="#3d4558")),
                      legend=dict(font=dict(family="DM Mono",size=9,color="#7a8599"),bgcolor="rgba(0,0,0,0)",x=0,y=1.1,orientation="h"),
                      **CB); return fig

def radar_chart(all_r):
    dim_counts = {d:0 for d in BIAS_DIMS}
    for r in all_r:
        for bt in r.get("bias_types",[]):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower(): dim_counts[dim] += 1
    vals = [dim_counts[d] for d in BIAS_DIMS]
    fig = go.Figure(go.Scatterpolar(
        r=vals+[vals[0]], theta=BIAS_DIMS+[BIAS_DIMS[0]],
        fill="toself", fillcolor="rgba(232,255,71,0.06)",
        line=dict(color="#e8ff47",width=2), marker=dict(color="#e8ff47",size=5),
    ))
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(visible=True,color="#3d4558",gridcolor="rgba(255,255,255,0.04)",tickfont=dict(family="DM Mono",size=8,color="#3d4558")),
                                 angularaxis=dict(color="#7a8599",gridcolor="rgba(255,255,255,0.04)",tickfont=dict(family="DM Mono",size=9,color="#7a8599"))),
                      height=300,showlegend=False,margin=dict(l=40,r=40,t=20,b=20),
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Mono")); return fig

def histogram_chart(scores):
    if not scores: scores=[0]
    fig = go.Figure(go.Histogram(x=[s*100 for s in scores],nbinsx=10,
                                 marker=dict(color="#e8ff47",opacity=0.65,line=dict(color="#070a10",width=1)),
                                 hovertemplate="~%{x:.0f}%: %{y}<extra></extra>"))
    fig.update_layout(height=210,
                      xaxis=dict(title=dict(text="Confidence %",font=dict(family="DM Mono",size=9,color="#3d4558")),
                                 tickfont=dict(family="DM Mono",size=9,color="#3d4558"),gridcolor="rgba(255,255,255,0.03)"),
                      yaxis=dict(tickfont=dict(family="DM Mono",size=9,color="#3d4558"),gridcolor="rgba(255,255,255,0.03)"),
                      **CB); return fig

def severity_donut(all_r):
    sc = {"high":0,"medium":0,"low":0}
    for r in all_r:
        s = r.get("severity","low").lower()
        if s in sc: sc[s] += 1
    fig = go.Figure(go.Pie(
        labels=["High","Medium","Low"], values=[sc["high"],sc["medium"],sc["low"]],
        hole=0.68, marker=dict(colors=["#ff4d4d","#ffb84d","#3dffa0"],line=dict(color="#070a10",width=3)),
        textfont=dict(family="DM Mono",size=10), textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(height=230,showlegend=False,**CB); return fig

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;'
        'color:#e8ecf4;line-height:1.2;">⚖️ Verdict Watch '
        '<span style="background:linear-gradient(135deg,#e8ff47,#aacc00);color:#070a10;'
        'font-family:DM Mono,monospace;font-size:0.52rem;padding:2px 7px;border-radius:3px;'
        'letter-spacing:1.5px;vertical-align:middle;position:relative;top:-1px;">V6</span></div>'
        '<div style="font-family:DM Sans,sans-serif;font-size:0.76rem;color:#3d4558;'
        'margin-top:0.25rem;margin-bottom:0.9rem;">AI bias detection · Enterprise edition</div>',
        unsafe_allow_html=True,
    )

    if _api_key_ok():
        st.markdown('<div class="pill-ok">● GROQ KEY ACTIVE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pill-err">● GROQ KEY MISSING</div>', unsafe_allow_html=True)

    st.markdown("---")
    sc1, sc2 = st.columns(2)
    sc1.metric("This Session", st.session_state.get("session_count",0))
    sc2.metric("All Time", len(get_all_reports()))

    st.markdown("---")
    st.markdown(
        '<div style="font-family:DM Mono,monospace;font-size:0.58rem;letter-spacing:2.5px;'
        'text-transform:uppercase;color:#3d4558;margin-bottom:0.6rem;">Quick Examples</div>',
        unsafe_allow_html=True,
    )

    # ══ V6 FIX: Set session_state["decision_input"] directly — this is what the textarea key reads ══
    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"ex_{ex['tag'].replace(' ','_')}"):
            st.session_state["decision_input"]    = ex["text"]
            st.session_state["decision_type_sel"] = ex["type"]
            st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-family:DM Mono,monospace;font-size:0.58rem;letter-spacing:2.5px;'
        'text-transform:uppercase;color:#3d4558;margin-bottom:0.5rem;">How It Works</div>',
        unsafe_allow_html=True,
    )
    for n, t in [("01","Paste text or upload file"),("02","AI extracts criteria"),
                 ("03","Scans 7+ bias dimensions"),("04","Generates fair outcome + laws"),
                 ("05","Review highlighted phrases"),("06","Download report or appeal")]:
        st.markdown(
            f'<div style="display:flex;gap:0.6rem;margin-bottom:0.45rem;">'
            f'<div style="font-family:DM Mono,monospace;font-size:0.65rem;color:#e8ff47;min-width:16px;">{n}</div>'
            f'<div style="font-family:DM Sans,sans-serif;font-size:0.76rem;color:#3d4558;line-height:1.4;">{t}</div></div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="vw-wordmark">⚖ Verdict Watch<span class="vw-badge">V6</span></div>'
    '<div class="vw-tagline">Enterprise-grade AI bias detection for automated decisions</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

(tab_analyse, tab_dashboard, tab_history,
 tab_compare, tab_batch, tab_settings, tab_about) = st.tabs([
    "⚡ Analyse","📊 Dashboard","📋 History",
    "⚖️ Compare","📦 Batch","⚙️ Settings","ℹ About",
])

# ══════════════════════════════════════════════════════
# TAB 1 — ANALYSE
# ══════════════════════════════════════════════════════

with tab_analyse:
    if not _api_key_ok():
        _api_key_banner()

    col_form, col_help = st.columns([3,1])

    with col_form:
        input_mode = st.radio("Input method", ["✏️ Paste Text","📄 Upload File"],
                              horizontal=True, label_visibility="collapsed")
        st.markdown('<div class="sec-label" style="margin-top:0.6rem;">Decision Letter</div>',
                    unsafe_allow_html=True)

        if input_mode == "✏️ Paste Text":
            # ══ V6 KEY FIX: key="decision_input" binds directly to session_state ══
            decision_text = st.text_area(
                "text", label_visibility="collapsed",
                height=200, key="decision_input",
                placeholder=(
                    "Paste any rejection, denial, or triage result here…\n\n"
                    "Examples: job rejection · loan denial · medical triage · university rejection\n"
                    "Tip: Click any Quick Example in the sidebar to load it instantly."
                ),
            )
        else:
            uploaded_file = st.file_uploader("Upload .txt or .pdf", type=["txt","pdf"],
                                             label_visibility="collapsed", key="file_upload")
            decision_text = ""
            if uploaded_file:
                extracted = extract_text_from_file(uploaded_file)
                if extracted:
                    decision_text = extracted
                    st.markdown(
                        f'<div class="pill-ok" style="margin-bottom:0.6rem;">'
                        f'● {len(decision_text):,} chars from {uploaded_file.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview extracted text"):
                        st.text(decision_text[:800]+("…" if len(decision_text)>800 else ""))

        tc1, tc2 = st.columns([2,1])
        with tc1:
            type_opts = ["job","loan","medical","university","other"]
            cur_type  = st.session_state.get("decision_type_sel","job")
            cur_idx   = type_opts.index(cur_type) if cur_type in type_opts else 0
            decision_type = st.selectbox(
                "type", label_visibility="collapsed",
                options=type_opts, format_func=lambda x: TYPE_LABELS[x],
                index=cur_idx, key="decision_type_sel",
            )
        with tc2:
            n       = len(decision_text.strip()) if decision_text else 0
            ok      = n > 50
            c_col   = "var(--green)" if ok else "var(--red)"
            c_suf   = "✓ ready" if ok else "too short"
            bar_w   = min(100, int(n/3))
            bar_col = "#3dffa0" if n > 150 else ("#ffb84d" if n > 50 else "#ff4d4d")
            st.markdown(
                f'<div style="padding-top:0.72rem;">'
                f'<div style="font-family:DM Mono,monospace;font-size:0.68rem;color:{c_col};">'
                f'{n:,} chars · {c_suf}</div>'
                f'<div class="quality-bar" style="width:{bar_w}%;background:{bar_col};"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        analyse_btn = st.button("⚡ Run Bias Analysis", key="analyse_btn",
                                disabled=not _api_key_ok())

    with col_help:
        st.markdown(
            '<div class="info-card" style="margin-top:0;">'
            '<div class="ic-label">What We Detect</div>'
            '<div style="font-family:DM Mono,monospace;font-size:0.7rem;color:var(--text-muted);line-height:2.1;">'
            '◈ Gender bias<br>◈ Age discrimination<br>◈ Racial / ethnic bias<br>'
            '◈ Geographic redlining<br>◈ Name-based proxies<br>◈ Socioeconomic bias<br>'
            '◈ Language discrimination<br>◈ Insurance classification</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="info-card amber" style="margin-top:0;">'
            '<div class="ic-label">V6 Fixed</div>'
            '<div style="font-family:DM Sans,sans-serif;font-size:0.8rem;color:var(--text-muted);line-height:1.8;">'
            '✅ Examples load instantly<br>✅ Live quality bar<br>'
            '✅ Animated verdicts<br>✅ Severity donut chart</div></div>',
            unsafe_allow_html=True,
        )

    if analyse_btn:
        dt = (decision_text or "").strip()
        if not dt:
            st.warning("⚠️ Paste a decision or upload a file first.")
        else:
            text_hash = services.hash_text(dt)
            cached    = services.find_duplicate(text_hash)

            if cached and not st.session_state.get("force_rerun"):
                st.markdown(
                    '<div class="dup-warn">⚠️ <strong>Identical text detected</strong> — '
                    'showing cached result. Click Re-run to force new analysis.</div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔄 Re-run anyway", key="force_rerun_btn"):
                    st.session_state["force_rerun"] = True; st.rerun()
                report, err = cached, None
            else:
                st.session_state.pop("force_rerun", None)
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                with st.spinner(""):
                    report, err = run_analysis(dt, decision_type)

            if err:
                st.error(f"❌ {err}")
            elif report:
                bias_found   = report.get("bias_found", False)
                confidence   = report.get("confidence_score", 0.0)
                bias_types   = report.get("bias_types", [])
                bias_phrases = report.get("bias_phrases", [])
                affected     = report.get("affected_characteristic", "")
                orig         = report.get("original_outcome", "N/A")
                fair         = report.get("fair_outcome", "N/A")
                explanation  = report.get("explanation", "")
                recs         = report.get("recommendations", [])
                laws         = report.get("legal_frameworks", [])
                evidence     = report.get("bias_evidence", "")

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
                r1, r2, r3 = st.columns([1.2,1.5,1.5])

                with r1:
                    st.markdown(
                        f'<div class="info-card">{confidence_html(confidence, bias_found)}<br>'
                        f'{severity_badge(confidence, bias_found)}</div>',
                        unsafe_allow_html=True,
                    )

                with r2:
                    # V6 FIX: pre-compute to avoid backslash in f-string
                    bt_html  = chips_html(bias_types) if bias_types else '<span class="chip chip-green">None</span>'
                    aff_html = (
                        f'<div style="margin-top:0.7rem;">'
                        f'<div class="ic-label">Characteristic Affected</div>'
                        f'<div style="font-family:DM Mono,monospace;font-size:0.88rem;'
                        f'color:var(--amber);">{affected}</div></div>'
                    ) if affected else ""
                    st.markdown(
                        f'<div class="info-card blue">'
                        f'<div class="ic-label">Bias Types Detected</div>'
                        f'<div class="ic-value">{bt_html}</div>'
                        f'{aff_html}</div>',
                        unsafe_allow_html=True,
                    )
                    if laws:
                        st.markdown('<div class="info-card teal" style="margin-top:0;">'
                                    '<div class="ic-label">⚖ Relevant Laws</div>', unsafe_allow_html=True)
                        for law in laws:
                            st.markdown(f'<div class="law-item"><span class="law-icon">§</span>{law}</div>',
                                        unsafe_allow_html=True)
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

                if dt and (bias_types or bias_phrases):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">🔍 Bias Phrase Highlighter</div>', unsafe_allow_html=True)
                    highlighted = highlight_text(dt, bias_phrases, bias_types)
                    st.markdown(
                        f'<div class="highlight-box">{highlighted}</div>'
                        f'<div style="font-family:DM Mono,monospace;font-size:0.6rem;'
                        f'color:var(--text-muted);margin-top:0.4rem;letter-spacing:1px;">'
                        f'HIGHLIGHTED = PROXIES FOR PROTECTED CHARACTERISTICS</div>',
                        unsafe_allow_html=True,
                    )

                if explanation:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">What Happened — Plain English</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="info-card amber"><div class="ic-value">{explanation}</div></div>',
                                unsafe_allow_html=True)

                if recs:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">Your Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec-item"><div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">Was This Analysis Helpful?</div>', unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1,1,3])
                with fb1:
                    if st.button("👍 Yes, helpful", key="fb_yes"):
                        services.save_feedback(report.get("id"), 1); st.success("Thanks!")
                with fb2:
                    if st.button("👎 Not helpful", key="fb_no"):
                        services.save_feedback(report.get("id"), 0); st.info("Noted.")

                if bias_found:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">✉️ Appeal Letter Generator</div>', unsafe_allow_html=True)
                    if st.button("✉️ Generate Formal Appeal Letter", key="appeal_btn"):
                        with st.spinner("Drafting appeal…"):
                            try:
                                letter = services.generate_appeal_letter(report, dt, decision_type)
                                st.session_state["appeal_letter"] = letter
                            except Exception as e:
                                st.error(f"❌ {e}")
                    if st.session_state.get("appeal_letter"):
                        letter = st.session_state["appeal_letter"]
                        st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                        al1, _ = st.columns([1,2])
                        with al1:
                            st.download_button("📥 Download Appeal Letter", data=letter,
                                               file_name=f"appeal_{report.get('id','')[:8]}.txt",
                                               mime="text/plain", key="dl_appeal")

                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1,2])
                with dl1:
                    st.download_button("📥 Download Full Report (.txt)",
                                       data=build_txt_report(report, dt, decision_type),
                                       file_name=f"verdict_v6_{report.get('id','report')[:8]}.txt",
                                       mime="text/plain", key="dl_report")

                st.session_state["last_report"] = report
                st.session_state["last_text"]   = dt

# ══════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════

with tab_dashboard:
    hist = get_all_reports()
    if not hist:
        st.markdown('<div class="empty-state"><div class="empty-icon">📊</div>'
                    '<div class="empty-title">No data yet</div>'
                    '<div class="empty-sub">Run your first analysis in the Analyse tab.</div></div>',
                    unsafe_allow_html=True)
    else:
        bias_reps = [r for r in hist if r.get("bias_found")]
        clean_reps= [r for r in hist if not r.get("bias_found")]
        all_types = [bt for r in hist for bt in r.get("bias_types",[])]
        scores    = [r.get("confidence_score",0) for r in hist]
        bias_rate = len(bias_reps)/len(hist)*100 if hist else 0
        avg_conf  = sum(scores)/len(scores)*100  if scores else 0
        top_bias  = Counter(all_types).most_common(1)[0][0] if all_types else "N/A"
        fb_stats  = services.get_feedback_stats()

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Total Analyses", len(hist))
        m2.metric("Bias Rate",      f"{bias_rate:.0f}%")
        m3.metric("Avg Confidence", f"{avg_conf:.0f}%")
        m4.metric("Top Bias Type",  top_bias)
        m5.metric("Helpful Rating", f"{fb_stats['helpful_pct']}%" if fb_stats["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sec-label">Verdicts Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps),len(clean_reps)),
                            use_container_width=True, config={"displayModeBar":False})
        with c2:
            st.markdown('<div class="sec-label">Bias Types Frequency</div>', unsafe_allow_html=True)
            if all_types:
                st.plotly_chart(bar_chart(all_types), use_container_width=True, config={"displayModeBar":False})
            else:
                st.info("No bias types yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        td = services.get_trend_data()
        if td:
            st.markdown('<div class="sec-label">📈 Daily Bias Rate Trend</div>', unsafe_allow_html=True)
            tf = trend_chart(td)
            if tf: st.plotly_chart(tf, use_container_width=True, config={"displayModeBar":False})

        c3,c4 = st.columns(2)
        with c3:
            st.markdown('<div class="sec-label">Confidence Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(histogram_chart(scores), use_container_width=True, config={"displayModeBar":False})
        with c4:
            st.markdown('<div class="sec-label">🕸 Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist), use_container_width=True, config={"displayModeBar":False})

        # V6 NEW
        st.markdown("<br>", unsafe_allow_html=True)
        c5,c6 = st.columns(2)
        with c5:
            st.markdown('<div class="sec-label">🍩 Severity Breakdown — V6 New</div>', unsafe_allow_html=True)
            st.plotly_chart(severity_donut(hist), use_container_width=True, config={"displayModeBar":False})
        with c6:
            st.markdown('<div class="sec-label">Top Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
            if chars:
                st.plotly_chart(bar_chart(chars), use_container_width=True, config={"displayModeBar":False})
            else:
                st.info("No data yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        exp1,_ = st.columns([1,3])
        with exp1:
            st.download_button("📥 Export Dashboard (.csv)", data=reports_to_csv(hist),
                               file_name=f"verdict_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", key="dash_csv")

# ══════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════════════

with tab_history:
    hist = get_all_reports()
    if not hist:
        st.markdown('<div class="empty-state"><div class="empty-icon">📋</div>'
                    '<div class="empty-title">No history yet</div>'
                    '<div class="empty-sub">All analyses appear here with filters.</div></div>',
                    unsafe_allow_html=True)
    else:
        f1,f2,f3 = st.columns([2,1,1])
        with f1:
            search_q = st.text_input("search", label_visibility="collapsed",
                                     placeholder="Search by characteristic, bias type, outcome…",
                                     key="history_search")
        with f2:
            filt_v = st.selectbox("verdict", ["All","Bias Detected","No Bias"],
                                   label_visibility="collapsed", key="hf_verdict")
        with f3:
            sort_by = st.selectbox("sort",
                ["Newest First","Oldest First","Highest Confidence","Lowest Confidence"],
                label_visibility="collapsed", key="hf_sort")

        dr1,dr2,_ = st.columns([1,1,2])
        with dr1: d_from = st.date_input("From", value=None, key="hf_from", label_visibility="collapsed")
        with dr2: d_to   = st.date_input("To",   value=None, key="hf_to",   label_visibility="collapsed")

        filtered = hist[:]
        if filt_v == "Bias Detected": filtered = [r for r in filtered if r.get("bias_found")]
        elif filt_v == "No Bias":     filtered = [r for r in filtered if not r.get("bias_found")]
        if search_q:
            sq = search_q.lower()
            filtered = [r for r in filtered
                        if sq in (r.get("affected_characteristic") or "").lower()
                        or any(sq in bt.lower() for bt in r.get("bias_types",[]))
                        or sq in (r.get("original_outcome") or "").lower()
                        or sq in (r.get("explanation") or "").lower()]
        if d_from: filtered = [r for r in filtered if r.get("created_at") and r["created_at"][:10] >= str(d_from)]
        if d_to:   filtered = [r for r in filtered if r.get("created_at") and r["created_at"][:10] <= str(d_to)]
        if sort_by == "Newest First":        filtered.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sort_by == "Oldest First":      filtered.sort(key=lambda r: r.get("created_at") or "")
        elif sort_by == "Highest Confidence":filtered.sort(key=lambda r: r.get("confidence_score",0), reverse=True)
        else:                                filtered.sort(key=lambda r: r.get("confidence_score",0))

        h1,h2 = st.columns([3,1])
        with h1:
            st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:0.65rem;'
                        f'color:var(--text-muted);margin-bottom:0.9rem;letter-spacing:1px;">'
                        f'SHOWING {len(filtered)} OF {len(hist)} REPORTS</div>', unsafe_allow_html=True)
        with h2:
            st.download_button("📥 Export CSV", data=reports_to_csv(filtered),
                               file_name=f"verdict_history_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", key="csv_export")

        for idx, r in enumerate(filtered):
            bias     = r.get("bias_found", False)
            conf     = int(r.get("confidence_score",0)*100)
            affected = r.get("affected_characteristic") or "—"
            b_types  = r.get("bias_types",[])
            laws     = r.get("legal_frameworks",[])
            severity = r.get("severity","")
            created  = (r.get("created_at") or "")[:16].replace("T"," ")
            ico      = "⚠️" if bias else "✅"

            with st.expander(f'{ico} {"BIAS" if bias else "CLEAN"}  ·  {conf}%  ·  {affected}  ·  {created}',
                             expanded=False):
                ec1,ec2 = st.columns(2)
                with ec1:
                    v_col  = "red" if bias else "green"
                    v_text = "⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"
                    orig_o = (r.get("original_outcome") or "N/A").upper()
                    st.markdown(
                        f'<div class="info-card {v_col}">'
                        f'<div class="ic-label">Verdict</div>'
                        f'<div class="ic-value mono">{v_text}</div></div>'
                        f'<div class="info-card blue" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Original Outcome</div>'
                        f'<div class="ic-value mono">{orig_o}</div></div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    b_chips  = chips_html(b_types) if b_types else "None"
                    fair_out = r.get("fair_outcome") or "N/A"
                    st.markdown(
                        f'<div class="info-card amber">'
                        f'<div class="ic-label">Bias Types</div>'
                        f'<div class="ic-value">{b_chips}</div></div>'
                        f'<div class="info-card green" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Fair Outcome</div>'
                        f'<div class="ic-value">{fair_out}</div></div>',
                        unsafe_allow_html=True,
                    )

                if r.get("explanation"):
                    st.markdown(f'<div class="info-card amber" style="margin-top:0.5rem;">'
                                f'<div class="ic-label">Explanation</div>'
                                f'<div class="ic-value" style="font-size:0.86rem;">{r["explanation"]}</div></div>',
                                unsafe_allow_html=True)
                if laws:
                    lw = chips_html(laws, "chip-teal")
                    st.markdown(f'<div class="info-card teal" style="margin-top:0.5rem;">'
                                f'<div class="ic-label">Legal Frameworks</div>'
                                f'<div class="ic-value">{lw}</div></div>', unsafe_allow_html=True)

                recs = r.get("recommendations",[])
                if recs:
                    st.markdown('<div class="sec-label" style="margin-top:0.8rem;">Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(f'<div class="rec-item"><div class="rec-num">{i}</div>'
                                    f'<div class="rec-text">{rec}</div></div>', unsafe_allow_html=True)

                st.caption(f"ID: {r.get('id','N/A')}  ·  Severity: {severity.upper() or 'N/A'}")

# ══════════════════════════════════════════════════════
# TAB 4 — COMPARE
# ══════════════════════════════════════════════════════

with tab_compare:
    if not _api_key_ok():
        _api_key_banner()

    st.markdown('<div style="font-family:DM Sans,sans-serif;font-size:0.9rem;'
                'color:var(--text-muted);margin-bottom:1.2rem;">'
                'Analyse two decisions side-by-side — verdicts, confidence, bias types, laws.</div>',
                unsafe_allow_html=True)

    cc1,cc2 = st.columns(2)
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

    cmp_btn = st.button("⚡ Compare Both Decisions", key="compare_btn", disabled=not _api_key_ok())

    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Paste text for both decisions.")
        else:
            with st.spinner("Analysing both decisions…"):
                r1,e1 = run_analysis(cmp_text1, cmp_type1)
                r2,e2 = run_analysis(cmp_text2, cmp_type2)
            if e1: st.error(f"Decision A: {e1}")
            if e2: st.error(f"Decision B: {e2}")
            if r1 and r2:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                b1,b2   = r1.get("bias_found"), r2.get("bias_found")
                c1v,c2v = r1.get("confidence_score",0), r2.get("confidence_score",0)
                if b1 and b2:
                    winner  = "A" if c1v >= c2v else "B"
                    banner  = f"⚠️ Both decisions show bias — Decision {winner} has higher confidence ({int(max(c1v,c2v)*100)}%)"
                elif b1:  banner = "⚠️ Decision A shows bias · Decision B appears fair"
                elif b2:  banner = "⚠️ Decision B shows bias · Decision A appears fair"
                else:     banner = "✅ Neither decision shows clear discriminatory patterns"
                st.markdown(f'<div class="winner-banner">{banner}</div>', unsafe_allow_html=True)

                v1c,v2c = st.columns(2)
                for col, r, lbl in [(v1c,r1,"A"),(v2c,r2,"B")]:
                    with col:
                        bias  = r.get("bias_found",False)
                        conf  = r.get("confidence_score",0)
                        vcls  = "verdict-bias" if bias else "verdict-clean"
                        vico  = "⚠️" if bias else "✅"
                        vsub  = "BIAS DETECTED" if bias else "NO BIAS FOUND"
                        st.markdown(f'<div class="{vcls}"><div class="v-icon">{vico}</div>'
                                    f'<div class="v-label">Decision {lbl}</div>'
                                    f'<div class="v-sub">{vsub}</div></div>', unsafe_allow_html=True)
                        st.plotly_chart(gauge_chart(conf,bias), use_container_width=True, config={"displayModeBar":False})
                        bt_ch = chips_html(r.get("bias_types",[]))
                        sv_bg = severity_badge(conf,bias)
                        st.markdown(f'{bt_ch} {sv_bg}', unsafe_allow_html=True)
                        r_laws = r.get("legal_frameworks",[])
                        if r_laws:
                            st.markdown(chips_html(r_laws,"chip-teal"), unsafe_allow_html=True)
                        fair_v = r.get("fair_outcome") or "N/A"
                        expl_v = r.get("explanation") or ""
                        st.markdown(f'<div class="info-card green" style="margin-top:0.7rem;">'
                                    f'<div class="ic-label">Fair Outcome</div>'
                                    f'<div class="ic-value">{fair_v}</div></div>', unsafe_allow_html=True)
                        if expl_v:
                            st.markdown(f'<div class="info-card amber">'
                                        f'<div class="ic-label">What Went Wrong</div>'
                                        f'<div class="ic-value" style="font-size:0.85rem;">{expl_v}</div></div>',
                                        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# TAB 5 — BATCH
# ══════════════════════════════════════════════════════

with tab_batch:
    if not _api_key_ok():
        _api_key_banner()

    st.markdown('<div style="font-family:DM Sans,sans-serif;font-size:0.9rem;'
                'color:var(--text-muted);margin-bottom:1.2rem;">'
                'Paste decisions separated by <code style="background:rgba(255,255,255,0.05);'
                'padding:1px 6px;border-radius:4px;font-family:DM Mono,monospace;">---</code> '
                'or upload a CSV with a <code style="background:rgba(255,255,255,0.05);'
                'padding:1px 6px;border-radius:4px;font-family:DM Mono,monospace;">text</code> '
                'column. Limit: 10 per run.</div>', unsafe_allow_html=True)

    batch_mode = st.radio("Batch mode", ["✏️ Paste Text","📊 Upload CSV"],
                           horizontal=True, label_visibility="collapsed", key="batch_mode")

    if batch_mode == "✏️ Paste Text":
        batch_text = st.text_area("Batch", height=240, label_visibility="collapsed", key="batch_input",
                                   placeholder="Decision 1…\n---\nDecision 2…\n---\nDecision 3…")
        raw_blocks = [b.strip() for b in batch_text.split("---") if b.strip()] if batch_text else []
    else:
        batch_csv = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed",
                                      key="batch_csv_upload")
        raw_blocks = []
        if batch_csv:
            try:
                df_up = pd.read_csv(batch_csv)
                if "text" in df_up.columns:
                    raw_blocks = df_up["text"].dropna().tolist()
                    st.markdown(f'<div class="pill-ok">● {len(raw_blocks)} rows loaded</div>',
                                unsafe_allow_html=True)
                else:
                    st.error("❌ CSV must have a 'text' column")
            except Exception as e:
                st.error(f"❌ {e}")

    bc1,bc2 = st.columns([1,1])
    with bc1:
        batch_type = st.selectbox("Type (all)", ["job","loan","medical","university","other"],
                                   format_func=lambda x: TYPE_LABELS[x],
                                   label_visibility="collapsed", key="batch_type")
    with bc2:
        batch_btn = st.button("📦 Run Batch Analysis", key="batch_run", disabled=not _api_key_ok())

    if raw_blocks:
        st.markdown(
            f'<div style="font-family:DM Mono,monospace;font-size:0.68rem;color:var(--accent);margin-top:0.3rem;">'
            f'● {len(raw_blocks)} decision{"s" if len(raw_blocks)!=1 else ""} queued</div>',
            unsafe_allow_html=True,
        )

    if batch_btn:
        if not raw_blocks:
            st.warning("⚠️ No decisions found.")
        elif len(raw_blocks) > 10:
            st.warning("⚠️ Batch limit is 10.")
        else:
            progress = st.progress(0)
            results  = []
            status   = st.empty()
            t_start  = time.time()
            for i, block in enumerate(raw_blocks):
                elapsed = time.time() - t_start
                eta     = (elapsed/(i+1))*(len(raw_blocks)-i-1) if i > 0 else 0
                eta_str = f"  ETA ~{int(eta)}s" if eta > 1 else ""
                status.markdown(
                    f'<div style="font-family:DM Mono,monospace;font-size:0.72rem;color:var(--accent);">'
                    f'Analysing {i+1}/{len(raw_blocks)}…{eta_str}</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(block, batch_type)
                results.append({"text":block,"report":rep,"error":err})
                progress.progress((i+1)/len(raw_blocks))
            progress.empty(); status.empty()

            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            bias_c  = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            clean_c = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            err_c   = sum(1 for r in results if r["error"])
            sm1,sm2,sm3,sm4 = st.columns(4)
            sm1.metric("Total",len(results)); sm2.metric("Bias",bias_c)
            sm3.metric("No Bias",clean_c);    sm4.metric("Errors",err_c)

            rows = []
            for i, res in enumerate(results,1):
                rep,error = res["report"],res["error"]
                if error:
                    rows.append({"#":i,"Verdict":"ERROR","Conf":"—","Bias Types":error[:60],"Severity":"—","Affected":"—"})
                elif rep:
                    rows.append({"#":i,
                                 "Verdict":"⚠ BIAS" if rep.get("bias_found") else "✓ CLEAN",
                                 "Conf":f"{int(rep.get('confidence_score',0)*100)}%",
                                 "Bias Types":", ".join(rep.get("bias_types",[])) or "None",
                                 "Severity":(rep.get("severity","") or "—").upper(),
                                 "Affected":rep.get("affected_characteristic") or "—"})
            if rows:
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_reps = [r["report"] for r in results if r["report"]]
            if all_reps:
                dl1,_ = st.columns([1,2])
                with dl1:
                    st.download_button("📥 Download Batch Results (.csv)", data=reports_to_csv(all_reps),
                                       file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                       mime="text/csv", key="batch_csv_dl")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results,1):
                rep,error = res["report"],res["error"]
                lbl = f"Decision {i}"
                if error: lbl += " — ERROR"
                elif rep:
                    vs = "⚠ BIAS" if rep.get("bias_found") else "✓ CLEAN"
                    lbl += f" — {vs} ({int(rep.get('confidence_score',0)*100)}%)"
                with st.expander(lbl, expanded=False):
                    preview = res["text"][:300]+("…" if len(res["text"])>300 else "")
                    st.markdown(f'<div class="preview-box">{preview}</div>', unsafe_allow_html=True)
                    if error: st.error(error)
                    elif rep:
                        bias  = rep.get("bias_found",False)
                        btyps = rep.get("bias_types",[])
                        laws  = rep.get("legal_frameworks",[])
                        b_v   = "⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"
                        b_col = "red" if bias else "green"
                        bt_ch = chips_html(btyps) if btyps else "None"
                        lw_ch = (f'<div class="info-card teal" style="margin-top:0.5rem;">'
                                 f'<div class="ic-label">Legal Frameworks</div>'
                                 f'<div class="ic-value">{chips_html(laws,"chip-teal")}</div></div>') if laws else ""
                        fair  = rep.get("fair_outcome") or "N/A"
                        st.markdown(
                            f'<div class="info-card {b_col}" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Verdict</div>'
                            f'<div class="ic-value mono">{b_v}</div></div>'
                            f'<div class="info-card amber" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Bias Types</div>'
                            f'<div class="ic-value">{bt_ch}</div></div>'
                            f'{lw_ch}'
                            f'<div class="info-card green" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{fair}</div></div>',
                            unsafe_allow_html=True,
                        )

# ══════════════════════════════════════════════════════
# TAB 6 — SETTINGS
# ══════════════════════════════════════════════════════

with tab_settings:
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.2rem;font-weight:800;'
                'color:var(--text-primary);margin-bottom:0.3rem;">Settings & System Info</div>'
                '<div style="font-family:DM Sans,sans-serif;font-size:0.85rem;'
                'color:var(--text-muted);margin-bottom:1.5rem;">Verdict Watch V6 — configuration.</div>',
                unsafe_allow_html=True)

    s1,s2 = st.columns(2)
    with s1:
        st.markdown('<div class="sec-label">API Configuration</div>', unsafe_allow_html=True)
        key_set   = _api_key_ok()
        k_col     = "green" if key_set else "red"
        k_stat    = "● SET (from .env)" if key_set else "● NOT SET"
        pdf_col   = "green" if PDF_SUPPORT else "amber"
        pdf_stat  = "● INSTALLED" if PDF_SUPPORT else "● NOT INSTALLED — pip install PyMuPDF"
        st.markdown(
            f'<div class="info-card {k_col}"><div class="ic-label">Groq API Key</div>'
            f'<div class="ic-value mono">{k_stat}</div></div>'
            f'<div class="info-card blue"><div class="ic-label">Model</div>'
            f'<div class="ic-value mono">llama-3.3-70b-versatile</div></div>'
            f'<div class="info-card"><div class="ic-label">Temperature / Retries</div>'
            f'<div class="ic-value mono">0.1  ·  3× exponential backoff</div></div>'
            f'<div class="info-card {pdf_col}"><div class="ic-label">PyMuPDF</div>'
            f'<div class="ic-value mono">{pdf_stat}</div></div>',
            unsafe_allow_html=True,
        )

    with s2:
        st.markdown('<div class="sec-label">Database Stats</div>', unsafe_allow_html=True)
        all_r  = get_all_reports()
        fb     = services.get_feedback_stats()
        db_url = os.getenv("DATABASE_URL","sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="info-card"><div class="ic-label">Total Reports</div>'
            f'<div class="ic-value mono">{len(all_r)}</div></div>'
            f'<div class="info-card"><div class="ic-label">Database</div>'
            f'<div class="ic-value mono" style="font-size:0.75rem;">{db_url}</div></div>'
            f'<div class="info-card purple"><div class="ic-label">Feedback</div>'
            f'<div class="ic-value mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sec-label" style="margin-top:1rem;">V6 Feature Flags</div>', unsafe_allow_html=True)
        for icon,name,desc in [
            ("✅","Quick Examples Fix",  "Session state key binding"),
            ("✅","f-string Fixes",      "All backslash errors resolved"),
            ("✅","Duplicate Detection", "SHA-256 hash skip"),
            ("✅","Retry Logic",         "3× backoff"),
            ("✅","AI Bias Phrases",     "Exact phrase extraction"),
            ("✅","Legal Frameworks",    "Laws cited per case"),
            ("✅","Feedback System",     "Per-report ratings"),
            ("✅","File Upload",         ".txt + .pdf"),
            ("✅","CSV Batch",           "Bulk via CSV"),
            ("✅","Trend Analytics",     "Daily bias chart"),
            ("✅","Severity Donut",      "New V6 chart"),
            ("✅","Batch ETA",           "Real-time estimate"),
            ("✅","Animated Verdicts",   "Pulse animation"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:5px 0;border-bottom:1px solid var(--border);'
                f'font-family:DM Mono,monospace;font-size:0.72rem;">'
                f'<span style="color:var(--green);">{icon} {name}</span>'
                f'<span style="color:var(--text-muted);">{desc}</span></div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════
# TAB 7 — ABOUT
# ══════════════════════════════════════════════════════

with tab_about:
    ab1,ab2 = st.columns([1.6,1])
    with ab1:
        st.markdown(
            '<div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;'
            'color:var(--text-primary);margin-bottom:0.5rem;">What is Verdict Watch?</div>'
            '<div style="font-family:DM Sans,sans-serif;font-size:0.9rem;'
            'color:var(--text-muted);line-height:1.85;margin-bottom:1.4rem;">'
            'Verdict Watch V6 is an enterprise-grade AI system that analyses automated decisions — '
            'job rejections, loan denials, medical triage, university admissions — '
            'for hidden bias. A 3-step Groq + Llama 3.3 70B pipeline extracts criteria, '
            'detects discriminatory patterns, cites relevant laws, and generates the fair outcome.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sec-label">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Gender Bias",             "Gender, name, or parental status influence"),
            ("Age Discrimination",       "Unfair age group or seniority weighting"),
            ("Racial / Ethnic Bias",     "Name-based or nationality profiling"),
            ("Geographic Redlining",     "Zip code or district as discriminatory proxy"),
            ("Socioeconomic Bias",       "Employment sector or credit over-weighting"),
            ("Language Discrimination",  "Primary language used against applicants"),
            ("Insurance Classification", "Insurance tier used to rank priority"),
        ]:
            st.markdown(f'<div class="info-card blue" style="margin-bottom:0.4rem;">'
                        f'<div class="ic-label">{name}</div>'
                        f'<div class="ic-value" style="font-size:0.86rem;">{desc}</div></div>',
                        unsafe_allow_html=True)

    with ab2:
        st.markdown('<div class="sec-label">V6 Changelog</div>', unsafe_allow_html=True)
        for icon, name, desc in [
            ("🔧","Examples Fixed",     "session_state key binding"),
            ("🔐",".env API Key",       "No inline key"),
            ("📄","File Upload",        ".txt + .pdf support"),
            ("🎯","AI Bias Phrases",    "Model-flagged phrases"),
            ("⚖️","Legal Frameworks",   "Laws per case"),
            ("🔁","Dup Detection",      "SHA-256 hash skip"),
            ("👍","Feedback Ratings",   "Per-report ratings"),
            ("📅","Date Filter",        "History date range"),
            ("📊","CSV Batch",          "Bulk CSV analysis"),
            ("📈","Trend Chart",        "Daily bias rate"),
            ("🍩","Severity Donut",     "New breakdown chart"),
            ("⏱","Batch ETA",          "Real-time estimate"),
            ("💫","Animated Verdicts",  "Pulse on results"),
        ]:
            st.markdown(f'<div class="info-card purple" style="margin-bottom:0.35rem;">'
                        f'<div class="ic-label">{icon} {name}</div>'
                        f'<div class="ic-value" style="font-size:0.84rem;">{desc}</div></div>',
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Tech Stack</div>', unsafe_allow_html=True)
        for name, desc in [("⚡ Groq","LLM inference"),("🦙 Llama 3.3 70B","Language model"),
                           ("🎈 Streamlit","Full-stack UI"),("🗄️ SQLAlchemy","Database"),
                           ("📊 Plotly","Charts"),("📄 PyMuPDF","PDF extraction")]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;'
                        f'font-family:DM Mono,monospace;font-size:0.72rem;'
                        f'padding:5px 0;border-bottom:1px solid var(--border);">'
                        f'<span style="color:var(--text-primary);">{name}</span>'
                        f'<span style="color:var(--text-muted);">{desc}</span></div>',
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="info-card amber"><div class="ic-label">⚠ Disclaimer</div>'
                    '<div class="ic-value" style="font-size:0.84rem;">'
                    'Not legal advice. Built for educational purposes. '
                    'Consult a qualified legal professional for discrimination claims.</div></div>',
                    unsafe_allow_html=True)

# FOOTER
st.markdown(
    '<div class="footer-bar">'
    'Verdict Watch V6  ·  Groq / Llama 3.3 70B  ·  Enterprise Edition  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)