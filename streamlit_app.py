"""
streamlit_app.py — Verdict Watch V13
Editorial Dark-Ink Edition — Complete UI/UX overhaul.

Fixes vs V11:
  ✦ Sparkline Plotly margin conflict fixed (margin not passed twice)
  ✦ Text visibility fixed across all cards/dark-mode
  ✦ Navigation restructured: Analyse · Dashboard · History · Batch · Test Suite · Settings · About
  ✦ Compare removed (merged into Analyse as side-by-side toggle)
  ✦ Test Suite tab: run ALL examples in one click, live results table
  ✦ 10 rich examples across all 5 decision types with varied bias patterns
  ✦ Uniform card system — single source of truth for all card variants
  ✦ All inline color references replaced with CSS vars
  ✦ Sidebar active state fixed, hover states consistent
  ✦ Progress bar height and style unified
  ✦ Empty states unified across all views
  ✦ Typography scale locked down — no rogue font-size overrides
"""

import streamlit as st
import services
import plotly.graph_objects as go
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
# THEME TOKENS  (light / dark)
# ══════════════════════════════════════════════════════

LIGHT = {
    "--bg":        "#0f1116",
    "--surf":      "#FFFFFF",
    "--surf2":     "#EEE9E2",
    "--surf3":     "#E4DFD8",
    "--border":    "#D8D3CB",
    "--t1":        "#0F0F1A",
    "--t2":        "#3D3D52",
    "--t3":        "#7A7A90",
    "--t-inv":     "#FFFFFF",
    "--ink":       "#0F0F1A",
    "--accent":    "#2B4EFF",
    "--acc-lt":    "#EBF0FF",
    "--red":       "#C42B2B",
    "--red-lt":    "#FFF0F0",
    "--green":     "#166534",
    "--grn-lt":    "#F0FDF4",
    "--amber":     "#92400E",
    "--amb-lt":    "#FFFBEB",
    "--sh":        "0 1px 4px rgba(0,0,0,.07)",
    "--sh2":       "0 6px 20px rgba(0,0,0,.09)",
}

DARK = {
    "--bg":        "#0f1116",
    "--surf":      "#14141E",
    "--surf2":     "#1B1B27",
    "--surf3":     "#22222F",
    "--border":    "#2C2C3E",
    "--t1":        "#EEEEF8",
    "--t2":        "#9090AA",
    "--t3":        "#55556A",
    "--t-inv":     "#0F0F1A",
    "--ink":       "#EEEEF8",
    "--accent":    "#6B8AFF",
    "--acc-lt":    "#151B3A",
    "--red":       "#FF7070",
    "--red-lt":    "#2A1212",
    "--green":     "#4ADE80",
    "--grn-lt":    "#0D2015",
    "--amber":     "#FBB040",
    "--amb-lt":    "#231600",
    "--sh":        "0 1px 4px rgba(0,0,0,.35)",
    "--sh2":       "0 6px 20px rgba(0,0,0,.5)",
}

def T() -> dict:
    return DARK  # Always dark

def tok(k: str) -> str:
    return DARK[k]

# ══════════════════════════════════════════════════════
# CSS  — single injection, CSS-var driven
# ══════════════════════════════════════════════════════

def inject_css():
    tv = T()
    vars_css = "\n".join(f"  {k}: {v};" for k, v in tv.items())

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
{vars_css}
  --r:      8px;
  --r-lg:   14px;
  --r-xl:   20px;
  --r-pill: 999px;
  --ff:     'Syne', system-ui, sans-serif;
  --ff-d:   'DM Serif Display', Georgia, serif;
  --ff-m:   'JetBrains Mono', monospace;
  --trans:  all 0.18s ease;
}}

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [class*="css"] {{
  font-family: var(--ff) !important;
  background: var(--bg) !important;
  color: var(--t1) !important;
}}

/* ── Sidebar ─────────────────────────────────── */
[data-testid="stSidebar"] {{
  background: var(--bg) !important;
  border-right: 1px solid rgba(255,255,255,.05) !important;
  min-width: 244px !important;
  max-width: 244px !important;
}}
[data-testid="stSidebar"] * {{
  color: rgba(255,255,255,.65) !important;
  font-family: var(--ff) !important;
}}

/* Sidebar nav buttons */
[data-testid="stSidebar"] .stButton > button {{
  background: transparent !important;
  color: rgba(255,255,255,.55) !important;
  border: none !important;
  border-radius: var(--r) !important;
  padding: 8px 10px !important;
  font-size: .8rem !important;
  font-weight: 500 !important;
  text-align: left !important;
  width: 100% !important;
  box-shadow: none !important;
  transform: none !important;
  transition: var(--trans) !important;
  letter-spacing: .01em !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  background: rgba(255,255,255,.08) !important;
  color: #fff !important;
  transform: none !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: rgba(107,138,255,.15) !important;
  color: #9db4ff !important;
  border-left: 2px solid #6B8AFF !important;
  border-right: none !important;
  border-top: none !important;
  border-bottom: none !important;
  font-weight: 700 !important;
}}

/* ── Hide Streamlit chrome ── */
footer, [data-testid="stStatusWidget"],
[data-testid="stDecoration"], #MainMenu {{
  display: none !important;
}}
.block-container {{ padding-top: 1.8rem !important; max-width: 1160px; }}
[data-testid="stTabs"] {{ display: none !important; }}

/* ── Main buttons ── */
.stButton > button {{
  font-family: var(--ff) !important;
  font-size: .875rem !important;
  font-weight: 700 !important;
  background: var(--accent) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: var(--r-pill) !important;
  padding: .55rem 1.65rem !important;
  box-shadow: 0 2px 12px rgba(107,138,255,.3) !important;
  transition: var(--trans) !important;
  letter-spacing: .025em !important;
}}
.stButton > button:hover {{
  opacity: .88 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 20px rgba(107,138,255,.5) !important;
}}
.stButton > button:active {{ transform: none !important; }}
.stButton > button:disabled {{ opacity: .3 !important; transform: none !important; box-shadow:none !important; }}
.stButton > button[kind="secondary"] {{
  background: transparent !important;
  color: var(--t1) !important;
  border: 1.5px solid var(--border) !important;
  box-shadow: none !important;
}}
.stButton > button[kind="secondary"]:hover {{
  background: var(--surf2) !important;
  transform: none !important;
}}


/* ── Sidebar button override (must come after main button rule) ── */
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {{
  background: transparent !important;
  color: rgba(255,255,255,.55) !important;
  box-shadow: none !important;
  border: none !important;
}}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {{
  background: rgba(255,255,255,.08) !important;
  color: #ffffff !important;
  box-shadow: none !important;
}}

/* ── Download button ── */
.stDownloadButton > button {{
  background: transparent !important;
  color: var(--accent) !important;
  border: 1.5px solid var(--accent) !important;
  border-radius: var(--r-pill) !important;
  font-family: var(--ff) !important;
  font-weight: 700 !important;
  font-size: .78rem !important;
  box-shadow: none !important;
  padding: .38rem 1.1rem !important;
  transform: none !important;
}}
.stDownloadButton > button:hover {{
  background: var(--acc-lt) !important;
  transform: none !important;
}}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {{
  font-family: var(--ff) !important;
  font-size: .88rem !important;
  background: var(--surf) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  color: var(--t1) !important;
  line-height: 1.7 !important;
  transition: border-color .2s !important;
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(107,138,255,.1) !important;
  outline: none !important;
}}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {{ color: var(--t3) !important; }}
.stTextArea label, .stTextInput label, .stSelectbox label, .stRadio label, .stDateInput label {{
  font-family: var(--ff) !important;
  font-size: .65rem !important;
  font-weight: 700 !important;
  color: var(--t3) !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
}}

/* ── Selectbox ── */
.stSelectbox > div > div {{
  background: var(--surf) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
}}

/* ── Radio ── */
.stRadio > div {{ gap: 5px !important; flex-wrap: wrap !important; }}
.stRadio > div > label {{
  background: var(--surf2) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r) !important;
  padding: 5px 13px !important;
  font-size: .78rem !important;
  font-weight: 600 !important;
  color: var(--t2) !important;
  cursor: pointer !important;
  transition: var(--trans) !important;
  text-transform: none !important;
  letter-spacing: normal !important;
}}
.stRadio > div > label:has(input:checked) {{
  background: var(--accent) !important;
  color: #ffffff !important;
  border-color: transparent !important;
}}

/* ── Metrics ── */
[data-testid="metric-container"] {{
  background: var(--surf) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  padding: .9rem 1.1rem .75rem !important;
  box-shadow: var(--sh) !important;
}}
[data-testid="metric-container"] label {{
  font-size: .62rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
  color: var(--t3) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
  font-family: var(--ff-m) !important;
  font-size: 1.55rem !important;
  color: var(--t1) !important;
}}

/* ── Progress ── */
.stProgress > div > div {{
  background: var(--accent) !important;
  border-radius: 2px !important;
  transition: width .3s ease !important;
}}
.stProgress > div {{
  background: var(--surf3) !important;
  border-radius: 2px !important;
  height: 3px !important;
}}

/* ── File uploader ── */
[data-testid="stFileUploader"] {{
  background: var(--surf) !important;
  border: 2px dashed var(--border) !important;
  border-radius: var(--r-lg) !important;
}}
[data-testid="stFileUploader"]:hover {{ border-color: var(--accent) !important; }}

/* ── Expander ── */
.streamlit-expanderHeader {{
  background: var(--surf) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
  font-family: var(--ff) !important;
  font-weight: 500 !important;
  font-size: .85rem !important;
}}
.streamlit-expanderContent {{
  background: var(--surf) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 var(--r) var(--r) !important;
}}

/* ══════════════════════════════════════════
   VERDICT WATCH COMPONENT LIBRARY
   ══════════════════════════════════════════ */

