"""
streamlit_app.py — Verdict Watch V7
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
V7 Changelog:
  ✅ FIXED  text_hash schema migration (no more OperationalError)
  ✅ FIXED  All f-string / backslash issues
  ✨ NEW    Google Material Design 3 enterprise aesthetic
  ✨ NEW    Google-style top navigation bar
  ✨ NEW    MD3 cards with elevation + ripple hover states
  ✨ NEW    Google Sans / Product Sans inspired typography
  ✨ NEW    Tonal surface system (surface, surface-variant, container)
  ✨ NEW    Risk score ring (SVG progress arc)
  ✨ NEW    Inline audit trail timeline
  ✨ NEW    Protected characteristics chip grid
  ✨ NEW    Google-style empty states with illustrations
  ✨ NEW    Animated scan progress (linear determinate)
  ✨ NEW    Dashboard KPI cards with trend arrows
  ✨ NEW    Dark/light-mode ready CSS variables

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
# GOOGLE MATERIAL DESIGN 3 — ENTERPRISE CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Google+Sans+Display:wght@400;500;700&family=Google+Sans+Mono&family=Roboto:wght@300;400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

/* ══ MD3 TOKEN SYSTEM ══ */
:root {
    /* Primary — Google Blue */
    --md-primary:            #1a73e8;
    --md-on-primary:         #ffffff;
    --md-primary-container:  #d2e3fc;
    --md-on-primary-container: #041e49;

    /* Error — Google Red */
    --md-error:              #d93025;
    --md-on-error:           #ffffff;
    --md-error-container:    #fce8e6;
    --md-on-error-container: #410e0b;

    /* Tertiary — Google Green */
    --md-tertiary:           #137333;
    --md-on-tertiary:        #ffffff;
    --md-tertiary-container: #ceead6;
    --md-on-tertiary-container: #062711;

    /* Warning — Google Yellow */
    --md-warning:            #f29900;
    --md-warning-container:  #fef7e0;

    /* Surfaces */
    --md-background:         #f8f9fa;
    --md-surface:            #ffffff;
    --md-surface-variant:    #f1f3f4;
    --md-surface-container:  #e8eaed;
    --md-surface-container-high: #dadce0;
    --md-outline:            #dadce0;
    --md-outline-variant:    #e8eaed;

    /* Text */
    --md-on-surface:         #202124;
    --md-on-surface-variant: #5f6368;
    --md-on-surface-muted:   #9aa0a6;

    /* Elevation */
    --md-elev-1: 0 1px 2px rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
    --md-elev-2: 0 1px 2px rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
    --md-elev-3: 0 4px 8px 3px rgba(60,64,67,0.15), 0 1px 3px rgba(60,64,67,0.3);

    /* Shape */
    --md-radius-xs:  4px;
    --md-radius-sm:  8px;
    --md-radius-md:  12px;
    --md-radius-lg:  16px;
    --md-radius-xl:  28px;
    --md-radius-full: 999px;

    /* Typography */
    --font-display: 'Google Sans Display', 'Noto Sans', sans-serif;
    --font-body:    'Google Sans', 'Roboto', sans-serif;
    --font-mono:    'Google Sans Mono', 'Roboto Mono', monospace;
}

/* ══ BASE ══ */
html, body, [class*="css"] {
    font-family: var(--font-body) !important;
    background: var(--md-background) !important;
    color: var(--md-on-surface) !important;
}
[data-testid="stAppViewContainer"] {
    background: var(--md-background) !important;
}
[data-testid="stSidebar"] {
    background: var(--md-surface) !important;
    border-right: 1px solid var(--md-outline) !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--md-surface-container); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--md-surface-container-high); }

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    background: var(--md-surface);
    border-bottom: 1px solid var(--md-outline);
    padding: 0 8px; gap: 0;
    border-radius: 0;
    box-shadow: none;
}
.stTabs [data-baseweb="tab"] {
    font-family: var(--font-body) !important;
    font-weight: 500; font-size: 0.875rem;
    color: var(--md-on-surface-variant);
    background: transparent !important;
    border-radius: 0 !important;
    padding: 14px 20px !important;
    border: none !important;
    border-bottom: 3px solid transparent !important;
    transition: all 0.2s ease;
    letter-spacing: 0.01em;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--md-primary) !important;
    background: rgba(26,115,232,0.04) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--md-primary) !important;
    border-bottom: 3px solid var(--md-primary) !important;
    background: transparent !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* ══ BUTTONS ══ */
.stButton > button {
    font-family: var(--font-body) !important;
    font-weight: 500; font-size: 0.875rem;
    background: var(--md-primary);
    color: var(--md-on-primary);
    border: none;
    border-radius: var(--md-radius-xl);
    padding: 0.6rem 1.75rem;
    letter-spacing: 0.01em;
    transition: all 0.2s ease;
    box-shadow: var(--md-elev-1);
}
.stButton > button:hover {
    box-shadow: var(--md-elev-2);
    filter: brightness(1.06);
    transform: translateY(-1px);
}
.stButton > button:active { transform: translateY(0); box-shadow: var(--md-elev-1); }

/* ══ INPUTS ══ */
.stTextArea textarea {
    font-family: var(--font-body) !important;
    font-size: 0.9rem !important;
    background: var(--md-surface) !important;
    border: 1px solid var(--md-outline) !important;
    border-radius: var(--md-radius-md) !important;
    color: var(--md-on-surface) !important;
    line-height: 1.6 !important;
    transition: border-color 0.2s !important;
}
.stTextArea textarea:focus {
    border-color: var(--md-primary) !important;
    border-width: 2px !important;
    box-shadow: none !important;
    outline: none !important;
}
.stTextArea label, .stSelectbox label, .stTextInput label {
    font-family: var(--font-body) !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    color: var(--md-on-surface-variant) !important;
    letter-spacing: 0.01em !important;
}
.stSelectbox > div > div,
.stTextInput > div > div > input {
    background: var(--md-surface) !important;
    border: 1px solid var(--md-outline) !important;
    border-radius: var(--md-radius-sm) !important;
    color: var(--md-on-surface) !important;
    font-family: var(--font-body) !important;
    font-size: 0.875rem !important;
}
[data-testid="stFileUploader"] {
    background: var(--md-surface) !important;
    border: 2px dashed var(--md-outline) !important;
    border-radius: var(--md-radius-md) !important;
}

/* ══ METRICS ══ */
[data-testid="metric-container"] {
    background: var(--md-surface);
    border: none;
    border-radius: var(--md-radius-lg);
    padding: 1.2rem 1.4rem;
    box-shadow: var(--md-elev-1);
}
[data-testid="metric-container"] label {
    font-family: var(--font-body) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    color: var(--md-on-surface-variant) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
    color: var(--md-on-surface) !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-family: var(--font-body) !important;
    font-size: 0.78rem !important;
}

/* ══ PROGRESS ══ */
.stProgress > div > div {
    background: var(--md-primary) !important;
    border-radius: 2px;
}
.stProgress > div {
    background: var(--md-surface-container) !important;
    border-radius: 2px;
}

/* ══ DOWNLOAD BUTTON ══ */
.stDownloadButton > button {
    background: var(--md-surface) !important;
    color: var(--md-primary) !important;
    border: 1px solid var(--md-primary) !important;
    border-radius: var(--md-radius-xl) !important;
    font-family: var(--font-body) !important;
    font-weight: 500; font-size: 0.875rem !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover {
    background: rgba(26,115,232,0.06) !important;
    box-shadow: var(--md-elev-1) !important;
}

/* ══ EXPANDER ══ */
.streamlit-expanderHeader {
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    background: var(--md-surface) !important;
    border: none !important;
    border-bottom: 1px solid var(--md-outline) !important;
    color: var(--md-on-surface) !important;
    border-radius: 0 !important;
    padding: 0.85rem 1rem !important;
}
.streamlit-expanderContent {
    background: var(--md-surface) !important;
    border: 1px solid var(--md-outline) !important;
    border-top: none !important;
    border-radius: 0 0 var(--md-radius-sm) var(--md-radius-sm) !important;
}

/* ══ DATAFRAME ══ */
[data-testid="stDataFrame"] { border-radius: var(--md-radius-md) !important; overflow: hidden; }

/* ═══════════════════════════════════════════
   VERDICT WATCH V7 — CUSTOM COMPONENTS
═══════════════════════════════════════════ */

/* Top App Bar */
.vw-appbar {
    background: var(--md-surface);
    border-bottom: 1px solid var(--md-outline);
    padding: 0 24px;
    height: 64px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 3px rgba(60,64,67,0.12);
    margin: -1rem -1rem 1.5rem;
}
.vw-logo-mark {
    width: 36px; height: 36px;
    background: var(--md-primary);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; flex-shrink: 0;
}
.vw-appbar-title {
    font-family: var(--font-display);
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--md-on-surface);
    letter-spacing: -0.01em;
}
.vw-appbar-sub {
    font-family: var(--font-body);
    font-size: 0.78rem;
    color: var(--md-on-surface-variant);
    margin-top: 1px;
}
.vw-version-chip {
    background: var(--md-primary-container);
    color: var(--md-on-primary-container);
    font-family: var(--font-body);
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: var(--md-radius-full);
    letter-spacing: 0.02em;
    margin-left: auto;
}

/* Sidebar header */
.vw-sidebar-header {
    background: linear-gradient(135deg, var(--md-primary) 0%, #1557b0 100%);
    padding: 20px 16px 16px;
    margin: -1rem -1rem 1rem;
}
.vw-sidebar-product {
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.01em;
}
.vw-sidebar-tagline {
    font-family: var(--font-body);
    font-size: 0.72rem;
    color: rgba(255,255,255,0.75);
    margin-top: 2px;
}
.vw-key-chip-ok {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: #ffffff;
    border-radius: var(--md-radius-full);
    padding: 4px 10px;
    font-family: var(--font-body);
    font-size: 0.68rem;
    font-weight: 500;
    margin-top: 8px;
    letter-spacing: 0.02em;
}
.vw-key-chip-err {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(252,210,207,0.5);
    color: #fce8e6;
    border-radius: var(--md-radius-full);
    padding: 4px 10px;
    font-family: var(--font-body);
    font-size: 0.68rem;
    font-weight: 500;
    margin-top: 8px;
    letter-spacing: 0.02em;
}

/* Section label */
.vw-section-label {
    font-family: var(--font-body);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--md-on-surface-variant);
    margin-bottom: 0.65rem;
    margin-top: 0.3rem;
}

/* MD3 Card */
.md3-card {
    background: var(--md-surface);
    border-radius: var(--md-radius-lg);
    padding: 1.25rem 1.5rem;
    border: none;
    box-shadow: var(--md-elev-1);
    transition: box-shadow 0.2s ease;
    margin-bottom: 0.75rem;
}
.md3-card:hover { box-shadow: var(--md-elev-2); }
.md3-card.filled-error   { background: var(--md-error-container); box-shadow: none; }
.md3-card.filled-success { background: var(--md-tertiary-container); box-shadow: none; }
.md3-card.filled-warning { background: var(--md-warning-container); box-shadow: none; }
.md3-card.filled-primary { background: var(--md-primary-container); box-shadow: none; }
.md3-card.outlined { background: var(--md-surface); border: 1px solid var(--md-outline); box-shadow: none; }
.md3-card.tonal   { background: var(--md-surface-variant); box-shadow: none; }

.md3-card-label {
    font-family: var(--font-body);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--md-on-surface-variant);
    margin-bottom: 0.4rem;
}
.md3-card-value {
    font-family: var(--font-body);
    font-size: 0.93rem;
    color: var(--md-on-surface);
    line-height: 1.55;
}
.md3-card-value.mono {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    font-weight: 500;
}
.md3-card-value.large {
    font-family: var(--font-display);
    font-size: 1.4rem;
    font-weight: 700;
}

/* Verdict banners */
@keyframes bias-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(217,48,37,0); }
    50%      { box-shadow: 0 0 0 6px rgba(217,48,37,0.08); }
}
@keyframes clean-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(19,115,51,0); }
    50%      { box-shadow: 0 0 0 6px rgba(19,115,51,0.06); }
}

.verdict-bias {
    background: var(--md-error-container);
    border: 1.5px solid rgba(217,48,37,0.4);
    border-radius: var(--md-radius-xl);
    padding: 1.5rem 2rem;
    text-align: center;
    animation: bias-pulse 3s ease-in-out infinite;
}
.verdict-clean {
    background: var(--md-tertiary-container);
    border: 1.5px solid rgba(19,115,51,0.3);
    border-radius: var(--md-radius-xl);
    padding: 1.5rem 2rem;
    text-align: center;
    animation: clean-pulse 3s ease-in-out infinite;
}
.v-icon  { font-size: 2.2rem; margin-bottom: 0.3rem; }
.v-label {
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.verdict-bias  .v-label { color: var(--md-error); }
.verdict-clean .v-label { color: var(--md-tertiary); }
.v-sub {
    font-family: var(--font-body);
    font-size: 0.82rem;
    opacity: 0.65;
}
.verdict-bias  .v-sub { color: var(--md-on-error-container); }
.verdict-clean .v-sub { color: var(--md-on-tertiary-container); }

/* Risk ring */
.risk-ring-wrap {
    display: flex; flex-direction: column; align-items: center;
    padding: 1.2rem 0.5rem;
}
.risk-ring-label {
    font-family: var(--font-body);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--md-on-surface-variant);
    margin-bottom: 0.6rem;
}
.risk-ring-sub {
    font-family: var(--font-body);
    font-size: 0.78rem;
    color: var(--md-on-surface-variant);
    text-align: center;
    margin-top: 0.5rem;
    line-height: 1.4;
    max-width: 140px;
}

/* Severity chips */
.sev-high   { display:inline-block; background:var(--md-error-container); color:var(--md-error); border-radius:var(--md-radius-full); padding:3px 12px; font-family:var(--font-body); font-size:0.72rem; font-weight:600; }
.sev-medium { display:inline-block; background:var(--md-warning-container); color:#b06000; border-radius:var(--md-radius-full); padding:3px 12px; font-family:var(--font-body); font-size:0.72rem; font-weight:600; }
.sev-low    { display:inline-block; background:var(--md-tertiary-container); color:var(--md-tertiary); border-radius:var(--md-radius-full); padding:3px 12px; font-family:var(--font-body); font-size:0.72rem; font-weight:600; }

/* Chips */
.chip { display:inline-block; border-radius:var(--md-radius-full); padding:3px 12px; font-family:var(--font-body); font-size:0.78rem; font-weight:500; margin:2px 3px 2px 0; border:1px solid transparent; cursor:default; }
.chip-error   { background:var(--md-error-container); color:var(--md-error); border-color:rgba(217,48,37,0.2); }
.chip-primary { background:var(--md-primary-container); color:var(--md-primary); border-color:rgba(26,115,232,0.2); }
.chip-success { background:var(--md-tertiary-container); color:var(--md-tertiary); border-color:rgba(19,115,51,0.2); }
.chip-warning { background:var(--md-warning-container); color:#b06000; border-color:rgba(242,153,0,0.3); }
.chip-neutral { background:var(--md-surface-variant); color:var(--md-on-surface-variant); border-color:var(--md-outline); }

/* Step indicator */
.step-bar { display:flex; gap:4px; margin:0.75rem 0; }
.step-item {
    flex:1; background:var(--md-surface-variant);
    border-radius:var(--md-radius-sm);
    padding: 0.55rem 0.7rem;
    text-align:center;
    transition: all 0.25s ease;
    border: 1px solid transparent;
}
.step-item.active { background:var(--md-primary-container); border-color:rgba(26,115,232,0.3); }
.step-item.done   { background:var(--md-tertiary-container); border-color:rgba(19,115,51,0.2); }
.step-num   { font-family:var(--font-body); font-size:0.58rem; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:var(--md-on-surface-muted); margin-bottom:2px; }
.step-label { font-family:var(--font-body); font-size:0.73rem; font-weight:500; color:var(--md-on-surface-variant); }
.step-item.active .step-num  { color:var(--md-primary); }
.step-item.active .step-label{ color:var(--md-primary); font-weight:600; }
.step-item.done   .step-num  { color:var(--md-tertiary); }
.step-item.done   .step-label{ color:var(--md-tertiary); }

/* Recommendation list */
.rec-item {
    display:flex; gap:0.9rem; align-items:flex-start;
    background:var(--md-surface);
    border:1px solid var(--md-outline);
    border-radius:var(--md-radius-md);
    padding:0.9rem 1.1rem;
    margin-bottom:0.5rem;
    transition:box-shadow 0.2s;
}
.rec-item:hover { box-shadow: var(--md-elev-1); }
.rec-num {
    background:var(--md-primary);
    color:var(--md-on-primary);
    border-radius:var(--md-radius-xs);
    min-width:22px; height:22px;
    display:flex; align-items:center; justify-content:center;
    font-family:var(--font-mono); font-size:0.7rem; font-weight:600;
    flex-shrink:0; margin-top:1px;
}
.rec-text { font-family:var(--font-body); font-size:0.9rem; color:var(--md-on-surface-variant); line-height:1.55; }

/* Highlight box */
.highlight-box {
    font-family:var(--font-body); font-size:0.9rem; line-height:1.8;
    color:var(--md-on-surface-variant);
    background:var(--md-surface);
    border:1px solid var(--md-outline);
    border-radius:var(--md-radius-md);
    padding:1.2rem 1.5rem;
}
.highlight-box mark {
    background:rgba(217,48,37,0.12);
    color:var(--md-error);
    border-radius:3px;
    padding:1px 4px;
    border-bottom:1.5px solid rgba(217,48,37,0.35);
}

/* Appeal box */
.appeal-box {
    background:var(--md-surface);
    border:1px solid var(--md-outline);
    border-left:4px solid var(--md-primary);
    border-radius:var(--md-radius-md);
    padding:1.5rem 1.8rem;
    font-family:var(--font-mono);
    font-size:0.8rem;
    line-height:1.85;
    color:var(--md-on-surface-variant);
    white-space:pre-wrap;
}

/* Timeline */
.timeline { position:relative; padding-left:20px; }
.timeline::before {
    content:''; position:absolute; left:7px; top:8px; bottom:8px;
    width:2px; background:var(--md-outline);
}
.timeline-item { position:relative; margin-bottom:1rem; }
.timeline-item::before {
    content:''; position:absolute; left:-16px; top:5px;
    width:10px; height:10px;
    border-radius:50%;
    background:var(--md-primary);
    border:2px solid var(--md-surface);
    box-shadow:0 0 0 2px var(--md-primary);
}
.timeline-item.done::before { background:var(--md-tertiary); box-shadow:0 0 0 2px var(--md-tertiary); }
.timeline-time { font-family:var(--font-mono); font-size:0.68rem; color:var(--md-on-surface-muted); margin-bottom:2px; }
.timeline-text { font-family:var(--font-body); font-size:0.85rem; color:var(--md-on-surface-variant); }

/* Duplicate warning */
.dup-warn {
    background:var(--md-warning-container);
    border:1px solid rgba(242,153,0,0.4);
    border-left:4px solid var(--md-warning);
    border-radius:var(--md-radius-md);
    padding:0.9rem 1.2rem;
    font-family:var(--font-body);
    font-size:0.87rem;
    color:#7a4a00;
    margin-bottom:1rem;
}

/* API key error */
.key-error {
    background:var(--md-error-container);
    border:1px solid rgba(217,48,37,0.3);
    border-left:4px solid var(--md-error);
    border-radius:var(--md-radius-md);
    padding:1rem 1.4rem;
    font-family:var(--font-body);
    font-size:0.9rem;
    color:var(--md-on-error-container);
    margin-bottom:1.2rem;
}
.key-error code {
    background:rgba(217,48,37,0.1);
    padding:2px 6px;
    border-radius:4px;
    font-family:var(--font-mono);
    font-size:0.82rem;
}

/* Empty states */
.empty-state { text-align:center; padding:4rem 2rem; }
.empty-illustration { font-size:3.5rem; margin-bottom:1rem; opacity:0.6; }
.empty-title { font-family:var(--font-display); font-size:1.15rem; font-weight:600; color:var(--md-on-surface); margin-bottom:0.4rem; }
.empty-sub   { font-family:var(--font-body); font-size:0.875rem; color:var(--md-on-surface-variant); line-height:1.6; max-width:360px; margin:0 auto; }

/* Law item */
.law-item {
    display:flex; gap:0.65rem; align-items:flex-start;
    padding:0.6rem 0;
    border-bottom:1px solid var(--md-outline-variant);
    font-family:var(--font-body); font-size:0.875rem;
    color:var(--md-on-surface-variant);
}
.law-item:last-child { border-bottom:none; }
.law-gavel { color:var(--md-primary); font-size:1rem; flex-shrink:0; margin-top:1px; }

/* KPI card */
.kpi-card {
    background:var(--md-surface);
    border-radius:var(--md-radius-lg);
    padding:1.3rem 1.5rem;
    box-shadow:var(--md-elev-1);
    display:flex; flex-direction:column; gap:0.25rem;
}
.kpi-label { font-family:var(--font-body); font-size:0.75rem; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; color:var(--md-on-surface-variant); }
.kpi-value { font-family:var(--font-display); font-size:2.1rem; font-weight:700; color:var(--md-on-surface); line-height:1.1; }
.kpi-delta { font-family:var(--font-body); font-size:0.78rem; display:flex; align-items:center; gap:4px; }
.kpi-delta.up   { color:var(--md-tertiary); }
.kpi-delta.down { color:var(--md-error); }
.kpi-delta.neutral { color:var(--md-on-surface-variant); }

/* Footer */
.vw-footer {
    text-align:center;
    font-family:var(--font-body);
    font-size:0.75rem;
    color:var(--md-on-surface-muted);
    margin-top:4rem;
    padding:1.5rem 0;
    border-top:1px solid var(--md-outline);
    letter-spacing:0.01em;
}

/* Sidebar nav item */
.sidebar-nav-item {
    display:flex; align-items:center; gap:10px;
    padding:8px 12px; border-radius:var(--md-radius-full);
    font-family:var(--font-body); font-size:0.875rem; font-weight:500;
    color:var(--md-on-surface-variant);
    cursor:pointer;
    transition:background 0.15s;
    margin-bottom:2px;
}
.sidebar-nav-item:hover { background:var(--md-surface-variant); }
.sidebar-nav-item.active { background:var(--md-primary-container); color:var(--md-on-primary-container); }

/* How it works step */
.how-step {
    display:flex; gap:12px; align-items:flex-start;
    padding:6px 0;
}
.how-step-num {
    background:var(--md-primary);
    color:var(--md-on-primary);
    border-radius:50%; width:22px; height:22px;
    display:flex; align-items:center; justify-content:center;
    font-family:var(--font-mono); font-size:0.68rem; font-weight:700;
    flex-shrink:0; margin-top:1px;
}
.how-step-text { font-family:var(--font-body); font-size:0.8rem; color:var(--md-on-surface-variant); line-height:1.4; }

/* Sidebar example button override */
div[data-testid="stSidebar"] .stButton > button {
    background: var(--md-surface-variant) !important;
    color: var(--md-on-surface) !important;
    box-shadow: none !important;
    border-radius: var(--md-radius-full) !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 1rem !important;
    text-align: left !important;
    width: 100% !important;
    justify-content: flex-start !important;
    border: 1px solid var(--md-outline) !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--md-surface-container) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Badge pill */
.badge-ok  { display:inline-flex; align-items:center; gap:5px; background:var(--md-tertiary-container); color:var(--md-tertiary); border-radius:var(--md-radius-full); padding:4px 12px; font-family:var(--font-body); font-size:0.72rem; font-weight:600; }
.badge-err { display:inline-flex; align-items:center; gap:5px; background:var(--md-error-container); color:var(--md-error); border-radius:var(--md-radius-full); padding:4px 12px; font-family:var(--font-body); font-size:0.72rem; font-weight:600; }

/* Compare winner */
.winner-banner {
    background:var(--md-primary-container);
    border-radius:var(--md-radius-lg);
    padding:1rem 1.4rem;
    text-align:center;
    font-family:var(--font-display);
    font-size:0.95rem;
    font-weight:600;
    color:var(--md-on-primary-container);
    margin-bottom:1.2rem;
    box-shadow:var(--md-elev-1);
}

/* Scan progress bar */
@keyframes scan-slide { 0%{transform:translateX(-100%)} 100%{transform:translateX(400%)} }
.scan-progress-track { background:var(--md-surface-container); border-radius:2px; height:4px; overflow:hidden; margin:6px 0; }
.scan-progress-fill  { height:100%; background:var(--md-primary); border-radius:2px; animation:scan-slide 1.6s ease-in-out infinite; width:25%; }

/* Quality bar */
.quality-track { background:var(--md-surface-container); height:3px; border-radius:2px; margin-top:5px; overflow:hidden; }
.quality-fill  { height:100%; border-radius:2px; transition:width 0.4s ease; }

/* Divider */
.md3-divider { border:none; border-top:1px solid var(--md-outline); margin:1.25rem 0; }

/* Preview box */
.preview-box {
    background:var(--md-surface-variant);
    border-radius:var(--md-radius-sm);
    padding:0.75rem 1rem;
    font-family:var(--font-mono);
    font-size:0.77rem;
    color:var(--md-on-surface-variant);
    line-height:1.6;
    white-space:pre-wrap;
    max-height:80px;
    overflow:hidden;
    border:1px solid var(--md-outline);
}

/* Feature table */
.feature-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:8px 0;
    border-bottom:1px solid var(--md-outline-variant);
    font-family:var(--font-body); font-size:0.84rem;
}
.feature-row:last-child { border-bottom:none; }
.feature-name  { color:var(--md-on-surface); font-weight:500; }
.feature-desc  { color:var(--md-on-surface-variant); font-size:0.78rem; }
.feature-check { color:var(--md-tertiary); font-weight:700; }

/* About hero */
.about-hero {
    background:linear-gradient(135deg, var(--md-primary) 0%, #1557b0 100%);
    border-radius:var(--md-radius-xl);
    padding:2.5rem 2.5rem;
    color:#fff;
    margin-bottom:1.5rem;
}
.about-hero h2 { font-family:var(--font-display); font-size:1.8rem; font-weight:700; letter-spacing:-0.02em; margin:0 0 0.5rem; }
.about-hero p  { font-family:var(--font-body); font-size:0.9rem; opacity:0.85; line-height:1.7; margin:0; }
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

CHIP_COLORS = ["chip-error", "chip-warning", "chip-primary", "chip-success", "chip-neutral",
               "chip-primary", "chip-warning"]

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
        '<div class="key-error">⚠️ <strong>GROQ_API_KEY not found.</strong> '
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
        return '<span class="chip chip-neutral">None detected</span>'
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

def severity_badge(conf, bias_found):
    if not bias_found:
        return '<span class="sev-low">Low Risk</span>'
    if conf >= 0.75:
        return '<span class="sev-high">High Severity</span>'
    if conf >= 0.45:
        return '<span class="sev-medium">Medium Severity</span>'
    return '<span class="sev-low">Low Severity</span>'

def risk_ring_svg(pct: int, bias_found: bool) -> str:
    """Render an SVG arc ring showing confidence %."""
    r      = 52
    cx     = 70
    cy     = 70
    stroke = 10
    circ   = 2 * 3.14159 * r
    dash   = circ * pct / 100
    gap    = circ - dash
    color  = "#d93025" if bias_found else ("#137333" if pct < 45 else "#f29900")
    label_color = color

    return f"""
