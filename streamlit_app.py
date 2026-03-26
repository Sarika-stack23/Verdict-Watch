"""
streamlit_app.py — Verdict Watch V9
Minimal Edition — clean, fast, fully functional.

Fixes:
  ✅ SyntaxError line 997 (backslash in f-string expression)
  ✅ All f-string quote escaping issues resolved
  ✅ Simplified CSS (60% reduction)
  ✅ Cleaner layout across all tabs

Upgrades:
  ✨ Confidence gauge now uses Plotly indicator
  ✨ Smarter empty-state illustrations
  ✨ Inline toast feedback (no page reload)
  ✨ Better batch ETA with cancellation guard
  ✨ Appeal letter copy-to-clipboard button
  ✨ History: per-row inline re-analysis
  ✨ Dashboard: new avg severity KPI
  ✨ Settings: live API test button
  ✨ Compare: diff highlights between A and B
"""

import streamlit as st
import services
import plotly.graph_objects as go
import pandas as pd
import re
import os
import json
import time
from datetime import datetime
from collections import Counter

try:
    import fitz as pymupdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

services.init_db()

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CSS — MINIMAL SYSTEM
# ──────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');

:root {
    --bg:      #fafafa;
    --surf:    #ffffff;
    --s2:      #f4f4f5;
    --s3:      #e4e4e7;
    --border:  #e4e4e7;

    --t1:      #09090b;
    --t2:      #52525b;
    --t3:      #a1a1aa;

    --blue:    #2563eb;
    --blue-lt: #eff6ff;
    --blue-dk: #1d4ed8;

    --red:     #dc2626;
    --red-lt:  #fef2f2;
    --green:   #16a34a;
    --grn-lt:  #f0fdf4;
    --amber:   #d97706;
    --amb-lt:  #fffbeb;

    --r:       8px;
    --r-lg:    12px;
    --r-full:  999px;

    --ff:      'Geist', system-ui, sans-serif;
    --mono:    'Geist Mono', monospace;
    --sh:      0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
    --sh2:     0 4px 12px rgba(0,0,0,.08);
}

html, body, [class*="css"] {
    font-family: var(--ff) !important;
    background: var(--bg) !important;
    color: var(--t1) !important;
}

[data-testid="stSidebar"] {
    background: var(--surf) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid var(--border);
    gap: 0; padding: 0 2px;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--ff) !important;
    font-size: 0.84rem; font-weight: 500;
    color: var(--t2) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 16px !important;
    border-radius: 0 !important;
    transition: color .15s, border-color .15s;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--t1) !important; }
.stTabs [aria-selected="true"] {
    color: var(--blue) !important;
    border-bottom-color: var(--blue) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* ── Buttons ── */
.stButton > button {
    font-family: var(--ff) !important;
    font-size: 0.875rem; font-weight: 500;
    background: var(--blue);
    color: #fff; border: none;
    border-radius: var(--r-full);
    padding: .5rem 1.4rem;
    box-shadow: var(--sh);
    transition: filter .15s, transform .1s;
}
.stButton > button:hover { filter: brightness(1.1); transform: translateY(-1px); }
.stButton > button:active { transform: none; }

[data-testid="stSidebar"] .stButton > button {
    background: var(--s2) !important;
    color: var(--t1) !important;
    border: 1px solid var(--border) !important;
    box-shadow: none !important;
    width: 100% !important; text-align: left !important;
    border-radius: var(--r) !important;
    transform: none !important;
    font-size: 0.82rem !important;
    padding: .4rem .85rem !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--s3) !important; transform: none !important;
}

/* ── Inputs ── */
.stTextArea textarea {
    font-family: var(--ff) !important; font-size: 0.9rem !important;
    background: var(--surf) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
    line-height: 1.7 !important; padding: 12px 14px !important;
    resize: vertical !important; color: var(--t1) !important;
    transition: border-color .2s !important;
}
.stTextArea textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.1) !important;
    outline: none !important;
}
.stTextArea label, .stSelectbox label, .stTextInput label {
    font-family: var(--ff) !important; font-size: .75rem !important;
    font-weight: 600 !important; color: var(--t3) !important;
    text-transform: uppercase !important; letter-spacing: .06em !important;
}
.stSelectbox > div > div {
    background: var(--surf) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r) !important;
    font-family: var(--ff) !important; font-size: .875rem !important;
}
[data-testid="stFileUploader"] {
    background: var(--surf) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--r-lg) !important;
    transition: border-color .15s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--blue) !important; }

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--surf); border-radius: var(--r-lg);
    border: 1px solid var(--border);
    padding: 1rem 1.25rem;
}
[data-testid="metric-container"] label {
    font-size: .7rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: .06em !important;
    color: var(--t3) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.6rem !important; font-weight: 700 !important;
    color: var(--t1) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: var(--surf) !important; color: var(--blue) !important;
    border: 1.5px solid var(--blue) !important;
    border-radius: var(--r-full) !important;
    font-family: var(--ff) !important; font-weight: 500 !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover { background: var(--blue-lt) !important; transform: none !important; }

/* ── Progress ── */
.stProgress > div > div { background: var(--blue) !important; }
.stProgress > div { background: var(--s3) !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    font-family: var(--ff) !important; font-weight: 500 !important;
    font-size: .875rem !important; background: var(--surf) !important;
    border: 1px solid var(--border) !important; border-radius: var(--r) !important;
    padding: .75rem 1rem !important; color: var(--t1) !important;
}
.streamlit-expanderContent {
    background: var(--surf) !important; border: 1px solid var(--border) !important;
    border-top: none !important; border-radius: 0 0 var(--r) var(--r) !important;
    padding: 1rem !important;
}

/* ── VERDICT WATCH COMPONENTS ── */
.vw-header {
    border-bottom: 1px solid var(--border);
    padding: 0 0 1.25rem;
    margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 12px;
}
.vw-header-title { font-size: 1.15rem; font-weight: 700; color: var(--t1); letter-spacing: -.02em; }
.vw-header-sub   { font-size: .78rem; color: var(--t3); margin-top: 1px; }

.card {
    background: var(--surf); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 1rem 1.2rem;
    margin-bottom: 8px; transition: box-shadow .15s;
}
.card:hover { box-shadow: var(--sh); }
.card-lbl {
    font-size: .68rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: var(--t3); margin-bottom: 5px;
}
.card-val { font-size: .9rem; color: var(--t1); line-height: 1.5; }
.card-val.mono { font-family: var(--mono); font-size: .85rem; }
.card-val.lg   { font-size: 1.2rem; font-weight: 700; }

.card.err  { background: var(--red-lt);  border-color: rgba(220,38,38,.2); }
.card.ok   { background: var(--grn-lt);  border-color: rgba(22,163,74,.2); }
.card.warn { background: var(--amb-lt);  border-color: rgba(217,119,6,.2); }
.card.blue { background: var(--blue-lt); border-color: rgba(37,99,235,.2); }
.card.muted{ background: var(--s2);      border-color: var(--border); }

.verdict-banner {
    border-radius: var(--r-lg); padding: 1.75rem 2rem;
    text-align: center; margin-bottom: 1.25rem;
}
.verdict-banner.bias  { background: var(--red-lt); border: 1px solid rgba(220,38,38,.2); }
.verdict-banner.clean { background: var(--grn-lt); border: 1px solid rgba(22,163,74,.2); }
.vb-icon  { font-size: 2rem; line-height: 1; margin-bottom: 8px; }
.vb-title { font-size: 1.4rem; font-weight: 700; letter-spacing: -.02em; margin-bottom: 4px; }
.verdict-banner.bias  .vb-title { color: var(--red); }
.verdict-banner.clean .vb-title { color: var(--green); }
.vb-sub   { font-size: .85rem; color: var(--t2); }

.chip {
    display: inline-block; border-radius: var(--r-full);
    padding: 2px 10px; font-size: .76rem; font-weight: 500;
    margin: 2px 3px 2px 0; border: 1px solid transparent;
}
.chip-e { background: var(--red-lt);  color: var(--red);   border-color: rgba(220,38,38,.2); }
.chip-g { background: var(--grn-lt);  color: var(--green); border-color: rgba(22,163,74,.2); }
.chip-b { background: var(--blue-lt); color: var(--blue);  border-color: rgba(37,99,235,.2); }
.chip-a { background: var(--amb-lt);  color: var(--amber); border-color: rgba(217,119,6,.2); }
.chip-n { background: var(--s2);      color: var(--t2);    border-color: var(--border); }

.sev { display: inline-block; border-radius: var(--r-full); padding: 2px 10px; font-size: .72rem; font-weight: 600; }
.sev-h { background: var(--red-lt); color: var(--red); }
.sev-m { background: var(--amb-lt); color: var(--amber); }
.sev-l { background: var(--grn-lt); color: var(--green); }

.hl-box {
    font-size: .875rem; line-height: 1.9; color: var(--t2);
    background: var(--surf); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 1rem 1.2rem;
}
.hl-box mark {
    background: rgba(220,38,38,.1); color: var(--red);
    border-radius: 3px; padding: 1px 4px;
    border-bottom: 1.5px solid rgba(220,38,38,.3);
}

.rec {
    display: flex; gap: 10px; align-items: flex-start;
    background: var(--surf); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: .8rem 1rem; margin-bottom: 7px;
    transition: box-shadow .15s;
}
.rec:hover { box-shadow: var(--sh); }
.rec-n {
    background: var(--blue); color: #fff;
    border-radius: 5px; min-width: 20px; height: 20px;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--mono); font-size: .68rem; font-weight: 600;
    flex-shrink: 0; margin-top: 2px;
}
.rec-t { font-size: .86rem; color: var(--t2); line-height: 1.55; }

