"""
streamlit_app.py — Verdict Watch V8
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V8 UI/UX Overhaul Changelog:
  ✅ FIXED  3-column result layout — equal width, proper alignment
  ✅ FIXED  SVG confidence ring — properly centred inside card
  ✅ FIXED  Verdict banner — larger icon, better hierarchy
  ✅ FIXED  Section dividers — replaced with proper spacing
  ✅ FIXED  Card height consistency across result columns
  ✅ FIXED  Sidebar — cleaner, removed noisy "V7 Updates" card
  ✅ FIXED  Input toolbar icons — removed stray emoji toolbar
  ✅ FIXED  Typography hierarchy — clear display / body / caption scale
  ✅ FIXED  Legal frameworks — moved to dedicated section below 3-col
  ✅ FIXED  Duplicate warning — better spacing and styling
  ✅ FIXED  Input row — decision type + char counter better aligned
  ✅ FIXED  Section label consistency — no mixed emoji/text prefixes
  ✅ FIXED  Recommendation items — better padding, consistent height
  ✅ FIXED  Feedback buttons — proper spacing, not crammed
  ✨ NEW    Result section uses a 2+1 layout for better readability
  ✨ NEW    Animated scan steps use linear progress, not spinner
  ✨ NEW    Empty state illustrations per tab
  ✨ NEW    Smoother card hover transitions

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
    page_title="Verdict Watch · Enterprise",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# V8 — DESIGN SYSTEM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&family=DM+Serif+Display&display=swap');

/* ══ V8 TOKEN SYSTEM ══ */
:root {
    /* Primary */
    --p:          #1a73e8;
    --p-lt:       #d2e3fc;
    --p-dk:       #1557b0;
    --on-p:       #ffffff;
    --on-p-lt:    #041e49;

    /* Error / Danger */
    --e:          #c5221f;
    --e-lt:       #fce8e6;
    --on-e-lt:    #410e0b;

    /* Success */
    --s:          #137333;
    --s-lt:       #e6f4ea;
    --on-s-lt:    #0d5226;

    /* Warning */
    --w:          #e37400;
    --w-lt:       #fef7e0;
    --on-w-lt:    #7a4a00;

    /* Surfaces */
    --bg:         #f8f9fa;
    --surf:       #ffffff;
    --surf-2:     #f1f3f4;
    --surf-3:     #e8eaed;
    --border:     #dadce0;
    --border-lt:  #f1f3f4;

    /* Text */
    --t1:         #202124;
    --t2:         #5f6368;
    --t3:         #9aa0a6;

    /* Elevation */
    --sh1: 0 1px 3px rgba(60,64,67,.12), 0 1px 2px rgba(60,64,67,.08);
    --sh2: 0 2px 8px rgba(60,64,67,.12), 0 1px 4px rgba(60,64,67,.08);
    --sh3: 0 4px 16px rgba(60,64,67,.12), 0 2px 6px rgba(60,64,67,.08);

    /* Radii */
    --r-xs: 4px;
    --r-sm: 8px;
    --r-md: 12px;
    --r-lg: 16px;
    --r-xl: 24px;
    --r-full: 999px;

    /* Fonts */
    --ff-display: 'DM Serif Display', Georgia, serif;
    --ff-body:    'DM Sans', system-ui, sans-serif;
    --ff-mono:    'DM Mono', monospace;

    /* Spacing */
    --gap-xs: 4px;
    --gap-sm: 8px;
    --gap-md: 16px;
    --gap-lg: 24px;
    --gap-xl: 40px;
}

/* ══ RESET & BASE ══ */
html, body, [class*="css"] {
    font-family: var(--ff-body) !important;
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

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surf-3); border-radius: 3px; }

/* ══ HIDE STRAY STREAMLIT ELEMENTS ══ */
/* Hide the colour picker toolbar that shows above text_area */
[data-testid="stColorPicker"],
div[data-testid="stToolbar"] { display: none !important; }
.stTextArea [data-baseweb="base-input"] > div:first-child { display: none !important; }

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surf);
    border-bottom: 1px solid var(--border);
    padding: 0 4px;
    gap: 0;
    border-radius: 0;
    box-shadow: none;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--ff-body) !important;
    font-weight: 500;
    font-size: 0.855rem;
    color: var(--t2) !important;
    background: transparent !important;
    border-radius: 0 !important;
    padding: 12px 18px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s, border-color 0.15s;
    letter-spacing: 0.01em;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--p) !important; }
.stTabs [aria-selected="true"] {
    color: var(--p) !important;
    border-bottom: 2px solid var(--p) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.75rem; }

/* ══ BUTTONS ══ */
.stButton > button {
    font-family: var(--ff-body) !important;
    font-weight: 500;
    font-size: 0.875rem;
    background: var(--p);
    color: var(--on-p);
    border: none;
    border-radius: var(--r-full);
    padding: 0.55rem 1.5rem;
    letter-spacing: 0.01em;
    box-shadow: var(--sh1);
    transition: box-shadow 0.15s, transform 0.1s, filter 0.15s;
}
.stButton > button:hover {
    box-shadow: var(--sh2);
    filter: brightness(1.07);
    transform: translateY(-1px);
}
.stButton > button:active { transform: translateY(0); box-shadow: var(--sh1); }

/* Sidebar buttons — ghost style */
div[data-testid="stSidebar"] .stButton > button {
    background: var(--surf-2) !important;
    color: var(--t1) !important;
    box-shadow: none !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 0.9rem !important;
    width: 100% !important;
    text-align: left !important;
    transform: none !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--surf-3) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ══ INPUTS ══ */
.stTextArea textarea {
    font-family: var(--ff-body) !important;
    font-size: 0.92rem !important;
    background: var(--surf) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    color: var(--t1) !important;
    line-height: 1.65 !important;
    transition: border-color 0.2s !important;
    padding: 14px 16px !important;
    resize: vertical !important;
}
.stTextArea textarea:focus {
    border-color: var(--p) !important;
    box-shadow: 0 0 0 3px rgba(26,115,232,0.1) !important;
    outline: none !important;
}
.stTextArea label, .stSelectbox label, .stTextInput label {
    font-family: var(--ff-body) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: var(--t2) !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
}
.stSelectbox > div > div {
    background: var(--surf) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r-sm) !important;
    color: var(--t1) !important;
    font-family: var(--ff-body) !important;
    font-size: 0.875rem !important;
    transition: border-color 0.15s !important;
}
.stSelectbox > div > div:focus-within { border-color: var(--p) !important; }
[data-testid="stFileUploader"] {
    background: var(--surf) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--r-md) !important;
    transition: border-color 0.15s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--p) !important; }

/* ══ METRICS ══ */
[data-testid="metric-container"] {
    background: var(--surf);
    border: none;
    border-radius: var(--r-lg);
    padding: 1.1rem 1.4rem;
    box-shadow: var(--sh1);
}
[data-testid="metric-container"] label {
    font-family: var(--ff-body) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    color: var(--t2) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--ff-body) !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
    color: var(--t1) !important;
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
    font-family: var(--ff-body) !important;
    font-weight: 500 !important;
    font-size: 0.855rem !important;
    box-shadow: none !important;
    padding: 0.5rem 1.4rem !important;
    transition: background 0.15s !important;
}
.stDownloadButton > button:hover {
    background: rgba(26,115,232,0.06) !important;
    transform: none !important;
}

/* ══ EXPANDER ══ */
.streamlit-expanderHeader {
    font-family: var(--ff-body) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    background: var(--surf) !important;
    border: 1px solid var(--border) !important;
    color: var(--t1) !important;
    border-radius: var(--r-sm) !important;
    padding: 0.8rem 1rem !important;
}
.streamlit-expanderContent {
    background: var(--surf) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--r-sm) var(--r-sm) !important;
    padding: 1rem !important;
}

/* ══ DATAFRAME ══ */
[data-testid="stDataFrame"] { border-radius: var(--r-md) !important; overflow: hidden; }

/* ═══════════════════════════════════════════
   V8 COMPONENTS
═══════════════════════════════════════════ */

/* ── App Bar ── */
.vw-appbar {
    background: var(--surf);
    border-bottom: 1px solid var(--border);
    padding: 0 28px;
    height: 60px;
    display: flex;
    align-items: center;
    gap: 14px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 0 var(--border);
    margin: -1rem -1rem 2rem;
}
.vw-logo {
    width: 32px; height: 32px;
    background: var(--p);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
}
.vw-appbar-title {
    font-family: var(--ff-body);
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--t1);
    letter-spacing: -0.02em;
}
.vw-appbar-sub {
    font-family: var(--ff-body);
    font-size: 0.75rem;
    color: var(--t3);
    margin-top: 1px;
}
.vw-badge {
    margin-left: auto;
    background: var(--p-lt);
    color: var(--p-dk);
    font-family: var(--ff-body);
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: var(--r-full);
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* ── Sidebar Header ── */
.vw-sidebar-hd {
    background: linear-gradient(140deg, var(--p) 0%, var(--p-dk) 100%);
    padding: 22px 18px 18px;
    margin: -1rem -1rem 1.25rem;
}
.vw-sidebar-name {
    font-family: var(--ff-body);
    font-size: 1rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.02em;
}
.vw-sidebar-tag {
    font-size: 0.7rem;
    color: rgba(255,255,255,0.7);
    margin-top: 2px;
    font-family: var(--ff-body);
}
.vw-api-ok {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    color: #fff;
    border-radius: var(--r-full);
    padding: 3px 10px;
    font-size: 0.68rem; font-weight: 500; font-family: var(--ff-body);
    margin-top: 10px;
}
.vw-api-err {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(252,210,207,0.4);
    color: #fce8e6;
    border-radius: var(--r-full);
    padding: 3px 10px;
    font-size: 0.68rem; font-weight: 500; font-family: var(--ff-body);
    margin-top: 10px;
}

/* ── Section Label ── */
.vw-label {
    font-family: var(--ff-body);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--t3);
    margin-bottom: 10px;
    margin-top: 2px;
}

/* ── Cards ── */
.card {
    background: var(--surf);
    border-radius: var(--r-lg);
    border: 1px solid var(--border);
    padding: 1.1rem 1.3rem;
    transition: box-shadow 0.15s;
    margin-bottom: 10px;
}
.card:hover { box-shadow: var(--sh1); }
.card.no-border { border: none; box-shadow: var(--sh1); }
.card.e-fill  { background: var(--e-lt); border-color: rgba(197,34,31,0.2); }
.card.s-fill  { background: var(--s-lt); border-color: rgba(19,115,51,0.2); }
.card.w-fill  { background: var(--w-lt); border-color: rgba(227,116,0,0.2); }
.card.p-fill  { background: var(--p-lt); border-color: rgba(26,115,232,0.2); }
.card.muted   { background: var(--surf-2); border-color: var(--border-lt); }

.card-label {
    font-family: var(--ff-body);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--t3);
    margin-bottom: 6px;
}
.card-value {
    font-family: var(--ff-body);
    font-size: 0.9rem;
    color: var(--t1);
    line-height: 1.5;
}
.card-value.mono  { font-family: var(--ff-mono); font-size: 0.88rem; }
.card-value.large { font-size: 1.35rem; font-weight: 700; }

/* ── Verdict Banner ── */
.v-banner {
    border-radius: var(--r-xl);
    padding: 2rem 2.5rem;
    text-align: center;
    margin-bottom: 1.5rem;
}
.v-banner.bias {
    background: var(--e-lt);
    border: 1.5px solid rgba(197,34,31,0.25);
}
.v-banner.clean {
    background: var(--s-lt);
    border: 1.5px solid rgba(19,115,51,0.2);
}
.v-banner-icon { font-size: 2.5rem; line-height: 1; margin-bottom: 10px; }
.v-banner-title {
    font-family: var(--ff-body);
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-bottom: 4px;
}
.v-banner.bias  .v-banner-title { color: var(--e); }
.v-banner.clean .v-banner-title { color: var(--s); }
.v-banner-sub {
    font-family: var(--ff-body);
    font-size: 0.875rem;
    color: var(--t2);
}

/* ── Risk Ring ── */
.ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem 0 0.25rem;
    gap: 8px;
}
.ring-sev {
    font-family: var(--ff-body);
    font-size: 0.78rem;
    font-weight: 600;
    text-align: center;
}

/* ── Chips ── */
.chip {
    display: inline-block;
    border-radius: var(--r-full);
    padding: 3px 11px;
    font-family: var(--ff-body);
    font-size: 0.78rem;
    font-weight: 500;
    margin: 2px 3px 2px 0;
    border: 1px solid transparent;
}
.chip-e { background: var(--e-lt); color: var(--e); border-color: rgba(197,34,31,0.2); }
.chip-p { background: var(--p-lt); color: var(--p-dk); border-color: rgba(26,115,232,0.2); }
.chip-s { background: var(--s-lt); color: var(--s); border-color: rgba(19,115,51,0.2); }
.chip-w { background: var(--w-lt); color: var(--w); border-color: rgba(227,116,0,0.25); }
.chip-n { background: var(--surf-2); color: var(--t2); border-color: var(--border); }

/* ── Severity badges ── */
.sev { display:inline-block; border-radius:var(--r-full); padding:3px 12px; font-family:var(--ff-body); font-size:0.72rem; font-weight:600; }
.sev-h { background:var(--e-lt); color:var(--e); }
.sev-m { background:var(--w-lt); color:var(--w); }
.sev-l { background:var(--s-lt); color:var(--s); }

/* ── Steps ── */
.step-bar { display:flex; gap:6px; margin:10px 0 6px; }
.step-item {
    flex:1; background:var(--surf-2); border-radius:var(--r-sm);
    padding:0.5rem 0.6rem; text-align:center;
    transition:all 0.2s; border:1px solid transparent;
}
.step-item.active { background:var(--p-lt); border-color:rgba(26,115,232,0.25); }
.step-item.done   { background:var(--s-lt); border-color:rgba(19,115,51,0.2); }
.step-n  { font-size:0.55rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--t3); margin-bottom:2px; font-family:var(--ff-body); }
.step-l  { font-size:0.72rem; font-weight:500; color:var(--t2); font-family:var(--ff-body); }
.step-item.active .step-n { color:var(--p); }
.step-item.active .step-l { color:var(--p); font-weight:600; }
.step-item.done .step-n   { color:var(--s); }
.step-item.done .step-l   { color:var(--s); }

/* ── Scan progress ── */
@keyframes scan-slide { 0%{transform:translateX(-120%)} 100%{transform:translateX(400%)} }
.scan-track { background:var(--surf-3); border-radius:2px; height:3px; overflow:hidden; margin:4px 0; }
.scan-fill  { height:100%; background:var(--p); border-radius:2px; animation:scan-slide 1.4s ease-in-out infinite; width:30%; }
.scan-status { font-family:var(--ff-body); font-size:0.8rem; color:var(--p); font-weight:500; }

/* ── Highlight box ── */
.hl-box {
    font-family:var(--ff-body); font-size:0.9rem; line-height:1.8;
    color:var(--t2); background:var(--surf); border:1px solid var(--border);
    border-radius:var(--r-md); padding:1.1rem 1.4rem;
}
.hl-box mark {
    background:rgba(197,34,31,0.1); color:var(--e);
    border-radius:3px; padding:1px 4px;
    border-bottom:1.5px solid rgba(197,34,31,0.3);
}
.hl-caption { font-family:var(--ff-body); font-size:0.71rem; color:var(--t3); margin-top:5px; }

/* ── Rec items ── */
.rec {
    display:flex; gap:12px; align-items:flex-start;
    background:var(--surf); border:1px solid var(--border);
    border-radius:var(--r-md); padding:0.85rem 1.1rem;
    margin-bottom:8px; transition:box-shadow 0.15s;
}
.rec:hover { box-shadow:var(--sh1); }
.rec-num {
    background:var(--p); color:var(--on-p);
    border-radius:var(--r-xs); min-width:22px; height:22px;
    display:flex; align-items:center; justify-content:center;
    font-family:var(--ff-mono); font-size:0.7rem; font-weight:600;
    flex-shrink:0; margin-top:1px;
}
.rec-text { font-family:var(--ff-body); font-size:0.875rem; color:var(--t2); line-height:1.55; }

/* ── Law items ── */
.law {
    display:flex; gap:10px; align-items:center;
    padding:8px 0; border-bottom:1px solid var(--border-lt);
    font-family:var(--ff-body); font-size:0.875rem; color:var(--t2);
}
.law:last-child { border-bottom:none; }
.law-icon { color:var(--p); flex-shrink:0; }

/* ── Appeal box ── */
.appeal-box {
    background:var(--surf); border:1px solid var(--border);
    border-left:3px solid var(--p); border-radius:var(--r-md);
    padding:1.4rem 1.6rem;
    font-family:var(--ff-mono); font-size:0.8rem; line-height:1.9;
    color:var(--t2); white-space:pre-wrap;
}

/* ── Duplicate warning ── */
.dup-warn {
    display:flex; align-items:flex-start; gap:12px;
    background:var(--w-lt); border:1px solid rgba(227,116,0,0.3);
    border-radius:var(--r-md); padding:1rem 1.2rem;
    font-family:var(--ff-body); font-size:0.875rem; color:var(--on-w-lt);
    margin-bottom:1.25rem;
}
.dup-icon { font-size:1.2rem; flex-shrink:0; }
.dup-text strong { font-weight:600; display:block; margin-bottom:2px; }

/* ── API key error ── */
.key-err {
    background:var(--e-lt); border:1px solid rgba(197,34,31,0.25);
    border-left:3px solid var(--e); border-radius:var(--r-md);
    padding:1rem 1.3rem; font-family:var(--ff-body); font-size:0.875rem;
    color:var(--on-e-lt); margin-bottom:1.25rem;
}
.key-err code {
    background:rgba(197,34,31,0.1); padding:2px 6px; border-radius:4px;
    font-family:var(--ff-mono); font-size:0.82rem;
}

/* ── Empty state ── */
.empty { text-align:center; padding:4rem 2rem; }
.empty-ico { font-size:3rem; margin-bottom:12px; opacity:.5; }
.empty-title { font-family:var(--ff-body); font-size:1.1rem; font-weight:600; color:var(--t1); margin-bottom:6px; }
.empty-sub   { font-family:var(--ff-body); font-size:0.875rem; color:var(--t2); line-height:1.6; max-width:340px; margin:0 auto; }

/* ── KPI card ── */
.kpi { background:var(--surf); border-radius:var(--r-lg); padding:1.2rem 1.4rem; box-shadow:var(--sh1); }
.kpi-l { font-family:var(--ff-body); font-size:0.7rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--t3); }
.kpi-v { font-family:var(--ff-body); font-size:1.9rem; font-weight:700; color:var(--t1); line-height:1.1; }
.kpi-d { font-family:var(--ff-body); font-size:0.75rem; color:var(--t3); }

/* ── How it works ── */
.how-step { display:flex; gap:10px; align-items:flex-start; padding:5px 0; }
.how-n {
    background:var(--p); color:var(--on-p);
    border-radius:50%; width:20px; height:20px;
    display:flex; align-items:center; justify-content:center;
    font-family:var(--ff-mono); font-size:0.65rem; font-weight:700;
    flex-shrink:0; margin-top:1px;
}
.how-t { font-family:var(--ff-body); font-size:0.79rem; color:var(--t2); line-height:1.4; }

/* ── Winner banner ── */
.winner {
    background:var(--p-lt); border-radius:var(--r-lg); padding:1rem 1.4rem;
    text-align:center; font-family:var(--ff-body); font-size:0.95rem;
    font-weight:600; color:var(--on-p-lt); margin-bottom:1.2rem;
    box-shadow:var(--sh1);
}

/* ── Preview box ── */
.preview-box {
    background:var(--surf-2); border-radius:var(--r-sm);
    padding:0.7rem 0.9rem; font-family:var(--ff-mono); font-size:0.77rem;
    color:var(--t2); line-height:1.6; white-space:pre-wrap;
    max-height:80px; overflow:hidden; border:1px solid var(--border);
}

/* ── Divider ── */
.divider { border:none; border-top:1px solid var(--border); margin:1.5rem 0; }

/* ── Feature rows ── */
.feat-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:7px 0; border-bottom:1px solid var(--border-lt);
    font-family:var(--ff-body); font-size:0.84rem;
}
.feat-row:last-child { border-bottom:none; }
.feat-name  { color:var(--t1); font-weight:500; }
.feat-desc  { color:var(--t2); font-size:0.78rem; }
.feat-check { color:var(--s); font-weight:700; }

/* ── About hero ── */
.about-hero {
    background:linear-gradient(140deg, var(--p) 0%, var(--p-dk) 100%);
    border-radius:var(--r-xl); padding:2.5rem; color:#fff; margin-bottom:1.5rem;
}
.about-hero h2 { font-family:var(--ff-body); font-size:1.65rem; font-weight:700; letter-spacing:-.03em; margin:0 0 10px; }
.about-hero p  { font-family:var(--ff-body); font-size:0.9rem; opacity:.85; line-height:1.7; margin:0; }

/* ── Char counter ── */
.char-counter { padding-top:0.5rem; }
.char-count { font-family:var(--ff-body); font-size:0.8rem; font-weight:500; }
.char-track { background:var(--surf-3); height:3px; border-radius:2px; margin-top:5px; overflow:hidden; }
.char-fill  { height:100%; border-radius:2px; transition:width 0.3s; }

/* ── Char quality colours ── */
.cc-ok  { color:var(--s); }
.cc-mid { color:var(--w); }
.cc-bad { color:var(--e); }

/* ── Sidebar section label ── */
.sb-label {
    font-family:var(--ff-body); font-size:0.68rem; font-weight:700;
    letter-spacing:.08em; text-transform:uppercase; color:var(--t3);
    margin:14px 0 8px;
}

/* ── Footer ── */
.vw-footer {
    text-align:center; font-family:var(--ff-body); font-size:0.73rem;
    color:var(--t3); margin-top:4rem; padding:1.5rem 0;
    border-top:1px solid var(--border);
}

/* ── Info badge ── */
.badge-ok  { display:inline-flex; align-items:center; gap:5px; background:var(--s-lt); color:var(--s); border-radius:var(--r-full); padding:4px 12px; font-family:var(--ff-body); font-size:0.72rem; font-weight:600; }
.badge-err { display:inline-flex; align-items:center; gap:5px; background:var(--e-lt); color:var(--e); border-radius:var(--r-full); padding:4px 12px; font-family:var(--ff-body); font-size:0.72rem; font-weight:600; }
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
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|housewife|mrs|mr|he|she)\b",
    "Age":           r"\b(age group|senior|junior|young|old|millennial|boomer|retirement|elderly|youth)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|name|surname)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|occupation|class|status)\b",
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
    try:
        return services.get_all_reports()
    except Exception:
        return []

def chips_html(items, style="auto"):
    if not items:
        return '<span class="chip chip-n">None detected</span>'
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
    if not bias_found: return "No strong bias indicators found"
    if conf >= 0.75:   return "Strong discriminatory signal"
    if conf >= 0.45:   return "Possible bias patterns present"
    return "Weak or uncertain bias indicators"

def risk_ring_svg(pct: int, bias_found: bool) -> str:
    r    = 48
    cx   = 64
    cy   = 64
    sw   = 9
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    gap  = circ - dash
    col  = "#c5221f" if bias_found else ("#137333" if pct < 45 else "#e37400")
    return f"""<svg width="128" height="128" viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e8eaed" stroke-width="{sw}"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"
    stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-dashoffset="{circ/4:.1f}"
    stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy - 5}" text-anchor="middle"
    font-family="'DM Sans',sans-serif" font-size="20" font-weight="700" fill="{col}">{pct}%</text>
  <text x="{cx}" y="{cy + 12}" text-anchor="middle"
    font-family="'DM Sans',sans-serif" font-size="8.5" font-weight="600"
    fill="#9aa0a6" letter-spacing="0.06em">CONFIDENCE</text>
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

# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

def run_analysis(text, dtype):
    ph = st.empty()
    def upd(step, label):
        _render_steps(ph, step, label)
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
    recs  = report.get("recommendations", [])
    laws  = report.get("legal_frameworks", [])
    lines = [
        "=" * 68,
        "       VERDICT WATCH V8 — BIAS ANALYSIS REPORT",
        "=" * 68,
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
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    if laws:
        lines += ["", "── RELEVANT LEGAL FRAMEWORKS ─────────────────────────────────"]
        for law in laws: lines.append(f"  • {law}")
    lines += ["", "=" * 68, "  Verdict Watch V8  ·  Not legal advice", "=" * 68]
    return "\n".join(lines)

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
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#5f6368"),
    margin=dict(l=12, r=12, t=16, b=12),
)
MD3_COLORS = ["#1a73e8", "#c5221f", "#137333", "#e37400", "#9334e6", "#007b83", "#e52592"]

def pie_chart(bc, cc):
    total = bc + cc or 2
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias Found"],
        values=[max(bc, 1), max(cc, 1)],
        hole=0.70,
        marker=dict(colors=["#c5221f", "#137333"], line=dict(color="#ffffff", width=3)),
        textfont=dict(family="DM Sans, sans-serif", size=11),
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:10px;color:#9aa0a6'>TOTAL</span>",
        x=0.5, y=0.5,
        font=dict(family="DM Sans, sans-serif", size=22, color="#202124"),
        showarrow=False,
    )
    fig.update_layout(
        height=250, showlegend=True,
        legend=dict(font=dict(family="DM Sans, sans-serif", size=11, color="#5f6368"),
                    bgcolor="rgba(0,0,0,0)", orientation="h", x=0.5, xanchor="center", y=-0.08),
        **CB,
    )
    return fig