/* Brand */
.vw-mark  {{ font-family: var(--ff-d) !important; font-size: 1.2rem; color: #fff; line-height: 1; }}
.vw-ver   {{ font-size: .55rem; letter-spacing: .16em; text-transform: uppercase; color: rgba(255,255,255,.3); margin-top: 3px; }}
.api-dot  {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }}
.api-ok   {{ background: #4ade80; }}
.api-err  {{ background: #f87171; }}

/* Page headings */
.ph      {{ font-family: var(--ff-d); font-size: 1.85rem; font-weight: 400; color: var(--t1); letter-spacing: -.03em; line-height: 1.1; margin-bottom: 4px; margin-top: 0; }}
.ps      {{ font-size: .8rem; color: var(--t3); margin-bottom: 1.6rem; }}
.lbl     {{ font-size: .62rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--t3); margin-bottom: 7px; }}

/* Cards — UNIFORM system */
.card {{
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: .9rem 1.15rem;
  margin-bottom: 7px;
  box-shadow: var(--sh);
}}
.card-lbl {{ font-size: .6rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--t3); margin-bottom: 5px; }}
.card-val {{ font-size: .875rem; color: var(--t1); line-height: 1.55; }}
.card-val.mono {{ font-family: var(--ff-m); font-size: .82rem; color: var(--t1); }}
.card-val.lg   {{ font-size: 1.1rem; font-weight: 700; color: var(--t1); }}
.card-val.serif {{ font-family: var(--ff-d); font-size: 1.05rem; color: var(--t1); }}

/* Card variants */
.card-err  {{ background: var(--red-lt);  border-color: var(--red);   border-left: 3px solid var(--red);  }}
.card-ok   {{ background: var(--grn-lt);  border-color: var(--green); border-left: 3px solid var(--green);}}
.card-warn {{ background: var(--amb-lt);  border-color: var(--amber); border-left: 3px solid var(--amber);}}
.card-info {{ background: var(--acc-lt);  border-color: var(--accent);border-left: 3px solid var(--accent);}}
.card-muted {{ background: var(--surf2); }}

/* Card text colour overrides so text is always visible */
.card-err  .card-val, .card-err  .card-lbl {{ color: var(--red)   !important; }}
.card-ok   .card-val, .card-ok   .card-lbl {{ color: var(--green) !important; }}
.card-warn .card-val, .card-warn .card-lbl {{ color: var(--amber) !important; }}
.card-info .card-val, .card-info .card-lbl {{ color: var(--accent)!important; }}
/* Override: text in mono/serif should stay readable, not inherit colour */
.card-err  .card-val.mono, .card-err  .card-val.lg  {{ color: var(--red)   !important; }}
.card-ok   .card-val.mono, .card-ok   .card-val.lg  {{ color: var(--green) !important; }}
.card-warn .card-val.mono, .card-warn .card-val.lg  {{ color: var(--amber) !important; }}

/* Verdict banner */
.vb {{
  border-radius: var(--r-xl);
  padding: 1.6rem 1.75rem;
  text-align: center;
  border: 1px solid;
  margin-bottom: .9rem;
}}
.vb-bias  {{ background: var(--red-lt);  border-color: var(--red);   }}
.vb-clean {{ background: var(--grn-lt);  border-color: var(--green); }}
.vb-title {{ font-family: var(--ff-d); font-size: 1.5rem; letter-spacing: -.02em; margin-bottom: 4px; }}
.vb-bias  .vb-title {{ color: var(--red);   }}
.vb-clean .vb-title {{ color: var(--green); }}
.vb-sub   {{ font-size: .8rem; color: var(--t2); }}

/* Chips */
.chip {{
  display: inline-block;
  border-radius: var(--r-pill);
  padding: 2px 9px;
  font-size: .71rem;
  font-weight: 600;
  margin: 2px 3px 2px 0;
  border: 1px solid transparent;
}}
.cr {{ background: var(--red-lt);  color: var(--red);    border-color: var(--red);   }}
.cg {{ background: var(--grn-lt);  color: var(--green);  border-color: var(--green); }}
.cb {{ background: var(--acc-lt);  color: var(--accent); border-color: var(--accent);}}
.ca {{ background: var(--amb-lt);  color: var(--amber);  border-color: var(--amber); }}
.cn {{ background: var(--surf2);   color: var(--t2);     border-color: var(--border);}}

/* Severity badge */
.sev {{ display: inline-block; border-radius: var(--r-pill); padding: 2px 9px; font-size: .67rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }}
.sev-h {{ background: var(--red-lt);  color: var(--red);    }}
.sev-m {{ background: var(--amb-lt);  color: var(--amber);  }}
.sev-l {{ background: var(--grn-lt);  color: var(--green);  }}

/* Mode badge */
.mb-quick {{ background: var(--amb-lt); color: var(--amber); border: 1px solid var(--amber); border-radius: var(--r-pill); padding: 2px 9px; font-size: .67rem; font-weight: 700; }}
.mb-full  {{ background: var(--acc-lt); color: var(--accent);border: 1px solid var(--accent);border-radius: var(--r-pill); padding: 2px 9px; font-size: .67rem; font-weight: 700; }}

/* Highlight box */
.hl-box {{
  font-size: .875rem;
  line-height: 2;
  color: var(--t1);
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1rem 1.15rem;
}}
.hl-box mark {{
  background: rgba(196,43,43,.12);
  color: var(--red);
  border-radius: 3px;
  padding: 1px 4px;
  border-bottom: 1.5px solid var(--red);
}}

/* Recommendations */
.rec {{
  display: flex; gap: 10px; align-items: flex-start;
  background: var(--surf); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: .75rem 1rem; margin-bottom: 6px;
}}
.rec-n {{
  background: var(--ink); color: var(--t-inv);
  border-radius: 5px; min-width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--ff-m); font-size: .62rem; font-weight: 700;
  flex-shrink: 0; margin-top: 1px;
}}
.rec-t {{ font-size: .83rem; color: var(--t1); line-height: 1.55; }}

/* Appeal box */
.appeal-box {{
  background: var(--surf2); border: 1px solid var(--border);
  border-left: 3px solid var(--accent); border-radius: var(--r-lg);
  padding: 1.1rem 1.4rem; font-family: var(--ff-m); font-size: .74rem;
  line-height: 1.9; color: var(--t1); white-space: pre-wrap;
}}

/* Timing pills */
.t-row {{ display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }}
.t-pill {{
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--surf2); border: 1px solid var(--border);
  border-radius: var(--r-pill); padding: 2px 9px;
  font-family: var(--ff-m); font-size: .68rem; color: var(--t3);
}}
.t-pill strong {{ color: var(--t2); font-weight: 500; }}

/* Scan steps */
.ss {{ display: flex; gap: 4px; margin-bottom: 6px; }}
.ss-i {{ flex:1; background:var(--surf2); border-radius:var(--r); padding:.4rem .5rem; text-align:center; border:1px solid transparent; transition:var(--trans); }}
.ss-done   {{ background:var(--grn-lt); border-color:var(--green); }}
.ss-active {{ background:var(--acc-lt); border-color:var(--accent); }}
.ss-lbl {{ font-size:.62rem; font-weight:700; letter-spacing:.04em; color:var(--t3); }}
.ss-done   .ss-lbl {{ color:var(--green); }}
.ss-active .ss-lbl {{ color:var(--accent); }}
@keyframes scan-anim {{ 0%{{transform:translateX(-100%)}} 100%{{transform:translateX(400%)}} }}
.scan-bar {{ height:2px; background:var(--surf3); border-radius:2px; overflow:hidden; margin:3px 0 5px; }}
.scan-fill {{ height:100%; width:25%; background:var(--accent); border-radius:2px; animation:scan-anim 1s ease-in-out infinite; }}

/* Empty states */
.empty {{ text-align:center; padding:3.5rem 1rem; }}
.empty-ico {{ font-size:2.5rem; opacity:.2; margin-bottom:10px; }}
.empty-t {{ font-family:var(--ff-d); font-size:1.15rem; color:var(--t2); margin-bottom:4px; }}
.empty-s {{ font-size:.8rem; color:var(--t3); line-height:1.65; max-width:280px; margin:0 auto; }}

/* Key error */
.key-err {{
  background: var(--red-lt); border: 1px solid var(--red);
  border-left: 3px solid var(--red); border-radius: var(--r-lg);
  padding: .85rem 1.15rem; font-size: .85rem; color: var(--red); margin-bottom: 1rem;
}}

/* Dup warning */
.dup-warn {{
  display: flex; align-items: flex-start; gap: 10px;
  background: var(--amb-lt); border: 1px solid var(--amber);
  border-radius: var(--r-lg); padding: .85rem 1.1rem;
  font-size: .85rem; color: var(--amber); margin-bottom: 1rem;
}}

/* Divider */
.div {{ border: none; border-top: 1px solid var(--border); margin: 1.1rem 0; }}

/* Sidebar section label */
.sb-lbl {{
  font-size: .58rem !important; font-weight: 700 !important;
  letter-spacing: .14em !important; text-transform: uppercase !important;
  color: rgba(255,255,255,.28) !important; padding: 14px 0 4px !important;
  display: block !important;
}}

/* Sidebar how-it-works step */
.sb-step {{ display:flex; gap:8px; padding:3px 0; align-items:flex-start; }}
.sb-sn {{ background:rgba(255,255,255,.1); color:rgba(255,255,255,.55); border-radius:4px; width:16px; height:16px; display:flex; align-items:center; justify-content:center; font-family:var(--ff-m); font-size:.58rem; font-weight:700; flex-shrink:0; margin-top:1px; }}
.sb-st {{ font-size:.75rem; color:rgba(255,255,255,.45); line-height:1.45; }}

/* Char progress */
.char-row {{ display:flex; justify-content:space-between; font-size:.7rem; font-weight:600; margin-top:5px; }}
.char-track {{ height:2px; background:var(--surf3); border-radius:1px; margin-top:4px; }}
.char-fill  {{ height:100%; border-radius:1px; transition:width .3s, background .3s; }}

/* Preview box for batch */
.preview {{ background:var(--surf2); border:1px solid var(--border); border-radius:var(--r); padding:.55rem .85rem; font-family:var(--ff-m); font-size:.72rem; color:var(--t1); line-height:1.6; max-height:65px; overflow:hidden; white-space:pre-wrap; margin-bottom:5px; }}

/* Test suite */
.test-row {{ display:flex; align-items:center; gap:10px; padding:.65rem 1rem; background:var(--surf); border:1px solid var(--border); border-radius:var(--r-lg); margin-bottom:5px; transition:var(--trans); }}
.test-row:hover {{ background:var(--surf2); }}
.test-ico {{ font-size:1.1rem; flex-shrink:0; }}
.test-tag {{ font-size:.78rem; font-weight:700; color:var(--t1); flex:1; }}
.test-type {{ font-size:.68rem; color:var(--t3); }}
.test-badge {{ font-size:.68rem; font-weight:700; border-radius:var(--r-pill); padding:2px 8px; }}
.test-pending {{ background:var(--surf3); color:var(--t3); }}
.test-running {{ background:var(--acc-lt); color:var(--accent); }}
.test-pass    {{ background:var(--grn-lt); color:var(--green); }}
.test-fail    {{ background:var(--red-lt); color:var(--red);   }}

/* Info box */
.info-box {{
  background: var(--acc-lt); border: 1px solid var(--accent);
  border-radius: var(--r-lg); padding: .8rem 1.1rem;
  font-size: .83rem; color: var(--accent);
}}

/* Settings feature row */
.feat-row {{ display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid var(--surf3); font-size:.82rem; }}
.feat-row:last-child {{ border-bottom:none; }}
.feat-name {{ font-weight:600; color:var(--t1); }}
.feat-desc {{ font-size:.73rem; color:var(--t3); }}
.feat-ico  {{ color:var(--green); font-weight:700; margin-right:7px; }}

/* Winner bar (Compare) */
.winner-bar {{ background:var(--acc-lt); border:1px solid var(--accent); border-radius:var(--r-lg); padding:.8rem 1.2rem; text-align:center; font-size:.88rem; font-weight:600; color:var(--accent); margin-bottom:.9rem; }}

/* Diff badge */
.diff-b {{ display:inline-block; border-radius:var(--r-pill); padding:2px 8px; font-size:.7rem; font-weight:700; margin:2px; }}
.diff-a  {{ background:var(--acc-lt); color:var(--accent); }}
.diff-bb {{ background:var(--red-lt); color:var(--red);    }}
.diff-sh {{ background:var(--grn-lt); color:var(--green);  }}

/* Ring */
.ring-wrap {{ display:flex; align-items:center; justify-content:center; margin:5px 0; }}

/* Law row */
.law-row {{ display:flex; align-items:center; gap:8px; padding:5px 0; border-bottom:1px solid var(--surf3); font-size:.82rem; color:var(--t1); }}
.law-row:last-child {{ border-bottom:none; }}
.law-row span.ico {{ color:var(--accent); }}


/* ── Toggle ── */
.stToggle > label > div {{
  background: var(--surf3) !important;
}}
.stToggle > label > div[data-checked="true"] {{
  background: var(--accent) !important;
}}
.stToggle span {{ color: var(--t2) !important; font-size: .82rem !important; }}

/* Dataframe override */
[data-testid="stDataFrame"] {{ border-radius: var(--r-lg) !important; overflow: hidden !important; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════

EXAMPLES = [
    {
        "tag":  "Software Engineer Rejection",
        "type": "job",
        "expect_bias": False,
        "text": (
            "Thank you for applying to the Software Engineer position. After careful review "
            "we have decided not to move forward. We felt other candidates were a stronger fit "
            "for our team culture at this time."
        ),
    },
    {
        "tag":  "Bank Loan Denial (Geographic)",
        "type": "loan",
        "expect_bias": True,
        "text": (
            "Your loan application has been declined. Primary reasons: insufficient credit history, "
            "residential area risk score, employment sector classification. "
            "You may reapply after 6 months."
        ),
    },
    {
        "tag":  "Medical Triage (Age + Insurance)",
        "type": "medical",
        "expect_bias": True,
        "text": (
            "Based on your intake assessment you have been assigned Priority Level 3. "
            "Factors considered: age group (65+), reported pain level, primary language (non-English), "
            "insurance classification (Medicaid). High-priority slots reserved for Priority 1–2 patients."
        ),
    },
    {
        "tag":  "University Admission (Zip Code)",
        "type": "university",
        "expect_bias": True,
        "text": (
            "We regret to inform you that your application for admission has not been successful. "
            "Our admissions committee considered zip code region diversity metrics, legacy status, "
            "and extracurricular profile alignment when making this decision."
        ),
    },
    {
        "tag":  "Housing Rental Rejection",
        "type": "other",
        "expect_bias": True,
        "text": (
            "After reviewing your rental application we are unable to proceed at this time. "
            "Factors reviewed include your neighbourhood of origin, employment sector, "
            "and family size relative to unit capacity. We wish you the best in your search."
        ),
    },
    {
        "tag":  "Marketing Manager — Gender Bias",
        "type": "job",
        "expect_bias": True,
        "text": (
            "Thank you for interviewing for the Marketing Manager role. While your qualifications "
            "were impressive, we felt the demands of the role — including frequent travel and "
            "extended hours — may not align with your current family obligations. "
            "We have moved forward with another candidate."
        ),
    },
    {
        "tag":  "Small Business Loan (Name-Based)",
        "type": "loan",
        "expect_bias": True,
        "text": (
            "Your small business loan application has been reviewed and we regret to inform you "
            "of our decision to decline. Our risk model flagged your application based on "
            "business owner surname origin score, neighbourhood commercial density index, "
            "and owner's primary spoken language. We encourage you to address these factors "
            "before reapplying in 12 months."
        ),
    },
    {
        "tag":  "Security Clearance Denial",
        "type": "other",
        "expect_bias": False,
        "text": (
            "Your application for security clearance has been denied based on the following "
            "objective findings: undisclosed foreign financial accounts, two instances of "
            "late tax filings in the past five years, and an open civil judgment. "
            "These findings are directly relevant to trustworthiness assessments under "
            "national security guidelines."
        ),
    },
    {
        "tag":  "Graduate School Rejection (Race Proxy)",
        "type": "university",
        "expect_bias": True,
        "text": (
            "After a holistic review of your application, the admissions committee has decided "
            "not to offer you a place in our programme. Factors that influenced this decision "
            "include undergraduate institution tier, applicant name-based cultural fit score, "
            "and geographic region of residence. We received a highly competitive pool this cycle."
        ),
    },
    {
        "tag":  "Insurance Claim Denial (Socioeconomic)",
        "type": "other",
        "expect_bias": True,
        "text": (
            "Your insurance claim #CLM-2024-8821 has been denied. Our automated assessment "
            "system identified the following risk factors: claimant occupation category "
            "(manual/unskilled labour), residential postcode risk band (Band D), "
            "and claim history pattern typical of high-risk socioeconomic segments. "
            "If you wish to appeal, you must do so within 14 days."
        ),
    },
]

TYPE_LABELS = {
    "job":        "Job Application",
    "loan":       "Bank Loan",
    "medical":    "Medical / Triage",
    "university": "University Admission",
    "other":      "Other / General",
}

BIAS_KW = {
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|family obligation|housewife|mrs|mr)\b",
    "Age":           r"\b(age group|senior|junior|young|old|millennial|boomer|elderly|youth|65\+|under 30)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|name|surname|cultural fit score|language score)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district|postcode risk|locality)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|occupation|class|status|manual labour|unskilled|socioeconomic)\b",
    "Language":      r"\b(primary language|language|accent|english|bilingual|non-english|native speaker)\b",
    "Insurance":     r"\b(insurance|coverage|uninsured|medicaid|medicare|policy|insurance classification|insurance tier)\b",
}
BIAS_DIMS = ["Gender", "Age", "Racial", "Geographic", "Socioeconomic", "Language", "Insurance"]

CHIP_CYC = ["cr", "ca", "cb", "cg", "cn"]

VIEWS = [
    ("analyse",   "⚡", "Analyse"),
    ("dashboard", "◎", "Dashboard"),
    ("history",   "▤", "History"),
    ("batch",     "⊞", "Batch"),
    ("test",      "⊘", "Test Suite"),
    ("settings",  "⊛", "Settings"),
    ("about",     "◷", "About"),
]

PAL = ["#2B4EFF","#C42B2B","#166534","#92400E","#7C3AED","#0891B2","#DB2777"]

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════

_DEFS = {
    "view":          "analyse",
    "session_count": 0,
    "last_report":   None,
    "last_text":     "",
    "last_dtype":    "job",
    "appeal_letter": None,
    "decision_input":"",
    "dtype_sel":     "job",
    "scan_mode":     "full",
    "force_rerun":   False,
    "fb_comment":    "",
    "cmp_ra":        None,
    "cmp_rb":        None,
}
for k, v in _DEFS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def api_ok() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())

def all_reports() -> list:
    try:
        return services.get_all_reports()
    except Exception:
        return []

def _trunc(s, length: int) -> str:
    s_str = str(s)
    out = "".join([ch for i, ch in enumerate(s_str) if i < length])
    if len(s_str) > length:
        return out + "…"
    return out

def _as_dict(x) -> dict:
    if isinstance(x, dict):
        return x
    return {}

def chips(items: list, style: str = "auto") -> str:
    if not items:
        return '<span class="chip cn">None detected</span>'
    html = ""
    for i, item in enumerate(items):
        cls = CHIP_CYC[i % len(CHIP_CYC)] if style == "auto" else style
        html += f'<span class="chip {cls}">{item}</span>'
    return html

def highlight_text(text: str, phrases: list, bias_types: list) -> str:
    out = text
    all_pats = set(phrases or [])
    for bt in (bias_types or []):
        for key, pat in BIAS_KW.items():
            if key.lower() in bt.lower() or bt.lower() in key.lower():
                for m in re.findall(pat, text, flags=re.IGNORECASE):
                    all_pats.add(m)
    for p in sorted(all_pats, key=len, reverse=True):
        if p and len(p) > 2:
            out = re.sub(re.escape(p), lambda m: f"<mark>{m.group()}</mark>", out, flags=re.IGNORECASE)
    return out

def sev_badge(conf: float, bias: bool, sev: str = "low") -> str:
    if not bias:
        return '<span class="sev sev-l">Low Risk</span>'
    s = (sev or "low").lower()
    if s == "high" or conf >= .75:
        return '<span class="sev sev-h">High</span>'
    if s == "medium" or conf >= .45:
        return '<span class="sev sev-m">Medium</span>'
    return '<span class="sev sev-l">Low</span>'

def ring_svg(pct: int, bias: bool, size: int = 110) -> str:
    r  = size * .38
    cx = cy = size / 2
    sw = size * .09
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    gap  = circ - dash
    col  = tok("--red") if bias else (tok("--green") if pct < 40 else tok("--amber"))
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{tok("--surf3")}" stroke-width="{sw}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"'
        f' stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-linecap="round"'
        f' transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy - size*.04}" text-anchor="middle"'
        f' font-family="JetBrains Mono,monospace" font-size="{size*.18}" font-weight="600" fill="{col}">{pct}%</text>'
        f'<text x="{cx}" y="{cy + size*.12}" text-anchor="middle"'
        f' font-family="Syne,sans-serif" font-size="{size*.07}" font-weight="700"'
        f' fill="{tok("--t3")}" letter-spacing="0.08em">CONF</text>'
        f'</svg>'
    )

