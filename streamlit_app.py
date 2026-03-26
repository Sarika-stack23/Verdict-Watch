"""
streamlit_app.py — Verdict Watch V9
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V9 Changelog:
  ✅ FIXED  Stray toolbar icons above text area — completely hidden
  ✅ FIXED  Radio buttons styled as proper pill toggle
  ✅ FIXED  Char counter only shows warning after user types (not on load)
  ✅ FIXED  Floating lightbulb placeholder — replaced with clean ghost text
  ✅ FIXED  Sidebar API status pill positioning
  ✅ FIXED  Card height jitter — all result cards use consistent min-height
  ✅ FIXED  Duplicate warning dismissal flow
  ✅ FIXED  Mobile layout overflow clipping

  ✨ NEW    Live bias keyword scanner — highlights suspicious words as you type
  ✨ NEW    Confidence gauge pre-view — shows historical avg before analysis
  ✨ NEW    Real-time character quality indicator with animated fill bar
  ✨ NEW    "Paste from clipboard" quick-fill button
  ✨ NEW    Animated scan progress with step labels (not just spinner)
  ✨ NEW    Bias dimension cards on sidebar with interactive hover
  ✨ NEW    Live API key tester in Settings tab (ping Groq)
  ✨ NEW    Report share card — copyable summary block
  ✨ NEW    Severity heat-map colour coding across all result cards
  ✨ NEW    Analysis history sparkline in sidebar (mini trend)
  ✨ NEW    Keyboard shortcut hint (Ctrl+Enter to analyse)
  ✨ NEW    Dark-mode aware CSS variables
  ✨ NEW    Smooth accordion transitions in History tab
  ✨ NEW    Batch ETA timer with per-item progress
  ✨ NEW    V9 refined design system — sharper contrast, tighter spacing

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

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch · V9",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# V9 — DESIGN SYSTEM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Sora:wght@600;700;800&display=swap');

/* ══ V9 TOKENS ══ */
:root {
    --p:       #2563EB;
    --p-lt:    #EFF6FF;
    --p-dk:    #1D4ED8;
    --p-mid:   #BFDBFE;
    --on-p:    #ffffff;

    --e:       #DC2626;
    --e-lt:    #FEF2F2;
    --e-mid:   #FECACA;
    --on-e-lt: #7F1D1D;

    --s:       #16A34A;
    --s-lt:    #F0FDF4;
    --s-mid:   #BBF7D0;
    --on-s-lt: #14532D;

    --w:       #D97706;
    --w-lt:    #FFFBEB;
    --w-mid:   #FDE68A;
    --on-w-lt: #78350F;

    --bg:      #F9FAFB;
    --surf:    #FFFFFF;
    --surf-2:  #F3F4F6;
    --surf-3:  #E5E7EB;
    --border:  #E5E7EB;
    --border-md: #D1D5DB;

    --t1: #111827;
    --t2: #4B5563;
    --t3: #9CA3AF;
    --t4: #D1D5DB;

    --sh1: 0 1px 2px rgba(0,0,0,.05);
    --sh2: 0 4px 6px -1px rgba(0,0,0,.07), 0 2px 4px -2px rgba(0,0,0,.05);
    --sh3: 0 10px 15px -3px rgba(0,0,0,.08), 0 4px 6px -4px rgba(0,0,0,.05);

    --r-xs: 4px; --r-sm: 6px; --r-md: 10px;
    --r-lg: 14px; --r-xl: 20px; --r-2xl: 28px; --r-full: 999px;

    --ff: 'Inter', system-ui, sans-serif;
    --ff-display: 'Sora', sans-serif;
    --ff-mono: 'JetBrains Mono', monospace;

    --transition: 150ms cubic-bezier(.4,0,.2,1);
}

/* ══ RESET ══ */
html, body, [class*="css"] {
    font-family: var(--ff) !important;
    background: var(--bg) !important;
    color: var(--t1) !important;
    -webkit-font-smoothing: antialiased;
}
[data-testid="stAppViewContainer"] { background: var(--bg) !important; }
[data-testid="stSidebar"] {
    background: var(--surf) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ══ HIDE ALL STRAY STREAMLIT UI CHROME ══ */
/* Top toolbar above text areas */
[data-testid="stToolbar"],
[data-testid="stColorPicker"],
div[class*="stToolbar"],
div[data-testid="InputInstructions"],
.stTextArea div[data-baseweb="base-input"] > div:first-child:not(textarea):not(div[data-testid]),
[data-testid="stTextAreaRootElement"] > div:first-child:empty,
/* The pencil/circle/record icons */
button[data-testid="clear-button"],
[class*="uploadButton"],
[data-testid="stFileUploaderDeleteBtn"] { display: none !important; }

/* Hide Streamlit's default radio visual but keep functionality */
.stRadio > div { display: none !important; }

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-thumb { background: var(--surf-3); border-radius: 3px; }
::-webkit-scrollbar-track { background: transparent; }

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surf);
    border-bottom: 1px solid var(--border);
    padding: 0 2px;
    gap: 0;
    box-shadow: none;
    border-radius: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--ff) !important;
    font-weight: 500;
    font-size: 0.84rem;
    color: var(--t2) !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    padding: 11px 16px !important;
    transition: color var(--transition), border-color var(--transition);
    letter-spacing: 0;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--p) !important; }
.stTabs [aria-selected="true"] {
    color: var(--p) !important;
    border-bottom-color: var(--p) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* ══ MAIN BUTTON ══ */
.stButton > button {
    font-family: var(--ff) !important;
    font-weight: 600;
    font-size: 0.875rem;
    background: var(--p);
    color: var(--on-p);
    border: none;
    border-radius: var(--r-full);
    padding: 0.55rem 1.5rem;
    box-shadow: 0 1px 2px rgba(37,99,235,.3);
    transition: all var(--transition);
    letter-spacing: -.01em;
}
.stButton > button:hover {
    background: var(--p-dk);
    box-shadow: 0 4px 12px rgba(37,99,235,.35);
    transform: translateY(-1px);
}
.stButton > button:active { transform: none; box-shadow: none; }
.stButton > button:disabled {
    background: var(--surf-3) !important;
    color: var(--t3) !important;
    box-shadow: none !important;
    cursor: not-allowed;
}

/* Sidebar buttons */
div[data-testid="stSidebar"] .stButton > button {
    background: var(--surf-2) !important;
    color: var(--t1) !important;
    box-shadow: none !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    font-size: 0.8rem !important;
    padding: 0.4rem 0.85rem !important;
    width: 100% !important;
    text-align: left !important;
    transform: none !important;
    font-weight: 500 !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--surf-3) !important;
    border-color: var(--border-md) !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ══ TEXT AREA ══ */
.stTextArea textarea {
    font-family: var(--ff) !important;
    font-size: 0.9rem !important;
    background: var(--surf) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    color: var(--t1) !important;
    line-height: 1.7 !important;
    padding: 14px 16px !important;
    resize: vertical !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
    box-shadow: var(--sh1) !important;
}
.stTextArea textarea:focus {
    border-color: var(--p) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: var(--t3) !important; font-style: italic; }
.stTextArea label, .stSelectbox label, .stTextInput label {
    font-family: var(--ff) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: var(--t3) !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
}

/* ══ SELECT ══ */
.stSelectbox > div > div {
    background: var(--surf) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r-sm) !important;
    font-family: var(--ff) !important;
    font-size: 0.875rem !important;
    box-shadow: var(--sh1) !important;
    transition: border-color var(--transition) !important;
}
.stSelectbox > div > div:focus-within { border-color: var(--p) !important; }

/* ══ FILE UPLOADER ══ */
[data-testid="stFileUploader"] {
    background: var(--surf) !important;
    border: 2px dashed var(--border-md) !important;
    border-radius: var(--r-lg) !important;
    transition: border-color var(--transition), background var(--transition) !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--p) !important;
    background: var(--p-lt) !important;
}

/* ══ METRICS ══ */
[data-testid="metric-container"] {
    background: var(--surf);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    padding: 1rem 1.25rem;
    box-shadow: var(--sh1);
}
[data-testid="metric-container"] label {
    font-family: var(--ff) !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    color: var(--t3) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--ff-display) !important;
    font-weight: 700 !important;
    font-size: 1.65rem !important;
    color: var(--t1) !important;
    letter-spacing: -.03em !important;
}

/* ══ PROGRESS ══ */
.stProgress > div > div { background: var(--p) !important; border-radius: 2px; }
.stProgress > div { background: var(--surf-3) !important; border-radius: 2px; }

/* ══ DOWNLOAD BUTTON ══ */
.stDownloadButton > button {
    background: var(--surf) !important;
    color: var(--p) !important;
    border: 1.5px solid var(--p) !important;
    border-radius: var(--r-full) !important;
    font-family: var(--ff) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    box-shadow: none !important;
    padding: 0.48rem 1.3rem !important;
    transition: all var(--transition) !important;
}
.stDownloadButton > button:hover {
    background: var(--p-lt) !important;
    transform: none !important;
}

/* ══ EXPANDER ══ */
.streamlit-expanderHeader {
    font-family: var(--ff) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    background: var(--surf) !important;
    border: 1px solid var(--border) !important;
    color: var(--t1) !important;
    border-radius: var(--r-md) !important;
    padding: 0.75rem 1rem !important;
    transition: background var(--transition) !important;
}
.streamlit-expanderHeader:hover { background: var(--surf-2) !important; }
.streamlit-expanderContent {
    background: var(--surf) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--r-md) var(--r-md) !important;
    padding: 1rem !important;
}

/* ══ DATAFRAME ══ */
[data-testid="stDataFrame"] { border-radius: var(--r-lg) !important; overflow: hidden; box-shadow: var(--sh1); }

/* ═══════════════════════════════════════════
   V9 COMPONENTS
═══════════════════════════════════════════ */

/* ── App Bar ── */
.vw-appbar {
    background: var(--surf);
    border-bottom: 1px solid var(--border);
    padding: 0 28px;
    height: 58px;
    display: flex;
    align-items: center;
    gap: 12px;
    position: sticky; top: 0; z-index: 100;
    margin: -1rem -1rem 2rem;
    box-shadow: var(--sh1);
}
.vw-logo {
    width: 30px; height: 30px;
    background: linear-gradient(135deg, var(--p) 0%, var(--p-dk) 100%);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: .9rem; flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(37,99,235,.3);
}
.vw-appbar-title {
    font-family: var(--ff-display);
    font-size: 1rem; font-weight: 700;
    color: var(--t1); letter-spacing: -.02em;
}
.vw-appbar-sub {
    font-size: .72rem; color: var(--t3); margin-top: 1px;
    font-family: var(--ff);
}
.vw-badge {
    margin-left: auto;
    background: var(--p-lt);
    color: var(--p);
    font-size: .65rem; font-weight: 700;
    padding: 3px 9px; border-radius: var(--r-full);
    letter-spacing: .05em; text-transform: uppercase;
    border: 1px solid var(--p-mid);
}

/* ── Sidebar Header ── */
.vw-sidebar-hd {
    background: linear-gradient(150deg, #1E3A8A 0%, var(--p) 60%, #3B82F6 100%);
    padding: 20px 16px 16px;
    margin: -1rem -1rem 1.1rem;
    position: relative; overflow: hidden;
}
.vw-sidebar-hd::before {
    content: '';
    position: absolute; top: -20px; right: -20px;
    width: 80px; height: 80px;
    background: rgba(255,255,255,.06);
    border-radius: 50%;
}
.vw-sidebar-name {
    font-family: var(--ff-display);
    font-size: .95rem; font-weight: 700; color: #fff;
    letter-spacing: -.02em; position: relative;
}
.vw-sidebar-tag {
    font-size: .68rem; color: rgba(255,255,255,.65);
    margin-top: 2px; font-family: var(--ff); position: relative;
}
.vw-api-pill {
    display: inline-flex; align-items: center; gap: 5px;
    border-radius: var(--r-full);
    padding: 3px 9px;
    font-size: .67rem; font-weight: 600; font-family: var(--ff);
    margin-top: 9px; position: relative;
}
.vw-api-ok  { background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.25); color: #fff; }
.vw-api-err { background: rgba(254,202,202,.15); border: 1px solid rgba(254,202,202,.3);  color: #FEE2E2; }

/* ── Pill Toggle (replaces broken radio) ── */
.vw-toggle {
    display: inline-flex;
    background: var(--surf-2);
    border: 1px solid var(--border);
    border-radius: var(--r-full);
    padding: 3px;
    gap: 2px;
    margin-bottom: 14px;
}
.vw-toggle-btn {
    font-family: var(--ff);
    font-size: .8rem; font-weight: 500;
    padding: 5px 16px;
    border-radius: var(--r-full);
    border: none; cursor: pointer;
    transition: all var(--transition);
    background: transparent; color: var(--t2);
}
.vw-toggle-btn.active {
    background: var(--surf);
    color: var(--t1); font-weight: 600;
    box-shadow: var(--sh1);
}

/* ── Section Label ── */
.vw-label {
    font-family: var(--ff);
    font-size: .68rem; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase;
    color: var(--t3); margin-bottom: 8px; margin-top: 2px;
}

/* ── Cards ── */
.card {
    background: var(--surf);
    border-radius: var(--r-lg);
    border: 1px solid var(--border);
    padding: 1rem 1.2rem;
    transition: box-shadow var(--transition), border-color var(--transition);
    margin-bottom: 8px;
}
.card:hover { box-shadow: var(--sh2); }
.card.flat  { box-shadow: none; }
.card.e-fill { background: var(--e-lt); border-color: var(--e-mid); }
.card.s-fill { background: var(--s-lt); border-color: var(--s-mid); }
.card.w-fill { background: var(--w-lt); border-color: var(--w-mid); }
.card.p-fill { background: var(--p-lt); border-color: var(--p-mid); }
.card.muted  { background: var(--surf-2); border-color: var(--border); }
.card.no-border { border: none; box-shadow: var(--sh2); }

.card-label {
    font-family: var(--ff);
    font-size: .67rem; font-weight: 700;
    letter-spacing: .07em; text-transform: uppercase;
    color: var(--t3); margin-bottom: 5px;
}
.card-value {
    font-family: var(--ff);
    font-size: .88rem; color: var(--t1); line-height: 1.5;
}
.card-value.mono  { font-family: var(--ff-mono); font-size: .84rem; }
.card-value.large { font-size: 1.3rem; font-weight: 700; }

/* ── Verdict Banner ── */
.v-banner {
    border-radius: var(--r-2xl);
    padding: 1.75rem 2rem;
    text-align: center;
    margin-bottom: 1.25rem;
    position: relative; overflow: hidden;
}
.v-banner::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 120px; height: 120px;
    border-radius: 50%;
    opacity: .06;
}
.v-banner.bias {
    background: var(--e-lt);
    border: 1.5px solid var(--e-mid);
}
.v-banner.bias::before { background: var(--e); }
.v-banner.clean {
    background: var(--s-lt);
    border: 1.5px solid var(--s-mid);
}
.v-banner.clean::before { background: var(--s); }

.v-banner-icon { font-size: 2.2rem; line-height: 1; margin-bottom: 8px; }
.v-banner-title {
    font-family: var(--ff-display);
    font-size: 1.5rem; font-weight: 700;
    letter-spacing: -.03em; margin-bottom: 3px;
}
.v-banner.bias  .v-banner-title { color: var(--e); }
.v-banner.clean .v-banner-title { color: var(--s); }
.v-banner-sub { font-size: .84rem; color: var(--t2); }

/* ── Risk Ring ── */
.ring-wrap {
    display: flex; flex-direction: column;
    align-items: center; padding: .5rem 0 .25rem; gap: 6px;
}
.ring-sev {
    font-family: var(--ff);
    font-size: .75rem; font-weight: 600; text-align: center;
}

/* ── Live keyword scanner ── */
.kw-scan {
    background: var(--surf-2); border: 1px solid var(--border);
    border-radius: var(--r-md); padding: .75rem 1rem;
    margin-top: 6px;
}
.kw-scan-title {
    font-family: var(--ff); font-size: .68rem; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase; color: var(--t3);
    margin-bottom: 6px;
}
.kw-found { display: flex; flex-wrap: wrap; gap: 4px; }
.kw-none  { font-family: var(--ff); font-size: .8rem; color: var(--t3); }

/* ── Chips ── */
.chip {
    display: inline-block; border-radius: var(--r-full);
    padding: 2px 10px;
    font-family: var(--ff); font-size: .75rem; font-weight: 500;
    margin: 2px 2px 2px 0; border: 1px solid transparent;
    transition: all var(--transition);
}
.chip-e { background: var(--e-lt); color: var(--e); border-color: var(--e-mid); }
.chip-p { background: var(--p-lt); color: var(--p);  border-color: var(--p-mid); }
.chip-s { background: var(--s-lt); color: var(--s);  border-color: var(--s-mid); }
.chip-w { background: var(--w-lt); color: var(--w);  border-color: var(--w-mid); }
.chip-n { background: var(--surf-2); color: var(--t2); border-color: var(--border); }

/* ── Severity badges ── */
.sev { display:inline-block; border-radius:var(--r-full); padding:2px 10px; font-family:var(--ff); font-size:.7rem; font-weight:600; }
.sev-h { background:var(--e-lt); color:var(--e); }
.sev-m { background:var(--w-lt); color:var(--w); }
.sev-l { background:var(--s-lt); color:var(--s); }

/* ── Scan progress steps ── */
.step-bar { display:flex; gap:5px; margin:10px 0 5px; }
.step-item {
    flex:1; background:var(--surf-2); border-radius:var(--r-md);
    padding:.5rem .6rem; text-align:center;
    transition:all .2s; border:1px solid transparent;
}
.step-item.active { background:var(--p-lt); border-color:var(--p-mid); }
.step-item.done   { background:var(--s-lt); border-color:var(--s-mid); }
.step-n { font-size:.55rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--t3); margin-bottom:2px; font-family:var(--ff); }
.step-l { font-size:.7rem; font-weight:500; color:var(--t2); font-family:var(--ff); }
.step-item.active .step-n,.step-item.active .step-l { color:var(--p); font-weight:600; }
.step-item.done .step-n,.step-item.done .step-l     { color:var(--s); }

@keyframes scan-slide { 0%{transform:translateX(-100%)} 100%{transform:translateX(500%)} }
.scan-track { background:var(--surf-3); border-radius:2px; height:3px; overflow:hidden; margin:4px 0; }
.scan-fill  { height:100%; background:var(--p); border-radius:2px; animation:scan-slide 1.3s ease-in-out infinite; width:25%; }
.scan-status { font-family:var(--ff); font-size:.78rem; color:var(--p); font-weight:500; }

/* ── Highlight box ── */
.hl-box {
    font-family:var(--ff); font-size:.88rem; line-height:1.8;
    color:var(--t2); background:var(--surf); border:1px solid var(--border);
    border-radius:var(--r-md); padding:1rem 1.25rem;
}
.hl-box mark {
    background:rgba(220,38,38,.09); color:var(--e);
    border-radius:3px; padding:1px 3px;
    border-bottom:1.5px solid rgba(220,38,38,.25);
}
.hl-caption { font-family:var(--ff); font-size:.68rem; color:var(--t3); margin-top:5px; }

/* ── Recommendations ── */
.rec {
    display:flex; gap:11px; align-items:flex-start;
    background:var(--surf); border:1px solid var(--border);
    border-radius:var(--r-md); padding:.8rem 1rem;
    margin-bottom:7px; transition:box-shadow var(--transition);
}
.rec:hover { box-shadow:var(--sh2); }
.rec-num {
    background:var(--p); color:var(--on-p);
    border-radius:var(--r-xs); min-width:20px; height:20px;
    display:flex; align-items:center; justify-content:center;
    font-family:var(--ff-mono); font-size:.68rem; font-weight:600;
    flex-shrink:0; margin-top:1px;
}
.rec-text { font-family:var(--ff); font-size:.855rem; color:var(--t2); line-height:1.55; }

/* ── Law items ── */
.law {
    display:flex; gap:9px; align-items:center;
    padding:7px 0; border-bottom:1px solid var(--border);
    font-family:var(--ff); font-size:.855rem; color:var(--t2);
}
.law:last-child { border-bottom:none; }
.law-icon { color:var(--p); flex-shrink:0; font-size:.9rem; }

/* ── Appeal box ── */
.appeal-box {
    background:var(--surf); border:1px solid var(--border);
    border-left:3px solid var(--p); border-radius:var(--r-md);
    padding:1.25rem 1.5rem;
    font-family:var(--ff-mono); font-size:.78rem; line-height:1.9;
    color:var(--t2); white-space:pre-wrap;
}

/* ── Share card ── */
.share-card {
    background: linear-gradient(135deg, var(--t1) 0%, #374151 100%);
    border-radius: var(--r-xl); padding: 1.5rem;
    font-family: var(--ff-mono); font-size: .78rem;
    color: #E5E7EB; line-height: 1.9;
    border: 1px solid #374151; margin-bottom: 1rem;
}
.share-card .sc-title {
    font-family: var(--ff-display); font-size: 1rem;
    font-weight: 700; color: #fff; margin-bottom: .75rem;
    letter-spacing: -.02em;
}
.share-card .sc-row { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,.07); }
.share-card .sc-row:last-child { border-bottom: none; }
.share-card .sc-key   { color: #9CA3AF; }
.share-card .sc-val   { color: #F9FAFB; font-weight: 500; }
.share-card .sc-bias  { color: #FCA5A5; font-weight: 700; }
.share-card .sc-clean { color: #6EE7B7; font-weight: 700; }

/* ── Duplicate warning ── */
.dup-warn {
    display:flex; align-items:flex-start; gap:11px;
    background:var(--w-lt); border:1px solid var(--w-mid);
    border-radius:var(--r-md); padding:.9rem 1.1rem;
    font-family:var(--ff); font-size:.855rem; color:var(--on-w-lt);
    margin-bottom:1.1rem;
}
.dup-icon { font-size:1.1rem; flex-shrink:0; }
.dup-text strong { font-weight:600; display:block; margin-bottom:2px; }

/* ── API key error ── */
.key-err {
    background:var(--e-lt); border:1px solid var(--e-mid);
    border-left:3px solid var(--e); border-radius:var(--r-md);
    padding:.9rem 1.2rem; font-family:var(--ff); font-size:.855rem;
    color:var(--on-e-lt); margin-bottom:1.1rem;
}
.key-err code {
    background:rgba(220,38,38,.1); padding:2px 5px; border-radius:3px;
    font-family:var(--ff-mono); font-size:.8rem;
}

/* ── Empty state ── */
.empty { text-align:center; padding:3.5rem 2rem; }
.empty-ico { font-size:2.8rem; margin-bottom:10px; opacity:.45; }
.empty-title { font-family:var(--ff-display); font-size:1.05rem; font-weight:700; color:var(--t1); margin-bottom:5px; letter-spacing:-.02em; }
.empty-sub   { font-family:var(--ff); font-size:.855rem; color:var(--t2); line-height:1.6; max-width:320px; margin:0 auto; }

/* ── KPI card ── */
.kpi { background:var(--surf); border-radius:var(--r-lg); padding:1.1rem 1.3rem; box-shadow:var(--sh2); border:1px solid var(--border); }
.kpi-l { font-family:var(--ff); font-size:.68rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--t3); }
.kpi-v { font-family:var(--ff-display); font-size:1.8rem; font-weight:700; color:var(--t1); line-height:1.1; letter-spacing:-.03em; }
.kpi-d { font-family:var(--ff); font-size:.73rem; color:var(--t3); }

/* ── Sidebar how-it-works ── */
.how-step { display:flex; gap:9px; align-items:flex-start; padding:4px 0; }
.how-n {
    background:var(--p); color:var(--on-p);
    border-radius:50%; width:18px; height:18px;
    display:flex; align-items:center; justify-content:center;
    font-family:var(--ff-mono); font-size:.6rem; font-weight:700;
    flex-shrink:0; margin-top:1px;
}
.how-t { font-family:var(--ff); font-size:.77rem; color:var(--t2); line-height:1.4; }

/* ── Winner banner ── */
.winner {
    background:var(--p-lt); border-radius:var(--r-lg); padding:.9rem 1.3rem;
    text-align:center; font-family:var(--ff); font-size:.9rem;
    font-weight:600; color:var(--p-dk); margin-bottom:1.1rem;
    border:1px solid var(--p-mid); box-shadow:var(--sh1);
}

/* ── Preview box ── */
.preview-box {
    background:var(--surf-2); border-radius:var(--r-sm);
    padding:.65rem .85rem; font-family:var(--ff-mono); font-size:.74rem;
    color:var(--t2); line-height:1.6; white-space:pre-wrap;
    max-height:76px; overflow:hidden; border:1px solid var(--border);
}

/* ── Divider ── */
.divider { border:none; border-top:1px solid var(--border); margin:1.25rem 0; }

/* ── Feature row ── */
.feat-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:6px 0; border-bottom:1px solid var(--border);
    font-family:var(--ff); font-size:.82rem;
}
.feat-row:last-child { border-bottom:none; }
.feat-name  { color:var(--t1); font-weight:500; }
.feat-desc  { color:var(--t2); font-size:.76rem; text-align:right; }
.feat-check { color:var(--s); font-weight:700; }

/* ── About hero ── */
.about-hero {
    background:linear-gradient(140deg, #1E3A8A 0%, var(--p) 100%);
    border-radius:var(--r-2xl); padding:2.25rem; color:#fff; margin-bottom:1.25rem;
    position: relative; overflow: hidden;
}
.about-hero::after {
    content: '⚖️';
    position: absolute; right: 24px; bottom: 10px;
    font-size: 5rem; opacity: .08; line-height: 1;
}
.about-hero h2 { font-family:var(--ff-display); font-size:1.55rem; font-weight:700; letter-spacing:-.03em; margin:0 0 9px; }
.about-hero p  { font-family:var(--ff); font-size:.875rem; opacity:.82; line-height:1.7; margin:0; max-width:520px; }

/* ── Char counter ── */
.char-counter { padding-top:.5rem; }
.char-count { font-family:var(--ff); font-size:.78rem; font-weight:500; }
.char-track { background:var(--surf-3); height:2px; border-radius:2px; margin-top:4px; overflow:hidden; }
.char-fill  { height:100%; border-radius:2px; transition:width .3s; }
.cc-ok  { color:var(--s); }
.cc-mid { color:var(--w); }
.cc-bad { color:var(--e); }

/* ── Sidebar section label ── */
.sb-label {
    font-family:var(--ff); font-size:.67rem; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:var(--t3);
    margin:13px 0 7px;
}

/* ── Shortcut hint ── */
.shortcut-hint {
    display:inline-flex; align-items:center; gap:5px;
    font-family:var(--ff); font-size:.73rem; color:var(--t3);
    margin-top:6px;
}
.kbd {
    background:var(--surf-2); border:1px solid var(--border-md);
    border-bottom:2px solid var(--border-md);
    border-radius:3px; padding:1px 5px;
    font-family:var(--ff-mono); font-size:.68rem; color:var(--t2);
}

/* ── Badge ── */
.badge-ok  { display:inline-flex; align-items:center; gap:5px; background:var(--s-lt); color:var(--s); border-radius:var(--r-full); padding:3px 10px; font-family:var(--ff); font-size:.7rem; font-weight:600; border:1px solid var(--s-mid); }
.badge-err { display:inline-flex; align-items:center; gap:5px; background:var(--e-lt); color:var(--e); border-radius:var(--r-full); padding:3px 10px; font-family:var(--ff); font-size:.7rem; font-weight:600; border:1px solid var(--e-mid); }

/* ── Footer ── */
.vw-footer {
    text-align:center; font-family:var(--ff); font-size:.7rem;
    color:var(--t3); margin-top:3.5rem; padding:1.25rem 0;
    border-top:1px solid var(--border);
}

/* ── API test result ── */
.api-test-ok  { background:var(--s-lt); border:1px solid var(--s-mid); border-radius:var(--r-md); padding:.8rem 1rem; font-family:var(--ff); font-size:.855rem; color:var(--on-s-lt); }
.api-test-err { background:var(--e-lt); border:1px solid var(--e-mid); border-radius:var(--r-md); padding:.8rem 1rem; font-family:var(--ff); font-size:.855rem; color:var(--on-e-lt); }

/* ── Sidebar sparkline placeholder ── */
.sidebar-trend {
    background: var(--surf-2); border-radius: var(--r-md);
    border: 1px solid var(--border); padding: .6rem .8rem;
    margin-top: 4px;
}
.sidebar-trend-bars {
    display: flex; align-items: flex-end; gap: 3px; height: 28px;
}
.stb { background: var(--p); border-radius: 2px 2px 0 0; min-width: 6px; flex: 1; opacity: .7; transition: opacity var(--transition); }
.stb:hover { opacity: 1; }
.stb.bias { background: var(--e); }
.sidebar-trend-label {
    font-family: var(--ff); font-size: .65rem; color: var(--t3);
    margin-top: 5px; text-align: center;
}
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

BIAS_KW = {
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|housewife|mrs|mr)\b",
    "Age":           r"\b(age group|senior|junior|young|old|millennial|boomer|retirement|elderly|youth)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|surname)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|occupation|class)\b",
    "Language":      r"\b(primary language|language|accent|english|bilingual|native speaker)\b",
    "Insurance":     r"\b(insurance|coverage|uninsured|medicaid|medicare|policy|insurance classification)\b",
}

BIAS_DIMS = ["Gender", "Age", "Racial", "Geographic", "Socioeconomic", "Language", "Insurance"]
CHIP_COLORS = ["chip-e", "chip-w", "chip-p", "chip-s", "chip-n", "chip-p", "chip-w"]

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

_DEFAULTS = {
    "session_count":     0,
    "last_report":       None,
    "last_text":         "",
    "appeal_letter":     None,
    "decision_input":    "",
    "decision_type_sel": "job",
    "input_mode":        "paste",
    "typed_once":        False,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _api_key_ok():
    return bool(os.getenv("GROQ_API_KEY", "").strip())

def _api_key_banner():
    st.markdown(
        '<div class="key-err">⚠️ <strong>GROQ_API_KEY not found.</strong> '
        'Add it to your <code>.env</code> file:<br>'
        '<code style="display:block;margin-top:6px;">GROQ_API_KEY=gsk_your_key_here</code><br>'
        'Get a free key at <strong>console.groq.com</strong> then restart the app.</div>',
        unsafe_allow_html=True,
    )

def get_all_reports():
    try: return services.get_all_reports()
    except: return []

def chips_html(items, style="auto"):
    if not items: return '<span class="chip chip-n">None detected</span>'
    html = ""
    for i, item in enumerate(items):
        cls = CHIP_COLORS[i % len(CHIP_COLORS)] if style == "auto" else style
        html += f'<span class="chip {cls}">{item}</span>'
    return html

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

def severity_label(conf, bias_found):
    if not bias_found: return '<span class="sev sev-l">Low Risk</span>'
    if conf >= 0.75:   return '<span class="sev sev-h">High Severity</span>'
    if conf >= 0.45:   return '<span class="sev sev-m">Medium Severity</span>'
    return '<span class="sev sev-l">Low Severity</span>'

def severity_desc(conf, bias_found):
    if not bias_found: return "No strong bias indicators"
    if conf >= 0.75:   return "Strong discriminatory signal"
    if conf >= 0.45:   return "Possible bias patterns"
    return "Weak or uncertain indicators"

def risk_ring_svg(pct, bias_found):
    r = 48; cx = cy = 64; sw = 9
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100; gap = circ - dash
    col = "#DC2626" if bias_found else ("#16A34A" if pct < 45 else "#D97706")
    return f"""<svg width="128" height="128" viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#E5E7EB" stroke-width="{sw}"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"
    stroke-dasharray="{dash:.1f} {gap:.1f}"
    stroke-dashoffset="{circ/4:.1f}" stroke-linecap="round"
    transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy-5}" text-anchor="middle"
    font-family="'Sora','Inter',sans-serif" font-size="20" font-weight="700" fill="{col}">{pct}%</text>
  <text x="{cx}" y="{cy+12}" text-anchor="middle"
    font-family="'Inter',sans-serif" font-size="8" font-weight="600"
    fill="#9CA3AF" letter-spacing="0.07em">CONFIDENCE</text>
