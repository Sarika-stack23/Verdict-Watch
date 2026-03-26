"""
streamlit_app.py — Verdict Watch V11
Editorial Dark-Ink Edition.

Design language: off-white parchment (#F7F4EF) + near-black ink (#111118).
Typography: DM Serif Display (headings) · Syne (UI labels) · JetBrains Mono (data).
Layout: Persistent left sidebar rail for navigation — no top tab bar.

V11 new features:
  ✦ Quick Scan mode (single Groq call)
  ✦ Dark mode toggle
  ✦ Confidence trend sparkline on dashboard
  ✦ Per-call timing display
  ✦ Feedback comments
  ✦ Improved empty states
  ✦ Full-text report download from History
  ✦ API health indicator in sidebar
  ✦ Compare: bias-type diff badges
"""

import streamlit as st
import services
import plotly.graph_objects as go
import pandas as pd
import re, os, json, time
from datetime import datetime
from collections import Counter

# ── Optional PDF support
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
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# THEME TOKENS
# ──────────────────────────────────────────────

LIGHT = {
    "--bg":       "#F7F4EF",
    "--surf":     "#FFFFFF",
    "--surf2":    "#F0EDE8",
    "--surf3":    "#E8E4DE",
    "--border":   "#DDD9D2",
    "--t1":       "#111118",
    "--t2":       "#4A4A5A",
    "--t3":       "#8A8A9A",
    "--ink":      "#111118",
    "--ink-inv":  "#FFFFFF",
    "--accent":   "#2B4EFF",
    "--acc-lt":   "#EEF1FF",
    "--acc-dk":   "#1A3AE0",
    "--red":      "#C53030",
    "--red-lt":   "#FFF5F5",
    "--green":    "#1A6B3C",
    "--grn-lt":   "#F0FDF4",
    "--amber":    "#B45309",
    "--amb-lt":   "#FFFBEB",
    "--sh":       "0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04)",
    "--sh2":      "0 4px 16px rgba(0,0,0,.08)",
}

DARK = {
    "--bg":       "#0D0D14",
    "--surf":     "#17171F",
    "--surf2":    "#1E1E28",
    "--surf3":    "#25252F",
    "--border":   "#2E2E3A",
    "--t1":       "#EEEEF5",
    "--t2":       "#9090A0",
    "--t3":       "#55556A",
    "--ink":      "#EEEEF5",
    "--ink-inv":  "#111118",
    "--accent":   "#5B7FFF",
    "--acc-lt":   "#1A1F3A",
    "--acc-dk":   "#7A99FF",
    "--red":      "#FF6B6B",
    "--red-lt":   "#2A1010",
    "--green":    "#4ADE80",
    "--grn-lt":   "#0D2010",
    "--amber":    "#FBB040",
    "--amb-lt":   "#271A04",
    "--sh":       "0 1px 3px rgba(0,0,0,.3), 0 1px 2px rgba(0,0,0,.2)",
    "--sh2":      "0 4px 16px rgba(0,0,0,.4)",
}

def tokens() -> dict:
    return DARK if st.session_state.get("dark_mode") else LIGHT

def tok(key: str) -> str:
    return tokens()[key]

# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────

def inject_css():
    T = tokens()
    vars_block = "\n".join(f"  {k}: {v};" for k, v in T.items())
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Syne:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
{vars_block}
  --r:     8px;
  --r-lg:  14px;
  --r-xl:  20px;
  --r-pill: 999px;
  --ff:    'Syne', system-ui, sans-serif;
  --ff-serif: 'DM Serif Display', Georgia, serif;
  --ff-mono:  'JetBrains Mono', 'Courier New', monospace;
}}

html, body, [class*="css"] {{
  font-family: var(--ff) !important;
  background: var(--bg) !important;
  color: var(--t1) !important;
}}

/* ── Sidebar (the "rail") ── */
[data-testid="stSidebar"] {{
  background: var(--ink) !important;
  border-right: 1px solid rgba(255,255,255,.06) !important;
  min-width: 248px !important;
  max-width: 248px !important;
}}
[data-testid="stSidebar"] * {{ color: rgba(255,255,255,.75) !important; }}
[data-testid="stSidebar"] .stMarkdown h3 {{
  color: rgba(255,255,255,.3) !important;
  font-size: .62rem !important;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
  margin: 18px 0 6px !important;
  font-family: var(--ff) !important;
}}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {{
  background: transparent !important;
  color: rgba(255,255,255,.6) !important;
  border: none !important;
  border-radius: var(--r) !important;
  padding: 7px 10px !important;
  font-family: var(--ff) !important;
  font-size: .82rem !important;
  font-weight: 400 !important;
  text-align: left !important;
  width: 100% !important;
  box-shadow: none !important;
  transform: none !important;
  transition: background .15s, color .15s !important;
  letter-spacing: .01em !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  background: rgba(255,255,255,.07) !important;
  color: rgba(255,255,255,.95) !important;
  transform: none !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: rgba(91,127,255,.2) !important;
  color: rgba(180,200,255,.95) !important;
  border: 1px solid rgba(91,127,255,.3) !important;
}}

/* ── Main tabs (override Streamlit's own) ── */
.stTabs [data-baseweb="tab-list"] {{ display: none !important; }}
.stTabs [data-baseweb="tab-panel"] {{ padding-top: 0 !important; }}

/* ── Main content buttons ── */
.stButton > button {{
  font-family: var(--ff) !important;
  font-size: .875rem !important;
  font-weight: 600 !important;
  background: var(--ink) !important;
  color: var(--ink-inv) !important;
  border: none !important;
  border-radius: var(--r-pill) !important;
  padding: .55rem 1.6rem !important;
  box-shadow: var(--sh) !important;
  transition: opacity .15s, transform .1s !important;
  letter-spacing: .02em !important;
}}
.stButton > button:hover {{ opacity: .85 !important; transform: translateY(-1px) !important; }}
.stButton > button:active {{ transform: none !important; }}
.stButton > button:disabled {{ opacity: .35 !important; transform: none !important; }}

/* ── Ghost / secondary button ── */
.stButton > button[kind="secondary"] {{
  background: transparent !important;
  color: var(--t1) !important;
  border: 1.5px solid var(--border) !important;
  box-shadow: none !important;
}}
.stButton > button[kind="secondary"]:hover {{
  background: var(--surf2) !important; transform: none !important;
}}

/* ── Download button ── */
.stDownloadButton > button {{
  background: transparent !important;
  color: var(--accent) !important;
  border: 1.5px solid var(--accent) !important;
  border-radius: var(--r-pill) !important;
  font-family: var(--ff) !important;
  font-weight: 600 !important;
  font-size: .8rem !important;
  box-shadow: none !important;
  padding: .4rem 1.1rem !important;
  transform: none !important;
}}
.stDownloadButton > button:hover {{
  background: var(--acc-lt) !important; transform: none !important;
}}

/* ── Text inputs ── */
.stTextArea textarea, .stTextInput input {{
  font-family: var(--ff) !important;
  font-size: .9rem !important;
  background: var(--surf) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  color: var(--t1) !important;
  transition: border-color .2s !important;
  line-height: 1.7 !important;
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(43,78,255,.08) !important;
  outline: none !important;
}}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {{
  color: var(--t3) !important;
}}
.stTextArea label, .stTextInput label, .stSelectbox label, .stRadio label {{
  font-family: var(--ff) !important;
  font-size: .68rem !important;
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
  font-family: var(--ff) !important;
  font-size: .875rem !important;
  color: var(--t1) !important;
}}

/* ── Radio ── */
.stRadio > div {{ gap: 6px !important; }}
.stRadio > div > label {{
  background: var(--surf2) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r) !important;
  padding: 6px 14px !important;
  font-size: .8rem !important;
  font-weight: 500 !important;
  color: var(--t2) !important;
  cursor: pointer !important;
  transition: all .15s !important;
  text-transform: none !important;
  letter-spacing: normal !important;
}}
.stRadio > div > label:has(input:checked) {{
  background: var(--ink) !important;
  color: var(--ink-inv) !important;
  border-color: var(--ink) !important;
}}

/* ── Metrics ── */
[data-testid="metric-container"] {{
  background: var(--surf) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  padding: 1rem 1.25rem !important;
  box-shadow: var(--sh) !important;
}}
[data-testid="metric-container"] label {{
  font-family: var(--ff) !important;
  font-size: .65rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
  color: var(--t3) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
  font-family: var(--ff-mono) !important;
  font-size: 1.65rem !important;
  font-weight: 500 !important;
  color: var(--t1) !important;
}}

/* ── Progress ── */
.stProgress > div > div {{ background: var(--accent) !important; border-radius: 2px !important; }}
.stProgress > div {{ background: var(--surf3) !important; border-radius: 2px !important; height: 3px !important; }}