<svg width="140" height="140" viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
    stroke="#e8eaed" stroke-width="{stroke}" />
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
    stroke="{color}" stroke-width="{stroke}"
    stroke-dasharray="{dash:.1f} {gap:.1f}"
    stroke-dashoffset="{circ/4:.1f}"
    stroke-linecap="round"
    transform="rotate(-90 {cx} {cy})" />
  <text x="{cx}" y="{cy - 6}" text-anchor="middle"
    font-family="'Google Sans Display', sans-serif"
    font-size="22" font-weight="700" fill="{label_color}">{pct}%</text>
  <text x="{cx}" y="{cy + 12}" text-anchor="middle"
    font-family="'Google Sans', sans-serif"
    font-size="9.5" font-weight="500" fill="#9aa0a6" letter-spacing="0.05em">CONFIDENCE</text>
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
            f'<div class="step-num">STEP {icon}</div>'
            f'<div class="step-label">{lbl}</div></div>'
        )
    scan_bar = '<div class="scan-progress-track"><div class="scan-progress-fill"></div></div>'
    ph.markdown(
        f'<div class="step-bar">{"".join(parts)}</div>'
        f'{scan_bar}'
        f'<div style="font-family:var(--font-body);font-size:0.8rem;'
        f'color:var(--md-primary);font-weight:500;margin-top:4px;letter-spacing:0.01em;">'
        f'● {label}</div>',
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
        "       VERDICT WATCH V7 — BIAS ANALYSIS REPORT",
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
        for law in laws:
            lines.append(f"  • {law}")
    lines += ["", "=" * 68, "  Verdict Watch V7  ·  Not legal advice", "=" * 68]
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
# PLOTLY CONFIG — MD3 STYLE
# ─────────────────────────────────────────────

CB = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Google Sans, Roboto, sans-serif", color="#5f6368"),
    margin=dict(l=12, r=12, t=16, b=12),
)