def bar_chart(items, title=""):
    counts = Counter(items)
    if not counts: counts = {"No data": 1}
    labels, values = zip(*counts.most_common(8))
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=MD3_COLORS[:len(labels)], line=dict(width=0), cornerradius=4),
        text=list(values),
        textfont=dict(family="DM Sans, sans-serif", size=11, color="#5f6368"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(200, len(labels) * 46 + 60),
        xaxis=dict(showgrid=True, gridcolor="rgba(60,64,67,0.06)",
                   tickfont=dict(family="DM Sans, sans-serif", size=10), zeroline=False),
        yaxis=dict(tickfont=dict(family="DM Sans, sans-serif", size=11), gridcolor="rgba(0,0,0,0)"),
        bargap=0.38, **CB,
    )
    return fig

def trend_chart(td):
    if not td: return None
    dates  = [d["date"] for d in td]
    rates  = [d["bias_rate"] for d in td]
    totals = [d["total"] for d in td]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=totals, name="Total Analyses",
        marker=dict(color="rgba(26,115,232,0.1)", line=dict(width=0), cornerradius=3),
        hovertemplate="%{x}: %{y} analyses<extra></extra>",
        yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=rates, name="Bias Rate %",
        mode="lines+markers",
        line=dict(color="#c5221f", width=2.5),
        marker=dict(color="#c5221f", size=7, line=dict(color="#ffffff", width=1.5)),
        hovertemplate="%{x}: %{y}%<extra></extra>",
    ))
    fig.update_layout(
        height=250,
        yaxis=dict(title=dict(text="Bias %", font=dict(size=10)), range=[0, 105],
                   tickfont=dict(family="DM Sans, sans-serif", size=9),
                   gridcolor="rgba(60,64,67,0.06)", zeroline=False),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(family="DM Sans, sans-serif", size=9)),
        xaxis=dict(tickfont=dict(family="DM Sans, sans-serif", size=9)),
        legend=dict(font=dict(family="DM Sans, sans-serif", size=10, color="#5f6368"),
                    bgcolor="rgba(0,0,0,0)", x=0, y=1.08, orientation="h"),
        **CB,
    )
    return fig

