"""
app.py — Verdict Watch V16 — AI Governance Edition
Dark minimal redesign. Every element earns its place.
Design principle: reduce friction between the user and the answer.
"""

import streamlit as st
import services
import pandas as pd
import re, os, json, time
from datetime import datetime
from collections import Counter

try:
    import fitz as pymupdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

services.init_db()

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title="Verdict Watch",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════

TYPE_LABELS = {
    "job":        "Job application",
    "loan":       "Loan decision",
    "medical":    "Medical triage",
    "university": "University admission",
    "other":      "Other",
}

# Examples load real text into the analyser — not decorative
EXAMPLES = {
    "job": {
        "label":    "Job rejection",
        "bias":     "Gender · parental status",
        "type":     "job",
        "text":     "We regret to inform you that your application for the Senior Engineer role has not been successful. While your background demonstrates some relevant experience, we found that candidates who had returned to the workforce after an extended absence were not the right fit for our fast-paced environment. We are seeking individuals with entry-level enthusiasm who can commit to the role without distraction.",
    },
    "loan": {
        "label":    "Loan denial",
        "bias":     "Geographic redlining",
        "type":     "loan",
        "text":     "After reviewing your mortgage application, we are unable to approve the requested amount at this time. Our assessment of your neighbourhood risk profile, combined with your employment in the public sector, indicates an elevated default risk that falls outside our current lending criteria. We encourage you to reapply when your circumstances change.",
    },
    "medical": {
        "label":    "Medical triage",
        "bias":     "Age discrimination",
        "type":     "medical",
        "text":     "Patient triaged to low-priority queue. Given patient age (67) and overall condition, aggressive intervention is not recommended at this stage. Resources are better allocated to younger patients with higher long-term prognosis. Standard monitoring protocol to be applied.",
    },
    "university": {
        "label":    "University rejection",
        "bias":     "Racial · ethnic bias",
        "type":     "university",
        "text":     "Thank you for applying to our undergraduate programme. After careful review, your application has not been successful. We noted that your surname and secondary school background suggest a cultural fit that may not align with our academic community's expectations and traditions.",
    },
}

VIEWS = [
    ("analyse",   "Analyse",     "Scan a decision for bias"),
    ("batch",     "Batch Audit", "Audit up to 10 decisions at once"),
    ("dashboard", "Dashboard",   "Systemic patterns across all reports"),
    ("history",   "History",     "Browse and search past reports"),
]

# Pipeline steps: what each step does and which model runs it
PIPELINE_STEPS = [
    ("Scan",      "Which protected characteristics are present?",      "Gemini"),
    ("Extract",   "What criteria drove this decision?",                "Gemini"),
    ("Detect",    "Bias across 7 dimensions: gender, age, race…",      "Gemini"),
    ("Outcome",   "What should the result have been?",                 "Gemini"),
    ("Fairness",  "Counterfactual parity — would different demographics get a different result?", "Vertex AI"),
    ("Explain",   "Phrase-by-phrase: each biased word mapped to the law it violates.", "Vertex AI"),
]

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════

_DEFS = {
    "view":           "analyse",
    "last_report":    None,
    "last_text":      "",
    "last_dtype":     "job",
    "scan_mode":      "full",
    "ai_provider":    "auto",   # always auto — user doesn't choose
    "ai_model":       "gemini-2.0-flash",
    "decision_input": "",
    "appeal_letter":  None,
    "batch_results":  None,
    "session_count":  0,
}
for k, v in _DEFS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
# CSS — dark, minimal, meaningful
# ══════════════════════════════════════════════════════

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap');

:root {
  --bg:        #0e0e0f;
  --bg2:       #161618;
  --bg3:       #1e1e21;
  --bg4:       #26262b;
  --border:    rgba(255,255,255,0.07);
  --border2:   rgba(255,255,255,0.13);
  --text:      #e2e2e5;
  --muted:     #808088;
  --muted2:    #4a4a54;
  --accent:    #4f8ef7;
  --accent-d:  rgba(79,142,247,0.12);
  --danger:    #e05454;
  --danger-d:  rgba(224,84,84,0.1);
  --success:   #4caf82;
  --success-d: rgba(76,175,130,0.1);
  --warn:      #d4943a;
  --warn-d:    rgba(212,148,58,0.1);
  --mono:      'IBM Plex Mono', monospace;
  --sans:      'IBM Plex Sans', -apple-system, sans-serif;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
  font-family: var(--sans) !important;
  font-size: 13px !important;
  color: var(--text) !important;
  background: var(--bg) !important;
}

/* ── Hide Streamlit chrome ── */
footer, [data-testid="stStatusWidget"], [data-testid="stDecoration"],
#MainMenu, [data-testid="stToolbar"], [data-testid="stHeader"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"] { background: var(--bg) !important; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
  min-width: 210px !important;
  max-width: 210px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebar"] * {
  color: var(--text) !important;
  font-family: var(--sans) !important;
  font-size: 12px !important;
}

/* Nav buttons */
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: none !important;
  border-radius: 5px !important;
  color: var(--muted) !important;
  font-size: 12px !important;
  font-weight: 400 !important;
  padding: 7px 10px !important;
  text-align: left !important;
  width: 100% !important;
  box-shadow: none !important;
  transition: background 0.1s, color 0.1s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--bg3) !important;
  color: var(--text) !important;
  transform: none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: var(--accent-d) !important;
  color: var(--accent) !important;
  border: none !important;
}

/* ── Main buttons ── */
.stButton > button {
  font-family: var(--sans) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 5px !important;
  padding: 8px 18px !important;
  box-shadow: none !important;
  transition: opacity 0.1s !important;
}
.stButton > button:hover { opacity: 0.85 !important; transform: none !important; }
.stButton > button:disabled { opacity: 0.3 !important; background: var(--bg4) !important; color: var(--muted) !important; }
.stButton > button[kind="secondary"] {
  background: var(--bg3) !important;
  color: var(--muted) !important;
  border: 1px solid var(--border2) !important;
  font-size: 12px !important;
  font-weight: 400 !important;
  padding: 6px 14px !important;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--bg4) !important;
  color: var(--text) !important;
  opacity: 1 !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
  background: var(--bg3) !important;
  color: var(--muted) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 5px !important;
  font-family: var(--sans) !important;
  font-size: 12px !important;
  font-weight: 400 !important;
  box-shadow: none !important;
  padding: 6px 14px !important;
  transform: none !important;
}
.stDownloadButton > button:hover {
  background: var(--bg4) !important;
  color: var(--text) !important;
  transform: none !important;
}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
  font-family: var(--sans) !important;
  font-size: 13px !important;
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 6px !important;
  color: var(--text) !important;
  line-height: 1.6 !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
  border-color: var(--accent) !important;
  box-shadow: none !important;
}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {
  color: var(--muted2) !important;
}
.stTextArea label, .stTextInput label {
  font-size: 10px !important;
  font-weight: 500 !important;
  color: var(--muted2) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
}

/* ── Select ── */
.stSelectbox > div > div {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 5px !important;
  color: var(--text) !important;
  font-size: 12px !important;
}
.stSelectbox label {
  font-size: 10px !important;
  font-weight: 500 !important;
  color: var(--muted2) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
}

/* ── Radio ── */
.stRadio > div { gap: 4px !important; }
.stRadio > div > label {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 5px !important;
  padding: 5px 12px !important;
  font-size: 12px !important;
  color: var(--muted) !important;
  cursor: pointer !important;
  transition: all 0.1s !important;
}
.stRadio > div > label:has(input:checked) {
  background: var(--accent-d) !important;
  color: var(--accent) !important;
  border-color: rgba(79,142,247,0.3) !important;
}
.stRadio label:first-child {
  font-size: 10px !important;
  font-weight: 500 !important;
  color: var(--muted2) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
  background: none !important;
  border: none !important;
  padding: 0 !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  padding: 12px 14px !important;
}
[data-testid="metric-container"] label {
  font-size: 10px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  color: var(--muted) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-size: 22px !important;
  font-weight: 500 !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
}