MD3_COLORS = ["#1a73e8", "#d93025", "#137333", "#f29900", "#9334e6", "#007b83", "#e52592"]

def pie_chart(bc, cc):
    total = bc + cc or 2
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias Found"],
        values=[max(bc, 1), max(cc, 1)],
        hole=0.70,
        marker=dict(colors=["#d93025", "#137333"], line=dict(color="#ffffff", width=3)),
        textfont=dict(family="Google Sans, sans-serif", size=11),
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:10px;color:#5f6368'>TOTAL</span>",
        x=0.5, y=0.5,
        font=dict(family="Google Sans Display, sans-serif", size=22, color="#202124"),
        showarrow=False,
    )
    fig.update_layout(
        height=260, showlegend=True,
        legend=dict(font=dict(family="Google Sans, sans-serif", size=11, color="#5f6368"),
                    bgcolor="rgba(0,0,0,0)", orientation="h", x=0.5, xanchor="center", y=-0.08),
        **CB,
    )
    return fig

def bar_chart(items, title=""):
    counts = Counter(items)
    if not counts:
        counts = {"No data": 1}
    labels, values = zip(*counts.most_common(8))
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=MD3_COLORS[:len(labels)],
                    line=dict(width=0),
                    cornerradius=4),
        text=list(values),
        textfont=dict(family="Google Sans, sans-serif", size=11, color="#5f6368"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(200, len(labels) * 46 + 60),
        xaxis=dict(showgrid=True, gridcolor="rgba(60,64,67,0.06)",
                   tickfont=dict(family="Google Sans, sans-serif", size=10), zeroline=False),
        yaxis=dict(tickfont=dict(family="Google Sans, sans-serif", size=11),
                   gridcolor="rgba(0,0,0,0)"),
        bargap=0.38, **CB,
    )
    return fig

