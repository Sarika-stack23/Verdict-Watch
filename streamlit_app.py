"""
streamlit_app.py — Verdict Watch V3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NO separate API server needed.
Calls services.py directly — just run:
  streamlit run streamlit_app.py

V3 New Features:
  • Zero-server architecture (no uvicorn needed)
  • Inline Groq API key input
  • Appeals Letter Generator
  • Batch Analysis (multiple decisions at once)
  • Bias Radar Chart
  • CSV export from History
  • Severity badge system
  • V3 design refinements
"""

import streamlit as st
import services
import plotly.graph_objects as go
import pandas as pd
import re
import os
import io
import json
from datetime import datetime
from collections import Counter
from groq import Groq

# ── Hardcoded API key — no .env or sidebar input needed
os.environ["GROQ_API_KEY"] = "REMOVED_SECRET"

# ── Init DB once
services.init_db()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch V3",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS DESIGN SYSTEM (V3)
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

:root {
    --bg-base:     #080b12;
    --bg-surface:  #0e1320;
    --bg-elevated: #141926;
    --bg-card:     #1a2030;
    --border:      rgba(255,255,255,0.06);
    --border-med:  rgba(255,255,255,0.10);
    --accent:      #e8ff47;
    --accent-dim:  rgba(232,255,71,0.12);
    --red:         #ff4d4d;
    --red-dim:     rgba(255,77,77,0.12);
    --green:       #4dffb0;
    --green-dim:   rgba(77,255,176,0.10);
    --blue:        #4d9fff;
    --blue-dim:    rgba(77,159,255,0.10);
    --amber:       #ffb84d;
    --amber-dim:   rgba(255,184,77,0.10);
    --purple:      #c084fc;
    --purple-dim:  rgba(192,132,252,0.10);
    --text-primary:   #eef0f8;
    --text-secondary: #8892aa;
    --text-muted:     #4a5268;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: var(--bg-base);
    color: var(--text-primary);
}

[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-elevated);
    border-radius: 12px;
    padding: 4px;
    gap: 2px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    font-size: 0.88rem;
    color: var(--text-secondary);
    background: transparent;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #080b12 !important;
    font-weight: 700;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

.stButton > button {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 0.88rem;
    background: var(--accent);
    color: #080b12;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.6rem;
    width: 100%;
    transition: all 0.2s ease;
}
.stButton > button:hover { opacity: 0.85; transform: translateY(-1px); }

.stTextArea textarea {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.92rem !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    line-height: 1.7 !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-dim) !important;
}
.stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextInput > div > div > input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-med) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
}

[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
}
[data-testid="metric-container"] label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
    color: var(--text-primary) !important;
}

.stProgress > div > div { background: var(--accent) !important; border-radius: 4px; }
.stDownloadButton > button {
    background: var(--bg-card) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600;
    border-radius: 10px !important;
    width: 100%;
}
.stDownloadButton > button:hover { background: var(--accent-dim) !important; }
.streamlit-expanderHeader {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    background: var(--bg-card) !important;
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    color: var(--text-secondary) !important;
}

/* ── V3 Custom Components ── */
.vw-wordmark {
    font-family: 'Syne', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -1.5px;
    color: var(--text-primary);
    line-height: 1;
}
.vw-tagline {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-top: 0.4rem;
}
.vw-v3-badge {
    display: inline-block;
    background: var(--purple);
    color: #080b12;
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    letter-spacing: 2px;
    padding: 3px 7px;
    border-radius: 4px;
    vertical-align: middle;
    margin-left: 8px;
    position: relative;
    top: -5px;
}

.verdict-bias {
    background: var(--red-dim);
    border: 1px solid var(--red);
    border-radius: 16px;
    padding: 1.4rem 2rem;
    text-align: center;
    box-shadow: 0 0 40px rgba(255,77,77,0.12);
}
.verdict-clean {
    background: var(--green-dim);
    border: 1px solid var(--green);
    border-radius: 16px;
    padding: 1.4rem 2rem;
    text-align: center;
    box-shadow: 0 0 40px rgba(77,255,176,0.08);
}
.v-icon { font-size: 2rem; }
.v-label {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-top: 0.3rem;
}
.verdict-bias .v-label { color: var(--red); }
.verdict-clean .v-label { color: var(--green); }
.v-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0.2rem;
    opacity: 0.6;
}
.verdict-bias .v-sub { color: var(--red); }
.verdict-clean .v-sub { color: var(--green); }

.severity-high   { color: var(--red);    background: var(--red-dim);    border: 1px solid rgba(255,77,77,0.3);    border-radius: 6px; padding: 2px 10px; font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 1px; }
.severity-medium { color: var(--amber);  background: var(--amber-dim);  border: 1px solid rgba(255,184,77,0.3);  border-radius: 6px; padding: 2px 10px; font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 1px; }
.severity-low    { color: var(--green);  background: var(--green-dim);  border: 1px solid rgba(77,255,176,0.3);  border-radius: 6px; padding: 2px 10px; font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 1px; }

.info-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.5rem;
}
.info-card.red    { border-left: 3px solid var(--red); }
.info-card.green  { border-left: 3px solid var(--green); }
.info-card.amber  { border-left: 3px solid var(--amber); }
.info-card.blue   { border-left: 3px solid var(--blue); }
.info-card.purple { border-left: 3px solid var(--purple); }
.ic-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
}
.ic-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    color: var(--text-primary);
    line-height: 1.6;
}
.ic-value.mono {
    font-family: 'DM Mono', monospace;
    font-size: 1rem;
    font-weight: 500;
}

.chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    margin: 2px 3px 2px 0;
    letter-spacing: 0.5px;
}
.chip-red    { background: var(--red-dim);    color: #ff9090; border: 1px solid rgba(255,77,77,0.3); }
.chip-green  { background: var(--green-dim);  color: #80ffd0; border: 1px solid rgba(77,255,176,0.3); }
.chip-blue   { background: var(--blue-dim);   color: #80c4ff; border: 1px solid rgba(77,159,255,0.3); }
.chip-amber  { background: var(--amber-dim);  color: #ffd480; border: 1px solid rgba(255,184,77,0.3); }
.chip-purple { background: var(--purple-dim); color: #e0b4ff; border: 1px solid rgba(192,132,252,0.3); }
.chip-muted  { background: rgba(255,255,255,0.05); color: var(--text-secondary); border: 1px solid var(--border); }

.rec-item {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.6rem;
}
.rec-num {
    background: var(--accent);
    color: #080b12;
    border-radius: 6px;
    min-width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    font-weight: 500;
    flex-shrink: 0;
    margin-top: 2px;
}
.rec-text {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.92rem;
    color: var(--text-secondary);
    line-height: 1.55;
}

/* Appeals letter box */
.appeal-box {
    background: var(--bg-card);
    border: 1px solid var(--purple);
    border-radius: 14px;
    padding: 1.5rem 2rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    line-height: 1.9;
    color: var(--text-secondary);
    white-space: pre-wrap;
    box-shadow: 0 0 30px rgba(192,132,252,0.08);
}

/* Batch table */
.batch-row-bias  { background: rgba(255,77,77,0.06); }
.batch-row-clean { background: rgba(77,255,176,0.04); }

.sec-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.7rem;
}
.divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }

.highlight-box {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.93rem;
    line-height: 1.8;
    color: var(--text-secondary);
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
}
.highlight-box mark {
    background: rgba(255,77,77,0.18);
    color: #ff9090;
    border-radius: 4px;
    padding: 1px 4px;
}

.status-pill-ok {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--green-dim); border: 1px solid rgba(77,255,176,0.3);
    color: var(--green); border-radius: 999px; padding: 4px 14px;
    font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 1px;
}
.status-pill-warn {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--amber-dim); border: 1px solid rgba(255,184,77,0.3);
    color: var(--amber); border-radius: 999px; padding: 4px 14px;
    font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 1px;
}
.status-pill-err {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--red-dim); border: 1px solid rgba(255,77,77,0.3);
    color: var(--red); border-radius: 999px; padding: 4px 14px;
    font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 1px;
}