/* ── File uploader ── */
[data-testid="stFileUploader"] {{
  background: var(--surf) !important;
  border: 2px dashed var(--border) !important;
  border-radius: var(--r-lg) !important;
  transition: border-color .15s !important;
}}
[data-testid="stFileUploader"]:hover {{ border-color: var(--accent) !important; }}

/* ── Expander ── */
.streamlit-expanderHeader {{
  font-family: var(--ff) !important;
  font-weight: 500 !important;
  font-size: .875rem !important;
  background: var(--surf) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
}}
.streamlit-expanderContent {{
  background: var(--surf) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 var(--r) var(--r) !important;
}}

/* ── Hide Streamlit chrome ── */
footer, [data-testid="stStatusWidget"],
[data-testid="stDecoration"], #MainMenu {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; }}

/* ── VERDICT WATCH COMPONENTS ── */

.vw-wordmark {{
  font-family: var(--ff-serif) !important;
  font-size: 1.25rem !important;
  color: #fff !important;
  letter-spacing: -.01em !important;
  line-height: 1 !important;
}}
.vw-tagline {{
  font-size: .6rem !important;
  color: rgba(255,255,255,.35) !important;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
  margin-top: 3px !important;
}}
.vw-api-dot {{
  display: inline-block; width: 7px; height: 7px;
  border-radius: 50%; margin-right: 5px;
  vertical-align: middle;
}}
.vw-api-ok  {{ background: #4ade80; }}
.vw-api-err {{ background: #f87171; }}

.page-heading {{
  font-family: var(--ff-serif);
  font-size: 2rem;
  font-weight: 400;
  color: var(--t1);
  letter-spacing: -.03em;
  line-height: 1.1;
  margin-bottom: 4px;
}}
.page-sub {{
  font-size: .82rem;
  color: var(--t3);
  letter-spacing: .01em;
  margin-bottom: 1.75rem;
}}

.lbl {{
  font-size: .65rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--t3);
  margin-bottom: 8px;
}}

.card {{
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1rem 1.2rem;
  margin-bottom: 8px;
  box-shadow: var(--sh);
}}
.card.err  {{ background: var(--red-lt);  border-color: rgba(197,48,48,.18); }}
.card.ok   {{ background: var(--grn-lt);  border-color: rgba(26,107,60,.18); }}
.card.warn {{ background: var(--amb-lt);  border-color: rgba(180,83,9,.18);  }}
.card.info {{ background: var(--acc-lt);  border-color: rgba(43,78,255,.18); }}
.card.muted {{ background: var(--surf2); }}

.card-lbl {{
  font-size: .62rem; font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase;
  color: var(--t3); margin-bottom: 6px;
}}
.card-val {{ font-size: .875rem; color: var(--t1); line-height: 1.55; }}
.card-val.mono  {{ font-family: var(--ff-mono); font-size: .8rem; }}
.card-val.lg    {{ font-size: 1.15rem; font-weight: 700; }}
.card-val.serif {{ font-family: var(--ff-serif); font-size: 1.1rem; }}

.verdict-banner {{
  border-radius: var(--r-xl);
  padding: 1.75rem 2rem;
  text-align: center;
  margin-bottom: 1rem;
  border: 1px solid;
}}
.verdict-banner.bias  {{
  background: var(--red-lt);
  border-color: rgba(197,48,48,.2);
}}
.verdict-banner.clean {{
  background: var(--grn-lt);
  border-color: rgba(26,107,60,.2);
}}
.vb-title {{
  font-family: var(--ff-serif);
  font-size: 1.6rem;
  font-weight: 400;
  letter-spacing: -.02em;
  margin-bottom: 4px;
}}
.verdict-banner.bias  .vb-title {{ color: var(--red);   }}
.verdict-banner.clean .vb-title {{ color: var(--green); }}
.vb-sub {{ font-size: .82rem; color: var(--t2); }}

.ring-wrap {{
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 6px 0;
}}

.chip {{
  display: inline-block;
  border-radius: var(--r-pill);
  padding: 2px 10px;
  font-size: .72rem;
  font-weight: 600;
  margin: 2px 3px 2px 0;
  border: 1px solid transparent;
  letter-spacing: .01em;
}}
.chip-r {{ background: var(--red-lt); color: var(--red);   border-color: rgba(197,48,48,.2);  }}
.chip-g {{ background: var(--grn-lt); color: var(--green); border-color: rgba(26,107,60,.2);  }}
.chip-b {{ background: var(--acc-lt); color: var(--accent); border-color: rgba(43,78,255,.2); }}
.chip-a {{ background: var(--amb-lt); color: var(--amber); border-color: rgba(180,83,9,.2);   }}
.chip-n {{ background: var(--surf2);  color: var(--t2);    border-color: var(--border);        }}

.sev {{
  display: inline-block;
  border-radius: var(--r-pill);
  padding: 2px 10px;
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
}}
.sev-h {{ background: var(--red-lt); color: var(--red);   }}
.sev-m {{ background: var(--amb-lt); color: var(--amber); }}
.sev-l {{ background: var(--grn-lt); color: var(--green); }}

.hl-box {{
  font-size: .875rem;
  line-height: 1.9;
  color: var(--t2);
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 1rem 1.2rem;
}}
.hl-box mark {{
  background: rgba(197,48,48,.1);
  color: var(--red);
  border-radius: 3px;
  padding: 1px 4px;
  border-bottom: 1.5px solid rgba(197,48,48,.3);
}}

.rec {{
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: .8rem 1rem;
  margin-bottom: 6px;
}}
.rec-n {{
  background: var(--ink);
  color: var(--ink-inv);
  border-radius: 5px;
  min-width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--ff-mono);
  font-size: .65rem; font-weight: 700;
  flex-shrink: 0; margin-top: 1px;
}}
.rec-t {{ font-size: .83rem; color: var(--t2); line-height: 1.55; }}

.appeal-box {{
  background: var(--surf2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--r-lg);
  padding: 1.1rem 1.4rem;
  font-family: var(--ff-mono);
  font-size: .76rem;
  line-height: 1.9;
  color: var(--t2);
  white-space: pre-wrap;
}}

.law-row {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--surf3);
  font-size: .83rem;
  color: var(--t2);
}}
.law-row:last-child {{ border-bottom: none; }}

.scan-steps {{
  display: flex; gap: 5px; margin-bottom: 8px;
}}
.ss-item {{
  flex: 1; background: var(--surf2);
  border-radius: var(--r); padding: .4rem .6rem;
  text-align: center; border: 1px solid transparent;
  transition: all .3s;
}}
.ss-item.done   {{ background: var(--grn-lt); border-color: rgba(26,107,60,.2); }}
.ss-item.active {{ background: var(--acc-lt); border-color: rgba(43,78,255,.2); }}
.ss-lbl {{
  font-size: .65rem; font-weight: 600;
  color: var(--t3); font-family: var(--ff);
  letter-spacing: .04em;
}}
.ss-item.done   .ss-lbl {{ color: var(--green); }}
.ss-item.active .ss-lbl {{ color: var(--accent); }}

.scan-track {{ background: var(--surf3); border-radius: 2px; height: 2px; overflow: hidden; margin: 4px 0; }}
@keyframes scan {{ 0%{{transform:translateX(-120%)}} 100%{{transform:translateX(400%)}} }}
.scan-fill {{ height: 100%; background: var(--accent); border-radius: 2px; animation: scan 1.2s ease-in-out infinite; width: 22%; }}

.timing-row {{
  display: flex; gap: 10px; margin-top: 8px; flex-wrap: wrap;
}}
.timing-pill {{
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--surf2); border: 1px solid var(--border);
  border-radius: var(--r-pill); padding: 2px 9px;
  font-family: var(--ff-mono); font-size: .7rem; color: var(--t3);
}}
.timing-pill strong {{ color: var(--t2); font-weight: 500; }}

.key-err {{
  background: var(--red-lt);
  border: 1px solid rgba(197,48,48,.25);
  border-left: 3px solid var(--red);
  border-radius: var(--r-lg);
  padding: .9rem 1.2rem;
  font-size: .875rem;
  color: var(--red);
  margin-bottom: 1rem;
}}

.dup-warn {{
  display: flex; align-items: flex-start; gap: 10px;
  background: var(--amb-lt);
  border: 1px solid rgba(180,83,9,.25);
  border-radius: var(--r-lg);
  padding: .9rem 1.1rem;
  font-size: .875rem; color: var(--amber);
  margin-bottom: 1rem;
}}

.empty {{
  text-align: center;
  padding: 4rem 1rem;
}}
.empty-ico {{ font-size: 2.8rem; opacity: .25; margin-bottom: 12px; }}
.empty-t {{
  font-family: var(--ff-serif);
  font-size: 1.2rem; color: var(--t2);
  margin-bottom: 5px;
}}
.empty-s {{ font-size: .83rem; color: var(--t3); line-height: 1.65; max-width: 300px; margin: 0 auto; }}

.divider {{ border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }}