/* ── Progress ── */
.stProgress > div > div { background: var(--accent) !important; border-radius: 2px !important; }
.stProgress > div { background: var(--bg3) !important; border-radius: 2px !important; height: 3px !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--bg2) !important;
  border: 1px dashed var(--border2) !important;
  border-radius: 6px !important;
}
[data-testid="stFileUploader"] * { color: var(--muted) !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  color: var(--text) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
}
.streamlit-expanderContent {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 6px 6px !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
  border-radius: 6px !important;
  overflow: hidden !important;
  border: 1px solid var(--border) !important;
}

/* ══════════════════════════════════
   COMPONENT LIBRARY
   Every class answers: what does
   this communicate?
   ══════════════════════════════════ */

/* Card — groups information that belongs together */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 10px;
}

/* Section label — tells the user what category of information follows */
.clbl {
  font-size: 10px;
  color: var(--muted2);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 10px;
  font-weight: 500;
}

/* Verdict banner — the first thing the user needs to see */
.verdict {
  border-radius: 7px;
  padding: 16px 18px;
  border: 1px solid;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.verdict-bias  { background: var(--danger-d);  border-color: rgba(224,84,84,0.25); }
.verdict-clean { background: var(--success-d); border-color: rgba(76,175,130,0.25); }
.v-title      { font-size: 15px; font-weight: 500; }
.v-title-bias  { color: var(--danger); }
.v-title-clean { color: var(--success); }
.v-sub        { font-size: 12px; color: var(--muted); margin-top: 3px; line-height: 1.5; }
.v-conf       { font-size: 28px; font-weight: 500; font-family: var(--mono); }
.v-conf-bias  { color: var(--danger); }
.v-conf-clean { color: var(--success); }

/* Bias type chips — each chip is a specific discrimination dimension found */
.chip { display: inline-block; border-radius: 4px; padding: 2px 8px; font-size: 11px; margin: 2px; }
.chip-r { background: var(--danger-d);  color: var(--danger);  border: 1px solid rgba(224,84,84,0.2); }
.chip-g { background: var(--success-d); color: var(--success); border: 1px solid rgba(76,175,130,0.2); }
.chip-a { background: var(--warn-d);    color: var(--warn);    border: 1px solid rgba(212,148,58,0.2); }
.chip-b { background: var(--accent-d);  color: var(--accent);  border: 1px solid rgba(79,142,247,0.2); }
.chip-n { background: var(--bg3);       color: var(--muted);   border: 1px solid var(--border2); }

/* Progress bar — shows a score on a 0–100 scale */
.bar-track { height: 3px; background: var(--bg4); border-radius: 2px; overflow: hidden; margin-top: 5px; }
.bar-fill  { height: 100%; border-radius: 2px; }

/* Pipeline step track — shows where in the 6-step process we are */
.step-track { display: flex; gap: 3px; margin: 8px 0; }
.step       { flex: 1; padding: 5px 3px; border-radius: 4px; text-align: center; font-size: 9px;
              letter-spacing: 0.04em; background: var(--bg3); color: var(--muted2);
              border: 1px solid var(--border); }
.step-done  { background: var(--success-d); color: var(--success); border-color: rgba(76,175,130,0.25); }
.step-active{ background: var(--accent-d);  color: var(--accent);  border-color: rgba(79,142,247,0.25); }

/* Biased phrase — verbatim evidence, monospace so it looks citable */
.phrase {
  border-left: 2px solid var(--danger);
  background: var(--danger-d);
  padding: 7px 12px;
  border-radius: 0 5px 5px 0;
  margin-bottom: 5px;
  font-size: 12px;
  color: var(--text);
  font-family: var(--mono);
  line-height: 1.5;
}
.phrase-meta {
  font-size: 11px;
  color: var(--muted);
  margin-top: 3px;
  font-family: var(--sans);
}
.phrase-law { color: var(--warn); }

/* Legal framework row — each law that was violated */
.law-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}
.law-row:last-child { border-bottom: none; }
.law-ico { color: var(--accent); font-size: 11px; flex-shrink: 0; margin-top: 1px; }

/* Recommendation row — numbered action the user should take */
.rec-row { display: flex; gap: 10px; align-items: flex-start; padding: 5px 0; }
.rec-n {
  width: 20px; height: 20px; border-radius: 4px;
  background: var(--bg3); border: 1px solid var(--border2);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; color: var(--muted); font-family: var(--mono);
  flex-shrink: 0; margin-top: 1px;
}
.rec-t { font-size: 13px; color: var(--muted); line-height: 1.6; }

/* Outcome boxes — original vs what should have happened */
.out-bias  { border-left: 2px solid var(--danger);  background: var(--danger-d);  padding: 12px 16px; border-radius: 0 6px 6px 0; }
.out-clean { border-left: 2px solid var(--success); background: var(--success-d); padding: 12px 16px; border-radius: 0 6px 6px 0; }
.out-lbl-r { font-size: 10px; color: var(--danger);  text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 5px; }
.out-lbl-g { font-size: 10px; color: var(--success); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 5px; }
.out-val-r { font-size: 14px; font-weight: 500; color: var(--danger);  font-family: var(--mono); }
.out-val-g { font-size: 13px; color: var(--success); line-height: 1.5; }

/* Appeal letter — monospace, looks like a real document */
.appeal-box {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px;
  font-size: 12px;
  line-height: 1.9;
  color: var(--muted);
  white-space: pre-wrap;
  font-family: var(--mono);
}