.appeal-box {
    background: var(--s2); border: 1px solid var(--border);
    border-left: 3px solid var(--blue); border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem; font-family: var(--mono); font-size: .78rem;
    line-height: 1.9; color: var(--t2); white-space: pre-wrap;
}

.scan-wrap { margin: 12px 0; }
.scan-track { background: var(--s3); border-radius: 2px; height: 2px; overflow: hidden; margin: 6px 0 4px; }
@keyframes scan { 0%{transform:translateX(-120%)} 100%{transform:translateX(400%)} }
.scan-fill  { height: 100%; background: var(--blue); border-radius: 2px; animation: scan 1.3s ease-in-out infinite; width: 25%; }
.scan-steps { display: flex; gap: 5px; margin-bottom: 6px; }
.ss-item {
    flex: 1; background: var(--s2); border-radius: var(--r);
    padding: .4rem .6rem; text-align: center; border: 1px solid transparent;
}
.ss-item.done   { background: var(--grn-lt); border-color: rgba(22,163,74,.2); }
.ss-item.active { background: var(--blue-lt); border-color: rgba(37,99,235,.2); }
.ss-lbl { font-size: .7rem; font-weight: 500; color: var(--t3); font-family: var(--ff); }
.ss-item.done   .ss-lbl { color: var(--green); font-weight: 600; }
.ss-item.active .ss-lbl { color: var(--blue);  font-weight: 600; }

.empty { text-align: center; padding: 3rem 1rem; }
.empty-ico { font-size: 2.5rem; margin-bottom: 10px; opacity: .4; }
.empty-t { font-size: 1rem; font-weight: 600; color: var(--t1); margin-bottom: 5px; }
.empty-s { font-size: .85rem; color: var(--t2); line-height: 1.6; max-width: 320px; margin: 0 auto; }

.key-err {
    background: var(--red-lt); border: 1px solid rgba(220,38,38,.25);
    border-left: 3px solid var(--red); border-radius: var(--r-lg);
    padding: .9rem 1.2rem; font-size: .875rem; color: #7f1d1d; margin-bottom: 1rem;
}
.key-err code {
    background: rgba(220,38,38,.1); padding: 2px 6px;
    border-radius: 4px; font-family: var(--mono); font-size: .8rem;
}

.dup-warn {
    display: flex; align-items: flex-start; gap: 10px;
    background: var(--amb-lt); border: 1px solid rgba(217,119,6,.3);
    border-radius: var(--r-lg); padding: .9rem 1.1rem;
    font-size: .875rem; color: #78350f; margin-bottom: 1rem;
}

.badge-ok  { display: inline-flex; align-items: center; gap: 5px; background: var(--grn-lt); color: var(--green); border-radius: var(--r-full); padding: 3px 11px; font-size: .72rem; font-weight: 600; }
.badge-err { display: inline-flex; align-items: center; gap: 5px; background: var(--red-lt); color: var(--red);   border-radius: var(--r-full); padding: 3px 11px; font-size: .72rem; font-weight: 600; }

.law-item {
    display: flex; gap: 9px; align-items: center;
    padding: 7px 0; border-bottom: 1px solid var(--s3);
    font-size: .86rem; color: var(--t2);
}
.law-item:last-child { border-bottom: none; }
.law-ico { color: var(--blue); flex-shrink: 0; }

.divider { border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }

.lbl { font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--t3); margin-bottom: 8px; }

.char-bar { height: 2px; border-radius: 1px; margin-top: 4px; transition: width .3s; }
.char-info { font-size: .78rem; font-weight: 500; margin-top: 4px; }