.badge-ok  {{ display:inline-flex; align-items:center; gap:5px; background:var(--grn-lt); color:var(--green); border-radius:var(--r-pill); padding:3px 11px; font-size:.72rem; font-weight:700; }}
.badge-err {{ display:inline-flex; align-items:center; gap:5px; background:var(--red-lt); color:var(--red);   border-radius:var(--r-pill); padding:3px 11px; font-size:.72rem; font-weight:700; }}
.badge-warn {{ display:inline-flex; align-items:center; gap:5px; background:var(--amb-lt); color:var(--amber); border-radius:var(--r-pill); padding:3px 11px; font-size:.72rem; font-weight:700; }}

.mode-badge-quick {{ background:var(--amb-lt); color:var(--amber); border:1px solid rgba(180,83,9,.2); border-radius:var(--r-pill); padding:2px 9px; font-size:.68rem; font-weight:700; letter-spacing:.04em; }}
.mode-badge-full  {{ background:var(--acc-lt); color:var(--accent); border:1px solid rgba(43,78,255,.2); border-radius:var(--r-pill); padding:2px 9px; font-size:.68rem; font-weight:700; letter-spacing:.04em; }}

.diff-badge {{ display:inline-block; border-radius:var(--r-pill); padding:2px 9px; font-size:.71rem; font-weight:700; margin:2px; }}
.diff-only-a {{ background:var(--acc-lt); color:var(--accent); }}
.diff-only-b {{ background:var(--red-lt); color:var(--red); }}
.diff-shared {{ background:var(--grn-lt); color:var(--green); }}

.winner-bar {{
  background: var(--acc-lt);
  border: 1px solid rgba(43,78,255,.15);
  border-radius: var(--r-lg);
  padding: .85rem 1.2rem;
  text-align: center;
  font-size: .9rem; font-weight: 600;
  color: var(--accent);
  margin-bottom: 1rem;
}}

.char-row {{
  display: flex; justify-content: space-between;
  font-size: .72rem; font-weight: 600; margin-top: 6px;
}}
.char-track {{ height: 2px; background: var(--surf3); border-radius: 1px; margin-top: 4px; }}
.char-fill  {{ height: 100%; border-radius: 1px; transition: width .3s, background .3s; }}

.sb-section-lbl {{
  font-size: .6rem !important;
  font-weight: 700 !important;
  letter-spacing: .14em !important;
  text-transform: uppercase !important;
  color: rgba(255,255,255,.28) !important;
  padding: 16px 0 5px !important;
  display: block !important;
}}
.sb-step-row {{
  display: flex; gap: 8px; padding: 3px 0; align-items: flex-start;
}}
.sb-step-n {{
  background: rgba(255,255,255,.1); color: rgba(255,255,255,.6);
  border-radius: 4px; width: 17px; height: 17px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--ff-mono); font-size: .6rem; font-weight: 700;
  flex-shrink: 0; margin-top: 1px;
}}
.sb-step-t {{ font-size: .77rem; color: rgba(255,255,255,.5); line-height: 1.45; }}

.preview-box {{
  background: var(--surf2); border: 1px solid var(--border);
  border-radius: var(--r); padding: .6rem .85rem;
  font-family: var(--ff-mono); font-size: .74rem;
  color: var(--t2); line-height: 1.6;
  max-height: 70px; overflow: hidden;
  white-space: pre-wrap; margin-bottom: 6px;
}}

.feature-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 0; border-bottom: 1px solid var(--surf3);
  font-size: .83rem;
}}
.feature-row:last-child {{ border-bottom: none; }}
.feature-name {{ font-weight: 500; color: var(--t1); }}
.feature-desc {{ font-size: .75rem; color: var(--t3); }}
.feature-check {{ color: var(--green); font-weight: 700; margin-right: 8px; }}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

EXAMPLES = [
    {"tag": "Job Rejection",  "type": "job",
     "text": "Thank you for applying to the Software Engineer position. After careful review we have decided not to move forward. We felt other candidates were a stronger fit for our team culture at this time."},
    {"tag": "Bank Loan",      "type": "loan",
     "text": "Your loan application has been declined. Primary reasons: insufficient credit history, residential area risk score, employment sector classification. You may reapply after 6 months."},
    {"tag": "Medical Triage", "type": "medical",
     "text": "Based on your intake assessment you have been assigned Priority Level 3. Factors considered: age group, reported pain level, primary language, insurance classification."},
    {"tag": "University",     "type": "university",
     "text": "We regret to inform you that your application for admission has not been successful. Our admissions committee considered zip code region diversity metrics, legacy status, and extracurricular profile alignment when making this decision."},
    {"tag": "Housing",        "type": "other",
     "text": "After reviewing your rental application we are unable to proceed. Factors reviewed include your neighbourhood of origin, employment sector, and family size relative to unit capacity."},
]

TYPE_LABELS = {
    "job": "Job Application", "loan": "Bank Loan",
    "medical": "Medical / Triage", "university": "University Admission", "other": "Other",
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

VIEWS = [
    ("analyse",   "⚡", "Analyse"),
    ("dashboard", "◎", "Dashboard"),
    ("history",   "▤", "History"),
    ("compare",   "⇔", "Compare"),
    ("batch",     "⊞", "Batch"),
    ("settings",  "⊛", "Settings"),
    ("about",     "◷", "About"),
]

CHIP_CYCLE = ["chip-r", "chip-a", "chip-b", "chip-g", "chip-n"]

# ──────────────────────────────────────────────
# PLOTLY BASE (respects dark/light)
# ──────────────────────────────────────────────

def plotly_base() -> dict:
    dark = st.session_state.get("dark_mode")
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Syne, system-ui, sans-serif",
            color="#9090A0" if dark else "#4A4A5A",
        ),
        margin=dict(l=10, r=10, t=16, b=10),
    )

PAL = ["#2B4EFF", "#C53030", "#1A6B3C", "#B45309", "#7C3AED", "#0891B2", "#DB2777"]

# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

_DEFAULTS = {
    "view":            "analyse",
    "session_count":   0,
    "last_report":     None,
    "last_text":       "",
    "appeal_letter":   None,
    "decision_input":  "",
    "dtype_sel":       "job",
    "scan_mode":       "full",
    "force_rerun":     False,
    "dark_mode":       False,
    "fb_comment":      "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def api_ok() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())

def all_reports() -> list[dict]:
    try:
        return services.get_all_reports()
    except Exception:
        return []

def chips(items: list, style: str = "auto") -> str:
    if not items:
        return '<span class="chip chip-n">None detected</span>'
    return "".join(
        f'<span class="chip {CHIP_CYCLE[i % len(CHIP_CYCLE)] if style == "auto" else style}">{item}</span>'
        for i, item in enumerate(items)
    )

def highlight(text: str, phrases: list, bias_types: list) -> str:
    out = text
    for p in (phrases or []):
        if p and len(p) > 2:
            out = re.sub(re.escape(p), lambda m: f"<mark>{m.group()}</mark>", out, flags=re.IGNORECASE)
    for b in (bias_types or []):
        for key, pat in BIAS_KW.items():
            if key.lower() in b.lower() or b.lower() in key.lower():
                out = re.sub(pat, lambda m: f"<mark>{m.group()}</mark>", out, flags=re.IGNORECASE)
    return out

def sev_badge(conf: float, bias: bool, sev: str = "low") -> str:
    if not bias:
        return '<span class="sev sev-l">Low Risk</span>'
    if sev == "high" or conf >= .75:
        return '<span class="sev sev-h">High</span>'
    if sev == "medium" or conf >= .45:
        return '<span class="sev sev-m">Medium</span>'
    return '<span class="sev sev-l">Low</span>'

def ring_svg(pct: int, bias: bool, size: int = 120) -> str:
    r, cx, cy = size * .38, size / 2, size / 2
    sw   = size * .09
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    gap  = circ - dash
    col  = tok("--red") if bias else (tok("--green") if pct < 45 else tok("--amber"))
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{tok("--surf3")}" stroke-width="{sw}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"'
        f' stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-linecap="round"'
        f' transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy - size*.04}" text-anchor="middle"'
        f' font-family="JetBrains Mono,monospace" font-size="{size*.18}" font-weight="500" fill="{col}">{pct}%</text>'
        f'<text x="{cx}" y="{cy + size*.1}" text-anchor="middle"'
        f' font-family="Syne,sans-serif" font-size="{size*.07}" font-weight="700"'
        f' fill="{tok("--t3")}" letter-spacing="0.08em">CONF</text>'
        f'</svg>'
    )

def timing_pills(timing: dict) -> str:
    if not timing:
        return ""
    parts = []
    labels = {"extract": "Extract", "detect": "Detect", "fair": "Fair", "quick": "Scan", "total": "Total"}
    for k, v in timing.items():
        lbl = labels.get(k, k)
        parts.append(f'<span class="timing-pill"><strong>{lbl}</strong> {v}ms</span>')
    return '<div class="timing-row">' + "".join(parts) + "</div>"