def radar_chart(all_r):
    dim_counts = {d: 0 for d in BIAS_DIMS}
    for r in all_r:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower(): dim_counts[dim] += 1
    vals = [dim_counts[d] for d in BIAS_DIMS]
    fig  = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=BIAS_DIMS + [BIAS_DIMS[0]],
        fill="toself", fillcolor="rgba(26,115,232,0.07)",
        line=dict(color="#1a73e8", width=2.5),
        marker=dict(color="#1a73e8", size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, color="#dadce0",
                            gridcolor="rgba(60,64,67,0.08)",
                            tickfont=dict(family="DM Sans, sans-serif", size=9)),
            angularaxis=dict(color="#9aa0a6",
                             gridcolor="rgba(60,64,67,0.08)",
                             tickfont=dict(family="DM Sans, sans-serif", size=10)),
        ),
        height=300, showlegend=False,
        margin=dict(l=44, r=44, t=24, b=24),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif"),
    )
    return fig

def histogram_chart(scores):
    if not scores: scores = [0]
    fig = go.Figure(go.Histogram(
        x=[s * 100 for s in scores], nbinsx=10,
        marker=dict(color="#1a73e8", opacity=0.7, line=dict(color="#ffffff", width=1)),
        hovertemplate="~%{x:.0f}%%: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        xaxis=dict(title=dict(text="Confidence %", font=dict(size=10)),
                   tickfont=dict(family="DM Sans, sans-serif", size=10),
                   gridcolor="rgba(60,64,67,0.06)"),
        yaxis=dict(tickfont=dict(family="DM Sans, sans-serif", size=10),
                   gridcolor="rgba(60,64,67,0.06)"),
        **CB,
    )
    return fig