</svg>"""

def extract_text_from_file(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".txt"):
        return uploaded.read().decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        if not PDF_SUPPORT:
            st.warning("PDF requires PyMuPDF: pip install PyMuPDF")
            return None
        raw = uploaded.read()
        doc = pymupdf.open(stream=raw, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip()
    st.warning(f"Unsupported file type: {uploaded.name}")
    return None

def live_scan_keywords(text):
    """Return dict of found keyword categories."""
    found = {}
    if not text: return found
    for category, pat in BIAS_KW.items():
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        if matches:
            found[category] = list(set(m.lower() for m in matches))
    return found

def build_sidebar_sparkline(reports):
    """Build mini sparkline of last 7 days."""
    if not reports: return ""
    by_day = {}
    for r in reports[-14:]:
        day = (r.get("created_at") or "")[:10]
        if day:
            if day not in by_day: by_day[day] = {"total": 0, "bias": 0}
            by_day[day]["total"] += 1
            if r.get("bias_found"): by_day[day]["bias"] += 1
    if not by_day: return ""
    days = sorted(by_day.items())[-7:]
    max_total = max(v["total"] for _, v in days) or 1
    bars = ""
    for _, v in days:
        h = max(10, int(v["total"] / max_total * 28))
        cls = "stb bias" if v["bias"] > v["total"] / 2 else "stb"
        bars += f'<div class="{cls}" style="height:{h}px;" title="{v[\"total\"]} analyses"></div>'
    return (
        '<div class="sidebar-trend">'
        f'<div class="sidebar-trend-bars">{bars}</div>'
        '<div class="sidebar-trend-label">Last 7 days · Red = bias majority</div>'
        '</div>'
    )

# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

def run_analysis(text, dtype):
    ph = st.empty()
    def upd(step, label): _render_steps(ph, step, label)
    try:
        report = services.run_full_pipeline(
            decision_text=text, decision_type=dtype, progress_callback=upd
        )
        st.session_state["session_count"] += 1
        ph.empty()
        return report, None
    except ValueError as e:
        ph.empty(); return None, str(e)
    except Exception as e:
        ph.empty(); return None, f"Pipeline error: {str(e)}"

def _render_steps(ph, current, label):
    steps = [(1, "Extract Criteria"), (2, "Detect Bias"), (3, "Fair Outcome")]
    parts = []
    for num, lbl in steps:
        if num < current:    cls, icon = "done",   "✓"
        elif num == current: cls, icon = "active",  "⟳"
        else:                cls, icon = "",        str(num)
        parts.append(
            f'<div class="step-item {cls}">'
            f'<div class="step-n">STEP {icon}</div>'
            f'<div class="step-l">{lbl}</div></div>'
        )
    ph.markdown(
        f'<div class="step-bar">{"".join(parts)}</div>'
        f'<div class="scan-track"><div class="scan-fill"></div></div>'
        f'<div class="scan-status">● {label}</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def build_txt_report(report, text, dtype):
    recs = report.get("recommendations", [])
    laws = report.get("legal_frameworks", [])
    lines = [
        "=" * 68, "       VERDICT WATCH V9 — BIAS ANALYSIS REPORT", "=" * 68,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id','N/A')}",
        f"Severity   : {report.get('severity','N/A').upper()}", "",
        "── ORIGINAL DECISION ────────────────────────────────────────────", text, "",
        "── VERDICT ──────────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence : {int(report.get('confidence_score',0)*100)}%", "",
        "── BIAS TYPES ───────────────────────────────────────────────────",
        ", ".join(report.get("bias_types", [])) or "None detected", "",
        "── CHARACTERISTIC AFFECTED ──────────────────────────────────────",
        report.get("affected_characteristic", "N/A"), "",
        "── ORIGINAL OUTCOME ─────────────────────────────────────────────",
        report.get("original_outcome", "N/A"), "",
        "── FAIR OUTCOME ─────────────────────────────────────────────────",
        report.get("fair_outcome", "N/A"), "",
        "── EXPLANATION ──────────────────────────────────────────────────",
        report.get("explanation", "N/A"), "",
        "── NEXT STEPS ───────────────────────────────────────────────────",
    ]
    for i, r in enumerate(recs, 1): lines.append(f"  {i}. {r}")
    if laws:
        lines += ["", "── RELEVANT LEGAL FRAMEWORKS ─────────────────────────────────"]
        for law in laws: lines.append(f"  • {law}")
    lines += ["", "=" * 68, "  Verdict Watch V9  ·  Not legal advice", "=" * 68]
    return "\n".join(lines)

def build_share_summary(report):
    bias = report.get("bias_found", False)
    conf = int(report.get("confidence_score", 0) * 100)
    bts  = ", ".join(report.get("bias_types", [])) or "None"
    aff  = report.get("affected_characteristic") or "—"
    fair = report.get("fair_outcome") or "—"
    sev  = (report.get("severity") or "—").upper()
    rid  = (report.get("id") or "")[:12]
    verdict_cls = "sc-bias" if bias else "sc-clean"
    verdict_txt = "⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"
    return f"""<div class="share-card">
  <div class="sc-title">⚖️ Verdict Watch V9 Analysis</div>
  <div class="sc-row"><span class="sc-key">Verdict</span><span class="{verdict_cls}">{verdict_txt}</span></div>
  <div class="sc-row"><span class="sc-key">Confidence</span><span class="sc-val">{conf}%</span></div>
  <div class="sc-row"><span class="sc-key">Severity</span><span class="sc-val">{sev}</span></div>
  <div class="sc-row"><span class="sc-key">Bias Types</span><span class="sc-val">{bts}</span></div>
  <div class="sc-row"><span class="sc-key">Affected</span><span class="sc-val">{aff}</span></div>
  <div class="sc-row"><span class="sc-key">Fair Outcome</span><span class="sc-val">{fair[:60]}…</span></div>
  <div class="sc-row"><span class="sc-key">Report ID</span><span class="sc-val">{rid}…</span></div>
