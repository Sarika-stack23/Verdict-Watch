"""
streamlit_app.py — Verdict Watch V4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Built for: Google Solution Challenge 2026 — Build with AI
Problem Statement: Unbiased AI Decision Making
Powered by: Groq (Llama 3.3 70B) + Gemini (Google AI — mandatory for hackathon)

V4 New Features:
  • PDF / DOCX / image upload (extract decision text automatically)
  • Gemini integration (Google AI — required by hackathon rules)
  • Onboarding welcome modal for first-time users
  • Guided step-by-step flow (1 → 2 → 3)
  • Tooltips & help text everywhere
  • Mobile-friendly layout
  • Empty state illustrations
  • Cleaner navigation
  • Hackathon compliance badge (Google AI model used)
  • Fixed all V3 issues (alignment, spacing, font clarity)
"""

import streamlit as st
import services
import plotly.graph_objects as go
import pandas as pd
import re
import os
import io
import json
import base64
from datetime import datetime
from collections import Counter
from groq import Groq

# ── Optional imports for file parsing
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    import google.generativeai as genai
    GEMINI_SUPPORT = True
except ImportError:
    GEMINI_SUPPORT = False

# ── Init DB once
services.init_db()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch V4 — Unbiased AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS — V4 Design System
# Clean, editorial, high-contrast dark theme
# Font: Clash Display (headings) + Instrument Sans (body) + JetBrains Mono (code/data)
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;0,9..144,900;1,9..144,400&family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
  --ink:       #0a0c0f;
  --ink-2:     #13171e;
  --ink-3:     #1c222c;
  --ink-4:     #252d3a;
  --rule:      rgba(255,255,255,0.07);
  --rule-2:    rgba(255,255,255,0.13);
  --snow:      #f0f2f7;
  --snow-2:    #b8bfcc;
  --snow-3:    #5a6478;
  --lime:      #c6f135;
  --lime-d:    rgba(198,241,53,0.11);
  --lime-dd:   rgba(198,241,53,0.05);
  --coral:     #ff5c5c;
  --coral-d:   rgba(255,92,92,0.12);
  --teal:      #3effc8;
  --teal-d:    rgba(62,255,200,0.10);
  --amber:     #ffb830;
  --amber-d:   rgba(255,184,48,0.11);
  --violet:    #a78bfa;
  --violet-d:  rgba(167,139,250,0.12);
  --blue:      #60a5fa;
  --blue-d:    rgba(96,165,250,0.11);
  --r:         14px;
  --r-sm:      9px;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
  font-family: 'Instrument Sans', sans-serif;
  background: var(--ink) !important;
  color: var(--snow);
}

/* ── Sidebar */
[data-testid="stSidebar"] {
  background: var(--ink-2) !important;
  border-right: 1px solid var(--rule) !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

/* ── Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: var(--ink-3);
  border-radius: 12px;
  padding: 4px;
  gap: 2px;
  border: 1px solid var(--rule);
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 600;
  font-size: 0.82rem;
  color: var(--snow-3);
  background: transparent;
  border-radius: 9px;
  padding: 7px 14px;
  border: none;
  letter-spacing: 0.2px;
}
.stTabs [aria-selected="true"] {
  background: var(--lime) !important;
  color: #0a0c0f !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.8rem; }

/* ── Buttons */
.stButton > button {
  font-family: 'Instrument Sans', sans-serif;
  font-weight: 700;
  font-size: 0.88rem;
  background: var(--lime);
  color: #0a0c0f;
  border: none;
  border-radius: 10px;
  padding: 0.65rem 1.5rem;
  width: 100%;
  letter-spacing: 0.3px;
  transition: opacity 0.18s, transform 0.18s;
}
.stButton > button:hover { opacity: 0.84; transform: translateY(-1px); }
.stButton > button:active { transform: translateY(0); }

/* ── Inputs */
.stTextArea textarea {
  font-family: 'Instrument Sans', sans-serif !important;
  font-size: 0.93rem !important;
  background: var(--ink-3) !important;
  border: 1.5px solid var(--rule-2) !important;
  border-radius: 12px !important;
  color: var(--snow) !important;
  line-height: 1.75 !important;
}
.stTextArea textarea:focus {
  border-color: var(--lime) !important;
  box-shadow: 0 0 0 2px rgba(198,241,53,0.14) !important;
}
.stSelectbox > div > div {
  background: var(--ink-3) !important;
  border: 1.5px solid var(--rule-2) !important;
  border-radius: 10px !important;
  color: var(--snow) !important;
}
.stTextInput > div > div > input {
  background: var(--ink-3) !important;
  border: 1.5px solid var(--rule-2) !important;
  border-radius: 10px !important;
  color: var(--snow) !important;
  font-family: 'Instrument Sans', sans-serif !important;
}

/* ── File uploader */
[data-testid="stFileUploadDropzone"] {
  background: var(--ink-3) !important;
  border: 2px dashed var(--rule-2) !important;
  border-radius: 14px !important;
  transition: border-color 0.2s;
}
[data-testid="stFileUploadDropzone"]:hover {
  border-color: var(--lime) !important;
}

/* ── Metrics */
[data-testid="metric-container"] {
  background: var(--ink-3);
  border: 1px solid var(--rule);
  border-radius: var(--r);
  padding: 1.2rem 1.4rem;
}
[data-testid="metric-container"] label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.62rem !important;
  letter-spacing: 2.5px !important;
  text-transform: uppercase !important;
  color: var(--snow-3) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-family: 'Fraunces', serif !important;
  font-weight: 900 !important;
  font-size: 2.1rem !important;
  color: var(--snow) !important;
}

/* ── Progress */
.stProgress > div > div { background: var(--lime) !important; border-radius: 4px; }

/* ── Download button */
.stDownloadButton > button {
  background: var(--ink-3) !important;
  color: var(--lime) !important;
  border: 1.5px solid var(--lime) !important;
  font-family: 'Instrument Sans', sans-serif !important;
  font-weight: 600;
  border-radius: 10px !important;
  width: 100%;
}
.stDownloadButton > button:hover { background: var(--lime-d) !important; }

/* ── Expander */
.streamlit-expanderHeader {
  font-family: 'Instrument Sans', sans-serif !important;
  font-weight: 600 !important;
  background: var(--ink-3) !important;
  border-radius: 10px !important;
  border: 1px solid var(--rule) !important;
  color: var(--snow-2) !important;
}

/* ── Info / Warning */
.stAlert { border-radius: 12px !important; font-family: 'Instrument Sans', sans-serif !important; }

/* ─── CUSTOM COMPONENTS ─────────────────────────── */

/* Hero wordmark */
.v4-hero {
  padding: 2rem 0 1rem;
}
.v4-wordmark {
  font-family: 'Fraunces', serif;
  font-size: 3.2rem;
  font-weight: 900;
  color: var(--snow);
  letter-spacing: -2px;
  line-height: 1;
}
.v4-tagline {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--snow-3);
  margin-top: 0.5rem;
}
.v4-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--lime);
  color: #0a0c0f;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.58rem;
  font-weight: 500;
  letter-spacing: 1.5px;
  padding: 3px 8px;
  border-radius: 5px;
  vertical-align: middle;
  position: relative;
  top: -6px;
  margin-left: 8px;
}
.hackathon-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--lime-d);
  border: 1px solid rgba(198,241,53,0.3);
  color: var(--lime);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 1px;
  padding: 5px 12px;
  border-radius: 99px;
  margin-top: 0.8rem;
}

/* Step indicator */
.step-row {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 2rem;
}
.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  position: relative;
}
.step-item:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 16px;
  left: 58%;
  right: 0;
  height: 2px;
  background: var(--rule-2);
  z-index: 0;
}
.step-item.done:not(:last-child)::after { background: var(--lime); }
.step-num {
  width: 32px; height: 32px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  font-weight: 500;
  border: 2px solid var(--rule-2);
  color: var(--snow-3);
  background: var(--ink-3);
  z-index: 1;
}
.step-item.done .step-num {
  background: var(--lime);
  color: #0a0c0f;
  border-color: var(--lime);
}
.step-item.active .step-num {
  background: var(--ink-3);
  color: var(--lime);
  border-color: var(--lime);
  box-shadow: 0 0 0 4px rgba(198,241,53,0.12);
}
.step-label {
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.7rem;
  color: var(--snow-3);
  margin-top: 0.4rem;
  text-align: center;
}
.step-item.active .step-label, .step-item.done .step-label { color: var(--snow-2); }