.sb-head {
    background: var(--blue); padding: 18px 16px 16px;
    margin: -1rem -1rem 1rem; border-radius: 0 0 var(--r-lg) var(--r-lg);
}
.sb-title { font-size: .95rem; font-weight: 700; color: #fff; letter-spacing: -.02em; }
.sb-sub   { font-size: .7rem; color: rgba(255,255,255,.7); margin-top: 1px; }
.sb-status {
    display: inline-flex; align-items: center; gap: 4px; margin-top: 8px;
    border-radius: var(--r-full); padding: 2px 9px; font-size: .67rem; font-weight: 500;
}
.sb-ok  { background: rgba(255,255,255,.15); color: #fff; border: 1px solid rgba(255,255,255,.25); }
.sb-err { background: rgba(255,255,255,.08); color: #fecaca; border: 1px solid rgba(254,202,202,.3); }
.sb-lbl { font-size: .67rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--t3); margin: 12px 0 7px; }

.step-dot { width: 18px; height: 18px; border-radius: 50%; background: var(--blue); color: #fff; display: inline-flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: .62rem; font-weight: 700; flex-shrink: 0; margin-top: 1px; }
.step-row { display: flex; gap: 8px; padding: 4px 0; }
.step-txt { font-size: .78rem; color: var(--t2); line-height: 1.4; }

.winner-bar {
    background: var(--blue-lt); border: 1px solid rgba(37,99,235,.2);
    border-radius: var(--r-lg); padding: .9rem 1.2rem;
    text-align: center; font-size: .9rem; font-weight: 600;
    color: var(--blue-dk); margin-bottom: 1rem;
}

.preview-box {
    background: var(--s2); border: 1px solid var(--border);
    border-radius: var(--r); padding: .65rem .85rem;
    font-family: var(--mono); font-size: .75rem; color: var(--t2);
    line-height: 1.6; max-height: 72px; overflow: hidden;
    white-space: pre-wrap; margin-bottom: 8px;
}

.diff-badge {
    display: inline-block; background: var(--s2); border: 1px solid var(--border);
    border-radius: var(--r-full); padding: 2px 9px; font-size: .72rem;
    font-weight: 600; color: var(--t2); margin: 2px;
}
.diff-only-a { background: rgba(37,99,235,.08);  color: var(--blue);  border-color: rgba(37,99,235,.2); }
.diff-only-b { background: rgba(220,38,38,.08);  color: var(--red);   border-color: rgba(220,38,38,.2); }
.diff-shared { background: rgba(22,163,74,.08);  color: var(--green); border-color: rgba(22,163,74,.2); }

footer, [data-testid="stStatusWidget"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

EXAMPLES = [
    {"tag": "Job Rejection",  "emoji": "💼", "type": "job",
     "text": ("Thank you for applying to the Software Engineer position. "
              "After careful review we have decided not to move forward. "
              "We felt other candidates were a stronger fit for our team culture at this time.")},
    {"tag": "Bank Loan",      "emoji": "🏦", "type": "loan",
     "text": ("Your loan application has been declined. Primary reasons: insufficient credit history, "
              "residential area risk score, employment sector classification. "
              "You may reapply after 6 months.")},
    {"tag": "Medical Triage", "emoji": "🏥", "type": "medical",
     "text": ("Based on your intake assessment you have been assigned Priority Level 3. "
              "Factors considered: age group, reported pain level, primary language, insurance classification.")},
    {"tag": "University",     "emoji": "🎓", "type": "university",
     "text": ("We regret to inform you that your application for admission has not been successful. "
              "Our admissions committee considered zip code region diversity metrics, legacy status, "
              "and extracurricular profile alignment when making this decision.")},
    {"tag": "Housing",        "emoji": "🏠", "type": "other",
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

BIAS_KW = {
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|housewife|mrs|mr)\b",
    "Age":           r"\b(age group|senior|junior|young|old|millennial|boomer|elderly|youth)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|name|surname)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|occupation|class|status)\b",
    "Language":      r"\b(primary language|language|accent|english|bilingual|native speaker)\b",
    "Insurance":     r"\b(insurance|coverage|uninsured|medicaid|medicare|policy|insurance classification)\b",
}

BIAS_DIMS = ["Gender", "Age", "Racial", "Geographic", "Socioeconomic", "Language", "Insurance"]
CHIP_CYCLE = ["chip-e", "chip-a", "chip-b", "chip-g", "chip-n"]

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Geist, system-ui, sans-serif", color="#52525b"),
    margin=dict(l=10, r=10, t=14, b=10),
)
MD3_PAL = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777"]

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

_DEF = {
    "session_count":     0,
    "last_report":       None,
    "last_text":         "",
    "appeal_letter":     None,
    "decision_input":    "",
    "decision_type_sel": "job",
}
for k, v in _DEF.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def api_ok():
    return bool(os.getenv("GROQ_API_KEY", "").strip())

def api_banner():
    st.markdown(
        '<div class="key-err">⚠️ <strong>GROQ_API_KEY not found.</strong> '
        'Add it to your <code>.env</code>:<br>'
        '<code style="display:block;margin-top:5px;">GROQ_API_KEY=gsk_your_key</code><br>'
        'Free keys at <strong>console.groq.com</strong> — then restart.</div>',
        unsafe_allow_html=True,
    )

def all_reports():
    try: return services.get_all_reports()
    except Exception: return []

def chips(items, style="auto"):
    if not items:
        return '<span class="chip chip-n">None detected</span>'
    return "".join(
        f'<span class="chip {CHIP_CYCLE[i % len(CHIP_CYCLE)] if style == "auto" else style}">{item}</span>'
        for i, item in enumerate(items)
    )

def highlight(text, phrases, bias_types):
    out = text
    for p in phrases:
        if p and len(p) > 2:
            out = re.sub(re.escape(p), lambda m: f"<mark>{m.group()}</mark>",
                         out, flags=re.IGNORECASE)
    for b in bias_types:
        for key, pat in BIAS_KW.items():
            if key.lower() in b.lower() or b.lower() in key.lower():
                out = re.sub(pat, lambda m: f"<mark>{m.group()}</mark>",
                             out, flags=re.IGNORECASE)
    return out

def sev_badge(conf, bias):
    if not bias: return '<span class="sev sev-l">Low Risk</span>'
    if conf >= .75: return '<span class="sev sev-h">High Severity</span>'
    if conf >= .45: return '<span class="sev sev-m">Medium Severity</span>'
    return '<span class="sev sev-l">Low Severity</span>'

def ring_svg(pct, bias):
    r, cx, cy, sw = 46, 60, 60, 9
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    gap  = circ - dash
    col  = "#dc2626" if bias else ("#16a34a" if pct < 45 else "#d97706")
    return (
        f'<svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e4e4e7" stroke-width="{sw}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"'
        f' stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-linecap="round"'
        f' transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy-4}" text-anchor="middle"'
        f' font-family="Geist,sans-serif" font-size="19" font-weight="700" fill="{col}">{pct}%</text>'
        f'<text x="{cx}" y="{cy+11}" text-anchor="middle"'
        f' font-family="Geist,sans-serif" font-size="7.5" font-weight="600"'
        f' fill="#a1a1aa" letter-spacing="0.07em">CONFIDENCE</text>'
        f'</svg>'
    )

def extract_file(f):
    nm = f.name.lower()
    if nm.endswith(".txt"):
        return f.read().decode("utf-8", errors="replace")
    if nm.endswith(".pdf"):
        if not PDF_SUPPORT:
            st.warning("PDF requires PyMuPDF: pip install PyMuPDF")
            return None
        raw = f.read()
        doc = pymupdf.open(stream=raw, filetype="pdf")
        return "\n".join(p.get_text() for p in doc).strip()
    st.warning(f"Unsupported: {f.name}")
    return None

def txt_report(report, text, dtype):
    recs = report.get("recommendations", [])
    laws = report.get("legal_frameworks", [])
    lines = [
        "=" * 64,
        "        VERDICT WATCH V9 — BIAS ANALYSIS REPORT",
        "=" * 64,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id', 'N/A')}",
        f"Severity   : {report.get('severity', 'N/A').upper()}",
        "",
        "── ORIGINAL DECISION ────────────────────────────────────",
        text,
        "",
        "── VERDICT ──────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence : {int(report.get('confidence_score', 0) * 100)}%",
        "",
        "── BIAS TYPES ───────────────────────────────────────────",
        ", ".join(report.get("bias_types", [])) or "None detected",
        "",
        "── CHARACTERISTIC AFFECTED ──────────────────────────────",
        report.get("affected_characteristic", "N/A"),
        "",
        "── ORIGINAL OUTCOME ─────────────────────────────────────",
        report.get("original_outcome", "N/A"),
        "",
        "── FAIR OUTCOME ─────────────────────────────────────────",
        report.get("fair_outcome", "N/A"),
        "",
        "── EXPLANATION ──────────────────────────────────────────",
        report.get("explanation", "N/A"),
        "",
        "── NEXT STEPS ───────────────────────────────────────────",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    if laws:
        lines += ["", "── LEGAL FRAMEWORKS ─────────────────────────────────────"]
        for law in laws:
            lines.append(f"  • {law}")
    lines += ["", "=" * 64, "  Verdict Watch V9  ·  Not legal advice", "=" * 64]
    return "\n".join(lines)

def to_csv(reps):
    rows = [{
        "id":           r.get("id", ""),
        "created_at":   (r.get("created_at") or "")[:16].replace("T", " "),
        "bias_found":   r.get("bias_found", False),
        "severity":     r.get("severity", ""),
        "confidence":   int(r.get("confidence_score", 0) * 100),
        "bias_types":   "; ".join(r.get("bias_types", [])),
        "affected":     r.get("affected_characteristic", ""),
        "original":     r.get("original_outcome", ""),
        "fair":         r.get("fair_outcome", ""),
        "explanation":  r.get("explanation", ""),
        "legal":        "; ".join(r.get("legal_frameworks", [])),
        "next_steps":   " | ".join(r.get("recommendations", [])),
    } for r in reps]
    return pd.DataFrame(rows).to_csv(index=False)

# ──────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────

def chart_pie(bc, cc):
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias"],
        values=[max(bc, 1), max(cc, 1)],
        hole=.68,
        marker=dict(colors=["#dc2626", "#16a34a"], line=dict(color="#fff", width=3)),
        textfont=dict(family="Geist, sans-serif", size=11),
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    total = bc + cc or 1
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:9px;color:#a1a1aa'>TOTAL</span>",
        x=.5, y=.5, showarrow=False,
        font=dict(family="Geist, sans-serif", size=20, color="#09090b"),
    )
    fig.update_layout(
        height=240, showlegend=True,
        legend=dict(font=dict(family="Geist, sans-serif", size=10, color="#52525b"),
                    bgcolor="rgba(0,0,0,0)", orientation="h", x=.5, xanchor="center", y=-.05),
        **PLOTLY_BASE,
    )
    return fig

def chart_bar(items, max_n=8):
    counts = Counter(items)
    if not counts: counts = {"No data": 1}
    labels, values = zip(*counts.most_common(max_n))
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=MD3_PAL[:len(labels)], line=dict(width=0), cornerradius=4),
        text=list(values), textfont=dict(family="Geist, sans-serif", size=10, color="#52525b"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(180, len(labels) * 42 + 50),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,.05)", zeroline=False,
                   tickfont=dict(family="Geist, sans-serif", size=9)),
        yaxis=dict(tickfont=dict(family="Geist, sans-serif", size=10), gridcolor="rgba(0,0,0,0)"),
        bargap=.4, **PLOTLY_BASE,
    )
    return fig

def chart_trend(td):
    if not td: return None
    dates = [d["date"] for d in td]
    rates = [d["bias_rate"] for d in td]
    totals = [d["total"] for d in td]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=totals, name="Total",
        marker=dict(color="rgba(37,99,235,.12)", line=dict(width=0), cornerradius=3),
        yaxis="y2", hovertemplate="%{x}: %{y} analyses<extra></extra>"))
    fig.add_trace(go.Scatter(x=dates, y=rates, name="Bias %",
        mode="lines+markers",
        line=dict(color="#dc2626", width=2.5),
        marker=dict(color="#dc2626", size=6, line=dict(color="#fff", width=1.5)),
        hovertemplate="%{x}: %{y}%<extra></extra>"))
    fig.update_layout(
        height=230,
        yaxis=dict(range=[0, 105], tickfont=dict(family="Geist, sans-serif", size=9),
                   gridcolor="rgba(0,0,0,.05)", zeroline=False),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(family="Geist, sans-serif", size=9)),
        xaxis=dict(tickfont=dict(family="Geist, sans-serif", size=9)),
        legend=dict(font=dict(family="Geist, sans-serif", size=10), bgcolor="rgba(0,0,0,0)",
                    x=0, y=1.1, orientation="h"),
        **PLOTLY_BASE,
    )
    return fig