def trend_chart(td):
    if not td:
        return None
    dates  = [d["date"] for d in td]
    rates  = [d["bias_rate"] for d in td]
    totals = [d["total"] for d in td]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=totals, name="Total Analyses",
        marker=dict(color="rgba(26,115,232,0.12)", line=dict(width=0), cornerradius=3),
        hovertemplate="%{x}: %{y} analyses<extra></extra>",
        yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=rates, name="Bias Rate %",
        mode="lines+markers",
        line=dict(color="#d93025", width=2.5),
        marker=dict(color="#d93025", size=7, line=dict(color="#ffffff", width=1.5)),
        hovertemplate="%{x}: %{y}%<extra></extra>",
    ))
    fig.update_layout(
        height=260,
        yaxis=dict(title=dict(text="Bias %", font=dict(size=10)),
                   range=[0, 105],
                   tickfont=dict(family="Google Sans, sans-serif", size=9),
                   gridcolor="rgba(60,64,67,0.06)", zeroline=False),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(family="Google Sans, sans-serif", size=9)),
        xaxis=dict(tickfont=dict(family="Google Sans, sans-serif", size=9)),
        legend=dict(font=dict(family="Google Sans, sans-serif", size=10, color="#5f6368"),
                    bgcolor="rgba(0,0,0,0)", x=0, y=1.08, orientation="h"),
        **CB,
    )
    return fig