/* Upload zone */
.upload-hint {
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.82rem;
  color: var(--snow-3);
  margin-top: 0.4rem;
  padding: 0.6rem 0.9rem;
  background: var(--lime-dd);
  border-radius: 8px;
  border-left: 3px solid var(--lime);
}

/* Verdict banners */
.verdict-bias {
  background: var(--coral-d);
  border: 1.5px solid rgba(255,92,92,0.4);
  border-radius: var(--r);
  padding: 1.8rem 2.2rem;
  text-align: center;
  box-shadow: 0 0 50px rgba(255,92,92,0.09);
}
.verdict-clean {
  background: var(--teal-d);
  border: 1.5px solid rgba(62,255,200,0.35);
  border-radius: var(--r);
  padding: 1.8rem 2.2rem;
  text-align: center;
  box-shadow: 0 0 50px rgba(62,255,200,0.07);
}
.v-icon { font-size: 2.2rem; }
.v-label {
  font-family: 'Fraunces', serif;
  font-size: 2rem;
  font-weight: 900;
  letter-spacing: -0.5px;
  margin-top: 0.3rem;
}
.verdict-bias  .v-label { color: var(--coral); }
.verdict-clean .v-label { color: var(--teal); }
.v-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 0.3rem;
  opacity: 0.55;
}
.verdict-bias  .v-sub { color: var(--coral); }
.verdict-clean .v-sub { color: var(--teal); }

/* Severity badges */
.sev-high   { background: var(--coral-d); color: #ff9090; border: 1px solid rgba(255,92,92,0.3);  border-radius: 6px; padding: 3px 11px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 1px; }
.sev-med    { background: var(--amber-d); color: #ffd47a; border: 1px solid rgba(255,184,48,0.3); border-radius: 6px; padding: 3px 11px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 1px; }
.sev-low    { background: var(--teal-d);  color: #80ffe0; border: 1px solid rgba(62,255,200,0.3); border-radius: 6px; padding: 3px 11px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 1px; }

/* Info cards */
.icard {
  background: var(--ink-3);
  border: 1px solid var(--rule);
  border-radius: var(--r);
  padding: 1rem 1.3rem;
  margin-bottom: 0.5rem;
}
.icard.coral  { border-left: 3px solid var(--coral); }
.icard.teal   { border-left: 3px solid var(--teal); }
.icard.amber  { border-left: 3px solid var(--amber); }
.icard.blue   { border-left: 3px solid var(--blue); }
.icard.violet { border-left: 3px solid var(--violet); }
.icard.lime   { border-left: 3px solid var(--lime); }
.ic-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--snow-3);
  margin-bottom: 0.45rem;
}
.ic-value {
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.92rem;
  color: var(--snow);
  line-height: 1.65;
}
.ic-value.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
}

/* Chips */
.chip { display: inline-block; padding: 3px 10px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; margin: 2px 3px 2px 0; }
.ch-coral  { background: var(--coral-d);  color: #ff9090; border: 1px solid rgba(255,92,92,0.25); }
.ch-teal   { background: var(--teal-d);   color: #7affdf; border: 1px solid rgba(62,255,200,0.25); }
.ch-blue   { background: var(--blue-d);   color: #93c5fd; border: 1px solid rgba(96,165,250,0.25); }
.ch-amber  { background: var(--amber-d);  color: #fcd68a; border: 1px solid rgba(255,184,48,0.25); }
.ch-violet { background: var(--violet-d); color: #c4b5fd; border: 1px solid rgba(167,139,250,0.25); }
.ch-muted  { background: rgba(255,255,255,0.04); color: var(--snow-3); border: 1px solid var(--rule); }

/* Recommendations */
.rec-item {
  display: flex; gap: 1rem; align-items: flex-start;
  background: var(--ink-3);
  border: 1px solid var(--rule);
  border-radius: 12px;
  padding: 0.9rem 1.2rem;
  margin-bottom: 0.55rem;
}
.rec-num {
  background: var(--lime);
  color: #0a0c0f;
  border-radius: 6px;
  min-width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem; font-weight: 500;
  flex-shrink: 0; margin-top: 1px;
}
.rec-text {
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.91rem;
  color: var(--snow-2);
  line-height: 1.6;
}

/* Highlight box */
.highlight-box {
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.92rem;
  line-height: 1.85;
  color: var(--snow-2);
  background: var(--ink-3);
  border: 1px solid var(--rule);
  border-radius: 12px;
  padding: 1.2rem 1.5rem;
}
.highlight-box mark {
  background: rgba(255,92,92,0.18);
  color: #ff9090;
  border-radius: 3px;
  padding: 1px 4px;
}

/* Appeal letter */
.appeal-box {
  background: var(--ink-3);
  border: 1.5px solid rgba(167,139,250,0.35);
  border-radius: var(--r);
  padding: 1.6rem 2rem;
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.88rem;
  line-height: 1.9;
  color: var(--snow-2);
  white-space: pre-wrap;
  box-shadow: 0 0 35px rgba(167,139,250,0.06);
}

/* Status pills */
.pill-ok   { display: inline-flex; align-items: center; gap: 6px; background: var(--teal-d);  border: 1px solid rgba(62,255,200,0.3);  color: var(--teal);  border-radius: 99px; padding: 4px 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 1px; }
.pill-warn { display: inline-flex; align-items: center; gap: 6px; background: var(--amber-d); border: 1px solid rgba(255,184,48,0.3);  color: var(--amber); border-radius: 99px; padding: 4px 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 1px; }
.pill-err  { display: inline-flex; align-items: center; gap: 6px; background: var(--coral-d); border: 1px solid rgba(255,92,92,0.3);   color: var(--coral); border-radius: 99px; padding: 4px 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 1px; }

/* Section labels */
.sec-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--snow-3);
  margin-bottom: 0.7rem;
}
.divider { border: none; border-top: 1px solid var(--rule); margin: 1.8rem 0; }

/* Empty state */
.empty-state {
  text-align: center;
  padding: 3.5rem 2rem;
  background: var(--ink-3);
  border: 1px dashed var(--rule-2);
  border-radius: var(--r);
  color: var(--snow-3);
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; opacity: 0.5; }
.empty-title { font-family: 'Fraunces', serif; font-size: 1.2rem; color: var(--snow-2); margin-bottom: 0.4rem; }
.empty-sub { font-family: 'Instrument Sans', sans-serif; font-size: 0.85rem; }

/* How-to steps in sidebar */
.hw { display: flex; gap: 0.7rem; align-items: flex-start; margin-bottom: 0.65rem; }
.hw-n { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--lime); min-width: 18px; padding-top: 1px; }
.hw-t { font-family: 'Instrument Sans', sans-serif; font-size: 0.8rem; color: var(--snow-3); line-height: 1.5; }

/* Extracted text preview */
.extracted-preview {
  background: var(--ink-4);
  border: 1px solid var(--rule-2);
  border-radius: 10px;
  padding: 1rem 1.3rem;
  font-family: 'Instrument Sans', sans-serif;
  font-size: 0.85rem;
  color: var(--snow-2);
  line-height: 1.7;
  max-height: 180px;
  overflow-y: auto;
  white-space: pre-wrap;
}

/* Feature cards (About tab) */
.feat-card {
  background: var(--ink-3);
  border: 1px solid var(--rule);
  border-radius: var(--r);
  padding: 1rem 1.3rem;
  margin-bottom: 0.5rem;
  transition: border-color 0.2s;
}
.feat-card:hover { border-color: var(--lime); }
.feat-title { font-family: 'Instrument Sans', sans-serif; font-size: 0.9rem; font-weight: 700; color: var(--snow); margin-bottom: 0.2rem; }
.feat-desc  { font-family: 'Instrument Sans', sans-serif; font-size: 0.82rem; color: var(--snow-3); }

/* Compare header */
.cmp-header {
  font-family: 'Fraunces', serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--snow);
  margin-bottom: 0.5rem;
}

/* Footer */
.footer-bar {
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 1.5px;
  color: var(--snow-3);
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--rule);
  text-transform: uppercase;
}
.footer-bar a { color: var(--lime); text-decoration: none; }