def txt_report(report: dict, text: str, dtype: str) -> str:
    recs  = report.get("recommendations", [])
    laws  = report.get("legal_frameworks", [])
    tm    = report.get("timing_ms", {})
    lines = [
        "=" * 64,
        "       VERDICT WATCH V11 — BIAS ANALYSIS REPORT",
        "=" * 64,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id', 'N/A')}",
        f"Mode       : {(report.get('mode') or 'full').upper()}",
        f"Severity   : {(report.get('severity') or 'N/A').upper()}",
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
        report.get("affected_characteristic") or "N/A",
        "",
        "── ORIGINAL OUTCOME ─────────────────────────────────────",
        report.get("original_outcome") or "N/A",
        "",
        "── FAIR OUTCOME ─────────────────────────────────────────",
        report.get("fair_outcome") or "N/A",
        "",
        "── EXPLANATION ──────────────────────────────────────────",
        report.get("explanation") or "N/A",
        "",
        "── NEXT STEPS ───────────────────────────────────────────",
        *[f"  {i+1}. {r}" for i, r in enumerate(recs)],
    ]
    if laws:
        lines += ["", "── LEGAL FRAMEWORKS ─────────────────────────────────────"]
        lines += [f"  • {l}" for l in laws]
    if tm:
        lines += ["", "── TIMING ───────────────────────────────────────────────"]
        lines += [f"  {k}: {v}ms" for k, v in tm.items()]
    lines += ["", "=" * 64, "  Verdict Watch V11  ·  Not legal advice", "=" * 64]
    return "\n".join(lines)

def to_csv(reps: list[dict]) -> str:
    rows = [{
        "id":          r.get("id", ""),
        "created_at":  (r.get("created_at") or "")[:16].replace("T", " "),
        "mode":        r.get("mode", "full"),
        "bias_found":  r.get("bias_found", False),
        "severity":    r.get("severity", ""),
        "confidence":  int(r.get("confidence_score", 0) * 100),
        "bias_types":  "; ".join(r.get("bias_types", [])),
        "affected":    r.get("affected_characteristic", ""),
        "original":    r.get("original_outcome", ""),
        "fair":        r.get("fair_outcome", ""),
        "explanation": r.get("explanation", ""),
        "legal":       "; ".join(r.get("legal_frameworks", [])),
        "next_steps":  " | ".join(r.get("recommendations", [])),
        "total_ms":    r.get("timing_ms", {}).get("total", ""),
    } for r in reps]
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
    st.warning(f"Unsupported file: {f.name}")
    return None

# ──────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────

def chart_pie(bias_n: int, clean_n: int) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias"],
        values=[max(bias_n, 1), max(clean_n, 1)],
        hole=.68,
        marker=dict(
            colors=[tok("--red"), tok("--green")],
            line=dict(color=tok("--bg"), width=3),
        ),
        textfont=dict(family="Syne, sans-serif", size=11),
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    total = bias_n + clean_n or 1
    fig.add_annotation(
        text=f"<b style='font-size:22px'>{total}</b><br><span style='font-size:9px;color:{tok('--t3')}'>TOTAL</span>",
        x=.5, y=.5, showarrow=False,
        font=dict(family="JetBrains Mono, monospace", size=20, color=tok("--t1")),
    )
    fig.update_layout(height=220, showlegend=True,
        legend=dict(font=dict(family="Syne,sans-serif",size=10), bgcolor="rgba(0,0,0,0)",
                    orientation="h", x=.5, xanchor="center", y=-.04),
        **plotly_base())
    return fig

def chart_bar(items: list, max_n: int = 8) -> go.Figure:
    counts = Counter(items)
    if not counts: counts = {"No data": 1}
    labels, values = zip(*counts.most_common(max_n))
    dark = st.session_state.get("dark_mode")
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=PAL[:len(labels)], line=dict(width=0), cornerradius=4),
        text=list(values),
        textfont=dict(family="JetBrains Mono, monospace", size=10, color=tok("--t2")),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(160, len(labels) * 40 + 50),
        xaxis=dict(showgrid=True, gridcolor=tok("--surf3"), zeroline=False,
                   tickfont=dict(family="JetBrains Mono,monospace", size=9)),
        yaxis=dict(tickfont=dict(family="Syne,sans-serif", size=10)),
        bargap=.4, **plotly_base())
    return fig

def chart_sparkline(scores: list[float]) -> go.Figure:
    """Small confidence trend line."""
    if not scores:
        scores = [0]
    fig = go.Figure(go.Scatter(
        y=scores, mode="lines",
        line=dict(color=tok("--accent"), width=2),
        fill="tozeroy",
        fillcolor=f"rgba(43,78,255,{'0.12' if not st.session_state.get('dark_mode') else '0.08'})",
        hovertemplate="Score %{y}%<extra></extra>",
    ))
    fig.update_layout(
        height=80,
        xaxis=dict(visible=False),
        yaxis=dict(range=[0, 105], visible=False),
        margin=dict(l=0, r=0, t=4, b=0),
        **plotly_base(),
    )
    return fig

def chart_trend(td: list[dict]) -> go.Figure | None:
    if not td: return None
    dates  = [d["date"] for d in td]
    rates  = [d["bias_rate"] for d in td]
    totals = [d["total"] for d in td]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=totals, name="Total",
        marker=dict(color=tok("--surf3"), line=dict(width=0), cornerradius=3),
        yaxis="y2", hovertemplate="%{x}: %{y} analyses<extra></extra>"))
    fig.add_trace(go.Scatter(x=dates, y=rates, name="Bias %",
        mode="lines+markers",
        line=dict(color=tok("--red"), width=2.5),
        marker=dict(color=tok("--red"), size=5, line=dict(color=tok("--bg"), width=1.5)),
        hovertemplate="%{x}: %{y}%<extra></extra>"))
    fig.update_layout(
        height=220,
        yaxis=dict(range=[0,105], tickfont=dict(family="JetBrains Mono,monospace",size=9),
                   gridcolor=tok("--surf3"), zeroline=False),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickfont=dict(family="JetBrains Mono,monospace",size=9)),
        xaxis=dict(tickfont=dict(family="Syne,sans-serif",size=9)),
        legend=dict(font=dict(family="Syne,sans-serif",size=10),bgcolor="rgba(0,0,0,0)",
                    x=0, y=1.1, orientation="h"),
        **plotly_base())
    return fig

def chart_radar(all_r: list[dict]) -> go.Figure:
    dc = {d: 0 for d in BIAS_DIMS}
    for r in all_r:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower():
                    dc[dim] += 1
    vals = [dc[d] for d in BIAS_DIMS]
    dark = st.session_state.get("dark_mode")
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=BIAS_DIMS + [BIAS_DIMS[0]],
        fill="toself",
        fillcolor=f"rgba(43,78,255,{'0.08' if not dark else '0.12'})",
        line=dict(color=tok("--accent"), width=2),
        marker=dict(color=tok("--accent"), size=5),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, gridcolor=tok("--surf3"),
                            tickfont=dict(family="JetBrains Mono,monospace", size=8)),
            angularaxis=dict(gridcolor=tok("--surf3"),
                             tickfont=dict(family="Syne,sans-serif", size=9)),
        ),
        height=260, showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Syne, sans-serif"),
    )
    return fig

def chart_gauge(val: float, bias: bool) -> go.Figure:
    col = tok("--red") if bias else tok("--green")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(val * 100),
        number={"suffix": "%", "font": {"family": "JetBrains Mono,monospace", "size": 24, "color": col}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0,
                     "tickfont": {"color": tok("--t3"), "size": 8}},
            "bar":  {"color": col, "thickness": 0.2},
            "bgcolor": tok("--surf2"),
            "borderwidth": 0,
            "steps": [
                {"range": [0, 33],   "color": f"rgba(26,107,60,.08)"},
                {"range": [33, 66],  "color": f"rgba(180,83,9,.08)"},
                {"range": [66, 100], "color": f"rgba(197,48,48,.08)"},
            ],
        },
    ))
    fig.update_layout(height=170, **plotly_base())
    return fig

# ──────────────────────────────────────────────
# PIPELINE RUNNER (with progress UI)
# ──────────────────────────────────────────────

def _render_steps(ph, current: int, label: str):
    steps = [(1, "EXTRACT"), (2, "DETECT"), (3, "GENERATE")]
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
        f'<div class="scan-steps">{"".join(parts)}</div>'
        f'<div class="scan-track"><div class="scan-fill"></div></div>'
        f'<div style="font-size:.76rem;color:{tok("--accent")};font-weight:600;margin-top:4px;">⬤ {label}</div>',
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

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────

inject_css()