def timing_pills(timing: dict) -> str:
    if not timing:
        return ""
    labels = {"extract":"Extract","detect":"Detect","fair":"Fair","quick":"Scan","total":"Total"}
    parts  = [
        f'<span class="t-pill"><strong>{labels.get(k,k)}</strong> {v}ms</span>'
        for k, v in timing.items()
    ]
    return '<div class="t-row">' + "".join(parts) + "</div>"

def txt_report(report: dict, text: str, dtype: str) -> str:
    tm   = report.get("timing_ms", {})
    laws = report.get("legal_frameworks", [])
    recs = report.get("recommendations", [])
    lines = [
        "=" * 64,
        "       VERDICT WATCH V12 — BIAS ANALYSIS REPORT",
        "=" * 64,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id','N/A')}",
        f"Mode       : {(report.get('mode') or 'full').upper()}",
        f"Severity   : {(report.get('severity') or 'N/A').upper()}",
        "",
        "── ORIGINAL DECISION ──────────────────────────────────────",
        text or "(not recorded)",
        "",
        "── VERDICT ────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence : {int(report.get('confidence_score', 0) * 100)}%",
        "",
        "── BIAS TYPES ─────────────────────────────────────────────",
        ", ".join(report.get("bias_types", [])) or "None detected",
        "",
        "── CHARACTERISTIC AFFECTED ────────────────────────────────",
        report.get("affected_characteristic") or "N/A",
        "",
        "── ORIGINAL OUTCOME ───────────────────────────────────────",
        report.get("original_outcome") or "N/A",
        "",
        "── FAIR OUTCOME ───────────────────────────────────────────",
        report.get("fair_outcome") or "N/A",
        "",
        "── EXPLANATION ────────────────────────────────────────────",
        report.get("explanation") or "N/A",
        "",
        "── NEXT STEPS ─────────────────────────────────────────────",
        *[f"  {i+1}. {r}" for i, r in enumerate(recs)],
    ]
    if laws:
        lines += ["","── LEGAL FRAMEWORKS ───────────────────────────────────────"]
        lines += [f"  • {l}" for l in laws]
    if tm:
        lines += ["","── TIMING ─────────────────────────────────────────────────"]
        lines += [f"  {k}: {v}ms" for k, v in tm.items()]
    lines += ["","=" * 64,"  Verdict Watch V12  ·  Not legal advice","=" * 64]
    return "\n".join(lines)

def to_csv(reps: list) -> str:
    rows = [{
        "id":         r.get("id",""),
        "created_at": (r.get("created_at") or "")[:16].replace("T"," "),
        "mode":       r.get("mode","full"),
        "bias_found": r.get("bias_found",False),
        "severity":   r.get("severity",""),
        "confidence": int(r.get("confidence_score",0)*100),
        "bias_types": "; ".join(r.get("bias_types",[])),
        "affected":   r.get("affected_characteristic",""),
        "original":   r.get("original_outcome",""),
        "fair":       r.get("fair_outcome",""),
        "explanation":r.get("explanation",""),
        "legal":      "; ".join(r.get("legal_frameworks",[])),
        "next_steps": " | ".join(r.get("recommendations",[])),
        "total_ms":   r.get("timing_ms",{}).get("total",""),
    } for r in reps if isinstance(r, dict)]
    return pd.DataFrame(rows).to_csv(index=False)