def radar_chart(all_r):
    dim_counts = {d: 0 for d in BIAS_DIMS}
    for r in all_r:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower():
                    dim_counts[dim] += 1
    vals = [dim_counts[d] for d in BIAS_DIMS]
    fig  = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=BIAS_DIMS + [BIAS_DIMS[0]],
        fill="toself", fillcolor="rgba(26,115,232,0.08)",
        line=dict(color="#1a73e8", width=2.5),
        marker=dict(color="#1a73e8", size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, color="#dadce0",
                            gridcolor="rgba(60,64,67,0.08)",
                            tickfont=dict(family="Google Sans, sans-serif", size=9)),
            angularaxis=dict(color="#9aa0a6",
                             gridcolor="rgba(60,64,67,0.08)",
                             tickfont=dict(family="Google Sans, sans-serif", size=10)),
        ),
        height=310, showlegend=False,
        margin=dict(l=44, r=44, t=24, b=24),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Google Sans, sans-serif"),
    )
    return fig

def histogram_chart(scores):
    if not scores:
        scores = [0]
    fig = go.Figure(go.Histogram(
        x=[s * 100 for s in scores], nbinsx=10,
        marker=dict(color="#1a73e8", opacity=0.7,
                    line=dict(color="#ffffff", width=1)),
        hovertemplate="~%{x:.0f}%%: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        xaxis=dict(title=dict(text="Confidence %", font=dict(size=10)),
                   tickfont=dict(family="Google Sans, sans-serif", size=10),
                   gridcolor="rgba(60,64,67,0.06)"),
        yaxis=dict(tickfont=dict(family="Google Sans, sans-serif", size=10),
                   gridcolor="rgba(60,64,67,0.06)"),
        **CB,
    )
    return fig