with st.sidebar:
    # Brand
    ok = api_ok()
    dot_cls = "vw-api-ok" if ok else "vw-api-err"
    st.markdown(
        f'<div style="padding:20px 0 14px;">'
        f'<div class="vw-wordmark">Verdict Watch</div>'
        f'<div class="vw-tagline">V11 · Bias Intelligence</div>'
        f'<div style="margin-top:10px;font-size:.7rem;color:rgba(255,255,255,.4);">'
        f'<span class="vw-api-dot {dot_cls}"></span>'
        f'{"Groq API connected" if ok else "API key missing — see Settings"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.07);margin:0 0 4px;"></div>', unsafe_allow_html=True)

    # Nav
    st.markdown('<span class="sb-section-lbl">Navigation</span>', unsafe_allow_html=True)
    for vid, icon, label in VIEWS:
        is_active = st.session_state["view"] == vid
        btn_type  = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {label}", key=f"nav_{vid}", type=btn_type, use_container_width=True):
            st.session_state["view"] = vid
            st.rerun()

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.07);margin:10px 0 4px;"></div>', unsafe_allow_html=True)

    # Examples
    st.markdown('<span class="sb-section-lbl">Quick Examples</span>', unsafe_allow_html=True)
    for ex in EXAMPLES:
        if st.button(ex["tag"], key=f"ex_{ex['tag']}", use_container_width=True):
            st.session_state["decision_input"] = ex["text"]
            st.session_state["dtype_sel"]      = ex["type"]
            st.session_state["view"]           = "analyse"
            st.rerun()

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.07);margin:10px 0 4px;"></div>', unsafe_allow_html=True)

    # How it works
    st.markdown('<span class="sb-section-lbl">How It Works</span>', unsafe_allow_html=True)
    for n, t in [
        ("1", "Paste text or upload a file"),
        ("2", "AI extracts decision criteria"),
        ("3", "Scans 7 bias dimensions"),
        ("4", "Generates fair outcome + laws"),
        ("5", "Download report or draft appeal"),
    ]:
        st.markdown(
            f'<div class="sb-step-row">'
            f'<div class="sb-step-n">{n}</div>'
            f'<div class="sb-step-t">{t}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.07);margin:10px 0 8px;"></div>', unsafe_allow_html=True)

    # Stats + dark toggle
    c1, c2 = st.columns(2)
    c1.metric("Session", st.session_state.get("session_count", 0))
    c2.metric("All Time", len(all_reports()))

    dark = st.toggle("Dark mode", value=st.session_state.get("dark_mode", False), key="dark_mode")

# ──────────────────────────────────────────────
# MAIN CONTENT — VIEW ROUTER
# ──────────────────────────────────────────────

view = st.session_state["view"]