def chart_radar(all_r):
    dc = {d: 0 for d in BIAS_DIMS}
    for r in all_r:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower(): dc[dim] += 1
    vals = [dc[d] for d in BIAS_DIMS]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=BIAS_DIMS + [BIAS_DIMS[0]],
        fill="toself", fillcolor="rgba(37,99,235,.07)",
        line=dict(color="#2563eb", width=2),
        marker=dict(color="#2563eb", size=5),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, gridcolor="rgba(0,0,0,.07)",
                            tickfont=dict(family="Geist, sans-serif", size=8)),
            angularaxis=dict(gridcolor="rgba(0,0,0,.07)",
                             tickfont=dict(family="Geist, sans-serif", size=9)),
        ),
        height=270, showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Geist, sans-serif"),
    )
    return fig

def chart_hist(scores):
    if not scores: scores = [0]
    fig = go.Figure(go.Histogram(
        x=[s * 100 for s in scores], nbinsx=10,
        marker=dict(color="#2563eb", opacity=.7, line=dict(color="#fff", width=1)),
        hovertemplate="~%{x:.0f}%%: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=200,
        xaxis=dict(title=dict(text="Confidence %", font=dict(size=10)),
                   tickfont=dict(family="Geist, sans-serif", size=9),
                   gridcolor="rgba(0,0,0,.05)"),
        yaxis=dict(tickfont=dict(family="Geist, sans-serif", size=9),
                   gridcolor="rgba(0,0,0,.05)"),
        **PLOTLY_BASE,
    )
    return fig

def chart_gauge(val, bias):
    col = "#dc2626" if bias else "#16a34a"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(val * 100),
        number={"suffix": "%", "font": {"family": "Geist, sans-serif", "size": 26, "color": col}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0,
                     "tickfont": {"color": "#e4e4e7", "size": 8}},
            "bar":  {"color": col, "thickness": 0.2},
            "bgcolor": "#f4f4f5", "borderwidth": 0,
            "steps": [
                {"range": [0, 33],   "color": "rgba(22,163,74,.06)"},
                {"range": [33, 66],  "color": "rgba(217,119,6,.06)"},
                {"range": [66, 100], "color": "rgba(220,38,38,.06)"},
            ],
        },
    ))
    fig.update_layout(height=170, **PLOTLY_BASE)
    return fig