/* Gemini badge */
.gemini-badge {
  display: inline-flex; align-items: center; gap: 7px;
  background: linear-gradient(135deg, rgba(96,165,250,0.12), rgba(167,139,250,0.12));
  border: 1px solid rgba(96,165,250,0.3);
  border-radius: 99px;
  padding: 5px 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.63rem;
  color: var(--blue);
  letter-spacing: 1px;
}

/* Info tooltip */
.tip {
  display: inline-block;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: var(--ink-4);
  border: 1px solid var(--rule-2);
  color: var(--snow-3);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  text-align: center;
  line-height: 16px;
  cursor: help;
  margin-left: 5px;
  vertical-align: middle;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--ink-2); }
::-webkit-scrollbar-thumb { background: var(--ink-4); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--snow-3); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

EXAMPLES = [
    {"tag": "Job Rejection",      "emoji": "💼", "type": "job",
     "text": ("Thank you for applying to the Software Engineer position. After careful review "
              "we have decided not to move forward. We felt other candidates were a stronger "
              "fit for our team culture at this time.")},
    {"tag": "Bank Loan Denial",   "emoji": "🏦", "type": "loan",
     "text": ("Your loan application has been declined. Primary reasons: insufficient credit "
              "history, residential area risk score, employment sector classification. "
              "You may reapply after 6 months.")},
    {"tag": "Medical Triage",     "emoji": "🏥", "type": "medical",
     "text": ("Based on your intake assessment you have been assigned Priority Level 3. "
              "Factors considered: age group, reported pain level, primary language, "
              "insurance classification.")},
    {"tag": "University Rejection","emoji": "🎓", "type": "university",
     "text": ("We regret to inform you that your application for admission has not been "
              "successful. Our admissions committee considered zip code region diversity "
              "metrics, legacy status, and extracurricular profile alignment.")},
    {"tag": "Insurance Denial",   "emoji": "📋", "type": "other",
     "text": ("After reviewing your claim, we are unable to provide coverage. Contributing "
              "factors include: neighborhood risk classification, occupational hazard tier, "
              "and historical claims ratio in your zip code.")},
]

TYPE_LABELS = {
    "job":        "💼  Job / Hiring",
    "loan":       "🏦  Bank Loan / Credit",
    "medical":    "🏥  Medical / Triage",
    "university": "🎓  University Admission",
    "other":      "📄  Other Decision",
}

BIAS_KEYWORDS = {
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|housewife|mrs|mr)\b",
    "Age":           r"\b(age group|senior|junior|young|old|millennial|boomer|retirement|elderly|youth)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|name|surname)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|occupation|class|status)\b",
    "Language":      r"\b(primary language|language|accent|english|bilingual|native speaker)\b",
    "Insurance":     r"\b(insurance|coverage|uninsured|medicaid|medicare|policy|insurance classification)\b",
}

CHIP_STYLES = ["ch-coral", "ch-amber", "ch-blue", "ch-teal", "ch-violet"]
BIAS_DIMS   = ["Gender", "Age", "Racial", "Geographic", "Socioeconomic", "Language", "Insurance"]

ACCEPTED_FILE_TYPES = ["pdf", "docx", "txt", "png", "jpg", "jpeg"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_api_key() -> str:
    if st.session_state.get("groq_api_key"):
        return st.session_state["groq_api_key"]
    return os.getenv("GROQ_API_KEY", "")

def get_gemini_key() -> str:
    if st.session_state.get("gemini_api_key"):
        return st.session_state["gemini_api_key"]
    return os.getenv("GEMINI_API_KEY", "")

def set_env_keys():
    if get_api_key():   os.environ["GROQ_API_KEY"]   = get_api_key()
    if get_gemini_key(): os.environ["GEMINI_API_KEY"] = get_gemini_key()

def check_groq_key() -> bool:  return bool(get_api_key())
def check_gemini_key() -> bool: return bool(get_gemini_key())

def run_analysis(text: str, dtype: str) -> tuple:
    set_env_keys()
    try:
        report = services.run_full_pipeline(decision_text=text, decision_type=dtype)
        return report, None
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Pipeline error: {str(e)}"

def get_all_reports() -> list:
    try:
        return services.get_all_reports()
    except Exception:
        return []

# ── File text extraction ──────────────────────

def extract_text_from_file(uploaded_file) -> str:
    """Extract text from PDF, DOCX, TXT, or image file."""
    fname = uploaded_file.name.lower()
    content = uploaded_file.read()

    if fname.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    if fname.endswith(".pdf"):
        if not PDF_SUPPORT:
            return "[PDF parsing unavailable — install PyMuPDF: pip install PyMuPDF]"
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            return text.strip() or "[PDF has no extractable text — may be scanned]"
        except Exception as e:
            return f"[PDF parse error: {e}]"

    if fname.endswith(".docx"):
        if not DOCX_SUPPORT:
            return "[DOCX parsing unavailable — install python-docx: pip install python-docx]"
        try:
            doc = DocxDocument(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            return f"[DOCX parse error: {e}]"

    if fname.endswith((".png", ".jpg", ".jpeg")):
        # Use Gemini Vision if available, else placeholder
        if check_gemini_key() and GEMINI_SUPPORT:
            try:
                genai.configure(api_key=get_gemini_key())
                model = genai.GenerativeModel("gemini-1.5-flash")
                img_data = base64.b64encode(content).decode()
                ext = fname.rsplit(".", 1)[-1]
                mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
                response = model.generate_content([
                    "Extract all text from this document image. Return only the raw text, "
                    "no formatting or commentary.",
                    {"mime_type": mime, "data": img_data},
                ])
                return response.text.strip()
            except Exception as e:
                return f"[Gemini Vision error: {e}]"
        else:
            return ("[Image OCR requires Gemini API key. Add your GEMINI_API_KEY in the sidebar, "
                    "or paste the text manually below.]")

    return "[Unsupported file type]"


def generate_appeal_letter(report: dict, decision_text: str, decision_type: str) -> str:
    set_env_keys()
    client = services.get_groq_client()
    bias_types  = ", ".join(report.get("bias_types", [])) or "undisclosed bias"
    affected    = report.get("affected_characteristic", "a protected characteristic")
    explanation = report.get("explanation", "")
    fair_outcome = report.get("fair_outcome", "a fair reassessment")

    system = (
        "You are an expert legal writer specialising in discrimination and bias cases. "
        "Write formal, persuasive appeal letters in plain English. "
        "Use [DATE], [YOUR NAME], [YOUR ADDRESS], [RECIPIENT NAME/TITLE], [ORGANISATION] "
        "as placeholders. Write in first person."
    )
    prompt = (
        f"Write a formal appeal letter based on:\n\n"
        f"Decision type: {decision_type}\n"
        f"Original decision: {decision_text}\n"
        f"Bias detected: {bias_types}\n"
        f"Characteristic affected: {affected}\n"
        f"What was wrong: {explanation}\n"
        f"Fair outcome should be: {fair_outcome}\n\n"
        "The letter should: open professionally, reference the specific decision, "
        "clearly state grounds for appeal citing discriminatory factors, "
        "request a formal review, close professionally. Under 400 words."
    )
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def gemini_plain_explanation(report: dict) -> str:
    """Use Gemini to generate a very plain-English explanation for non-technical users."""
    if not check_gemini_key() or not GEMINI_SUPPORT:
        return ""
    try:
        genai.configure(api_key=get_gemini_key())
        model = genai.GenerativeModel("gemini-1.5-flash")
        bias_types   = ", ".join(report.get("bias_types", [])) or "unknown"
        affected     = report.get("affected_characteristic", "unknown")
        fair_outcome = report.get("fair_outcome", "unknown")
        prompt = (
            f"Explain in 2-3 simple sentences (like explaining to a non-technical person) "
            f"why this decision may be unfair. Bias types: {bias_types}. "
            f"Characteristic affected: {affected}. Fair outcome: {fair_outcome}. "
            "Be empathetic, clear, and direct."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return ""


# ── Rendering helpers ─────────────────────────

def chips_html(items, style="auto"):
    if not items:
        return '<span class="chip ch-muted">None detected</span>'
    html = ""
    for i, item in enumerate(items):
        s = CHIP_STYLES[i % len(CHIP_STYLES)] if style == "auto" else style
        html += f'<span class="chip {s}">{item}</span>'
    return html

def highlight_text(text, bias_types):
    out = text
    for bias in bias_types:
        for key, pat in BIAS_KEYWORDS.items():
            if key.lower() in bias.lower() or bias.lower() in key.lower():
                out = re.sub(pat, lambda m: f"<mark>{m.group()}</mark>",
                             out, flags=re.IGNORECASE)
    return out

def severity_badge(conf, bias_found):
    if not bias_found:
        return '<span class="sev-low">LOW RISK</span>'
    if conf >= 0.75:
        return '<span class="sev-high">HIGH SEVERITY</span>'
    if conf >= 0.45:
        return '<span class="sev-med">MEDIUM SEVERITY</span>'
    return '<span class="sev-low">LOW SEVERITY</span>'

def gauge_chart(value, bias_found):
    color = "#ff5c5c" if bias_found else "#3effc8"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(value * 100),
        number={"suffix": "%", "font": {"family": "Fraunces", "size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "transparent",
                     "tickfont": {"color": "#5a6478", "size": 9}},
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "#1c222c",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 33],  "color": "rgba(62,255,200,0.04)"},
                {"range": [33, 66], "color": "rgba(255,184,48,0.04)"},
                {"range": [66, 100],"color": "rgba(255,92,92,0.04)"},
            ],
            "threshold": {"line": {"color": color, "width": 2.5},
                          "thickness": 0.7, "value": value * 100},
        },
    ))
    fig.update_layout(
        height=180, margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Fraunces"},
    )
    return fig