def extract_file(f) -> str | None:
    name = f.name.lower()
    if name.endswith(".txt"):
        return f.read().decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        if not PDF_SUPPORT:
            st.warning("PDF support requires: pip install PyMuPDF")
            return None
        raw = f.read()
        doc = pymupdf.open(stream=raw, filetype="pdf")
        return "\n".join(p.get_text() for p in doc).strip()
    st.warning(f"Unsupported file type: {f.name}")
    return None

# ══════════════════════════════════════════════════════
# PLOTLY CHARTS — fixed margin conflict
# ══════════════════════════════════════════════════════

def _base() -> dict:
    dark = True
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Syne, system-ui, sans-serif",
                 "color": "#9090AA" if dark else "#3D3D52"},
    }

def chart_pie(b: int, c: int) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["Bias Detected","No Bias"],
        values=[max(b,1), max(c,1)],
        hole=.68,
        marker={"colors": [tok("--red"), tok("--green")],
                "line": {"color": tok("--bg"), "width": 3}},
        textfont={"family": "Syne,sans-serif", "size": 11},
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    total = b + c or 1
    fig.add_annotation(
        text=f"<b style='font-size:20px'>{total}</b><br>"
             f"<span style='font-size:9px;color:{tok('--t3')}'>TOTAL</span>",
        x=.5, y=.5, showarrow=False,
        font={"family": "JetBrains Mono,monospace", "size": 18, "color": tok("--t1")},
    )
    fig.update_layout(
        height=200, showlegend=True,
        legend={"font": {"family": "Syne,sans-serif", "size": 10},
                "bgcolor": "rgba(0,0,0,0)", "orientation": "h",
                "x": .5, "xanchor": "center", "y": -.04},
        margin={"l": 10, "r": 10, "t": 16, "b": 10},
        **_base(),
    )
    return fig

def chart_bar(items: list[str], max_n: int = 8) -> go.Figure:
    counts = Counter(items)
    if not counts:
        counts = Counter({"No data": 1})
    labels, values = zip(*counts.most_common(max_n))
    labels_list = list(labels)
    fig = go.Figure(go.Bar(
        x=list(values), y=labels_list, orientation="h",
        marker={"color": [PAL[i] for i in range(len(labels_list))], "line": {"width": 0}, "cornerradius": 4},
        text=list(values), textfont={"family": "JetBrains Mono,monospace", "size": 9, "color": tok("--t2")},
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(150, len(labels) * 38 + 40),
        xaxis={"showgrid": True, "gridcolor": tok("--surf3"), "zeroline": False,
               "tickfont": {"family": "JetBrains Mono,monospace", "size": 9}},
        yaxis={"tickfont": {"family": "Syne,sans-serif", "size": 9}},
        bargap=.4,
        margin=dict(l=10, r=30, t=10, b=10),
        **_base(),
    )
    return fig

def chart_sparkline(scores: list[float]) -> go.Figure:
    """Confidence sparkline — fixed: no duplicate margin keys."""
    if not scores:
        scores = [0]
    dark = True
    fill_col = "rgba(107,138,255,0.10)" if dark else "rgba(43,78,255,0.08)"
    fig = go.Figure(go.Scatter(
        y=scores, mode="lines",
        line={"color": tok("--accent"), "width": 2},
        fill="tozeroy",
        fillcolor=fill_col,
        hovertemplate="Score %{y}%<extra></extra>",
    ))
    # Single update_layout call — no conflict
    fig.update_layout(
        height=75,
        xaxis={"visible": False},
        yaxis={"range": [0, 105], "visible": False},
        margin={"l": 0, "r": 0, "t": 4, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Syne,sans-serif"},
    )
    return fig

def chart_trend(td: list) -> go.Figure | None:
    if not td:
        return None
    dates  = [d.get("date","")      for d in td if isinstance(d, dict)]
    rates  = [d.get("bias_rate",0) for d in td if isinstance(d, dict)]
    totals = [d.get("total",0)     for d in td if isinstance(d, dict)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=totals, name="Total",
        marker={"color": tok("--surf3"), "line": {"width": 0}, "cornerradius": 3},
        yaxis="y2", hovertemplate="%{x}: %{y} analyses<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=rates, name="Bias %", mode="lines+markers",
        line={"color": tok("--red"), "width": 2.5},
        marker={"color": tok("--red"), "size": 5, "line": {"color": tok("--bg"), "width": 1.5}},
        hovertemplate="%{x}: %{y}%<extra></extra>",
    ))
    fig.update_layout(
        height=210,
        yaxis={"range": [0,105], "tickfont": {"family": "JetBrains Mono,monospace", "size": 9},
               "gridcolor": tok("--surf3"), "zeroline": False},
        yaxis2={"overlaying": "y", "side": "right", "showgrid": False,
                "tickfont": {"family": "JetBrains Mono,monospace", "size": 9}},
        xaxis={"tickfont": {"family": "Syne,sans-serif", "size": 9}},
        legend={"font": {"family": "Syne,sans-serif", "size": 10},
                "bgcolor": "rgba(0,0,0,0)", "x": 0, "y": 1.1, "orientation": "h"},
        margin={"l": 10, "r": 40, "t": 20, "b": 10},
        **_base(),
    )
    return fig

def chart_radar(all_r: list) -> go.Figure:
    dim_counts = {d: 0 for d in BIAS_DIMS}
    for r in all_r:
        if isinstance(r, dict):
            for bt in _as_dict(r).get("bias_types", []):
                for dim in BIAS_DIMS:
                    if dim.lower() in bt.lower():
                        dim_counts[dim] = int(dim_counts.get(dim, 0)) + 1
    vals = [dim_counts[d] for d in BIAS_DIMS]
    dark = True
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=BIAS_DIMS + [BIAS_DIMS[0]],
        fill="toself",
        fillcolor=f"rgba(107,138,255,{'0.10' if dark else '0.07'})",
        line={"color": tok("--accent"), "width": 2},
        marker={"color": tok("--accent"), "size": 5},
    ))
    fig.update_layout(
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "radialaxis": {"visible": True, "gridcolor": tok("--surf3"),
                           "tickfont": {"family": "JetBrains Mono,monospace", "size": 8}},
            "angularaxis": {"gridcolor": tok("--surf3"),
                            "tickfont": {"family": "Syne,sans-serif", "size": 9}},
        },
        height=250, showlegend=False,
        margin={"l": 40, "r": 40, "t": 20, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Syne,sans-serif"},
    )
    return fig

def chart_gauge(val: float, bias: bool) -> go.Figure:
    col = tok("--red") if bias else tok("--green")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(val * 100),
        number={"suffix": "%", "font": {"family": "JetBrains Mono,monospace", "size": 22, "color": col}},
        gauge={
            "axis": {"range": [0,100], "tickwidth": 0,
                     "tickfont": {"color": tok("--t3"), "size": 8}},
            "bar": {"color": col, "thickness": 0.2},
            "bgcolor": tok("--surf2"), "borderwidth": 0,
            "steps": [
                {"range": [0,  33],  "color": "rgba(22,101,52,.07)"},
                {"range": [33, 66],  "color": "rgba(146,64,14,.07)"},
                {"range": [66, 100], "color": "rgba(196,43,43,.07)"},
            ],
        },
    ))
    fig.update_layout(height=160, margin={"l": 10, "r": 10, "t": 20, "b": 10}, **_base())
    return fig

# ══════════════════════════════════════════════════════
# PIPELINE RUNNER
# ══════════════════════════════════════════════════════

def _render_steps(ph, current: int, label: str):
    steps = [(1,"EXTRACT"), (2,"DETECT"), (3,"GENERATE")]
    parts: list[str] = []
    for num, lbl in steps:
        if   num < current:    cls, ico = "ss-done",   "✓"
        elif num == current:   cls, ico = "ss-active",  "⟳"
        else:                  cls, ico = "",           str(num)
        parts.append(f'<div class="ss-i {cls}"><div class="ss-lbl">{ico} {lbl}</div></div>')
    ph.markdown(
        f'<div class="ss">{"".join(parts)}</div>'
        f'<div class="scan-bar"><div class="scan-fill"></div></div>'
        f'<div style="font-size:.74rem;color:{tok("--accent")};font-weight:600;">⬤ {label}</div>',
        unsafe_allow_html=True,
    )

def run_analysis(text: str, dtype: str, mode: str = "full") -> tuple[dict | None, str | None]:
    ph = st.empty()
    def cb(step, label): _render_steps(ph, step, label)
    try:
        if mode == "quick":
            r = services.quick_scan(decision_text=text, decision_type=dtype)
        else:
            r = services.run_full_pipeline(decision_text=text, decision_type=dtype, progress_callback=cb)
        st.session_state["session_count"] += 1
        ph.empty()
        return r, None
    except ValueError as e:
        ph.empty(); return None, str(e)
    except Exception as e:
        ph.empty(); return None, f"Pipeline error: {e}"

# ══════════════════════════════════════════════════════
# RESULT RENDERER  (reused in Analyse + Test Suite)
# ══════════════════════════════════════════════════════