.how-step { display: flex; gap: 0.8rem; align-items: flex-start; margin-bottom: 0.7rem; }
.how-num  { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: var(--accent); min-width: 18px; padding-top: 2px; }
.how-text { font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; }

.compare-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.4rem;
}
.footer-bar {
    text-align: center;
    font-family: 'DM Mono', monospace;
    font-size: 0.66rem;
    letter-spacing: 1.5px;
    color: var(--text-muted);
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    text-transform: uppercase;
}

/* Grade badge */
.grade-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px; height: 64px;
    border-radius: 14px;
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    border: 2px solid currentColor;
}

/* Sentence bias row */
.sent-row {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    line-height: 1.6;
    padding: 0.55rem 0.9rem;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    border-left: 3px solid transparent;
}
.sent-row.flagged {
    background: rgba(255,77,77,0.07);
    border-left-color: var(--red);
    color: var(--text-primary);
}
.sent-row.clean {
    background: rgba(255,255,255,0.02);
    border-left-color: rgba(255,255,255,0.05);
    color: var(--text-secondary);
}
.sent-dims {
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 1px;
    color: #ff9090;
    margin-top: 2px;
}

/* Legal ref card */
.legal-card {
    background: var(--bg-card);
    border: 1px solid rgba(77,159,255,0.2);
    border-left: 3px solid var(--blue);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.4rem;
}
.legal-dim   { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 2px; color: var(--blue); text-transform: uppercase; }
.legal-text  { font-family: 'DM Sans', sans-serif; font-size: 0.82rem; color: var(--text-secondary); margin-top: 3px; }
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
    {"tag": "Bank Loan", "emoji": "🏦", "type": "loan",
     "text": ("Your loan application has been declined. Primary reasons: insufficient credit history, "
              "residential area risk score, employment sector classification. "
              "You may reapply after 6 months.")},
    {"tag": "Medical Triage", "emoji": "🏥", "type": "medical",
     "text": ("Based on your intake assessment you have been assigned Priority Level 3. "
              "Factors considered: age group, reported pain level, primary language, insurance classification.")},
    {"tag": "University", "emoji": "🎓", "type": "university",
     "text": ("We regret to inform you that your application for admission has not been successful. "
              "Our admissions committee considered zip code region diversity metrics, legacy status, "
              "and extracurricular profile alignment when making this decision.")},
]