/* Batch item row */
.bitem {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.bitem:last-child { border-bottom: none; }
.bitem-n {
  width: 22px; height: 22px; border-radius: 4px;
  background: var(--bg3); border: 1px solid var(--border2);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; color: var(--muted); font-family: var(--mono); flex-shrink: 0;
}
.bitem-txt { flex: 1; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Empty state — patient, not apologetic */
.empty-state { text-align: center; padding: 60px 20px; color: var(--muted2); }
.empty-t     { font-size: 14px; margin-bottom: 6px; color: var(--muted); }
.empty-s     { font-size: 12px; line-height: 1.6; max-width: 300px; margin: 0 auto; }

/* Sidebar brand */
.sb-logo    { padding: 18px 14px 14px; border-bottom: 1px solid var(--border); }
.sb-name    { font-size: 14px; font-weight: 500; color: var(--text); display: flex; align-items: center; gap: 8px; }
.sb-sub     { font-size: 10px; color: var(--muted2); margin-top: 3px; letter-spacing: 0.05em; }
.sb-grp     { font-size: 9px; color: var(--muted2); letter-spacing: 0.1em; text-transform: uppercase;
              padding: 10px 10px 5px; }
.sb-foot    { padding: 12px 14px; border-top: 1px solid var(--border); }

/* Provider status dots — green = ready, amber = standby, red = missing */
.prow       { display: flex; align-items: center; gap: 7px; padding: 3px 0; font-size: 11px; color: var(--muted); }
.dot-s      { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
.dot-g      { background: var(--success); }
.dot-a      { background: var(--warn); }
.dot-r      { background: var(--danger); }

/* Topbar */
.topbar {
  height: 46px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 12px;
}
.topbar-title { font-size: 13px; font-weight: 500; color: var(--text); }
.topbar-sub   { font-size: 11px; color: var(--muted2); }
.topbar-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }

/* Diff row — compact key/value display */
.diff-row {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 5px 0; border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.diff-row:last-child { border-bottom: none; }
.diff-k { color: var(--muted); }
.diff-v { color: var(--muted2); font-size: 11px; font-family: var(--mono); }

/* Key error */
.key-err {
  background: var(--warn-d); border: 1px solid rgba(212,148,58,0.3);
  border-radius: 6px; padding: 10px 14px;
  font-size: 12px; color: var(--warn); margin-bottom: 14px;
  line-height: 1.6;
}

/* Example buttons in sidebar */
.ex-btn-type { font-size: 9px; color: var(--muted2); text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 2px; display: block; }
.ex-btn-bias { color: var(--danger); font-size: 11px; margin-top: 3px; display: block; }

/* Example buttons in right panel — make bias part red */
[data-testid="stSidebar"] ~ * .stButton [data-testid*="ex_"] button,
.stButton > button[kind="secondary"] {
  text-align: left !important;
  line-height: 1.4 !important;
}

/* Confidence hint — explains what the number means */
.conf-hint { font-size: 11px; color: var(--muted2); margin-top: 2px; line-height: 1.5; }

/* Style the native Streamlit sidebar collapse button */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 6px !important;
  color: var(--muted) !important;
  width: 32px !important;
  height: 32px !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
  background: var(--bg4) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

/* Sidebar toggle button */
.sb-toggle-btn {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 9999;
  background: var(--bg3);
  border: 1px solid var(--border2);
  border-radius: 6px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.sb-toggle-btn:hover { background: var(--bg4); border-color: var(--accent); }
.sb-toggle-btn svg { display: block; }
</style>
""", unsafe_allow_html=True)

inject_css()

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def gemini_ok():  return bool(os.getenv("GEMINI_API_KEY"))
def groq_ok():    return bool(os.getenv("GROQ_API_KEY"))
def vertex_ok():  return bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
def any_api_ok(): return gemini_ok() or groq_ok()

def _best_provider():
    """Always picks the best available provider — user never chooses."""
    if gemini_ok(): return "gemini"
    if groq_ok():   return "groq"
    return "gemini"

def all_reports():
    try:    return services.get_all_reports()
    except: return []

def _trunc(s, n): return s[:n] + "…" if len(s or "") > n else (s or "")

def sev_chip(sev, bias):
    if not bias:      return '<span class="chip chip-g">No bias</span>'
    s = (sev or "low").lower()
    if s == "high":   return '<span class="chip chip-r">High severity</span>'
    if s == "medium": return '<span class="chip chip-a">Medium severity</span>'
    return '<span class="chip chip-n">Low severity</span>'

def bias_chips(types):
    if not types: return '<span class="chip chip-n">None detected</span>'
    return "".join(f'<span class="chip chip-r">{t}</span>' for t in types)

def _score_color(val):
    if val >= 70: return "var(--success)"
    if val >= 40: return "var(--warn)"
    return "var(--danger)"

def bar_html(label, val, sub=None):
    col   = _score_color(val)
    v_str = sub if sub else f"{val} / 100"
    return f"""
<div style="margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
    <span style="color:var(--muted);">{label}</span>
    <span style="color:{col};font-family:var(--mono);">{v_str}</span>
  </div>
  <div class="bar-track"><div class="bar-fill" style="width:{min(val,100)}%;background:{col};"></div></div>
</div>"""

def steps_html(done=0, active=-1):
    """
    Renders the pipeline step track.
    done = number of completed steps (0–6)
    active = index of currently running step (-1 = none)
    Each step shows its label. Tooltip-style description lives in sidebar.
    """
    parts = []
    for i, (lbl, _, _) in enumerate(PIPELINE_STEPS):
        if i < done:
            parts.append(f'<div class="step step-done">✓ {lbl}</div>')
        elif i == active:
            parts.append(f'<div class="step step-active">… {lbl}</div>')
        else:
            parts.append(f'<div class="step">{i} {lbl}</div>')
    return '<div class="step-track">' + "".join(parts) + "</div>"

def run_analysis(text, dtype, mode="full", provider="gemini"):
    try:
        if mode == "quick":
            rep = services.quick_scan(text, dtype, provider)
        else:
            rep = services.run_full_pipeline(text, dtype, provider=provider)
        return rep, None
    except Exception as e:
        return None, str(e)

def to_csv(reps):
    rows = [{
        "id":            r.get("id",""),
        "created_at":    (r.get("created_at") or "")[:16].replace("T"," "),
        "decision_type": r.get("decision_type",""),
        "mode":          r.get("mode","full"),
        "ai_provider":   r.get("ai_provider","gemini"),
        "bias_found":    r.get("bias_found",False),
        "severity":      r.get("severity",""),
        "confidence":    int(r.get("confidence_score",0)*100),
        "bias_types":    "; ".join(r.get("bias_types",[])),
        "affected":      r.get("affected_characteristic",""),
        "original":      r.get("original_outcome",""),
        "fair":          r.get("fair_outcome",""),
        "explanation":   r.get("explanation",""),
        "legal":         "; ".join(r.get("legal_frameworks",[])),
        "next_steps":    " | ".join(r.get("recommendations",[])),
    } for r in reps if isinstance(r, dict)]
    return pd.DataFrame(rows).to_csv(index=False)

# ══════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════

with st.sidebar:
    gem = gemini_ok()
    grq = groq_ok()
    vtx = vertex_ok()

    # Brand
    st.markdown(f"""
<div class="sb-logo">
  <div class="sb-name">
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#4f8ef7" stroke-width="1.5">
      <path d="M8 1L2 4.5v5L8 13l6-3.5v-5z"/>
      <path d="M8 1v12M2 4.5l6 3.5 6-3.5"/>
    </svg>
    Verdict Watch
  </div>
  <div class="sb-sub">AI Bias Detection · V16</div>
</div>
""", unsafe_allow_html=True)

    # Navigation — each item has a purpose description
    st.markdown('<div class="sb-grp">Views</div>', unsafe_allow_html=True)
    for vid, vlabel, vdesc in VIEWS:
        is_active = st.session_state["view"] == vid
        if st.button(vlabel, key=f"nav_{vid}",
                     type="primary" if is_active else "secondary",
                     use_container_width=True):
            st.session_state["view"] = vid
            st.rerun()

    # Provider status — green/amber/red tells the user what's available
    st.markdown(f"""
<div class="sb-foot">
  <div class="prow">
    <span class="dot-s {'dot-g' if gem else 'dot-r'}"></span>
    Gemini — {'primary (Steps 0–3)' if gem else 'no key'}
  </div>
  <div class="prow">
    <span class="dot-s {'dot-g' if vtx else 'dot-a'}"></span>
    Vertex AI — {'governance (Steps 4–5)' if vtx else 'standby · Gemini fallback'}
  </div>
  <div class="prow">
    <span class="dot-s {'dot-g' if grq else 'dot-r'}"></span>
    Groq — {'fallback if Gemini fails' if grq else 'no key'}
  </div>
  <div style="font-size:10px;color:var(--muted2);margin-top:8px;line-height:1.5;">
    The pipeline always picks the best available provider automatically.
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# TOPBAR
# ══════════════════════════════════════════════════════

view      = st.session_state["view"]
view_meta = {v[0]: v for v in VIEWS}
view_desc = view_meta.get(view, ("","",""))[2]

st.markdown(f"""
<div class="topbar">
  <div>
    <div class="topbar-title">{view_meta.get(view,("","Verdict Watch",""))[1]}</div>
    <div class="topbar-sub">{view_desc}</div>
  </div>
  <div class="topbar-right">
    <span class="chip chip-n" style="font-size:10px;">6-step governance pipeline</span>
    {'<span class="chip chip-g" style="font-size:10px;">Gemini ready</span>' if gemini_ok() else '<span class="chip chip-r" style="font-size:10px;">No API key</span>'}
  </div>
</div>
<button class="sb-toggle-btn" onclick="
  var sb = window.parent.document.querySelector('[data-testid=stSidebar]');
  var btn = window.parent.document.querySelector('[data-testid=stSidebarCollapsedControl] button');
  if (btn) btn.click();
" title="Toggle sidebar">
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--muted)" stroke-width="1.5">
    <line x1="2" y1="4" x2="14" y2="4"/>
    <line x1="2" y1="8" x2="14" y2="8"/>
    <line x1="2" y1="12" x2="14" y2="12"/>
  </svg>
</button>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONTENT WRAPPER
# ══════════════════════════════════════════════════════

st.markdown('<div style="padding:18px 20px;">', unsafe_allow_html=True)

if not any_api_ok():
    st.markdown("""
<div class="key-err">
  No API key found. Add <code>GEMINI_API_KEY</code> or <code>GROQ_API_KEY</code> to your .env file and restart.
  <br>Without a key, the pipeline cannot run.
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW: ANALYSE
# ══════════════════════════════════════════════════════

if view == "analyse":
    col_left, col_right = st.columns([1, 0.36], gap="medium")

    with col_left:

        # ── Input ──
        # Why: The user pastes the verbatim text they received.
        # Verbatim matters — the AI looks for exact phrases, not summaries.
        st.markdown("""
<div class="card">
  <div class="clbl">Decision text</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:8px;line-height:1.5;">
    Paste the exact text of the rejection, denial, or triage note.
    Verbatim is better — the AI identifies specific biased phrases and maps them to the law violated.
  </div>
""", unsafe_allow_html=True)

        dec_text = st.text_area(
            "Decision text",
            value=st.session_state.get("decision_input", ""),
            height=130,
            placeholder="Paste any rejection letter, loan denial, medical triage note, or university decision here…",
            label_visibility="collapsed",
            key="dec_txt_input",
        )
        if dec_text != st.session_state.get("decision_input",""):
            st.session_state["decision_input"] = dec_text

        char_count = len(dec_text or "")
        hint_color = "var(--danger)" if char_count < 30 else "var(--success)"
        hint_text  = f"{char_count} chars · minimum 30" if char_count < 30 else f"{char_count} chars · ready to analyse"
        st.markdown(f'<div style="font-size:11px;color:{hint_color};margin:4px 0 10px;font-family:var(--mono);">{hint_text}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            # Decision type affects which legal frameworks are checked.
            # Job → Title VII. Loan → Fair Housing Act. Medical → ADA. University → Title VI.
            dtype = st.selectbox(
                "Decision type — affects legal frameworks checked",
                list(TYPE_LABELS.keys()),
                format_func=lambda x: TYPE_LABELS[x],
                index=list(TYPE_LABELS.keys()).index(st.session_state.get("last_dtype","job")),
                key="dtype_sel",
            )
        with c2:
            # Scan depth: Full runs all 6 steps (~15s). Quick = bias detection only (~4s).
            # Quick is useful for batch preview; Full is what the person in crisis needs.
            scan_mode = st.radio(
                "Scan depth — Full: all 6 steps (~15s). Quick: bias only (~4s)",
                ["full","quick"],
                format_func=lambda x: "Full · 6 steps" if x=="full" else "Quick · bias only",
                horizontal=True,
                key="scan_sel",
            )

        st.session_state["scan_mode"] = scan_mode
        st.markdown('</div>', unsafe_allow_html=True)

        run_btn = st.button(
            "Run analysis",
            key="run_btn",
            disabled=not any_api_ok() or char_count < 30,
        )

        # ── Result area ──
        report = st.session_state.get("last_report")
        dt     = st.session_state.get("last_text","")

        if run_btn:
            with st.spinner(""):
                ph    = st.empty()
                steps = [s[0] for s in PIPELINE_STEPS]
                for i in range(6):
                    ph.markdown(steps_html(i, i), unsafe_allow_html=True)
                    time.sleep(0.15)
                rep, err = run_analysis(dec_text, dtype, scan_mode, provider=_best_provider())
                ph.empty()
                if err:
                    st.error(f"Analysis failed: {err}")
                else:
                    st.session_state["last_report"]   = rep
                    st.session_state["last_text"]     = dec_text
                    st.session_state["last_dtype"]    = dtype
                    st.session_state["appeal_letter"] = None
                    st.session_state["session_count"] = st.session_state.get("session_count",0)+1
                    report = rep
                    st.rerun()

        if report and isinstance(report, dict):
            bias   = report.get("bias_found", False)
            conf   = int(report.get("confidence_score", 0) * 100)
            btypes = report.get("bias_types", [])
            aff    = report.get("affected_characteristic","")
            orig   = (report.get("original_outcome") or "N/A").upper()
            fair   = report.get("fair_outcome") or "N/A"
            expl   = report.get("explanation","")
            recs   = report.get("recommendations",[])
            laws   = report.get("legal_frameworks",[])
            phrases= report.get("bias_phrases",[])
            sev    = report.get("severity","low")
            mode_r = report.get("mode","full")
            fscore = report.get("fairness_scores",{})
            etrace = report.get("explainability_trace",{})
            cw     = report.get("characteristic_weights",{})

            done_steps = 4 if mode_r=="quick" else 6
            st.markdown(steps_html(done_steps), unsafe_allow_html=True)

            # ── VERDICT — first thing, biggest thing ──
            # The user needs to know the answer before they read the evidence.
            vcls   = "verdict-bias" if bias else "verdict-clean"
            vtcls  = "v-title-bias" if bias else "v-title-clean"
            vccls  = "v-conf-bias"  if bias else "v-conf-clean"
            vtitle = "Bias detected" if bias else "No bias found"
            vsub_parts = []
            if aff:     vsub_parts.append(aff.title())
            if sev and bias: vsub_parts.append(f"{sev.title()} severity")
            vsub = " · ".join(vsub_parts) if vsub_parts else ("Decision appears fair" if not bias else "")
            v_ico = (
                """<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="var(--danger)" stroke-width="2">
                     <path d="M9 2L16.5 15.5H1.5Z"/><line x1="9" y1="7" x2="9" y2="11"/>
                     <circle cx="9" cy="13.5" r="0.5" fill="var(--danger)"/>
                   </svg>""" if bias else
                """<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="var(--success)" stroke-width="2">
                     <polyline points="3,9 7.5,13.5 15,5"/>
                   </svg>"""
            )
            chips_html = bias_chips(btypes)

            st.markdown(f"""
<div class="verdict {vcls}">
  <div style="width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;
              background:{'var(--danger-d)' if bias else 'var(--success-d)'};flex-shrink:0;">
    {v_ico}
  </div>
  <div style="flex:1;">
    <div class="v-title {vtcls}">{vtitle}</div>
    <div class="v-sub">{vsub}</div>
    <div style="margin-top:7px;">{chips_html}</div>
  </div>
  <div style="text-align:right;flex-shrink:0;">
    <div class="v-conf {vccls}">{conf}%</div>
    <div class="conf-hint">confidence<br>AI's certainty, not legal proof</div>
  </div>
</div>""", unsafe_allow_html=True)

            # ── Original vs fair outcome ──
            # Side by side: what happened vs what should have happened.
            # The gap between these two is the harm.
            o1, o2 = st.columns(2)
            with o1:
                st.markdown(f'<div class="out-bias"><div class="out-lbl-r">Original outcome</div><div class="out-val-r">{orig}</div></div>', unsafe_allow_html=True)
            with o2:
                st.markdown(f'<div class="out-clean"><div class="out-lbl-g">Should have been</div><div class="out-val-g">{fair}</div></div>', unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

            # ── Explainability trace — the most important section ──
            # Each phrase is exact, verbatim evidence. Monospace = citable.
            # The characteristic and law follow each phrase — cause and effect.
            if etrace and isinstance(etrace, dict) and etrace.get("reasoning_chain"):
                chain = etrace.get("reasoning_chain",[])
                root  = etrace.get("root_cause","")
                retro = etrace.get("retroactive_correction","")
                chain_html = ""
                for step in chain[:5]:
                    phrase_txt = step.get("phrase","")
                    char_t     = step.get("characteristic_triggered","")
                    law_v      = step.get("legal_violation","")
                    if phrase_txt:
                        chain_html += f"""
<div class="phrase">
  "{phrase_txt}"
  <div class="phrase-meta">
    Targets: {char_t}
    {f'<span class="phrase-law"> · {law_v}</span>' if law_v else ''}
  </div>
</div>"""
                retro_html = f'<div style="font-size:12px;color:var(--success);margin-top:10px;padding:8px 12px;background:var(--success-d);border-radius:5px;line-height:1.6;"><strong>Correction:</strong> {retro}</div>' if retro else ""
                root_html  = f'<div style="font-size:12px;color:var(--danger);margin-bottom:8px;padding:6px 10px;background:var(--danger-d);border-radius:4px;">Root cause: {root}</div>' if root else ""
                st.markdown(f"""
<div class="card">
  <div class="clbl">Phrase-level evidence — exact words that triggered bias findings</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    Each phrase below is verbatim from the decision. Copy these when filing a complaint or writing your appeal.
  </div>
  {root_html}{chain_html}{retro_html}
</div>""", unsafe_allow_html=True)

            elif phrases or (bias and dt):
                # Fallback: raw phrase list from bias detection
                phrase_list = phrases[:5] if phrases else ([expl[:120]] if expl else [])
                if phrase_list:
                    phrase_html = "".join(f'<div class="phrase">"{p}"</div>' for p in phrase_list)
                    st.markdown(f'<div class="card"><div class="clbl">Bias evidence — phrases flagged</div>{phrase_html}</div>', unsafe_allow_html=True)

            # ── Legal frameworks ──
            # Each law listed was violated by this decision.
            # The user needs these names when contacting a lawyer or filing a complaint.
            if laws:
                rows_l = "".join(f'<div class="law-row"><span class="law-ico">§</span><div><strong style="color:var(--text);">{l}</strong></div></div>' for l in laws)
                st.markdown(f"""
<div class="card">
  <div class="clbl">Laws violated — cite these when filing a complaint or writing an appeal</div>
  {rows_l}
</div>""", unsafe_allow_html=True)

            # ── Fairness audit (Vertex AI Steps 4+5) ──
            # Demographic parity: would someone different have gotten a different result?
            # Score ≥ 70 = fair, 40–70 = partial disparity, < 40 = unfair.
            if fscore and isinstance(fscore, dict) and "overall_fairness_score" in fscore:
                fs     = fscore.get("overall_fairness_score", 0)
                fv     = fscore.get("fairness_verdict","")
                fsum   = fscore.get("audit_summary","")
                parity = fscore.get("demographic_parity_scores",{})
                fv_map = {"fair":"Fair — no counterfactual disparity",
                          "partially_fair":"Partial disparity detected",
                          "unfair":"Significant disparity — decision likely unfair"}
                fv_col_map = {"fair":"var(--success)","partially_fair":"var(--warn)","unfair":"var(--danger)"}
                fv_lbl = fv_map.get(fv, "—")
                fv_col = fv_col_map.get(fv, "var(--muted)")
                bars   = "".join(bar_html(k.replace("_"," ").title(), int(v)) for k,v in parity.items())

                st.markdown(f"""
<div class="card">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
    <div class="clbl" style="margin-bottom:0;">Fairness audit — Vertex AI</div>
    <span class="chip chip-b" style="font-size:10px;">Steps 4+5</span>
  </div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:12px;line-height:1.5;">
    Counterfactual test: would this decision have changed if the applicant had a different gender, age, or name?
    Score ≥ 70 is fair. Below 40 is significant disparity.
  </div>
  {bars}
  <div style="margin-top:10px;padding:8px 12px;background:var(--bg3);border-radius:5px;font-size:12px;">
    Overall: <span style="font-family:var(--mono);color:var(--text);font-weight:500;">{fs} / 100</span>
    &nbsp;·&nbsp; <span style="color:{fv_col};">{fv_lbl}</span>
  </div>
  {'<div style="font-size:11px;color:var(--muted2);margin-top:8px;line-height:1.5;">'+fsum+'</div>' if fsum else ''}
</div>""", unsafe_allow_html=True)

            # ── Characteristic weights (Step 0 pre-scan) ──
            # Shows how much each protected characteristic influenced the decision.
            # High influence + bias detected = strong case.
            if cw and isinstance(cw, dict):
                cw_html = "".join(bar_html(
                    k.replace("_"," ").title(), int(v), f"{int(v)}% influence"
                ) for k,v in sorted(cw.items(), key=lambda x:-x[1]))
                st.markdown(f"""
<div class="card">
  <div class="clbl">Characteristic influence — how heavily each protected characteristic featured in this decision</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    High influence on a protected characteristic combined with a biased outcome = strong evidence of discrimination.
  </div>
  {cw_html}
</div>""", unsafe_allow_html=True)

            # ── Recommendations ──
            # Numbered actions. One action per number. No waffle.
            if recs:
                recs_html = "".join(
                    f'<div class="rec-row"><div class="rec-n">{i+1}</div><div class="rec-t">{r}</div></div>'
                    for i, r in enumerate(recs)
                )
                st.markdown(f'<div class="card"><div class="clbl">What to do next</div>{recs_html}</div>', unsafe_allow_html=True)

            # ── Appeal letter — only shown when bias is found ──
            # No point generating an appeal if there's no bias.
            if bias:
                if st.button("Generate appeal letter", key="appeal_btn", type="secondary"):
                    with st.spinner("Drafting appeal…"):
                        try:
                            letter = services.generate_appeal_letter(
                                report, dt, dtype, provider=_best_provider())
                            st.session_state["appeal_letter"] = letter
                        except Exception as e:
                            st.error(f"Failed: {e}")

                if st.session_state.get("appeal_letter"):
                    letter = st.session_state["appeal_letter"]
                    st.markdown(f"""
<div class="card">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <div class="clbl" style="margin-bottom:0;">Appeal letter</div>
    <div style="font-size:11px;color:var(--muted2);">References exact phrases and laws found above</div>
  </div>
  <div class="appeal-box">{letter}</div>
  <div style="font-size:10px;color:var(--muted2);margin-top:8px;line-height:1.5;">
    Not legal advice. This letter is a starting point — review with a lawyer before sending.
  </div>
</div>""", unsafe_allow_html=True)
                    st.download_button(
                        "Download appeal letter (.txt)",
                        data=letter,
                        file_name=f"appeal_{(report.get('id') or 'x')[:8]}.txt",
                        mime="text/plain",
                        key="dl_letter",
                    )

            # ── Feedback — was this analysis useful? ──
            fb1, fb2, _ = st.columns([1,1,4])
            with fb1:
                if st.button("Helpful", key="fb_y", type="secondary"):
                    services.save_feedback(report.get("id",""), 1, "")
                    st.success("Thanks")
            with fb2:
                if st.button("Not helpful", key="fb_n", type="secondary"):
                    services.save_feedback(report.get("id",""), 0, "")

            # ── Export ──
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            st.download_button(
                "Export full report (.csv)",
                data=to_csv([report]),
                file_name=f"verdict_{(report.get('id') or 'r')[:8]}.csv",
                mime="text/csv",
                key="dl_rpt",
            )

        elif not report:
            st.markdown("""
<div class="empty-state">
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="var(--muted2)" stroke-width="1.5" style="margin:0 auto 14px;display:block;">
    <path d="M14 2L3 8v10l11 6 11-6V8z"/>
    <path d="M14 2v22M3 8l11 6 11-6"/>
  </svg>
  <div class="empty-t">No analysis yet</div>
  <div class="empty-s">
    Paste a rejection letter, loan denial, medical triage note,
    or university decision above — then click Run analysis.
  </div>
</div>""", unsafe_allow_html=True)

    # ── Right column ──
    with col_right:

        # Pipeline status card
        # Shows which steps completed and which model ran them.
        current_report = st.session_state.get("last_report")
        done = 0
        if current_report:
            done = 4 if current_report.get("mode","full")=="quick" else 6
        st.markdown(f"""
<div class="card">
  <div class="clbl">Pipeline status</div>
  {steps_html(done)}
  <div style="font-size:11px;color:var(--muted2);margin-top:6px;line-height:1.5;">
    Steps 0–3 run on Gemini. Steps 4–5 run on Vertex AI (enterprise governance layer).
    If Vertex AI is unavailable, Gemini handles all steps.
  </div>
</div>""", unsafe_allow_html=True)

        # Quick examples — clicking loads real text into the analyser
        st.markdown('<div class="card"><div class="clbl">Try an example — click to load</div>', unsafe_allow_html=True)
        for key, ex in EXAMPLES.items():
            label_html = f'<span style="display:block;font-size:12px;color:var(--text);">{ex["label"]}</span><span style="display:block;font-size:10px;color:var(--danger);margin-top:1px;">{ex["bias"]}</span>'
            btn_clicked = st.button(
                f"{ex['label']} · {ex['bias']}",
                key=f"ex_{key}",
                type="secondary",
                use_container_width=True,
            )
            if btn_clicked:
                st.session_state["decision_input"] = ex["text"]
                st.session_state["last_dtype"]     = ex["type"]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # File upload — for PDF rejection letters
        # Text is extracted automatically so the user doesn't need to copy-paste.
        st.markdown("""
<div class="card">
  <div class="clbl">Upload a document</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:8px;line-height:1.5;">
    Have a PDF rejection letter? Upload it — text is extracted and loaded into the analyser automatically.
  </div>
""", unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "PDF or text file",
            type=["txt","pdf"],
            label_visibility="collapsed",
            key="file_up",
        )
        if uploaded:
            fname = uploaded.name.lower()
            if fname.endswith(".txt"):
                content = uploaded.read().decode("utf-8", errors="replace")
                st.session_state["decision_input"] = content
                st.rerun()
            elif fname.endswith(".pdf"):
                if PDF_SUPPORT:
                    raw  = uploaded.read()
                    doc  = pymupdf.open(stream=raw, filetype="pdf")
                    content = "\n".join(p.get_text() for p in doc).strip()
                    if content:
                        st.session_state["decision_input"] = content
                        st.rerun()
                    else:
                        st.warning("Could not extract text from this PDF. The document may be scanned. Try pasting the text directly.")
                else:
                    st.warning("PDF support requires: pip install PyMuPDF")
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW: BATCH AUDIT
# Purpose: organisations auditing multiple decisions at once.
# Different audience from Analyse — HR teams, banks, researchers.
# ══════════════════════════════════════════════════════

elif view == "batch":
    col_left, col_right = st.columns([1, 0.36], gap="medium")

    with col_left:
        st.markdown("""
<div class="card">
  <div class="clbl">Decisions to audit</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    Paste up to 10 decisions separated by a blank line, or upload a CSV with a <code>text</code> column.
    Each decision runs the full 6-step pipeline independently.
  </div>
""", unsafe_allow_html=True)

        batch_mode = st.radio(
            "Input mode",
            ["Paste text","Upload CSV"],
            horizontal=True,
            label_visibility="collapsed",
            key="batch_mode",
        )

        blocks = []
        if batch_mode == "Paste text":
            bt = st.text_area(
                "Batch text",
                height=160,
                label_visibility="collapsed",
                key="b_in",
                placeholder="Decision 1: We regret to inform…\n\nDecision 2: After reviewing your loan application…",
            )
            blocks = [b.strip() for b in re.split(r'\n\s*\n', bt) if b.strip() and len(b.strip()) >= 30] if bt else []
            if not blocks and bt:
                blocks = [b.strip() for b in bt.split("---") if b.strip() and len(b.strip()) >= 30]
        else:
            bf = st.file_uploader("CSV file", type=["csv"], label_visibility="collapsed", key="b_csv")
            if bf:
                try:
                    dfu = pd.read_csv(bf)
                    if "text" in dfu.columns:
                        blocks = [t for t in dfu["text"].dropna().tolist() if len(str(t).strip()) >= 30]
                        st.markdown(f'<span class="chip chip-g">{len(blocks)} rows loaded from CSV</span>', unsafe_allow_html=True)
                    else:
                        st.error("CSV must have a 'text' column.")
                except Exception as e:
                    st.error(f"Could not read CSV: {e}")

        bc1, bc2 = st.columns(2)
        with bc1:
            btype = st.selectbox(
                "Decision type",
                list(TYPE_LABELS.keys()),
                format_func=lambda x: TYPE_LABELS[x],
                label_visibility="collapsed",
                key="b_type",
            )
        with bc2:
            q_count = len(blocks)
            q_color = "var(--success)" if q_count > 0 else "var(--muted2)"
            st.markdown(f'<div style="font-size:12px;color:{q_color};padding-top:6px;font-family:var(--mono);">{q_count} decision{"s" if q_count!=1 else ""} queued</div>', unsafe_allow_html=True)

        batch_run = st.button(
            "Run batch audit",
            key="b_run",
            disabled=not any_api_ok() or not blocks,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if batch_run:
            if len(blocks) > 10:
                st.warning("Maximum 10 decisions per batch. Only the first 10 will be processed.")
                blocks = blocks[:10]

            prog    = st.progress(0)
            status  = st.empty()
            results = []
            t0 = time.time()
            for i, blk in enumerate(blocks):
                elapsed = time.time() - t0
                eta     = (elapsed/(i+1))*(len(blocks)-i-1) if i > 0 else 0
                eta_str = f" · ~{int(eta)}s remaining" if eta > 2 else ""
                status.markdown(f'<div style="font-size:12px;color:var(--muted);font-family:var(--mono);">Analysing {i+1} of {len(blocks)}{eta_str}</div>', unsafe_allow_html=True)
                rep, err = run_analysis(blk, btype, "full", _best_provider())
                results.append({"text": blk, "report": rep, "error": err})
                prog.progress((i+1)/len(blocks))
            prog.empty()
            status.empty()
            st.session_state["batch_results"] = results

        batch_results = st.session_state.get("batch_results")
        if batch_results:
            valid = [r for r in batch_results if isinstance(r.get("report"), dict)]
            b_cnt = sum(1 for r in valid if r["report"].get("bias_found"))
            c_cnt = len(valid) - b_cnt
            e_cnt = sum(1 for r in batch_results if r.get("error"))
            avg_c = int(sum(r["report"].get("confidence_score",0) for r in valid)/len(valid)*100) if valid else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Processed", len(valid))
            m2.metric("Bias found", b_cnt)
            m3.metric("Clean", c_cnt)
            m4.metric("Avg confidence", f"{avg_c}%")

            items_html = ""
            for i, res in enumerate(batch_results, 1):
                rep = res.get("report"); err = res.get("error")
                txt_preview = _trunc(res.get("text",""), 65)
                if err:
                    items_html += f'<div class="bitem"><div class="bitem-n">{i}</div><div class="bitem-txt">{txt_preview}</div><span class="chip chip-r">Error</span></div>'
                elif isinstance(rep, dict):
                    bias_ = rep.get("bias_found",False)
                    conf_ = int(rep.get("confidence_score",0)*100)
                    sev_  = rep.get("severity","low")
                    lbl   = "Bias" if bias_ else "Clean"
                    rc    = "chip-r" if bias_ else "chip-g"
                    items_html += f'<div class="bitem"><div class="bitem-n">{i}</div><div class="bitem-txt">{txt_preview}</div><span class="chip {rc}">{lbl} · {conf_}%</span>{sev_chip(sev_, bias_)}</div>'

            st.markdown(f'<div class="card" style="padding:0;overflow:hidden;">{items_html}</div>', unsafe_allow_html=True)

            all_r = [r["report"] for r in valid]
            if all_r:
                try:
                    agg = services.generate_model_bias_report(all_r)
                    dim_par = agg.get("dim_parity_scores", {})
                    if dim_par:
                        bars_agg = "".join(bar_html(k.replace("_"," ").title(), int(v)) for k,v in dim_par.items())
                        st.markdown(f"""
<div class="card">
  <div class="clbl">Aggregate fairness — demographic parity across all {len(all_r)} decisions</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    Scores below 70 indicate systematic disparity for that characteristic across this batch.
  </div>
  {bars_agg}
</div>""", unsafe_allow_html=True)
                except:
                    pass

                st.download_button(
                    "Export all results (.csv)",
                    data=to_csv(all_r),
                    file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    key="b_dl",
                )

    with col_right:
        # Sample dataset — for demos and evaluators
        # Not surfaced prominently because it's not for the person in crisis
        st.markdown("""
<div class="card">
  <div class="clbl">Sample dataset</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    10 realistic past decisions as CSV — download, then upload above to demo the batch pipeline.
    Useful for evaluators and demos.
  </div>
""", unsafe_allow_html=True)
        try:
            sample_csv = services.generate_sample_dataset()
            st.download_button(
                "Download sample CSV",
                data=sample_csv,
                file_name="sample_decisions.csv",
                mime="text/csv",
                key="sample_dl",
                use_container_width=True,
            )
        except:
            pass
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
<div class="card">
  <div class="clbl">How batch audit works</div>
  <div class="diff-row"><span class="diff-k">Input</span><span class="diff-v">one per block or CSV</span></div>
  <div class="diff-row"><span class="diff-k">Per decision</span><span class="diff-v">full 6-step pipeline</span></div>
  <div class="diff-row"><span class="diff-k">Results</span><span class="diff-v">individual + aggregate</span></div>
  <div class="diff-row"><span class="diff-k">Aggregate</span><span class="diff-v">parity across all decisions</span></div>
  <div class="diff-row"><span class="diff-k">Limit</span><span class="diff-v">10 decisions per run</span></div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW: DASHBOARD
# Purpose: systemic patterns across many decisions.
# Audience: researchers, HR teams, policy advocates.
# ══════════════════════════════════════════════════════

elif view == "dashboard":
    hist = all_reports()
    if not hist:
        st.markdown("""
<div class="empty-state">
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="var(--muted2)" stroke-width="1.5" style="margin:0 auto 14px;display:block;">
    <polyline points="2,20 8,14 14,18 20,8 26,12"/>
  </svg>
  <div class="empty-t">No data yet</div>
  <div class="empty-s">
    Run your first analysis to populate the dashboard.
    The dashboard shows systemic patterns across all decisions — it needs at least a few reports to be useful.
  </div>
</div>""", unsafe_allow_html=True)
    else:
        b_reps = [r for r in hist if r.get("bias_found")]
        scores = [r.get("confidence_score",0) for r in hist]
        b_rate = round(len(b_reps)/len(hist)*100) if hist else 0
        avg_c  = round(sum(scores)/len(scores)*100) if scores else 0
        all_bt = [bt for r in hist for bt in r.get("bias_types",[])]

        avg_fs = None
        try:
            agg    = services.generate_model_bias_report(hist)
            avg_fs = agg.get("avg_fairness_score")
        except: pass

        # Top metrics — numbers that matter at a glance
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total analysed", len(hist))
        m2.metric("Bias detected",  len(b_reps))
        m3.metric("Bias rate",      f"{b_rate}%")
        m4.metric("Avg fairness",   f"{avg_fs}/100" if avg_fs is not None else "—")

        sev_map = {"high":0,"medium":0,"low":0}
        for r in hist:
            s = (r.get("severity") or "low").lower()
            sev_map[s] = sev_map.get(s,0)+1
        s1, s2, s3 = st.columns(3)
        s1.metric("High severity",  sev_map["high"])
        s2.metric("Medium severity",sev_map["medium"])
        s3.metric("Low / no bias",  sev_map["low"])

        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

        ch1, ch2 = st.columns(2, gap="medium")
        with ch1:
            # Top bias types — which discrimination is most common in this dataset
            counts = Counter(all_bt).most_common(6)
            bar_colors = ["var(--danger)","var(--warn)","var(--accent)","var(--success)","var(--muted)","var(--muted2)"]
            bars_html = ""
            if counts:
                max_c = max(c for _, c in counts)
                for i, (lbl, cnt) in enumerate(counts):
                    pct = int(cnt/max_c*100)
                    col = bar_colors[i % len(bar_colors)]
                    bars_html += f"""
<div style="margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
    <span style="color:var(--muted);">{lbl}</span>
    <span style="color:{col};font-family:var(--mono);">{cnt} cases</span>
  </div>
  <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{col};"></div></div>
</div>"""
            else:
                bars_html = '<div style="font-size:12px;color:var(--muted2);">No bias types recorded yet.</div>'

            st.markdown(f"""
<div class="card">
  <div class="clbl">Most frequent bias types</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    Which kinds of discrimination appear most often in your dataset.
  </div>
  {bars_html}
</div>""", unsafe_allow_html=True)

        with ch2:
            # Demographic parity per characteristic — systemic fairness view
            try:
                agg    = services.generate_model_bias_report(hist)
                dp     = agg.get("dim_parity_scores",{})
                if dp:
                    dp_html = "".join(bar_html(k.replace("_"," ").title(), int(v)) for k,v in dp.items())
                    dp_note = '<div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">Average parity score per characteristic across all decisions. Below 70 = systematic disparity.</div>'
                else:
                    dp_html = '<div style="font-size:12px;color:var(--muted2);">Run full analyses to see parity scores.</div>'
                    dp_note = ""
            except:
                dp_html = '<div style="font-size:12px;color:var(--muted2);">No fairness data yet.</div>'
                dp_note = ""
            st.markdown(f'<div class="card"><div class="clbl">Demographic parity by characteristic</div>{dp_note}{dp_html}</div>', unsafe_allow_html=True)

        # Recent explainability phrases — systemic language patterns
        recent_phrases = []
        for r in reversed(hist[:20]):
            et = r.get("explainability_trace",{})
            if isinstance(et, dict):
                for step in (et.get("reasoning_chain") or [])[:2]:
                    phrase = step.get("phrase","")
                    char_t = step.get("characteristic_triggered","")
                    law    = step.get("legal_violation","")
                    if phrase:
                        recent_phrases.append((phrase, char_t, law))
            if len(recent_phrases) >= 4:
                break

        if recent_phrases:
            phrases_html = "".join(f"""
<div class="phrase">
  "{p}"
  <div class="phrase-meta">
    {c}{f' <span class="phrase-law">· {l}</span>' if l else ''}
  </div>
</div>""" for p, c, l in recent_phrases[:4])
            st.markdown(f"""
<div class="card">
  <div class="clbl">Recent biased phrases — language patterns across decisions</div>
  <div style="font-size:12px;color:var(--muted2);margin-bottom:10px;line-height:1.5;">
    These phrases appeared in recent decisions and triggered bias findings.
    Recurring patterns indicate systemic language problems.
  </div>
  {phrases_html}
</div>""", unsafe_allow_html=True)

        dl_col, _ = st.columns([1,4])
        with dl_col:
            st.download_button(
                "Export all reports (.csv)",
                data=to_csv(hist),
                file_name=f"verdict_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="dash_dl",
            )

# ══════════════════════════════════════════════════════
# VIEW: HISTORY
# Purpose: browse, search, and revisit past analyses.
# Audience: individuals tracking their case, researchers.
# ══════════════════════════════════════════════════════

elif view == "history":
    hist = all_reports()
    if not hist:
        st.markdown("""
<div class="empty-state">
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="var(--muted2)" stroke-width="1.5" style="margin:0 auto 14px;display:block;">
    <line x1="4" y1="8" x2="22" y2="8"/>
    <line x1="4" y1="14" x2="22" y2="14"/>
    <line x1="4" y1="20" x2="16" y2="20"/>
  </svg>
  <div class="empty-t">No history yet</div>
  <div class="empty-s">Run your first analysis to see it here.</div>
</div>""", unsafe_allow_html=True)
    else:
        # Filters
        f1, f2, f3, f4 = st.columns([2,1,1,1])
        with f1:
            q = st.text_input("Search", placeholder="Search by bias type, characteristic, outcome…",
                              label_visibility="collapsed", key="h_q")
        with f2:
            ftype = st.selectbox("Type", ["All"]+list(TYPE_LABELS.values()),
                                 label_visibility="collapsed", key="h_t")
        with f3:
            fv = st.selectbox("Verdict", ["All","Bias","No bias"],
                              label_visibility="collapsed", key="h_v")
        with f4:
            sv = st.selectbox("Sort", ["Newest","Oldest","High confidence","Low confidence"],
                              label_visibility="collapsed", key="h_s")

        filt = list(hist)
        if fv == "Bias":    filt = [r for r in filt if r.get("bias_found")]
        elif fv == "No bias": filt = [r for r in filt if not r.get("bias_found")]
        if ftype != "All":
            inv = {v:k for k,v in TYPE_LABELS.items()}
            tc  = inv.get(ftype,"")
            if tc: filt = [r for r in filt if r.get("decision_type","") == tc]
        if q:
            ql = q.lower()
            filt = [r for r in filt if
                    ql in (r.get("affected_characteristic") or "").lower()
                    or any(ql in bt.lower() for bt in r.get("bias_types",[]))
                    or ql in (r.get("original_outcome") or "").lower()
                    or ql in (r.get("explanation") or "").lower()]
        if sv == "Newest":          filt.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sv == "Oldest":        filt.sort(key=lambda r: r.get("created_at") or "")
        elif sv == "High confidence": filt.sort(key=lambda r: r.get("confidence_score",0), reverse=True)
        else:                       filt.sort(key=lambda r: r.get("confidence_score",0))

        hdr1, hdr2 = st.columns([3,1])
        with hdr1:
            st.markdown(f'<div style="font-size:11px;color:var(--muted2);margin-bottom:12px;font-family:var(--mono);">Showing {len(filt)} of {len(hist)} reports</div>', unsafe_allow_html=True)
        with hdr2:
            st.download_button(
                "Export (.csv)",
                data=to_csv(filt),
                file_name=f"verdict_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="hist_dl",
            )

        # Summary table
        rows_data = []
        for r in filt[:100]:
            bias_   = r.get("bias_found",False)
            conf_   = int(r.get("confidence_score",0)*100)
            aff_    = _trunc(r.get("affected_characteristic") or "—", 20)
            created = (r.get("created_at") or "")[:10]
            sev_    = (r.get("severity") or "low").title()
            rid_    = (r.get("id") or "")[:8]
            dtype_  = TYPE_LABELS.get(r.get("decision_type","other"),"—")
            rows_data.append({
                "ID":          f"#{rid_}",
                "Type":        dtype_,
                "Result":      "Bias" if bias_ else "Clean",
                "Confidence":  f"{conf_}%",
                "Severity":    sev_,
                "Characteristic": aff_,
                "Date":        created,
            })
        if rows_data:
            st.dataframe(pd.DataFrame(rows_data), use_container_width=True, hide_index=True)

        # Expandable details
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="clbl">Report details</div>', unsafe_allow_html=True)
        for r in filt[:20]:
            bias_    = r.get("bias_found",False)
            conf_    = int(r.get("confidence_score",0)*100)
            aff_     = _trunc(r.get("affected_characteristic") or "unknown", 20)
            created  = (r.get("created_at") or "")[:10]
            rid_     = (r.get("id") or "")[:8]
            verdict_ = "Bias" if bias_ else "Clean"
            sev_     = (r.get("severity") or "low").title()
            title    = f"{verdict_} · #{rid_} · {conf_}% confidence · {aff_} · {created}"

            with st.expander(title, expanded=False):
                dc1, dc2 = st.columns(2, gap="medium")
                with dc1:
                    orig_ = (r.get("original_outcome") or "N/A").upper()
                    st.markdown(f'<div class="out-bias"><div class="out-lbl-r">Original outcome</div><div class="out-val-r">{orig_}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="margin-top:8px;"><div class="clbl">Bias types</div>{bias_chips(r.get("bias_types",[]))}</div>', unsafe_allow_html=True)
                with dc2:
                    fair_ = r.get("fair_outcome") or "N/A"
                    st.markdown(f'<div class="out-clean"><div class="out-lbl-g">Should have been</div><div class="out-val-g">{fair_}</div></div>', unsafe_allow_html=True)

                if r.get("explanation"):
                    st.markdown(f'<div style="margin-top:10px;font-size:12px;color:var(--muted);line-height:1.7;">{r["explanation"]}</div>', unsafe_allow_html=True)

                laws_ = r.get("legal_frameworks",[])
                if laws_:
                    rows_l = "".join(f'<div class="law-row"><span class="law-ico">§</span>{l}</div>' for l in laws_)
                    st.markdown(f'<div class="card" style="margin-top:10px;"><div class="clbl">Laws violated</div>{rows_l}</div>', unsafe_allow_html=True)

                recs_ = r.get("recommendations",[])
                if recs_:
                    recs_h = "".join(
                        f'<div class="rec-row"><div class="rec-n">{i+1}</div><div class="rec-t">{rec}</div></div>'
                        for i, rec in enumerate(recs_)
                    )
                    st.markdown(f'<div class="card" style="margin-top:10px;"><div class="clbl">What to do next</div>{recs_h}</div>', unsafe_allow_html=True)

                st.download_button(
                    "Download this report (.csv)",
                    data=to_csv([r]),
                    file_name=f"verdict_{(r.get('id') or 'x')[:8]}.csv",
                    mime="text/csv",
                    key=f"dl_{r.get('id','x')}",
                )

st.markdown('</div>', unsafe_allow_html=True)