def render_result(report: dict, dt: str, dtype: str, compact: bool = False):
    """Render a full analysis result. compact=True for Test Suite inline."""
    bias  = report.get("bias_found", False)
    conf  = report.get("confidence_score", 0.0)
    pct   = int(conf * 100)
    btype = report.get("bias_types", [])
    aff   = report.get("affected_characteristic", "")
    orig  = report.get("original_outcome", "N/A")
    fair  = report.get("fair_outcome", "N/A")
    expl  = report.get("explanation", "")
    recs  = report.get("recommendations", [])
    laws  = report.get("legal_frameworks", [])
    evid  = report.get("bias_evidence", "")
    tm    = report.get("timing_ms", {})
    mode_ = report.get("mode", "full")

    # Banner
    vcls  = "vb-bias" if bias else "vb-clean"
    vico  = "⚠" if bias else "✓"
    vtxt  = "Bias Detected" if bias else "No Bias Found"
    vsub  = "This decision contains discriminatory patterns." if bias else "No strong discriminatory signals found."
    mbadge = f'<span class="mb-quick">Quick</span>' if mode_ == "quick" else f'<span class="mb-full">Full</span>'

    st.markdown(
        f'<div class="vb {vcls}">'
        f'<div style="font-size:1.8rem;line-height:1;margin-bottom:5px;">{vico}</div>'
        f'<div class="vb-title">{vtxt}</div>'
        f'<div class="vb-sub">{vsub}</div>'
        f'<div style="margin-top:8px;">{mbadge} {sev_badge(conf, bias, report.get("severity","low"))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Ring + bias types
    rc1, rc2 = st.columns([1, 2], gap="small")
    with rc1:
        aff_html = ""
        if aff:
            aff_html = (
                f'<div style="margin-top:9px;">'
                f'<div class="card-lbl">Affected</div>'
                f'<div style="font-size:.9rem;font-weight:700;color:{tok("--amber")};">{aff.title()}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="ring-wrap">{ring_svg(pct, bias)}</div>'
            f'{aff_html}</div>',
            unsafe_allow_html=True,
        )
    with rc2:
        st.markdown(
            f'<div class="card" style="height:100%;">'
            f'<div class="card-lbl">Bias Types</div>'
            f'<div style="line-height:2.2;">{chips(btype) if btype else chips([])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Outcomes
    ocls = "card-err" if bias else "card-muted"
    st.markdown(
        f'<div class="card {ocls}">'
        f'<div class="card-lbl">Original Decision</div>'
        f'<div class="card-val mono lg">{orig.upper()}</div>'
        f'</div>'
        f'<div class="card card-ok">'
        f'<div class="card-lbl">Should Have Been</div>'
        f'<div class="card-val serif">{fair}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if evid:
        st.markdown(
            f'<div class="card card-warn">'
            f'<div class="card-lbl">Bias Evidence</div>'
            f'<div class="card-val" style="font-size:.83rem;">{evid}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if tm:
        st.markdown(timing_pills(tm), unsafe_allow_html=True)

    if not compact:
        # Highlight
        if dt and (btype or report.get("bias_phrases")):
            st.markdown('<div class="lbl" style="margin-top:11px;">Highlighted Phrases</div>', unsafe_allow_html=True)
            hl = highlight_text(dt, report.get("bias_phrases",[]), btype)
            st.markdown(
                f'<div class="hl-box">{hl}</div>'
                f'<div style="font-size:.66rem;color:{tok("--t3")};margin-top:3px;">Highlighted = potential bias proxies</div>',
                unsafe_allow_html=True,
            )

        if expl:
            st.markdown('<div class="lbl" style="margin-top:11px;">Plain English</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card card-warn"><div class="card-val">{expl}</div></div>', unsafe_allow_html=True)

        if laws:
            st.markdown('<div class="lbl" style="margin-top:11px;">Legal Frameworks</div>', unsafe_allow_html=True)
            rows_html = "".join(
                f'<div class="law-row"><span class="ico">⚖</span>{l}</div>' for l in laws
            )
            st.markdown(f'<div class="card card-info">{rows_html}</div>', unsafe_allow_html=True)

        if recs:
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Recommended Next Steps</div>', unsafe_allow_html=True)
            for i, rec in enumerate(recs, 1):
                st.markdown(
                    f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>',
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════════════
# INJECT CSS + SIDEBAR
# ══════════════════════════════════════════════════════

inject_css()

with st.sidebar:
    ok = api_ok()
    dot_cls = "api-ok" if ok else "api-err"
    st.markdown(
        f'<div style="padding:18px 0 12px;">'
        f'<div class="vw-mark">Verdict Watch</div>'
        f'<div class="vw-ver">V13 · Bias Intelligence</div>'
        f'<div style="margin-top:9px;font-size:.68rem;color:rgba(255,255,255,.38);">'
        f'<span class="api-dot {dot_cls}"></span>'
        f'{"Groq API connected" if ok else "API key missing — see Settings"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.06);margin-bottom:4px;"></div>', unsafe_allow_html=True)

    st.markdown('<span class="sb-lbl">Navigation</span>', unsafe_allow_html=True)
    for vid, icon, label in VIEWS:
        is_active = st.session_state["view"] == vid
        if st.button(f"{icon}  {label}", key=f"nav_{vid}",
                     type="primary" if is_active else "secondary",
                     use_container_width=True):
            st.session_state["view"] = vid
            st.rerun()

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.06);margin:10px 0 4px;"></div>', unsafe_allow_html=True)

    st.markdown('<span class="sb-lbl">Try an Example</span>', unsafe_allow_html=True)
    # Show only 4 representative examples
    _SIDEBAR_EX = [1, 2, 5, 8]  # Bank Loan (geo), Medical (age+ins), Marketing (gender), Grad School (race)
    for idx in _SIDEBAR_EX:
        ex = EXAMPLES[idx]
        short = _trunc(ex.get("tag", ""), 28)
        if st.button(short, key=f"ex_{ex['tag']}", use_container_width=True):
            st.session_state["decision_input"] = ex["text"]
            st.session_state["dtype_sel"]      = ex["type"]
            st.session_state["view"]           = "analyse"
            st.rerun()

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.06);margin:10px 0 8px;"></div>', unsafe_allow_html=True)
    sc = st.session_state.get("session_count", 0)
    ar = len(all_reports())
    st.markdown(
        f'<div style="padding:4px 2px 8px;">'
        f'<span style="font-size:.68rem;color:rgba(255,255,255,.35);">Session </span>'
        f'<span style="font-size:.68rem;color:rgba(255,255,255,.65);font-weight:700;">{sc}</span>'
        f'<span style="font-size:.68rem;color:rgba(255,255,255,.2);margin:0 6px;">·</span>'
        f'<span style="font-size:.68rem;color:rgba(255,255,255,.35);">Total </span>'
        f'<span style="font-size:.68rem;color:rgba(255,255,255,.65);font-weight:700;">{ar}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════
# VIEW ROUTER
# ══════════════════════════════════════════════════════

view = st.session_state["view"]

# ─────────────────────────────────────────────────────
# ANALYSE
# ─────────────────────────────────────────────────────
if view == "analyse":
    st.markdown('<div class="ph">Analyse a Decision</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Paste any rejection, denial, or triage text to detect hidden bias.</div>', unsafe_allow_html=True)

    if not api_ok():
        st.markdown(
            '<div class="key-err">⚠ <strong>GROQ_API_KEY not found.</strong> '
            'Add it to your <code>.env</code> file and restart. '
            'Free key at <strong>console.groq.com</strong></div>',
            unsafe_allow_html=True,
        )

    # ── Input section — left 2/3, right 1/3 is breathing room ──
    input_col, _right_pad = st.columns([5, 2], gap="large")

    ctp2 = "other"  # default, overridden if compare mode active

    with input_col:
        mode_sel = st.radio(
            "input_mode", ["✏  Paste Text", "📄  Upload File"],
            horizontal=True, label_visibility="collapsed", key="input_mode",
        )

        st.markdown('<div class="lbl" style="margin-top:6px;">Decision Text</div>', unsafe_allow_html=True)

        if "Paste" in mode_sel:
            decision_text = st.text_area(
                "text", label_visibility="collapsed", height=190,
                key="decision_input",
                placeholder=(
                    "Paste any rejection letter, loan denial, triage outcome, "
                    "or university decision here…\n\n"
                    "Tip — load an example from the sidebar →"
                ),
            )
        else:
            uf = st.file_uploader("File", type=["txt","pdf"],
                                  label_visibility="collapsed", key="file_up")
            decision_text = ""
            if uf:
                ex = extract_file(uf)
                if ex:
                    decision_text = ex
                    st.markdown(
                        f'<div style="margin-bottom:7px;"><span class="chip cg">✓ {len(ex):,} chars from {uf.name}</span></div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview"):
                        st.text(_trunc(ex, 600))

        # Type selector + scan mode + char counter
        opts = ["job","loan","medical","university","other"]
        cur  = st.session_state.get("dtype_sel","job")
        idx  = opts.index(cur) if cur in opts else 0

        tc1, tc2 = st.columns([2, 1])
        with tc1:
            dtype = st.selectbox(
                "Type", opts, format_func=lambda x: TYPE_LABELS[x],
                index=idx, key="dtype_sel",
            )
        with tc2:
            n = len((decision_text or "").strip())
            if n > 150:   cc, cl = tok("--green"), "Ready"
            elif n > 50:  cc, cl = tok("--amber"), "Min length"
            else:         cc, cl = tok("--red"),   "Too short"
            w = min(100, int(n / 3))
            st.markdown(
                f'<div style="margin-top:22px;">'
                f'<div class="char-row" style="color:{cc};">'
                f'<span>{n:,} chars</span><span style="font-size:.65rem;">{cl}</span></div>'
                f'<div class="char-track"><div class="char-fill" style="width:{w}%;background:{cc};"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        scan_mode = st.radio(
            "Scan Mode",
            ["full","quick"],
            format_func=lambda x: "⚡ Full — 3-step deep analysis" if x == "full" else "◎ Quick — single call, faster",
            horizontal=True, key="scan_mode",
        )

        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

        ba1, ba2 = st.columns([2, 1])
        with ba1:
            run_btn = st.button("⚡ Run Analysis", key="run_btn", disabled=not api_ok())
        with ba2:
            compare_mode = st.toggle("Side-by-side compare", value=False, key="compare_toggle")

        if compare_mode:
            st.markdown('<div class="lbl" style="margin-top:8px;">Decision B (for comparison)</div>', unsafe_allow_html=True)
            dt_b = st.text_area("text_b", label_visibility="collapsed", height=120,
                                key="decision_input_b",
                                placeholder="Paste second decision to compare…")
            ctp2 = st.selectbox("Type B", opts, format_func=lambda x: TYPE_LABELS[x],
                                label_visibility="collapsed", key="dtype_b")

        # Show detected bias signals if text is long enough
        if decision_text and len(decision_text.strip()) > 30:
            detected = [d for d in BIAS_DIMS if re.search(BIAS_KW[d], decision_text, re.IGNORECASE)]
            if detected:
                st.markdown('<div class="lbl" style="margin-top:8px;">Signals detected in text</div>', unsafe_allow_html=True)
                st.markdown(
                    "".join(f'<span class="chip ca" style="margin-bottom:4px;">{d}</span>' for d in detected),
                    unsafe_allow_html=True,
                )

    with _right_pad:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card" style="margin-top:2px;border-left:3px solid var(--accent);">'
            f'<div class="card-lbl">How it works</div>'
            f'<div style="margin-top:6px;">' +
            "".join(
                f'<div style="display:flex;gap:8px;padding:5px 0;align-items:flex-start;">'
                f'<div style="background:var(--surf3);color:var(--t2);border-radius:4px;min-width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-family:var(--ff-m);font-size:.58rem;font-weight:700;flex-shrink:0;">{n}</div>'
                f'<div style="font-size:.77rem;color:var(--t2);line-height:1.5;">{t}</div></div>'
                for n, t in [
                    ("1","Paste or upload your decision text"),
                    ("2","AI extracts the criteria used"),
                    ("3","Scans for bias across 7 dimensions"),
                    ("4","Generates the fair outcome + laws"),
                    ("5","Download report or draft appeal"),
                ]
            ) +
            f'</div></div>'
            f'<div class="card card-info" style="margin-top:8px;">'
            f'<div class="card-lbl">Bias Dimensions Scanned</div>'
            f'<div style="margin-top:6px;">' +
            "".join(f'<span class="chip cn" style="margin-bottom:3px;">{d}</span>' for d in BIAS_DIMS) +
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── Run logic (full width below input) ──
    if run_btn:
        dt = (decision_text or "").strip()
        if not dt:
            st.warning("⚠ Paste or upload a decision first.")
        else:
            th     = services.hash_text(dt)
            cached = services.find_duplicate(th)

            if cached and not st.session_state.get("force_rerun"):
                st.markdown(
                    '<div class="dup-warn">⚠ <div><strong>Identical text — showing cached result.</strong><br>'
                    'Click Re-run for a fresh analysis.</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("🔄 Re-run", key="force_btn"):
                    st.session_state["force_rerun"] = True
                    st.rerun()
                report, err = cached, None
            else:
                st.session_state.pop("force_rerun", None)
                with st.spinner(""):
                    report, err = run_analysis(dt, dtype, mode=scan_mode)

            if err:
                st.error(f"❌ {err}")
            elif report:
                st.session_state["last_report"] = report
                st.session_state["last_text"]   = dt
                st.session_state["last_dtype"]  = dtype
                st.session_state["appeal_letter"] = None

            # Compare side B
            if compare_mode and not err:
                dt2 = (st.session_state.get("decision_input_b") or "").strip()
                if dt2:
                    with st.spinner("Analysing Decision B…"):
                        rb, eb = run_analysis(dt2, ctp2, mode=scan_mode)
                    if eb:
                        st.error(f"Decision B error: {eb}")
                    else:
                        st.session_state["cmp_ra"] = report
                        st.session_state["cmp_rb"] = rb

    report = st.session_state.get("last_report")
    dt     = st.session_state.get("last_text", "")
    dtype_ = st.session_state.get("last_dtype", "other")

    # ── Results rendered full-width below the form ──
    if report or (compare_mode and st.session_state.get("cmp_ra")):
        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

    # Compare view
    if compare_mode and st.session_state.get("cmp_ra") and st.session_state.get("cmp_rb"):
        ra, rb = st.session_state["cmp_ra"], st.session_state["cmp_rb"]
        ba, bb = ra.get("bias_found"), rb.get("bias_found")
        ca, cb = ra.get("confidence_score",0), rb.get("confidence_score",0)

        if ba and bb:
            w   = "A" if ca >= cb else "B"
            msg = f"Both show bias — Decision {w} has higher confidence ({int(max(ca,cb)*100)}%)"
        elif ba: msg = "Decision A shows bias · Decision B appears fair"
        elif bb: msg = "Decision B shows bias · Decision A appears fair"
        else:    msg = "Neither decision contains discriminatory patterns"
        st.markdown(f'<div class="winner-bar">{msg}</div>', unsafe_allow_html=True)

        set_a = set(ra.get("bias_types",[])); set_b = set(rb.get("bias_types",[]))
        only_a = set_a - set_b; only_b = set_b - set_a; shared = set_a & set_b
        if set_a or set_b:
            diff = '<div class="lbl">Bias Type Diff</div><div style="margin-bottom:10px;">'
            for t in sorted(shared): diff += f'<span class="diff-b diff-sh">Both: {t}</span>'
            for t in sorted(only_a): diff += f'<span class="diff-b diff-a">A: {t}</span>'
            for t in sorted(only_b): diff += f'<span class="diff-b diff-bb">B: {t}</span>'
            diff += "</div>"
            st.markdown(diff, unsafe_allow_html=True)

        v1, v2 = st.columns(2, gap="small")
        for col, r, lbl in [(v1, ra, "A"), (v2, rb, "B")]:
            with col:
                b_  = r.get("bias_found", False)
                vcls_ = "vb-bias" if b_ else "vb-clean"
                vt_ = "⚠ Bias" if b_ else "✓ Clean"
                st.markdown(
                    f'<div class="vb {vcls_}" style="padding:1rem;">'
                    f'<div class="vb-title" style="font-size:1.1rem;">Decision {lbl}</div>'
                    f'<div class="vb-sub" style="font-size:.78rem;">{vt_}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.plotly_chart(chart_gauge(r.get("confidence_score",0), b_),
                                use_container_width=True, config={"displayModeBar":False})
                st.markdown(chips(r.get("bias_types",[])), unsafe_allow_html=True)
                st.markdown(f'<div style="margin-top:4px;">{sev_badge(r.get("confidence_score",0), b_, r.get("severity","low"))}</div>', unsafe_allow_html=True)
                if r.get("fair_outcome"):
                    st.markdown(
                        f'<div class="card card-ok" style="margin-top:7px;">'
                        f'<div class="card-lbl">Fair Outcome</div>'
                        f'<div class="card-val serif">{r["fair_outcome"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        st.stop()

    if not report:
        st.markdown(
            '<div class="empty">'
            '<div class="empty-ico">⚖</div>'
            '<div class="empty-t">No analysis yet</div>'
            '<div class="empty-s">Paste a decision above and click Run Analysis.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        render_result(report, dt, dtype_)
        bias_ = report.get("bias_found", False)

        # Feedback
        st.markdown('<hr class="div">', unsafe_allow_html=True)
        st.markdown('<div class="lbl">Was this analysis helpful?</div>', unsafe_allow_html=True)
        fb_comment = st.text_input("Comment", key="fb_comment",
                                   label_visibility="collapsed",
                                   placeholder="Optional: notes on this analysis…")
        fb1, fb2, _ = st.columns([1, 1, 3])
        with fb1:
            if st.button("👍 Helpful", key="fb_y"):
                services.save_feedback(report.get("id",""), 1, fb_comment)
                st.success("Thanks!")
        with fb2:
            if st.button("👎 Not helpful", key="fb_n"):
                services.save_feedback(report.get("id",""), 0, fb_comment)
                st.info("Noted.")

        # Appeal
        if bias_:
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Formal Appeal Letter</div>', unsafe_allow_html=True)
            if st.button("✉ Generate Appeal Letter", key="appeal_btn"):
                with st.spinner("Drafting letter…"):
                    try:
                        letter = services.generate_appeal_letter(report, dt, dtype_)
                        st.session_state["appeal_letter"] = letter
                    except Exception as e:
                        st.error(f"❌ {e}")
            if st.session_state.get("appeal_letter"):
                letter = st.session_state["appeal_letter"]
                st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                st.download_button(
                    "↓ Download Letter", data=letter,
                    file_name=f"appeal_{(report.get('id') or 'x')[:8]}.txt",
                    mime="text/plain", key="dl_letter",
                )

        # Downloads
        st.markdown("<br>", unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "↓ Full Report (.txt)",
                data=txt_report(report, dt, dtype_),
                file_name=f"verdict_v12_{(report.get('id') or 'r')[:8]}.txt",
                mime="text/plain", key="dl_rpt",
            )
        with dl2:
            st.download_button(
                "↓ CSV",
                data=to_csv([report]),
                file_name=f"verdict_v12_{(report.get('id') or 'r')[:8]}.csv",
                mime="text/csv", key="dl_csv_single",
            )

# ─────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────
elif view == "dashboard":
    st.markdown('<div class="ph">Analytics Dashboard</div>', unsafe_allow_html=True)
    hist = all_reports()

    if not hist:
        st.markdown(
            '<div class="empty"><div class="empty-ico">◎</div>'
            '<div class="empty-t">Nothing to show yet</div>'
            '<div class="empty-s">Run your first analysis to populate the dashboard.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        b_reps  = [r for r in hist if r.get("bias_found")]
        c_reps  = [r for r in hist if not r.get("bias_found")]
        all_bt  = [bt for r in hist for bt in r.get("bias_types", [])]
        scores  = [r.get("confidence_score", 0) for r in hist]
        b_rate  = round(len(b_reps) / len(hist) * 100) if hist else 0
        avg_c   = round(sum(scores) / len(scores) * 100) if scores else 0
        top_b   = Counter(all_bt).most_common(1)[0][0] if all_bt else "—"
        fb      = services.get_feedback_stats()
        sev_map = {"high": 3, "medium": 2, "low": 1}
        sev_vals  = [sev_map.get((r.get("severity") or "low").lower(), 1) for r in hist]
        avg_sev_n = sum(sev_vals) / len(sev_vals) if sev_vals else 1
        avg_sev   = "High" if avg_sev_n >= 2.5 else ("Medium" if avg_sev_n >= 1.5 else "Low")

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Total",         len(hist))
        k2.metric("Bias Rate",     f"{b_rate}%")
        k3.metric("Avg Confidence",f"{avg_c}%")
        k4.metric("Top Bias",      top_b)
        k5.metric("Avg Severity",  avg_sev)
        k6.metric("Helpful %",     f"{fb['helpful_pct']}%" if fb["total"] else "—")

        # Sparkline — fixed no margin conflict
        spark_scores = services.get_confidence_trend(30)
        if spark_scores:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="lbl">Confidence Trend (last 30 analyses)</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_sparkline(spark_scores), use_container_width=True,
                            config={"displayModeBar": False})

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="lbl">Verdict Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_pie(len(b_reps), len(c_reps)), use_container_width=True,
                            config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="lbl">Bias Type Frequency</div>', unsafe_allow_html=True)
            if all_bt:
                st.plotly_chart(chart_bar(all_bt), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.markdown('<div class="empty"><div class="empty-s">No bias types recorded yet.</div></div>', unsafe_allow_html=True)

        td = services.get_trend_data()
        if td:
            st.markdown('<div class="lbl" style="margin-top:.5rem;">Daily Bias Rate Trend</div>', unsafe_allow_html=True)
            tf = chart_trend(td)
            if tf:
                st.plotly_chart(tf, use_container_width=True, config={"displayModeBar": False})

        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="lbl">Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_radar(hist), use_container_width=True,
                            config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="lbl">Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [str(r.get("affected_characteristic")) for r in hist if r.get("affected_characteristic")]
            if chars:
                st.plotly_chart(chart_bar(chars), use_container_width=True,
                                config={"displayModeBar": False})
            else:
                st.markdown('<div class="empty"><div class="empty-s">No characteristic data yet.</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        dl1, _ = st.columns([1,4])
        with dl1:
            st.download_button("↓ Export CSV", data=to_csv(hist),
                file_name=f"verdict_dash_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_dl")

        if fb.get("recent_comments"):
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Recent Feedback Comments</div>', unsafe_allow_html=True)
            for c in fb["recent_comments"]:
                st.markdown(
                    f'<div class="card card-muted" style="margin-bottom:5px;">'
                    f'<div class="card-val" style="font-size:.8rem;">{c}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

# ─────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────
elif view == "history":
    st.markdown('<div class="ph">Analysis History</div>', unsafe_allow_html=True)
    hist = all_reports()

    if not hist:
        st.markdown(
            '<div class="empty"><div class="empty-ico">▤</div>'
            '<div class="empty-t">No history yet</div>'
            '<div class="empty-s">All past analyses appear here.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        f1, f2, f3 = st.columns([3,1,1])
        with f1: q  = st.text_input("Search",   placeholder="Search bias type, outcome…", key="h_q")
        with f2: fv = st.selectbox("Verdict",   ["All","Bias","No Bias"],    key="h_v")
        with f3: sv = st.selectbox("Sort",      ["Newest","Oldest","High Conf","Low Conf"], key="h_s")

        d1c, d2c, _ = st.columns([1,1,2])
        with d1c: df_in = st.date_input("From", value=None, key="h_df")
        with d2c: dt_in = st.date_input("To",   value=None, key="h_dt")

        filt = list(hist)
        if fv == "Bias":      filt = [r for r in filt if r.get("bias_found")]
        elif fv == "No Bias": filt = [r for r in filt if not r.get("bias_found")]
        if q:
            ql = q.lower()
            filt = [r for r in filt
                    if ql in (r.get("affected_characteristic") or "").lower()
                    or any(ql in bt.lower() for bt in r.get("bias_types",[]))
                    or ql in (r.get("original_outcome") or "").lower()
                    or ql in (r.get("explanation") or "").lower()]
        if df_in: filt = [r for r in filt if (r.get("created_at") or "")[:10] >= str(df_in)]
        if dt_in: filt = [r for r in filt if (r.get("created_at") or "")[:10] <= str(dt_in)]

        if sv == "Newest":      filt.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sv == "Oldest":    filt.sort(key=lambda r: r.get("created_at") or "")
        elif sv == "High Conf": filt.sort(key=lambda r: r.get("confidence_score",0), reverse=True)
        else:                   filt.sort(key=lambda r: r.get("confidence_score",0))

        hdr1, hdr2 = st.columns([3,1])
        with hdr1:
            st.markdown(
                f'<div style="font-size:.73rem;color:{tok("--t3")};margin-bottom:9px;">'
                f'Showing {len(filt)} of {len(hist)} reports</div>',
                unsafe_allow_html=True,
            )
        with hdr2:
            st.download_button("↓ CSV", data=to_csv(filt),
                file_name=f"verdict_hist_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="hist_dl")

        for r in filt:
            bias    = r.get("bias_found", False)
            conf    = int(r.get("confidence_score",0)*100)
            aff     = r.get("affected_characteristic") or "—"
            created = (r.get("created_at") or "")[:16].replace("T"," ")
            ico     = "⚠" if bias else "✓"
            mode_lbl = "Quick" if r.get("mode") == "quick" else "Full"
            sev_lbl  = (r.get("severity") or "low").upper()

            with st.expander(f'{ico} {"Bias" if bias else "No Bias"}  ·  {conf}%  ·  {aff}  ·  {created}  [{mode_lbl}]'):
                ec1, ec2 = st.columns(2, gap="large")
                with ec1:
                    vcls = "card-err" if bias else "card-ok"
                    vt   = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                    st.markdown(
                        f'<div class="card {vcls}">'
                        f'<div class="card-lbl">Verdict</div>'
                        f'<div class="card-val mono">{vt}</div>'
                        f'</div>'
                        f'<div class="card card-muted" style="margin-top:6px;">'
                        f'<div class="card-lbl">Original Outcome</div>'
                        f'<div class="card-val mono">{(r.get("original_outcome") or "N/A").upper()}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    st.markdown(
                        f'<div class="card card-warn">'
                        f'<div class="card-lbl">Bias Types</div>'
                        f'<div class="card-val">{chips(r.get("bias_types",[]))}</div>'
                        f'</div>'
                        f'<div class="card card-ok" style="margin-top:6px;">'
                        f'<div class="card-lbl">Fair Outcome</div>'
                        f'<div class="card-val serif">{r.get("fair_outcome") or "N/A"}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="card card-muted" style="margin-top:6px;">'
                        f'<div class="card-lbl">Explanation</div>'
                        f'<div class="card-val" style="font-size:.83rem;">{r["explanation"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                laws = r.get("legal_frameworks",[])
                if laws:
                    rows_html = "".join(f'<div class="law-row"><span class="ico">⚖</span>{l}</div>' for l in laws)
                    st.markdown(
                        f'<div class="card card-info" style="margin-top:6px;">'
                        f'<div class="card-lbl">Legal Frameworks</div>'
                        f'{rows_html}</div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations",[])
                if recs:
                    st.markdown('<div class="lbl" style="margin-top:9px;">Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs,1):
                        st.markdown(
                            f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )
                tm = r.get("timing_ms",{})
                if tm:
                    st.markdown(timing_pills(tm), unsafe_allow_html=True)
                st.caption(f"ID: {r.get('id','N/A')}  ·  Severity: {sev_lbl}")
                st.download_button(
                    "↓ Report (.txt)",
                    data=txt_report(r, "", "other"),
                    file_name=f"verdict_{(r.get('id') or 'x')[:8]}.txt",
                    mime="text/plain", key=f"dl_{r.get('id','x')}",
                )

# ─────────────────────────────────────────────────────
# BATCH
# ─────────────────────────────────────────────────────
elif view == "batch":
    st.markdown('<div class="ph">Batch Processing</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ps">Analyse up to 10 decisions at once. '
        f'Separate with <code style="background:{tok("--surf2")};padding:1px 6px;border-radius:4px;font-family:var(--ff-m)">---</code> '
        f'or upload a CSV with a <code style="background:{tok("--surf2")};padding:1px 6px;border-radius:4px;font-family:var(--ff-m)">text</code> column.</div>',
        unsafe_allow_html=True,
    )
    if not api_ok():
        st.markdown('<div class="key-err">⚠ API key missing — see Settings.</div>', unsafe_allow_html=True)

    bmode = st.radio("Batch input", ["✏  Paste Text","📊  Upload CSV"],
                     horizontal=True, label_visibility="collapsed", key="bm")
    if "Paste" in bmode:
        bt = st.text_area("Batch text", height=200, label_visibility="collapsed", key="b_in",
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
                    st.markdown(f'<span class="chip cg">✓ {len(blocks)} rows loaded</span>', unsafe_allow_html=True)
                else:
                    st.error("CSV must have a 'text' column.")
            except Exception as e:
                st.error(f"❌ {e}")

    bc1, bc2, bc3 = st.columns([2,1,1])
    with bc1:
        btype = st.selectbox("Decision type (all)", ["job","loan","medical","university","other"],
                             format_func=lambda x: TYPE_LABELS[x],
                             label_visibility="collapsed", key="b_type")
    with bc2:
        scan_b = st.radio("Mode",["full","quick"], horizontal=True,
                          format_func=lambda x: "Full" if x == "full" else "Quick", key="b_scan")
    with bc3:
        brun = st.button("⊞ Run Batch", key="b_run", disabled=not api_ok())

    if blocks:
        st.markdown(
            f'<span class="chip cb">● {len(blocks)} decision{"s" if len(blocks)!=1 else ""} queued</span>',
            unsafe_allow_html=True,
        )

    if brun:
        if not blocks:
            st.warning("⚠ No decisions found.")
        elif len(blocks) > 10:
            st.warning("⚠ Batch limit is 10 decisions.")
        else:
            prog   = st.progress(0)
            status = st.empty()
            results= []
            t0     = time.time()

            for i, blk in enumerate(blocks):
                elapsed = time.time() - t0
                eta     = (elapsed / (i+1)) * (len(blocks) - i - 1) if i > 0 else 0
                eta_str = f" · ETA ~{int(eta)}s" if eta > 1 else ""
                status.markdown(
                    f'<div style="font-size:.78rem;color:{tok("--accent")};font-weight:600;">'
                    f'Analysing {i+1}/{len(blocks)}{eta_str}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(blk, btype, mode=scan_b)
                results.append({"text": blk, "report": rep, "error": err})
                prog.progress((i+1) / len(blocks))

            prog.empty(); status.empty()
            st.markdown('<hr class="div">', unsafe_allow_html=True)

            c_map = {"b_c": 0, "c_c": 0, "e_c": 0}
            for r in results:
                rep_r = r.get("report")
                if r.get("error"):
                    c_map["e_c"] = int(c_map["e_c"]) + 1
                elif isinstance(rep_r, dict):
                    rep_dict = _as_dict(rep_r)
                    if rep_dict.get("bias_found"):
                        c_map["b_c"] = int(c_map["b_c"]) + 1
                    else:
                        c_map["c_c"] = int(c_map["c_c"]) + 1

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total",         len(results))
            m2.metric("Bias Detected", c_map["b_c"])
            m3.metric("No Bias",       c_map["c_c"])
            m4.metric("Errors",        c_map["e_c"])

            rows = []
            for i, res in enumerate(results, 1):
                rep = res.get("report")
                err = res.get("error", "")
                if err and isinstance(err, str):
                    rows.append({"#":i,"Verdict":"ERROR","Conf":"—","Bias Types":"".join(list(err)[:50]),"Severity":"—","Affected":"—"})
                elif isinstance(rep, dict):
                    rows.append({
                        "#":          i,
                        "Verdict":    "⚠ Bias" if rep.get("bias_found") else "✓ Clean",
                        "Conf":       f"{int(rep.get('confidence_score',0)*100)}%",
                        "Bias Types": ", ".join(rep.get("bias_types",[])) or "None",
                        "Severity":   (rep.get("severity") or "—").title(),
                        "Affected":   rep.get("affected_characteristic") or "—",
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_r: list[dict] = []
            for r in results:
                th_rep = r.get("report")
                if isinstance(th_rep, dict):
                    all_r.append(th_rep)
                    
            if all_r:
                dl1, _ = st.columns([1,3])
                with dl1:
                    st.download_button("↓ Download CSV",
                        data=to_csv(all_r),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="b_dl")

            st.markdown('<div class="lbl" style="margin-top:1rem;">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep, err = res["report"], res["error"]
                lbl = f"Decision {i}"
                if err: lbl += " — Error"
                elif rep:
                    vs    = "⚠ Bias" if rep.get("bias_found") else "✓ Clean"
                    conf_ = int(rep.get("confidence_score",0)*100)
                    lbl  += f" — {vs} ({conf_}%)"
                with st.expander(lbl, expanded=False):
                    preview = res["text"][:250] + ("…" if len(res["text"]) > 250 else "")
                    st.markdown(f'<div class="preview">{preview}</div>', unsafe_allow_html=True)
                    if err:
                        st.error(err)
                    elif rep:
                        b_ = rep.get("bias_found", False)
                        st.markdown(
                            f'<div class="card {"card-err" if b_ else "card-ok"}">'
                            f'<div class="card-lbl">Verdict</div>'
                            f'<div class="card-val mono">{"⚠ Bias Detected" if b_ else "✓ No Bias Found"}</div>'
                            f'</div>'
                            f'<div class="card card-warn" style="margin-top:6px;">'
                            f'<div class="card-lbl">Bias Types</div>'
                            f'<div>{chips(rep.get("bias_types",[]))}</div>'
                            f'</div>'
                            f'<div class="card card-ok" style="margin-top:6px;">'
                            f'<div class="card-lbl">Fair Outcome</div>'
                            f'<div class="card-val serif">{rep.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

# ─────────────────────────────────────────────────────
# TEST SUITE  ← NEW
# ─────────────────────────────────────────────────────
elif view == "test":
    st.markdown('<div class="ph">Test Suite</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ps">Run all built-in examples in one click to verify bias detection accuracy. '
        'Each test has an expected outcome — pass means the model agrees.</div>',
        unsafe_allow_html=True,
    )

    if not api_ok():
        st.markdown('<div class="key-err">⚠ API key missing — cannot run tests.</div>', unsafe_allow_html=True)
    else:
        # Summary of examples
        st.markdown('<div class="lbl" style="margin-bottom:10px;">Test Cases</div>', unsafe_allow_html=True)
        for i, ex in enumerate(EXAMPLES, 1):
            expect = "Bias expected" if ex["expect_bias"] else "Clean expected"
            etype  = TYPE_LABELS[ex["type"]]
            ico    = "⚠" if ex["expect_bias"] else "✓"
            st.markdown(
                f'<div class="test-row">'
                f'<div class="test-ico">{ico}</div>'
                f'<div style="flex:1;">'
                f'<div class="test-tag">{i}. {ex["tag"]}</div>'
                f'<div class="test-type">{etype} · {expect}</div>'
                f'</div>'
                f'<span class="test-badge test-pending" id="tb-{i}">Pending</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Scan mode for test suite
        ts_mode = st.radio("Scan mode for tests",
                           ["quick","full"],
                           format_func=lambda x: "Quick (faster, 1 call each)" if x == "quick" else "Full (3 calls, detailed)",
                           horizontal=True, key="ts_mode")

        run_all = st.button("⊘ Run All Tests", key="ts_run", type="primary")

        if run_all:
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Live Results</div>', unsafe_allow_html=True)

            prog      = st.progress(0)
            ts_results= []
            tsc = {"pass": 0, "fail": 0, "err": 0}

            for i, ex in enumerate(EXAMPLES):
                prog.progress((i) / len(EXAMPLES))
                ph_status = st.empty()
                ph_status.markdown(
                    f'<div style="font-size:.78rem;color:{tok("--accent")};font-weight:600;">'
                    f'Running test {i+1}/{len(EXAMPLES)}: {ex["tag"]}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(ex["text"], ex["type"], mode=ts_mode)
                ph_status.empty()

                if err:
                    status  = "error"
                    status_lbl = "ERROR"
                    tsc["err"] = int(tsc["err"]) + 1
                    ts_results.append({"ex": ex, "rep": None, "err": err, "status": "error"})
                else:
                    got_bias = False
                    if isinstance(rep, dict):
                        rep_d = _as_dict(rep)
                        got_bias = bool(rep_d.get("bias_found", False))
                    expected    = ex["expect_bias"]
                    passed      = (got_bias == expected)
                    status      = "pass" if passed else "fail"
                    status_lbl  = "PASS ✓" if passed else "FAIL ✗"
                    if passed: tsc["pass"] = int(tsc["pass"]) + 1
                    else:      tsc["fail"] = int(tsc["fail"]) + 1
                    ts_results.append({"ex": ex, "rep": rep, "err": None, "status": status, "passed": passed})

            prog.progress(1.0)

            # Summary metrics
            st.markdown("<br>", unsafe_allow_html=True)
            sm1, sm2, sm3, sm4, sm5 = st.columns(5)
            sm1.metric("Total Tests",  len(EXAMPLES))
            sm2.metric("Passed ✓",     tsc["pass"])
            sm3.metric("Failed ✗",     tsc["fail"])
            sm4.metric("Errors",       tsc["err"])
            sm5.metric("Accuracy",     f"{round(int(tsc['pass']) / len(EXAMPLES) * 100)}%")

            # Accuracy bar
            acc = int(tsc["pass"]) / len(EXAMPLES)
            acc_col = tok("--green") if acc >= .8 else (tok("--amber") if acc >= .5 else tok("--red"))
            st.markdown(
                f'<div class="char-track" style="height:5px;margin:10px 0 18px;">'
                f'<div class="char-fill" style="width:{int(acc*100)}%;background:{acc_col};height:100%;"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Per-test detail
            for i, res in enumerate(ts_results, 1):
                ex     = res["ex"]
                status = res["status"]
                badge_cls = f"test-{status}"
                badge_lbl = {"pass":"PASS ✓","fail":"FAIL ✗","error":"ERROR"}[status]
                ico    = "✅" if status == "pass" else ("❌" if status == "fail" else "⚠")

                with st.expander(f'{ico} Test {i}: {ex["tag"]}  [{badge_lbl}]', expanded=(status != "pass")):
                    # Decision text preview
                    st.markdown(f'<div class="preview">{ex["text"]}</div>', unsafe_allow_html=True)

                    if res["err"]:
                        st.error(f"Error: {res['err']}")
                    else:
                        rep = res["rep"]
                        got = rep.get("bias_found", False)
                        exp = ex["expect_bias"]
                        conf_ = int(rep.get("confidence_score",0)*100)

                        # Expected vs Got
                        ecol, gcol = st.columns(2, gap="small")
                        with ecol:
                            exp_cls  = "card-warn" if exp else "card-muted"
                            exp_ico  = "⚠" if exp else "✓"
                            st.markdown(
                                f'<div class="card {exp_cls}">'
                                f'<div class="card-lbl">Expected</div>'
                                f'<div class="card-val mono">{exp_ico} {"Bias" if exp else "No Bias"}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        with gcol:
                            got_cls = "card-err" if got else "card-ok"
                            got_ico = "⚠" if got else "✓"
                            match_lbl = "✓ Match" if (got == exp) else "✗ Mismatch"
                            st.markdown(
                                f'<div class="card {got_cls}">'
                                f'<div class="card-lbl">Got · {match_lbl}</div>'
                                f'<div class="card-val mono">{got_ico} {"Bias" if got else "No Bias"} ({conf_}%)</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # Bias types
                        if rep.get("bias_types"):
                            st.markdown(
                                f'<div class="card card-muted" style="margin-top:6px;">'
                                f'<div class="card-lbl">Detected Bias Types</div>'
                                f'<div>{chips(rep.get("bias_types",[]))}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # Explanation
                        if rep.get("explanation"):
                            st.markdown(
                                f'<div class="card card-muted" style="margin-top:6px;">'
                                f'<div class="card-lbl">Explanation</div>'
                                f'<div class="card-val" style="font-size:.82rem;">{rep["explanation"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # Timing
                        if rep.get("timing_ms"):
                            st.markdown(timing_pills(rep["timing_ms"]), unsafe_allow_html=True)

            # Export test results
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            test_rows = []
            for i, res in enumerate(ts_results, 1):
                ex = res["ex"]
                rep = res.get("rep") or {}
                test_rows.append({
                    "test_n":        i,
                    "tag":           ex["tag"],
                    "type":          ex["type"],
                    "expected_bias": ex["expect_bias"],
                    "got_bias":      rep.get("bias_found","error"),
                    "passed":        res.get("passed", False),
                    "confidence":    int(rep.get("confidence_score",0)*100) if rep else 0,
                    "bias_types":    "; ".join(rep.get("bias_types",[])) if rep else "",
                    "explanation":   rep.get("explanation","") if rep else res.get("err",""),
                    "total_ms":      rep.get("timing_ms",{}).get("total","") if rep else "",
                })
            dl1, _ = st.columns([1,3])
            with dl1:
                st.download_button(
                    "↓ Download Test Report (CSV)",
                    data=pd.DataFrame(test_rows).to_csv(index=False),
                    file_name=f"verdict_test_suite_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv", key="ts_dl",
                )

# ─────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────
elif view == "settings":
    st.markdown('<div class="ph">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Verdict Watch V12 — configuration and diagnostics.</div>', unsafe_allow_html=True)

    sc1, sc2 = st.columns(2, gap="large")
    with sc1:
        st.markdown('<div class="lbl">API & Model</div>', unsafe_allow_html=True)
        ko  = api_ok()
        kst = "✓ Set — loaded from .env" if ko else "✗ Not set"
        kcl = "card-ok" if ko else "card-err"
        pcl = "card-ok" if PDF_SUPPORT else "card-warn"
        pst = "✓ PyMuPDF installed" if PDF_SUPPORT else "pip install PyMuPDF"
        st.markdown(
            f'<div class="card {kcl}"><div class="card-lbl">Groq API Key</div><div class="card-val mono">{kst}</div></div>'
            f'<div class="card"><div class="card-lbl">Model</div><div class="card-val mono">{services._MODEL}</div></div>'
            f'<div class="card"><div class="card-lbl">Pipeline</div><div class="card-val mono">3-step · temp 0.1 · {services._MAX_RETRIES}× retry</div></div>'
            f'<div class="card {pcl}"><div class="card-lbl">PDF Support</div><div class="card-val mono">{pst}</div></div>',
            unsafe_allow_html=True,
        )
        if ko:
            if st.button("⊛ Test API Connection", key="api_test"):
                with st.spinner("Pinging Groq…"):
                    try:
                        client = services.get_groq_client()
                        client.chat.completions.create(
                            model=services._MODEL, max_tokens=5,
                            messages=[{"role":"user","content":"ping"}],
                        )
                        st.success("✓ Groq API connection successful")
                    except Exception as e:
                        st.error(f"✗ {e}")

    with sc2:
        st.markdown('<div class="lbl">Database & Usage</div>', unsafe_allow_html=True)
        all_r  = all_reports()
        fb     = services.get_feedback_stats()
        db_url = os.getenv("DATABASE_URL", "sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="card"><div class="card-lbl">Total Reports</div>'
            f'<div class="card-val mono lg">{len(all_r)}</div></div>'
            f'<div class="card"><div class="card-lbl">Database URL</div>'
            f'<div class="card-val mono" style="font-size:.73rem;">{db_url}</div></div>'
            f'<div class="card card-info"><div class="card-lbl">User Feedback</div>'
            f'<div class="card-val mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="lbl" style="margin-top:14px;">V12 Changelog</div>', unsafe_allow_html=True)
        for ico, name, desc in [
            ("✦","Sparkline Bug Fixed",     "Resolved Plotly margin conflict on dashboard"),
            ("✦","Text Visibility Fixed",   "All card variants have guaranteed readable text"),
            ("✦","Test Suite Tab",          "One-click run of all 10 built-in test cases"),
            ("✦","10 Rich Examples",        "Diverse bias patterns across all decision types"),
            ("✦","Uniform Card System",     "Single CSS card API — no more ad-hoc styles"),
            ("✦","Side-by-Side Compare",    "Integrated into Analyse view via toggle"),
            ("✦","Richer Sidebar Examples", "All 10 examples accessible from sidebar"),
            ("✦","CSS Var Driven",          "Zero hardcoded hex colours — pure CSS vars"),
            ("✦","Compact empty states",    "Consistent empty state design across all views"),
            ("✦","services.py unchanged",   "All fixes are UI-only — no backend changes"),
        ]:
            st.markdown(
                f'<div class="feat-row">'
                f'<span><span class="feat-ico">{ico}</span>'
                f'<span class="feat-name">{name}</span></span>'
                f'<span class="feat-desc">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────
# ABOUT
# ─────────────────────────────────────────────────────
elif view == "about":
    st.markdown('<div class="ph">About Verdict Watch</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ps">Enterprise-grade AI bias detection for automated decisions. V12 — Editorial Dark-Ink Edition.</div>',
        unsafe_allow_html=True,
    )

    ab1, ab2 = st.columns([1.6, 1], gap="large")
    with ab1:
        st.markdown(
            f'<div class="card" style="background:{tok("--surf2")};'
            f'border-color:{tok("--border")};margin-bottom:12px;">'
            f'<div style="font-family:var(--ff-d);font-size:1.1rem;color:{tok("--t1")};margin-bottom:6px;">What is Verdict Watch?</div>'
            f'<div style="font-size:.82rem;color:{tok("--t2")};line-height:1.75;">'
            f'A 3-step Groq + Llama 3.3 70B pipeline that extracts decision criteria, '
            f'detects discriminatory patterns across 7 bias dimensions, cites relevant laws, '
            f'and generates the fair outcome you deserved — all from pasting a rejection letter.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="lbl">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Gender Bias",              "Gender, name, or parental status as a decision factor"),
            ("Age Discrimination",       "Unfair weighting of age group or seniority"),
            ("Racial / Ethnic Bias",     "Name-based, nationality, or origin profiling"),
            ("Geographic Redlining",     "Zip code or district as a discriminatory proxy"),
            ("Socioeconomic Bias",       "Employment sector or credit score over-weighting"),
            ("Language Discrimination",  "Primary language used against applicants"),
            ("Insurance Classification", "Insurance tier used to rank treatment priority"),
        ]:
            st.markdown(
                f'<div class="card" style="margin-bottom:5px;">'
                f'<div class="card-lbl">{name}</div>'
                f'<div class="card-val" style="font-size:.82rem;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="lbl">Tech Stack</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Groq",               "LLM inference"),
            ("Llama 3.3 70B",      "Language model"),
            ("FastAPI",            "REST API"),
            ("Streamlit ≥ 1.35",   "Web UI"),
            ("SQLAlchemy + SQLite","Database"),
            ("Plotly",             "Charts"),
            ("DM Serif Display",   "Heading font"),
            ("Syne",               "UI font"),
            ("JetBrains Mono",     "Data font"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid {tok("--surf3")};">'
                f'<span style="font-size:.82rem;font-weight:500;color:{tok("--t1")};">{name}</span>'
                f'<span style="font-size:.73rem;color:{tok("--t3")};">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="card card-warn">'
            f'<div class="card-lbl">⚠ Disclaimer</div>'
            f'<div class="card-val" style="font-size:.79rem;">'
            f'Not legal advice. Built for educational awareness only. '
            f'Consult a qualified legal professional for discrimination claims.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="text-align:center;font-size:.68rem;color:{tok("--t3")};margin-top:12px;">'
            f'Verdict Watch V12 · Powered by Groq / Llama 3.3 70B'
            f'</div>',
            unsafe_allow_html=True,
        )