def radar_chart(all_reports):
    dim_counts = {d: 0 for d in BIAS_DIMS}
    for r in all_reports:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower():
                    dim_counts[dim] += 1
    vals = [dim_counts[d] for d in BIAS_DIMS]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=BIAS_DIMS + [BIAS_DIMS[0]],
        fill="toself",
        fillcolor="rgba(198,241,53,0.06)",
        line=dict(color="#c6f135", width=2),
        marker=dict(color="#c6f135", size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, color="#5a6478",
                            gridcolor="rgba(255,255,255,0.05)",
                            tickfont=dict(family="JetBrains Mono", size=9, color="#5a6478")),
            angularaxis=dict(color="#b8bfcc",
                             gridcolor="rgba(255,255,255,0.05)",
                             tickfont=dict(family="JetBrains Mono", size=9, color="#b8bfcc")),
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=300, margin=dict(l=50, r=50, t=30, b=30),
        showlegend=False,
    )
    return fig

def pie_chart(bc, cc):
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias Found"],
        values=[bc or 1, cc or 1],
        hole=0.68,
        marker=dict(colors=["#ff5c5c", "#3effc8"],
                    line=dict(color="#0a0c0f", width=3)),
        textfont=dict(family="JetBrains Mono", size=10),
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    total = bc + cc
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:9px'>TOTAL</span>",
        x=0.5, y=0.5,
        font=dict(family="Fraunces", size=20, color="#f0f2f7"),
        showarrow=False,
    )
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(family="JetBrains Mono", size=9, color="#b8bfcc"),
                    bgcolor="rgba(0,0,0,0)", orientation="h",
                    x=0.5, xanchor="center", y=-0.05),
    )
    return fig

def bar_chart(all_types):
    if not all_types:
        return None
    counts = Counter(all_types)
    labels, values = zip(*counts.most_common())
    colors = ["#ff5c5c", "#ffb830", "#60a5fa", "#3effc8", "#a78bfa", "#f87171", "#fb923c"]
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=colors[:len(labels)], line=dict(width=0)),
        text=list(values),
        textfont=dict(family="JetBrains Mono", size=10, color="#f0f2f7"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(200, len(labels) * 46 + 60),
        margin=dict(l=10, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                   tickfont=dict(family="JetBrains Mono", size=9, color="#5a6478"), zeroline=False),
        yaxis=dict(tickfont=dict(family="JetBrains Mono", size=9, color="#b8bfcc"),
                   gridcolor="rgba(0,0,0,0)"),
        bargap=0.38,
    )
    return fig

def reports_to_csv(reports):
    rows = []
    for r in reports:
        rows.append({
            "id":                      r.get("id", ""),
            "created_at":              (r.get("created_at") or "")[:16],
            "bias_found":              r.get("bias_found", False),
            "confidence_pct":          int(r.get("confidence_score", 0) * 100),
            "bias_types":              "; ".join(r.get("bias_types", [])),
            "affected_characteristic": r.get("affected_characteristic", ""),
            "original_outcome":        r.get("original_outcome", ""),
            "fair_outcome":            r.get("fair_outcome", ""),
            "explanation":             r.get("explanation", ""),
            "recommendations":         " | ".join(r.get("recommendations", [])),
        })
    return pd.DataFrame(rows).to_csv(index=False)