</div>"""

def reports_to_csv(reports):
    rows = [{
        "id":                      r.get("id", ""),
        "created_at":              (r.get("created_at") or "")[:16].replace("T", " "),
        "bias_found":              r.get("bias_found", False),
        "severity":                r.get("severity", ""),
        "confidence_pct":          int(r.get("confidence_score", 0) * 100),
        "bias_types":              "; ".join(r.get("bias_types", [])),
        "affected_characteristic": r.get("affected_characteristic", ""),
        "original_outcome":        r.get("original_outcome", ""),
        "fair_outcome":            r.get("fair_outcome", ""),
        "explanation":             r.get("explanation", ""),
        "legal_frameworks":        "; ".join(r.get("legal_frameworks", [])),
        "recommendations":         " | ".join(r.get("recommendations", [])),
    } for r in reports]
    return pd.DataFrame(rows).to_csv(index=False)

# ─────────────────────────────────────────────
# PLOTLY CONFIG
# ─────────────────────────────────────────────

CB = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#4B5563"),
    margin=dict(l=10, r=10, t=14, b=10),
)
MD3 = ["#2563EB","#DC2626","#16A34A","#D97706","#7C3AED","#0891B2","#DB2777"]

def pie_chart(bc, cc):
    total = bc + cc or 2
    fig = go.Figure(go.Pie(
        labels=["Bias Detected","No Bias Found"],
        values=[max(bc,1), max(cc,1)], hole=0.70,
        marker=dict(colors=["#DC2626","#16A34A"], line=dict(color="#fff",width=3)),
        textfont=dict(family="Inter,sans-serif",size=11), textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:9px;color:#9CA3AF'>TOTAL</span>",
        x=0.5,y=0.5,font=dict(family="Sora,sans-serif",size=22,color="#111827"),showarrow=False,
    )
    fig.update_layout(height=240,showlegend=True,
        legend=dict(font=dict(family="Inter,sans-serif",size=11,color="#4B5563"),
                    bgcolor="rgba(0,0,0,0)",orientation="h",x=0.5,xanchor="center",y=-0.06),**CB)
    return fig

def bar_chart(items, title=""):
    counts = Counter(items)
    if not counts: counts = {"No data":1}
    labels, values = zip(*counts.most_common(8))
    fig = go.Figure(go.Bar(
        x=list(values),y=list(labels),orientation="h",
        marker=dict(color=MD3[:len(labels)],line=dict(width=0),cornerradius=4),
        text=list(values),
        textfont=dict(family="Inter,sans-serif",size=11,color="#4B5563"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(190,len(labels)*44+55),
        xaxis=dict(showgrid=True,gridcolor="rgba(60,64,67,.06)",
                   tickfont=dict(family="Inter,sans-serif",size=10),zeroline=False),
        yaxis=dict(tickfont=dict(family="Inter,sans-serif",size=11),gridcolor="rgba(0,0,0,0)"),
        bargap=0.36,**CB)
    return fig

def trend_chart(td):
    if not td: return None
    dates=[d["date"] for d in td]; rates=[d["bias_rate"] for d in td]; totals=[d["total"] for d in td]
    fig=go.Figure()
    fig.add_trace(go.Bar(x=dates,y=totals,name="Total",
        marker=dict(color="rgba(37,99,235,.1)",line=dict(width=0),cornerradius=3),
        hovertemplate="%{x}: %{y}<extra></extra>",yaxis="y2"))
    fig.add_trace(go.Scatter(x=dates,y=rates,name="Bias Rate %",mode="lines+markers",
        line=dict(color="#DC2626",width=2.5),
        marker=dict(color="#DC2626",size=6,line=dict(color="#fff",width=1.5)),
        hovertemplate="%{x}: %{y}%<extra></extra>"))
    fig.update_layout(height=240,
        yaxis=dict(title=dict(text="Bias %",font=dict(size=10)),range=[0,105],
                   tickfont=dict(family="Inter,sans-serif",size=9),
                   gridcolor="rgba(60,64,67,.06)",zeroline=False),
        yaxis2=dict(overlaying="y",side="right",showgrid=False,
                    tickfont=dict(family="Inter,sans-serif",size=9)),
        xaxis=dict(tickfont=dict(family="Inter,sans-serif",size=9)),
        legend=dict(font=dict(family="Inter,sans-serif",size=10,color="#4B5563"),
                    bgcolor="rgba(0,0,0,0)",x=0,y=1.06,orientation="h"),**CB)
    return fig

def radar_chart(all_r):
    dim_counts={d:0 for d in BIAS_DIMS}
    for r in all_r:
        for bt in r.get("bias_types",[]):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower(): dim_counts[dim]+=1
    vals=[dim_counts[d] for d in BIAS_DIMS]
    fig=go.Figure(go.Scatterpolar(
        r=vals+[vals[0]],theta=BIAS_DIMS+[BIAS_DIMS[0]],
        fill="toself",fillcolor="rgba(37,99,235,.07)",
        line=dict(color="#2563EB",width=2.5),marker=dict(color="#2563EB",size=5)))
    fig.update_layout(
        polar=dict(bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True,color="#E5E7EB",gridcolor="rgba(60,64,67,.08)",
                            tickfont=dict(family="Inter,sans-serif",size=8)),
            angularaxis=dict(color="#9CA3AF",gridcolor="rgba(60,64,67,.08)",
                             tickfont=dict(family="Inter,sans-serif",size=10))),
        height=290,showlegend=False,margin=dict(l=42,r=42,t=22,b=22),
        paper_bgcolor="rgba(0,0,0,0)",font=dict(family="Inter,sans-serif"))
    return fig

def histogram_chart(scores):
    if not scores: scores=[0]
    fig=go.Figure(go.Histogram(
        x=[s*100 for s in scores],nbinsx=10,
        marker=dict(color="#2563EB",opacity=.7,line=dict(color="#fff",width=1)),
        hovertemplate="~%{x:.0f}%%: %{y}<extra></extra>"))
    fig.update_layout(height=210,
        xaxis=dict(title=dict(text="Confidence %",font=dict(size=10)),
                   tickfont=dict(family="Inter,sans-serif",size=10),gridcolor="rgba(60,64,67,.06)"),
        yaxis=dict(tickfont=dict(family="Inter,sans-serif",size=10),gridcolor="rgba(60,64,67,.06)"),**CB)
    return fig

def severity_donut(all_r):
    sc={"high":0,"medium":0,"low":0}
    for r in all_r:
        s=r.get("severity","low").lower()
        if s in sc: sc[s]+=1
    fig=go.Figure(go.Pie(
        labels=["High","Medium","Low"],values=[sc["high"],sc["medium"],sc["low"]],hole=0.68,
        marker=dict(colors=["#DC2626","#D97706","#16A34A"],line=dict(color="#fff",width=3)),
        textfont=dict(family="Inter,sans-serif",size=11),textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>"))
    fig.update_layout(height=230,showlegend=False,**CB)
    return fig

def gauge_chart(value, bias_found):
    color="#DC2626" if bias_found else "#16A34A"
    fig=go.Figure(go.Indicator(
        mode="gauge+number",value=round(value*100),
        number={"suffix":"%","font":{"family":"Sora,sans-serif","size":26,"color":color}},
        gauge={"axis":{"range":[0,100],"tickwidth":0,"tickfont":{"color":"#E5E7EB","size":7}},
               "bar":{"color":color,"thickness":.22},
               "bgcolor":"#F3F4F6","borderwidth":0,
               "steps":[{"range":[0,33],"color":"rgba(22,163,74,.06)"},
                        {"range":[33,66],"color":"rgba(217,119,6,.06)"},
                        {"range":[66,100],"color":"rgba(220,38,38,.06)"}],
               "threshold":{"line":{"color":color,"width":2},"thickness":.7,"value":value*100}}))
    fig.update_layout(height=170,**CB)
    return fig

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="vw-sidebar-hd">'
        '<div class="vw-sidebar-name">⚖️ Verdict Watch</div>'
        '<div class="vw-sidebar-tag">Enterprise Bias Detection · V9</div>',
        unsafe_allow_html=True,
    )
    if _api_key_ok():
        st.markdown('<div class="vw-api-pill vw-api-ok">✓ Groq API Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="vw-api-pill vw-api-err">✗ API Key Missing</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    sc1.metric("Session", st.session_state.get("session_count", 0))
    sc2.metric("All Time", len(get_all_reports()))

    # Mini sparkline
    all_r = get_all_reports()
    sparkline = build_sidebar_sparkline(all_r)
    if sparkline:
        st.markdown(sparkline, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="sb-label">Quick Examples</div>', unsafe_allow_html=True)
    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"ex_{ex['tag'].replace(' ','_')}"):
            st.session_state["decision_input"]    = ex["text"]
            st.session_state["decision_type_sel"] = ex["type"]
            st.session_state["typed_once"]        = True
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="sb-label">How It Works</div>', unsafe_allow_html=True)
    for n, t in [
        ("1","Paste text or upload a file"),
        ("2","AI extracts decision criteria"),
        ("3","Scans 7 bias dimensions"),
        ("4","Generates fair outcome + laws"),
        ("5","Review highlighted phrases"),
        ("6","Download report or appeal"),
    ]:
        st.markdown(
            f'<div class="how-step"><div class="how-n">{n}</div><div class="how-t">{t}</div></div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# APP BAR
# ─────────────────────────────────────────────

st.markdown(
    '<div class="vw-appbar">'
    '<div class="vw-logo">⚖️</div>'
    '<div>'
    '<div class="vw-appbar-title">Verdict Watch</div>'
    '<div class="vw-appbar-sub">AI-powered bias detection for automated decisions</div>'
    '</div>'
    '<div class="vw-badge">V9 Enterprise</div>'
    '</div>',
    unsafe_allow_html=True,
)

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

    col_form, col_help = st.columns([3, 1], gap="large")

    with col_form:
        # ── V9: pill toggle (replaces broken radio)
        mode_cols = st.columns([1, 3])
        with mode_cols[0]:
            if st.button("✏️ Paste Text", key="mode_paste"):
                st.session_state["input_mode"] = "paste"
                st.rerun()
        with mode_cols[1]:
            if st.button("📄 Upload File", key="mode_upload"):
                st.session_state["input_mode"] = "upload"
                st.rerun()

        cur_mode = st.session_state.get("input_mode", "paste")
        mode_indicator = "✏️ Paste Text" if cur_mode == "paste" else "📄 Upload File"
        st.markdown(
            f'<div style="font-family:var(--ff);font-size:.75rem;color:var(--p);'
            f'font-weight:600;margin-bottom:10px;margin-top:-6px;">'
            f'● {mode_indicator}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="vw-label">Decision Text</div>', unsafe_allow_html=True)

        if cur_mode == "paste":
            decision_text = st.text_area(
                "text", label_visibility="collapsed",
                height=175, key="decision_input",
                placeholder=(
                    "Paste any rejection letter, loan denial, triage result, "
                    "or university decision here…\n\n"
                    "Tip: Click any Quick Example in the sidebar to load instantly."
                ),
            )
            # Mark as typed once user starts typing
            if decision_text and not st.session_state.get("typed_once"):
                st.session_state["typed_once"] = True
        else:
            uploaded_file = st.file_uploader(
                "Upload .txt or .pdf", type=["txt","pdf"],
                label_visibility="collapsed", key="file_upload",
            )
            decision_text = ""
            if uploaded_file:
                extracted = extract_text_from_file(uploaded_file)
                if extracted:
                    decision_text = extracted
                    st.session_state["typed_once"] = True
                    st.markdown(
                        f'<div class="badge-ok" style="margin-bottom:10px;">'
                        f'✓ {len(decision_text):,} chars from {uploaded_file.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview extracted text"):
                        st.text(decision_text[:800] + ("…" if len(decision_text) > 800 else ""))

        # ── V9: Live keyword scanner
        kw_found = live_scan_keywords(decision_text or "")
        if kw_found and st.session_state.get("typed_once"):
            cats_html = ""
            for cat, words in kw_found.items():
                word_list = ", ".join(f"<em>{w}</em>" for w in words[:3])
                color_map = {
                    "Gender":"chip-e","Age":"chip-w","Racial":"chip-e",
                    "Geographic":"chip-p","Socioeconomic":"chip-w",
                    "Language":"chip-p","Insurance":"chip-n"
                }
                cats_html += (
                    f'<span class="chip {color_map.get(cat,\"chip-n\")}" '
                    f'title="{word_list}">{cat}</span>'
                )
            st.markdown(
                f'<div class="kw-scan">'
                f'<div class="kw-scan-title">⚡ Live Bias Signal Scan</div>'
                f'<div class="kw-found">{cats_html}</div>'
                f'<div style="font-family:var(--ff);font-size:.7rem;color:var(--t3);margin-top:5px;">'
                f'Hover chips to see detected words · This is a quick scan, not the full AI analysis</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif st.session_state.get("typed_once") and decision_text:
            st.markdown(
                '<div class="kw-scan">'
                '<div class="kw-scan-title">⚡ Live Bias Signal Scan</div>'
                '<div class="kw-none">No obvious bias keywords detected — run full analysis to be sure</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Type + char counter row
        tc1, tc2 = st.columns([2, 1])
        with tc1:
            type_opts = ["job","loan","medical","university","other"]
            cur_type  = st.session_state.get("decision_type_sel","job")
            cur_idx   = type_opts.index(cur_type) if cur_type in type_opts else 0
            decision_type = st.selectbox(
                "Decision type", options=type_opts,
                format_func=lambda x: TYPE_LABELS[x],
                index=cur_idx, key="decision_type_sel",
            )
        with tc2:
            n = len((decision_text or "").strip())
            typed_once = st.session_state.get("typed_once", False)
            # V9 FIX: only show red if user has actually typed
            if not typed_once or n == 0:
                cc_cls, bar_col, status = "cc-bad", "#D1D5DB", "0 chars · Too short"
            elif n > 150: cc_cls, bar_col, status = "cc-ok",  "#16A34A", f"{n:,} chars · Ready"
            elif n > 50:  cc_cls, bar_col, status = "cc-mid", "#D97706", f"{n:,} chars · Minimum met"
            else:         cc_cls, bar_col, status = "cc-bad", "#DC2626", f"{n:,} chars · Too short"
            bar_w = min(100, int(n / 3))
            st.markdown(
                f'<div class="char-counter">'
                f'<div class="char-count {cc_cls}">{status}</div>'
                f'<div class="char-track">'
                f'<div class="char-fill" style="width:{bar_w}%;background:{bar_col};"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div style="height:2px"></div>', unsafe_allow_html=True)
        btn_col, hint_col = st.columns([1, 2])
        with btn_col:
            analyse_btn = st.button(
                "⚡ Run Bias Analysis", key="analyse_btn",
                disabled=not _api_key_ok(),
            )
        with hint_col:
            st.markdown(
                '<div class="shortcut-hint" style="margin-top:8px;">'
                'Tip: Load an example from sidebar to try</div>',
                unsafe_allow_html=True,
            )

    with col_help:
        # V9: richer bias dimensions card
        st.markdown(
            '<div class="card" style="padding:1rem;">'
            '<div class="card-label">Bias Dimensions</div>'
            '<div style="display:flex;flex-direction:column;gap:6px;margin-top:4px;">',
            unsafe_allow_html=True,
        )
        dim_icons = {
            "Gender & parental status": ("chip-e", "👤"),
            "Age discrimination":       ("chip-w", "🎂"),
            "Racial / ethnic bias":     ("chip-e", "🌍"),
            "Geographic redlining":     ("chip-p", "📍"),
            "Name-based proxies":       ("chip-p", "🔤"),
            "Socioeconomic status":     ("chip-w", "💰"),
            "Language profiling":       ("chip-p", "💬"),
            "Insurance classification": ("chip-n", "🏥"),
        }
        dims_html = ""
        for dim, (chip, ico) in dim_icons.items():
            dims_html += (
                f'<div style="display:flex;align-items:center;gap:7px;'
                f'padding:4px 0;border-bottom:1px solid var(--border);">'
                f'<span style="font-size:.85rem;">{ico}</span>'
                f'<span style="font-family:var(--ff);font-size:.78rem;color:var(--t2);">{dim}</span>'
                f'</div>'
            )
        st.markdown(dims_html + '</div></div>', unsafe_allow_html=True)

        # V9: historical avg if reports exist
        hist_r = get_all_reports()
        if hist_r:
            bias_r = [r for r in hist_r if r.get("bias_found")]
            bias_pct = int(len(bias_r) / len(hist_r) * 100)
            avg_conf = int(sum(r.get("confidence_score",0) for r in hist_r) / len(hist_r) * 100)
            st.markdown(
                f'<div class="card p-fill" style="margin-top:8px;">'
                f'<div class="card-label">Historical Avg</div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:4px;">'
                f'<div style="text-align:center;">'
                f'<div style="font-family:var(--ff-display);font-size:1.3rem;font-weight:700;color:var(--p);">{bias_pct}%</div>'
                f'<div style="font-family:var(--ff);font-size:.67rem;color:var(--t3);">Bias Rate</div>'
                f'</div>'
                f'<div style="text-align:center;">'
                f'<div style="font-family:var(--ff-display);font-size:1.3rem;font-weight:700;color:var(--p);">{avg_conf}%</div>'
                f'<div style="font-family:var(--ff);font-size:.67rem;color:var(--t3);">Avg Conf.</div>'
                f'</div>'
                f'<div style="text-align:center;">'
                f'<div style="font-family:var(--ff-display);font-size:1.3rem;font-weight:700;color:var(--p);">{len(hist_r)}</div>'
                f'<div style="font-family:var(--ff);font-size:.67rem;color:var(--t3);">Reports</div>'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # ── Run analysis
    if analyse_btn:
        dt = (decision_text or "").strip()
        if not dt:
            st.warning("⚠️ Paste a decision text or upload a file first.")
        else:
            text_hash = services.hash_text(dt)
            cached    = services.find_duplicate(text_hash)

            if cached and not st.session_state.get("force_rerun"):
                st.markdown(
                    '<div class="dup-warn"><div class="dup-icon">⚠️</div>'
                    '<div class="dup-text"><strong>Identical text detected — showing cached result.</strong>'
                    'Click Re-run to force a fresh analysis.</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔄 Re-run anyway", key="force_rerun_btn"):
                    st.session_state["force_rerun"] = True
                    st.rerun()
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
                pct          = int(confidence * 100)

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Verdict banner
                banner_cls = "bias" if bias_found else "clean"
                banner_ico = "⚠️" if bias_found else "✅"
                banner_ttl = "Bias Detected" if bias_found else "No Bias Found"
                banner_sub = "This decision shows discriminatory patterns" if bias_found else "Decision appears free of discriminatory factors"
                st.markdown(
                    f'<div class="v-banner {banner_cls}">'
                    f'<div class="v-banner-icon">{banner_ico}</div>'
                    f'<div class="v-banner-title">{banner_ttl}</div>'
                    f'<div class="v-banner-sub">{banner_sub}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # ── Result grid
                left, right = st.columns([3, 2], gap="large")

                with left:
                    ring_col, info_col = st.columns([1, 2], gap="medium")
                    with ring_col:
                        st.markdown(
                            f'<div class="card" style="text-align:center;padding:1rem .75rem;">'
                            f'<div class="card-label" style="text-align:center;">Risk Score</div>'
                            f'<div class="ring-wrap">'
                            f'{risk_ring_svg(pct, bias_found)}'
                            f'<div class="ring-sev">{severity_label(confidence, bias_found)}</div>'
                            f'<div style="font-family:var(--ff);font-size:.7rem;color:var(--t3);'
                            f'text-align:center;margin-top:1px;">{severity_desc(confidence, bias_found)}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                    with info_col:
                        bt_html  = chips_html(bias_types) if bias_types else '<span class="chip chip-s">None detected</span>'
                        aff_block = ""
                        if affected:
                            aff_block = (
                                f'<div style="margin-top:10px;">'
                                f'<div class="card-label">Characteristic Affected</div>'
                                f'<div style="font-family:var(--ff);font-size:.95rem;'
                                f'font-weight:700;color:var(--w);">{affected.title()}</div>'
                                f'</div>'
                            )
                        st.markdown(
                            f'<div class="card" style="height:100%;">'
                            f'<div class="card-label">Bias Types Detected</div>'
                            f'<div style="line-height:1.9;">{bt_html}</div>'
                            f'{aff_block}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Phrase highlighter
                    if dt and (bias_types or bias_phrases):
                        st.markdown('<div class="vw-label" style="margin-top:12px;">Bias Phrase Highlighter</div>', unsafe_allow_html=True)
                        highlighted = highlight_text(dt, bias_phrases, bias_types)
                        st.markdown(
                            f'<div class="hl-box">{highlighted}</div>'
                            f'<div class="hl-caption">Highlighted = potential proxies for protected characteristics</div>',
                            unsafe_allow_html=True,
                        )

                    # Explanation
                    if explanation:
                        st.markdown('<div class="vw-label" style="margin-top:12px;">What Happened — Plain English</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card w-fill"><div class="card-value">{explanation}</div></div>',
                            unsafe_allow_html=True,
                        )

                with right:
                    orig_cls = "e-fill" if bias_found else "muted"
                    st.markdown(
                        f'<div class="card {orig_cls}">'
                        f'<div class="card-label">Original Decision</div>'
                        f'<div class="card-value mono" style="font-size:1rem;font-weight:700;">'
                        f'{orig.upper()}</div></div>'
                        f'<div class="card s-fill">'
                        f'<div class="card-label">Should Have Been</div>'
                        f'<div class="card-value" style="font-weight:600;">{fair}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if evidence:
                        st.markdown(
                            f'<div class="card w-fill">'
                            f'<div class="card-label">Bias Evidence</div>'
                            f'<div class="card-value" style="font-size:.84rem;">{evidence}</div></div>',
                            unsafe_allow_html=True,
                        )
                    if laws:
                        st.markdown(
                            '<div class="card"><div class="card-label">Relevant Legal Frameworks</div>',
                            unsafe_allow_html=True,
                        )
                        for law in laws:
                            st.markdown(f'<div class="law"><span class="law-icon">⚖️</span>{law}</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                    # V9: Share card
                    st.markdown('<div class="vw-label" style="margin-top:10px;">Share Summary</div>', unsafe_allow_html=True)
                    st.markdown(build_share_summary(report), unsafe_allow_html=True)

                # ── Recommendations
                if recs:
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-label">Recommended Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec"><div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )

                # ── Feedback
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="vw-label">Was This Analysis Helpful?</div>', unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1, 1, 4])
                with fb1:
                    if st.button("👍 Helpful", key="fb_yes"):
                        services.save_feedback(report.get("id"), 1); st.success("Thank you!")
                with fb2:
                    if st.button("👎 Not helpful", key="fb_no"):
                        services.save_feedback(report.get("id"), 0); st.info("Noted.")

                # ── Appeal
                if bias_found:
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-label">Formal Appeal Letter</div>', unsafe_allow_html=True)
                    if st.button("✉️ Generate Appeal Letter", key="appeal_btn"):
                        with st.spinner("Drafting formal appeal…"):
                            try:
                                letter = services.generate_appeal_letter(report, dt, decision_type)
                                st.session_state["appeal_letter"] = letter
                            except Exception as e:
                                st.error(f"❌ {e}")
                    if st.session_state.get("appeal_letter"):
                        letter = st.session_state["appeal_letter"]
                        st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                        dl1, _ = st.columns([1, 3])
                        with dl1:
                            st.download_button("📥 Download Appeal", data=letter,
                                file_name=f"appeal_{report.get('id','')[:8]}.txt",
                                mime="text/plain", key="dl_appeal")

                # ── Download
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 3])
                with dl1:
                    st.download_button("📥 Download Full Report (.txt)",
                        data=build_txt_report(report, dt, decision_type),
                        file_name=f"verdict_v9_{report.get('id','report')[:8]}.txt",
                        mime="text/plain", key="dl_report")

                st.session_state["last_report"] = report
                st.session_state["last_text"]   = dt

# ══════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════

with tab_dashboard:
    hist = get_all_reports()
    if not hist:
        st.markdown(
            '<div class="empty"><div class="empty-ico">📊</div>'
            '<div class="empty-title">No analytics data yet</div>'
            '<div class="empty-sub">Run your first analysis in the Analyse tab to populate the dashboard.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        bias_reps  = [r for r in hist if r.get("bias_found")]
        clean_reps = [r for r in hist if not r.get("bias_found")]
        all_types  = [bt for r in hist for bt in r.get("bias_types", [])]
        scores     = [r.get("confidence_score", 0) for r in hist]
        bias_rate  = len(bias_reps)/len(hist)*100 if hist else 0
        avg_conf   = sum(scores)/len(scores)*100 if scores else 0
        top_bias   = Counter(all_types).most_common(1)[0][0] if all_types else "N/A"
        fb_stats   = services.get_feedback_stats()

        k1,k2,k3,k4,k5 = st.columns(5)
        k1.metric("Total Analyses",  len(hist))
        k2.metric("Bias Rate",       f"{bias_rate:.0f}%")
        k3.metric("Avg Confidence",  f"{avg_conf:.0f}%")
        k4.metric("Top Bias Type",   top_bias)
        k5.metric("Helpful Rating",  f"{fb_stats['helpful_pct']}%" if fb_stats["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="vw-label">Verdict Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps),len(clean_reps)), use_container_width=True, config={"displayModeBar":False})
        with c2:
            st.markdown('<div class="vw-label">Bias Type Frequency</div>', unsafe_allow_html=True)
            if all_types: st.plotly_chart(bar_chart(all_types), use_container_width=True, config={"displayModeBar":False})
            else: st.info("No bias types recorded yet.")

        td = services.get_trend_data()
        if td:
            st.markdown('<div class="vw-label">Daily Bias Rate Trend</div>', unsafe_allow_html=True)
            tf = trend_chart(td)
            if tf: st.plotly_chart(tf, use_container_width=True, config={"displayModeBar":False})

        c3,c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="vw-label">Confidence Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(histogram_chart(scores), use_container_width=True, config={"displayModeBar":False})
        with c4:
            st.markdown('<div class="vw-label">Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist), use_container_width=True, config={"displayModeBar":False})

        c5,c6 = st.columns(2, gap="large")
        with c5:
            st.markdown('<div class="vw-label">Severity Breakdown</div>', unsafe_allow_html=True)
            st.plotly_chart(severity_donut(hist), use_container_width=True, config={"displayModeBar":False})
        with c6:
            st.markdown('<div class="vw-label">Top Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
            if chars: st.plotly_chart(bar_chart(chars), use_container_width=True, config={"displayModeBar":False})
            else: st.info("No data yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        dl1,_ = st.columns([1,4])
        with dl1:
            st.download_button("📥 Export Dashboard (.csv)", data=reports_to_csv(hist),
                file_name=f"verdict_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_csv")

# ══════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════════════

with tab_history:
    hist = get_all_reports()
    if not hist:
        st.markdown(
            '<div class="empty"><div class="empty-ico">📋</div>'
            '<div class="empty-title">No history yet</div>'
            '<div class="empty-sub">All past analyses appear here with filtering and export options.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        f1,f2,f3 = st.columns([2,1,1])
        with f1:
            search_q = st.text_input("Search", placeholder="Search by characteristic, bias type, outcome…", key="history_search")
        with f2:
            filt_v = st.selectbox("Verdict", ["All","Bias Detected","No Bias"], key="hf_verdict")
        with f3:
            sort_by = st.selectbox("Sort", ["Newest First","Oldest First","Highest Confidence","Lowest Confidence"], key="hf_sort")

        dr1,dr2,_ = st.columns([1,1,2])
        with dr1: d_from = st.date_input("From", value=None, key="hf_from")
        with dr2: d_to   = st.date_input("To",   value=None, key="hf_to")

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
        if sort_by == "Newest First":         filtered.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sort_by == "Oldest First":       filtered.sort(key=lambda r: r.get("created_at") or "")
        elif sort_by == "Highest Confidence": filtered.sort(key=lambda r: r.get("confidence_score",0), reverse=True)
        else:                                 filtered.sort(key=lambda r: r.get("confidence_score",0))

        h1,h2 = st.columns([3,1])
        with h1:
            st.markdown(
                f'<div style="font-family:var(--ff);font-size:.78rem;color:var(--t3);margin-bottom:12px;">'
                f'Showing {len(filtered)} of {len(hist)} reports</div>',
                unsafe_allow_html=True,
            )
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

            with st.expander(
                f'{ico} {"Bias Detected" if bias else "No Bias"}  ·  {conf}% confidence  ·  {affected}  ·  {created}',
                expanded=False,
            ):
                ec1,ec2 = st.columns(2, gap="large")
                with ec1:
                    vcls   = "e-fill" if bias else "s-fill"
                    v_text = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                    orig_o = (r.get("original_outcome") or "N/A").upper()
                    st.markdown(
                        f'<div class="card {vcls}"><div class="card-label">Verdict</div>'
                        f'<div class="card-value mono">{v_text}</div></div>'
                        f'<div class="card" style="margin-top:7px;"><div class="card-label">Original Outcome</div>'
                        f'<div class="card-value mono">{orig_o}</div></div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    b_chips  = chips_html(b_types) if b_types else "None"
                    fair_out = r.get("fair_outcome") or "N/A"
                    st.markdown(
                        f'<div class="card w-fill"><div class="card-label">Bias Types</div>'
                        f'<div class="card-value">{b_chips}</div></div>'
                        f'<div class="card s-fill" style="margin-top:7px;"><div class="card-label">Fair Outcome</div>'
                        f'<div class="card-value">{fair_out}</div></div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="card muted" style="margin-top:7px;"><div class="card-label">Explanation</div>'
                        f'<div class="card-value" style="font-size:.855rem;">{r["explanation"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                if laws:
                    lw = chips_html(laws, "chip-p")
                    st.markdown(
                        f'<div class="card p-fill" style="margin-top:7px;"><div class="card-label">Legal Frameworks</div>'
                        f'<div class="card-value">{lw}</div></div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations",[])
                if recs:
                    st.markdown('<div class="vw-label" style="margin-top:10px;">Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec"><div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )
                st.caption(f"Report ID: {r.get('id','N/A')}  ·  Severity: {severity.upper() or 'N/A'}")

# ══════════════════════════════════════════════════════
# TAB 4 — COMPARE
# ══════════════════════════════════════════════════════

with tab_compare:
    if not _api_key_ok(): _api_key_banner()
    st.markdown(
        '<div style="font-family:var(--ff);font-size:.875rem;color:var(--t2);margin-bottom:1.1rem;">'
        'Analyse two decisions side-by-side — verdict, confidence, bias types, and applicable laws.</div>',
        unsafe_allow_html=True,
    )
    cc1,cc2 = st.columns(2, gap="large")
    with cc1:
        st.markdown('<div style="font-family:var(--ff-display);font-size:.95rem;font-weight:700;color:var(--t1);margin-bottom:7px;">Decision A</div>', unsafe_allow_html=True)
        cmp_text1 = st.text_area("Text A", height=130, label_visibility="collapsed", placeholder="Paste first decision…", key="cmp1")
        cmp_type1 = st.selectbox("Type A", ["job","loan","medical","university","other"], format_func=lambda x: TYPE_LABELS[x], label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div style="font-family:var(--ff-display);font-size:.95rem;font-weight:700;color:var(--t1);margin-bottom:7px;">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=130, label_visibility="collapsed", placeholder="Paste second decision…", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job","loan","medical","university","other"], format_func=lambda x: TYPE_LABELS[x], label_visibility="collapsed", key="cmp_type2")

    cmp_btn = st.button("⚡ Compare Both Decisions", key="compare_btn", disabled=not _api_key_ok())
    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Please paste text for both decisions.")
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
                if b1 and b2:   banner = f"⚠️ Both show bias — Decision {'A' if c1v >= c2v else 'B'} has higher confidence ({int(max(c1v,c2v)*100)}%)"
                elif b1:        banner = "⚠️ Decision A shows bias · Decision B appears fair"
                elif b2:        banner = "⚠️ Decision B shows bias · Decision A appears fair"
                else:           banner = "✅ Neither decision shows clear discriminatory patterns"
                st.markdown(f'<div class="winner">{banner}</div>', unsafe_allow_html=True)

                v1c,v2c = st.columns(2, gap="large")
                for col,r,lbl in [(v1c,r1,"A"),(v2c,r2,"B")]:
                    with col:
                        bias=r.get("bias_found",False); conf=r.get("confidence_score",0)
                        vcls="bias" if bias else "clean"; vico="⚠️" if bias else "✅"
                        vsub="Bias Detected" if bias else "No Bias Found"
                        st.markdown(
                            f'<div class="v-banner {vcls}" style="margin-bottom:10px;">'
                            f'<div class="v-banner-icon">{vico}</div>'
                            f'<div class="v-banner-title">Decision {lbl}</div>'
                            f'<div class="v-banner-sub">{vsub}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.plotly_chart(gauge_chart(conf,bias), use_container_width=True, config={"displayModeBar":False})
                        bt_ch=chips_html(r.get("bias_types",[])); sv_bdg=severity_label(conf,bias)
                        st.markdown(f'{bt_ch}<br>{sv_bdg}', unsafe_allow_html=True)
                        r_laws=r.get("legal_frameworks",[])
                        if r_laws: st.markdown(chips_html(r_laws,"chip-p"), unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card s-fill" style="margin-top:9px;">'
                            f'<div class="card-label">Fair Outcome</div>'
                            f'<div class="card-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )
                        if r.get("explanation"):
                            st.markdown(
                                f'<div class="card w-fill"><div class="card-label">What Went Wrong</div>'
                                f'<div class="card-value" style="font-size:.84rem;">{r["explanation"]}</div></div>',
                                unsafe_allow_html=True,
                            )

# ══════════════════════════════════════════════════════
# TAB 5 — BATCH
# ══════════════════════════════════════════════════════

with tab_batch:
    if not _api_key_ok(): _api_key_banner()
    st.markdown(
        '<div style="font-family:var(--ff);font-size:.875rem;color:var(--t2);margin-bottom:1.1rem;">'
        'Paste decisions separated by <code style="background:var(--surf-2);padding:2px 6px;'
        'border-radius:3px;font-family:var(--ff-mono);">---</code> '
        'or upload a CSV with a <code style="background:var(--surf-2);padding:2px 6px;'
        'border-radius:3px;font-family:var(--ff-mono);">text</code> column. Limit: 10 per run.</div>',
        unsafe_allow_html=True,
    )
    batch_mode = st.radio("Batch mode",["✏️ Paste Text","📊 Upload CSV"],horizontal=True,label_visibility="collapsed",key="batch_mode")
    if batch_mode == "✏️ Paste Text":
        batch_text = st.text_area("Batch",height=210,label_visibility="collapsed",key="batch_input",
            placeholder="Decision 1…\n---\nDecision 2…\n---\nDecision 3…")
        raw_blocks = [b.strip() for b in batch_text.split("---") if b.strip()] if batch_text else []
    else:
        batch_csv = st.file_uploader("Upload CSV",type=["csv"],label_visibility="collapsed",key="batch_csv_upload")
        raw_blocks = []
        if batch_csv:
            try:
                df_up=pd.read_csv(batch_csv)
                if "text" in df_up.columns:
                    raw_blocks=df_up["text"].dropna().tolist()
                    st.markdown(f'<div class="badge-ok">✓ {len(raw_blocks)} rows loaded</div>', unsafe_allow_html=True)
                else: st.error("❌ CSV must contain a column named 'text'")
            except Exception as e: st.error(f"❌ {e}")

    bc1,bc2 = st.columns([1,1])
    with bc1:
        batch_type = st.selectbox("Type (all)",["job","loan","medical","university","other"],
            format_func=lambda x: TYPE_LABELS[x],label_visibility="collapsed",key="batch_type")
    with bc2:
        batch_btn = st.button("📦 Run Batch Analysis",key="batch_run",disabled=not _api_key_ok())

    if raw_blocks:
        st.markdown(
            f'<div style="font-family:var(--ff);font-size:.8rem;color:var(--p);font-weight:500;margin-top:3px;">'
            f'● {len(raw_blocks)} decision{"s" if len(raw_blocks)!=1 else ""} queued</div>',
            unsafe_allow_html=True,
        )

    if batch_btn:
        if not raw_blocks: st.warning("⚠️ No decisions found.")
        elif len(raw_blocks) > 10: st.warning("⚠️ Batch limit is 10.")
        else:
            progress=st.progress(0); results=[]; status=st.empty(); t_start=time.time()
            for i, block in enumerate(raw_blocks):
                elapsed=time.time()-t_start
                eta=(elapsed/(i+1))*(len(raw_blocks)-i-1) if i>0 else 0
                eta_str=f"  ·  ETA ~{int(eta)}s" if eta>1 else ""
                status.markdown(
                    f'<div style="font-family:var(--ff);font-size:.8rem;color:var(--p);font-weight:500;">'
                    f'Analysing {i+1} of {len(raw_blocks)}{eta_str}…</div>',
                    unsafe_allow_html=True,
                )
                rep,err=run_analysis(block, batch_type)
                results.append({"text":block,"report":rep,"error":err})
                progress.progress((i+1)/len(raw_blocks))
            progress.empty(); status.empty()

            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            bias_c=sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            clean_c=sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            err_c=sum(1 for r in results if r["error"])
            sm1,sm2,sm3,sm4=st.columns(4)
            sm1.metric("Total",len(results)); sm2.metric("Bias",bias_c)
            sm3.metric("No Bias",clean_c); sm4.metric("Errors",err_c)

            rows=[]
            for i,res in enumerate(results,1):
                rep,error=res["report"],res["error"]
                if error: rows.append({"#":i,"Verdict":"ERROR","Conf":"—","Bias Types":error[:60],"Severity":"—","Affected":"—"})
                elif rep:
                    rows.append({"#":i,
                        "Verdict":"⚠ Bias" if rep.get("bias_found") else "✓ Clean",
                        "Conf":f"{int(rep.get('confidence_score',0)*100)}%",
                        "Bias Types":", ".join(rep.get("bias_types",[])) or "None",
                        "Severity":(rep.get("severity","") or "—").upper(),
                        "Affected":rep.get("affected_characteristic") or "—"})
            if rows:
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_reps=[r["report"] for r in results if r["report"]]
            if all_reps:
                dl1,_=st.columns([1,3])
                with dl1:
                    st.download_button("📥 Download Batch Results (.csv)",data=reports_to_csv(all_reps),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",key="batch_csv_dl")

# ══════════════════════════════════════════════════════
# TAB 6 — SETTINGS
# ══════════════════════════════════════════════════════

with tab_settings:
    st.markdown(
        '<div style="font-family:var(--ff-display);font-size:1.2rem;font-weight:700;'
        'color:var(--t1);margin-bottom:3px;letter-spacing:-.02em;">Settings &amp; System Status</div>'
        '<div style="font-family:var(--ff);font-size:.855rem;color:var(--t2);margin-bottom:1.4rem;">'
        'Verdict Watch V9 Enterprise — configuration and diagnostics.</div>',
        unsafe_allow_html=True,
    )
    s1,s2 = st.columns(2, gap="large")
    with s1:
        st.markdown('<div class="vw-label">API &amp; Model</div>', unsafe_allow_html=True)
        key_set  = _api_key_ok()
        k_vcls   = "s-fill" if key_set else "e-fill"
        k_stat   = "✓ Set (from .env)" if key_set else "✗ Not Set"
        pdf_vcls = "s-fill" if PDF_SUPPORT else "w-fill"
        pdf_stat = "✓ Installed" if PDF_SUPPORT else "Not installed — pip install PyMuPDF"
        st.markdown(
            f'<div class="card {k_vcls}"><div class="card-label">Groq API Key</div>'
            f'<div class="card-value mono">{k_stat}</div></div>'
            f'<div class="card"><div class="card-label">Model</div>'
            f'<div class="card-value mono">llama-3.3-70b-versatile</div></div>'
            f'<div class="card"><div class="card-label">Temperature · Retries</div>'
            f'<div class="card-value mono">0.1  ·  3× exponential backoff</div></div>'
            f'<div class="card {pdf_vcls}"><div class="card-label">PyMuPDF (PDF)</div>'
            f'<div class="card-value mono">{pdf_stat}</div></div>',
            unsafe_allow_html=True,
        )

        # V9: Live API key tester
        st.markdown('<div class="vw-label" style="margin-top:14px;">Live API Key Test</div>', unsafe_allow_html=True)
        if st.button("🔌 Test Groq Connection", key="test_api"):
            if not _api_key_ok():
                st.markdown('<div class="api-test-err">✗ No API key set in .env</div>', unsafe_allow_html=True)
            else:
                with st.spinner("Pinging Groq…"):
                    try:
                        from groq import Groq as _Groq
                        _c = _Groq(api_key=os.getenv("GROQ_API_KEY"))
                        _r = _c.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            max_tokens=5,
                            messages=[{"role":"user","content":"hi"}],
                        )
                        st.markdown('<div class="api-test-ok">✓ Groq API is reachable and responding normally.</div>', unsafe_allow_html=True)
                    except Exception as ex:
                        st.markdown(f'<div class="api-test-err">✗ Connection failed: {ex}</div>', unsafe_allow_html=True)

    with s2:
        st.markdown('<div class="vw-label">Database &amp; Feedback</div>', unsafe_allow_html=True)
        all_r  = get_all_reports()
        fb     = services.get_feedback_stats()
        db_url = os.getenv("DATABASE_URL","sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="card no-border"><div class="card-label">Total Reports</div>'
            f'<div class="card-value large">{len(all_r)}</div></div>'
            f'<div class="card"><div class="card-label">Database URL</div>'
            f'<div class="card-value mono" style="font-size:.75rem;">{db_url}</div></div>'
            f'<div class="card p-fill"><div class="card-label">User Feedback</div>'
            f'<div class="card-value mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="vw-label">V9 Feature Registry</div>', unsafe_allow_html=True)
    features = [
        ("Stray Toolbar Icons Fix",    "All stray Streamlit chrome hidden",          True),
        ("Char Counter Fix",           "Only warns after user starts typing",         True),
        ("Input Mode Toggle Fix",      "Pill toggle replaces broken radio",           True),
        ("Live Bias Keyword Scanner",  "Highlights suspicious words as you type",     True),
        ("Share Summary Card",         "Dark copyable result card",                   True),
        ("Sidebar Sparkline",          "Mini 7-day trend in sidebar",                 True),
        ("Historical Avg Preview",     "Bias rate + confidence before analysis",      True),
        ("Live API Key Tester",        "Ping Groq directly from Settings",            True),
        ("Richer Bias Dimension Card", "Icons + interactive hover",                   True),
        ("V9 Inter + Sora Typography", "Sharper, more professional type system",      True),
        ("Refined Color Tokens",       "Higher contrast, precise palette",            True),
        ("Schema Migration Fix",       "text_hash OperationalError resolved",         True),
        ("Duplicate Detection",        "SHA-256 hash caching",                        True),
        ("Retry Logic",                "3× exponential backoff",                      True),
        ("Bias Phrase Extraction",     "Model-flagged exact phrases",                 True),
        ("Legal Frameworks",           "Laws cited per case",                         True),
        ("Feedback System",            "Per-report thumbs up/down",                   True),
        ("File Upload",                ".txt + .pdf (PyMuPDF)",                       True),
        ("CSV Batch Analysis",         "Up to 10 decisions per run",                  True),
        ("Trend Analytics",            "Daily bias rate chart",                       True),
        ("Appeal Letter Generator",    "Formal discrimination appeal",                True),
        ("Export (TXT + CSV)",         "Full report + batch export",                  True),
    ]
    feat_html='<div class="card" style="padding:.4rem 1.2rem;">'
    for name,desc,enabled in features:
        icon="✓" if enabled else "○"; color="var(--s)" if enabled else "var(--t3)"
        feat_html+=(
            f'<div class="feat-row">'
            f'<span class="feat-name"><span class="feat-check" style="color:{color};margin-right:7px;">{icon}</span>{name}</span>'
            f'<span class="feat-desc">{desc}</span></div>'
        )
    feat_html+='</div>'
    st.markdown(feat_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# TAB 7 — ABOUT
# ══════════════════════════════════════════════════════

with tab_about:
    st.markdown(
        '<div class="about-hero">'
        '<h2>What is Verdict Watch?</h2>'
        '<p>Verdict Watch V9 is an enterprise-grade AI system that analyses automated decisions — '
        'job rejections, loan denials, medical triage, university admissions — for hidden bias. '
        'A 3-step Groq + Llama 3.3 70B pipeline extracts criteria, detects discriminatory patterns, '
        'cites relevant laws, and generates the fair outcome you deserved.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    ab1,ab2 = st.columns([1.6,1], gap="large")
    with ab1:
        st.markdown('<div class="vw-label">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        dims = [
            ("👤","Gender Bias",             "Gender, name, or parental status used as decision factor"),
            ("🎂","Age Discrimination",       "Unfair weighting of age group or seniority"),
            ("🌍","Racial / Ethnic Bias",     "Name-based, nationality, or origin profiling"),
            ("📍","Geographic Redlining",     "Zip code or district as discriminatory proxy"),
            ("💰","Socioeconomic Bias",       "Employment sector or credit score over-weighting"),
            ("💬","Language Discrimination",  "Primary language used against applicants"),
            ("🏥","Insurance Classification", "Insurance tier or status used to rank priority"),
        ]
        for ico,name,desc in dims:
            st.markdown(
                f'<div class="card" style="margin-bottom:6px;">'
                f'<div style="display:flex;gap:10px;align-items:flex-start;">'
                f'<span style="font-size:1.1rem;margin-top:1px;">{ico}</span>'
                f'<div><div class="card-label">{name}</div>'
                f'<div class="card-value" style="font-size:.855rem;">{desc}</div></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    with ab2:
        st.markdown('<div class="vw-label">V9 Changelog</div>', unsafe_allow_html=True)
        changes=[
            ("🔧","Toolbar Fix",        "All stray icons hidden"),
            ("⚡","Live KW Scan",       "Real-time keyword scanner"),
            ("🎴","Share Card",         "Dark copyable summary"),
            ("📊","Sidebar Sparkline",  "Mini 7-day trend"),
            ("🔌","API Tester",         "Live Groq ping in Settings"),
            ("🔡","Typography V9",      "Inter + Sora system"),
            ("🎨","Color Tokens V9",    "Higher contrast palette"),
            ("📌","Historical Avg",     "Pre-analysis stats block"),
            ("✅","Counter Fix",        "No red on empty load"),
            ("🃏","Bias Dim Icons",     "Richer sidebar cards"),
            ("📋","History Filters",    "Search + date + sort"),
            ("📦","Batch ETA",          "Per-item progress timer"),
        ]
        ch_html='<div class="card" style="padding:.4rem 1.2rem;">'
        for ico,name,desc in changes:
            ch_html+=(f'<div class="feat-row"><span class="feat-name">{ico} {name}</span>'
                      f'<span class="feat-desc">{desc}</span></div>')
        ch_html+='</div>'
        st.markdown(ch_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="vw-label">Tech Stack</div>', unsafe_allow_html=True)
        tech=[("⚡ Groq","LLM inference"),("🦙 Llama 3.3 70B","Language model"),
              ("🎈 Streamlit","Full-stack UI"),("🗄 SQLAlchemy","ORM + SQLite"),
              ("📊 Plotly","Interactive charts"),("📄 PyMuPDF","PDF extraction"),
              ("✍️ Inter + Sora","V9 type system")]
        t_html='<div class="card muted" style="padding:.4rem 1.2rem;">'
        for name,desc in tech:
            t_html+=f'<div class="feat-row"><span class="feat-name">{name}</span><span class="feat-desc">{desc}</span></div>'
        t_html+='</div>'
        st.markdown(t_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="card w-fill"><div class="card-label">⚠ Legal Disclaimer</div>'
            '<div class="card-value" style="font-size:.84rem;">'
            'Not legal advice. Built for educational and awareness purposes. '
            'Consult a qualified legal professional for discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )

# ── FOOTER
st.markdown(
    '<div class="vw-footer">'
    'Verdict Watch V9 Enterprise  ·  Powered by Groq / Llama 3.3 70B  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)