TYPE_LABELS = {
    "job":        "💼 Job Application",
    "loan":       "🏦 Bank Loan",
    "medical":    "🏥 Medical / Triage",
    "university": "🎓 University Admission",
    "other":      "📄 Other",
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

CHIP_STYLES = ["chip-red", "chip-amber", "chip-blue", "chip-green", "chip-purple"]
BIAS_DIMS   = ["Gender", "Age", "Racial", "Geographic", "Socioeconomic", "Language", "Insurance"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "")

def set_env_key():
    pass  # key is already set at module level

def check_groq_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY", ""))


def run_analysis(text: str, dtype: str) -> tuple:
    """Run full pipeline — returns (report_dict, error_str | None)."""
    set_env_key()
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


def generate_appeal_letter(report: dict, decision_text: str, decision_type: str) -> str:
    """V3: Generate a formal appeal letter via Groq."""
    set_env_key()
    client = services.get_groq_client()
    bias_types = ", ".join(report.get("bias_types", [])) or "undisclosed bias"
    affected   = report.get("affected_characteristic", "a protected characteristic")
    explanation = report.get("explanation", "")
    fair_outcome = report.get("fair_outcome", "a fair reassessment")

    system = (
        "You are an expert legal writer specialising in discrimination and bias cases. "
        "Write formal, persuasive appeal letters in plain English. "
        "Use [DATE], [YOUR NAME], [YOUR ADDRESS], [RECIPIENT NAME/TITLE], [ORGANISATION] "
        "as placeholders. Write in first person."
    )
    prompt = (
        f"Write a formal appeal letter based on these facts:\n\n"
        f"Decision type: {decision_type}\n"
        f"Original decision text: {decision_text}\n"
        f"Bias detected: {bias_types}\n"
        f"Characteristic affected: {affected}\n"
        f"What was wrong: {explanation}\n"
        f"What fair outcome should be: {fair_outcome}\n\n"
        "The letter should: open professionally, reference the specific decision, "
        "clearly state grounds for appeal citing the discriminatory factors, "
        "request a formal review, and close professionally. "
        "Keep it under 400 words."
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


def chips_html(items, style="auto"):
    if not items:
        return '<span class="chip chip-muted">None detected</span>'
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


def severity_badge(conf: float, bias_found: bool) -> str:
    if not bias_found:
        return '<span class="severity-low">LOW RISK</span>'
    if conf >= 0.75:
        return '<span class="severity-high">HIGH SEVERITY</span>'
    if conf >= 0.45:
        return '<span class="severity-medium">MEDIUM SEVERITY</span>'
    return '<span class="severity-low">LOW SEVERITY</span>'


LEGAL_REFS = {
    "Gender":        "Equality Act 2010 (UK) · Title VII Civil Rights Act (US) · EU Equal Treatment Directive 2006/54/EC",
    "Age":           "Age Discrimination in Employment Act (US) · Equality Act 2010 s.5 (UK) · EU Directive 2000/78/EC",
    "Racial":        "Race Relations Act / Equality Act 2010 (UK) · Civil Rights Act Title VI (US) · ICERD",
    "Geographic":    "Fair Housing Act (US) · EU Anti-Discrimination Directives · ECHR Article 14",
    "Socioeconomic": "Equality Act 2010 s.1 (UK) · ECHR Protocol 12 · ILO Discrimination Convention 111",
    "Language":      "Title VI Civil Rights Act (US) · EU Charter Article 21 · ECHR Article 14",
    "Insurance":     "ACA Section 1557 (US) · Equality Act 2010 (UK) · EU Gender Goods & Services Directive",
}

FAIRNESS_GRADES = [
    (0.0,  0.15, "A", "#4dffb0", "Likely fair — no strong discriminatory signals detected."),
    (0.15, 0.35, "B", "#80ffd0", "Mostly fair — minor indicators worth monitoring."),
    (0.35, 0.55, "C", "#ffb84d", "Questionable — moderate bias signals present."),
    (0.55, 0.75, "D", "#ff9090", "Likely biased — significant discriminatory factors found."),
    (0.75, 1.01, "F", "#ff4d4d", "Highly biased — strong discriminatory patterns detected."),
]

def fairness_grade(confidence: float, bias_found: bool) -> tuple:
    """Returns (grade, color, description)."""
    if not bias_found:
        return "A", "#4dffb0", "Likely fair — no strong discriminatory signals detected."
    for lo, hi, grade, color, desc in FAIRNESS_GRADES:
        if lo <= confidence < hi:
            return grade, color, desc
    return "F", "#ff4d4d", "Highly biased — strong discriminatory patterns detected."


def get_legal_refs(bias_types: list) -> list:
    """Return relevant legal references for detected bias types."""
    refs = []
    for bt in bias_types:
        for dim, ref in LEGAL_REFS.items():
            if dim.lower() in bt.lower() and ref not in refs:
                refs.append((dim, ref))
    return refs


def extract_bias_sentences(text: str, bias_types: list) -> list:
    """Split text into sentences and flag which ones contain bias keywords."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    flagged = []
    for sent in sentences:
        matched = []
        for bt in bias_types:
            for dim, pat in BIAS_KEYWORDS.items():
                if dim.lower() in bt.lower():
                    if re.search(pat, sent, re.IGNORECASE):
                        matched.append(dim)
        flagged.append({"sentence": sent, "bias_dims": list(set(matched))})
    return flagged


def generate_rebuttal_points(report: dict, decision_text: str) -> str:
    """Generate bullet-point rebuttal arguments via Groq."""
    set_env_key()
    client = services.get_groq_client()
    bias_types  = ", ".join(report.get("bias_types", [])) or "undisclosed"
    affected    = report.get("affected_characteristic", "protected characteristic")
    explanation = report.get("explanation", "")
    system = (
        "You are an expert in employment law and discrimination cases. "
        "Generate a concise numbered list of strong rebuttal arguments the applicant "
        "can use when challenging the decision. Be specific and legally grounded. "
        "Return plain text, numbered 1-5, no markdown."
    )
    prompt = (
        f"Decision text: {decision_text}\n"
        f"Bias types found: {bias_types}\n"
        f"Characteristic affected: {affected}\n"
        f"What went wrong: {explanation}\n\n"
        "Write 5 specific rebuttal points the person can raise in an appeal or complaint."
    )
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile", max_tokens=600,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


# ─── Charts ───────────────────────────────────

def gauge_chart(value, bias_found):
    color = "#ff4d4d" if bias_found else "#4dffb0"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(value * 100),
        number={"suffix": "%", "font": {"family": "Syne", "size": 30, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "transparent",
                     "tickfont": {"color": "#4a5268", "size": 9}},
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "#1a2030",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  33],  "color": "rgba(77,255,176,0.05)"},
                {"range": [33, 66],  "color": "rgba(255,184,77,0.05)"},
                {"range": [66, 100], "color": "rgba(255,77,77,0.05)"},
            ],
            "threshold": {"line": {"color": color, "width": 2.5},
                          "thickness": 0.7, "value": value * 100},
        },
    ))
    fig.update_layout(
        height=180, margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Syne"},
    )
    return fig


def radar_chart(all_reports: list):
    """V3: Radar chart of bias dimension frequency across all reports."""
    dim_counts = {d: 0 for d in BIAS_DIMS}
    for r in all_reports:
        for bt in r.get("bias_types", []):
            for dim in BIAS_DIMS:
                if dim.lower() in bt.lower():
                    dim_counts[dim] += 1

    vals   = [dim_counts[d] for d in BIAS_DIMS]
    labels = BIAS_DIMS

    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(232,255,71,0.07)",
        line=dict(color="#e8ff47", width=2),
        marker=dict(color="#e8ff47", size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, color="#4a5268",
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(family="DM Mono", size=9, color="#4a5268"),
            ),
            angularaxis=dict(
                color="#8892aa",
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(family="DM Mono", size=10, color="#8892aa"),
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=50, r=50, t=30, b=30),
        showlegend=False,
    )
    return fig


def pie_chart(bias_count, clean_count):
    total = bias_count + clean_count or 2
    fig = go.Figure(go.Pie(
        labels=["Bias Detected", "No Bias Found"],
        values=[bias_count or 1, clean_count or 1],
        hole=0.68,
        marker=dict(colors=["#ff4d4d", "#4dffb0"],
                    line=dict(color="#080b12", width=3)),
        textfont=dict(family="DM Mono", size=11),
        textinfo="percent",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size:10px'>TOTAL</span>",
        x=0.5, y=0.5,
        font=dict(family="Syne", size=20, color="#eef0f8"),
        showarrow=False,
    )
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(family="DM Mono", size=10, color="#8892aa"),
                    bgcolor="rgba(0,0,0,0)", orientation="h",
                    x=0.5, xanchor="center", y=-0.05),
    )
    return fig


def bar_chart(all_types):
    if not all_types:
        all_types = ["No data"]
    counts = Counter(all_types)
    labels, values = zip(*counts.most_common()) if counts else (["None"], [0])
    colors = ["#ff4d4d", "#ffb84d", "#4d9fff", "#4dffb0", "#c084fc", "#f87171", "#fb923c"]
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=colors[:len(labels)], line=dict(width=0)),
        text=list(values),
        textfont=dict(family="DM Mono", size=11, color="#eef0f8"),
        textposition="outside",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=max(200, len(labels) * 46 + 60),
        margin=dict(l=10, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                   tickfont=dict(family="DM Mono", size=10, color="#4a5268"), zeroline=False),
        yaxis=dict(tickfont=dict(family="DM Mono", size=10, color="#8892aa"),
                   gridcolor="rgba(0,0,0,0)"),
        bargap=0.38,
    )
    return fig


def histogram_chart(scores):
    if not scores:
        scores = [0]
    fig = go.Figure(go.Histogram(
        x=[s * 100 for s in scores], nbinsx=10,
        marker=dict(color="#e8ff47", opacity=0.7, line=dict(color="#080b12", width=1)),
        hovertemplate="~%{x:.0f}%: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=220, margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Confidence %",
                              font=dict(family="DM Mono", size=10, color="#4a5268")),
                   tickfont=dict(family="DM Mono", size=10, color="#4a5268"),
                   gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(tickfont=dict(family="DM Mono", size=10, color="#4a5268"),
                   gridcolor="rgba(255,255,255,0.04)"),
    )
    return fig


def timeline_chart(bias_flags):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(bias_flags))),
        y=[1 if b else 0 for b in bias_flags],
        mode="markers+lines",
        marker=dict(color=["#ff4d4d" if b else "#4dffb0" for b in bias_flags],
                    size=10, line=dict(color="#080b12", width=2)),
        line=dict(color="rgba(255,255,255,0.07)", width=1.5),
        hovertemplate="#%{x}: %{text}<extra></extra>",
        text=["Bias" if b else "Clean" for b in bias_flags],
    ))
    fig.update_layout(
        height=200, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(tickvals=[0, 1], ticktext=["Clean", "Bias"],
                   tickfont=dict(family="DM Mono", size=10, color="#4a5268"),
                   gridcolor="rgba(255,255,255,0.04)"),
        xaxis=dict(tickfont=dict(family="DM Mono", size=10, color="#4a5268"),
                   gridcolor="rgba(255,255,255,0.04)"),
    )
    return fig


# ─── Report builders ───────────────────────────

def build_txt_report(report, text, dtype):
    recs  = report.get("recommendations", [])
    lines = [
        "=" * 64, "     VERDICT WATCH V3 — BIAS ANALYSIS REPORT", "=" * 64,
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Type      : {dtype.upper()}",
        f"Report ID : {report.get('id', 'N/A')}", "",
        "── ORIGINAL DECISION TEXT ──", text, "",
        "── VERDICT ─────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence: {int(report.get('confidence_score', 0) * 100)}%", "",
        "── BIAS TYPES ──────────────────────────────────────────────",
        ", ".join(report.get("bias_types", [])) or "None detected", "",
        "── CHARACTERISTIC AFFECTED ─────────────────────────────────",
        report.get("affected_characteristic", "N/A"), "",
        "── ORIGINAL OUTCOME ────────────────────────────────────────",
        report.get("original_outcome", "N/A"), "",
        "── FAIR OUTCOME ────────────────────────────────────────────",
        report.get("fair_outcome", "N/A"), "",
        "── EXPLANATION ─────────────────────────────────────────────",
        report.get("explanation", "N/A"), "",
        "── NEXT STEPS ──────────────────────────────────────────────",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    lines += ["", "=" * 64,
              "  Verdict Watch V3  ·  Groq / Llama 3.3 70B  ·  Not legal advice",
              "=" * 64]
    return "\n".join(lines)


def build_compare_txt(r1, r2, t1, t2):
    def fmt(r, t, lbl):
        return [f"── Decision {lbl} ──────────────────────────────────────────",
                f"Text    : {t[:140]}...",
                f"Verdict : {'BIAS DETECTED' if r.get('bias_found') else 'NO BIAS FOUND'}",
                f"Confidence: {int(r.get('confidence_score', 0) * 100)}%",
                f"Bias Types: {', '.join(r.get('bias_types', [])) or 'None'}",
                f"Fair Outcome: {r.get('fair_outcome', 'N/A')}", ""]
    lines = ["=" * 64, "  VERDICT WATCH V3 — COMPARISON REPORT", "=" * 64,
             f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    lines += fmt(r1, t1, "A") + fmt(r2, t2, "B")
    lines += ["=" * 64, "  Not legal advice.", "=" * 64]
    return "\n".join(lines)


def reports_to_csv(reports: list) -> str:
    rows = []
    for r in reports:
        rows.append({
            "id":                   r.get("id", ""),
            "created_at":           (r.get("created_at") or "")[:16],
            "bias_found":           r.get("bias_found", False),
            "confidence_pct":       int(r.get("confidence_score", 0) * 100),
            "bias_types":           "; ".join(r.get("bias_types", [])),
            "affected_characteristic": r.get("affected_characteristic", ""),
            "original_outcome":     r.get("original_outcome", ""),
            "fair_outcome":         r.get("fair_outcome", ""),
            "explanation":          r.get("explanation", ""),
            "recommendations":      " | ".join(r.get("recommendations", [])),
        })
    return pd.DataFrame(rows).to_csv(index=False)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne,sans-serif; font-size:1.05rem; font-weight:700; color:#eef0f8;">'
        '⚖️ Verdict Watch '
        '<span style="background:#c084fc; color:#080b12; font-family:DM Mono,monospace; '
        'font-size:0.55rem; padding:2px 6px; border-radius:3px; letter-spacing:1px; '
        'vertical-align:middle; position:relative; top:-2px;">V3</span></div>'
        '<div style="font-family:DM Sans,sans-serif; font-size:0.78rem; color:#4a5268; '
        'line-height:1.5; margin-top:0.3rem; margin-bottom:1rem;">'
        'AI-powered bias detection. No server required.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        '<div style="font-family:DM Mono,monospace; font-size:0.6rem; letter-spacing:2.5px; '
        'text-transform:uppercase; color:#4a5268; margin-bottom:0.5rem;">Quick Examples</div>',
        unsafe_allow_html=True,
    )
    for ex in EXAMPLES:
        if st.button(f"{ex['emoji']} {ex['tag']}", key=f"ex_{ex['type']}"):
            st.session_state["prefill_text"] = ex["text"]
            st.session_state["prefill_type"] = ex["type"]
            st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-family:DM Mono,monospace; font-size:0.6rem; letter-spacing:2.5px; '
        'text-transform:uppercase; color:#4a5268; margin-bottom:0.6rem;">How It Works</div>',
        unsafe_allow_html=True,
    )
    for n, t in [
        ("01", "Paste any rejection or denial letter"),
        ("02", "AI extracts the criteria used"),
        ("03", "Scans for 7+ bias dimensions"),
        ("04", "Generates what was fair"),
        ("05", "Optional: generate appeal letter"),
        ("06", "Shows actionable next steps"),
    ]:
        st.markdown(
            f'<div class="how-step"><div class="how-num">{n}</div>'
            f'<div class="how-text">{t}</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="vw-wordmark">⚖ Verdict Watch'
    '<span class="vw-v3-badge">V3</span></div>'
    '<div class="vw-tagline">AI-powered bias detection for automated decisions</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_analyse, tab_dashboard, tab_history, tab_compare, tab_batch, tab_about = st.tabs([
    "⚡ Analyse", "📊 Dashboard", "📋 History", "⚖️ Compare", "📦 Batch", "ℹ About",
])


# ═══════════════════════════════════════════════
# TAB 1 — ANALYSE
# ═══════════════════════════════════════════════

with tab_analyse:
    prefill_text = st.session_state.get("prefill_text", "")
    prefill_type = st.session_state.get("prefill_type", "job")

    col_form, _ = st.columns([3, 1])
    with col_form:
        st.markdown('<div class="sec-label">Your Decision Letter</div>', unsafe_allow_html=True)
        decision_text = st.text_area(
            "Decision letter", label_visibility="collapsed",
            value=prefill_text, height=200, key="decision_input",
            placeholder=(
                "Paste the rejection letter, loan denial, medical triage result, "
                "or any automated decision here...\n\n"
                "Tip: Use the sidebar examples to try instantly."
            ),
        )
        st.markdown('<div class="sec-label" style="margin-top:0.8rem;">Decision Type</div>',
                    unsafe_allow_html=True)
        dc1, dc2 = st.columns([2, 1])
        with dc1:
            type_opts    = ["job", "loan", "medical", "university", "other"]
            decision_type = st.selectbox(
                "Type", label_visibility="collapsed", options=type_opts,
                format_func=lambda x: TYPE_LABELS[x],
                index=type_opts.index(prefill_type) if prefill_type in type_opts else 0,
                key="decision_type",
            )
        with dc2:
            n = len(decision_text.strip())
            st.markdown(
                f'<div style="padding-top:0.75rem; font-family:DM Mono,monospace; font-size:0.7rem; '
                f'color:{"#4dffb0" if n > 50 else "#ff4d4d"};">'
                f'{n} chars {"✓" if n > 50 else "— add more"}</div>',
                unsafe_allow_html=True,
            )
        analyse_btn = st.button("⚡ Run Bias Analysis", key="analyse_btn")

    if analyse_btn:
        st.session_state.pop("prefill_text", None)
        st.session_state.pop("prefill_type", None)
        if not decision_text.strip():
            st.warning("⚠️ Please paste a decision text first.")
        elif not check_groq_key():
            st.error("❌ No Groq API key. Add it in the sidebar or your .env file.")
        else:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            with st.spinner("Running 3-step AI analysis..."):
                report, err = run_analysis(decision_text, decision_type)

            if err:
                st.error(f"❌ {err}")
            elif report:
                bias_found  = report.get("bias_found", False)
                confidence  = report.get("confidence_score", 0.0)
                bias_types  = report.get("bias_types", [])
                affected    = report.get("affected_characteristic", "")
                orig        = report.get("original_outcome", "N/A")
                fair        = report.get("fair_outcome", "N/A")
                explanation = report.get("explanation", "")
                recs        = report.get("recommendations", [])

                # ── Verdict Banner
                if bias_found:
                    st.markdown(
                        '<div class="verdict-bias"><div class="v-icon">⚠️</div>'
                        '<div class="v-label">BIAS DETECTED</div>'
                        '<div class="v-sub">Decision shows discriminatory patterns</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="verdict-clean"><div class="v-icon">✅</div>'
                        '<div class="v-label">NO BIAS FOUND</div>'
                        '<div class="v-sub">Decision appears free of discriminatory factors</div></div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("<br>", unsafe_allow_html=True)

                # ── Gauge + Meta + Outcomes
                r1c, r2c, r3c = st.columns([1.2, 1.4, 1.4])

                with r1c:
                    st.markdown('<div class="sec-label">Confidence Score</div>', unsafe_allow_html=True)
                    st.plotly_chart(gauge_chart(confidence, bias_found),
                                    use_container_width=True, config={"displayModeBar": False})
                    st.markdown(severity_badge(confidence, bias_found), unsafe_allow_html=True)

                with r2c:
                    st.markdown('<div class="sec-label">Bias Types Found</div>', unsafe_allow_html=True)
                    st.markdown(chips_html(bias_types) if bias_types
                                else '<span class="chip chip-green">None detected</span>',
                                unsafe_allow_html=True)
                    if affected:
                        st.markdown(
                            f'<div style="margin-top:0.8rem;">'
                            f'<div class="sec-label">Characteristic Affected</div>'
                            f'<div style="font-family:DM Mono,monospace; font-size:0.88rem; '
                            f'color:#ffb84d;">{affected}</div></div>',
                            unsafe_allow_html=True,
                        )

                with r3c:
                    st.markdown(
                        f'<div class="info-card red" style="margin-bottom:0.6rem;">'
                        f'<div class="ic-label">Original Decision</div>'
                        f'<div class="ic-value mono">{orig.upper()}</div></div>'
                        f'<div class="info-card green">'
                        f'<div class="ic-label">Should Have Been</div>'
                        f'<div class="ic-value">{fair}</div></div>',
                        unsafe_allow_html=True,
                    )

                # ── Bias Phrase Highlighter
                if bias_types and decision_text.strip():
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">🔍 Bias Phrase Highlighter</div>',
                                unsafe_allow_html=True)
                    highlighted = highlight_text(decision_text, bias_types)
                    st.markdown(
                        f'<div class="highlight-box">{highlighted}</div>'
                        f'<div style="font-family:DM Mono,monospace; font-size:0.62rem; '
                        f'color:#4a5268; margin-top:0.4rem; letter-spacing:1px;">'
                        f'HIGHLIGHTED WORDS ARE COMMON PROXIES FOR PROTECTED CHARACTERISTICS</div>',
                        unsafe_allow_html=True,
                    )

                # ── Explanation
                if explanation:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">What Happened — Plain English</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="info-card amber">'
                        f'<div class="ic-value">{explanation}</div></div>',
                        unsafe_allow_html=True,
                    )

                # ── Fairness Grade
                grade, gcolor, gdesc = fairness_grade(confidence, bias_found)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">🎓 Fairness Grade</div>', unsafe_allow_html=True)
                gc1, gc2 = st.columns([1, 5])
                with gc1:
                    st.markdown(
                        f'<div class="grade-badge" style="color:{gcolor}; border-color:{gcolor};">'
                        f'{grade}</div>',
                        unsafe_allow_html=True,
                    )
                with gc2:
                    st.markdown(
                        f'<div style="padding-top:0.6rem; font-family:DM Sans,sans-serif; '
                        f'font-size:0.92rem; color:{gcolor}; font-weight:600;">{gdesc}</div>',
                        unsafe_allow_html=True,
                    )

                # ── Sentence-level Bias Breakdown
                if bias_types and decision_text.strip():
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">🔬 Sentence-Level Bias Breakdown</div>',
                                unsafe_allow_html=True)
                    flagged_sents = extract_bias_sentences(decision_text, bias_types)
                    for item in flagged_sents:
                        if item["bias_dims"]:
                            dims_str = " · ".join(item["bias_dims"]).upper()
                            st.markdown(
                                f'<div class="sent-row flagged">{item["sentence"]}'
                                f'<div class="sent-dims">⚑ {dims_str}</div></div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div class="sent-row clean">{item["sentence"]}</div>',
                                unsafe_allow_html=True,
                            )

                # ── Legal References
                legal_refs = get_legal_refs(bias_types)
                if legal_refs:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">⚖️ Relevant Laws & Protections</div>',
                                unsafe_allow_html=True)
                    for dim, ref in legal_refs:
                        st.markdown(
                            f'<div class="legal-card">'
                            f'<div class="legal-dim">{dim} Bias</div>'
                            f'<div class="legal-text">{ref}</div></div>',
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

                # ── Rebuttal Points Generator
                if bias_found:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="sec-label">🗣️ Rebuttal Points Generator</div>',
                                unsafe_allow_html=True)
                    st.markdown(
                        '<div style="font-family:DM Sans,sans-serif; font-size:0.85rem; '
                        'color:#8892aa; margin-bottom:0.8rem;">AI-generated arguments you can '
                        'use when challenging this decision verbally or in writing.</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("🗣️ Generate Rebuttal Points", key="rebuttal_btn"):
                        with st.spinner("Building your arguments..."):
                            try:
                                rb = generate_rebuttal_points(report, decision_text)
                                st.session_state["rebuttal_points"] = rb
                            except Exception as e:
                                st.error(f"❌ {e}")
                    if st.session_state.get("rebuttal_points"):
                        st.markdown(
                            f'<div class="appeal-box">{st.session_state["rebuttal_points"]}</div>',
                            unsafe_allow_html=True,
                        )

                # ── V3: Appeals Letter Generator
                if bias_found:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(
                        '<div class="sec-label">✉️ Appeals Letter Generator — New in V3</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        '<div style="font-family:DM Sans,sans-serif; font-size:0.85rem; '
                        'color:#8892aa; margin-bottom:0.8rem;">Generate a formal appeal '
                        'letter you can send to the decision-maker. Fill in the '
                        '[PLACEHOLDERS] before sending.</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("✉️ Generate Appeal Letter", key="appeal_btn"):
                        with st.spinner("Drafting your appeal letter..."):
                            try:
                                letter = generate_appeal_letter(
                                    report, decision_text, decision_type
                                )
                                st.session_state["appeal_letter"] = letter
                            except Exception as e:
                                st.error(f"❌ {e}")

                    if st.session_state.get("appeal_letter"):
                        letter = st.session_state["appeal_letter"]
                        st.markdown(
                            f'<div class="appeal-box">{letter}</div>',
                            unsafe_allow_html=True,
                        )
                        al1, _ = st.columns([1, 2])
                        with al1:
                            st.download_button(
                                "📥 Download Appeal Letter (.txt)",
                                data=letter,
                                file_name=f"appeal_letter_{report.get('id','')[:8]}.txt",
                                mime="text/plain",
                                key="dl_appeal",
                            )

                # ── Downloads
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

                st.session_state["last_report"] = report
                st.session_state["last_text"]   = decision_text


# ═══════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ═══════════════════════════════════════════════

with tab_dashboard:
    hist = get_all_reports()

    if not hist:
        st.info("No analyses yet. Run your first analysis in the Analyse tab.")
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
        m1.metric("Total Analyses",  len(hist))
        m2.metric("Bias Rate",       f"{bias_rate:.0f}%")
        m3.metric("Avg Confidence",  f"{avg_conf:.0f}%")
        m4.metric("Top Bias Type",   top_bias)

        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sec-label">Verdicts Distribution</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(pie_chart(len(bias_reps), len(clean_reps)),
                            use_container_width=True, config={"displayModeBar": False})
        with c2:
            st.markdown('<div class="sec-label">Bias Types Frequency</div>',
                        unsafe_allow_html=True)
            if all_types:
                st.plotly_chart(bar_chart(all_types),
                                use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No bias types detected yet.")

        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="sec-label">Confidence Distribution</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(histogram_chart(scores),
                            use_container_width=True, config={"displayModeBar": False})
        with c4:
            st.markdown('<div class="sec-label">Analysis Timeline</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(timeline_chart(bflags),
                            use_container_width=True, config={"displayModeBar": False})

        # ── V3: Bias Radar Chart
        st.markdown("<br>", unsafe_allow_html=True)
        rad_col, char_col = st.columns([1, 1])
        with rad_col:
            st.markdown('<div class="sec-label">🕸 Bias Dimension Radar — New in V3</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(radar_chart(hist),
                            use_container_width=True, config={"displayModeBar": False})
        with char_col:
            st.markdown('<div class="sec-label">Affected Characteristics</div>',
                        unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist
                     if r.get("affected_characteristic")]
            if chars:
                cdf = pd.DataFrame([
                    {"Characteristic": k, "Count": v,
                     "% of Analyses": f"{v / len(hist) * 100:.0f}%"}
                    for k, v in Counter(chars).most_common()
                ])
                st.dataframe(cdf, use_container_width=True, hide_index=True)
            else:
                st.info("No characteristic data yet.")


# ═══════════════════════════════════════════════
# TAB 3 — HISTORY
# ═══════════════════════════════════════════════

with tab_history:
    hist = get_all_reports()

    if not hist:
        st.info("No analyses yet. Head to the Analyse tab to get started.")
    else:
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            search_q = st.text_input(
                "search", label_visibility="collapsed",
                placeholder="Search by characteristic or bias type...",
                key="history_search",
            )
        with f2:
            filt_v = st.selectbox("verdict", ["All", "Bias Detected", "No Bias"],
                                   label_visibility="collapsed", key="history_filter")
        with f3:
            sort_by = st.selectbox(
                "sort",
                ["Newest First", "Oldest First", "Highest Confidence", "Lowest Confidence"],
                label_visibility="collapsed", key="history_sort",
            )

        filtered = hist[:]
        if filt_v == "Bias Detected":
            filtered = [r for r in filtered if r.get("bias_found")]
        elif filt_v == "No Bias":
            filtered = [r for r in filtered if not r.get("bias_found")]
        if search_q:
            sq = search_q.lower()
            filtered = [r for r in filtered
                        if sq in (r.get("affected_characteristic") or "").lower()
                        or any(sq in bt.lower() for bt in r.get("bias_types", []))]
        if sort_by == "Newest First":
            filtered.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sort_by == "Oldest First":
            filtered.sort(key=lambda r: r.get("created_at") or "")
        elif sort_by == "Highest Confidence":
            filtered.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
        else:
            filtered.sort(key=lambda r: r.get("confidence_score", 0))

        hdr1, hdr2 = st.columns([3, 1])
        with hdr1:
            st.markdown(
                f'<div style="font-family:DM Mono,monospace; font-size:0.68rem; '
                f'color:#4a5268; margin-bottom:1rem; letter-spacing:1px;">'
                f'SHOWING {len(filtered)} OF {len(hist)}</div>',
                unsafe_allow_html=True,
            )
        with hdr2:
            # ── V3: CSV Export
            st.download_button(
                "📥 Export CSV",
                data=reports_to_csv(filtered),
                file_name=f"verdict_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="csv_export",
            )

        for r in filtered:
            bias     = r.get("bias_found", False)
            conf     = int(r.get("confidence_score", 0) * 100)
            affected = r.get("affected_characteristic") or "—"
            b_types  = r.get("bias_types", [])
            created  = (r.get("created_at") or "")[:16].replace("T", " ")

            with st.expander(
                f'{"⚠️ BIAS" if bias else "✅ CLEAN"}  ·  {conf}%  ·  {affected}  ·  {created}',
                expanded=False,
            ):
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.markdown(
                        f'<div class="info-card {"red" if bias else "green"}">'
                        f'<div class="ic-label">Verdict</div>'
                        f'<div class="ic-value mono">{"⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"}</div></div>'
                        f'<div class="info-card blue" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Original Outcome</div>'
                        f'<div class="ic-value mono">{(r.get("original_outcome") or "N/A").upper()}</div></div>',
                        unsafe_allow_html=True,
                    )
                with ec2:
                    st.markdown(
                        f'<div class="info-card amber">'
                        f'<div class="ic-label">Bias Types</div>'
                        f'<div class="ic-value">{chips_html(b_types) if b_types else "None"}</div></div>'
                        f'<div class="info-card green" style="margin-top:0.5rem;">'
                        f'<div class="ic-label">Fair Outcome</div>'
                        f'<div class="ic-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                        unsafe_allow_html=True,
                    )
                if r.get("explanation"):
                    st.markdown(
                        f'<div class="info-card amber" style="margin-top:0.5rem;">'
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


# ═══════════════════════════════════════════════
# TAB 4 — COMPARE
# ═══════════════════════════════════════════════

with tab_compare:
    st.markdown(
        '<div style="font-family:DM Sans,sans-serif; font-size:0.93rem; '
        'color:#8892aa; margin-bottom:1.2rem;">'
        'Analyse two decisions side-by-side and compare bias verdicts, '
        'confidence, and fair outcomes.</div>',
        unsafe_allow_html=True,
    )

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown('<div class="compare-header">Decision A</div>', unsafe_allow_html=True)
        cmp_text1 = st.text_area("Text A", height=150, label_visibility="collapsed",
                                  placeholder="Paste first decision here...", key="cmp1")
        cmp_type1 = st.selectbox("Type A", ["job", "loan", "medical", "university", "other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div class="compare-header">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=150, label_visibility="collapsed",
                                  placeholder="Paste second decision here...", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job", "loan", "medical", "university", "other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type2")

    cmp_btn = st.button("⚡ Compare Both Decisions", key="compare_btn")

    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Paste text for both Decision A and B.")
        elif not check_groq_key():
            st.error("❌ No Groq API key.")
        else:
            with st.spinner("Analysing both decisions..."):
                r1, e1 = run_analysis(cmp_text1, cmp_type1)
                r2, e2 = run_analysis(cmp_text2, cmp_type2)

            if e1: st.error(f"Decision A: {e1}")
            if e2: st.error(f"Decision B: {e2}")

            if r1 and r2:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                v1c, v2c = st.columns(2)

                for col, r, lbl in [(v1c, r1, "A"), (v2c, r2, "B")]:
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
                        st.plotly_chart(gauge_chart(conf, bias),
                                        use_container_width=True, config={"displayModeBar": False})
                        st.markdown(
                            chips_html(r.get("bias_types", [])) + " " + severity_badge(conf, bias),
                            unsafe_allow_html=True,
                        )
                        affected = r.get("affected_characteristic") or "—"
                        st.markdown(
                            f'<div style="font-family:DM Mono,monospace; font-size:0.8rem; '
                            f'color:#ffb84d; margin-top:0.5rem;">Affected: {affected}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="info-card green" style="margin-top:0.8rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{r.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">Comparison Summary</div>',
                            unsafe_allow_html=True)
                b1, b2   = r1.get("bias_found"), r2.get("bias_found")
                c1v, c2v = r1.get("confidence_score", 0), r2.get("confidence_score", 0)
                if b1 and b2:
                    winner  = "A" if c1v >= c2v else "B"
                    summary = (f"Both decisions show bias. Decision {winner} has higher "
                               f"confidence ({int(max(c1v, c2v) * 100)}%).")
                elif b1:
                    summary = "Decision A shows bias; Decision B appears fair."
                elif b2:
                    summary = "Decision B shows bias; Decision A appears fair."
                else:
                    summary = "Neither decision shows clear discriminatory patterns."
                st.markdown(
                    f'<div class="info-card blue"><div class="ic-value">{summary}</div></div>',
                    unsafe_allow_html=True,
                )

                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Comparison Report (.txt)",
                        data=build_compare_txt(r1, r2, cmp_text1, cmp_text2),
                        file_name=f"verdict_compare_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                    )


# ═══════════════════════════════════════════════
# TAB 5 — BATCH ANALYSIS  (New in V3)
# ═══════════════════════════════════════════════

with tab_batch:
    st.markdown(
        '<div style="font-family:DM Sans,sans-serif; font-size:0.93rem; '
        'color:#8892aa; margin-bottom:1.2rem;">'
        'Analyse multiple decisions at once. Separate each decision with '
        '<code style="background:rgba(255,255,255,0.05); padding:1px 6px; '
        'border-radius:4px; font-family:DM Mono,monospace;">---</code> '
        'on its own line.</div>',
        unsafe_allow_html=True,
    )

    batch_text = st.text_area(
        "Batch decisions", height=280, label_visibility="collapsed",
        key="batch_input",
        placeholder=(
            "Paste your first decision here...\n---\n"
            "Paste your second decision here...\n---\n"
            "Paste your third decision here..."
        ),
    )
    bc1, bc2 = st.columns([1, 1])
    with bc1:
        batch_type = st.selectbox(
            "Batch type (applies to all)",
            ["job", "loan", "medical", "university", "other"],
            format_func=lambda x: TYPE_LABELS[x],
            label_visibility="collapsed",
            key="batch_type",
        )
    with bc2:
        batch_btn = st.button("📦 Run Batch Analysis", key="batch_run")

    if batch_btn:
        raw_blocks = [b.strip() for b in batch_text.split("---") if b.strip()]
        if not raw_blocks:
            st.warning("⚠️ No decisions found. Separate them with --- on its own line.")
        elif not check_groq_key():
            st.error("❌ No Groq API key.")
        elif len(raw_blocks) > 10:
            st.warning("⚠️ Batch limit is 10 decisions at once.")
        else:
            progress = st.progress(0)
            results  = []
            for i, block in enumerate(raw_blocks):
                with st.spinner(f"Analysing decision {i + 1} of {len(raw_blocks)}..."):
                    rep, err = run_analysis(block, batch_type)
                    results.append({"text": block, "report": rep, "error": err})
                progress.progress((i + 1) / len(raw_blocks))
            progress.empty()

            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown(f'<div class="sec-label">Batch Results — {len(results)} decisions</div>',
                        unsafe_allow_html=True)

            # Summary row
            bias_count  = sum(1 for r in results if r["report"] and r["report"].get("bias_found"))
            clean_count = sum(1 for r in results if r["report"] and not r["report"].get("bias_found"))
            err_count   = sum(1 for r in results if r["error"])

            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Bias Detected", bias_count)
            sm2.metric("No Bias Found", clean_count)
            sm3.metric("Errors",        err_count)

            st.markdown("<br>", unsafe_allow_html=True)

            # Results table
            table_rows = []
            for i, res in enumerate(results, 1):
                rep   = res["report"]
                error = res["error"]
                if error:
                    table_rows.append({
                        "#":           i,
                        "Verdict":     "ERROR",
                        "Confidence":  "—",
                        "Bias Types":  error[:60],
                        "Affected":    "—",
                        "Fair Outcome": "—",
                    })
                elif rep:
                    table_rows.append({
                        "#":           i,
                        "Verdict":     "⚠ BIAS" if rep.get("bias_found") else "✓ CLEAN",
                        "Confidence":  f"{int(rep.get('confidence_score', 0) * 100)}%",
                        "Bias Types":  ", ".join(rep.get("bias_types", [])) or "None",
                        "Affected":    rep.get("affected_characteristic") or "—",
                        "Fair Outcome": rep.get("fair_outcome") or "—",
                    })

            if table_rows:
                df = pd.DataFrame(table_rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

            # Download CSV
            all_batch_reports = [r["report"] for r in results if r["report"]]
            if all_batch_reports:
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Batch Results (.csv)",
                        data=reports_to_csv(all_batch_reports),
                        file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        key="batch_csv",
                    )

            # Detail expanders
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Detailed Results</div>', unsafe_allow_html=True)
            for i, res in enumerate(results, 1):
                rep   = res["report"]
                error = res["error"]
                label = f"Decision {i}"
                if error:
                    label += " — ERROR"
                elif rep:
                    bias = rep.get("bias_found", False)
                    conf = int(rep.get("confidence_score", 0) * 100)
                    label += f" — {'⚠ BIAS' if bias else '✓ CLEAN'} ({conf}%)"

                with st.expander(label, expanded=False):
                    st.markdown(
                        f'<div class="info-card blue"><div class="ic-label">Decision Text</div>'
                        f'<div class="ic-value" style="font-size:0.85rem;">{res["text"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if error:
                        st.error(error)
                    elif rep:
                        bias  = rep.get("bias_found", False)
                        btyps = rep.get("bias_types", [])
                        st.markdown(
                            f'<div class="info-card {"red" if bias else "green"}" '
                            f'style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Verdict</div>'
                            f'<div class="ic-value mono">{"⚠ BIAS DETECTED" if bias else "✓ NO BIAS FOUND"}</div></div>'
                            f'<div class="info-card amber" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Bias Types</div>'
                            f'<div class="ic-value">{chips_html(btyps) if btyps else "None"}</div></div>'
                            f'<div class="info-card green" style="margin-top:0.5rem;">'
                            f'<div class="ic-label">Fair Outcome</div>'
                            f'<div class="ic-value">{rep.get("fair_outcome") or "N/A"}</div></div>',
                            unsafe_allow_html=True,
                        )
                        if rep.get("explanation"):
                            st.markdown(
                                f'<div class="info-card amber" style="margin-top:0.5rem;">'
                                f'<div class="ic-label">Explanation</div>'
                                f'<div class="ic-value" style="font-size:0.88rem;">'
                                f'{rep["explanation"]}</div></div>',
                                unsafe_allow_html=True,
                            )


# ═══════════════════════════════════════════════
# TAB 6 — ABOUT
# ═══════════════════════════════════════════════

with tab_about:
    ab1, ab2 = st.columns([1.6, 1])

    with ab1:
        st.markdown(
            '<div style="font-family:Syne,sans-serif; font-size:1.5rem; font-weight:800; '
            'color:#eef0f8; margin-bottom:0.5rem;">What is Verdict Watch?</div>'
            '<div style="font-family:DM Sans,sans-serif; font-size:0.93rem; '
            'color:#8892aa; line-height:1.8; margin-bottom:1.5rem;">'
            'Verdict Watch analyses automated decisions — job rejections, loan denials, '
            'medical triage, university admissions — for hidden bias against protected '
            'characteristics. A 3-step AI pipeline powered by Groq and Llama 3.3 70B '
            'extracts criteria, detects discriminatory patterns, and generates what the '
            'fair outcome should have been.'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sec-label">Bias Types Detected</div>',
                    unsafe_allow_html=True)
        bias_info = [
            ("Gender Bias",        "Decisions influenced by gender, name, or parental status"),
            ("Age Discrimination",  "Unfair weighting of age group or seniority proxies"),
            ("Racial / Ethnic Bias","Name-based or origin-based ethnic profiling"),
            ("Geographic Redlining","Residential area or zip code used as a proxy"),
            ("Socioeconomic Bias",  "Employment sector or credit history weighting"),
            ("Language Discrimination", "Primary language used against applicants"),
            ("Insurance / Class Bias",  "Insurance tier used to rank medical priority"),
        ]
        for name, desc in bias_info:
            st.markdown(
                f'<div class="info-card blue" style="margin-bottom:0.5rem;">'
                f'<div class="ic-label">{name}</div>'
                f'<div class="ic-value" style="font-size:0.87rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="sec-label">V3 Changelog</div>',
                    unsafe_allow_html=True)
        v3_feats = [
            ("🔌", "Zero-Server Architecture", "No uvicorn needed — runs standalone"),
            ("🔑", "Inline API Key Input",      "Paste Groq key in sidebar, no .env required"),
            ("✉️", "Appeals Letter Generator",  "AI-drafted formal appeal letter"),
            ("📦", "Batch Analysis",            "Analyse up to 10 decisions at once"),
            ("🕸",  "Bias Radar Chart",          "Visual breakdown of 7 bias dimensions"),
            ("📥", "CSV Export",                "Export history to CSV from History tab"),
            ("🏷️", "Severity Badges",           "High / Medium / Low risk classification"),
            ("🟣", "V3 Design Refresh",         "Purple V3 badge + refined palette"),
        ]
        for icon, name, desc in v3_feats:
            st.markdown(
                f'<div class="info-card purple" style="margin-bottom:0.4rem;">'
                f'<div class="ic-label">{icon} {name}</div>'
                f'<div class="ic-value" style="font-size:0.87rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Tech Stack</div>', unsafe_allow_html=True)
        for name, desc in [
            ("⚡ Groq",          "LLM inference"),
            ("🦙 Llama 3.3 70B", "Language model"),
            ("🎈 Streamlit",     "Full-stack UI (standalone)"),
            ("🗄️ SQLite",        "Persistent local database"),
            ("📊 Plotly",        "Interactive charts"),
        ]:
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; '
                f'font-family:DM Mono,monospace; font-size:0.75rem; '
                f'padding:5px 0; border-bottom:1px solid rgba(255,255,255,0.05);">'
                f'<span style="color:#eef0f8;">{name}</span>'
                f'<span style="color:#4a5268;">{desc}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="info-card amber">'
            '<div class="ic-label">⚠ Disclaimer</div>'
            '<div class="ic-value" style="font-size:0.86rem;">'
            'Not legal advice. Built for educational and awareness purposes only. '
            'Consult a qualified legal professional for formal discrimination claims.'
            '</div></div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="footer-bar">'
    'Verdict Watch V3  ·  Powered by Groq / Llama 3.3 70B  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)