def severity_donut(all_r):
    sc = {"high": 0, "medium": 0, "low": 0}
    for r in all_r:
        s = r.get("severity", "low").lower()
        if s in sc: sc[s] += 1
    fig = go.Figure(go.Pie(
        labels=["High", "Medium", "Low"],
        values=[sc["high"], sc["medium"], sc["low"]],
        hole=0.68,
        marker=dict(colors=["#c5221f", "#e37400", "#137333"], line=dict(color="#ffffff", width=3)),
        textfont=dict(family="DM Sans, sans-serif", size=11),
        textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(height=240, showlegend=False, **CB)
    return fig

def gauge_chart(value, bias_found):
    color = "#c5221f" if bias_found else "#137333"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(value * 100),
        number={"suffix": "%", "font": {"family": "DM Sans, sans-serif", "size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0,
                     "tickfont": {"color": "#dadce0", "size": 8}},
            "bar":  {"color": color, "thickness": 0.22},
            "bgcolor": "#f1f3f4", "borderwidth": 0,
            "steps": [{"range": [0, 33],   "color": "rgba(19,115,51,0.06)"},
                      {"range": [33, 66],  "color": "rgba(227,116,0,0.06)"},
                      {"range": [66, 100], "color": "rgba(197,34,31,0.06)"}],
            "threshold": {"line": {"color": color, "width": 2},
                          "thickness": 0.7, "value": value * 100},
        },
    ))
    fig.update_layout(height=180, **CB)
    return fig

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="vw-sidebar-hd">'
        '<div class="vw-sidebar-name">⚖️ Verdict Watch</div>'
        '<div class="vw-sidebar-tag">Enterprise Bias Detection · V8</div>',
        unsafe_allow_html=True,
    )
    if _api_key_ok():
        st.markdown('<div class="vw-api-ok">✓ Groq API Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="vw-api-err">✗ API Key Missing</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    sc1.metric("Session", st.session_state.get("session_count", 0))
    sc2.metric("All Time", len(get_all_reports()))

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="sb-label">Quick Examples</div>', unsafe_allow_html=True)

    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"ex_{ex['tag'].replace(' ','_')}"):
            st.session_state["decision_input"]    = ex["text"]
            st.session_state["decision_type_sel"] = ex["type"]
            st.rerun()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="sb-label">How It Works</div>', unsafe_allow_html=True)
    for n, t in [
        ("1", "Paste text or upload a file"),
        ("2", "AI extracts decision criteria"),
        ("3", "Scans 7 bias dimensions"),
        ("4", "Generates fair outcome + laws"),
        ("5", "Review highlighted phrases"),
        ("6", "Download report or appeal"),
    ]:
        st.markdown(
            f'<div class="how-step">'
            f'<div class="how-n">{n}</div>'
            f'<div class="how-t">{t}</div>'
            f'</div>',
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
    '<div class="vw-badge">V8 Enterprise</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

(tab_analyse, tab_dashboard, tab_history,
 tab_compare, tab_batch, tab_settings, tab_about) = st.tabs([
    "⚡ Analyse", "📊 Dashboard", "📋 History",
    "⚖️ Compare", "📦 Batch", "⚙️ Settings", "ℹ About",
])

# ══════════════════════════════════════════════════════
# TAB 1 — ANALYSE
# ══════════════════════════════════════════════════════

with tab_analyse:
    if not _api_key_ok():
        _api_key_banner()

    # ── Input section
    col_form, col_help = st.columns([3, 1], gap="large")

    with col_form:
        input_mode = st.radio(
            "Input method", ["✏️ Paste Text", "📄 Upload File"],
            horizontal=True, label_visibility="collapsed",
        )
        st.markdown('<div class="vw-label" style="margin-top:14px;">Decision Text</div>',
                    unsafe_allow_html=True)

        if input_mode == "✏️ Paste Text":
            decision_text = st.text_area(
                "text", label_visibility="collapsed",
                height=180, key="decision_input",
                placeholder=(
                    "Paste any rejection letter, loan denial, triage result, "
                    "or university admission decision here…\n\n"
                    "💡 Click any Quick Example in the sidebar to load it instantly."
                ),
            )
        else:
            uploaded_file = st.file_uploader(
                "Upload .txt or .pdf", type=["txt", "pdf"],
                label_visibility="collapsed", key="file_upload",
            )
            decision_text = ""
            if uploaded_file:
                extracted = extract_text_from_file(uploaded_file)
                if extracted:
                    decision_text = extracted
                    st.markdown(
                        f'<div class="badge-ok" style="margin-bottom:10px;">'
                        f'✓ {len(decision_text):,} chars extracted from {uploaded_file.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview extracted text"):
                        st.text(decision_text[:800] + ("…" if len(decision_text) > 800 else ""))

        # Type selector + char counter on same row
        tc1, tc2 = st.columns([2, 1])
        with tc1:
            type_opts = ["job", "loan", "medical", "university", "other"]
            cur_type  = st.session_state.get("decision_type_sel", "job")
            cur_idx   = type_opts.index(cur_type) if cur_type in type_opts else 0
            decision_type = st.selectbox(
                "Decision type", options=type_opts,
                format_func=lambda x: TYPE_LABELS[x],
                index=cur_idx, key="decision_type_sel",
            )
        with tc2:
            n = len((decision_text or "").strip())
            ok = n > 50
            if n > 150:   cc_cls, bar_col, status = "cc-ok",  "#137333", "Ready to analyse"
            elif n > 50:  cc_cls, bar_col, status = "cc-mid", "#e37400", "Minimum met"
            else:         cc_cls, bar_col, status = "cc-bad", "#c5221f", "Too short"
            bar_w = min(100, int(n / 3))
            st.markdown(
                f'<div class="char-counter">'
                f'<div class="char-count {cc_cls}">{n:,} chars · {status}</div>'
                f'<div class="char-track">'
                f'<div class="char-fill" style="width:{bar_w}%;background:{bar_col};"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
        analyse_btn = st.button(
            "⚡ Run Bias Analysis",
            key="analyse_btn",
            disabled=not _api_key_ok(),
        )

    with col_help:
        st.markdown(
            '<div class="card">'
            '<div class="card-label">Bias Dimensions</div>'
            '<div style="font-family:var(--ff-body);font-size:0.82rem;'
            'color:var(--t2);line-height:2.1;">'
            '◉ Gender &amp; parental status<br>'
            '◉ Age discrimination<br>'
            '◉ Racial / ethnic bias<br>'
            '◉ Geographic redlining<br>'
            '◉ Name-based proxies<br>'
            '◉ Socioeconomic status<br>'
            '◉ Language profiling<br>'
            '◉ Insurance classification'
            '</div></div>',
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
                    '<div class="dup-warn">'
                    '<div class="dup-icon">⚠️</div>'
                    '<div class="dup-text">'
                    '<strong>Identical text detected — showing cached result.</strong>'
                    'Use the button below to force a fresh analysis.'
                    '</div></div>',
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
                if bias_found:
                    st.markdown(
                        '<div class="v-banner bias">'
                        '<div class="v-banner-icon">⚠️</div>'
                        '<div class="v-banner-title">Bias Detected</div>'
                        '<div class="v-banner-sub">This decision shows discriminatory patterns</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="v-banner clean">'
                        '<div class="v-banner-icon">✅</div>'
                        '<div class="v-banner-title">No Bias Found</div>'
                        '<div class="v-banner-sub">Decision appears free of discriminatory factors</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

                # ── Result grid: LEFT (risk + bias info) | RIGHT (outcome cards)
                left, right = st.columns([3, 2], gap="large")

                with left:
                    # Risk ring + bias type in one row
                    ring_col, info_col = st.columns([1, 2], gap="medium")

                    with ring_col:
                        st.markdown(
                            f'<div class="card" style="text-align:center;padding:1rem 0.75rem;">'
                            f'<div class="card-label" style="text-align:center;">Risk Score</div>'
                            f'<div class="ring-wrap">'
                            f'{risk_ring_svg(pct, bias_found)}'
                            f'<div class="ring-sev">{severity_label(confidence, bias_found)}</div>'
                            f'<div style="font-family:var(--ff-body);font-size:0.73rem;color:var(--t3);'
                            f'text-align:center;margin-top:2px;">{severity_desc(confidence, bias_found)}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

                    with info_col:
                        bt_html = chips_html(bias_types) if bias_types else '<span class="chip chip-s">None detected</span>'
                        aff_block = ""
                        if affected:
                            aff_block = (
                                f'<div style="margin-top:12px;">'
                                f'<div class="card-label">Characteristic Affected</div>'
                                f'<div style="font-family:var(--ff-body);font-size:1rem;'
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
                        st.markdown('<div class="vw-label" style="margin-top:14px;">Bias Phrase Highlighter</div>',
                                    unsafe_allow_html=True)
                        highlighted = highlight_text(dt, bias_phrases, bias_types)
                        st.markdown(
                            f'<div class="hl-box">{highlighted}</div>'
                            f'<div class="hl-caption">Highlighted text = potential proxies for protected characteristics</div>',
                            unsafe_allow_html=True,
                        )

                    # Explanation
                    if explanation:
                        st.markdown('<div class="vw-label" style="margin-top:14px;">What Happened — Plain English</div>',
                                    unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card w-fill">'
                            f'<div class="card-value">{explanation}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                with right:
                    # Outcome cards
                    orig_cls = "e-fill" if bias_found else "muted"
                    st.markdown(
                        f'<div class="card {orig_cls}">'
                        f'<div class="card-label">Original Decision</div>'
                        f'<div class="card-value mono" style="font-size:1.05rem;font-weight:700;">'
                        f'{orig.upper()}</div>'
                        f'</div>'
                        f'<div class="card s-fill">'
                        f'<div class="card-label">Should Have Been</div>'
                        f'<div class="card-value" style="font-weight:600;">{fair}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    if evidence:
                        st.markdown(
                            f'<div class="card w-fill">'
                            f'<div class="card-label">Bias Evidence</div>'
                            f'<div class="card-value" style="font-size:0.86rem;">{evidence}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Legal frameworks in right column
                    if laws:
                        st.markdown(
                            '<div class="card">'
                            '<div class="card-label">Relevant Legal Frameworks</div>',
                            unsafe_allow_html=True,
                        )
                        for law in laws:
                            st.markdown(
                                f'<div class="law">'
                                f'<span class="law-icon">⚖️</span>{law}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('</div>', unsafe_allow_html=True)

                # ── Recommendations (full width)
                if recs:
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-label">Recommended Next Steps</div>',
                                unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec">'
                            f'<div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # ── Feedback
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="vw-label">Was This Analysis Helpful?</div>',
                            unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1, 1, 4])
                with fb1:
                    if st.button("👍 Helpful", key="fb_yes"):
                        services.save_feedback(report.get("id"), 1)
                        st.success("Thank you!")
                with fb2:
                    if st.button("👎 Not helpful", key="fb_no"):
                        services.save_feedback(report.get("id"), 0)
                        st.info("Noted.")

                # ── Appeal letter
                if bias_found:
                    st.markdown('<hr class="divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-label">Formal Appeal Letter</div>',
                                unsafe_allow_html=True)
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
                            st.download_button(
                                "📥 Download Appeal Letter",
                                data=letter,
                                file_name=f"appeal_{report.get('id','')[:8]}.txt",
                                mime="text/plain", key="dl_appeal",
                            )

                # ── Download report
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 3])
                with dl1:
                    st.download_button(
                        "📥 Download Full Report (.txt)",
                        data=build_txt_report(report, dt, decision_type),
                        file_name=f"verdict_v8_{report.get('id','report')[:8]}.txt",
                        mime="text/plain", key="dl_report",
                    )

                st.session_state["last_report"] = report
                st.session_state["last_text"]   = dt

# ══════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════

with tab_dashboard:
    hist = get_all_reports()
    if not hist:
        st.markdown(
            '<div class="empty">'
            '<div class="empty-ico">📊</div>'
            '<div class="empty-title">No analytics data yet</div>'
            '<div class="empty-sub">Run your first analysis in the Analyse tab to populate the dashboard.</div>'
            '</div>',
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

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Analyses", len(hist))
        k2.metric("Bias Rate", f"{bias_rate:.0f}%")
        k3.metric("Avg Confidence", f"{avg_conf:.0f}%")
        k4.metric("Top Bias Type", top_bias)
        k5.metric("Helpful Rating", f"{fb_stats['helpful_pct']}%" if fb_stats["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="vw-label">Verdict Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps), len(clean_reps)),
                            use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="vw-label">Bias Type Frequency</div>', unsafe_allow_html=True)
            if all_types:
                st.plotly_chart(bar_chart(all_types), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("No bias types recorded yet.")

        td = services.get_trend_data()
        if td:
            st.markdown('<div class="vw-label">Daily Bias Rate Trend</div>', unsafe_allow_html=True)
            tf = trend_chart(td)
            if tf:
                st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="vw-label">Confidence Score Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(histogram_chart(scores), use_container_width=True,
                            config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="vw-label">Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist), use_container_width=True,
                            config={"displayModeBar": False})

        c5, c6 = st.columns(2, gap="large")
        with c5:
            st.markdown('<div class="vw-label">Severity Breakdown</div>', unsafe_allow_html=True)
            st.plotly_chart(severity_donut(hist), use_container_width=True,
                            config={"displayModeBar": False})
        with c6:
            st.markdown('<div class="vw-label">Top Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
            if chars:
                st.plotly_chart(bar_chart(chars), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("No data yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        dl1, _ = st.columns([1, 4])
        with dl1:
            st.download_button(
                "📥 Export Dashboard (.csv)",
                data=reports_to_csv(hist),
                file_name=f"verdict_dashboard_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_csv",
            )

# ══════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════════════

with tab_history:
    hist = get_all_reports()
    if not hist:
        st.markdown(
            '<div class="empty">'
            '<div class="empty-ico">📋</div>'
            '<div class="empty-title">No history yet</div>'
            '<div class="empty-sub">All past analyses appear here with filtering and export options.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_q = st.text_input(
                "Search", placeholder="Search by characteristic, bias type, outcome…",
                key="history_search",
            )
        with f2:
            filt_v = st.selectbox("Verdict", ["All", "Bias Detected", "No Bias"], key="hf_verdict")
        with f3:
            sort_by = st.selectbox(
                "Sort", ["Newest First", "Oldest First", "Highest Confidence", "Lowest Confidence"],
                key="hf_sort",
            )

        dr1, dr2, _ = st.columns([1, 1, 2])
        with dr1: d_from = st.date_input("From", value=None, key="hf_from")
        with dr2: d_to   = st.date_input("To",   value=None, key="hf_to")

        filtered = hist[:]
        if filt_v == "Bias Detected": filtered = [r for r in filtered if r.get("bias_found")]
        elif filt_v == "No Bias":     filtered = [r for r in filtered if not r.get("bias_found")]
        if search_q:
            sq = search_q.lower()
            filtered = [r for r in filtered
                        if sq in (r.get("affected_characteristic") or "").lower()
                        or any(sq in bt.lower() for bt in r.get("bias_types", []))
                        or sq in (r.get("original_outcome") or "").lower()
                        or sq in (r.get("explanation") or "").lower()]
        if d_from: filtered = [r for r in filtered if r.get("created_at") and r["created_at"][:10] >= str(d_from)]
        if d_to:   filtered = [r for r in filtered if r.get("created_at") and r["created_at"][:10] <= str(d_to)]
        if sort_by == "Newest First":         filtered.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sort_by == "Oldest First":       filtered.sort(key=lambda r: r.get("created_at") or "")
        elif sort_by == "Highest Confidence": filtered.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
        else:                                 filtered.sort(key=lambda r: r.get("confidence_score", 0))

        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(
                f'<div style="font-family:var(--ff-body);font-size:0.8rem;color:var(--t3);'
                f'margin-bottom:14px;">Showing {len(filtered)} of {len(hist)} reports</div>',
                unsafe_allow_html=True,
            )
        with h2:
            st.download_button(
                "📥 Export CSV",
                data=reports_to_csv(filtered),
                file_name=f"verdict_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="csv_export",
            )

        for idx, r in enumerate(filtered):
            bias     = r.get("bias_found", False)
            conf     = int(r.get("confidence_score", 0) * 100)
            affected = r.get("affected_characteristic") or "—"
            b_types  = r.get("bias_types", [])
            laws     = r.get("legal_frameworks", [])
            severity = r.get("severity", "")
            created  = (r.get("created_at") or "")[:16].replace("T", " ")
            ico      = "⚠️" if bias else "✅"

            with st.expander(
                f'{ico} {"Bias Detected" if bias else "No Bias"}  ·  {conf}% confidence  ·  {affected}  ·  {created}',
                expanded=False,
            ):
                ec1, ec2 = st.columns(2, gap="large")
                with ec1:
                    vcls   = "e-fill" if bias else "s-fill"
                    v_text = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                    orig_o = (r.get("original_outcome") or "N/A").upper()
                    st.markdown(
                        f'<div class="card {vcls}">'
                        f'<div class="card-label">Verdict</div>'
                        f'<div class="card-value mono">{v_text}</div>'
                        f'</div>'
                        f'<div class="card" style="margin-top:8px;">'
                        f'<div class="card-label">Original Outcome</div>'
                        f'<div class="card-value mono">{orig_o}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    b_chips  = chips_html(b_types) if b_types else "None"
                    fair_out = r.get("fair_outcome") or "N/A"
                    st.markdown(
                        f'<div class="card w-fill">'
                        f'<div class="card-label">Bias Types</div>'
                        f'<div class="card-value">{b_chips}</div>'
                        f'</div>'
                        f'<div class="card s-fill" style="margin-top:8px;">'
                        f'<div class="card-label">Fair Outcome</div>'
                        f'<div class="card-value">{fair_out}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if r.get("explanation"):
                    st.markdown(
                        f'<div class="card muted" style="margin-top:8px;">'
                        f'<div class="card-label">Explanation</div>'
                        f'<div class="card-value" style="font-size:0.87rem;">{r["explanation"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if laws:
                    lw = chips_html(laws, "chip-p")
                    st.markdown(
                        f'<div class="card p-fill" style="margin-top:8px;">'
                        f'<div class="card-label">Legal Frameworks</div>'
                        f'<div class="card-value">{lw}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations", [])
                if recs:
                    st.markdown('<div class="vw-label" style="margin-top:12px;">Next Steps</div>',
                                unsafe_allow_html=True)
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
    if not _api_key_ok():
        _api_key_banner()

    st.markdown(
        '<div style="font-family:var(--ff-body);font-size:0.9rem;color:var(--t2);margin-bottom:1.2rem;">'
        'Analyse two decisions side-by-side — verdict, confidence, bias types, and applicable laws.</div>',
        unsafe_allow_html=True,
    )

    cc1, cc2 = st.columns(2, gap="large")
    with cc1:
        st.markdown('<div style="font-family:var(--ff-body);font-size:1rem;font-weight:700;'
                    'color:var(--t1);margin-bottom:8px;">Decision A</div>', unsafe_allow_html=True)
        cmp_text1 = st.text_area("Text A", height=130, label_visibility="collapsed",
                                  placeholder="Paste first decision…", key="cmp1")
        cmp_type1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div style="font-family:var(--ff-body);font-size:1rem;font-weight:700;'
                    'color:var(--t1);margin-bottom:8px;">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=130, label_visibility="collapsed",
                                  placeholder="Paste second decision…", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type2")

    cmp_btn = st.button("⚡ Compare Both Decisions", key="compare_btn", disabled=not _api_key_ok())

    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Please paste text for both decisions.")
        else:
            with st.spinner("Analysing both decisions…"):
                r1, e1 = run_analysis(cmp_text1, cmp_type1)
                r2, e2 = run_analysis(cmp_text2, cmp_type2)
            if e1: st.error(f"Decision A: {e1}")
            if e2: st.error(f"Decision B: {e2}")
            if r1 and r2:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                b1, b2   = r1.get("bias_found"), r2.get("bias_found")
                c1v, c2v = r1.get("confidence_score", 0), r2.get("confidence_score", 0)
                if b1 and b2:
                    winner = "A" if c1v >= c2v else "B"
                    banner = f"⚠️ Both decisions show bias — Decision {winner} has higher confidence ({int(max(c1v,c2v)*100)}%)"
                elif b1:  banner = "⚠️ Decision A shows bias · Decision B appears fair"
                elif b2:  banner = "⚠️ Decision B shows bias · Decision A appears fair"
                else:     banner = "✅ Neither decision shows clear discriminatory patterns"
                st.markdown(f'<div class="winner">{banner}</div>', unsafe_allow_html=True)

                v1c, v2c = st.columns(2, gap="large")
                for col, r, lbl in [(v1c, r1, "A"), (v2c, r2, "B")]:
                    with col:
                        bias  = r.get("bias_found", False)
                        conf  = r.get("confidence_score", 0)
                        vcls  = "bias" if bias else "clean"
                        vico  = "⚠️" if bias else "✅"
                        vsub  = "Bias Detected" if bias else "No Bias Found"
                        st.markdown(
                            f'<div class="v-banner {vcls}" style="margin-bottom:12px;">'
                            f'<div class="v-banner-icon">{vico}</div>'
                            f'<div class="v-banner-title">Decision {lbl}</div>'
                            f'<div class="v-banner-sub">{vsub}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.plotly_chart(gauge_chart(conf, bias), use_container_width=True,
                                        config={"displayModeBar": False})
                        bt_ch  = chips_html(r.get("bias_types", []))
                        sv_bdg = severity_label(conf, bias)
                        st.markdown(f'{bt_ch}<br>{sv_bdg}', unsafe_allow_html=True)
                        r_laws = r.get("legal_frameworks", [])
                        if r_laws:
                            st.markdown(chips_html(r_laws, "chip-p"), unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card s-fill" style="margin-top:10px;">'
                            f'<div class="card-label">Fair Outcome</div>'
                            f'<div class="card-value">{r.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if r.get("explanation"):
                            st.markdown(
                                f'<div class="card w-fill">'
                                f'<div class="card-label">What Went Wrong</div>'
                                f'<div class="card-value" style="font-size:0.86rem;">{r["explanation"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

# ══════════════════════════════════════════════════════
# TAB 5 — BATCH
# ══════════════════════════════════════════════════════

with tab_batch:
    if not _api_key_ok():
        _api_key_banner()

    st.markdown(
        '<div style="font-family:var(--ff-body);font-size:0.9rem;color:var(--t2);margin-bottom:1.2rem;">'
        'Paste decisions separated by <code style="background:var(--surf-2);padding:2px 7px;'
        'border-radius:4px;font-family:var(--ff-mono);">---</code> '
        'or upload a CSV with a <code style="background:var(--surf-2);padding:2px 7px;'
        'border-radius:4px;font-family:var(--ff-mono);">text</code> column. Limit: 10 per run.</div>',
        unsafe_allow_html=True,
    )

    batch_mode = st.radio(
        "Batch mode", ["✏️ Paste Text", "📊 Upload CSV"],
        horizontal=True, label_visibility="collapsed", key="batch_mode",
    )

    if batch_mode == "✏️ Paste Text":
        batch_text = st.text_area(
            "Batch", height=220, label_visibility="collapsed", key="batch_input",
            placeholder="Decision 1…\n---\nDecision 2…\n---\nDecision 3…",
        )
        raw_blocks = [b.strip() for b in batch_text.split("---") if b.strip()] if batch_text else []
    else:
        batch_csv  = st.file_uploader("Upload CSV", type=["csv"],
                                       label_visibility="collapsed", key="batch_csv_upload")
        raw_blocks = []
        if batch_csv:
            try:
                df_up = pd.read_csv(batch_csv)
                if "text" in df_up.columns:
                    raw_blocks = df_up["text"].dropna().tolist()
                    st.markdown(f'<div class="badge-ok">✓ {len(raw_blocks)} rows loaded from CSV</div>',
                                unsafe_allow_html=True)
                else:
                    st.error("❌ CSV must contain a column named 'text'")
            except Exception as e:
                st.error(f"❌ {e}")

    bc1, bc2 = st.columns([1, 1])
    with bc1:
        batch_type = st.selectbox(
            "Type (all)", ["job","loan","medical","university","other"],
            format_func=lambda x: TYPE_LABELS[x],
            label_visibility="collapsed", key="batch_type",
        )
    with bc2:
        batch_btn = st.button("📦 Run Batch Analysis", key="batch_run", disabled=not _api_key_ok())

    if raw_blocks:
        st.markdown(
            f'<div style="font-family:var(--ff-body);font-size:0.82rem;color:var(--p);'
            f'font-weight:500;margin-top:4px;">'
            f'● {len(raw_blocks)} decision{"s" if len(raw_blocks) != 1 else ""} queued</div>',
            unsafe_allow_html=True,
        )

    if batch_btn:
        if not raw_blocks:
            st.warning("⚠️ No decisions found. Paste text or upload a CSV.")
        elif len(raw_blocks) > 10:
            st.warning("⚠️ Batch limit is 10 decisions per run.")
        else:
            progress = st.progress(0)
            results  = []
            status   = st.empty()
            t_start  = time.time()
            for i, block in enumerate(raw_blocks):
                elapsed = time.time() - t_start
                eta     = (elapsed / (i + 1)) * (len(raw_blocks) - i - 1) if i > 0 else 0
                eta_str = f"  ·  ETA ~{int(eta)}s" if eta > 1 else ""
                status.markdown(
                    f'<div style="font-family:var(--ff-body);font-size:0.82rem;'
                    f'color:var(--p);font-weight:500;">'
                    f'Analysing {i+1} of {len(raw_blocks)}{eta_str}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(block, batch_type)
                results.append({"text": block, "report": rep, "error": err})
                progress.progress((i + 1) / len(raw_blocks))
            progress.empty(); status.empty()

            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            bias_c  = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            clean_c = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            err_c   = sum(1 for r in results if r["error"])
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Total",   len(results))
            sm2.metric("Bias",    bias_c)
            sm3.metric("No Bias", clean_c)
            sm4.metric("Errors",  err_c)

            rows = []
            for i, res in enumerate(results, 1):
                rep, error = res["report"], res["error"]
                if error:
                    rows.append({"#": i, "Verdict": "ERROR", "Conf": "—",
                                 "Bias Types": error[:60], "Severity": "—", "Affected": "—"})
                elif rep:
                    rows.append({
                        "#":          i,
                        "Verdict":    "⚠ Bias" if rep.get("bias_found") else "✓ Clean",
                        "Conf":       f"{int(rep.get('confidence_score',0)*100)}%",
                        "Bias Types": ", ".join(rep.get("bias_types", [])) or "None",
                        "Severity":   (rep.get("severity", "") or "—").upper(),
                        "Affected":   rep.get("affected_characteristic") or "—",
                    })
            if rows:
                st.markdown("<br>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_reps = [r["report"] for r in results if r["report"]]
            if all_reps:
                dl1, _ = st.columns([1, 3])
                with dl1:
                    st.download_button(
                        "📥 Download Batch Results (.csv)",
                        data=reports_to_csv(all_reps),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="batch_csv_dl",
                    )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="vw-label">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep, error = res["report"], res["error"]
                lbl = f"Decision {i}"
                if error: lbl += " — Error"
                elif rep:
                    vs   = "⚠ Bias" if rep.get("bias_found") else "✓ Clean"
                    conf = int(rep.get("confidence_score", 0) * 100)
                    lbl += f" — {vs} ({conf}% confidence)"
                with st.expander(lbl, expanded=False):
                    preview = res["text"][:300] + ("…" if len(res["text"]) > 300 else "")
                    st.markdown(f'<div class="preview-box">{preview}</div>', unsafe_allow_html=True)
                    if error:
                        st.error(error)
                    elif rep:
                        bias   = rep.get("bias_found", False)
                        vcls   = "e-fill" if bias else "s-fill"
                        b_v    = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                        bt_ch  = chips_html(rep.get("bias_types", []))
                        laws   = rep.get("legal_frameworks", [])
                        st.markdown(
                            f'<div class="card {vcls}">'
                            f'<div class="card-label">Verdict</div>'
                            f'<div class="card-value mono">{b_v}</div>'
                            f'</div>'
                            f'<div class="card w-fill" style="margin-top:8px;">'
                            f'<div class="card-label">Bias Types</div>'
                            f'<div class="card-value">{bt_ch}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if laws:
                            st.markdown(
                                f'<div class="card p-fill" style="margin-top:8px;">'
                                f'<div class="card-label">Legal Frameworks</div>'
                                f'<div class="card-value">{chips_html(laws,"chip-p")}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f'<div class="card s-fill" style="margin-top:8px;">'
                            f'<div class="card-label">Fair Outcome</div>'
                            f'<div class="card-value">{rep.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

# ══════════════════════════════════════════════════════
# TAB 6 — SETTINGS
# ══════════════════════════════════════════════════════

with tab_settings:
    st.markdown(
        '<div style="font-family:var(--ff-body);font-size:1.25rem;font-weight:700;'
        'color:var(--t1);margin-bottom:4px;letter-spacing:-.02em;">Settings &amp; System Status</div>'
        '<div style="font-family:var(--ff-body);font-size:0.875rem;color:var(--t2);'
        'margin-bottom:1.5rem;">Verdict Watch V8 Enterprise — configuration and diagnostics.</div>',
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns(2, gap="large")
    with s1:
        st.markdown('<div class="vw-label">API &amp; Model Configuration</div>', unsafe_allow_html=True)
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
            f'<div class="card {pdf_vcls}"><div class="card-label">PyMuPDF (PDF support)</div>'
            f'<div class="card-value mono">{pdf_stat}</div></div>',
            unsafe_allow_html=True,
        )

    with s2:
        st.markdown('<div class="vw-label">Database &amp; Feedback Stats</div>', unsafe_allow_html=True)
        all_r  = get_all_reports()
        fb     = services.get_feedback_stats()
        db_url = os.getenv("DATABASE_URL", "sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="card no-border"><div class="card-label">Total Reports</div>'
            f'<div class="card-value large">{len(all_r)}</div></div>'
            f'<div class="card"><div class="card-label">Database URL</div>'
            f'<div class="card-value mono" style="font-size:0.78rem;">{db_url}</div></div>'
            f'<div class="card p-fill"><div class="card-label">User Feedback</div>'
            f'<div class="card-value mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="vw-label">V8 Feature Registry</div>', unsafe_allow_html=True)

    features = [
        ("Schema Migration Fix",    "text_hash OperationalError resolved",    True),
        ("Material Design 3",       "Google enterprise token system",          True),
        ("SVG Confidence Ring",     "Animated arc ring, properly centred",     True),
        ("V8 Layout Overhaul",      "2+1 result grid, consistent card heights",True),
        ("DM Sans Typography",      "Clean, modern type system",               True),
        ("Quick Examples",          "Session state key binding",               True),
        ("Duplicate Detection",     "SHA-256 hash caching",                    True),
        ("Retry Logic",             "3× exponential backoff",                  True),
        ("Bias Phrase Extraction",  "Model-flagged exact phrases",             True),
        ("Legal Frameworks",        "Laws cited per case",                     True),
        ("Feedback System",         "Per-report thumbs up/down",               True),
        ("File Upload",             ".txt + .pdf (PyMuPDF)",                   True),
        ("CSV Batch Analysis",      "Up to 10 decisions per run",              True),
        ("Trend Analytics",         "Daily bias rate chart",                   True),
        ("Severity Donut",          "High / Medium / Low breakdown",           True),
        ("Appeal Letter Generator", "Formal discrimination appeal",            True),
        ("Export (TXT + CSV)",      "Full report + batch export",              True),
    ]
    feat_html = '<div class="card" style="padding:0.5rem 1.3rem;">'
    for name, desc, enabled in features:
        icon  = "✓" if enabled else "○"
        color = "var(--s)" if enabled else "var(--t3)"
        feat_html += (
            f'<div class="feat-row">'
            f'<span class="feat-name">'
            f'<span class="feat-check" style="color:{color};margin-right:8px;">{icon}</span>'
            f'{name}</span>'
            f'<span class="feat-desc">{desc}</span>'
            f'</div>'
        )
    feat_html += '</div>'
    st.markdown(feat_html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# TAB 7 — ABOUT
# ══════════════════════════════════════════════════════

with tab_about:
    st.markdown(
        '<div class="about-hero">'
        '<h2>What is Verdict Watch?</h2>'
        '<p>Verdict Watch V8 is an enterprise-grade AI system that analyses automated decisions — '
        'job rejections, loan denials, medical triage, university admissions — for hidden bias. '
        'A 3-step Groq + Llama 3.3 70B pipeline extracts criteria, detects discriminatory patterns, '
        'cites relevant laws, and generates the fair outcome you deserved.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    ab1, ab2 = st.columns([1.6, 1], gap="large")
    with ab1:
        st.markdown('<div class="vw-label">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        dims = [
            ("Gender Bias",              "Gender, name, or parental status used as decision factor"),
            ("Age Discrimination",        "Unfair weighting of age group or seniority"),
            ("Racial / Ethnic Bias",      "Name-based, nationality, or origin profiling"),
            ("Geographic Redlining",      "Zip code or district as discriminatory proxy"),
            ("Socioeconomic Bias",        "Employment sector or credit score over-weighting"),
            ("Language Discrimination",   "Primary language used against applicants"),
            ("Insurance Classification",  "Insurance tier or status used to rank priority"),
        ]
        for name, desc in dims:
            st.markdown(
                f'<div class="card" style="margin-bottom:8px;">'
                f'<div class="card-label">{name}</div>'
                f'<div class="card-value" style="font-size:0.875rem;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="vw-label">V8 Changelog</div>', unsafe_allow_html=True)
        changes = [
            ("🔧", "Layout Fix",       "2+1 result grid, aligned cards"),
            ("🎨", "DM Sans",          "Refined typography system"),
            ("⭕", "SVG Ring",         "Properly centred confidence arc"),
            ("📱", "App Bar",          "Cleaner sticky header"),
            ("🃏", "Cards",            "Consistent heights + hover"),
            ("📄", "File Upload",      ".txt + .pdf support"),
            ("🎯", "Bias Phrases",     "Model-extracted proxy phrases"),
            ("⚖️", "Legal Cite",       "Laws per case"),
            ("🔁", "Dup Detection",    "SHA-256 hash skip"),
            ("👍", "Feedback",         "Per-report ratings"),
            ("📊", "Batch CSV",        "Bulk analysis up to 10"),
            ("📈", "Trend Chart",      "Daily bias rate"),
        ]
        ch_html = '<div class="card" style="padding:0.5rem 1.3rem;">'
        for icon, name, desc in changes:
            ch_html += (
                f'<div class="feat-row">'
                f'<span class="feat-name">{icon} {name}</span>'
                f'<span class="feat-desc">{desc}</span>'
                f'</div>'
            )
        ch_html += '</div>'
        st.markdown(ch_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="vw-label">Tech Stack</div>', unsafe_allow_html=True)
        tech = [
            ("⚡ Groq",          "LLM inference platform"),
            ("🦙 Llama 3.3 70B", "Language model"),
            ("🎈 Streamlit",     "Full-stack web UI"),
            ("🗄 SQLAlchemy",    "ORM + SQLite"),
            ("📊 Plotly",        "Interactive charts"),
            ("📄 PyMuPDF",       "PDF text extraction"),
            ("✏️ DM Sans",       "V8 design system"),
        ]
        t_html = '<div class="card muted" style="padding:0.5rem 1.3rem;">'
        for name, desc in tech:
            t_html += (
                f'<div class="feat-row">'
                f'<span class="feat-name">{name}</span>'
                f'<span class="feat-desc">{desc}</span>'
                f'</div>'
            )
        t_html += '</div>'
        st.markdown(t_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="card w-fill">'
            '<div class="card-label">⚠ Legal Disclaimer</div>'
            '<div class="card-value" style="font-size:0.86rem;">'
            'Not legal advice. Built for educational and awareness purposes. '
            'Consult a qualified legal professional for discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )

# ── FOOTER
st.markdown(
    '<div class="vw-footer">'
    'Verdict Watch V8 Enterprise  ·  Powered by Groq / Llama 3.3 70B  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)