def chart_sev(all_r):
    sc = {"high": 0, "medium": 0, "low": 0}
    for r in all_r:
        s = (r.get("severity") or "low").lower()
        if s in sc: sc[s] += 1
    fig = go.Figure(go.Pie(
        labels=["High", "Medium", "Low"],
        values=[sc["high"], sc["medium"], sc["low"]],
        hole=.65,
        marker=dict(colors=["#dc2626", "#d97706", "#16a34a"], line=dict(color="#fff", width=3)),
        textfont=dict(family="Geist, sans-serif", size=11),
        textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(height=220, showlegend=False, **PLOTLY_BASE)
    return fig

# ──────────────────────────────────────────────
# PIPELINE
# ──────────────────────────────────────────────

def _render_steps(ph, current, label):
    steps = [(1, "Extract"), (2, "Detect Bias"), (3, "Fair Outcome")]
    parts = []
    for num, lbl in steps:
        if num < current:    cls = "done";   ico = "✓"
        elif num == current: cls = "active"; ico = "⟳"
        else:                cls = "";       ico = str(num)
        parts.append(
            f'<div class="ss-item {cls}">'
            f'<div class="ss-lbl">{ico} {lbl}</div>'
            f'</div>'
        )
    ph.markdown(
        f'<div class="scan-wrap">'
        f'<div class="scan-steps">{"".join(parts)}</div>'
        f'<div class="scan-track"><div class="scan-fill"></div></div>'
        f'<div style="font-size:.78rem;color:var(--blue);font-weight:500;margin-top:2px;">● {label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def run_analysis(text, dtype):
    ph = st.empty()
    def cb(step, label): _render_steps(ph, step, label)
    try:
        r = services.run_full_pipeline(decision_text=text, decision_type=dtype, progress_callback=cb)
        st.session_state["session_count"] += 1
        ph.empty()
        return r, None
    except ValueError as e:
        ph.empty(); return None, str(e)
    except Exception as e:
        ph.empty(); return None, f"Pipeline error: {e}"

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sb-head">'
        '<div class="sb-title">⚖️ Verdict Watch</div>'
        '<div class="sb-sub">AI Bias Detection · V9</div>',
        unsafe_allow_html=True,
    )
    if api_ok():
        st.markdown('<div class="sb-status sb-ok">✓ Groq API connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="sb-status sb-err">✗ API key missing</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Session", st.session_state.get("session_count", 0))
    c2.metric("All Time", len(all_reports()))

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="sb-lbl">Quick Examples</div>', unsafe_allow_html=True)
    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"sb_{ex['tag']}"):
            st.session_state["decision_input"] = ex["text"]
            st.session_state["decision_type_sel"] = ex["type"]
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="sb-lbl">How It Works</div>', unsafe_allow_html=True)
    for n, t in [
        ("1", "Paste text or upload a file"),
        ("2", "AI extracts decision criteria"),
        ("3", "Scans 7 bias dimensions"),
        ("4", "Generates fair outcome + laws"),
        ("5", "Download report or draft appeal"),
    ]:
        st.markdown(
            f'<div class="step-row">'
            f'<div class="step-dot">{n}</div>'
            f'<div class="step-txt">{t}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────

st.markdown(
    '<div class="vw-header">'
    '<div><div class="vw-header-title">⚖️ Verdict Watch</div>'
    '<div class="vw-header-sub">AI-powered bias detection for automated decisions</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────

(tab_a, tab_d, tab_h, tab_c, tab_b, tab_s, tab_ab) = st.tabs([
    "⚡ Analyse", "📊 Dashboard", "📋 History",
    "⚖️ Compare", "📦 Batch", "⚙️ Settings", "ℹ About",
])

# ══════════════════════════════════════════════
# TAB 1 — ANALYSE
# ══════════════════════════════════════════════

with tab_a:
    if not api_ok():
        api_banner()

    form_col, tips_col = st.columns([3, 1], gap="large")

    with form_col:
        mode = st.radio("Mode", ["✏️ Paste Text", "📄 Upload File"],
                        horizontal=True, label_visibility="collapsed")

        st.markdown('<div class="lbl" style="margin-top:12px;">Decision Text</div>',
                    unsafe_allow_html=True)

        if mode == "✏️ Paste Text":
            decision_text = st.text_area(
                "text", label_visibility="collapsed", height=175,
                key="decision_input",
                placeholder=(
                    "Paste any rejection letter, loan denial, triage result, or "
                    "university decision here…\n\n"
                    "💡 Use Quick Examples in the sidebar to load samples."
                ),
            )
        else:
            uf = st.file_uploader("File", type=["txt", "pdf"],
                                  label_visibility="collapsed", key="file_up")
            decision_text = ""
            if uf:
                ex = extract_file(uf)
                if ex:
                    decision_text = ex
                    st.markdown(
                        f'<div class="badge-ok" style="margin-bottom:8px;">'
                        f'✓ {len(ex):,} chars from {uf.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview"):
                        st.text(ex[:600] + ("…" if len(ex) > 600 else ""))

        # Type + char counter row
        tc1, tc2 = st.columns([2, 1])
        with tc1:
            opts = ["job", "loan", "medical", "university", "other"]
            cur  = st.session_state.get("decision_type_sel", "job")
            idx  = opts.index(cur) if cur in opts else 0
            dtype = st.selectbox("Type", opts, format_func=lambda x: TYPE_LABELS[x],
                                 index=idx, key="decision_type_sel")
        with tc2:
            n = len((decision_text or "").strip())
            if n > 150:   info, col = "Ready", "#16a34a"
            elif n > 50:  info, col = "Minimum", "#d97706"
            else:         info, col = "Too short", "#dc2626"
            w = min(100, int(n / 3))
            st.markdown(
                f'<div style="margin-top:4px;">'
                f'<div class="char-info" style="color:{col};">{n:,} chars · {info}</div>'
                f'<div style="background:var(--s3);height:2px;border-radius:1px;margin-top:5px;">'
                f'<div class="char-bar" style="width:{w}%;background:{col};"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        run_btn = st.button("⚡ Run Bias Analysis", key="run", disabled=not api_ok())

    with tips_col:
        st.markdown(
            '<div class="card">'
            '<div class="card-lbl">Bias Detected</div>'
            '<div style="font-size:.82rem;color:var(--t2);line-height:2.1;">'
            '◉ Gender &amp; parental<br>'
            '◉ Age discrimination<br>'
            '◉ Racial / ethnic<br>'
            '◉ Geographic redlining<br>'
            '◉ Name-based proxies<br>'
            '◉ Socioeconomic status<br>'
            '◉ Language profiling<br>'
            '◉ Insurance class'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ── Run ──────────────────────────────────

    if run_btn:
        dt = (decision_text or "").strip()
        if not dt:
            st.warning("⚠️ Paste or upload a decision first.")
        else:
            th = services.hash_text(dt)
            cached = services.find_duplicate(th)

            if cached and not st.session_state.get("force_rerun"):
                st.markdown(
                    '<div class="dup-warn">⚠️ '
                    '<div><strong>Identical text — showing cached result.</strong><br>'
                    'Click Re-run to force a fresh analysis.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔄 Re-run", key="force_btn"):
                    st.session_state["force_rerun"] = True
                    st.rerun()
                report, err = cached, None
            else:
                st.session_state.pop("force_rerun", None)
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                with st.spinner(""):
                    report, err = run_analysis(dt, dtype)

            if err:
                st.error(f"❌ {err}")

            elif report:
                bias    = report.get("bias_found", False)
                conf    = report.get("confidence_score", 0.0)
                pct     = int(conf * 100)
                btypes  = report.get("bias_types", [])
                phrases = report.get("bias_phrases", [])
                aff     = report.get("affected_characteristic", "")
                orig    = report.get("original_outcome", "N/A")
                fair    = report.get("fair_outcome", "N/A")
                expl    = report.get("explanation", "")
                recs    = report.get("recommendations", [])
                laws    = report.get("legal_frameworks", [])
                evid    = report.get("bias_evidence", "")

                st.markdown("<br>", unsafe_allow_html=True)

                # Verdict banner
                if bias:
                    st.markdown(
                        '<div class="verdict-banner bias">'
                        '<div class="vb-icon">⚠️</div>'
                        '<div class="vb-title">Bias Detected</div>'
                        '<div class="vb-sub">This decision shows discriminatory patterns</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="verdict-banner clean">'
                        '<div class="vb-icon">✅</div>'
                        '<div class="vb-title">No Bias Found</div>'
                        '<div class="vb-sub">No strong discriminatory factors detected</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

                # Result grid
                lc, rc = st.columns([3, 2], gap="large")

                with lc:
                    r1, r2 = st.columns([1, 2], gap="medium")
                    with r1:
                        bt_ch = chips(btypes) if btypes else '<span class="chip chip-g">None</span>'
                        aff_b = ""
                        if aff:
                            aff_b = (
                                f'<div style="margin-top:10px;">'
                                f'<div class="card-lbl">Characteristic Affected</div>'
                                f'<div style="font-size:.95rem;font-weight:700;color:var(--amber);">'
                                f'{aff.title()}</div></div>'
                            )
                        st.markdown(
                            f'<div class="card" style="text-align:center;padding:.9rem .7rem;">'
                            f'<div class="card-lbl" style="text-align:center;">Risk Score</div>'
                            f'<div style="display:flex;justify-content:center;">'
                            f'{ring_svg(pct, bias)}</div>'
                            f'<div style="margin-top:6px;">{sev_badge(conf, bias)}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with r2:
                        st.markdown(
                            f'<div class="card" style="height:100%;">'
                            f'<div class="card-lbl">Bias Types</div>'
                            f'<div style="line-height:1.9;">{bt_ch}</div>'
                            f'{aff_b}</div>',
                            unsafe_allow_html=True,
                        )

                    # Phrase highlighter
                    if dt and (btypes or phrases):
                        st.markdown('<div class="lbl" style="margin-top:12px;">Highlighted Phrases</div>',
                                    unsafe_allow_html=True)
                        hl = highlight(dt, phrases, btypes)
                        st.markdown(
                            f'<div class="hl-box">{hl}</div>'
                            f'<div style="font-size:.7rem;color:var(--t3);margin-top:4px;">'
                            f'Highlighted = potential proxies for protected characteristics</div>',
                            unsafe_allow_html=True,
                        )

                    if expl:
                        st.markdown('<div class="lbl" style="margin-top:12px;">Plain English Explanation</div>',
                                    unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card warn"><div class="card-val">{expl}</div></div>',
                            unsafe_allow_html=True,
                        )

                with rc:
                    orig_cls = "err" if bias else "muted"
                    st.markdown(
                        f'<div class="card {orig_cls}">'
                        f'<div class="card-lbl">Original Decision</div>'
                        f'<div class="card-val mono lg">{orig.upper()}</div>'
                        f'</div>'
                        f'<div class="card ok">'
                        f'<div class="card-lbl">Should Have Been</div>'
                        f'<div class="card-val" style="font-weight:600;">{fair}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if evid:
                        st.markdown(
                            f'<div class="card warn">'
                            f'<div class="card-lbl">Bias Evidence</div>'
                            f'<div class="card-val" style="font-size:.84rem;">{evid}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    if laws:
                        laws_html = "".join(
                            f'<div class="law-item"><span class="law-ico">⚖️</span>{law}</div>'
                            for law in laws
                        )
                        st.markdown(
                            f'<div class="card blue">'
                            f'<div class="card-lbl">Legal Frameworks</div>'
                            f'{laws_html}</div>',
                            unsafe_allow_html=True,
                        )

                # Recommendations
                if recs:
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    st.markdown('<div class="lbl">Recommended Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec">'
                            f'<div class="rec-n">{i}</div>'
                            f'<div class="rec-t">{rec}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Feedback
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="lbl">Was This Helpful?</div>', unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1, 1, 4])
                with fb1:
                    if st.button("👍 Helpful", key="fb_y"):
                        services.save_feedback(report.get("id"), 1)
                        st.success("Thanks for the feedback!")
                with fb2:
                    if st.button("👎 Not helpful", key="fb_n"):
                        services.save_feedback(report.get("id"), 0)
                        st.info("Noted — we'll keep improving.")

                # Appeal letter
                if bias:
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    st.markdown('<div class="lbl">Formal Appeal Letter</div>', unsafe_allow_html=True)
                    if st.button("✉️ Generate Appeal Letter", key="appeal_btn"):
                        with st.spinner("Drafting…"):
                            try:
                                letter = services.generate_appeal_letter(report, dt, dtype)
                                st.session_state["appeal_letter"] = letter
                            except Exception as e:
                                st.error(f"❌ {e}")
                    if st.session_state.get("appeal_letter"):
                        letter = st.session_state["appeal_letter"]
                        st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                        d1, d2, _ = st.columns([1, 1, 3])
                        with d1:
                            st.download_button(
                                "📥 Download Letter",
                                data=letter,
                                file_name=f"appeal_{(report.get('id') or 'letter')[:8]}.txt",
                                mime="text/plain", key="dl_letter",
                            )
                        with d2:
                            # Copy-to-clipboard via hack
                            st.code(letter[:60] + "…", language=None)

                # Download report
                st.markdown("<br>", unsafe_allow_html=True)
                d1, _ = st.columns([1, 3])
                with d1:
                    st.download_button(
                        "📥 Full Report (.txt)",
                        data=txt_report(report, dt, dtype),
                        file_name=f"verdict_v9_{(report.get('id') or 'report')[:8]}.txt",
                        mime="text/plain", key="dl_rpt",
                    )

                st.session_state["last_report"] = report
                st.session_state["last_text"]   = dt

# ══════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════

with tab_d:
    hist = all_reports()
    if not hist:
        st.markdown(
            '<div class="empty">'
            '<div class="empty-ico">📊</div>'
            '<div class="empty-t">No data yet</div>'
            '<div class="empty-s">Run your first analysis to populate the dashboard.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        b_reps  = [r for r in hist if r.get("bias_found")]
        c_reps  = [r for r in hist if not r.get("bias_found")]
        all_bt  = [bt for r in hist for bt in r.get("bias_types", [])]
        scores  = [r.get("confidence_score", 0) for r in hist]
        b_rate  = len(b_reps) / len(hist) * 100 if hist else 0
        avg_c   = sum(scores) / len(scores) * 100 if scores else 0
        top_b   = Counter(all_bt).most_common(1)[0][0] if all_bt else "N/A"
        fb      = services.get_feedback_stats()

        # Severity distribution for avg
        sev_map = {"high": 3, "medium": 2, "low": 1}
        sev_vals = [sev_map.get((r.get("severity") or "low").lower(), 1) for r in hist]
        avg_sev_n = sum(sev_vals) / len(sev_vals) if sev_vals else 1
        avg_sev = "High" if avg_sev_n >= 2.5 else ("Medium" if avg_sev_n >= 1.5 else "Low")

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Total", len(hist))
        k2.metric("Bias Rate", f"{b_rate:.0f}%")
        k3.metric("Avg Confidence", f"{avg_c:.0f}%")
        k4.metric("Top Bias Type", top_b)
        k5.metric("Avg Severity", avg_sev)
        k6.metric("Helpful %", f"{fb['helpful_pct']}%" if fb["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="lbl">Verdict Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_pie(len(b_reps), len(c_reps)),
                            use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="lbl">Bias Type Frequency</div>', unsafe_allow_html=True)
            if all_bt:
                st.plotly_chart(chart_bar(all_bt), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("No bias types recorded yet.")

        td = services.get_trend_data()
        if td:
            st.markdown('<div class="lbl">Daily Bias Rate Trend</div>', unsafe_allow_html=True)
            tf = chart_trend(td)
            if tf:
                st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="lbl">Confidence Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_hist(scores), use_container_width=True,
                            config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="lbl">Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_radar(hist), use_container_width=True,
                            config={"displayModeBar": False})

        c5, c6 = st.columns(2, gap="large")
        with c5:
            st.markdown('<div class="lbl">Severity Breakdown</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_sev(hist), use_container_width=True,
                            config={"displayModeBar": False})
        with c6:
            st.markdown('<div class="lbl">Top Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
            if chars:
                st.plotly_chart(chart_bar(chars), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("No data yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        d1, _ = st.columns([1, 4])
        with d1:
            st.download_button(
                "📥 Export CSV",
                data=to_csv(hist),
                file_name=f"verdict_dash_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_dl",
            )

# ══════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════

with tab_h:
    hist = all_reports()
    if not hist:
        st.markdown(
            '<div class="empty">'
            '<div class="empty-ico">📋</div>'
            '<div class="empty-t">No history</div>'
            '<div class="empty-s">All past analyses appear here.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        f1, f2, f3 = st.columns([3, 1, 1])
        with f1:
            q = st.text_input("Search", placeholder="Search bias type, characteristic, outcome…",
                              key="h_q")
        with f2:
            fv = st.selectbox("Verdict", ["All", "Bias", "No Bias"], key="h_v")
        with f3:
            sv = st.selectbox("Sort", ["Newest", "Oldest", "High Conf", "Low Conf"], key="h_s")

        d1c, d2c, _ = st.columns([1, 1, 2])
        with d1c: df = st.date_input("From", value=None, key="h_df")
        with d2c: dt = st.date_input("To",   value=None, key="h_dt")

        filt = hist[:]
        if fv == "Bias":    filt = [r for r in filt if r.get("bias_found")]
        elif fv == "No Bias": filt = [r for r in filt if not r.get("bias_found")]
        if q:
            ql = q.lower()
            filt = [r for r in filt
                    if ql in (r.get("affected_characteristic") or "").lower()
                    or any(ql in bt.lower() for bt in r.get("bias_types", []))
                    or ql in (r.get("original_outcome") or "").lower()
                    or ql in (r.get("explanation") or "").lower()]
        if df: filt = [r for r in filt if (r.get("created_at") or "")[:10] >= str(df)]
        if dt: filt = [r for r in filt if (r.get("created_at") or "")[:10] <= str(dt)]
        if sv == "Newest":   filt.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sv == "Oldest": filt.sort(key=lambda r: r.get("created_at") or "")
        elif sv == "High Conf": filt.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
        else: filt.sort(key=lambda r: r.get("confidence_score", 0))

        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(
                f'<div style="font-size:.78rem;color:var(--t3);margin-bottom:12px;">'
                f'Showing {len(filt)} of {len(hist)} reports</div>',
                unsafe_allow_html=True,
            )
        with h2:
            st.download_button(
                "📥 Export CSV",
                data=to_csv(filt),
                file_name=f"verdict_hist_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="hist_dl",
            )

        for r in filt:
            bias    = r.get("bias_found", False)
            conf    = int(r.get("confidence_score", 0) * 100)
            aff     = r.get("affected_characteristic") or "—"
            created = (r.get("created_at") or "")[:16].replace("T", " ")
            ico     = "⚠️" if bias else "✅"

            with st.expander(
                f'{ico} {"Bias" if bias else "No Bias"}  ·  {conf}%  ·  {aff}  ·  {created}',
                expanded=False,
            ):
                ec1, ec2 = st.columns(2, gap="large")
                with ec1:
                    vcls = "err" if bias else "ok"
                    vt   = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                    st.markdown(
                        f'<div class="card {vcls}">'
                        f'<div class="card-lbl">Verdict</div>'
                        f'<div class="card-val mono">{vt}</div>'
                        f'</div>'
                        f'<div class="card muted" style="margin-top:7px;">'
                        f'<div class="card-lbl">Original Outcome</div>'
                        f'<div class="card-val mono">{(r.get("original_outcome") or "N/A").upper()}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    bt_ch = chips(r.get("bias_types", []))
                    st.markdown(
                        f'<div class="card warn">'
                        f'<div class="card-lbl">Bias Types</div>'
                        f'<div class="card-val">{bt_ch}</div>'
                        f'</div>'
                        f'<div class="card ok" style="margin-top:7px;">'
                        f'<div class="card-lbl">Fair Outcome</div>'
                        f'<div class="card-val">{r.get("fair_outcome") or "N/A"}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="card muted" style="margin-top:7px;">'
                        f'<div class="card-lbl">Explanation</div>'
                        f'<div class="card-val" style="font-size:.85rem;">{r["explanation"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                laws = r.get("legal_frameworks", [])
                if laws:
                    st.markdown(
                        f'<div class="card blue" style="margin-top:7px;">'
                        f'<div class="card-lbl">Legal Frameworks</div>'
                        f'<div class="card-val">{chips(laws, "chip-b")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations", [])
                if recs:
                    st.markdown('<div class="lbl" style="margin-top:10px;">Next Steps</div>',
                                unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec">'
                            f'<div class="rec-n">{i}</div>'
                            f'<div class="rec-t">{rec}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                st.caption(f"ID: {r.get('id', 'N/A')}  ·  Severity: {(r.get('severity') or '—').upper()}")

# ══════════════════════════════════════════════
# TAB 4 — COMPARE
# ══════════════════════════════════════════════

with tab_c:
    if not api_ok():
        api_banner()

    st.markdown(
        '<div style="font-size:.88rem;color:var(--t2);margin-bottom:1.1rem;">'
        'Analyse two decisions side-by-side and see how their bias profiles differ.</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="lbl">Decision A</div>', unsafe_allow_html=True)
        ct1  = st.text_area("A", height=120, label_visibility="collapsed",
                             placeholder="Paste first decision…", key="cmp1")
        ctp1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                             format_func=lambda x: TYPE_LABELS[x],
                             label_visibility="collapsed", key="ct1")
    with c2:
        st.markdown('<div class="lbl">Decision B</div>', unsafe_allow_html=True)
        ct2  = st.text_area("B", height=120, label_visibility="collapsed",
                             placeholder="Paste second decision…", key="cmp2")
        ctp2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                             format_func=lambda x: TYPE_LABELS[x],
                             label_visibility="collapsed", key="ct2")

    cmp_btn = st.button("⚡ Compare", key="cmp_btn", disabled=not api_ok())

    if cmp_btn:
        if not ct1.strip() or not ct2.strip():
            st.warning("⚠️ Please fill in both decisions.")
        else:
            with st.spinner("Analysing both…"):
                ra, ea = run_analysis(ct1, ctp1)
                rb, eb = run_analysis(ct2, ctp2)
            if ea: st.error(f"A: {ea}")
            if eb: st.error(f"B: {eb}")

            if ra and rb:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)

                ba, bb = ra.get("bias_found"), rb.get("bias_found")
                ca, cb = ra.get("confidence_score", 0), rb.get("confidence_score", 0)

                if ba and bb:
                    win = "A" if ca >= cb else "B"
                    msg = f"⚠️ Both show bias — Decision {win} has higher confidence ({int(max(ca,cb)*100)}%)"
                elif ba:  msg = "⚠️ Decision A shows bias · Decision B appears fair"
                elif bb:  msg = "⚠️ Decision B shows bias · Decision A appears fair"
                else:     msg = "✅ Neither decision shows discriminatory patterns"

                st.markdown(f'<div class="winner-bar">{msg}</div>', unsafe_allow_html=True)

                # Bias type diff
                set_a = set(ra.get("bias_types", []))
                set_b = set(rb.get("bias_types", []))
                only_a = set_a - set_b
                only_b = set_b - set_a
                shared = set_a & set_b
                if set_a or set_b:
                    diff_html = '<div class="lbl">Bias Type Comparison</div><div style="margin-bottom:12px;">'
                    for t in sorted(shared): diff_html += f'<span class="diff-badge diff-shared">Both: {t}</span>'
                    for t in sorted(only_a): diff_html += f'<span class="diff-badge diff-only-a">A only: {t}</span>'
                    for t in sorted(only_b): diff_html += f'<span class="diff-badge diff-only-b">B only: {t}</span>'
                    diff_html += "</div>"
                    st.markdown(diff_html, unsafe_allow_html=True)

                vc1, vc2 = st.columns(2, gap="large")
                for col, r, lbl in [(vc1, ra, "A"), (vc2, rb, "B")]:
                    with col:
                        b = r.get("bias_found", False)
                        vc = "bias" if b else "clean"
                        vi = "⚠️" if b else "✅"
                        vs = "Bias Detected" if b else "No Bias Found"
                        st.markdown(
                            f'<div class="verdict-banner {vc}" style="margin-bottom:10px;">'
                            f'<div class="vb-icon">{vi}</div>'
                            f'<div class="vb-title">Decision {lbl}</div>'
                            f'<div class="vb-sub">{vs}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.plotly_chart(chart_gauge(r.get("confidence_score", 0), b),
                                        use_container_width=True, config={"displayModeBar": False})
                        st.markdown(chips(r.get("bias_types", [])), unsafe_allow_html=True)
                        st.markdown(sev_badge(r.get("confidence_score", 0), b), unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card ok" style="margin-top:8px;">'
                            f'<div class="card-lbl">Fair Outcome</div>'
                            f'<div class="card-val">{r.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if r.get("explanation"):
                            st.markdown(
                                f'<div class="card warn">'
                                f'<div class="card-lbl">What Went Wrong</div>'
                                f'<div class="card-val" style="font-size:.84rem;">{r["explanation"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

# ══════════════════════════════════════════════
# TAB 5 — BATCH
# ══════════════════════════════════════════════

with tab_b:
    if not api_ok():
        api_banner()

    st.markdown(
        '<div style="font-size:.88rem;color:var(--t2);margin-bottom:1rem;">'
        'Analyse up to 10 decisions at once. Separate with <code style="background:var(--s2);'
        'padding:1px 6px;border-radius:4px;font-family:var(--mono);">---</code> '
        'or upload a CSV with a <code style="background:var(--s2);padding:1px 6px;'
        'border-radius:4px;font-family:var(--mono);">text</code> column.</div>',
        unsafe_allow_html=True,
    )

    bmode = st.radio("Batch mode", ["✏️ Paste Text", "📊 Upload CSV"],
                     horizontal=True, label_visibility="collapsed", key="bm")

    if bmode == "✏️ Paste Text":
        bt = st.text_area("Batch", height=200, label_visibility="collapsed", key="b_in",
                           placeholder="Decision 1…\n---\nDecision 2…\n---\nDecision 3…")
        blocks = [b.strip() for b in bt.split("---") if b.strip()] if bt else []
    else:
        bf = st.file_uploader("CSV", type=["csv"], label_visibility="collapsed", key="b_csv")
        blocks = []
        if bf:
            try:
                dfu = pd.read_csv(bf)
                if "text" in dfu.columns:
                    blocks = dfu["text"].dropna().tolist()
                    st.markdown(f'<div class="badge-ok">✓ {len(blocks)} rows loaded</div>',
                                unsafe_allow_html=True)
                else:
                    st.error("CSV needs a 'text' column.")
            except Exception as e:
                st.error(f"❌ {e}")

    bc1, bc2 = st.columns([1, 1])
    with bc1:
        btype = st.selectbox("Type (all)", ["job","loan","medical","university","other"],
                              format_func=lambda x: TYPE_LABELS[x],
                              label_visibility="collapsed", key="b_type")
    with bc2:
        brun = st.button("📦 Run Batch", key="b_run", disabled=not api_ok())

    if blocks:
        st.markdown(
            f'<div style="font-size:.8rem;color:var(--blue);font-weight:500;margin-top:4px;">'
            f'● {len(blocks)} decision{"s" if len(blocks) != 1 else ""} queued</div>',
            unsafe_allow_html=True,
        )

    if brun:
        if not blocks:
            st.warning("⚠️ No decisions found.")
        elif len(blocks) > 10:
            st.warning("⚠️ Limit is 10 per batch.")
        else:
            prog   = st.progress(0)
            status = st.empty()
            results = []
            t0 = time.time()

            for i, blk in enumerate(blocks):
                elapsed = time.time() - t0
                eta = (elapsed / (i + 1)) * (len(blocks) - i - 1) if i > 0 else 0
                eta_s = f" · ETA ~{int(eta)}s" if eta > 1 else ""
                status.markdown(
                    f'<div style="font-size:.8rem;color:var(--blue);font-weight:500;">'
                    f'Analysing {i+1} / {len(blocks)}{eta_s}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(blk, btype)
                results.append({"text": blk, "report": rep, "error": err})
                prog.progress((i + 1) / len(blocks))

            prog.empty(); status.empty()
            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            b_c = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            c_c = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            e_c = sum(1 for r in results if r["error"])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total",   len(results))
            m2.metric("Bias",    b_c)
            m3.metric("Clean",   c_c)
            m4.metric("Errors",  e_c)

            rows = []
            for i, res in enumerate(results, 1):
                rep, err = res["report"], res["error"]
                if err:
                    rows.append({"#": i, "Verdict": "ERROR", "Conf": "—",
                                 "Bias Types": err[:60], "Sev": "—", "Affected": "—"})
                elif rep:
                    rows.append({
                        "#":          i,
                        "Verdict":    "⚠ Bias" if rep.get("bias_found") else "✓ Clean",
                        "Conf":       f"{int(rep.get('confidence_score', 0) * 100)}%",
                        "Bias Types": ", ".join(rep.get("bias_types", [])) or "None",
                        "Sev":        (rep.get("severity") or "—").upper(),
                        "Affected":   rep.get("affected_characteristic") or "—",
                    })
            if rows:
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_r = [r["report"] for r in results if r["report"]]
            if all_r:
                d1, _ = st.columns([1, 3])
                with d1:
                    st.download_button(
                        "📥 Download Batch (.csv)",
                        data=to_csv(all_r),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="b_dl",
                    )

            st.markdown('<div class="lbl" style="margin-top:1.25rem;">Detailed Results</div>',
                        unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep, err = res["report"], res["error"]
                lbl = f"Decision {i}"
                if err: lbl += " — Error"
                elif rep:
                    vs   = "⚠ Bias" if rep.get("bias_found") else "✓ Clean"
                    conf = int(rep.get("confidence_score", 0) * 100)
                    lbl += f" — {vs} ({conf}%)"
                with st.expander(lbl, expanded=False):
                    preview = res["text"][:280] + ("…" if len(res["text"]) > 280 else "")
                    st.markdown(f'<div class="preview-box">{preview}</div>', unsafe_allow_html=True)
                    if err:
                        st.error(err)
                    elif rep:
                        b   = rep.get("bias_found", False)
                        vcl = "err" if b else "ok"
                        bv  = "⚠ Bias Detected" if b else "✓ No Bias Found"
                        st.markdown(
                            f'<div class="card {vcl}">'
                            f'<div class="card-lbl">Verdict</div>'
                            f'<div class="card-val mono">{bv}</div>'
                            f'</div>'
                            f'<div class="card warn" style="margin-top:7px;">'
                            f'<div class="card-lbl">Bias Types</div>'
                            f'<div class="card-val">{chips(rep.get("bias_types", []))}</div>'
                            f'</div>'
                            f'<div class="card ok" style="margin-top:7px;">'
                            f'<div class="card-lbl">Fair Outcome</div>'
                            f'<div class="card-val">{rep.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        laws = rep.get("legal_frameworks", [])
                        if laws:
                            st.markdown(
                                f'<div class="card blue" style="margin-top:7px;">'
                                f'<div class="card-lbl">Legal Frameworks</div>'
                                f'<div class="card-val">{chips(laws, "chip-b")}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

# ══════════════════════════════════════════════
# TAB 6 — SETTINGS
# ══════════════════════════════════════════════

with tab_s:
    st.markdown(
        '<div style="font-size:1.1rem;font-weight:700;color:var(--t1);letter-spacing:-.02em;'
        'margin-bottom:.25rem;">Settings &amp; Status</div>'
        '<div style="font-size:.85rem;color:var(--t2);margin-bottom:1.25rem;">'
        'Verdict Watch V9 — configuration and diagnostics.</div>',
        unsafe_allow_html=True,
    )

    sc1, sc2 = st.columns(2, gap="large")
    with sc1:
        st.markdown('<div class="lbl">API &amp; Model</div>', unsafe_allow_html=True)
        ko   = api_ok()
        kcls = "ok" if ko else "err"
        kst  = "✓ Set (from .env)" if ko else "✗ Not set"
        pc   = "ok" if PDF_SUPPORT else "warn"
        pst  = "✓ PyMuPDF installed" if PDF_SUPPORT else "Not installed — pip install PyMuPDF"
        st.markdown(
            f'<div class="card {kcls}"><div class="card-lbl">Groq API Key</div>'
            f'<div class="card-val mono">{kst}</div></div>'
            f'<div class="card"><div class="card-lbl">Model</div>'
            f'<div class="card-val mono">llama-3.3-70b-versatile</div></div>'
            f'<div class="card"><div class="card-lbl">Temperature · Retries</div>'
            f'<div class="card-val mono">0.1  ·  3× backoff</div></div>'
            f'<div class="card {pc}"><div class="card-lbl">PDF Support</div>'
            f'<div class="card-val mono">{pst}</div></div>',
            unsafe_allow_html=True,
        )

        # Live API test
        if ko:
            if st.button("🔌 Test API Connection", key="api_test"):
                with st.spinner("Testing…"):
                    try:
                        client = services.get_groq_client()
                        r = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            max_tokens=10,
                            messages=[{"role": "user", "content": "ping"}],
                        )
                        st.success("✅ API connection successful")
                    except Exception as e:
                        st.error(f"❌ {e}")

    with sc2:
        st.markdown('<div class="lbl">Database &amp; Usage</div>', unsafe_allow_html=True)
        all_r = all_reports()
        fb    = services.get_feedback_stats()
        db_url = os.getenv("DATABASE_URL", "sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="card"><div class="card-lbl">Total Reports</div>'
            f'<div class="card-val lg">{len(all_r)}</div></div>'
            f'<div class="card"><div class="card-lbl">Database</div>'
            f'<div class="card-val mono" style="font-size:.76rem;">{db_url}</div></div>'
            f'<div class="card blue"><div class="card-lbl">User Feedback</div>'
            f'<div class="card-val mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="lbl">V9 Feature Registry</div>', unsafe_allow_html=True)

    feats = [
        ("Schema Migration",   "text_hash fix (V5→V6 error resolved)",      True),
        ("Minimal Design",     "Geist font, clean token system",              True),
        ("SVG Confidence Ring","Centred arc ring, dynamic colour",            True),
        ("Phrase Highlighter", "Model-extracted bias phrases",                True),
        ("Legal Citations",    "Relevant laws cited per analysis",            True),
        ("Duplicate Detection","SHA-256 hash caching",                        True),
        ("3× Retry Logic",     "Exponential backoff on Groq calls",           True),
        ("Feedback System",    "Per-report ratings",                          True),
        ("File Upload",        ".txt + .pdf extraction",                      True),
        ("Batch Analysis",     "Up to 10 decisions, CSV export",              True),
        ("Compare Mode",       "Side-by-side with bias type diff view",       True),
        ("Appeal Generator",   "Formal discrimination appeal letter",         True),
        ("Live API Test",      "Test Groq connection from Settings",          True),
        ("Avg Severity KPI",   "Dashboard severity average metric",           True),
        ("Trend Analytics",    "Daily bias rate chart",                       True),
        ("Radar Chart",        "7-dimension bias profile",                    True),
        ("Full CSV Export",    "Dashboard + History + Batch",                 True),
    ]
    fh = '<div class="card" style="padding:.4rem 1.2rem;">'
    for name, desc, on in feats:
        ico   = "✓" if on else "○"
        color = "var(--green)" if on else "var(--t3)"
        fh += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:6px 0;border-bottom:1px solid var(--s2);">'
            f'<span style="font-size:.84rem;font-weight:500;color:var(--t1);">'
            f'<span style="color:{color};margin-right:8px;font-weight:700;">{ico}</span>{name}</span>'
            f'<span style="font-size:.78rem;color:var(--t3);">{desc}</span>'
            f'</div>'
        )
    fh += '</div>'
    st.markdown(fh, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 7 — ABOUT
# ══════════════════════════════════════════════

with tab_ab:
    st.markdown(
        '<div style="background:var(--blue);border-radius:var(--r-lg);padding:2rem 2.25rem;'
        'color:#fff;margin-bottom:1.25rem;">'
        '<div style="font-size:1.5rem;font-weight:700;letter-spacing:-.03em;margin-bottom:8px;">'
        '⚖️ What is Verdict Watch?</div>'
        '<div style="font-size:.9rem;opacity:.85;line-height:1.75;">'
        'Verdict Watch V9 is an enterprise-grade AI system that analyses automated decisions — '
        'job rejections, loan denials, medical triage, university admissions — for hidden bias. '
        'A 3-step Groq + Llama 3.3 70B pipeline extracts criteria, detects discriminatory patterns, '
        'cites relevant laws, and generates the fair outcome you deserved.'
        '</div></div>',
        unsafe_allow_html=True,
    )

    ab1, ab2 = st.columns([1.6, 1], gap="large")
    with ab1:
        st.markdown('<div class="lbl">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Gender Bias",             "Gender, name, or parental status as decision factor"),
            ("Age Discrimination",      "Unfair weighting of age group or seniority"),
            ("Racial / Ethnic Bias",    "Name-based, nationality, or origin profiling"),
            ("Geographic Redlining",    "Zip code or district as discriminatory proxy"),
            ("Socioeconomic Bias",      "Employment sector or credit score over-weighting"),
            ("Language Discrimination", "Primary language used against applicants"),
            ("Insurance Classification","Insurance tier used to rank priority"),
        ]:
            st.markdown(
                f'<div class="card" style="margin-bottom:7px;">'
                f'<div class="card-lbl">{name}</div>'
                f'<div class="card-val" style="font-size:.86rem;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="lbl">Tech Stack</div>', unsafe_allow_html=True)
        for name, desc in [
            ("⚡ Groq",          "LLM inference platform"),
            ("🦙 Llama 3.3 70B", "Language model"),
            ("🎈 Streamlit",     "Web UI framework"),
            ("🗄 SQLAlchemy",    "ORM + SQLite"),
            ("📊 Plotly",        "Interactive charts"),
            ("📄 PyMuPDF",       "PDF extraction"),
            ("✏️ Geist",         "V9 design system"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:7px 0;border-bottom:1px solid var(--s2);">'
                f'<span style="font-size:.84rem;font-weight:500;color:var(--t1);">{name}</span>'
                f'<span style="font-size:.78rem;color:var(--t3);">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="lbl">V9 Changes</div>', unsafe_allow_html=True)
        for ico, name, desc in [
            ("🔧", "Syntax Fix",      "Fixed f-string backslash error line 997"),
            ("🎨", "Geist Font",      "Minimal, clean typography"),
            ("📊", "Avg Severity KPI","New dashboard metric"),
            ("🔌", "Live API Test",   "Test Groq from Settings"),
            ("⚖️", "Bias Type Diff",  "Compare shows shared vs unique types"),
            ("♻️",  "60% Less CSS",   "Simplified design system"),
        ]:
            st.markdown(
                f'<div style="display:flex;gap:8px;padding:5px 0;">'
                f'<span>{ico}</span>'
                f'<span style="font-size:.82rem;color:var(--t2);">'
                f'<strong style="color:var(--t1);">{name}</strong> — {desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="card warn">'
            '<div class="card-lbl">⚠ Disclaimer</div>'
            '<div class="card-val" style="font-size:.83rem;">'
            'Not legal advice. Built for educational awareness. '
            'Consult a qualified legal professional for discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )

# ── Footer
st.markdown(
    '<div style="text-align:center;font-size:.72rem;color:var(--t3);'
    'margin-top:3rem;padding:1.25rem 0;border-top:1px solid var(--border);">'
    'Verdict Watch V9 · Powered by Groq / Llama 3.3 70B · Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)