# ══════════════════════════════════════════════
# ANALYSE
# ══════════════════════════════════════════════
if view == "analyse":
    st.markdown('<div class="page-heading">Analyse a Decision</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Paste any rejection, denial, or triage text to detect hidden bias.</div>', unsafe_allow_html=True)

    if not api_ok():
        st.markdown(
            '<div class="key-err">⚠ <strong>GROQ_API_KEY not found.</strong> '
            'Add it to your <code>.env</code> file, then restart.<br>'
            'Free keys at <strong>console.groq.com</strong>.</div>',
            unsafe_allow_html=True,
        )

    form_col, result_col = st.columns([3, 2], gap="large")

    with form_col:
        mode_sel = st.radio(
            "Input mode", ["✏ Paste Text", "📄 Upload File"],
            horizontal=True, label_visibility="collapsed", key="input_mode",
        )

        st.markdown('<div class="lbl" style="margin-top:12px;">Decision Text</div>', unsafe_allow_html=True)

        if mode_sel == "✏ Paste Text":
            decision_text = st.text_area(
                "text", label_visibility="collapsed", height=180,
                key="decision_input",
                placeholder=(
                    "Paste any rejection letter, loan denial, triage outcome, "
                    "or university decision here…\n\n"
                    "Tip — load an example from the sidebar →"
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
                        f'<div class="badge-ok" style="margin-bottom:8px;">✓ {len(ex):,} chars from {uf.name}</div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("Preview"):
                        st.text(ex[:600] + ("…" if len(ex) > 600 else ""))

        # Type + char counter
        tc1, tc2 = st.columns([2, 1])
        with tc1:
            opts = ["job", "loan", "medical", "university", "other"]
            cur  = st.session_state.get("dtype_sel", "job")
            idx  = opts.index(cur) if cur in opts else 0
            dtype = st.selectbox(
                "Type", opts, format_func=lambda x: TYPE_LABELS[x],
                index=idx, key="dtype_sel",
            )
        with tc2:
            n = len((decision_text or "").strip())
            if n > 150:   char_col, char_lbl = tok("--green"), "Ready"
            elif n > 50:  char_col, char_lbl = tok("--amber"), "Minimum"
            else:         char_col, char_lbl = tok("--red"),   "Too short"
            w = min(100, int(n / 3))
            st.markdown(
                f'<div style="margin-top:4px;">'
                f'<div class="char-row" style="color:{char_col};">'
                f'<span>{n:,} chars</span><span>{char_lbl}</span></div>'
                f'<div class="char-track"><div class="char-fill" style="width:{w}%;background:{char_col};"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Scan mode
        scan_mode = st.radio(
            "Scan mode",
            ["full", "quick"],
            format_func=lambda x: "⚡ Full Scan (3 Groq calls · detailed)" if x == "full" else "⚡ Quick Scan (1 call · faster)",
            horizontal=True,
            key="scan_mode",
        )

        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
        run_btn = st.button("⚡ Run Analysis", key="run_btn", disabled=not api_ok())

        # Bias dimension legend
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="lbl">Dimensions Detected</div>', unsafe_allow_html=True)
        st.markdown(
            "".join(f'<span class="chip chip-n" style="margin-bottom:4px;">{d}</span>' for d in BIAS_DIMS),
            unsafe_allow_html=True,
        )

    # ── Run logic ─────────────────────────────
    with result_col:
        if run_btn:
            dt = (decision_text or "").strip()
            if not dt:
                st.warning("⚠ Paste or upload a decision first.")
            else:
                th = services.hash_text(dt)
                cached = services.find_duplicate(th)

                if cached and not st.session_state.get("force_rerun"):
                    st.markdown(
                        '<div class="dup-warn">⚠ <div><strong>Identical text — showing cached result.</strong><br>'
                        'Click Re-run for a fresh analysis.</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("🔄 Re-run analysis", key="force_btn"):
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
                    st.session_state["appeal_letter"] = None

        report = st.session_state.get("last_report")
        dt     = st.session_state.get("last_text", "")

        if not report:
            st.markdown(
                '<div class="empty">'
                '<div class="empty-ico">⚖</div>'
                '<div class="empty-t">No analysis yet</div>'
                '<div class="empty-s">Paste a decision on the left and click Run Analysis.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
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

            # Verdict banner
            vcls  = "bias" if bias else "clean"
            vico  = "⚠" if bias else "✓"
            vtxt  = "Bias Detected" if bias else "No Bias Found"
            vsub  = "This decision shows discriminatory patterns." if bias else "No strong discriminatory signals detected."
            mbadge = f'<span class="mode-badge-quick">Quick</span>' if mode_ == "quick" else f'<span class="mode-badge-full">Full</span>'
            st.markdown(
                f'<div class="verdict-banner {vcls}">'
                f'<div style="font-size:2rem;line-height:1;margin-bottom:6px;">{vico}</div>'
                f'<div class="vb-title">{vtxt}</div>'
                f'<div class="vb-sub">{vsub}</div>'
                f'<div style="margin-top:8px;">{mbadge} {sev_badge(conf, bias, report.get("severity","low"))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Ring + types
            r1, r2 = st.columns([1, 2], gap="small")
            with r1:
                bt_ch = chips(btype) if btype else '<span class="chip chip-g">None</span>'
                aff_b = ""
                if aff:
                    aff_b = (
                        f'<div style="margin-top:10px;">'
                        f'<div class="card-lbl">Affected</div>'
                        f'<div style="font-size:.95rem;font-weight:700;color:{tok("--amber")};">{aff.title()}</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div class="card" style="text-align:center;padding:.9rem .7rem;">'
                    f'<div class="ring-wrap">{ring_svg(pct, bias, 110)}</div>'
                    f'{aff_b}</div>',
                    unsafe_allow_html=True,
                )
            with r2:
                st.markdown(
                    f'<div class="card" style="height:100%;">'
                    f'<div class="card-lbl">Bias Types</div>'
                    f'<div style="line-height:2;">{bt_ch}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Outcomes
            orig_cls = "err" if bias else "muted"
            st.markdown(
                f'<div class="card {orig_cls}">'
                f'<div class="card-lbl">Original Decision</div>'
                f'<div class="card-val mono lg">{orig.upper()}</div>'
                f'</div>'
                f'<div class="card ok">'
                f'<div class="card-lbl">Should Have Been</div>'
                f'<div class="card-val serif">{fair}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if evid:
                st.markdown(
                    f'<div class="card warn"><div class="card-lbl">Bias Evidence</div>'
                    f'<div class="card-val" style="font-size:.84rem;">{evid}</div></div>',
                    unsafe_allow_html=True,
                )

            # Timing
            if tm:
                st.markdown(timing_pills(tm), unsafe_allow_html=True)

            # Phrase highlighter
            if dt and (btype or report.get("bias_phrases")):
                st.markdown('<div class="lbl" style="margin-top:12px;">Highlighted Phrases</div>', unsafe_allow_html=True)
                hl = highlight(dt, report.get("bias_phrases", []), btype)
                st.markdown(
                    f'<div class="hl-box">{hl}</div>'
                    f'<div style="font-size:.68rem;color:{tok("--t3")};margin-top:3px;">Highlighted = potential bias proxies</div>',
                    unsafe_allow_html=True,
                )

            if expl:
                st.markdown('<div class="lbl" style="margin-top:12px;">Plain English</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="card warn"><div class="card-val">{expl}</div></div>', unsafe_allow_html=True)

            if laws:
                st.markdown('<div class="lbl" style="margin-top:12px;">Legal Frameworks</div>', unsafe_allow_html=True)
                law_rows = "".join(f'<div class="law-row"><span style="color:{tok("--accent")}">⚖</span>{l}</div>' for l in laws)
                st.markdown(f'<div class="card info">{law_rows}</div>', unsafe_allow_html=True)

            if recs:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="lbl">Recommended Next Steps</div>', unsafe_allow_html=True)
                for i, rec in enumerate(recs, 1):
                    st.markdown(
                        f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>',
                        unsafe_allow_html=True,
                    )

            # Feedback
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Feedback</div>', unsafe_allow_html=True)
            fb_comment = st.text_input("Comment (optional)", key="fb_comment", label_visibility="collapsed",
                                       placeholder="Optional: any notes on this analysis…")
            fb1, fb2, _ = st.columns([1, 1, 3])
            with fb1:
                if st.button("👍 Helpful", key="fb_y"):
                    services.save_feedback(report.get("id", ""), 1, fb_comment)
                    st.success("Thanks!")
            with fb2:
                if st.button("👎 Not helpful", key="fb_n"):
                    services.save_feedback(report.get("id", ""), 0, fb_comment)
                    st.info("Noted.")

            # Appeal
            if bias:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                st.markdown('<div class="lbl">Formal Appeal Letter</div>', unsafe_allow_html=True)
                if st.button("✉ Generate Appeal Letter", key="appeal_btn"):
                    with st.spinner("Drafting formal letter…"):
                        try:
                            letter = services.generate_appeal_letter(report, dt, dtype)
                            st.session_state["appeal_letter"] = letter
                        except Exception as e:
                            st.error(f"❌ {e}")
                if st.session_state.get("appeal_letter"):
                    letter = st.session_state["appeal_letter"]
                    st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                    st.download_button(
                        "↓ Download Letter",
                        data=letter,
                        file_name=f"appeal_{(report.get('id') or 'x')[:8]}.txt",
                        mime="text/plain", key="dl_letter",
                    )

            # Downloads
            st.markdown("<br>", unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    "↓ Full Report (.txt)",
                    data=txt_report(report, dt, dtype),
                    file_name=f"verdict_v11_{(report.get('id') or 'r')[:8]}.txt",
                    mime="text/plain", key="dl_rpt",
                )
            with dl2:
                st.download_button(
                    "↓ CSV",
                    data=to_csv([report]),
                    file_name=f"verdict_v11_{(report.get('id') or 'r')[:8]}.csv",
                    mime="text/csv", key="dl_csv_single",
                )

# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
elif view == "dashboard":
    st.markdown('<div class="page-heading">Analytics Dashboard</div>', unsafe_allow_html=True)
    hist = all_reports()

    if not hist:
        st.markdown(
            '<div class="empty">'
            '<div class="empty-ico">◎</div>'
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
        k1.metric("Total",        len(hist))
        k2.metric("Bias Rate",    f"{b_rate}%")
        k3.metric("Avg Conf",     f"{avg_c}%")
        k4.metric("Top Bias",     top_b)
        k5.metric("Avg Severity", avg_sev)
        k6.metric("Helpful %",    f"{fb['helpful_pct']}%" if fb["total"] else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        # Sparkline
        spark_scores = services.get_confidence_trend(30)
        if spark_scores:
            st.markdown('<div class="lbl">Confidence Trend (last 30 analyses)</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_sparkline(spark_scores), use_container_width=True, config={"displayModeBar": False})

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="lbl">Verdict Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_pie(len(b_reps), len(c_reps)), use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="lbl">Bias Type Frequency</div>', unsafe_allow_html=True)
            if all_bt:
                st.plotly_chart(chart_bar(all_bt), use_container_width=True, config={"displayModeBar": False})
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
            st.markdown('<div class="lbl">Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_radar(hist), use_container_width=True, config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="lbl">Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist if r.get("affected_characteristic")]
            if chars:
                st.plotly_chart(chart_bar(chars), use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No characteristic data yet.")

        st.markdown("<br>", unsafe_allow_html=True)
        dl1, _ = st.columns([1, 4])
        with dl1:
            st.download_button("↓ Export CSV", data=to_csv(hist),
                file_name=f"verdict_dash_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_dl")

        # Recent feedback comments
        if fb.get("recent_comments"):
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Recent Feedback Comments</div>', unsafe_allow_html=True)
            for c in fb["recent_comments"]:
                st.markdown(
                    f'<div class="card muted" style="margin-bottom:6px;">'
                    f'<div class="card-val" style="font-size:.82rem;">{c}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

# ══════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════
elif view == "history":
    st.markdown('<div class="page-heading">Analysis History</div>', unsafe_allow_html=True)
    hist = all_reports()

    if not hist:
        st.markdown(
            '<div class="empty"><div class="empty-ico">▤</div>'
            '<div class="empty-t">No history yet</div>'
            '<div class="empty-s">All past analyses appear here.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        f1, f2, f3 = st.columns([3, 1, 1])
        with f1:
            q = st.text_input("Search", placeholder="Search bias type, characteristic, outcome…", key="h_q")
        with f2:
            fv = st.selectbox("Verdict", ["All", "Bias", "No Bias"], key="h_v")
        with f3:
            sv = st.selectbox("Sort", ["Newest", "Oldest", "High Conf", "Low Conf"], key="h_s")

        d1c, d2c, _ = st.columns([1, 1, 2])
        with d1c: df_in = st.date_input("From", value=None, key="h_df")
        with d2c: dt_in = st.date_input("To",   value=None, key="h_dt")

        filt = hist[:]
        if fv == "Bias":     filt = [r for r in filt if r.get("bias_found")]
        elif fv == "No Bias": filt = [r for r in filt if not r.get("bias_found")]
        if q:
            ql = q.lower()
            filt = [r for r in filt
                    if ql in (r.get("affected_characteristic") or "").lower()
                    or any(ql in bt.lower() for bt in r.get("bias_types", []))
                    or ql in (r.get("original_outcome") or "").lower()
                    or ql in (r.get("explanation") or "").lower()]
        if df_in: filt = [r for r in filt if (r.get("created_at") or "")[:10] >= str(df_in)]
        if dt_in: filt = [r for r in filt if (r.get("created_at") or "")[:10] <= str(dt_in)]
        if sv == "Newest":      filt.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sv == "Oldest":    filt.sort(key=lambda r: r.get("created_at") or "")
        elif sv == "High Conf": filt.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
        else:                   filt.sort(key=lambda r: r.get("confidence_score", 0))

        hdr1, hdr2 = st.columns([3, 1])
        with hdr1:
            st.markdown(
                f'<div style="font-size:.75rem;color:{tok("--t3")};margin-bottom:10px;">'
                f'Showing {len(filt)} of {len(hist)} reports</div>',
                unsafe_allow_html=True,
            )
        with hdr2:
            st.download_button("↓ CSV", data=to_csv(filt),
                file_name=f"verdict_hist_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="hist_dl")

        for r in filt:
            bias    = r.get("bias_found", False)
            conf    = int(r.get("confidence_score", 0) * 100)
            aff     = r.get("affected_characteristic") or "—"
            created = (r.get("created_at") or "")[:16].replace("T", " ")
            ico     = "⚠" if bias else "✓"
            mode_lbl = "Quick" if r.get("mode") == "quick" else "Full"

            with st.expander(
                f'{ico} {"Bias" if bias else "No Bias"}  ·  {conf}%  ·  {aff}  ·  {created}  [{mode_lbl}]',
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
                        f'<div class="card muted" style="margin-top:6px;">'
                        f'<div class="card-lbl">Original Outcome</div>'
                        f'<div class="card-val mono">{(r.get("original_outcome") or "N/A").upper()}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    st.markdown(
                        f'<div class="card warn">'
                        f'<div class="card-lbl">Bias Types</div>'
                        f'<div class="card-val">{chips(r.get("bias_types", []))}</div>'
                        f'</div>'
                        f'<div class="card ok" style="margin-top:6px;">'
                        f'<div class="card-lbl">Fair Outcome</div>'
                        f'<div class="card-val serif">{r.get("fair_outcome") or "N/A"}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="card muted" style="margin-top:6px;">'
                        f'<div class="card-lbl">Explanation</div>'
                        f'<div class="card-val" style="font-size:.84rem;">{r["explanation"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                laws = r.get("legal_frameworks", [])
                if laws:
                    st.markdown(
                        f'<div class="card info" style="margin-top:6px;">'
                        f'<div class="card-lbl">Legal Frameworks</div>'
                        f'<div>{chips(laws, "chip-b")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                recs = r.get("recommendations", [])
                if recs:
                    st.markdown('<div class="lbl" style="margin-top:10px;">Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs, 1):
                        st.markdown(
                            f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>',
                            unsafe_allow_html=True,
                        )
                tm = r.get("timing_ms", {})
                if tm:
                    st.markdown(timing_pills(tm), unsafe_allow_html=True)
                st.caption(f"ID: {r.get('id','N/A')}  ·  Severity: {(r.get('severity') or '—').upper()}")
                st.download_button(
                    f"↓ Report (txt)",
                    data=txt_report(r, "", r.get("decisionType", "other")),
                    file_name=f"verdict_{(r.get('id') or 'x')[:8]}.txt",
                    mime="text/plain", key=f"dl_{r.get('id','x')}",
                )

# ══════════════════════════════════════════════
# COMPARE
# ══════════════════════════════════════════════
elif view == "compare":
    st.markdown('<div class="page-heading">Compare Two Decisions</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-sub">Analyse two decisions side-by-side to surface differential bias patterns.</div>',
        unsafe_allow_html=True,
    )
    if not api_ok(): st.markdown('<div class="key-err">⚠ API key missing — see Settings.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="lbl">Decision A</div>', unsafe_allow_html=True)
        ct1  = st.text_area("A", height=120, label_visibility="collapsed", placeholder="Paste first decision…", key="cmp1")
        ctp1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                             format_func=lambda x: TYPE_LABELS[x], label_visibility="collapsed", key="ct1")
    with c2:
        st.markdown('<div class="lbl">Decision B</div>', unsafe_allow_html=True)
        ct2  = st.text_area("B", height=120, label_visibility="collapsed", placeholder="Paste second decision…", key="cmp2")
        ctp2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                             format_func=lambda x: TYPE_LABELS[x], label_visibility="collapsed", key="ct2")

    scan_cmp = st.radio("Scan mode", ["full","quick"],
                        format_func=lambda x: "Full" if x == "full" else "Quick",
                        horizontal=True, key="cmp_scan")

    cmp_btn = st.button("⇔ Compare Both", key="cmp_btn", disabled=not api_ok())

    if cmp_btn:
        if not ct1.strip() or not ct2.strip():
            st.warning("⚠ Fill in both decisions.")
        else:
            with st.spinner("Analysing both decisions…"):
                ra, ea = run_analysis(ct1, ctp1, mode=scan_cmp)
                rb, eb = run_analysis(ct2, ctp2, mode=scan_cmp)
            if ea: st.error(f"Decision A error: {ea}")
            if eb: st.error(f"Decision B error: {eb}")

            if ra and rb:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                ba, bb = ra.get("bias_found"), rb.get("bias_found")
                ca, cb = ra.get("confidence_score", 0), rb.get("confidence_score", 0)

                if ba and bb:
                    win = "A" if ca >= cb else "B"
                    msg = f"Both show bias — Decision {win} has higher confidence ({int(max(ca,cb)*100)}%)"
                elif ba:  msg = "Decision A shows bias · Decision B appears fair"
                elif bb:  msg = "Decision B shows bias · Decision A appears fair"
                else:     msg = "Neither decision shows discriminatory patterns"
                st.markdown(f'<div class="winner-bar">{msg}</div>', unsafe_allow_html=True)

                set_a, set_b = set(ra.get("bias_types", [])), set(rb.get("bias_types", []))
                only_a = set_a - set_b; only_b = set_b - set_a; shared = set_a & set_b
                if set_a or set_b:
                    diff_html = '<div class="lbl">Bias Type Comparison</div><div style="margin-bottom:14px;">'
                    for t in sorted(shared): diff_html += f'<span class="diff-badge diff-shared">Both: {t}</span>'
                    for t in sorted(only_a): diff_html += f'<span class="diff-badge diff-only-a">A: {t}</span>'
                    for t in sorted(only_b): diff_html += f'<span class="diff-badge diff-only-b">B: {t}</span>'
                    diff_html += "</div>"
                    st.markdown(diff_html, unsafe_allow_html=True)

                vc1, vc2 = st.columns(2, gap="large")
                for col, r, lbl in [(vc1, ra, "A"), (vc2, rb, "B")]:
                    with col:
                        b   = r.get("bias_found", False)
                        vcls_ = "bias" if b else "clean"
                        vt_   = "Bias Detected" if b else "No Bias Found"
                        st.markdown(
                            f'<div class="verdict-banner {vcls_}" style="margin-bottom:10px;">'
                            f'<div class="vb-title">Decision {lbl}</div>'
                            f'<div class="vb-sub">{vt_}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.plotly_chart(chart_gauge(r.get("confidence_score", 0), b),
                                        use_container_width=True, config={"displayModeBar": False})
                        st.markdown(chips(r.get("bias_types", [])), unsafe_allow_html=True)
                        st.markdown(sev_badge(r.get("confidence_score", 0), b, r.get("severity","low")), unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="card ok" style="margin-top:8px;">'
                            f'<div class="card-lbl">Fair Outcome</div>'
                            f'<div class="card-val serif">{r.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if r.get("explanation"):
                            st.markdown(
                                f'<div class="card warn">'
                                f'<div class="card-lbl">What Went Wrong</div>'
                                f'<div class="card-val" style="font-size:.83rem;">{r["explanation"]}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

# ══════════════════════════════════════════════
# BATCH
# ══════════════════════════════════════════════
elif view == "batch":
    st.markdown('<div class="page-heading">Batch Processing</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-sub">Analyse up to 10 decisions at once. '
        f'Separate with <code style="background:{tok("--surf2")};padding:1px 6px;border-radius:4px;font-family:var(--ff-mono)">---</code> '
        f'or upload a CSV with a <code style="background:{tok("--surf2")};padding:1px 6px;border-radius:4px;font-family:var(--ff-mono)">text</code> column.</div>',
        unsafe_allow_html=True,
    )
    if not api_ok(): st.markdown('<div class="key-err">⚠ API key missing — see Settings.</div>', unsafe_allow_html=True)

    bmode = st.radio("Batch input", ["✏ Paste Text", "📊 Upload CSV"],
                     horizontal=True, label_visibility="collapsed", key="bm")
    if bmode == "✏ Paste Text":
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
                    st.markdown(f'<div class="badge-ok">✓ {len(blocks)} rows loaded</div>', unsafe_allow_html=True)
                else:
                    st.error("CSV must have a 'text' column.")
            except Exception as e:
                st.error(f"❌ {e}")

    bc1, bc2, bc3 = st.columns([2, 1, 1])
    with bc1:
        btype = st.selectbox("Decision type (all)", ["job","loan","medical","university","other"],
                             format_func=lambda x: TYPE_LABELS[x],
                             label_visibility="collapsed", key="b_type")
    with bc2:
        scan_b = st.radio("Mode", ["full","quick"], horizontal=True,
                          format_func=lambda x: "Full" if x == "full" else "Quick", key="b_scan")
    with bc3:
        brun = st.button("⊞ Run Batch", key="b_run", disabled=not api_ok())

    if blocks:
        st.markdown(
            f'<div style="font-size:.78rem;color:{tok("--accent")};font-weight:600;margin-top:4px;">'
            f'● {len(blocks)} decision{"s" if len(blocks)!=1 else ""} queued</div>',
            unsafe_allow_html=True,
        )

    if brun:
        if not blocks:
            st.warning("⚠ No decisions found.")
        elif len(blocks) > 10:
            st.warning("⚠ Batch limit is 10 decisions.")
        else:
            prog    = st.progress(0)
            status  = st.empty()
            results = []
            t0      = time.time()

            for i, blk in enumerate(blocks):
                elapsed = time.time() - t0
                eta     = (elapsed / (i + 1)) * (len(blocks) - i - 1) if i > 0 else 0
                eta_str = f" · ETA ~{int(eta)}s" if eta > 1 else ""
                status.markdown(
                    f'<div style="font-size:.8rem;color:{tok("--accent")};font-weight:600;">'
                    f'Analysing {i+1} / {len(blocks)}{eta_str}…</div>',
                    unsafe_allow_html=True,
                )
                rep, err = run_analysis(blk, btype, mode=scan_b)
                results.append({"text": blk, "report": rep, "error": err})
                prog.progress((i + 1) / len(blocks))

            prog.empty(); status.empty()
            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            b_c = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            c_c = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            e_c = sum(1 for r in results if r["error"])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", len(results))
            m2.metric("Bias Detected", b_c)
            m3.metric("No Bias", c_c)
            m4.metric("Errors", e_c)

            rows = []
            for i, res in enumerate(results, 1):
                rep, err = res["report"], res["error"]
                if err:
                    rows.append({"#": i, "Verdict": "ERROR", "Conf": "—",
                                 "Bias Types": err[:50], "Severity": "—", "Affected": "—"})
                elif rep:
                    rows.append({
                        "#":          i,
                        "Verdict":    "Bias" if rep.get("bias_found") else "Clean",
                        "Conf":       f"{int(rep.get('confidence_score', 0) * 100)}%",
                        "Bias Types": ", ".join(rep.get("bias_types", [])) or "None",
                        "Severity":   (rep.get("severity") or "—").title(),
                        "Affected":   rep.get("affected_characteristic") or "—",
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_r = [r["report"] for r in results if r["report"]]
            if all_r:
                dl1, _ = st.columns([1, 3])
                with dl1:
                    st.download_button("↓ Download CSV",
                        data=to_csv(all_r),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="b_dl")

            st.markdown('<div class="lbl" style="margin-top:1.25rem;">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep, err = res["report"], res["error"]
                lbl = f"Decision {i}"
                if err: lbl += " — Error"
                elif rep:
                    vs   = "Bias" if rep.get("bias_found") else "Clean"
                    conf_ = int(rep.get("confidence_score", 0) * 100)
                    lbl  += f" — {vs} ({conf_}%)"
                with st.expander(lbl, expanded=False):
                    preview = res["text"][:250] + ("…" if len(res["text"]) > 250 else "")
                    st.markdown(f'<div class="preview-box">{preview}</div>', unsafe_allow_html=True)
                    if err:
                        st.error(err)
                    elif rep:
                        b_ = rep.get("bias_found", False)
                        st.markdown(
                            f'<div class="card {"err" if b_ else "ok"}">'
                            f'<div class="card-lbl">Verdict</div>'
                            f'<div class="card-val mono">{"⚠ Bias Detected" if b_ else "✓ No Bias Found"}</div>'
                            f'</div>'
                            f'<div class="card warn" style="margin-top:6px;">'
                            f'<div class="card-lbl">Bias Types</div>'
                            f'<div>{chips(rep.get("bias_types",[]))}</div>'
                            f'</div>'
                            f'<div class="card ok" style="margin-top:6px;">'
                            f'<div class="card-lbl">Fair Outcome</div>'
                            f'<div class="card-val serif">{rep.get("fair_outcome") or "N/A"}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if rep.get("legal_frameworks"):
                            st.markdown(
                                f'<div class="card info" style="margin-top:6px;">'
                                f'<div class="card-lbl">Legal Frameworks</div>'
                                f'<div>{chips(rep["legal_frameworks"],"chip-b")}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

# ══════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════
elif view == "settings":
    st.markdown('<div class="page-heading">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Verdict Watch V11 — configuration and diagnostics.</div>', unsafe_allow_html=True)

    sc1, sc2 = st.columns(2, gap="large")
    with sc1:
        st.markdown('<div class="lbl">API & Model</div>', unsafe_allow_html=True)
        ko   = api_ok()
        k_st = "✓ Set — loaded from .env" if ko else "✗ Not set"
        k_cl = "ok" if ko else "err"
        p_cl = "ok" if PDF_SUPPORT else "warn"
        p_st = "✓ PyMuPDF installed" if PDF_SUPPORT else "Not installed — pip install PyMuPDF"
        st.markdown(
            f'<div class="card {k_cl}"><div class="card-lbl">Groq API Key</div><div class="card-val mono">{k_st}</div></div>'
            f'<div class="card"><div class="card-lbl">Model</div><div class="card-val mono">{services._MODEL}</div></div>'
            f'<div class="card"><div class="card-lbl">Pipeline</div><div class="card-val mono">3-step · temp 0.1 · {services._MAX_RETRIES}× retry</div></div>'
            f'<div class="card {p_cl}"><div class="card-lbl">PDF Support</div><div class="card-val mono">{p_st}</div></div>',
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
            f'<div class="card"><div class="card-lbl">Total Reports</div><div class="card-val mono lg">{len(all_r)}</div></div>'
            f'<div class="card"><div class="card-lbl">Database URL</div><div class="card-val mono" style="font-size:.74rem;">{db_url}</div></div>'
            f'<div class="card info"><div class="card-lbl">User Feedback</div><div class="card-val mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="lbl" style="margin-top:14px;">V11 Changelog</div>', unsafe_allow_html=True)
        for ico, name, desc in [
            ("✦", "Quick Scan Mode",       "Single Groq call, ~3× faster"),
            ("✦", "Dark Mode Toggle",      "Sidebar switch, all tokens adapt"),
            ("✦", "Confidence Sparkline",  "Trend of last 30 scores on dashboard"),
            ("✦", "Per-call Timing",       "ms per pipeline step shown on report"),
            ("✦", "Feedback Comments",     "Text comments stored alongside rating"),
            ("✦", "History Download",      "Per-row .txt download in History tab"),
            ("✦", "API /appeal Endpoint",  "Appeal now callable via FastAPI"),
            ("✦", "Idempotent Migrations", "Schema migrations safe to re-run"),
            ("✦", "Cleaner Architecture",  "services / api / streamlit all refactored"),
        ]:
            st.markdown(
                f'<div class="feature-row">'
                f'<span><span class="feature-check">{ico}</span><span class="feature-name">{name}</span></span>'
                f'<span class="feature-desc">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════
# ABOUT
# ══════════════════════════════════════════════
elif view == "about":
    st.markdown('<div class="page-heading">About Verdict Watch</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-sub">'
        f'Enterprise-grade AI bias detection for automated decisions. '
        f'V11 — Editorial Dark-Ink Edition.'
        f'</div>',
        unsafe_allow_html=True,
    )

    ab1, ab2 = st.columns([1.6, 1], gap="large")
    with ab1:
        st.markdown(
            f'<div class="card" style="background:{tok("--ink")};border-color:{tok("--ink")};margin-bottom:12px;">'
            f'<div style="font-family:var(--ff-serif);font-size:1.15rem;color:white;margin-bottom:6px;">What is Verdict Watch?</div>'
            f'<div style="font-size:.83rem;color:rgba(255,255,255,.6);line-height:1.75;">'
            f'A 3-step Groq + Llama 3.3 70B pipeline that extracts decision criteria, '
            f'detects discriminatory patterns across 7 bias dimensions, cites relevant laws, '
            f'and generates the fair outcome you deserved — all from pasting a rejection letter.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="lbl">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Gender Bias",             "Gender, name, or parental status as a decision factor"),
            ("Age Discrimination",      "Unfair weighting of age group or seniority"),
            ("Racial / Ethnic Bias",    "Name-based, nationality, or origin profiling"),
            ("Geographic Redlining",    "Zip code or district as a discriminatory proxy"),
            ("Socioeconomic Bias",      "Employment sector or credit score over-weighting"),
            ("Language Discrimination", "Primary language used against applicants"),
            ("Insurance Classification","Insurance tier used to rank treatment priority"),
        ]:
            st.markdown(
                f'<div class="card" style="margin-bottom:5px;">'
                f'<div class="card-lbl">{name}</div>'
                f'<div class="card-val" style="font-size:.83rem;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="lbl">Tech Stack</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Groq",              "LLM inference"),
            ("Llama 3.3 70B",     "Language model"),
            ("FastAPI",           "REST API"),
            ("Streamlit ≥ 1.35",  "Web UI"),
            ("SQLAlchemy + SQLite","Database"),
            ("Plotly",            "Charts"),
            ("DM Serif Display",  "Heading font"),
            ("Syne",              "UI font"),
            ("JetBrains Mono",    "Data font"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid {tok("--surf3")};">'
                f'<span style="font-size:.83rem;font-weight:500;color:{tok("--t1")};">{name}</span>'
                f'<span style="font-size:.74rem;color:{tok("--t3")};">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="card warn">'
            f'<div class="card-lbl">⚠ Disclaimer</div>'
            f'<div class="card-val" style="font-size:.8rem;">'
            f'Not legal advice. Built for educational awareness only. '
            f'Consult a qualified legal professional for discrimination claims.'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="text-align:center;font-size:.7rem;color:{tok("--t3")};">'
            f'Verdict Watch V11 · Powered by Groq / Llama 3.3 70B'
            f'</div>',
            unsafe_allow_html=True,
        )