def build_txt_report(report, text, dtype):
    recs = report.get("recommendations", [])
    lines = [
        "=" * 64, "  VERDICT WATCH V4 — BIAS ANALYSIS REPORT", "=" * 64,
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type      : {dtype.upper()}",
        f"Report ID : {report.get('id', 'N/A')}", "",
        f"Built for Google Solution Challenge 2026 — Build with AI", "",
        "── ORIGINAL DECISION TEXT ──", text, "",
        "── VERDICT ──", "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence: {int(report.get('confidence_score', 0) * 100)}%", "",
        "── BIAS TYPES ──",
        ", ".join(report.get("bias_types", [])) or "None detected", "",
        "── CHARACTERISTIC AFFECTED ──",
        report.get("affected_characteristic", "N/A"), "",
        "── ORIGINAL OUTCOME ──", report.get("original_outcome", "N/A"), "",
        "── FAIR OUTCOME ──", report.get("fair_outcome", "N/A"), "",
        "── EXPLANATION ──", report.get("explanation", "N/A"), "",
        "── NEXT STEPS ──",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    lines += ["", "=" * 64,
              "  Not legal advice. For educational purposes only.",
              "  Powered by Groq Llama 3.3 70B + Google Gemini",
              "=" * 64]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    # Logo
    st.markdown(
        '<div style="font-family:Fraunces,serif; font-size:1.15rem; font-weight:900; '
        'color:#f0f2f7; line-height:1;">⚖️ Verdict Watch</div>'
        '<div style="font-family:JetBrains Mono,monospace; font-size:0.56rem; '
        'letter-spacing:2px; text-transform:uppercase; color:#5a6478; margin-top:3px;">'
        'V4 · Unbiased AI · GSC 2026</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── API Keys section
    st.markdown('<div class="sec-label">API Keys</div>', unsafe_allow_html=True)

    env_groq = os.getenv("GROQ_API_KEY", "")
    if env_groq:
        st.markdown('<div class="pill-ok">● GROQ CONNECTED</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pill-warn">● GROQ KEY NEEDED</div>', unsafe_allow_html=True)
        key_input = st.text_input(
            "Groq API Key", label_visibility="collapsed",
            placeholder="gsk_...", type="password", key="groq_key_input",
            help="Get a free key at console.groq.com",
        )
        if key_input:
            st.session_state["groq_api_key"] = key_input
            st.success("✓ Groq key saved")

    st.markdown("<br style='margin-top:4px'>", unsafe_allow_html=True)

    env_gemini = os.getenv("GEMINI_API_KEY", "")
    gemini_connected = bool(env_gemini or st.session_state.get("gemini_api_key"))
    if gemini_connected:
        st.markdown('<div class="gemini-badge">🤖 GEMINI CONNECTED (Google AI)</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace; font-size:0.6rem; '
            'letter-spacing:1px; color:#5a6478; margin-bottom:4px;">'
            'GEMINI KEY (Optional — enables image OCR + plain-English explanations)</div>',
            unsafe_allow_html=True,
        )
        gemini_input = st.text_input(
            "Gemini API Key", label_visibility="collapsed",
            placeholder="AIza...", type="password", key="gemini_key_input",
            help="Get free key at aistudio.google.com — required for image upload",
        )
        if gemini_input:
            st.session_state["gemini_api_key"] = gemini_input
            st.success("✓ Gemini key saved")

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:1rem 0">', unsafe_allow_html=True)

    # ── Quick examples
    st.markdown('<div class="sec-label">Quick Examples</div>', unsafe_allow_html=True)
    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"ex_{ex['type']}_{ex['tag'][:3]}"):
            st.session_state["prefill_text"] = ex["text"]
            st.session_state["prefill_type"] = ex["type"]
            st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:1rem 0">', unsafe_allow_html=True)

    # ── How it works
    st.markdown('<div class="sec-label">How It Works</div>', unsafe_allow_html=True)
    steps = [
        ("01", "Paste text OR upload a PDF/DOCX/image"),
        ("02", "AI extracts the criteria used to decide"),
        ("03", "Scans for 7 types of hidden bias"),
        ("04", "Shows what the fair outcome should be"),
        ("05", "Optional: generate formal appeal letter"),
        ("06", "Download full report or export CSV"),
    ]
    for n, t in steps:
        st.markdown(
            f'<div class="hw"><div class="hw-n">{n}</div><div class="hw-t">{t}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:1rem 0">', unsafe_allow_html=True)

    # ── Hackathon compliance
    st.markdown('<div class="sec-label">Hackathon Compliance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="icard lime" style="font-family:JetBrains Mono,monospace;font-size:0.7rem;'
        'color:#c6f135;line-height:1.8;">'
        '✅ Google Gemini 1.5 Flash<br>✅ Build with AI theme<br>'
        '✅ Unbiased AI Decisions<br>✅ Real-world social impact</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

hc1, hc2 = st.columns([3, 1])
with hc1:
    st.markdown(
        '<div class="v4-hero">'
        '<div class="v4-wordmark">⚖ Verdict Watch'
        '<span class="v4-badge">V4</span></div>'
        '<div class="v4-tagline">AI-powered bias detection for automated decisions</div>'
        '<div style="margin-top:0.7rem;">'
        '<span class="hackathon-badge">🏆 Google Solution Challenge 2026 · Build with AI · Unbiased AI Decision Making</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )
with hc2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if gemini_connected:
        st.markdown(
            '<div class="gemini-badge" style="float:right;">🤖 Powered by Gemini + Groq</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_analyse, tab_dashboard, tab_history, tab_compare, tab_batch, tab_about = st.tabs([
    "⚡  Analyse",
    "📊  Dashboard",
    "📋  History",
    "⚖️  Compare",
    "📦  Batch",
    "ℹ  About",
])


# ═══════════════════════════════════════════════════════════
# TAB 1 — ANALYSE
# ═══════════════════════════════════════════════════════════

with tab_analyse:

    prefill_text = st.session_state.get("prefill_text", "")
    prefill_type = st.session_state.get("prefill_type", "job")

    # ── Step indicator
    uploaded_done = bool(st.session_state.get("extracted_text") or prefill_text)
    analysed_done = bool(st.session_state.get("last_report"))

    st.markdown(f"""
    <div class="step-row">
      <div class="step-item {'done' if uploaded_done else 'active'}">
        <div class="step-num">{'✓' if uploaded_done else '1'}</div>
        <div class="step-label">Input</div>
      </div>
      <div class="step-item {'done' if analysed_done else ('active' if uploaded_done else '')}">
        <div class="step-num">{'✓' if analysed_done else '2'}</div>
        <div class="step-label">Analyse</div>
      </div>
      <div class="step-item {'active' if analysed_done else ''}">
        <div class="step-num">3</div>
        <div class="step-label">Report</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-column input layout
    col_left, col_right = st.columns([1.1, 1], gap="large")

    with col_left:
        # ────────── UPLOAD SECTION
        st.markdown(
            '<div class="sec-label">📎 Upload a Document <span style="color:#5a6478;font-size:0.58rem;">'
            '(PDF · DOCX · TXT · PNG · JPG)</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="upload-hint">💡 Upload your rejection letter, triage result, '
            'or denial notice and we\'ll extract the text automatically.</div>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Upload document", label_visibility="collapsed",
            type=ACCEPTED_FILE_TYPES, key="file_uploader",
            help="Supported: PDF, Word doc, plain text, or an image of the document",
        )

        if uploaded_file:
            with st.spinner(f"Extracting text from {uploaded_file.name}..."):
                extracted = extract_text_from_file(uploaded_file)
            if extracted.startswith("["):
                st.warning(extracted)
            else:
                st.session_state["extracted_text"] = extracted
                st.markdown('<div class="sec-label" style="margin-top:0.8rem;">Extracted Text Preview</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="extracted-preview">{extracted[:600]}{"..." if len(extracted)>600 else ""}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"✓ {len(extracted)} characters extracted from {uploaded_file.name}")

        # ── Divider
        st.markdown(
            '<div style="display:flex;align-items:center;gap:0.8rem;margin:1.2rem 0;">'
            '<div style="flex:1;height:1px;background:rgba(255,255,255,0.07)"></div>'
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;'
            'color:#5a6478;letter-spacing:2px;">OR TYPE / PASTE</div>'
            '<div style="flex:1;height:1px;background:rgba(255,255,255,0.07)"></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # ── Text area
        st.markdown('<div class="sec-label">✏️ Decision Text</div>', unsafe_allow_html=True)
        default_val = st.session_state.get("extracted_text") or prefill_text
        decision_text = st.text_area(
            "Decision text", label_visibility="collapsed",
            value=default_val, height=180, key="decision_input",
            placeholder=(
                "Paste the rejection letter, loan denial, medical triage result, "
                "or any automated decision here…\n\n"
                "Or use the upload section above, or pick a quick example from the sidebar."
            ),
        )

        char_count = len(decision_text.strip())
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.66rem;'
            f'color:{"#3effc8" if char_count > 50 else "#ff5c5c"};margin-top:3px;">'
            f'{char_count} characters · {"Ready ✓" if char_count > 50 else "Add more text"}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        # ── Decision type
        st.markdown('<div class="sec-label">Decision Type</div>', unsafe_allow_html=True)
        type_opts = ["job", "loan", "medical", "university", "other"]
        decision_type = st.selectbox(
            "Type", label_visibility="collapsed",
            options=type_opts,
            format_func=lambda x: TYPE_LABELS[x],
            index=type_opts.index(prefill_type) if prefill_type in type_opts else 0,
            key="decision_type",
            help="Selecting the correct type helps the AI tailor its bias analysis",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── What we check for
        st.markdown('<div class="sec-label">We check for these bias types</div>', unsafe_allow_html=True)
        for label, icon in [
            ("Gender / Parental Status", "👤"),
            ("Age Discrimination", "🕐"),
            ("Racial / Ethnic Bias", "🌍"),
            ("Geographic Redlining", "📍"),
            ("Socioeconomic Status", "💰"),
            ("Language Discrimination", "🗣️"),
            ("Insurance / Class Bias", "📋"),
        ]:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.04);">'
                f'<span style="font-size:0.9rem;">{icon}</span>'
                f'<span style="font-family:Instrument Sans,sans-serif;font-size:0.82rem;'
                f'color:#b8bfcc;">{label}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Clear extracted text button
        if st.session_state.get("extracted_text"):
            if st.button("🗑 Clear Uploaded Text", key="clear_extracted"):
                st.session_state.pop("extracted_text", None)
                st.rerun()

    # ── Analyse button (full width)
    st.markdown("<br>", unsafe_allow_html=True)
    btn_col, _ = st.columns([1, 2])
    with btn_col:
        analyse_btn = st.button("⚡  Run Bias Analysis", key="analyse_btn")

    # ─── RESULTS ───────────────────────────────────────────

    if analyse_btn:
        st.session_state.pop("prefill_text", None)
        st.session_state.pop("prefill_type", None)
        st.session_state.pop("extracted_text", None)
        st.session_state.pop("appeal_letter", None)

        if not decision_text.strip():
            st.warning("⚠️ Please paste or upload a decision text first.")
        elif not check_groq_key():
            st.error("❌ No Groq API key found. Add it in the sidebar or your .env file.")
        else:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Step 3 · Analysis Report</div>',
                        unsafe_allow_html=True)

            prog = st.progress(0, text="Step 1/3 · Extracting decision criteria…")
            with st.spinner(""):
                report, err = run_analysis(decision_text, decision_type)
            prog.progress(100, text="Done ✓")
            prog.empty()

            if err:
                st.error(f"❌ {err}")
                st.info("Make sure your Groq API key is valid and you have an internet connection.")
            elif report:
                st.session_state["last_report"] = report
                st.session_state["last_text"]   = decision_text

                bias_found  = report.get("bias_found", False)
                confidence  = report.get("confidence_score", 0.0)
                bias_types  = report.get("bias_types", [])
                affected    = report.get("affected_characteristic", "")
                orig        = report.get("original_outcome", "N/A")
                fair        = report.get("fair_outcome", "N/A")
                explanation = report.get("explanation", "")
                recs        = report.get("recommendations", [])

                # ── Verdict banner
                if bias_found:
                    st.markdown(
                        '<div class="verdict-bias">'
                        '<div class="v-icon">⚠️</div>'
                        '<div class="v-label">BIAS DETECTED</div>'
                        '<div class="v-sub">This decision shows discriminatory patterns</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="verdict-clean">'
                        '<div class="v-icon">✅</div>'
                        '<div class="v-label">NO BIAS FOUND</div>'
                        '<div class="v-sub">Decision appears free of discriminatory factors</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Gemini plain-English summary (if available)
                if bias_found and check_gemini_key() and GEMINI_SUPPORT:
                    with st.spinner("Gemini generating plain-English explanation..."):
                        gemini_explain = gemini_plain_explanation(report)
                    if gemini_explain:
                        st.markdown(
                            '<div class="icard lime">'
                            '<div class="ic-label">🤖 Gemini Simple Explanation (Google AI)</div>'
                            f'<div class="ic-value">{gemini_explain}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("<br>", unsafe_allow_html=True)

                # ── Score + Details + Outcomes
                rc1, rc2, rc3 = st.columns([1.2, 1.4, 1.4])

                with rc1:
                    st.markdown('<div class="sec-label">Confidence Score</div>',
                                unsafe_allow_html=True)
                    st.plotly_chart(gauge_chart(confidence, bias_found),
                                    use_container_width=True, config={"displayModeBar": False})
                    st.markdown(severity_badge(confidence, bias_found), unsafe_allow_html=True)

                with rc2:
                    st.markdown('<div class="sec-label">Bias Types Detected</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        chips_html(bias_types) if bias_types
                        else '<span class="chip ch-teal">None detected ✓</span>',
                        unsafe_allow_html=True,
                    )
                    if affected:
                        st.markdown(
                            f'<div style="margin-top:0.9rem;">'
                            f'<div class="sec-label">Characteristic Affected</div>'
                            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.9rem;'
                            f'color:#ffb830;">{affected}</div></div>',
                            unsafe_allow_html=True,
                        )

                with rc3:
                    st.markdown(
                        f'<div class="icard coral" style="margin-bottom:0.6rem;">'
                        f'<div class="ic-label">Original Decision</div>'
                        f'<div class="ic-value mono">{orig.upper()}</div></div>'
                        f'<div class="icard teal">'
                        f'<div class="ic-label">Should Have Been</div>'
                        f'<div class="ic-value">{fair}</div></div>',
                        unsafe_allow_html=True,
                    )

                # ── Bias phrase highlighter
                if bias_types and decision_text.strip():
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">🔍 Bias Phrase Highlighter — Problematic words are highlighted</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="highlight-box">{highlight_text(decision_text, bias_types)}</div>',
                        unsafe_allow_html=True,
                    )

                # ── Explanation
                if explanation:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">What Happened — Plain English</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="icard amber"><div class="ic-value">{explanation}</div></div>',
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

                # ── Appeals letter (only if bias found)
                if bias_found:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("✉️ Generate Formal Appeal Letter", expanded=False):
                        st.markdown(
                            '<div style="font-family:Instrument Sans,sans-serif;font-size:0.85rem;'
                            'color:#b8bfcc;margin-bottom:0.8rem;">'
                            'Generate a formal letter you can send to the decision-maker. '
                            'Fill in the <strong>[PLACEHOLDERS]</strong> before sending. '
                            '<em>Not legal advice.</em></div>',
                            unsafe_allow_html=True,
                        )
                        if st.button("✉️ Draft Appeal Letter", key="appeal_btn"):
                            with st.spinner("Drafting appeal letter..."):
                                try:
                                    letter = generate_appeal_letter(report, decision_text, decision_type)
                                    st.session_state["appeal_letter"] = letter
                                except Exception as e:
                                    st.error(f"❌ {e}")

                        if st.session_state.get("appeal_letter"):
                            letter = st.session_state["appeal_letter"]
                            st.markdown(f'<div class="appeal-box">{letter}</div>',
                                        unsafe_allow_html=True)
                            dl_a, _ = st.columns([1, 2])
                            with dl_a:
                                st.download_button(
                                    "📥 Download Appeal Letter (.txt)",
                                    data=letter,
                                    file_name=f"appeal_{report.get('id','')[:8]}.txt",
                                    mime="text/plain",
                                    key="dl_appeal",
                                )

                # ── Download
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Full Report (.txt)",
                        data=build_txt_report(report, decision_text, decision_type),
                        file_name=f"verdict_watch_{report.get('id','report')[:8]}.txt",
                        mime="text/plain",
                        key="dl_report",
                    )

                st.markdown(
                    '<div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;'
                    'color:#5a6478;margin-top:0.5rem;">'
                    '⚠ Not legal advice. For educational and awareness purposes only.</div>',
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ═══════════════════════════════════════════════════════════

with tab_dashboard:
    hist = get_all_reports()

    if not hist:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">📊</div>'
            '<div class="empty-title">No data yet</div>'
            '<div class="empty-sub">Run your first analysis to see stats here.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        bias_reps  = [r for r in hist if r.get("bias_found")]
        clean_reps = [r for r in hist if not r.get("bias_found")]
        all_types  = [bt for r in hist for bt in r.get("bias_types", [])]
        scores     = [r.get("confidence_score", 0) for r in hist]
        bflags     = [r.get("bias_found", False) for r in hist]
        bias_rate  = (len(bias_reps) / len(hist) * 100) if hist else 0
        avg_conf   = (sum(scores) / len(scores) * 100) if scores else 0
        top_bias   = Counter(all_types).most_common(1)[0][0] if all_types else "N/A"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Analyses", len(hist))
        m2.metric("Bias Rate",      f"{bias_rate:.0f}%")
        m3.metric("Avg Confidence", f"{avg_conf:.0f}%")
        m4.metric("Top Bias Type",  top_bias)

        st.markdown("<br>", unsafe_allow_html=True)

        dc1, dc2 = st.columns(2)
        with dc1:
            st.markdown('<div class="sec-label">Verdicts Distribution</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps), len(clean_reps)),
                            use_container_width=True, config={"displayModeBar": False})
        with dc2:
            st.markdown('<div class="sec-label">Bias Types Frequency</div>',
                        unsafe_allow_html=True)
            bc = bar_chart(all_types)
            if bc:
                st.plotly_chart(bc, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No bias types detected yet.")

        st.markdown("<br>", unsafe_allow_html=True)

        radc, charc = st.columns(2)
        with radc:
            st.markdown('<div class="sec-label">Bias Dimension Radar</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist), use_container_width=True,
                            config={"displayModeBar": False})
        with charc:
            st.markdown('<div class="sec-label">Affected Characteristics</div>',
                        unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist
                     if r.get("affected_characteristic")]
            if chars:
                cdf = pd.DataFrame([
                    {"Characteristic": k, "Count": v,
                     "% of Total": f"{v / len(hist) * 100:.0f}%"}
                    for k, v in Counter(chars).most_common()
                ])
                st.dataframe(cdf, use_container_width=True, hide_index=True)
            else:
                st.info("No characteristic data yet.")


# ═══════════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ═══════════════════════════════════════════════════════════

with tab_history:
    hist = get_all_reports()

    if not hist:
        st.markdown(
            '<div class="empty-state">'
            '<div class="empty-icon">📋</div>'
            '<div class="empty-title">No past analyses</div>'
            '<div class="empty-sub">Your analysis history will appear here.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_q = st.text_input(
                "search", label_visibility="collapsed",
                placeholder="🔍  Search by characteristic or bias type…",
                key="history_search",
            )
        with f2:
            filt_v = st.selectbox("verdict", ["All", "Bias Detected", "No Bias"],
                                   label_visibility="collapsed", key="history_filter")
        with f3:
            sort_by = st.selectbox("sort", ["Newest First", "Oldest First",
                                            "Highest Confidence", "Lowest Confidence"],
                                   label_visibility="collapsed", key="history_sort")

        filtered = hist[:]
        if filt_v == "Bias Detected": filtered = [r for r in filtered if r.get("bias_found")]
        elif filt_v == "No Bias":     filtered = [r for r in filtered if not r.get("bias_found")]
        if search_q:
            sq = search_q.lower()
            filtered = [r for r in filtered
                        if sq in (r.get("affected_characteristic") or "").lower()
                        or any(sq in bt.lower() for bt in r.get("bias_types", []))]
        if   sort_by == "Newest First":       filtered.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sort_by == "Oldest First":       filtered.sort(key=lambda r: r.get("created_at") or "")
        elif sort_by == "Highest Confidence": filtered.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
        else:                                 filtered.sort(key=lambda r: r.get("confidence_score", 0))

        hh1, hh2 = st.columns([3, 1])
        with hh1:
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
                f'color:#5a6478;margin-bottom:0.8rem;">Showing {len(filtered)} of {len(hist)}</div>',
                unsafe_allow_html=True,
            )
        with hh2:
            st.download_button(
                "📥 Export CSV",
                data=reports_to_csv(filtered),
                file_name=f"verdict_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="csv_export",
            )

        for r in filtered:
            bias    = r.get("bias_found", False)
            conf    = int(r.get("confidence_score", 0) * 100)
            affected = r.get("affected_characteristic") or "—"
            b_types = r.get("bias_types", [])
            created = (r.get("created_at") or "")[:16].replace("T", " ")
            icon    = "⚠️" if bias else "✅"

            with st.expander(
                f"{icon}  {'BIAS' if bias else 'CLEAN'}  ·  {conf}% confidence  ·  {affected}  ·  {created}",
                expanded=False,
            ):
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.markdown(
                        f'<div class="icard {"coral" if bias else "teal"}">'
                        f'<div class="ic-label">Verdict</div>'
                        f'<div class="ic-value mono">{"⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"}</div></div>'
                        f'<div class="icard blue" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Original Outcome</div>'
                        f'<div class="ic-value mono">{(r.get("original_outcome") or "N/A").upper()}</div></div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    st.markdown(
                        f'<div class="icard amber">'
                        f'<div class="ic-label">Bias Types</div>'
                        f'<div class="ic-value">{chips_html(b_types) if b_types else "None"}</div></div>'
                        f'<div class="icard teal" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Fair Outcome</div>'
                        f'<div class="ic-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="icard amber" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Explanation</div>'
                        f'<div class="ic-value" style="font-size:0.88rem;">{r["explanation"]}</div></div>',
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
                st.caption(f"Report ID: {r.get('id', 'N/A')}")


# ═══════════════════════════════════════════════════════════
# TAB 4 — COMPARE
# ═══════════════════════════════════════════════════════════

with tab_compare:
    st.markdown(
        '<div style="font-family:Instrument Sans,sans-serif;font-size:0.92rem;'
        'color:#b8bfcc;margin-bottom:1.3rem;">'
        'Compare two decisions side-by-side to see which is more biased, '
        'and get a comparative verdict.</div>',
        unsafe_allow_html=True,
    )

    cc1, cc2 = st.columns(2, gap="large")
    with cc1:
        st.markdown('<div class="cmp-header">Decision A</div>', unsafe_allow_html=True)
        cmp_text1 = st.text_area("Text A", height=150, label_visibility="collapsed",
                                  placeholder="Paste first decision here…", key="cmp1")
        cmp_type1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div class="cmp-header">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=150, label_visibility="collapsed",
                                  placeholder="Paste second decision here…", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type2")

    btn_c, _ = st.columns([1, 2])
    with btn_c:
        cmp_btn = st.button("⚡  Compare Both Decisions", key="compare_btn")

    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Paste text for both Decision A and B.")
        elif not check_groq_key():
            st.error("❌ No Groq API key.")
        else:
            with st.spinner("Analysing both decisions…"):
                r1, e1 = run_analysis(cmp_text1, cmp_type1)
                r2, e2 = run_analysis(cmp_text2, cmp_type2)

            if e1: st.error(f"Decision A: {e1}")
            if e2: st.error(f"Decision B: {e2}")

            if r1 and r2:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                v1, v2 = st.columns(2, gap="large")
                for col, r, lbl in [(v1, r1, "A"), (v2, r2, "B")]:
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
                        st.plotly_chart(gauge_chart(conf, bias), use_container_width=True,
                                        config={"displayModeBar": False})
                        st.markdown(
                            chips_html(r.get("bias_types", [])) + " " + severity_badge(conf, bias),
                            unsafe_allow_html=True,
                        )
                        affected = r.get("affected_characteristic") or "—"
                        st.markdown(
                            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.78rem;'
                            f'color:#ffb830;margin-top:0.5rem;">Affected: {affected}</div>'
                            f'<div class="icard teal" style="margin-top:0.8rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )

                st.markdown("<br>", unsafe_allow_html=True)
                b1, b2   = r1.get("bias_found"), r2.get("bias_found")
                c1v, c2v = r1.get("confidence_score", 0), r2.get("confidence_score", 0)
                if b1 and b2:
                    winner  = "A" if c1v >= c2v else "B"
                    summary = f"Both decisions show bias. Decision {winner} has higher confidence ({int(max(c1v,c2v)*100)}%)."
                elif b1:
                    summary = "Decision A shows bias; Decision B appears fair."
                elif b2:
                    summary = "Decision B shows bias; Decision A appears fair."
                else:
                    summary = "Neither decision shows clear discriminatory patterns."
                st.markdown(
                    f'<div class="icard blue"><div class="ic-label">Comparison Summary</div>'
                    f'<div class="ic-value">{summary}</div></div>',
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════
# TAB 5 — BATCH
# ═══════════════════════════════════════════════════════════

with tab_batch:
    st.markdown(
        '<div style="font-family:Instrument Sans,sans-serif;font-size:0.92rem;'
        'color:#b8bfcc;margin-bottom:0.5rem;">'
        'Analyse up to 10 decisions at once. Separate each with '
        '<code style="background:rgba(255,255,255,0.06);padding:1px 6px;border-radius:4px;'
        'font-family:JetBrains Mono,monospace;">---</code> on its own line.</div>',
        unsafe_allow_html=True,
    )

    batch_text = st.text_area(
        "Batch", height=260, label_visibility="collapsed", key="batch_input",
        placeholder=(
            "Paste your first decision here...\n---\n"
            "Paste your second decision here...\n---\n"
            "Paste your third decision here..."
        ),
    )
    bc1, bc2 = st.columns([1, 1])
    with bc1:
        batch_type = st.selectbox(
            "Batch type", ["job","loan","medical","university","other"],
            format_func=lambda x: TYPE_LABELS[x],
            label_visibility="collapsed", key="batch_type",
        )
    with bc2:
        batch_btn = st.button("📦  Run Batch Analysis", key="batch_run")

    if batch_btn:
        raw_blocks = [b.strip() for b in batch_text.split("---") if b.strip()]
        if not raw_blocks:
            st.warning("⚠️ No decisions found. Separate them with --- on its own line.")
        elif not check_groq_key():
            st.error("❌ No Groq API key.")
        elif len(raw_blocks) > 10:
            st.warning("⚠️ Max 10 decisions per batch. Please split into smaller batches.")
        else:
            progress = st.progress(0)
            results  = []
            for i, block in enumerate(raw_blocks):
                with st.spinner(f"Analysing decision {i+1} of {len(raw_blocks)}…"):
                    rep, err = run_analysis(block, batch_type)
                    results.append({"text": block, "report": rep, "error": err})
                progress.progress((i + 1) / len(raw_blocks))
            progress.empty()

            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            bias_c  = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            clean_c = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            err_c   = sum(1 for r in results if r["error"])

            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Bias Detected", bias_c)
            sm2.metric("No Bias Found", clean_c)
            sm3.metric("Errors",        err_c)

            st.markdown("<br>", unsafe_allow_html=True)

            table_rows = []
            for i, res in enumerate(results, 1):
                rep   = res["report"]
                error = res["error"]
                if error:
                    table_rows.append({"#": i, "Verdict": "ERROR", "Confidence": "—",
                                       "Bias Types": error[:60], "Affected": "—", "Fair Outcome": "—"})
                elif rep:
                    table_rows.append({
                        "#":           i,
                        "Verdict":     "⚠ BIAS" if rep.get("bias_found") else "✓ CLEAN",
                        "Confidence":  f"{int(rep.get('confidence_score',0)*100)}%",
                        "Bias Types":  ", ".join(rep.get("bias_types", [])) or "None",
                        "Affected":    rep.get("affected_characteristic") or "—",
                        "Fair Outcome": rep.get("fair_outcome") or "—",
                    })

            if table_rows:
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            all_batch = [r["report"] for r in results if r["report"]]
            if all_batch:
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Batch CSV",
                        data=reports_to_csv(all_batch),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="batch_csv",
                    )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep   = res["report"]
                error = res["error"]
                lbl   = f"Decision {i}"
                if error:  lbl += " — ERROR"
                elif rep:
                    bias = rep.get("bias_found", False)
                    conf = int(rep.get("confidence_score", 0) * 100)
                    lbl += f" — {'⚠ BIAS' if bias else '✓ CLEAN'} ({conf}%)"
                with st.expander(lbl, expanded=False):
                    st.markdown(
                        f'<div class="icard blue"><div class="ic-label">Decision Text</div>'
                        f'<div class="ic-value" style="font-size:0.85rem;">{res["text"][:400]}{"..." if len(res["text"])>400 else ""}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if error:
                        st.error(error)
                    elif rep:
                        bias  = rep.get("bias_found", False)
                        btyps = rep.get("bias_types", [])
                        st.markdown(
                            f'<div class="icard {"coral" if bias else "teal"}" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Verdict</div>'
                            f'<div class="ic-value mono">{"⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"}</div></div>'
                            f'<div class="icard amber" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Bias Types</div>'
                            f'<div class="ic-value">{chips_html(btyps) if btyps else "None"}</div></div>'
                            f'<div class="icard teal" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{rep.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )


# ═══════════════════════════════════════════════════════════
# TAB 6 — ABOUT
# ═══════════════════════════════════════════════════════════

with tab_about:
    ab1, ab2 = st.columns([1.5, 1], gap="large")

    with ab1:
        st.markdown(
            '<div style="font-family:Fraunces,serif;font-size:1.6rem;font-weight:900;'
            'color:#f0f2f7;margin-bottom:0.6rem;">What is Verdict Watch?</div>'
            '<div style="font-family:Instrument Sans,sans-serif;font-size:0.92rem;'
            'color:#b8bfcc;line-height:1.85;margin-bottom:1.5rem;">'
            'Verdict Watch is an AI-powered tool that analyses automated decisions — '
            'job rejections, loan denials, medical triage, university admissions — '
            'for hidden bias against protected characteristics.<br><br>'
            'Built for the <strong style="color:#c6f135;">Google Solution Challenge 2026</strong> '
            'under the <strong style="color:#c6f135;">Unbiased AI Decision Making</strong> '
            'problem statement. It uses a 3-step AI pipeline powered by '
            '<strong>Groq Llama 3.3 70B</strong> and <strong>Google Gemini 1.5 Flash</strong> '
            'to extract criteria, detect discriminatory patterns, and generate what the '
            'fair outcome should have been.</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-label">Problem Statement Alignment</div>',
                    unsafe_allow_html=True)
        align_points = [
            ("Pre-model audit",    "Analyses what criteria were used before producing bias verdict"),
            ("Post-decision audit","Evaluates the decision for discriminatory patterns"),
            ("AI Governance layer","Explains how AI reached its bias detection conclusion"),
            ("Explainability",     "Shows which words/phrases triggered the bias detection"),
            ("Fairness metrics",   "Confidence score + severity rating + bias type classification"),
            ("Retroactive correction", "Generates what the fair outcome should have been"),
        ]
        for name, desc in align_points:
            st.markdown(
                f'<div class="feat-card">'
                f'<div class="feat-title">✅ {name}</div>'
                f'<div class="feat-desc">{desc}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Bias Types Detected</div>', unsafe_allow_html=True)
        bias_info = [
            ("👤 Gender Bias",           "Decisions influenced by gender, name, or parental status"),
            ("🕐 Age Discrimination",     "Unfair weighting of age group or seniority proxies"),
            ("🌍 Racial / Ethnic Bias",   "Name-based or origin-based ethnic profiling"),
            ("📍 Geographic Redlining",   "Residential area or zip code used as a proxy"),
            ("💰 Socioeconomic Bias",     "Employment sector or credit history weighting"),
            ("🗣️ Language Discrimination","Primary language used against applicants"),
            ("📋 Insurance / Class Bias", "Insurance tier used to rank medical priority"),
        ]
        for name, desc in bias_info:
            st.markdown(
                f'<div class="icard blue" style="margin-bottom:0.45rem;">'
                f'<div class="ic-label">{name}</div>'
                f'<div class="ic-value" style="font-size:0.86rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="sec-label">V4 New Features</div>', unsafe_allow_html=True)
        v4_feats = [
            ("📎", "PDF / DOCX / Image Upload", "Extract text from uploaded documents automatically"),
            ("🤖", "Google Gemini Integration", "Plain-English explanations + image OCR via Gemini 1.5 Flash"),
            ("🎯", "Step-by-step guided flow", "Clear 3-step progress indicator"),
            ("🔑", "Dual API key support", "Groq + Gemini keys via sidebar"),
            ("🖼️", "Empty states", "Helpful guidance when no data exists"),
            ("📋", "Type selector with icons", "Clearer decision type selection"),
            ("📥", "Better download UX", "Report + appeal letter + CSV exports"),
            ("🏆", "Hackathon compliance badge", "Shows Google AI model usage"),
            ("🧹", "V4 design refresh", "Fraunces serif + Instrument Sans + lime palette"),
        ]
        for icon, name, desc in v4_feats:
            st.markdown(
                f'<div class="feat-card">'
                f'<div class="feat-title">{icon} {name}</div>'
                f'<div class="feat-desc">{desc}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Tech Stack</div>', unsafe_allow_html=True)
        tech = [
            ("⚡ Groq",              "LLM inference engine"),
            ("🦙 Llama 3.3 70B",    "Primary language model"),
            ("🤖 Gemini 1.5 Flash", "Google AI (hackathon req.)"),
            ("🎈 Streamlit",        "Full-stack UI, zero server"),
            ("🗄️ SQLite",           "Persistent local database"),
            ("📊 Plotly",           "Interactive charts"),
            ("📄 PyMuPDF",          "PDF text extraction"),
            ("📝 python-docx",      "Word doc extraction"),
        ]
        for name, desc in tech:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'font-family:JetBrains Mono,monospace;font-size:0.72rem;'
                f'padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                f'<span style="color:#f0f2f7;">{name}</span>'
                f'<span style="color:#5a6478;">{desc}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="icard amber">'
            '<div class="ic-label">⚠ Disclaimer</div>'
            '<div class="ic-value" style="font-size:0.85rem;">'
            'Not legal advice. Built for educational and awareness purposes. '
            'Consult a qualified legal professional for formal discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="icard lime">'
            '<div class="ic-label">🏆 Google Solution Challenge 2026</div>'
            '<div class="ic-value" style="font-size:0.85rem;">'
            'Theme: Build with AI<br>'
            'Problem: Unbiased AI Decision Making<br>'
            'Uses: Gemini 1.5 Flash (Google AI model ✓)<br>'
            'Impact: Helps people identify discriminatory automated decisions'
            '</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="footer-bar">'
    'Verdict Watch V4  ·  Groq Llama 3.3 70B + Google Gemini 1.5 Flash  ·  '
    'Google Solution Challenge 2026 — Build with AI  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)