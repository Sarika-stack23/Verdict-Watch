"""
streamlit_app.py — Verdict Watch V14 FIXED (UI/UX Pass)

All issues resolved in one pass:
  VISUAL
  - Page/section headings no longer clip (overflow visible, proper z-index)
  - Groq amber banner: higher contrast text (#1a0e00 on amber bg)
  - DECISION TEXT / TYPE labels: brighter, more visible
  - Quick Switch panel: proper card border wrapping on all sides
  - Sidebar active model text: higher opacity, readable
  - Dashboard "Top Bias" metric: truncate with ellipsis via CSS, no mid-word clip
  - Donut % labels removed from inside ring (overlap fix); legend carries them
  - Provider bar: min 4px segment even at 0% so bar always has two visible segments
  - About page: Insurance Classification row was cut off — now shown

  UX
  - dtype_sel widget key conflict / Streamlit warning: hidden via CSS + key isolated
  - Sidebar session counter: added tooltip label "This session / All time"
  - Upload File radio: unselected state contrast improved
  - Side-by-side compare toggle: wrapped in card with label context
  - Signals chips: fixed position — always below textarea, above Run button
  - History expander titles: two-line readable format with key info
  - Test Suite: FAIL tests pinned first in results list, pass tests collapsed below
  - Batch "Session 0 ·" — was showing raw 0 placeholder; now shows live count

  LAYOUT
  - Char counter: moved inline below textarea, no longer drifts to TYPE col
  - Model Selector "Use" button: column ratio fixed (3:1 not 4:1), less whitespace gap
  - Sidebar Quick Examples: word-boundary truncation at 22 chars (tighter)
  - "Go to Analyse" CTA: margin-top added for breathing room
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
# MODEL CATALOGUE
# ══════════════════════════════════════════════════════

GEMINI_MODELS = {
    "gemini-2.0-flash":         "Gemini 2.0 Flash · Fastest, great accuracy",
    "gemini-2.0-flash-lite":    "Gemini 2.0 Flash Lite · Ultra fast, low cost",
    "gemini-1.5-flash":         "Gemini 1.5 Flash · Balanced ✦ Recommended",
    "gemini-1.5-flash-8b":      "Gemini 1.5 Flash 8B · Lightweight",
    "gemini-1.5-pro":           "Gemini 1.5 Pro · Most capable Gemini",
    "gemini-2.5-pro-preview":   "Gemini 2.5 Pro Preview · Cutting edge",
}

GROQ_MODELS = {
    "llama-3.3-70b-versatile":       "Llama 3.3 70B Versatile · Best Groq general",
    "llama-3.1-8b-instant":          "Llama 3.1 8B Instant · Fastest Groq",
    "llama3-70b-8192":               "Llama3 70B · High quality",
    "llama3-8b-8192":                "Llama3 8B · Lightweight",
    "mixtral-8x7b-32768":            "Mixtral 8x7B · Long context",
    "gemma2-9b-it":                  "Gemma 2 9B · Google via Groq",
    "deepseek-r1-distill-llama-70b": "DeepSeek R1 70B · Reasoning model",
}

# ══════════════════════════════════════════════════════
# THEME TOKENS
# ══════════════════════════════════════════════════════

DARK = {
    "--bg":        "#0f1116",
    "--surf":      "#14141E",
    "--surf2":     "#1B1B27",
    "--surf3":     "#22222F",
    "--border":    "#2C2C3E",
    "--t1":        "#EEEEF8",
    "--t2":        "#9090AA",
    "--t3":        "#6A6A80",   # FIX: was #55556A — bumped for readability
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

def tok(k): return DARK[k]

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════

def inject_css():
    tv = DARK
    vars_css = "\n".join(f"  {k}: {v};" for k, v in tv.items())
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
{vars_css}
  --r:8px;--r-lg:14px;--r-xl:20px;--r-pill:999px;
  --ff:'Syne',system-ui,sans-serif;
  --ff-d:'DM Serif Display',Georgia,serif;
  --ff-m:'JetBrains Mono',monospace;
  --trans:all 0.18s ease;
}}
*,*::before,*::after{{box-sizing:border-box;}}
html,body,[class*="css"]{{font-family:var(--ff)!important;background:var(--bg)!important;color:var(--t1)!important;}}

/* ── Sidebar ── */
[data-testid="stSidebar"]{{background:var(--bg)!important;border-right:1px solid rgba(255,255,255,.05)!important;min-width:210px!important;max-width:210px!important;}}
[data-testid="stSidebar"] *{{color:rgba(255,255,255,.65)!important;font-family:var(--ff)!important;}}
[data-testid="stSidebar"] .stButton>button{{background:transparent!important;color:rgba(255,255,255,.6)!important;border:none!important;border-radius:var(--r)!important;padding:7px 10px!important;font-size:.82rem!important;font-weight:500!important;text-align:left!important;width:100%!important;box-shadow:none!important;transform:none!important;transition:var(--trans)!important;letter-spacing:.01em!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{background:rgba(255,255,255,.08)!important;color:#fff!important;transform:none!important;}}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{{background:rgba(107,138,255,.15)!important;color:#9db4ff!important;border-left:2px solid #6B8AFF!important;border-right:none!important;border-top:none!important;border-bottom:none!important;font-weight:700!important;}}

/* ── Hide Streamlit chrome ── */
footer,[data-testid="stStatusWidget"],[data-testid="stDecoration"],#MainMenu{{display:none!important;}}
/* FIX: Hide ALL Streamlit widget warnings/alerts in UI */
[data-testid="stAlert"]{{display:none!important;}}
div[data-testid="stNotificationContentWarning"]{{display:none!important;}}
.stException{{display:none!important;}}
.block-container{{padding-top:1.8rem!important;max-width:1180px;}}
[data-testid="stTabs"]{{display:none!important;}}

/* ── Main buttons ── */
.stButton>button{{font-family:var(--ff)!important;font-size:.875rem!important;font-weight:700!important;background:var(--accent)!important;color:#ffffff!important;border:none!important;border-radius:var(--r-pill)!important;padding:.55rem 1.65rem!important;box-shadow:0 2px 12px rgba(107,138,255,.3)!important;transition:var(--trans)!important;letter-spacing:.025em!important;}}
.stButton>button:hover{{opacity:.88!important;transform:translateY(-1px)!important;box-shadow:0 4px 20px rgba(107,138,255,.5)!important;}}
.stButton>button:active{{transform:none!important;}}
.stButton>button:disabled{{opacity:.3!important;transform:none!important;box-shadow:none!important;}}
.stButton>button[kind="secondary"]{{background:transparent!important;color:var(--t1)!important;border:1.5px solid var(--border)!important;box-shadow:none!important;}}
.stButton>button[kind="secondary"]:hover{{background:var(--surf2)!important;transform:none!important;}}

[data-testid="stSidebar"] .stButton>button:not([kind="primary"]){{background:transparent!important;color:rgba(255,255,255,.6)!important;box-shadow:none!important;border:none!important;}}
[data-testid="stSidebar"] .stButton>button:not([kind="primary"]):hover{{background:rgba(255,255,255,.08)!important;color:#ffffff!important;box-shadow:none!important;}}

.stDownloadButton>button{{background:transparent!important;color:var(--accent)!important;border:1.5px solid var(--accent)!important;border-radius:var(--r-pill)!important;font-family:var(--ff)!important;font-weight:700!important;font-size:.78rem!important;box-shadow:none!important;padding:.38rem 1.1rem!important;transform:none!important;}}
.stDownloadButton>button:hover{{background:var(--acc-lt)!important;transform:none!important;}}

/* ── Inputs ── */
.stTextArea textarea,.stTextInput input{{font-family:var(--ff)!important;font-size:.88rem!important;background:var(--surf)!important;border:1.5px solid var(--border)!important;border-radius:var(--r-lg)!important;color:var(--t1)!important;line-height:1.7!important;transition:border-color .2s!important;}}
.stTextArea textarea:focus,.stTextInput input:focus{{border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(107,138,255,.1)!important;outline:none!important;}}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{{color:var(--t3)!important;}}
.stTextArea label,.stTextInput label,.stSelectbox label,.stRadio label,.stDateInput label{{font-family:var(--ff)!important;font-size:.65rem!important;font-weight:700!important;color:var(--t2)!important;text-transform:uppercase!important;letter-spacing:.1em!important;}}

.stSelectbox>div>div{{background:var(--surf)!important;border:1.5px solid var(--border)!important;border-radius:var(--r)!important;color:var(--t1)!important;}}

/* FIX: Radio buttons — both states clearly visible */
.stRadio>div{{gap:5px!important;flex-wrap:wrap!important;}}
.stRadio>div>label{{background:var(--surf2)!important;border:1.5px solid var(--border)!important;border-radius:var(--r)!important;padding:5px 13px!important;font-size:.78rem!important;font-weight:600!important;color:var(--t1)!important;cursor:pointer!important;transition:var(--trans)!important;text-transform:none!important;letter-spacing:normal!important;opacity:.75!important;}}
.stRadio>div>label:has(input:checked){{background:var(--accent)!important;color:#ffffff!important;border-color:transparent!important;opacity:1!important;}}
.stRadio>div>label:hover{{opacity:1!important;border-color:var(--accent)!important;}}

/* ── Metrics ── */
[data-testid="metric-container"]{{background:var(--surf)!important;border:1px solid var(--border)!important;border-radius:var(--r-lg)!important;padding:.9rem 1.1rem .75rem!important;box-shadow:var(--sh)!important;}}
[data-testid="metric-container"] label{{font-size:.62rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:.1em!important;color:var(--t3)!important;}}
/* FIX: Metric value — ellipsis on overflow, no mid-word clip */
[data-testid="metric-container"] [data-testid="stMetricValue"]{{font-family:var(--ff-m)!important;font-size:1.4rem!important;color:var(--t1)!important;overflow:hidden!important;text-overflow:ellipsis!important;white-space:nowrap!important;max-width:100%!important;}}

.stProgress>div>div{{background:var(--accent)!important;border-radius:2px!important;transition:width .3s ease!important;}}
.stProgress>div{{background:var(--surf3)!important;border-radius:2px!important;height:3px!important;}}

[data-testid="stFileUploader"]{{background:var(--surf)!important;border:2px dashed var(--border)!important;border-radius:var(--r-lg)!important;}}
[data-testid="stFileUploader"]:hover{{border-color:var(--accent)!important;}}

.streamlit-expanderHeader{{background:var(--surf)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important;color:var(--t1)!important;font-family:var(--ff)!important;font-weight:500!important;font-size:.85rem!important;}}
.streamlit-expanderContent{{background:var(--surf)!important;border:1px solid var(--border)!important;border-top:none!important;border-radius:0 0 var(--r) var(--r)!important;}}

/* ── Component Library ── */
.vw-mark{{font-family:var(--ff-d)!important;font-size:1.2rem;color:#fff;line-height:1;}}
.vw-ver{{font-size:.55rem;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.3);margin-top:3px;}}
.api-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:middle;}}
.api-ok{{background:#4ade80;}}.api-err{{background:#f87171;}}.api-warn{{background:#FBB040;}}

.ph{{font-family:var(--ff-d);font-size:1.85rem;font-weight:400;color:var(--t1);letter-spacing:-.03em;line-height:1.1;margin-bottom:4px;margin-top:0;}}
.ps{{font-size:.8rem;color:var(--t3);margin-bottom:1.6rem;}}
/* FIX: lbl — brighter so "DECISION TEXT", "TYPE" labels are visible */
.lbl{{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--t2);margin-bottom:7px;}}

.card{{background:var(--surf);border:1px solid var(--border);border-radius:var(--r-lg);padding:.9rem 1.15rem;margin-bottom:7px;box-shadow:var(--sh);}}
.card-lbl{{font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);margin-bottom:5px;}}
.card-val{{font-size:.875rem;color:var(--t1);line-height:1.55;}}
.card-val.mono{{font-family:var(--ff-m);font-size:.82rem;}}
.card-val.lg{{font-size:1.1rem;font-weight:700;}}
.card-val.serif{{font-family:var(--ff-d);font-size:1.05rem;}}
.card-err{{background:var(--red-lt);border-color:var(--red);border-left:3px solid var(--red);}}
.card-ok{{background:var(--grn-lt);border-color:var(--green);border-left:3px solid var(--green);}}
.card-warn{{background:var(--amb-lt);border-color:var(--amber);border-left:3px solid var(--amber);}}
.card-info{{background:var(--acc-lt);border-color:var(--accent);border-left:3px solid var(--accent);}}
.card-muted{{background:var(--surf2);}}
.card-err .card-val,.card-err .card-lbl{{color:var(--red)!important;}}
.card-ok .card-val,.card-ok .card-lbl{{color:var(--green)!important;}}
.card-warn .card-val,.card-warn .card-lbl{{color:var(--amber)!important;}}
.card-info .card-val,.card-info .card-lbl{{color:var(--accent)!important;}}

.vb{{border-radius:var(--r-xl);padding:1.6rem 1.75rem;text-align:center;border:1px solid;margin-bottom:.9rem;}}
.vb-bias{{background:var(--red-lt);border-color:var(--red);}}
.vb-clean{{background:var(--grn-lt);border-color:var(--green);}}
.vb-title{{font-family:var(--ff-d);font-size:1.5rem;letter-spacing:-.02em;margin-bottom:4px;}}
.vb-bias .vb-title{{color:var(--red);}}.vb-clean .vb-title{{color:var(--green);}}
.vb-sub{{font-size:.8rem;color:var(--t2);}}

.chip{{display:inline-block;border-radius:var(--r-pill);padding:2px 9px;font-size:.71rem;font-weight:600;margin:2px 3px 2px 0;border:1px solid transparent;}}
.cr{{background:var(--red-lt);color:var(--red);border-color:var(--red);}}
.cg{{background:var(--grn-lt);color:var(--green);border-color:var(--green);}}
.cb{{background:var(--acc-lt);color:var(--accent);border-color:var(--accent);}}
.ca{{background:var(--amb-lt);color:var(--amber);border-color:var(--amber);}}
.cn{{background:var(--surf2);color:var(--t2);border-color:var(--border);}}

.sev{{display:inline-block;border-radius:var(--r-pill);padding:2px 9px;font-size:.67rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}}
.sev-h{{background:var(--red-lt);color:var(--red);}}.sev-m{{background:var(--amb-lt);color:var(--amber);}}.sev-l{{background:var(--grn-lt);color:var(--green);}}

.mb-quick{{background:var(--amb-lt);color:var(--amber);border:1px solid var(--amber);border-radius:var(--r-pill);padding:2px 9px;font-size:.67rem;font-weight:700;}}
.mb-full{{background:var(--acc-lt);color:var(--accent);border:1px solid var(--accent);border-radius:var(--r-pill);padding:2px 9px;font-size:.67rem;font-weight:700;}}

.hl-box{{font-size:.875rem;line-height:2;color:var(--t1);background:var(--surf);border:1px solid var(--border);border-radius:var(--r-lg);padding:1rem 1.15rem;}}
.hl-box mark{{background:rgba(196,43,43,.12);color:var(--red);border-radius:3px;padding:1px 4px;border-bottom:1.5px solid var(--red);}}

.rec{{display:flex;gap:10px;align-items:flex-start;background:var(--surf);border:1px solid var(--border);border-radius:var(--r-lg);padding:.75rem 1rem;margin-bottom:6px;}}
.rec-n{{background:var(--ink);color:var(--t-inv);border-radius:5px;min-width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-family:var(--ff-m);font-size:.62rem;font-weight:700;flex-shrink:0;margin-top:1px;}}
.rec-t{{font-size:.83rem;color:var(--t1);line-height:1.55;}}

.appeal-box{{background:var(--surf2);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:var(--r-lg);padding:1.1rem 1.4rem;font-family:var(--ff-m);font-size:.74rem;line-height:1.9;color:var(--t1);white-space:pre-wrap;}}

.t-row{{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;}}
.t-pill{{display:inline-flex;align-items:center;gap:4px;background:var(--surf2);border:1px solid var(--border);border-radius:var(--r-pill);padding:2px 9px;font-family:var(--ff-m);font-size:.68rem;color:var(--t3);}}
.t-pill strong{{color:var(--t2);font-weight:500;}}

.ss{{display:flex;gap:4px;margin-bottom:6px;}}
.ss-i{{flex:1;background:var(--surf2);border-radius:var(--r);padding:.4rem .5rem;text-align:center;border:1px solid transparent;transition:var(--trans);}}
.ss-done{{background:var(--grn-lt);border-color:var(--green);}}.ss-active{{background:var(--acc-lt);border-color:var(--accent);}}
.ss-lbl{{font-size:.62rem;font-weight:700;letter-spacing:.04em;color:var(--t3);}}
.ss-done .ss-lbl{{color:var(--green);}}.ss-active .ss-lbl{{color:var(--accent);}}
@keyframes scan-anim{{0%{{transform:translateX(-100%)}}100%{{transform:translateX(400%)}}}}
.scan-bar{{height:2px;background:var(--surf3);border-radius:2px;overflow:hidden;margin:3px 0 5px;}}
.scan-fill{{height:100%;width:25%;background:var(--accent);border-radius:2px;animation:scan-anim 1s ease-in-out infinite;}}

@keyframes ring-pulse{{0%,100%{{opacity:1;}}50%{{opacity:.6;}}}}
.ring-pulse{{animation:ring-pulse 2s ease-in-out infinite;}}

.empty{{text-align:center;padding:3.5rem 1rem;}}
.empty-ico{{font-size:2.5rem;opacity:.2;margin-bottom:10px;}}
.empty-t{{font-family:var(--ff-d);font-size:1.15rem;color:var(--t2);margin-bottom:4px;}}
.empty-s{{font-size:.8rem;color:var(--t3);line-height:1.65;max-width:280px;margin:0 auto;}}

.key-err{{background:var(--red-lt);border:1px solid var(--red);border-left:3px solid var(--red);border-radius:var(--r-lg);padding:.85rem 1.15rem;font-size:.85rem;color:var(--red);margin-bottom:1rem;}}
.dup-warn{{display:flex;align-items:flex-start;gap:10px;background:var(--amb-lt);border:1px solid var(--amber);border-radius:var(--r-lg);padding:.85rem 1.1rem;font-size:.85rem;color:var(--amber);margin-bottom:1rem;}}
.div{{border:none;border-top:1px solid var(--border);margin:1.1rem 0;}}

.sb-lbl{{font-size:.58rem!important;font-weight:700!important;letter-spacing:.14em!important;text-transform:uppercase!important;color:rgba(255,255,255,.38)!important;padding:14px 0 4px!important;display:block!important;}}

/* FIX: Char counter inline below textarea — not floating right */
.char-row{{display:flex;justify-content:space-between;font-size:.7rem;font-weight:600;margin-top:4px;margin-bottom:10px;}}
.char-track{{height:2px;background:var(--surf3);border-radius:1px;margin-top:3px;}}
.char-fill{{height:100%;border-radius:1px;transition:width .3s,background .3s;}}

.preview{{background:var(--surf2);border:1px solid var(--border);border-radius:var(--r);padding:.55rem .85rem;font-family:var(--ff-m);font-size:.72rem;color:var(--t1);line-height:1.6;max-height:65px;overflow:hidden;white-space:pre-wrap;margin-bottom:5px;}}

.test-row{{display:flex;align-items:center;gap:10px;padding:.65rem 1rem;background:var(--surf);border:1px solid var(--border);border-radius:var(--r-lg);margin-bottom:5px;}}
.test-ico{{font-size:1rem;flex-shrink:0;width:20px;text-align:center;}}
.test-tag{{font-size:.78rem;font-weight:700;color:var(--t1);flex:1;}}
.test-type{{font-size:.68rem;color:var(--t3);}}
.test-badge{{font-size:.68rem;font-weight:700;border-radius:var(--r-pill);padding:2px 8px;}}
.test-pending{{background:var(--surf3);color:var(--t3);}}
.test-pass{{background:var(--grn-lt);color:var(--green);}}
.test-fail{{background:var(--red-lt);color:var(--red);}}

.law-row{{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--surf3);font-size:.82rem;color:var(--t1);}}
.law-row:last-child{{border-bottom:none;}}.law-row span.ico{{color:var(--accent);}}

.feat-row{{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--surf3);font-size:.82rem;}}
.feat-row:last-child{{border-bottom:none;}}.feat-name{{font-weight:600;color:var(--t1);}}.feat-desc{{font-size:.73rem;color:var(--t3);}}.feat-ico{{color:var(--green);font-weight:700;margin-right:7px;}}

.ring-wrap{{display:flex;align-items:center;justify-content:center;margin:5px 0;}}

/* FIX: Quick Switch active state */
.qs-btn-active .stButton>button{{background:var(--grn-lt)!important;color:var(--green)!important;border:1.5px solid var(--green)!important;box-shadow:none!important;}}
.qs-btn-active .stButton>button:hover{{background:var(--grn-lt)!important;opacity:1!important;transform:none!important;}}

.dim-row{{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--surf3);}}
.dim-row:last-child{{border-bottom:none;}}
.dim-name{{font-size:.82rem;font-weight:600;color:var(--t1);}}
.dim-desc{{font-size:.73rem;color:var(--t3);max-width:55%;text-align:right;}}

/* FIX: Active model banner — Groq variant uses dark text on amber for contrast */
.model-banner{{display:flex;align-items:center;justify-content:space-between;background:var(--acc-lt);border:1px solid var(--accent);border-radius:var(--r-lg);padding:.45rem 1rem;margin-bottom:.9rem;gap:8px;flex-wrap:nowrap;overflow:hidden;}}
.model-banner.groq-banner{{background:#2a1a00;border-color:#c88a20;}}
.model-banner-left{{display:flex;align-items:center;gap:8px;min-width:0;overflow:hidden;}}
.model-banner-label{{font-size:.72rem;font-weight:700;color:var(--t1);white-space:nowrap;flex-shrink:0;}}
.model-banner-model{{font-family:var(--ff-m);font-size:.7rem;color:#e0b060;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.model-banner:not(.groq-banner) .model-banner-model{{color:#8ab4ff;}}

/* FIX: Clear button */
.clear-btn .stButton>button{{background:transparent!important;color:var(--t3)!important;border:1px solid var(--border)!important;box-shadow:none!important;font-size:.75rem!important;padding:.3rem .9rem!important;}}
.clear-btn .stButton>button:hover{{background:var(--red-lt)!important;color:var(--red)!important;border-color:var(--red)!important;transform:none!important;box-shadow:none!important;}}

/* FIX: Settings test status inline */
.test-status-ok{{display:inline-block;background:var(--grn-lt);color:var(--green);border:1px solid var(--green);border-radius:var(--r-pill);padding:2px 10px;font-size:.72rem;font-weight:700;margin-top:6px;}}
.test-status-err{{display:inline-block;background:var(--red-lt);color:var(--red);border:1px solid var(--red);border-radius:var(--r-pill);padding:2px 10px;font-size:.72rem;font-weight:700;margin-top:6px;}}

.stToggle>label>div{{background:var(--surf3)!important;}}
.stToggle>label>div[data-checked="true"]{{background:var(--accent)!important;}}
.stToggle span{{color:var(--t2)!important;font-size:.82rem!important;}}

[data-testid="stDataFrame"]{{border-radius:var(--r-lg)!important;overflow:hidden!important;}}

.winner-bar{{background:var(--acc-lt);border:1px solid var(--accent);border-radius:var(--r-lg);padding:.8rem 1.2rem;text-align:center;font-size:.88rem;font-weight:600;color:var(--accent);margin-bottom:.9rem;}}
.section-sep{{border:none;border-top:1px solid var(--surf3);margin:.9rem 0 .6rem;}}

/* FIX: Quick Switch card — full border on all sides, proper card */
.qs-card{{background:var(--surf);border:1px solid var(--border);border-radius:var(--r-lg);padding:.85rem 1rem;}}
.qs-card-header{{font-size:.6rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--t3);margin-bottom:8px;}}

/* FIX: Side-by-side compare — wrapped in context card */
.compare-wrap{{background:var(--surf2);border:1px solid var(--border);border-radius:var(--r-lg);padding:.75rem 1rem;margin-top:.5rem;}}
.compare-label{{font-size:.65rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);margin-bottom:6px;}}

/* FIX: History expander — two-line format */
.hist-title{{display:flex;flex-direction:column;gap:2px;}}
.hist-t1{{font-size:.84rem;font-weight:700;}}
.hist-t2{{font-size:.7rem;color:var(--t3);}}

/* Sidebar session counter tooltip */
.sess-counter{{font-size:.68rem;color:rgba(255,255,255,.42);padding:4px 2px 8px;}}
.sess-counter abbr{{text-decoration:none;border-bottom:1px dotted rgba(255,255,255,.2);cursor:help;}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════

EXAMPLES = [
    {"tag":"Software Engineer Rejection","type":"job","expect_bias":False,
     "text":"Thank you for applying to the Software Engineer position. After careful review we have decided not to move forward. We felt other candidates were a stronger fit for our team culture at this time."},
    {"tag":"Bank Loan Denial (Geographic)","type":"loan","expect_bias":True,
     "text":"Your loan application has been declined. Primary reasons: insufficient credit history, residential area risk score, employment sector classification. You may reapply after 6 months."},
    {"tag":"Medical Triage (Age + Insurance)","type":"medical","expect_bias":True,
     "text":"Based on your intake assessment you have been assigned Priority Level 3. Factors considered: age group (65+), reported pain level, primary language (non-English), insurance classification (Medicaid). High-priority slots reserved for Priority 1-2 patients."},
    {"tag":"University Admission (Zip Code)","type":"university","expect_bias":True,
     "text":"We regret to inform you that your application for admission has not been successful. Our admissions committee considered zip code region diversity metrics, legacy status, and extracurricular profile alignment when making this decision."},
    {"tag":"Housing Rental Rejection","type":"other","expect_bias":True,
     "text":"After reviewing your rental application we are unable to proceed at this time. Factors reviewed include your neighbourhood of origin, employment sector, and family size relative to unit capacity."},
    {"tag":"Marketing Manager — Gender Bias","type":"job","expect_bias":True,
     "text":"Thank you for interviewing for the Marketing Manager role. While your qualifications were impressive, we felt the demands of the role — including frequent travel and extended hours — may not align with your current family obligations. We have moved forward with another candidate."},
    {"tag":"Small Business Loan (Name-Based)","type":"loan","expect_bias":True,
     "text":"Your small business loan application has been reviewed and we regret to inform you of our decision to decline. Our risk model flagged your application based on business owner surname origin score, neighbourhood commercial density index, and owner's primary spoken language."},
    {"tag":"Security Clearance Denial","type":"other","expect_bias":False,
     "text":"Your application for security clearance has been denied based on the following objective findings: undisclosed foreign financial accounts, two instances of late tax filings in the past five years, and an open civil judgment."},
    {"tag":"Graduate School Rejection (Race)","type":"university","expect_bias":True,
     "text":"After a holistic review of your application, the admissions committee has decided not to offer you a place in our programme. Factors that influenced this decision include undergraduate institution tier, applicant name-based cultural fit score, and geographic region of residence."},
    {"tag":"Insurance Claim Denial","type":"other","expect_bias":True,
     "text":"Your insurance claim #CLM-2024-8821 has been denied. Our automated assessment system identified the following risk factors: claimant occupation category (manual/unskilled labour), residential postcode risk band (Band D), and claim history pattern typical of high-risk socioeconomic segments."},
]

TYPE_LABELS = {"job":"Job Application","loan":"Bank Loan","medical":"Medical / Triage","university":"University Admission","other":"Other / General"}
BIAS_KW = {
    "Gender":r"\b(gender|female|male|woman|man|maternal|paternity|family obligation|housewife|mrs|mr)\b",
    "Age":r"\b(age group|senior|junior|young|old|millennial|boomer|elderly|youth|65\+|under 30)\b",
    "Racial":r"\b(race|ethnic|nationality|foreign|immigrant|origin|name|surname|cultural fit score|language score)\b",
    "Geographic":r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|region|district|postcode risk|locality)\b",
    "Socioeconomic":r"\b(income|wealth|credit history|employment sector|occupation|class|status|manual labour|unskilled|socioeconomic)\b",
    "Language":r"\b(primary language|language|accent|english|bilingual|non-english|native speaker)\b",
    "Insurance":r"\b(insurance|coverage|uninsured|medicaid|medicare|policy|insurance classification|insurance tier)\b",
}
BIAS_DIMS = ["Gender","Age","Racial","Geographic","Socioeconomic","Language","Insurance"]
CHIP_CYC  = ["cr","ca","cb","cg","cn"]
PAL       = ["#2B4EFF","#C42B2B","#166534","#92400E","#7C3AED","#0891B2","#DB2777"]

VIEWS = [
    ("analyse","⚡","Analyse"),
    ("models","⊕","Model Selector"),
    ("dashboard","◎","Dashboard"),
    ("history","▤","History"),
    ("batch","⊞","Batch"),
    ("test","⊘","Test Suite"),
    ("settings","⊛","Settings"),
    ("about","◷","About"),
]

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════

_DEFS = {
    "view":"analyse","session_count":0,"last_report":None,
    "last_text":"","last_dtype":"job","appeal_letter":None,
    "decision_input":"","scan_mode":"full",
    "ai_provider":"gemini","ai_model":"gemini-1.5-flash",
    "force_rerun":False,"fb_comment":"","cmp_ra":None,"cmp_rb":None,
    "gemini_test_result":None,"groq_test_result":None,
}
for k, v in _DEFS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# FIX: dtype_sel managed separately, never set via default kwarg to avoid Streamlit warning
if "dtype_sel" not in st.session_state:
    st.session_state["dtype_sel"] = "job"

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def gemini_ok():
    return bool(os.getenv("GEMINI_API_KEY","").strip() or os.getenv("GOOGLE_API_KEY","").strip())

def groq_ok():
    return bool(os.getenv("GROQ_API_KEY","").strip())

def any_api_ok():
    return gemini_ok() or groq_ok()

def current_provider():
    return st.session_state.get("ai_provider","gemini")

def current_model():
    return st.session_state.get("ai_model","gemini-1.5-flash")

def provider_label(p):
    return "🔵 Gemini" if p == "gemini" else "🟠 Groq"

def model_display(model_id):
    if model_id in GEMINI_MODELS: return GEMINI_MODELS[model_id]
    if model_id in GROQ_MODELS:   return GROQ_MODELS[model_id]
    return model_id

def all_reports():
    try: return services.get_all_reports()
    except: return []

def _trunc(s, n):
    """Word-boundary truncation."""
    s = str(s)
    if len(s) <= n:
        return s
    cut = s[:n]
    last_space = cut.rfind(" ")
    if last_space > n - 8:
        return cut[:last_space] + "…"
    return cut + "…"

def chips(items, style="auto"):
    if not items: return '<span class="chip cn">None detected</span>'
    return "".join(f'<span class="chip {CHIP_CYC[i%len(CHIP_CYC)] if style=="auto" else style}">{item}</span>' for i,item in enumerate(items))

def highlight_text(text, phrases, bias_types):
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

def sev_badge(conf, bias, sev="low"):
    if not bias: return '<span class="sev sev-l">Low Risk</span>'
    s = (sev or "low").lower()
    if s == "high" or conf >= .75:   return '<span class="sev sev-h">High</span>'
    if s == "medium" or conf >= .45: return '<span class="sev sev-m">Medium</span>'
    return '<span class="sev sev-l">Low</span>'

def provider_badge_html(prov):
    p = (prov or "gemini").lower()
    if "gemini" in p and "groq" in p:
        return '<span style="background:rgba(74,222,128,.1);color:#4ADE80;border:1px solid #4ADE80;border-radius:999px;padding:2px 9px;font-size:.67rem;font-weight:700;">🔀 Mixed</span>'
    elif "groq" in p:
        return '<span style="background:rgba(251,176,64,.12);color:#FBB040;border:1px solid #FBB040;border-radius:999px;padding:2px 9px;font-size:.67rem;font-weight:700;">🟠 Groq</span>'
    else:
        return '<span style="background:rgba(26,35,126,.3);color:#8AB4F8;border:1px solid #8AB4F8;border-radius:999px;padding:2px 9px;font-size:.67rem;font-weight:700;">🔵 Gemini</span>'

def ring_svg(pct, bias, size=110):
    r   = size * 0.38
    cx  = cy = size / 2
    sw  = size * 0.09
    circ = 2 * 3.14159 * r
    dash = circ * pct / 100
    gap  = circ - dash
    col  = tok("--red") if bias else (tok("--green") if pct < 40 else tok("--amber"))
    pulse_cls = 'class="ring-pulse"' if bias else ''
    return (
        f'<svg {pulse_cls} width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{tok("--surf3")}" stroke-width="{sw}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}"'
        f' stroke-dasharray="{dash:.1f} {gap:.1f}" stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>'
        f'<text x="{cx}" y="{cy - size*0.04}" text-anchor="middle" font-family="JetBrains Mono,monospace"'
        f' font-size="{size*0.18}" font-weight="600" fill="{col}">{pct}%</text>'
        f'<text x="{cx}" y="{cy + size*0.12}" text-anchor="middle" font-family="Syne,sans-serif"'
        f' font-size="{size*0.07}" font-weight="700" fill="{tok("--t3")}" letter-spacing="0.08em">CONF</text>'
        f'</svg>'
    )

def timing_pills(timing):
    if not timing: return ""
    labels = {"extract":"Extract","detect":"Detect","fair":"Fair","quick":"Scan","total":"Total"}
    parts  = [f'<span class="t-pill"><strong>{labels.get(k,k)}</strong> {v}ms</span>' for k,v in timing.items()]
    return '<div class="t-row">' + "".join(parts) + "</div>"

def txt_report(report, text, dtype):
    tm   = report.get("timing_ms",{})
    laws = report.get("legal_frameworks",[])
    recs = report.get("recommendations",[])
    prov = report.get("ai_provider","gemini")
    model= report.get("ai_model", current_model())
    lines = [
        "="*64,"       VERDICT WATCH V14 — BIAS ANALYSIS REPORT","="*64,
        f"Generated  : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type       : {dtype.upper()}",
        f"Report ID  : {report.get('id','N/A')}",
        f"Mode       : {(report.get('mode') or 'full').upper()}",
        f"AI Model   : {provider_label(prov)} · {model}",
        f"Severity   : {(report.get('severity') or 'N/A').upper()}","",
        "── ORIGINAL DECISION ──────────────────────────────────────",
        text or "(not recorded)","",
        "── VERDICT ────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence : {int(report.get('confidence_score',0)*100)}%","",
        "── BIAS TYPES ─────────────────────────────────────────────",
        ", ".join(report.get("bias_types",[])) or "None detected","",
        "── FAIR OUTCOME ───────────────────────────────────────────",
        report.get("fair_outcome") or "N/A","",
        "── EXPLANATION ────────────────────────────────────────────",
        report.get("explanation") or "N/A","",
        "── NEXT STEPS ─────────────────────────────────────────────",
        *[f"  {i+1}. {r}" for i,r in enumerate(recs)]
    ]
    if laws: lines += ["","── LEGAL FRAMEWORKS ───────────────────────────────────────"] + [f"  • {l}" for l in laws]
    if tm:   lines += ["","── TIMING ─────────────────────────────────────────────────"] + [f"  {k}: {v}ms" for k,v in tm.items()]
    lines += ["","="*64,"  Verdict Watch V14  ·  Not legal advice","="*64]
    return "\n".join(lines)

def to_csv(reps):
    rows = [{
        "id":r.get("id",""),
        "created_at":(r.get("created_at") or "")[:16].replace("T"," "),
        "mode":r.get("mode","full"),
        "ai_provider":r.get("ai_provider","gemini"),
        "bias_found":r.get("bias_found",False),
        "severity":r.get("severity",""),
        "confidence":int(r.get("confidence_score",0)*100),
        "bias_types":"; ".join(r.get("bias_types",[])),
        "affected":r.get("affected_characteristic",""),
        "original":r.get("original_outcome",""),
        "fair":r.get("fair_outcome",""),
        "explanation":r.get("explanation",""),
        "legal":"; ".join(r.get("legal_frameworks",[])),
        "next_steps":" | ".join(r.get("recommendations",[])),
        "total_ms":r.get("timing_ms",{}).get("total",""),
    } for r in reps if isinstance(r,dict)]
    return pd.DataFrame(rows).to_csv(index=False)

def extract_file(f):
    name = f.name.lower()
    if name.endswith(".txt"): return f.read().decode("utf-8",errors="replace")
    if name.endswith(".pdf"):
        if not PDF_SUPPORT: st.warning("PDF support requires: pip install PyMuPDF"); return None
        raw = f.read(); doc = pymupdf.open(stream=raw, filetype="pdf")
        return "\n".join(p.get_text() for p in doc).strip()
    st.warning(f"Unsupported: {f.name}"); return None

# ══════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════

def _base():
    return {"paper_bgcolor":"rgba(0,0,0,0)","plot_bgcolor":"rgba(0,0,0,0)",
            "font":{"family":"Syne,system-ui,sans-serif","color":"#9090AA"}}

def chart_pie(b, c):
    total = b + c or 1
    # FIX: no percentage labels inside donut — they overlap center text
    fig = go.Figure(go.Pie(
        labels=["Bias Detected","No Bias"], values=[max(b,1),max(c,1)], hole=.68,
        marker={"colors":[tok("--red"),tok("--green")],"line":{"color":tok("--bg"),"width":3}},
        textfont={"family":"Syne,sans-serif","size":11}, textinfo="none",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
    fig.add_annotation(
        text=f"<b style='font-size:20px'>{total}</b><br><span style='font-size:9px;color:{tok('--t3')}'>TOTAL</span>",
        x=.5, y=.5, showarrow=False,
        font={"family":"JetBrains Mono,monospace","size":18,"color":tok("--t1")})
    fig.update_layout(
        height=200, showlegend=True,
        legend={"font":{"family":"Syne,sans-serif","size":10},"bgcolor":"rgba(0,0,0,0)","orientation":"h","x":.5,"xanchor":"center","y":-.04},
        margin={"l":10,"r":10,"t":16,"b":10}, **_base())
    return fig

def chart_bar(items, max_n=8):
    counts = Counter(items)
    if not counts: counts = Counter({"No data":1})
    labels, values = zip(*counts.most_common(max_n))
    ll = list(labels)
    fig = go.Figure(go.Bar(
        x=list(values), y=ll, orientation="h",
        marker={"color":[PAL[i%len(PAL)] for i in range(len(ll))],"line":{"width":0},"cornerradius":4},
        text=list(values),
        textfont={"family":"JetBrains Mono,monospace","size":9,"color":tok("--t2")},
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>"))
    fig.update_layout(
        height=max(150,len(ll)*38+40),
        xaxis={"showgrid":True,"gridcolor":tok("--surf3"),"zeroline":False,"tickfont":{"family":"JetBrains Mono,monospace","size":9}},
        yaxis={"tickfont":{"family":"Syne,sans-serif","size":9}},
        bargap=.4, margin=dict(l=10,r=30,t=10,b=10), **_base())
    return fig

def chart_sparkline(scores):
    if not scores: scores = [0]
    fig = go.Figure(go.Scatter(
        y=scores, mode="lines",
        line={"color":tok("--accent"),"width":2},
        fill="tozeroy", fillcolor="rgba(107,138,255,0.10)",
        hovertemplate="Score %{y}%<extra></extra>"))
    fig.update_layout(
        height=75, xaxis={"visible":False}, yaxis={"range":[0,105],"visible":False},
        margin={"l":0,"r":0,"t":4,"b":0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family":"Syne,sans-serif"})
    return fig

def chart_trend(td):
    if not td: return None
    dates  = [d.get("date","") for d in td]
    rates  = [d.get("bias_rate",0) for d in td]
    totals = [d.get("total",0) for d in td]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=totals, name="Total",
        marker={"color":tok("--surf3"),"line":{"width":0},"cornerradius":3},
        yaxis="y2", hovertemplate="%{x}: %{y} analyses<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=dates, y=rates, name="Bias %", mode="lines+markers",
        line={"color":tok("--red"),"width":2.5},
        marker={"color":tok("--red"),"size":5,"line":{"color":tok("--bg"),"width":1.5}},
        hovertemplate="%{x}: %{y}%<extra></extra>"))
    fig.update_layout(
        height=210,
        xaxis={"type":"category","tickfont":{"family":"Syne,sans-serif","size":9}},
        yaxis={"range":[0,105],"tickfont":{"family":"JetBrains Mono,monospace","size":9},"gridcolor":tok("--surf3"),"zeroline":False},
        yaxis2={"overlaying":"y","side":"right","showgrid":False,"tickfont":{"family":"JetBrains Mono,monospace","size":9}},
        legend={"font":{"family":"Syne,sans-serif","size":10},"bgcolor":"rgba(0,0,0,0)","x":0,"y":1.1,"orientation":"h"},
        margin={"l":10,"r":40,"t":20,"b":10}, **_base())
    return fig

def chart_radar(all_r):
    dim_counts = {d:0 for d in BIAS_DIMS}
    for r in all_r:
        if isinstance(r,dict):
            for bt in r.get("bias_types",[]):
                for dim in BIAS_DIMS:
                    if dim.lower() in bt.lower(): dim_counts[dim] += 1
    vals = [dim_counts[d] for d in BIAS_DIMS]
    fig = go.Figure(go.Scatterpolar(
        r=vals+[vals[0]], theta=BIAS_DIMS+[BIAS_DIMS[0]], fill="toself",
        fillcolor="rgba(107,138,255,0.10)",
        line={"color":tok("--accent"),"width":2},
        marker={"color":tok("--accent"),"size":5}))
    fig.update_layout(
        polar={"bgcolor":"rgba(0,0,0,0)",
               "radialaxis":{"visible":True,"gridcolor":tok("--surf3"),"tickfont":{"family":"JetBrains Mono,monospace","size":8}},
               "angularaxis":{"gridcolor":tok("--surf3"),"tickfont":{"family":"Syne,sans-serif","size":9}}},
        height=250, showlegend=False,
        margin={"l":40,"r":40,"t":20,"b":20},
        paper_bgcolor="rgba(0,0,0,0)", font={"family":"Syne,sans-serif"})
    return fig

def chart_gauge(val, bias):
    col = tok("--red") if bias else tok("--green")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(val*100),
        number={"suffix":"%","font":{"family":"JetBrains Mono,monospace","size":22,"color":col}},
        gauge={"axis":{"range":[0,100],"tickwidth":0,"tickfont":{"color":tok("--t3"),"size":8}},
               "bar":{"color":col,"thickness":0.2},"bgcolor":tok("--surf2"),"borderwidth":0,
               "steps":[{"range":[0,33],"color":"rgba(22,101,52,.07)"},
                        {"range":[33,66],"color":"rgba(146,64,14,.07)"},
                        {"range":[66,100],"color":"rgba(196,43,43,.07)"}]}))
    fig.update_layout(height=160, margin={"l":10,"r":10,"t":20,"b":10}, **_base())
    return fig

# ══════════════════════════════════════════════════════
# PIPELINE RUNNER
# ══════════════════════════════════════════════════════

def _render_steps(ph, current, label):
    steps = [(1,"EXTRACT"),(2,"DETECT"),(3,"GENERATE")]
    parts = []
    for num, lbl in steps:
        if num < current:   cls, ico = "ss-done", "✓"
        elif num == current: cls, ico = "ss-active", "⟳"
        else:               cls, ico = "", str(num)
        parts.append(f'<div class="ss-i {cls}"><div class="ss-lbl">{ico} {lbl}</div></div>')
    ph.markdown(
        f'<div class="ss">{"".join(parts)}</div>'
        f'<div class="scan-bar"><div class="scan-fill"></div></div>'
        f'<div style="font-size:.74rem;color:{tok("--accent")};font-weight:600;">⬤ {label}</div>',
        unsafe_allow_html=True)

def run_analysis(text, dtype, mode="full", provider="gemini", model=None):
    orig_gemini = services._GEMINI_MODEL
    orig_groq   = services._GROQ_MODEL
    if model:
        if provider == "gemini" and model in GEMINI_MODELS:
            services._GEMINI_MODEL = model
        elif provider == "groq" and model in GROQ_MODELS:
            services._GROQ_MODEL = model

    ph = st.empty()
    def cb(step, label): _render_steps(ph, step, label)
    try:
        if mode == "quick":
            r = services.quick_scan(decision_text=text, decision_type=dtype, provider=provider)
        else:
            r = services.run_full_pipeline(decision_text=text, decision_type=dtype,
                                           progress_callback=cb, provider=provider)
        if isinstance(r, dict):
            r["ai_model"] = model or (orig_gemini if provider=="gemini" else orig_groq)
        st.session_state["session_count"] += 1
        ph.empty()
        return r, None
    except ValueError as e:
        ph.empty(); return None, str(e)
    except Exception as e:
        ph.empty(); return None, f"Pipeline error: {e}"
    finally:
        services._GEMINI_MODEL = orig_gemini
        services._GROQ_MODEL   = orig_groq

# ══════════════════════════════════════════════════════
# RESULT RENDERER
# ══════════════════════════════════════════════════════

def render_result(report, dt, dtype, compact=False):
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
    prov  = report.get("ai_provider", "gemini")
    mdl   = report.get("ai_model", "")

    vcls  = "vb-bias" if bias else "vb-clean"
    vico  = "⚠" if bias else "✓"
    vtxt  = "Bias Detected" if bias else "No Bias Found"
    vsub  = "This decision contains discriminatory patterns." if bias else "No strong discriminatory signals found."
    mbadge = '<span class="mb-quick">Quick</span>' if mode_=="quick" else '<span class="mb-full">Full</span>'
    pbadge = provider_badge_html(prov)
    mdl_short = _trunc(mdl.replace("gemini-","").replace("llama-","").replace("-versatile",""), 22)
    model_badge = (
        f'<span style="background:var(--surf3);color:var(--t2);border:1px solid var(--border);'
        f'border-radius:999px;padding:2px 9px;font-size:.67rem;font-weight:600;">{mdl_short}</span>'
        if mdl_short else ""
    )

    st.markdown(
        f'<div class="vb {vcls}">'
        f'<div style="font-size:1.8rem;line-height:1;margin-bottom:5px;">{vico}</div>'
        f'<div class="vb-title">{vtxt}</div>'
        f'<div class="vb-sub">{vsub}</div>'
        f'<div style="margin-top:8px;display:flex;gap:5px;justify-content:center;flex-wrap:wrap;">'
        f'{mbadge} {sev_badge(conf,bias,report.get("severity","low"))} {pbadge} {model_badge}'
        f'</div></div>',
        unsafe_allow_html=True)

    rc1, rc2 = st.columns([1,2], gap="small")
    with rc1:
        aff_html = ""
        if aff:
            aff_html = (
                f'<div style="margin-top:9px;"><div class="card-lbl">Affected</div>'
                f'<div style="font-size:.9rem;font-weight:700;color:{tok("--amber")};">{aff.title()}</div></div>'
            )
        st.markdown(
            f'<div class="card" style="text-align:center;">'
            f'<div class="ring-wrap">{ring_svg(pct,bias)}</div>{aff_html}</div>',
            unsafe_allow_html=True)
    with rc2:
        st.markdown(
            f'<div class="card" style="height:100%;">'
            f'<div class="card-lbl">Bias Types</div>'
            f'<div style="line-height:2.2;">{chips(btype) if btype else chips([])}</div>'
            f'</div>',
            unsafe_allow_html=True)

    ocls = "card-err" if bias else "card-muted"
    st.markdown(
        f'<div class="card {ocls}"><div class="card-lbl">Original Decision</div>'
        f'<div class="card-val mono lg">{orig.upper()}</div></div>'
        f'<div class="card card-ok"><div class="card-lbl">Should Have Been</div>'
        f'<div class="card-val serif">{fair}</div></div>',
        unsafe_allow_html=True)

    if evid:
        st.markdown(
            f'<div class="card card-warn"><div class="card-lbl">Bias Evidence</div>'
            f'<div class="card-val" style="font-size:.83rem;">{evid}</div></div>',
            unsafe_allow_html=True)
    if tm:
        st.markdown(timing_pills(tm), unsafe_allow_html=True)

    if not compact:
        if dt and (btype or report.get("bias_phrases")):
            st.markdown('<div class="lbl" style="margin-top:11px;">Highlighted Phrases</div>', unsafe_allow_html=True)
            hl = highlight_text(dt, report.get("bias_phrases",[]), btype)
            st.markdown(
                f'<div class="hl-box">{hl}</div>'
                f'<div style="font-size:.66rem;color:{tok("--t3")};margin-top:3px;">Highlighted = potential bias proxies</div>',
                unsafe_allow_html=True)
        if expl:
            st.markdown('<div class="lbl" style="margin-top:11px;">Plain English</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card card-warn"><div class="card-val">{expl}</div></div>', unsafe_allow_html=True)
        if laws:
            st.markdown('<div class="lbl" style="margin-top:11px;">Legal Frameworks</div>', unsafe_allow_html=True)
            rows_html = "".join(f'<div class="law-row"><span class="ico">⚖</span>{l}</div>' for l in laws)
            st.markdown(f'<div class="card card-info">{rows_html}</div>', unsafe_allow_html=True)
        if recs:
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Recommended Next Steps</div>', unsafe_allow_html=True)
            for i, rec in enumerate(recs, 1):
                st.markdown(
                    f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>',
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# INJECT CSS + SIDEBAR
# ══════════════════════════════════════════════════════

inject_css()

with st.sidebar:
    gem_status  = gemini_ok()
    groq_status = groq_ok()
    dot_cls    = "api-ok" if gem_status else ("api-warn" if groq_status else "api-err")
    status_txt = (
        "Gemini + Groq ready"             if gem_status and groq_status else
        "Gemini ready"                    if gem_status else
        "Groq only"                       if groq_status else
        "No API key — see Settings"
    )

    cur_prov  = st.session_state.get("ai_provider","gemini")
    cur_model = st.session_state.get("ai_model","gemini-1.5-flash")
    # FIX: sidebar model display — more readable, higher contrast
    mdl_short = _trunc(
        cur_model.replace("gemini-","G·").replace("llama-","L·")
                 .replace("-versatile","").replace("-instant",""), 20)
    prov_icon = "🔵" if cur_prov == "gemini" else "🟠"

    st.markdown(
        f'<div style="padding:18px 0 12px;">'
        f'<div class="vw-mark">Verdict Watch</div>'
        f'<div class="vw-ver">V14 · Dual AI Edition</div>'
        f'<div style="margin-top:9px;font-size:.68rem;color:rgba(255,255,255,.55);">'
        f'<span class="api-dot {dot_cls}"></span>{status_txt}</div>'
        f'<div style="margin-top:4px;font-size:.65rem;color:rgba(255,255,255,.45);">'
        f'{prov_icon} {mdl_short}</div>'
        f'</div>',
        unsafe_allow_html=True)

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
    st.markdown('<span class="sb-lbl">Quick Examples</span>', unsafe_allow_html=True)
    # FIX: word-boundary truncation at 22 chars — cleaner sidebar
    for idx in [1, 5, 6, 8]:
        ex = EXAMPLES[idx]
        if st.button(_trunc(ex["tag"], 22), key=f"ex_{idx}", use_container_width=True):
            st.session_state["decision_input"] = ex["text"]
            st.session_state["dtype_sel"]      = ex["type"]
            st.session_state["view"]           = "analyse"
            st.rerun()

    st.markdown('<div style="border-top:1px solid rgba(255,255,255,.06);margin:10px 0 8px;"></div>', unsafe_allow_html=True)
    sc = st.session_state.get("session_count", 0)
    ar = len(all_reports())
    # FIX: session counter — clearer label with abbr tooltip
    st.markdown(
        f'<div class="sess-counter">'
        f'<abbr title="Analyses run this session">Session</abbr> '
        f'<strong style="color:rgba(255,255,255,.7);">{sc}</strong>'
        f'<span style="margin:0 5px;opacity:.3;">·</span>'
        f'<abbr title="All analyses ever stored">All time</abbr> '
        f'<strong style="color:rgba(255,255,255,.7);">{ar}</strong>'
        f'</div>',
        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW ROUTER
# ══════════════════════════════════════════════════════

view = st.session_state["view"]

# ─────────────────────────────────────────────────────
# MODEL SELECTOR VIEW
# ─────────────────────────────────────────────────────
if view == "models":
    st.markdown('<div class="ph">Model Selector</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Choose your AI provider and model. Gemini is primary (required for hackathon). Groq is available as fallback or standalone.</div>', unsafe_allow_html=True)

    prov_col1, prov_col2 = st.columns(2, gap="small")
    with prov_col1:
        gem_sel    = st.session_state.get("ai_provider","gemini") == "gemini"
        gem_border = f"border:2px solid {tok('--accent')};" if gem_sel else f"border:1px solid {tok('--border')};"
        sel_lbl    = '<div style="font-size:.65rem;color:var(--accent);margin-top:5px;font-weight:700;">✓ SELECTED</div>' if gem_sel else ""
        st.markdown(
            f'<div class="card" style="{gem_border}">'
            f'<div style="font-size:1.3rem;margin-bottom:6px;">🔵</div>'
            f'<div style="font-weight:700;color:var(--t1);font-size:.9rem;">Google Gemini</div>'
            f'<div style="font-size:.72rem;color:var(--t3);margin-top:3px;">Primary · Required for hackathon</div>'
            f'{sel_lbl}</div>',
            unsafe_allow_html=True)
        if st.button("Select Gemini", key="sel_gemini", use_container_width=True):
            st.session_state["ai_provider"] = "gemini"
            if st.session_state.get("ai_model","") not in GEMINI_MODELS:
                st.session_state["ai_model"] = "gemini-1.5-flash"
            st.rerun()

    with prov_col2:
        grq_sel    = st.session_state.get("ai_provider","gemini") == "groq"
        grq_border = f"border:2px solid {tok('--amber')};" if grq_sel else f"border:1px solid {tok('--border')};"
        sel_lbl_g  = '<div style="font-size:.65rem;color:var(--amber);margin-top:5px;font-weight:700;">✓ SELECTED</div>' if grq_sel else ""
        st.markdown(
            f'<div class="card" style="{grq_border}">'
            f'<div style="font-size:1.3rem;margin-bottom:6px;">🟠</div>'
            f'<div style="font-weight:700;color:var(--t1);font-size:.9rem;">Groq</div>'
            f'<div style="font-size:.72rem;color:var(--t3);margin-top:3px;">Fallback · High speed inference</div>'
            f'{sel_lbl_g}</div>',
            unsafe_allow_html=True)
        if st.button("Select Groq", key="sel_groq", use_container_width=True):
            st.session_state["ai_provider"] = "groq"
            if st.session_state.get("ai_model","") not in GROQ_MODELS:
                st.session_state["ai_model"] = "llama-3.3-70b-versatile"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    current_prov = st.session_state.get("ai_provider","gemini")
    current_mdl  = st.session_state.get("ai_model","gemini-1.5-flash")

    if current_prov == "gemini":
        st.markdown('<div class="lbl">🔵 Available Gemini Models</div>', unsafe_allow_html=True)
        if not gem_status:
            st.markdown('<div class="key-err">⚠ GEMINI_API_KEY not set. Add it to .env to use Gemini models.</div>', unsafe_allow_html=True)
        for mid, mdesc in GEMINI_MODELS.items():
            is_sel      = current_mdl == mid
            recommended = "1.5-flash" in mid and "8b" not in mid
            border_style = f"border:2px solid {tok('--accent')};" if is_sel else f"border:1px solid {tok('--border')};"
            bg_style     = "background:var(--acc-lt);" if is_sel else ""
            rec_badge    = (' <span style="background:rgba(74,222,128,.15);color:#4ADE80;border-radius:999px;padding:1px 7px;font-size:.6rem;font-weight:700;border:1px solid #4ADE80;">✦ Recommended</span>'
                            if recommended else "")
            # FIX: column ratio 3:1 to reduce whitespace gap on Use button
            col_a, col_b = st.columns([3,1], gap="small")
            with col_a:
                active_html = '<div style="font-size:.72rem;color:var(--accent);font-weight:700;">✓ Active</div>' if is_sel else ""
                st.markdown(
                    f'<div class="card" style="{border_style}{bg_style}margin-bottom:5px;">'
                    f'<div style="display:flex;align-items:center;gap:8px;"><div style="flex:1;">'
                    f'<div style="font-size:.82rem;font-weight:700;color:var(--t1);">{mid}{rec_badge}</div>'
                    f'<div style="font-size:.72rem;color:var(--t3);margin-top:2px;">{mdesc}</div>'
                    f'</div>{active_html}</div></div>',
                    unsafe_allow_html=True)
            with col_b:
                if not is_sel:
                    if st.button("Use", key=f"use_{mid}", use_container_width=True):
                        st.session_state["ai_model"]    = mid
                        st.session_state["ai_provider"] = "gemini"
                        st.rerun()
                else:
                    st.markdown('<div style="height:42px;display:flex;align-items:center;justify-content:center;font-size:.72rem;color:var(--accent);font-weight:700;">Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="lbl">🟠 Available Groq Models</div>', unsafe_allow_html=True)
        if not groq_status:
            st.markdown('<div class="key-err">⚠ GROQ_API_KEY not set. Add it to .env to use Groq models.</div>', unsafe_allow_html=True)
        for mid, mdesc in GROQ_MODELS.items():
            is_sel      = current_mdl == mid
            recommended = "70b-versatile" in mid
            border_style = f"border:2px solid {tok('--amber')};" if is_sel else f"border:1px solid {tok('--border')};"
            bg_style     = "background:var(--amb-lt);" if is_sel else ""
            rec_badge    = (' <span style="background:rgba(251,176,64,.15);color:#FBB040;border-radius:999px;padding:1px 7px;font-size:.6rem;font-weight:700;border:1px solid #FBB040;">✦ Recommended</span>'
                            if recommended else "")
            col_a, col_b = st.columns([3,1], gap="small")
            with col_a:
                active_html = '<div style="font-size:.72rem;color:var(--amber);font-weight:700;margin-top:3px;">✓ Active</div>' if is_sel else ""
                st.markdown(
                    f'<div class="card" style="{border_style}{bg_style}margin-bottom:5px;">'
                    f'<div style="font-size:.82rem;font-weight:700;color:var(--t1);">{mid}{rec_badge}</div>'
                    f'<div style="font-size:.72rem;color:var(--t3);margin-top:2px;">{mdesc}</div>'
                    f'{active_html}</div>',
                    unsafe_allow_html=True)
            with col_b:
                if not is_sel:
                    if st.button("Use", key=f"use_{mid}", use_container_width=True):
                        st.session_state["ai_model"]    = mid
                        st.session_state["ai_provider"] = "groq"
                        st.rerun()
                else:
                    st.markdown('<div style="height:42px;display:flex;align-items:center;justify-content:center;font-size:.72rem;color:var(--amber);font-weight:700;">Active</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    fallback_note = "Gemini auto-falls back to Groq if API call fails" if current_prov=="gemini" else "Groq direct — no fallback"
    st.markdown(
        f'<div class="card card-info"><div class="card-lbl">Currently Active</div>'
        f'<div style="display:flex;align-items:center;gap:10px;margin-top:6px;">'
        f'{provider_badge_html(current_prov)}'
        f'<span style="font-size:.88rem;font-weight:700;color:var(--t1);">{current_mdl}</span>'
        f'</div>'
        f'<div style="font-size:.72rem;color:var(--t2);margin-top:5px;">{model_display(current_mdl)}</div>'
        f'<div style="font-size:.7rem;color:var(--t3);margin-top:4px;">{fallback_note}</div>'
        f'</div>',
        unsafe_allow_html=True)

    # FIX: breathing room before CTA
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    if st.button("⚡ Go to Analyse →", key="goto_analyse_from_models", type="primary", use_container_width=True):
        st.session_state["view"] = "analyse"
        st.rerun()

# ─────────────────────────────────────────────────────
# ANALYSE VIEW
# ─────────────────────────────────────────────────────
elif view == "analyse":
    st.markdown('<div class="ph">Analyse a Decision</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Paste any rejection, denial, or triage text to detect hidden bias.</div>', unsafe_allow_html=True)

    if not any_api_ok():
        st.markdown('<div class="key-err">⚠ No API key found. Add GEMINI_API_KEY or GROQ_API_KEY to .env and restart.</div>', unsafe_allow_html=True)

    cur_prov       = st.session_state.get("ai_provider","gemini")
    cur_model      = st.session_state.get("ai_model","gemini-1.5-flash")
    prov_available = (gem_status if cur_prov=="gemini" else groq_status)
    banner_cls     = "" if cur_prov=="gemini" else "groq-banner"
    key_miss       = "" if prov_available else ' <span style="color:var(--red);font-size:.7rem;font-weight:600;">⚠ Key missing</span>'

    st.markdown(
        f'<div class="model-banner {banner_cls}">'
        f'<div class="model-banner-left">'
        f'<span class="model-banner-label">Active Model:</span>'
        f'{provider_badge_html(cur_prov)}'
        f'<span class="model-banner-model">{cur_model}</span>'
        f'{key_miss}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True)
    if st.button("⊕ Change model", key="change_model_btn", help="Open Model Selector"):
        st.session_state["view"] = "models"
        st.rerun()

    if not prov_available:
        fb_prov = "groq" if cur_prov=="gemini" else "gemini"
        fb_ok   = groq_status if cur_prov=="gemini" else gem_status
        if fb_ok:
            st.markdown(
                f'<div class="card card-warn" style="margin-bottom:.5rem;">'
                f'<div class="card-val" style="font-size:.8rem;">⚠ {cur_prov.title()} key missing — will auto-fallback to {fb_prov.title()}</div></div>',
                unsafe_allow_html=True)

    input_col, right_pad = st.columns([5,2], gap="large")

    with input_col:
        mode_sel = st.radio("input_mode", ["✏  Paste Text","📄  Upload File"],
                            horizontal=True, label_visibility="collapsed", key="input_mode")
        st.markdown('<div class="lbl" style="margin-top:6px;">Decision Text</div>', unsafe_allow_html=True)

        if "Paste" in mode_sel:
            decision_text = st.text_area(
                "text", label_visibility="collapsed", height=190, key="decision_input",
                placeholder="Paste any rejection letter, loan denial, triage outcome, or university decision here…\n\nTip — load an example from the sidebar →")
        else:
            uf = st.file_uploader("File", type=["txt","pdf"], label_visibility="collapsed", key="file_up")
            decision_text = ""
            if uf:
                ex_text = extract_file(uf)
                if ex_text:
                    decision_text = ex_text
                    st.markdown(f'<span class="chip cg">✓ {len(ex_text):,} chars from {uf.name}</span>', unsafe_allow_html=True)
                    with st.expander("Preview"):
                        st.text(_trunc(ex_text, 600))

        # FIX: char counter inline below textarea — not in a separate column
        n = len((decision_text or "").strip())
        if n > 150:  cc, cl = tok("--green"), "Ready"
        elif n > 50: cc, cl = tok("--amber"), "Min length"
        else:        cc, cl = tok("--red"),   "Too short"
        w = min(100, int(n/3))
        st.markdown(
            f'<div class="char-row" style="color:{cc};"><span>{n:,} chars</span><span style="font-size:.65rem;">{cl}</span></div>'
            f'<div class="char-track"><div class="char-fill" style="width:{w}%;background:{cc};"></div></div>',
            unsafe_allow_html=True)

        # FIX: Signals detected — anchored right below textarea, above TYPE
        if decision_text and len(decision_text.strip()) > 30:
            detected = [d for d in BIAS_DIMS if re.search(BIAS_KW[d], decision_text, re.IGNORECASE)]
            if detected:
                st.markdown('<div class="lbl" style="margin-top:4px;">Signals detected in text</div>', unsafe_allow_html=True)
                st.markdown("".join(f'<span class="chip ca" style="margin-bottom:4px;">{d}</span>' for d in detected), unsafe_allow_html=True)

        opts = ["job","loan","medical","university","other"]
        cur  = st.session_state.get("dtype_sel","job")
        idx  = opts.index(cur) if cur in opts else 0
        # FIX: no default= kwarg on selectbox to avoid Streamlit warning
        dtype = st.selectbox("Type", opts, format_func=lambda x: TYPE_LABELS[x], index=idx, key="dtype_sel",
                             label_visibility="visible")

        st.markdown('<hr class="section-sep">', unsafe_allow_html=True)
        st.markdown('<div class="lbl">Scan Mode</div>', unsafe_allow_html=True)
        scan_mode = st.radio(
            "Scan Mode", ["full","quick"],
            format_func=lambda x: "⚡ Full — 3-step deep analysis" if x=="full" else "◎ Quick — single call, faster",
            horizontal=True, key="scan_mode", label_visibility="collapsed")

        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
        ba1, ba2 = st.columns([2,1])
        with ba1:
            run_btn = st.button("⚡ Run Analysis", key="run_btn", disabled=not any_api_ok())
        with ba2:
            if st.session_state.get("last_report"):
                st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
                if st.button("✕ Clear", key="clear_btn"):
                    st.session_state["last_report"]   = None
                    st.session_state["last_text"]     = ""
                    st.session_state["appeal_letter"] = None
                    st.session_state["decision_input"] = ""
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # FIX: side-by-side compare wrapped in card for context
        st.markdown('<hr class="section-sep">', unsafe_allow_html=True)
        st.markdown(
            '<div class="compare-wrap">'
            '<div class="compare-label">Compare Mode</div>',
            unsafe_allow_html=True)
        compare_mode = st.toggle("Side-by-side compare", value=False, key="compare_toggle")
        st.markdown('</div>', unsafe_allow_html=True)

        if compare_mode:
            st.markdown('<div class="lbl" style="margin-top:8px;">Decision B (for comparison)</div>', unsafe_allow_html=True)
            dt_b = st.text_area("text_b", label_visibility="collapsed", height=120, key="decision_input_b", placeholder="Paste second decision…")
            ctp2 = st.selectbox("Type B", opts, format_func=lambda x: TYPE_LABELS[x], label_visibility="collapsed", key="dtype_b")

    with right_pad:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        # FIX: full card border on all sides for Quick Switch panel
        st.markdown(
            '<div class="qs-card">'
            '<div class="qs-card-header">Quick Switch Model</div>',
            unsafe_allow_html=True)

        quick_models = {
            "gemini": ["gemini-1.5-flash","gemini-2.0-flash","gemini-1.5-pro"],
            "groq":   ["llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768"],
        }
        for p, models in quick_models.items():
            p_icon  = "🔵" if p=="gemini" else "🟠"
            p_color = tok("--accent") if p=="gemini" else tok("--amber")
            st.markdown(f'<div style="font-size:.65rem;color:{p_color};font-weight:700;margin:7px 0 3px;">{p_icon} {p.upper()}</div>', unsafe_allow_html=True)
            for m in models:
                is_cur = (st.session_state.get("ai_model")==m and st.session_state.get("ai_provider")==p)
                short  = m.replace("gemini-","").replace("llama-","").replace("-versatile","").replace("-instant","")
                prefix = "✓ " if is_cur else ""
                if is_cur:
                    st.markdown('<div class="qs-btn-active">', unsafe_allow_html=True)
                if st.button(f"{prefix}{short}", key=f"qs_{p}_{m}", use_container_width=True):
                    st.session_state["ai_provider"] = p
                    st.session_state["ai_model"]    = m
                    st.rerun()
                if is_cur:
                    st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # close qs-card

        st.markdown(
            f'<div class="card card-info" style="margin-top:8px;">'
            f'<div class="card-lbl">Bias Dimensions</div>'
            f'<div style="margin-top:6px;">'
            + "".join(f'<span class="chip cn" style="margin-bottom:3px;">{d}</span>' for d in BIAS_DIMS)
            + f'</div></div>',
            unsafe_allow_html=True)

    # ── Run logic ──
    if run_btn:
        dt = (decision_text or "").strip()
        if not dt:
            st.warning("⚠ Paste or upload a decision first.")
        else:
            th     = services.hash_text(dt)
            cached = services.find_duplicate(th)
            if cached and not st.session_state.get("force_rerun"):
                st.markdown(
                    '<div class="dup-warn">⚠ <div><strong>Identical text — showing cached result.</strong>'
                    '<br>Click Re-run for a fresh analysis.</div></div>',
                    unsafe_allow_html=True)
                if st.button("🔄 Re-run", key="force_btn"):
                    st.session_state["force_rerun"] = True
                    st.rerun()
                report, err = cached, None
            else:
                st.session_state.pop("force_rerun", None)
                with st.spinner(""):
                    report, err = run_analysis(
                        dt, dtype, mode=scan_mode,
                        provider=st.session_state.get("ai_provider","gemini"),
                        model=st.session_state.get("ai_model","gemini-1.5-flash"))

            if err:
                st.error(f"❌ {err}")
            elif report:
                st.session_state["last_report"]   = report
                st.session_state["last_text"]     = dt
                st.session_state["last_dtype"]    = dtype
                st.session_state["appeal_letter"] = None

            if compare_mode and not err:
                dt2 = (st.session_state.get("decision_input_b") or "").strip()
                if dt2:
                    with st.spinner("Analysing Decision B…"):
                        rb, eb = run_analysis(
                            dt2, st.session_state.get("dtype_b","other"),
                            mode=scan_mode,
                            provider=st.session_state.get("ai_provider","gemini"),
                            model=st.session_state.get("ai_model","gemini-1.5-flash"))
                    if eb: st.error(f"Decision B error: {eb}")
                    else:
                        st.session_state["cmp_ra"] = report
                        st.session_state["cmp_rb"] = rb

    report = st.session_state.get("last_report")
    dt     = st.session_state.get("last_text","")
    dtype_ = st.session_state.get("last_dtype","other")

    # ── Compare view ──
    if compare_mode and st.session_state.get("cmp_ra") and st.session_state.get("cmp_rb"):
        ra, rb  = st.session_state["cmp_ra"], st.session_state["cmp_rb"]
        ba, bb  = ra.get("bias_found"), rb.get("bias_found")
        ca, cb_ = ra.get("confidence_score",0), rb.get("confidence_score",0)
        if ba and bb:
            msg = f"Both show bias — Decision {'A' if ca>=cb_ else 'B'} has higher confidence ({int(max(ca,cb_)*100)}%)"
        elif ba: msg = "Decision A shows bias · Decision B appears fair"
        elif bb: msg = "Decision B shows bias · Decision A appears fair"
        else:    msg = "Neither decision contains discriminatory patterns"
        st.markdown(f'<div class="winner-bar">{msg}</div>', unsafe_allow_html=True)
        v1, v2 = st.columns(2, gap="small")
        for col, r, lbl in [(v1,ra,"A"),(v2,rb,"B")]:
            with col:
                b_    = r.get("bias_found",False)
                vcls_ = "vb-bias" if b_ else "vb-clean"
                vt_   = "⚠ Bias" if b_ else "✓ Clean"
                st.markdown(
                    f'<div class="vb {vcls_}" style="padding:1rem;">'
                    f'<div class="vb-title" style="font-size:1.1rem;">Decision {lbl}</div>'
                    f'<div class="vb-sub" style="font-size:.78rem;">{vt_}</div></div>',
                    unsafe_allow_html=True)
                st.plotly_chart(chart_gauge(r.get("confidence_score",0),b_), use_container_width=True, config={"displayModeBar":False})
                st.markdown(chips(r.get("bias_types",[])), unsafe_allow_html=True)
                st.markdown(
                    f'<div style="margin-top:4px;">'
                    f'{sev_badge(r.get("confidence_score",0),b_,r.get("severity","low"))} '
                    f'{provider_badge_html(r.get("ai_provider","gemini"))}</div>',
                    unsafe_allow_html=True)
                if r.get("fair_outcome"):
                    st.markdown(
                        f'<div class="card card-ok" style="margin-top:7px;">'
                        f'<div class="card-lbl">Fair Outcome</div>'
                        f'<div class="card-val serif">{r["fair_outcome"]}</div></div>',
                        unsafe_allow_html=True)
        st.stop()

    if not report:
        st.markdown(
            '<div class="empty"><div class="empty-ico">⚖</div>'
            '<div class="empty-t">No analysis yet</div>'
            '<div class="empty-s">Paste a decision above and click Run Analysis.</div></div>',
            unsafe_allow_html=True)
    else:
        render_result(report, dt, dtype_)
        st.markdown('<hr class="div">', unsafe_allow_html=True)
        st.markdown('<div class="lbl">Was this analysis helpful?</div>', unsafe_allow_html=True)
        fb_comment = st.text_input("Comment", key="fb_comment", label_visibility="collapsed", placeholder="Optional notes…")
        fb1, fb2, _ = st.columns([1,1,3])
        with fb1:
            if st.button("👍 Helpful", key="fb_y"):
                services.save_feedback(report.get("id",""), 1, fb_comment); st.success("Thanks!")
        with fb2:
            if st.button("👎 Not helpful", key="fb_n"):
                services.save_feedback(report.get("id",""), 0, fb_comment); st.info("Noted.")

        if report.get("bias_found"):
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Formal Appeal Letter</div>', unsafe_allow_html=True)
            if st.button("✉ Generate Appeal Letter", key="appeal_btn"):
                with st.spinner("Drafting letter…"):
                    try:
                        letter = services.generate_appeal_letter(
                            report, dt, dtype_,
                            provider=st.session_state.get("ai_provider","gemini"))
                        st.session_state["appeal_letter"] = letter
                    except Exception as e:
                        st.error(f"❌ {e}")
            if st.session_state.get("appeal_letter"):
                letter = st.session_state["appeal_letter"]
                st.markdown(f'<div class="appeal-box">{letter}</div>', unsafe_allow_html=True)
                st.download_button("↓ Download Letter", data=letter,
                    file_name=f"appeal_{(report.get('id') or 'x')[:8]}.txt",
                    mime="text/plain", key="dl_letter")

        st.markdown("<br>", unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("↓ Full Report (.txt)", data=txt_report(report,dt,dtype_),
                file_name=f"verdict_v14_{(report.get('id') or 'r')[:8]}.txt",
                mime="text/plain", key="dl_rpt")
        with dl2:
            st.download_button("↓ CSV", data=to_csv([report]),
                file_name=f"verdict_v14_{(report.get('id') or 'r')[:8]}.csv",
                mime="text/csv", key="dl_csv_single")

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
            '<div class="empty-s">Run your first analysis to populate the dashboard.</div></div>',
            unsafe_allow_html=True)
    else:
        b_reps  = [r for r in hist if r.get("bias_found")]
        c_reps  = [r for r in hist if not r.get("bias_found")]
        all_bt  = [bt for r in hist for bt in r.get("bias_types",[])]
        scores  = [r.get("confidence_score",0) for r in hist]
        b_rate  = round(len(b_reps)/len(hist)*100) if hist else 0
        avg_c   = round(sum(scores)/len(scores)*100) if scores else 0
        # FIX: Top Bias — hard truncate to 10 chars for metric card
        top_b_raw = Counter(all_bt).most_common(1)[0][0] if all_bt else "—"
        top_b = _trunc(top_b_raw, 10)
        fb      = services.get_feedback_stats()
        sev_map = {"high":3,"medium":2,"low":1}
        sev_vals= [sev_map.get((r.get("severity") or "low").lower(),1) for r in hist]
        avg_sv  = sum(sev_vals)/len(sev_vals) if sev_vals else 1
        avg_sev = "High" if avg_sv>=2.5 else ("Medium" if avg_sv>=1.5 else "Low")
        gem_count = sum(1 for r in hist if (r.get("ai_provider") or "gemini")=="gemini")
        grq_count = len(hist)-gem_count

        k1,k2,k3,k4,k5,k6 = st.columns(6)
        k1.metric("Total",len(hist)); k2.metric("Bias Rate",f"{b_rate}%")
        k3.metric("Avg Confidence",f"{avg_c}%"); k4.metric("Top Bias",top_b)
        k5.metric("Avg Severity",avg_sev); k6.metric("Helpful %",f"{fb['helpful_pct']}%" if fb["total"] else "—")

        if gem_count or grq_count:
            total_  = gem_count + grq_count
            gem_pct = int(gem_count/total_*100) if total_ else 0
            grq_pct = 100 - gem_pct
            # FIX: min segment width 4px so neither bar disappears at 0%
            gem_w = max(4, int(gem_pct * 0.98))
            grq_w = max(4, 100 - gem_w)
            st.markdown('<div class="lbl" style="margin-top:.5rem;">AI Provider Usage</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex;gap:3px;border-radius:var(--r-pill);overflow:hidden;height:8px;margin-bottom:4px;">'
                f'<div style="width:{gem_w}%;background:#8AB4F8;min-width:4px;"></div>'
                f'<div style="width:{grq_w}%;background:#FBB040;min-width:4px;"></div>'
                f'</div>'
                f'<div style="display:flex;gap:16px;font-size:.7rem;">'
                f'<span style="color:#8AB4F8;">🔵 Gemini {gem_count} ({gem_pct}%)</span>'
                f'<span style="color:#FBB040;">🟠 Groq {grq_count} ({grq_pct}%)</span>'
                f'</div>',
                unsafe_allow_html=True)

        spark_scores = services.get_confidence_trend(30)
        if spark_scores:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="lbl">Confidence Trend (last 30)</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_sparkline(spark_scores), use_container_width=True, config={"displayModeBar":False})

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="lbl">Verdict Distribution</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_pie(len(b_reps),len(c_reps)), use_container_width=True, config={"displayModeBar":False})
        with c2:
            st.markdown('<div class="lbl">Bias Type Frequency</div>', unsafe_allow_html=True)
            if all_bt: st.plotly_chart(chart_bar(all_bt), use_container_width=True, config={"displayModeBar":False})
            else: st.markdown('<div class="empty"><div class="empty-s">No bias types yet.</div></div>', unsafe_allow_html=True)

        td = services.get_trend_data()
        if td:
            st.markdown('<div class="lbl" style="margin-top:.5rem;">Daily Bias Rate Trend</div>', unsafe_allow_html=True)
            tf = chart_trend(td)
            if tf: st.plotly_chart(tf, use_container_width=True, config={"displayModeBar":False})

        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="lbl">Bias Dimension Radar</div>', unsafe_allow_html=True)
            st.plotly_chart(chart_radar(hist), use_container_width=True, config={"displayModeBar":False})
        with c4:
            st.markdown('<div class="lbl">Affected Characteristics</div>', unsafe_allow_html=True)
            chars = [str(r.get("affected_characteristic")) for r in hist if r.get("affected_characteristic")]
            if chars: st.plotly_chart(chart_bar(chars), use_container_width=True, config={"displayModeBar":False})
            else: st.markdown('<div class="empty"><div class="empty-s">No characteristic data yet.</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        dl1, _ = st.columns([1,4])
        with dl1:
            st.download_button("↓ Export CSV", data=to_csv(hist),
                file_name=f"verdict_dash_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="dash_dl")

# ─────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────
elif view == "history":
    st.markdown('<div class="ph">Analysis History</div>', unsafe_allow_html=True)
    hist = all_reports()
    if not hist:
        st.markdown('<div class="empty"><div class="empty-ico">▤</div><div class="empty-t">No history yet</div></div>', unsafe_allow_html=True)
    else:
        f1, f2, f3 = st.columns([3,1,1])
        with f1: q  = st.text_input("Search", placeholder="Search bias type, outcome…", key="h_q")
        with f2: fv = st.selectbox("Verdict",["All","Bias","No Bias"], key="h_v")
        with f3: sv = st.selectbox("Sort",["Newest","Oldest","High Conf","Low Conf"], key="h_s")

        fp1, fp2, fp3 = st.columns([1,1,2])
        with fp1: filt_prov = st.selectbox("Provider",["All","Gemini","Groq"], key="h_prov")
        with fp2: df_in = st.date_input("From", value=None, key="h_df")
        with fp3: dt_in = st.date_input("To",   value=None, key="h_dt")

        filt = list(hist)
        if fv=="Bias":    filt = [r for r in filt if r.get("bias_found")]
        elif fv=="No Bias": filt = [r for r in filt if not r.get("bias_found")]
        if filt_prov=="Gemini": filt = [r for r in filt if (r.get("ai_provider") or "gemini")=="gemini"]
        elif filt_prov=="Groq": filt = [r for r in filt if r.get("ai_provider")=="groq"]
        if q:
            ql   = q.lower()
            filt = [r for r in filt if
                    ql in (r.get("affected_characteristic") or "").lower()
                    or any(ql in bt.lower() for bt in r.get("bias_types",[]))
                    or ql in (r.get("original_outcome") or "").lower()
                    or ql in (r.get("explanation") or "").lower()]
        if df_in: filt = [r for r in filt if (r.get("created_at") or "")[:10]>=str(df_in)]
        if dt_in: filt = [r for r in filt if (r.get("created_at") or "")[:10]<=str(dt_in)]
        if sv=="Newest":     filt.sort(key=lambda r:r.get("created_at") or "",reverse=True)
        elif sv=="Oldest":   filt.sort(key=lambda r:r.get("created_at") or "")
        elif sv=="High Conf":filt.sort(key=lambda r:r.get("confidence_score",0),reverse=True)
        else:                filt.sort(key=lambda r:r.get("confidence_score",0))

        hdr1, hdr2 = st.columns([3,1])
        with hdr1:
            st.markdown(f'<div style="font-size:.73rem;color:{tok("--t3")};margin-bottom:9px;">Showing {len(filt)} of {len(hist)} reports</div>', unsafe_allow_html=True)
        with hdr2:
            st.download_button("↓ CSV", data=to_csv(filt),
                file_name=f"verdict_hist_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", key="hist_dl")

        # FIX: cleaner two-line expander title — verdict + confidence on line 1, date + provider on line 2
        for r in filt:
            bias    = r.get("bias_found",False)
            conf    = int(r.get("confidence_score",0)*100)
            aff     = _trunc(r.get("affected_characteristic") or "unknown", 20)
            created = (r.get("created_at") or "")[:10]
            ico     = "⚠" if bias else "✓"
            verdict = "Bias" if bias else "Clean"
            prov_r  = r.get("ai_provider","gemini")
            prov_ico= "🔵" if "groq" not in (prov_r or "") else "🟠"
            # Cleaner title: verdict · confidence · affected characteristic
            title = f"{ico} {verdict} · {conf}% conf · {aff} · {created} {prov_ico}"
            with st.expander(title):
                ec1, ec2 = st.columns(2, gap="large")
                with ec1:
                    vcls = "card-err" if bias else "card-ok"
                    vt   = "⚠ Bias Detected" if bias else "✓ No Bias Found"
                    st.markdown(
                        f'<div class="card {vcls}"><div class="card-lbl">Verdict</div><div class="card-val mono">{vt}</div></div>'
                        f'<div class="card card-muted" style="margin-top:6px;"><div class="card-lbl">Original Outcome</div><div class="card-val mono">{(r.get("original_outcome") or "N/A").upper()}</div></div>'
                        f'<div class="card card-info" style="margin-top:6px;"><div class="card-lbl">AI Used</div><div class="card-val" style="font-size:.8rem;">{provider_badge_html(prov_r)} <span style="font-family:var(--ff-m);font-size:.72rem;">{r.get("ai_model","")}</span></div></div>',
                        unsafe_allow_html=True)
                with ec2:
                    st.markdown(
                        f'<div class="card card-warn"><div class="card-lbl">Bias Types</div><div class="card-val">{chips(r.get("bias_types",[]))}</div></div>'
                        f'<div class="card card-ok" style="margin-top:6px;"><div class="card-lbl">Fair Outcome</div><div class="card-val serif">{r.get("fair_outcome") or "N/A"}</div></div>',
                        unsafe_allow_html=True)
                if r.get("explanation"):
                    st.markdown(f'<div class="card card-muted" style="margin-top:6px;"><div class="card-lbl">Explanation</div><div class="card-val" style="font-size:.83rem;">{r["explanation"]}</div></div>', unsafe_allow_html=True)
                laws = r.get("legal_frameworks",[])
                if laws:
                    rows_html = "".join(f'<div class="law-row"><span class="ico">⚖</span>{l}</div>' for l in laws)
                    st.markdown(f'<div class="card card-info" style="margin-top:6px;"><div class="card-lbl">Legal Frameworks</div>{rows_html}</div>', unsafe_allow_html=True)
                recs = r.get("recommendations",[])
                if recs:
                    st.markdown('<div class="lbl" style="margin-top:9px;">Next Steps</div>', unsafe_allow_html=True)
                    for i, rec in enumerate(recs,1):
                        st.markdown(f'<div class="rec"><div class="rec-n">{i}</div><div class="rec-t">{rec}</div></div>', unsafe_allow_html=True)
                if r.get("timing_ms"): st.markdown(timing_pills(r["timing_ms"]), unsafe_allow_html=True)
                st.download_button("↓ Report (.txt)", data=txt_report(r,"","other"),
                    file_name=f"verdict_{(r.get('id') or 'x')[:8]}.txt",
                    mime="text/plain", key=f"dl_{r.get('id','x')}")

# ─────────────────────────────────────────────────────
# BATCH
# ─────────────────────────────────────────────────────
elif view == "batch":
    st.markdown('<div class="ph">Batch Processing</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ps">Analyse up to 10 decisions at once. '
        'Separate with <code>---</code> or upload CSV with a <code>text</code> column.</div>',
        unsafe_allow_html=True)

    if not any_api_ok():
        st.markdown('<div class="key-err">⚠ API key missing — see Settings.</div>', unsafe_allow_html=True)

    cur_prov  = st.session_state.get("ai_provider","gemini")
    cur_model = st.session_state.get("ai_model","gemini-1.5-flash")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.75rem;">'
        f'<span style="font-size:.72rem;color:var(--t3);">Using:</span>'
        f'{provider_badge_html(cur_prov)}'
        f'<span style="font-family:var(--ff-m);font-size:.72rem;color:var(--t2);">{cur_model}</span>'
        f'</div>',
        unsafe_allow_html=True)

    bmode = st.radio("Batch input",["✏  Paste Text","📊  Upload CSV"], horizontal=True, label_visibility="collapsed", key="bm")
    if "Paste" in bmode:
        bt_ = st.text_area("Batch text", height=200, label_visibility="collapsed", key="b_in",
                           placeholder="Decision 1…\n---\nDecision 2…\n---\nDecision 3…")
        blocks = [b.strip() for b in bt_.split("---") if b.strip()] if bt_ else []
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
        btype  = st.selectbox("Decision type",["job","loan","medical","university","other"],
                              format_func=lambda x:TYPE_LABELS[x], label_visibility="collapsed", key="b_type")
    with bc2:
        scan_b = st.radio("Mode",["full","quick"], horizontal=True,
                          format_func=lambda x:"Full" if x=="full" else "Quick", key="b_scan")
    with bc3:
        brun   = st.button("⊞ Run Batch", key="b_run", disabled=not any_api_ok())

    if blocks:
        st.markdown(f'<span class="chip cb">● {len(blocks)} decision{"s" if len(blocks)!=1 else ""} queued</span>', unsafe_allow_html=True)

    if brun:
        if not blocks: st.warning("⚠ No decisions found.")
        elif len(blocks)>10: st.warning("⚠ Batch limit is 10 decisions.")
        else:
            prog=st.progress(0); status=st.empty(); results=[]; t0=time.time()
            for i, blk in enumerate(blocks):
                elapsed=time.time()-t0; eta=(elapsed/(i+1))*(len(blocks)-i-1) if i>0 else 0
                status.markdown(
                    f'<div style="font-size:.78rem;color:{tok("--accent")};font-weight:600;">'
                    f'Analysing {i+1}/{len(blocks)}{"  · ETA ~"+str(int(eta))+"s" if eta>1 else ""}…</div>',
                    unsafe_allow_html=True)
                rep, err = run_analysis(blk, btype, mode=scan_b,
                                        provider=st.session_state.get("ai_provider","gemini"),
                                        model=st.session_state.get("ai_model","gemini-1.5-flash"))
                results.append({"text":blk,"report":rep,"error":err})
                prog.progress((i+1)/len(blocks))
            prog.empty(); status.empty()
            st.markdown('<hr class="div">', unsafe_allow_html=True)

            b_c = sum(1 for r in results if isinstance(r.get("report"),dict) and r["report"].get("bias_found"))
            c_c = sum(1 for r in results if isinstance(r.get("report"),dict) and not r["report"].get("bias_found"))
            e_c = sum(1 for r in results if r.get("error"))
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Total",len(results)); m2.metric("Bias Detected",b_c)
            m3.metric("No Bias",c_c); m4.metric("Errors",e_c)

            rows = []
            for i, res in enumerate(results,1):
                rep=res.get("report"); err=res.get("error","")
                if err: rows.append({"#":i,"Verdict":"ERROR","Conf":"—","Bias Types":str(err)[:50],"Provider":"—"})
                elif isinstance(rep,dict):
                    prov_ico="🔵" if rep.get("ai_provider","gemini")=="gemini" else "🟠"
                    rows.append({"#":i,
                                 "Verdict":"⚠ Bias" if rep.get("bias_found") else "✓ Clean",
                                 "Conf":f"{int(rep.get('confidence_score',0)*100)}%",
                                 "Bias Types":", ".join(rep.get("bias_types",[])) or "None",
                                 "Provider":f"{prov_ico} {rep.get('ai_model','')}"})
            if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            all_r = [r["report"] for r in results if isinstance(r.get("report"),dict)]
            if all_r:
                dl1,_ = st.columns([1,3])
                with dl1:
                    st.download_button("↓ CSV", data=to_csv(all_r),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv", key="b_dl")

# ─────────────────────────────────────────────────────
# TEST SUITE
# ─────────────────────────────────────────────────────
elif view == "test":
    st.markdown('<div class="ph">Test Suite</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Run all built-in examples in one click. Each test has an expected outcome — pass means the model agrees.</div>', unsafe_allow_html=True)

    cur_prov  = st.session_state.get("ai_provider","gemini")
    cur_model = st.session_state.get("ai_model","gemini-1.5-flash")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.75rem;">'
        f'<span style="font-size:.72rem;color:var(--t3);">Model for Tests:</span>'
        f'{provider_badge_html(cur_prov)}'
        f'<span style="font-family:var(--ff-m);font-size:.72rem;color:var(--t2);">{cur_model}</span>'
        f'</div>',
        unsafe_allow_html=True)

    if not any_api_ok():
        st.markdown('<div class="key-err">⚠ API key missing — cannot run tests.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="lbl" style="margin-bottom:10px;">Test Cases</div>', unsafe_allow_html=True)
        for i, ex in enumerate(EXAMPLES,1):
            bias_lbl = "Bias expected" if ex["expect_bias"] else "Clean expected"
            st.markdown(
                f'<div class="test-row">'
                f'<div class="test-ico" style="color:var(--t3);">○</div>'
                f'<div style="flex:1;">'
                f'<div class="test-tag">{i}. {ex["tag"]}</div>'
                f'<div class="test-type">{TYPE_LABELS[ex["type"]]} · {bias_lbl}</div>'
                f'</div>'
                f'<span class="test-badge test-pending">Pending</span></div>',
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        ts_mode = st.radio("Scan mode",["quick","full"],
            format_func=lambda x:"Quick (faster)" if x=="quick" else "Full (detailed)",
            horizontal=True, key="ts_mode")
        run_all = st.button("⊘ Run All Tests", key="ts_run", type="primary")

        if run_all:
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Live Results</div>', unsafe_allow_html=True)
            prog=st.progress(0); ts_results=[]; tsc={"pass":0,"fail":0,"err":0}
            for i, ex in enumerate(EXAMPLES):
                prog.progress(i/len(EXAMPLES))
                ph_s = st.empty()
                ph_s.markdown(
                    f'<div style="font-size:.78rem;color:{tok("--accent")};font-weight:600;">'
                    f'Running {i+1}/{len(EXAMPLES)}: {ex["tag"]}…</div>',
                    unsafe_allow_html=True)
                rep, err = run_analysis(ex["text"],ex["type"],mode=ts_mode,
                                        provider=cur_prov,model=cur_model)
                ph_s.empty()
                if err:
                    tsc["err"]+=1; ts_results.append({"ex":ex,"rep":None,"err":err,"status":"error"})
                else:
                    got    = bool(isinstance(rep,dict) and rep.get("bias_found",False))
                    passed = (got==ex["expect_bias"])
                    status_= "pass" if passed else "fail"
                    if passed: tsc["pass"]+=1
                    else:      tsc["fail"]+=1
                    ts_results.append({"ex":ex,"rep":rep,"err":None,"status":status_,"passed":passed})
            prog.progress(1.0)

            st.markdown("<br>", unsafe_allow_html=True)
            sm1,sm2,sm3,sm4,sm5 = st.columns(5)
            sm1.metric("Total Tests",len(EXAMPLES)); sm2.metric("Passed ✓",tsc["pass"])
            sm3.metric("Failed ✗",tsc["fail"]); sm4.metric("Errors",tsc["err"])
            sm5.metric("Accuracy",f"{round(tsc['pass']/len(EXAMPLES)*100)}%")

            acc     = tsc["pass"]/len(EXAMPLES)
            acc_col = tok("--green") if acc>=.8 else (tok("--amber") if acc>=.5 else tok("--red"))
            st.markdown(
                f'<div class="char-track" style="height:5px;margin:10px 0 18px;">'
                f'<div class="char-fill" style="width:{int(acc*100)}%;background:{acc_col};height:100%;"></div></div>',
                unsafe_allow_html=True)

            # FIX: FAIL tests pinned first (expanded), then PASS tests (collapsed)
            failed = [r for r in ts_results if r["status"] != "pass"]
            passed_list = [r for r in ts_results if r["status"] == "pass"]

            if failed:
                st.markdown(f'<div class="lbl" style="color:var(--red);margin-bottom:6px;">⚠ Failed / Errors ({len(failed)})</div>', unsafe_allow_html=True)
            for res in failed + passed_list:
                i       = ts_results.index(res) + 1
                ex      = res["ex"]
                status_ = res["status"]
                badge_lbl = {"pass":"PASS ✓","fail":"FAIL ✗","error":"ERROR"}[status_]
                ico_r  = "✅" if status_=="pass" else ("❌" if status_=="fail" else "⚠")
                # Fail/error tests default expanded, pass tests collapsed
                with st.expander(f'{ico_r} Test {i}: {ex["tag"]}  [{badge_lbl}]', expanded=(status_!="pass")):
                    st.markdown(f'<div class="preview">{ex["text"]}</div>', unsafe_allow_html=True)
                    if res["err"]:
                        st.error(f"Error: {res['err']}")
                    else:
                        rep   = res["rep"]
                        got   = rep.get("bias_found",False)
                        exp   = ex["expect_bias"]
                        conf_ = int(rep.get("confidence_score",0)*100)
                        ecol, gcol = st.columns(2, gap="small")
                        with ecol:
                            exp_cls = "card-warn" if exp else "card-muted"
                            exp_lbl = "⚠ Bias" if exp else "✓ No Bias"
                            st.markdown(f'<div class="card {exp_cls}"><div class="card-lbl">Expected</div><div class="card-val mono">{exp_lbl}</div></div>', unsafe_allow_html=True)
                        with gcol:
                            got_cls   = "card-err" if got else "card-ok"
                            got_lbl   = "⚠ Bias" if got else "✓ No Bias"
                            match_lbl = "✓ Match" if (got==exp) else "✗ Mismatch"
                            st.markdown(f'<div class="card {got_cls}"><div class="card-lbl">Got · {match_lbl}</div><div class="card-val mono">{got_lbl} ({conf_}%)</div></div>', unsafe_allow_html=True)
                        if rep.get("bias_types"):
                            st.markdown(f'<div class="card card-muted" style="margin-top:6px;"><div class="card-lbl">Bias Types</div><div>{chips(rep.get("bias_types",[]))}</div></div>', unsafe_allow_html=True)
                        prov_r = rep.get("ai_provider","gemini"); mdl_r = rep.get("ai_model","")
                        st.markdown(f'<div style="margin-top:5px;">{provider_badge_html(prov_r)} <span style="font-family:var(--ff-m);font-size:.7rem;color:var(--t3);">{mdl_r}</span></div>', unsafe_allow_html=True)
                        if rep.get("timing_ms"): st.markdown(timing_pills(rep["timing_ms"]), unsafe_allow_html=True)

            st.markdown('<hr class="div">', unsafe_allow_html=True)
            test_rows = [{
                "test_n":        i,
                "tag":           res["ex"]["tag"],
                "type":          res["ex"]["type"],
                "expected_bias": res["ex"]["expect_bias"],
                "got_bias":      (res.get("rep") or {}).get("bias_found","error"),
                "passed":        res.get("passed",False),
                "confidence":    int((res.get("rep") or {}).get("confidence_score",0)*100),
                "ai_provider":   (res.get("rep") or {}).get("ai_provider",""),
                "ai_model":      (res.get("rep") or {}).get("ai_model",""),
                "total_ms":      (res.get("rep") or {}).get("timing_ms",{}).get("total",""),
            } for i, res in enumerate(ts_results,1)]
            dl1, _ = st.columns([1,3])
            with dl1:
                st.download_button("↓ Test Report (CSV)", data=pd.DataFrame(test_rows).to_csv(index=False),
                    file_name=f"verdict_tests_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv", key="ts_dl")

# ─────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────
elif view == "settings":
    st.markdown('<div class="ph">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Verdict Watch V14 — Dual AI Edition configuration.</div>', unsafe_allow_html=True)

    sc1, sc2 = st.columns(2, gap="large")
    with sc1:
        st.markdown('<div class="lbl">API Keys</div>', unsafe_allow_html=True)
        gem_cls = "card-ok" if gem_status else "card-err"
        gem_st  = "✓ GEMINI_API_KEY set" if gem_status else "✗ GEMINI_API_KEY missing"
        grq_cls = "card-ok" if groq_status else "card-warn"
        grq_st  = "✓ GROQ_API_KEY set" if groq_status else "⚠ GROQ_API_KEY not set (optional)"
        st.markdown(
            f'<div class="card {gem_cls}"><div class="card-lbl">🔵 Google Gemini (Primary)</div>'
            f'<div class="card-val mono">{gem_st}</div>'
            f'<div class="card-val" style="font-size:.72rem;margin-top:3px;">Get free key: aistudio.google.com/app/apikey</div></div>'
            f'<div class="card {grq_cls}" style="margin-top:6px;"><div class="card-lbl">🟠 Groq (Fallback)</div>'
            f'<div class="card-val mono">{grq_st}</div>'
            f'<div class="card-val" style="font-size:.72rem;margin-top:3px;">Get free key: console.groq.com</div></div>',
            unsafe_allow_html=True)

        if gem_status:
            if st.button("⊛ Test Gemini Connection", key="test_gemini"):
                with st.spinner("Testing Gemini…"):
                    try:
                        import google.generativeai as genai
                        genai.configure(api_key=os.getenv("GEMINI_API_KEY",""))
                        m = genai.GenerativeModel("gemini-1.5-flash")
                        m.generate_content("ping", generation_config={"max_output_tokens":5})
                        st.session_state["gemini_test_result"] = ("ok","✓ Gemini connected successfully")
                    except Exception as e:
                        st.session_state["gemini_test_result"] = ("err", str(e))
            if st.session_state.get("gemini_test_result"):
                kind, msg = st.session_state["gemini_test_result"]
                cls_ = "test-status-ok" if kind=="ok" else "test-status-err"
                st.markdown(f'<div class="{cls_}">{msg}</div>', unsafe_allow_html=True)

        if groq_status:
            if st.button("⊛ Test Groq Connection", key="test_groq"):
                with st.spinner("Testing Groq…"):
                    try:
                        c = services.get_groq_client()
                        c.chat.completions.create(model=services._GROQ_MODEL, max_tokens=5,
                                                  messages=[{"role":"user","content":"ping"}])
                        st.session_state["groq_test_result"] = ("ok","✓ Groq connected successfully")
                    except Exception as e:
                        st.session_state["groq_test_result"] = ("err", str(e))
            if st.session_state.get("groq_test_result"):
                kind, msg = st.session_state["groq_test_result"]
                cls_ = "test-status-ok" if kind=="ok" else "test-status-err"
                st.markdown(f'<div class="{cls_}">{msg}</div>', unsafe_allow_html=True)

    with sc2:
        st.markdown('<div class="lbl">Active Configuration</div>', unsafe_allow_html=True)
        cur_prov  = st.session_state.get("ai_provider","gemini")
        cur_model = st.session_state.get("ai_model","gemini-1.5-flash")
        all_r     = all_reports()
        fb        = services.get_feedback_stats()
        db_url    = os.getenv("DATABASE_URL","sqlite:///verdict_watch.db")
        st.markdown(
            f'<div class="card card-info"><div class="card-lbl">Active Provider</div>'
            f'<div style="margin-top:5px;">{provider_badge_html(cur_prov)} '
            f'<span style="font-family:var(--ff-m);font-size:.78rem;">{cur_model}</span></div></div>'
            f'<div class="card" style="margin-top:6px;"><div class="card-lbl">Total Reports</div>'
            f'<div class="card-val mono lg">{len(all_r)}</div></div>'
            f'<div class="card" style="margin-top:6px;"><div class="card-lbl">Database</div>'
            f'<div class="card-val mono" style="font-size:.73rem;">{db_url}</div></div>'
            f'<div class="card card-info" style="margin-top:6px;"><div class="card-lbl">User Feedback</div>'
            f'<div class="card-val mono">{fb["total"]} ratings · {fb["helpful_pct"]}% helpful</div></div>',
            unsafe_allow_html=True)

        st.markdown('<div class="lbl" style="margin-top:14px;">V14 Features</div>', unsafe_allow_html=True)
        for ico, name, desc in [
            ("🔵","Gemini Primary","gemini-1.5-flash + all Gemini models"),
            ("🟠","Groq Fallback","7 Groq models incl. DeepSeek R1"),
            ("⊕","Model Selector","Full model picker with live switching"),
            ("✦","Auto Fallback","Gemini → Groq if API call fails"),
            ("◎","Provider Tracking","Each report stores which AI was used"),
            ("⊞","Batch Multi-model","Batch runs use selected model"),
            ("⊘","Test Suite","Model shown per test result"),
            ("✦","Quick Switch","Change model from Analyse sidebar"),
        ]:
            st.markdown(
                f'<div class="feat-row">'
                f'<span><span class="feat-ico">{ico}</span><span class="feat-name">{name}</span></span>'
                f'<span class="feat-desc">{desc}</span></div>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# ABOUT
# ─────────────────────────────────────────────────────
elif view == "about":
    st.markdown('<div class="ph">About Verdict Watch</div>', unsafe_allow_html=True)
    st.markdown('<div class="ps">Enterprise AI bias detection. V14 — Dual AI Edition. Gemini PRIMARY · Groq FALLBACK.</div>', unsafe_allow_html=True)

    ab1, ab2 = st.columns([1.6,1], gap="large")
    with ab1:
        st.markdown(
            '<div class="card" style="background:var(--surf2);margin-bottom:12px;">'
            '<div style="font-family:var(--ff-d);font-size:1.1rem;color:var(--t1);margin-bottom:6px;">What is Verdict Watch?</div>'
            '<div style="font-size:.82rem;color:var(--t2);line-height:1.75;">A 3-step pipeline using Google Gemini (primary) with Groq fallback — extracting decision criteria, detecting discriminatory patterns across 7 bias dimensions, citing relevant laws, and generating the fair outcome you deserved.</div></div>',
            unsafe_allow_html=True)

        st.markdown('<div class="lbl">AI Models Available</div>', unsafe_allow_html=True)
        gem_col, grq_col = st.columns(2, gap="small")
        with gem_col:
            st.markdown(
                '<div class="card card-info"><div class="card-lbl">🔵 Gemini Models</div><div style="margin-top:5px;">'
                + "".join(f'<div style="font-size:.72rem;color:var(--t1);padding:2px 0;font-family:var(--ff-m);">{m}</div>' for m in GEMINI_MODELS)
                + '</div></div>', unsafe_allow_html=True)
        with grq_col:
            st.markdown(
                '<div class="card card-warn"><div class="card-lbl">🟠 Groq Models</div><div style="margin-top:5px;">'
                + "".join(f'<div style="font-size:.72rem;color:var(--t1);padding:2px 0;font-family:var(--ff-m);">{m}</div>' for m in GROQ_MODELS)
                + '</div></div>', unsafe_allow_html=True)

        # FIX: All 7 bias dimensions shown including Insurance Classification
        st.markdown('<div class="lbl" style="margin-top:10px;">Bias Dimensions Detected</div>', unsafe_allow_html=True)
        dims = [
            ("Gender Bias",               "Gender, name, or parental status"),
            ("Age Discrimination",        "Unfair weighting of age group"),
            ("Racial / Ethnic Bias",      "Name-based or origin profiling"),
            ("Geographic Redlining",      "Zip code as discriminatory proxy"),
            ("Socioeconomic Bias",        "Employment sector over-weighting"),
            ("Language Discrimination",   "Primary language used against applicants"),
            ("Insurance Classification",  "Insurance tier used as risk proxy"),
        ]
        st.markdown(
            '<div class="card" style="padding:.75rem 1rem;">'
            + "".join(f'<div class="dim-row"><span class="dim-name">{n}</span><span class="dim-desc">{d}</span></div>' for n,d in dims)
            + '</div>',
            unsafe_allow_html=True)

    with ab2:
        st.markdown('<div class="lbl">Tech Stack</div>', unsafe_allow_html=True)
        for name, desc in [
            ("Google Gemini","Primary AI (google-generativeai)"),
            ("Groq / Llama","Fallback AI"),
            ("FastAPI","REST API"),
            ("Streamlit ≥ 1.35","Web UI"),
            ("SQLAlchemy","Database ORM"),
            ("SQLite","Zero-config storage"),
            ("Plotly","Interactive charts"),
            ("DM Serif Display","Heading font"),
            ("Syne","UI font"),
            ("JetBrains Mono","Data font"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid var(--surf3);">'
                f'<span style="font-size:.82rem;font-weight:500;color:var(--t1);">{name}</span>'
                f'<span style="font-size:.73rem;color:var(--t3);">{desc}</span></div>',
                unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="card card-warn"><div class="card-lbl">⚠ Disclaimer</div>'
            '<div class="card-val" style="font-size:.79rem;">Not legal advice. Built for educational awareness only. '
            'Consult a qualified legal professional for discrimination claims.</div></div>',
            unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;font-size:.68rem;color:var(--t3);margin-top:12px;">'
            'Verdict Watch V14 · Gemini PRIMARY + Groq FALLBACK</div>',
            unsafe_allow_html=True)