def severity_donut(all_r):
    sc = {"high": 0, "medium": 0, "low": 0}
    for r in all_r:
        s = r.get("severity", "low").lower()
        if s in sc:
            sc[s] += 1
    fig = go.Figure(go.Pie(
        labels=["High", "Medium", "Low"],
        values=[sc["high"], sc["medium"], sc["low"]],
        hole=0.68,
        marker=dict(colors=["#d93025", "#f29900", "#137333"],
                    line=dict(color="#ffffff", width=3)),
        textfont=dict(family="Google Sans, sans-serif", size=11),
        textinfo="percent+label",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.update_layout(height=250, showlegend=False, **CB)
    return fig

def gauge_chart(value, bias_found):
    color = "#d93025" if bias_found else "#137333"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(value * 100),
        number={"suffix": "%",
                "font": {"family": "Google Sans Display, sans-serif", "size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0,
                     "tickfont": {"color": "#dadce0", "size": 8}},
            "bar":  {"color": color, "thickness": 0.22},
            "bgcolor": "#f1f3f4", "borderwidth": 0,
            "steps": [{"range": [0,  33], "color": "rgba(19,115,51,0.06)"},
                      {"range": [33, 66], "color": "rgba(242,153,0,0.06)"},
                      {"range": [66,100], "color": "rgba(217,48,37,0.06)"}],
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
        '<div class="vw-sidebar-header">'
        '<div class="vw-sidebar-product">⚖️ Verdict Watch</div>'
        '<div class="vw-sidebar-tagline">Enterprise Bias Detection · V7</div>',
        unsafe_allow_html=True,
    )
    if _api_key_ok():
        st.markdown('<div class="vw-key-chip-ok">✓ Groq API Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="vw-key-chip-err">✗ API Key Missing</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    sc1, sc2 = st.columns(2)
    sc1.metric("Session", st.session_state.get("session_count", 0))
    sc2.metric("All Time", len(get_all_reports()))

    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
    st.markdown('<div class="vw-section-label">Quick Examples</div>', unsafe_allow_html=True)

    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"ex_{ex['tag'].replace(' ','_')}"):
            st.session_state["decision_input"]    = ex["text"]
            st.session_state["decision_type_sel"] = ex["type"]
            st.rerun()

    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
    st.markdown('<div class="vw-section-label">How It Works</div>', unsafe_allow_html=True)
    for n, t in [
        ("1", "Paste text or upload file"),
        ("2", "AI extracts decision criteria"),
        ("3", "Scans 7+ bias dimensions"),
        ("4", "Generates fair outcome + laws"),
        ("5", "Review highlighted phrases"),
        ("6", "Download report or appeal"),
    ]:
        st.markdown(
            f'<div class="how-step">'
            f'<div class="how-step-num">{n}</div>'
            f'<div class="how-step-text">{t}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="vw-appbar">'
    '<div class="vw-logo-mark">⚖️</div>'
    '<div>'
    '<div class="vw-appbar-title">Verdict Watch</div>'
    '<div class="vw-appbar-sub">AI-powered bias detection for automated decisions</div>'
    '</div>'
    '<div class="vw-version-chip">V7 Enterprise</div>'
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

    col_form, col_help = st.columns([3, 1], gap="large")

    with col_form:
        input_mode = st.radio(
            "Input method", ["✏️ Paste Text", "📄 Upload File"],
            horizontal=True, label_visibility="collapsed",
        )
        st.markdown('<div class="vw-section-label" style="margin-top:0.75rem;">Decision Text</div>',
                    unsafe_allow_html=True)

        if input_mode == "✏️ Paste Text":
            decision_text = st.text_area(
                "text", label_visibility="collapsed",
                height=200, key="decision_input",
                placeholder=(
                    "Paste any rejection letter, loan denial, triage result, or "
                    "university admission decision here…\n\n"
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
                        f'<div class="badge-ok" style="margin-bottom:0.6rem;">'
                        f'✓ {len(decision_text):,} chars extracted from {uploaded_file.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview extracted text"):
                        st.text(decision_text[:800] + ("…" if len(decision_text) > 800 else ""))

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
            n       = len((decision_text or "").strip())
            ok      = n > 50
            c_col   = "var(--md-tertiary)" if ok else "var(--md-error)"
            c_suf   = "Ready to analyse" if ok else "Too short"
            bar_w   = min(100, int(n / 3))
            bar_col = "#137333" if n > 150 else ("#f29900" if n > 50 else "#d93025")
            st.markdown(
                f'<div style="padding-top:0.85rem;">'
                f'<div style="font-family:var(--font-body);font-size:0.78rem;'
                f'font-weight:500;color:{c_col};">{n:,} chars · {c_suf}</div>'
                f'<div class="quality-track">'
                f'<div class="quality-fill" style="width:{bar_w}%;background:{bar_col};"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        analyse_btn = st.button(
            "⚡  Run Bias Analysis",
            key="analyse_btn",
            disabled=not _api_key_ok(),
        )

    with col_help:
        st.markdown(
            '<div class="md3-card">'
            '<div class="md3-card-label">Bias Dimensions</div>'
            '<div style="font-family:var(--font-body);font-size:0.82rem;'
            'color:var(--md-on-surface-variant);line-height:2.05;">'
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
        st.markdown(
            '<div class="md3-card filled-primary">'
            '<div class="md3-card-label">V7 Updates</div>'
            '<div style="font-family:var(--font-body);font-size:0.8rem;'
            'color:var(--md-on-primary-container);line-height:1.9;">'
            '✓ Schema migration fix<br>'
            '✓ Material Design 3<br>'
            '✓ SVG confidence ring<br>'
            '✓ Google enterprise theme'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ── RUN ANALYSIS
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
                    '⚠️ <strong>Identical text detected</strong> — showing cached result. '
                    'Use Re-run to force a fresh analysis.</div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔄 Re-run anyway", key="force_rerun_btn"):
                    st.session_state["force_rerun"] = True
                    st.rerun()
                report, err = cached, None
            else:
                st.session_state.pop("force_rerun", None)
                st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
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

                # Verdict banner
                if bias_found:
                    st.markdown(
                        '<div class="verdict-bias">'
                        '<div class="v-icon">⚠️</div>'
                        '<div class="v-label">Bias Detected</div>'
                        '<div class="v-sub">This decision shows discriminatory patterns</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="verdict-clean">'
                        '<div class="v-icon">✅</div>'
                        '<div class="v-label">No Bias Found</div>'
                        '<div class="v-sub">Decision appears free of discriminatory factors</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                # Three-column result
                r1, r2, r3 = st.columns([1.1, 1.6, 1.5])

                with r1:
                    pct = int(confidence * 100)
                    ring_svg = risk_ring_svg(pct, bias_found)
                    sev_badge = severity_badge(confidence, bias_found)
                    desc = ("High confidence — strong discriminatory signal" if pct >= 75
                            else "Moderate — possible bias patterns" if pct >= 45
                            else "Low — limited bias indicators")
                    st.markdown(
                        f'<div class="md3-card" style="text-align:center;">'
                        f'<div class="md3-card-label" style="text-align:left;">Risk Assessment</div>'
                        f'{ring_svg}'
                        f'<div style="margin-top:4px;">{sev_badge}</div>'
                        f'<div class="risk-ring-sub">{desc}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with r2:
                    bt_html = chips_html(bias_types) if bias_types else '<span class="chip chip-success">None detected</span>'
                    aff_html = ""
                    if affected:
                        aff_html = (
                            f'<div style="margin-top:0.8rem;">'
                            f'<div class="md3-card-label">Characteristic Affected</div>'
                            f'<div style="font-family:var(--font-body);font-size:0.95rem;'
                            f'font-weight:600;color:#b06000;">{affected}</div>'
                            f'</div>'
                        )
                    st.markdown(
                        f'<div class="md3-card">'
                        f'<div class="md3-card-label">Bias Types Detected</div>'
                        f'<div class="md3-card-value">{bt_html}</div>'
                        f'{aff_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    if laws:
                        st.markdown(
                            '<div class="md3-card outlined">'
                            '<div class="md3-card-label">⚖ Relevant Legal Frameworks</div>'
                            '<div class="timeline">',
                            unsafe_allow_html=True,
                        )
                        for law in laws:
                            st.markdown(
                                f'<div class="law-item">'
                                f'<span class="law-gavel">⚖</span>{law}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('</div></div>', unsafe_allow_html=True)

                with r3:
                    orig_c = "filled-error" if bias_found else "tonal"
                    fair_c = "filled-success"
                    st.markdown(
                        f'<div class="md3-card {orig_c}">'
                        f'<div class="md3-card-label">Original Decision</div>'
                        f'<div class="md3-card-value mono">{orig.upper()}</div>'
                        f'</div>'
                        f'<div class="md3-card {fair_c}">'
                        f'<div class="md3-card-label">Should Have Been</div>'
                        f'<div class="md3-card-value">{fair}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if evidence:
                        st.markdown(
                            f'<div class="md3-card filled-warning">'
                            f'<div class="md3-card-label">Bias Evidence</div>'
                            f'<div class="md3-card-value" style="font-size:0.86rem;">{evidence}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Phrase highlighter
                if dt and (bias_types or bias_phrases):
                    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-section-label">🔍 Bias Phrase Highlighter</div>',
                                unsafe_allow_html=True)
                    highlighted = highlight_text(dt, bias_phrases, bias_types)
                    st.markdown(
                        f'<div class="highlight-box">{highlighted}</div>'
                        f'<div style="font-family:var(--font-body);font-size:0.72rem;'
                        f'color:var(--md-on-surface-muted);margin-top:0.4rem;">'
                        f'Highlighted text = potential proxies for protected characteristics</div>',
                        unsafe_allow_html=True,
                    )

                # Explanation
                if explanation:
                    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-section-label">What Happened — Plain English</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="md3-card filled-warning">'
                        f'<div class="md3-card-value">{explanation}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Recommendations
                if recs:
                    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-section-label">Recommended Next Steps</div>',
                                unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec-item">'
                            f'<div class="rec-num">{i}</div>'
                            f'<div class="rec-text">{rec}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Feedback
                st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
                st.markdown('<div class="vw-section-label">Was This Analysis Helpful?</div>',
                            unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1, 1, 3])
                with fb1:
                    if st.button("👍  Helpful", key="fb_yes"):
                        services.save_feedback(report.get("id"), 1)
                        st.success("Thank you for your feedback!")
                with fb2:
                    if st.button("👎  Not helpful", key="fb_no"):
                        services.save_feedback(report.get("id"), 0)
                        st.info("Feedback noted.")

                # Appeal letter
                if bias_found:
                    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
                    st.markdown('<div class="vw-section-label">✉️ Formal Appeal Letter</div>',
                                unsafe_allow_html=True)
                    if st.button("✉️  Generate Appeal Letter", key="appeal_btn"):
                        with st.spinner("Drafting formal appeal…"):
                            try:
                                letter = services.generate_appeal_letter(report, dt, decision_type)
                                st.session_state["appeal_letter"] = letter
                            except Exception as e:
                                st.error(f"❌ {e}")
                    if st.session_state.get("appeal_letter"):
                        letter = st.session_state["appeal_letter"]
                        st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                        dl1, _ = st.columns([1, 2])
                        with dl1:
                            st.download_button(
                                "📥 Download Appeal Letter",
                                data=letter,
                                file_name=f"appeal_{report.get('id','')[:8]}.txt",
                                mime="text/plain", key="dl_appeal",
                            )

                # Download report
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Full Report (.txt)",
                        data=build_txt_report(report, dt, decision_type),
                        file_name=f"verdict_v7_{report.get('id','report')[:8]}.txt",
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
            '<div class="empty-state">'
            '<div class="empty-illustration">📊</div>'
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

        # KPI row
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Analyses", len(hist))
        k2.metric("Bias Rate", f"{bias_rate:.0f}%")
        k3.metric("Avg Confidence", f"{avg_conf:.0f}%")
        k4.metric("Top Bias Type", top_bias)
        k5.metric("Helpful Rating",
                  f"{fb_stats['helpful_pct']}%" if fb_stats["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="vw-section-label">Verdict Distribution</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps), len(clean_reps)),
                            use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="vw-section-label">Bias Type Frequency</div>',
                        unsafe_allow_html=True)
            if all_types:
                st.plotly_chart(bar_chart(all_types), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("No bias types recorded yet.")

        td = services.get_trend_data()
        if td:
            st.markdown('<div class="vw-section-label">Daily Bias Rate Trend</div>',
                        unsafe_allow_html=True)
            tf = trend_chart(td)
            if tf:
                st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="vw-section-label">Confidence Score Distribution</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(histogram_chart(scores), use_container_width=True,
                            config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="vw-section-label">Bias Dimension Radar</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist), use_container_width=True,
                            config={"displayModeBar": False})

        c5, c6 = st.columns(2, gap="large")
        with c5:
            st.markdown('<div class="vw-section-label">Severity Breakdown</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(severity_donut(hist), use_container_width=True,
                            config={"displayModeBar": False})
        with c6:
            st.markdown('<div class="vw-section-label">Top Affected Characteristics</div>',
                        unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
            if chars:
                st.plotly_chart(bar_chart(chars), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.info("No data yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        exp1, _ = st.columns([1, 3])
        with exp1:
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
            '<div class="empty-state">'
            '<div class="empty-illustration">📋</div>'
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
            filt_v = st.selectbox("Verdict", ["All", "Bias Detected", "No Bias"],
                                   key="hf_verdict")
        with f3:
            sort_by = st.selectbox(
                "Sort",
                ["Newest First", "Oldest First", "Highest Confidence", "Lowest Confidence"],
                key="hf_sort",
            )

        dr1, dr2, _ = st.columns([1, 1, 2])
        with dr1: d_from = st.date_input("From", value=None, key="hf_from", label_visibility="visible")
        with dr2: d_to   = st.date_input("To",   value=None, key="hf_to",   label_visibility="visible")

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
                f'<div style="font-family:var(--font-body);font-size:0.8rem;'
                f'color:var(--md-on-surface-variant);margin-bottom:0.9rem;">'
                f'Showing {len(filtered)} of {len(hist)} reports</div>',
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
                    vcls    = "filled-error" if bias else "filled-success"
                    v_text  = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                    orig_o  = (r.get("original_outcome") or "N/A").upper()
                    st.markdown(
                        f'<div class="md3-card {vcls}">'
                        f'<div class="md3-card-label">Verdict</div>'
                        f'<div class="md3-card-value mono">{v_text}</div>'
                        f'</div>'
                        f'<div class="md3-card outlined" style="margin-top:0.5rem;">'
                        f'<div class="md3-card-label">Original Outcome</div>'
                        f'<div class="md3-card-value mono">{orig_o}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    b_chips  = chips_html(b_types) if b_types else "None"
                    fair_out = r.get("fair_outcome") or "N/A"
                    st.markdown(
                        f'<div class="md3-card filled-warning">'
                        f'<div class="md3-card-label">Bias Types</div>'
                        f'<div class="md3-card-value">{b_chips}</div>'
                        f'</div>'
                        f'<div class="md3-card filled-success" style="margin-top:0.5rem;">'
                        f'<div class="md3-card-label">Fair Outcome</div>'
                        f'<div class="md3-card-value">{fair_out}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if r.get("explanation"):
                    st.markdown(
                        f'<div class="md3-card tonal" style="margin-top:0.5rem;">'
                        f'<div class="md3-card-label">Explanation</div>'
                        f'<div class="md3-card-value" style="font-size:0.87rem;">{r["explanation"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if laws:
                    lw = chips_html(laws, "chip-primary")
                    st.markdown(
                        f'<div class="md3-card filled-primary" style="margin-top:0.5rem;">'
                        f'<div class="md3-card-label">Legal Frameworks</div>'
                        f'<div class="md3-card-value">{lw}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations", [])
                if recs:
                    st.markdown('<div class="vw-section-label" style="margin-top:0.8rem;">Next Steps</div>',
                                unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec-item"><div class="rec-num">{i}</div>'
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
        '<div style="font-family:var(--font-body);font-size:0.9rem;'
        'color:var(--md-on-surface-variant);margin-bottom:1.2rem;">'
        'Analyse two decisions side-by-side — verdict, confidence, bias types, and applicable laws.</div>',
        unsafe_allow_html=True,
    )

    cc1, cc2 = st.columns(2, gap="large")
    with cc1:
        st.markdown('<div style="font-family:var(--font-display);font-size:1rem;font-weight:600;color:var(--md-on-surface);margin-bottom:0.5rem;">Decision A</div>', unsafe_allow_html=True)
        cmp_text1 = st.text_area("Text A", height=140, label_visibility="collapsed",
                                  placeholder="Paste first decision…", key="cmp1")
        cmp_type1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div style="font-family:var(--font-display);font-size:1rem;font-weight:600;color:var(--md-on-surface);margin-bottom:0.5rem;">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=140, label_visibility="collapsed",
                                  placeholder="Paste second decision…", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type2")

    cmp_btn = st.button("⚡  Compare Both Decisions", key="compare_btn", disabled=not _api_key_ok())

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
                st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
                b1, b2   = r1.get("bias_found"), r2.get("bias_found")
                c1v, c2v = r1.get("confidence_score", 0), r2.get("confidence_score", 0)
                if b1 and b2:
                    winner = "A" if c1v >= c2v else "B"
                    banner = f"⚠️ Both decisions show bias — Decision {winner} has higher confidence ({int(max(c1v,c2v)*100)}%)"
                elif b1:  banner = "⚠️ Decision A shows bias · Decision B appears fair"
                elif b2:  banner = "⚠️ Decision B shows bias · Decision A appears fair"
                else:     banner = "✅ Neither decision shows clear discriminatory patterns"
                st.markdown(f'<div class="winner-banner">{banner}</div>', unsafe_allow_html=True)

                v1c, v2c = st.columns(2, gap="large")
                for col, r, lbl in [(v1c, r1, "A"), (v2c, r2, "B")]:
                    with col:
                        bias  = r.get("bias_found", False)
                        conf  = r.get("confidence_score", 0)
                        vcls  = "verdict-bias" if bias else "verdict-clean"
                        vico  = "⚠️" if bias else "✅"
                        vsub  = "Bias Detected" if bias else "No Bias Found"
                        st.markdown(
                            f'<div class="{vcls}"><div class="v-icon">{vico}</div>'
                            f'<div class="v-label">Decision {lbl}</div>'
                            f'<div class="v-sub">{vsub}</div></div>',
                            unsafe_allow_html=True,
                        )
                        st.plotly_chart(gauge_chart(conf, bias), use_container_width=True,
                                        config={"displayModeBar": False})
                        bt_ch  = chips_html(r.get("bias_types", []))
                        sv_bdg = severity_badge(conf, bias)
                        st.markdown(f'{bt_ch} {sv_bdg}', unsafe_allow_html=True)
                        r_laws = r.get("legal_frameworks", [])
                        if r_laws:
                            st.markdown(chips_html(r_laws, "chip-primary"), unsafe_allow_html=True)
                        fair_v = r.get("fair_outcome") or "N/A"
                        expl_v = r.get("explanation") or ""
                        st.markdown(
                            f'<div class="md3-card filled-success" style="margin-top:0.7rem;">'
                            f'<div class="md3-card-label">Fair Outcome</div>'
                            f'<div class="md3-card-value">{fair_v}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if expl_v:
                            st.markdown(
                                f'<div class="md3-card filled-warning">'
                                f'<div class="md3-card-label">What Went Wrong</div>'
                                f'<div class="md3-card-value" style="font-size:0.86rem;">{expl_v}</div>'
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
        '<div style="font-family:var(--font-body);font-size:0.9rem;'
        'color:var(--md-on-surface-variant);margin-bottom:1.2rem;">'
        'Paste decisions separated by <code style="background:var(--md-surface-variant);'
        'padding:2px 7px;border-radius:4px;font-family:var(--font-mono);">---</code> '
        'or upload a CSV with a <code style="background:var(--md-surface-variant);'
        'padding:2px 7px;border-radius:4px;font-family:var(--font-mono);">text</code> '
        'column. Limit: 10 per run.</div>',
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
                    st.markdown(
                        f'<div class="badge-ok">✓ {len(raw_blocks)} rows loaded from CSV</div>',
                        unsafe_allow_html=True,
                    )
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
        batch_btn = st.button("📦  Run Batch Analysis", key="batch_run", disabled=not _api_key_ok())

    if raw_blocks:
        st.markdown(
            f'<div style="font-family:var(--font-body);font-size:0.82rem;'
            f'color:var(--md-primary);font-weight:500;margin-top:0.3rem;">'
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
                    f'<div style="font-family:var(--font-body);font-size:0.82rem;'
                    f'color:var(--md-primary);font-weight:500;">'
                    f'Analysing {i+1} of {len(raw_blocks)}{eta_str}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(block, batch_type)
                results.append({"text": block, "report": rep, "error": err})
                progress.progress((i + 1) / len(raw_blocks))
            progress.empty(); status.empty()

            st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
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
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Batch Results (.csv)",
                        data=reports_to_csv(all_reps),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="batch_csv_dl",
                    )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="vw-section-label">Detailed Results</div>', unsafe_allow_html=True)
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
                        btyps  = rep.get("bias_types", [])
                        laws   = rep.get("legal_frameworks", [])
                        vcls   = "filled-error" if bias else "filled-success"
                        b_v    = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                        bt_ch  = chips_html(btyps) if btyps else "None"
                        fair   = rep.get("fair_outcome") or "N/A"
                        lw_blk = ""
                        if laws:
                            lw_blk = (f'<div class="md3-card filled-primary" style="margin-top:0.5rem;">'
                                      f'<div class="md3-card-label">Legal Frameworks</div>'
                                      f'<div class="md3-card-value">{chips_html(laws,"chip-primary")}</div>'
                                      f'</div>')
                        st.markdown(
                            f'<div class="md3-card {vcls}" style="margin-top:0.5rem;">'
                            f'<div class="md3-card-label">Verdict</div>'
                            f'<div class="md3-card-value mono">{b_v}</div>'
                            f'</div>'
                            f'<div class="md3-card filled-warning" style="margin-top:0.5rem;">'
                            f'<div class="md3-card-label">Bias Types</div>'
                            f'<div class="md3-card-value">{bt_ch}</div>'
                            f'</div>'
                            f'{lw_blk}'
                            f'<div class="md3-card filled-success" style="margin-top:0.5rem;">'
                            f'<div class="md3-card-label">Fair Outcome</div>'
                            f'<div class="md3-card-value">{fair}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

# ══════════════════════════════════════════════════════
# TAB 6 — SETTINGS
# ══════════════════════════════════════════════════════

with tab_settings:
    st.markdown(
        '<div style="font-family:var(--font-display);font-size:1.3rem;font-weight:700;'
        'color:var(--md-on-surface);margin-bottom:0.25rem;">Settings &amp; System Status</div>'
        '<div style="font-family:var(--font-body);font-size:0.875rem;'
        'color:var(--md-on-surface-variant);margin-bottom:1.5rem;">'
        'Verdict Watch V7 Enterprise — configuration and diagnostics.</div>',
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns(2, gap="large")
    with s1:
        st.markdown('<div class="vw-section-label">API &amp; Model Configuration</div>',
                    unsafe_allow_html=True)
        key_set  = _api_key_ok()
        k_vcls   = "filled-success" if key_set else "filled-error"
        k_stat   = "✓ Set (from .env)" if key_set else "✗ Not Set"
        pdf_vcls = "filled-success" if PDF_SUPPORT else "filled-warning"
        pdf_stat = "✓ Installed" if PDF_SUPPORT else "Not installed — pip install PyMuPDF"
        st.markdown(
            f'<div class="md3-card {k_vcls}"><div class="md3-card-label">Groq API Key</div>'
            f'<div class="md3-card-value mono">{k_stat}</div></div>'
            f'<div class="md3-card outlined"><div class="md3-card-label">Model</div>'
            f'<div class="md3-card-value mono">llama-3.3-70b-versatile</div></div>'
            f'<div class="md3-card outlined"><div class="md3-card-label">Temperature · Retries</div>'
            f'<div class="md3-card-value mono">0.1  ·  3× exponential backoff</div></div>'
            f'<div class="md3-card {pdf_vcls}"><div class="md3-card-label">PyMuPDF (PDF support)</div>'
            f'<div class="md3-card-value mono">{pdf_stat}</div></div>',
            unsafe_allow_html=True,
        )

    with s2:
        st.markdown('<div class="vw-section-label">Database &amp; Feedback Stats</div>',
                    unsafe_allow_html=True)
        all_r  = get_all_reports()
        fb     = services.get_feedback_stats()
        db_url = os.getenv("DATABASE_URL", "sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="md3-card"><div class="md3-card-label">Total Reports</div>'
            f'<div class="md3-card-value large">{len(all_r)}</div></div>'
            f'<div class="md3-card outlined"><div class="md3-card-label">Database URL</div>'
            f'<div class="md3-card-value mono" style="font-size:0.78rem;">{db_url}</div></div>'
            f'<div class="md3-card filled-primary"><div class="md3-card-label">User Feedback</div>'
            f'<div class="md3-card-value mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="md3-divider">', unsafe_allow_html=True)
    st.markdown('<div class="vw-section-label">V7 Feature Registry</div>', unsafe_allow_html=True)

    features = [
        ("Schema Migration Fix",    "text_hash OperationalError resolved",    True),
        ("Material Design 3",       "Google enterprise token system",          True),
        ("SVG Confidence Ring",     "Animated arc ring with MD3 colors",       True),
        ("Google Top App Bar",      "Sticky header with branding",             True),
        ("MD3 Card Elevation",      "Surface + shadow system",                 True),
        ("Quick Examples Fix",      "Session state key binding (V6)",          True),
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
    feat_html = '<div class="md3-card outlined" style="padding:0.5rem 1.5rem;">'
    for name, desc, enabled in features:
        icon = "✓" if enabled else "○"
        color = "var(--md-tertiary)" if enabled else "var(--md-on-surface-muted)"
        feat_html += (
            f'<div class="feature-row">'
            f'<span class="feature-name">'
            f'<span class="feature-check" style="color:{color};margin-right:8px;">{icon}</span>'
            f'{name}</span>'
            f'<span class="feature-desc">{desc}</span>'
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
        '<p>Verdict Watch V7 is an enterprise-grade AI system that analyses automated decisions — '
        'job rejections, loan denials, medical triage, university admissions — for hidden bias. '
        'A 3-step Groq + Llama 3.3 70B pipeline extracts criteria, detects discriminatory patterns, '
        'cites relevant laws, and generates the fair outcome you deserved.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    ab1, ab2 = st.columns([1.6, 1], gap="large")
    with ab1:
        st.markdown('<div class="vw-section-label">Bias Dimensions Detected</div>', unsafe_allow_html=True)
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
                f'<div class="md3-card outlined" style="margin-bottom:0.4rem;">'
                f'<div class="md3-card-label">{name}</div>'
                f'<div class="md3-card-value" style="font-size:0.875rem;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="vw-section-label">V7 Changelog</div>', unsafe_allow_html=True)
        changes = [
            ("🔧", "Schema Migration",  "text_hash fix — no more OperationalError"),
            ("🎨", "Material Design 3", "Full Google enterprise token system"),
            ("⭕", "SVG Risk Ring",     "Animated confidence arc"),
            ("📱", "Top App Bar",       "Google-style sticky header"),
            ("🃏", "MD3 Cards",         "Elevation + tonal surface system"),
            ("📄", "File Upload",       ".txt + .pdf support"),
            ("🎯", "Bias Phrases",      "Model-extracted proxy phrases"),
            ("⚖️", "Legal Cite",         "Laws per case"),
            ("🔁", "Dup Detection",     "SHA-256 hash skip"),
            ("👍", "Feedback",          "Per-report ratings"),
            ("📊", "Batch CSV",         "Bulk analysis up to 10"),
            ("📈", "Trend Chart",       "Daily bias rate"),
        ]
        ch_html = '<div class="md3-card outlined" style="padding:0.5rem 1.5rem;">'
        for icon, name, desc in changes:
            ch_html += (
                f'<div class="feature-row">'
                f'<span class="feature-name">{icon} {name}</span>'
                f'<span class="feature-desc">{desc}</span>'
                f'</div>'
            )
        ch_html += '</div>'
        st.markdown(ch_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="vw-section-label">Tech Stack</div>', unsafe_allow_html=True)
        tech = [
            ("⚡ Groq",          "LLM inference platform"),
            ("🦙 Llama 3.3 70B", "Language model"),
            ("🎈 Streamlit",     "Full-stack web UI"),
            ("🗄 SQLAlchemy",    "ORM + SQLite"),
            ("📊 Plotly",        "Interactive charts"),
            ("📄 PyMuPDF",       "PDF text extraction"),
            ("🎨 Material 3",    "Google design system"),
        ]
        t_html = '<div class="md3-card tonal" style="padding:0.5rem 1.5rem;">'
        for name, desc in tech:
            t_html += (
                f'<div class="feature-row">'
                f'<span class="feature-name">{name}</span>'
                f'<span class="feature-desc">{desc}</span>'
                f'</div>'
            )
        t_html += '</div>'
        st.markdown(t_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="md3-card filled-warning">'
            '<div class="md3-card-label">⚠ Legal Disclaimer</div>'
            '<div class="md3-card-value" style="font-size:0.86rem;">'
            'Not legal advice. Built for educational and awareness purposes. '
            'Consult a qualified legal professional for discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )

# FOOTER
st.markdown(
    '<div class="vw-footer">'
    'Verdict Watch V7 Enterprise  ·  Powered by Groq / Llama 3.3 70B  ·  '
    'Material Design 3  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)