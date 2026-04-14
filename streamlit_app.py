"""
streamlit_app.py — Verdict Watch
Clean rewrite: single nav, full-width, professional grade.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import services
import pandas as pd
import re, os
try:
    import plotly.graph_objects as _go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False
from datetime import datetime
from collections import Counter

try:
    import fitz as pymupdf
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

services.init_db()

st.set_page_config(
    page_title="Verdict Watch — AI Bias Detection",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Force Streamlit theme primary color to our accent blue
# This prevents the default coral/red primary button color
st.markdown("""
<style>
:root {
  --primary-color: #4f8ef7;
  --primary-color-rgb: 79, 142, 247;
}
/* Override Streamlit's own primary color CSS variable */
.stApp { --primary: #4f8ef7 !important; }
button[kind="primary"], [data-testid="baseButton-primary"] {
  background-color: #4f8ef7 !important;
  border-color: #4f8ef7 !important;
  color: white !important;
}
button[kind="primary"]:hover, [data-testid="baseButton-primary"]:hover {
  background-color: #3a7de0 !important;
  border-color: #3a7de0 !important;
  opacity: 1 !important;
}

/* ── Radio disabled option muting ── */
.model-sel-wrap [data-testid="stRadio"] label:has(input:disabled) {
  opacity: .35 !important;
  cursor: not-allowed !important;
  text-decoration: line-through !important;
}
/* ── Code block (appeal letter) ── */
.stCode {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}
.stCode code {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  color: var(--muted) !important;
  line-height: 1.9 !important;
}
/* ── Dataframe ── */
[data-testid="stDataFrame"] thead th {
  background: var(--bg3) !important;
  color: var(--muted) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: .04em !important;
}

/* Try it now run button — slightly calmer than full accent */
.run-btn-wrap .stButton > button {
  background: var(--bg4) !important;
  border: 1px solid var(--accent) !important;
  color: var(--accent) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  height: 52px !important;
  letter-spacing: .02em !important;
}
.run-btn-wrap .stButton > button:hover {
  background: var(--accent) !important;
  color: #fff !important;
  opacity: 1 !important;
}
/* Step connector line color for done steps */
.step.step-done-group::after {
  background: var(--success) !important;
}
/* Wider provlbl */
.vw-provlbl { font-size: 11px; color: var(--muted); margin-left: 4px; }

/* ── Summary / Full toggle ── */
.stRadio[data-testid*="view_toggle"] > div {
  gap: 2px !important;
}
.stRadio[data-testid*="view_toggle"] label {
  padding: 4px 12px !important;
  font-size: 12px !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border2) !important;
  background: var(--bg3) !important;
  color: var(--muted) !important;
}
.stRadio[data-testid*="view_toggle"] label:has(input:checked) {
  background: var(--bg4) !important;
  color: var(--text) !important;
  border-color: var(--border2) !important;
  font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════

TYPE_LABELS = {
    "job":        "Job application",
    "loan":       "Loan / mortgage",
    "medical":    "Medical triage",
    "university": "University admission",
    "other":      "Other / general",
}

BIAS_KW = {
    "Gender":        r"\b(gender|female|male|woman|man|maternal|paternity|family obligation|mrs|mr)\b",
    "Age":           r"\b(age group|senior|junior|young|old|elderly|youth|65\+|under 30)\b",
    "Racial":        r"\b(race|ethnic|nationality|foreign|immigrant|origin|surname|cultural fit)\b",
    "Geographic":    r"\b(zip code|postcode|residential area|neighbourhood|neighborhood|district)\b",
    "Socioeconomic": r"\b(income|wealth|credit history|employment sector|manual labour|unskilled)\b",
    "Language":      r"\b(primary language|accent|non-english|native speaker|bilingual)\b",
    "Insurance":     r"\b(insurance|uninsured|medicaid|medicare|insurance classification)\b",
    "Disability":    r"\b(disability|disabled|accessibility|accommodation|impairment|medical leave|chronic)\b",
    "Name-based":    r"\b(surname|last name|name origin|name score|cultural fit)\b",
}

URGENCY_COLORS = {
    "immediate": ("rgba(224,84,84,.12)", "var(--danger)"),
    "high":      ("rgba(212,148,58,.12)", "var(--warn)"),
    "medium":    ("rgba(79,142,247,.12)", "var(--accent)"),
    "low":       ("rgba(76,175,130,.12)", "var(--success)"),
}

VIEWS = ["try", "analyse", "batch", "reports", "settings"]
VIEW_LABELS = ["Try it now", "Analyse", "Batch", "Reports", "Settings"]

TEST_SAMPLES = [
    {
        "label": "Job rejection — cited 'family obligations'",
        "dtype": "job",
        "text": (
            "Thank you for applying to the Marketing Manager role. We felt the demands "
            "of the role — including frequent travel and long hours — may not align with "
            "your current family obligations and caring responsibilities. We have decided "
            "to move forward with another candidate whose personal circumstances are "
            "better suited to the role requirements."
        ),
    },
    {
        "label": "Loan denial — flagged by postcode",
        "dtype": "loan",
        "text": (
            "After reviewing your mortgage application, we are unable to approve the "
            "requested amount. Our risk assessment model has flagged your residential "
            "postcode as a high-risk zone. Additionally, your employment in the manual "
            "labour sector places you in a category outside our current lending criteria. "
            "You may reapply after 12 months."
        ),
    },
    {
        "label": "Medical triage — deprioritised by age",
        "dtype": "medical",
        "text": (
            "Patient triaged to low-priority queue. Factors considered: age group (67), "
            "primary language non-English which may affect treatment compliance, insurance "
            "classification Medicaid. High-priority slots are reserved for Priority 1-2 "
            "patients. Given patient age and overall condition, aggressive intervention "
            "is not recommended at this time."
        ),
    },
    {
        "label": "University rejection — 'cultural fit score'",
        "dtype": "university",
        "text": (
            "After careful holistic review, the admissions committee has decided not to "
            "offer you a place. Factors considered included name-based cultural fit score, "
            "secondary school background, and geographic region of residence. We encourage "
            "applicants whose profiles better align with our community values to apply "
            "in future cycles."
        ),
    },
]

# ── Demo mode — shown when no API key configured ──
DEMO_REPORT = {
    "id": "demo00000001",
    "analysis_id": "demo-analysis",
    "bias_found": True,
    "bias_types": ["Gender", "Socioeconomic"],
    "affected_characteristic": "gender",
    "original_outcome": "REJECTED",
    "fair_outcome": "Application should have been assessed on merit alone",
    "explanation": "The decision explicitly cited 'family obligations' as a reason for rejection. This is a proxy for gender discrimination — it assumes caring responsibilities based on the applicant's perceived gender. Under the Equality Act 2010, this constitutes direct discrimination on the grounds of sex.",
    "confidence_score": 0.91,
    "recommendations": [
        "Request written reasons for the rejection within 14 days.",
        "File a claim with the Employment Tribunal within 3 months of the discriminatory act.",
        "Contact ACAS for early conciliation before issuing proceedings — this is a legal requirement.",
    ],
    "created_at": "2026-04-13T10:00:00+00:00",
    "bias_phrases": ["family obligations", "caring responsibilities", "personal circumstances"],
    "legal_frameworks": ["Equality Act 2010 — s.13 Direct Discrimination", "Employment Rights Act 1996"],
    "international_laws": ["CEDAW — UN Convention on Elimination of Discrimination Against Women"],
    "fair_reasoning": "The decision criteria should be limited to skills, experience, and job requirements.",
    "severity": "high",
    "bias_evidence": "The phrase 'family obligations' is a well-documented proxy for gender bias in hiring decisions.",
    "timing_ms": {"total": 24500},
    "retry_counts": {},
    "mode": "full",
    "ai_provider": "demo",
    "ai_model": "demo-mode",
    "decision_type": "job",
    "fairness_scores": {
        "overall_fairness_score": 22,
        "fairness_verdict": "unfair",
        "demographic_parity_scores": {"gender": 18, "socioeconomic": 35},
    },
    "explainability_trace": {},
    "characteristic_weights": {"gender": 85, "socioeconomic": 45},
    "risk_score": 78,
    "urgency_tier": "immediate",
    "escalation_flag": True,
    "appeal_letter": """[DATE]
[YOUR NAME]
[YOUR ADDRESS]

[RECIPIENT NAME]
[ORGANISATION]
[ORGANISATION ADDRESS]

Dear [RECIPIENT NAME],

Re: Formal Appeal Against Discriminatory Hiring Decision

I am writing to formally appeal the decision to reject my application for the Marketing Manager role, as communicated on [DATE OF REJECTION].

Having reviewed the reasons provided, I believe the decision constitutes direct sex discrimination under the Equality Act 2010. Specifically, the rejection cited "family obligations and caring responsibilities" as factors. These are not legitimate job requirements and represent assumptions about my personal circumstances based on my gender.

The following phrases in your decision letter are discriminatory:
  - "family obligations and caring responsibilities"
  - "personal circumstances are better suited"

These references violate Section 13 of the Equality Act 2010, which prohibits direct discrimination on grounds of sex, and Article 11 of CEDAW.

I request a formal review of this decision and reassessment of my application on merit alone. I expect a response within 14 days. Should I not receive a satisfactory response, I will initiate ACAS early conciliation as a precursor to an Employment Tribunal claim.

Sincerely,
[YOUR NAME]""",
    "disability_bias": False,
    "intersectional_bias": {"detected": False},
    "severity_per_phrase": [
        {"phrase": "family obligations", "severity": "high", "characteristic_triggered": "Gender"},
        {"phrase": "caring responsibilities", "severity": "high", "characteristic_triggered": "Gender"},
        {"phrase": "personal circumstances", "severity": "medium", "characteristic_triggered": "Gender"},
    ],
    "legal_timeline": {
        "jurisdiction": "United Kingdom",
        "deadlines": [
            {"body": "ACAS", "action": "Initiate early conciliation", "window_days": 90, "window_description": "3 months from discriminatory act", "priority": "critical"},
            {"body": "Employment Tribunal", "action": "Submit ET1 claim form", "window_days": 91, "window_description": "After ACAS certificate issued", "priority": "high"},
        ],
        "immediate_actions": [
            "Save all correspondence with the employer.",
            "Document the exact date you received the rejection.",
            "Contact ACAS on 0300 123 1100 to start early conciliation.",
        ],
        "evidence_to_preserve": ["Rejection email", "Job description", "Your application", "Any prior communications"],
        "pro_bono_resources": ["ACAS", "Citizens Advice", "Equality Advisory Support Service"],
        "estimated_timeline_months": 9,
    },
    "precedents": {
        "precedents": [
            {
                "case_name": "Horsey v Dyfed County Council [1982] IRLR 395",
                "year": 1982, "jurisdiction": "United Kingdom",
                "relevance_score": 88,
                "why_relevant": "Established that assumptions about family responsibilities constitute sex discrimination under UK law.",
                "outcome": "Tribunal found in favour of the claimant.",
                "key_principle": "Stereotypical assumptions about caring roles are unlawful direct discrimination.",
            },
        ],
        "strongest_precedent": "Horsey v Dyfed County Council [1982] IRLR 395",
        "legal_strategy_hint": "Emphasise that the rejection letter explicitly referenced family circumstances, making this a clear case of direct discrimination requiring no inference.",
        "estimated_win_probability": "medium",
    },
}


_SAMPLE_CSV = """\
text
"Your loan application has been declined. Primary reasons: insufficient credit history, residential area risk score, employment sector classification. You may reapply after 6 months."
"Thank you for applying to the Marketing Manager role. We felt the demands of the role — including frequent travel — may not align with your current family obligations. We have moved forward with another candidate."
"Patient triaged to low-priority queue. Factors: age group (67), primary language (non-English), insurance classification (Medicaid). High-priority slots reserved for Priority 1-2."
"After holistic review the committee decided not to offer you a place. Factors include name-based cultural fit score, undergraduate institution tier, and geographic region of residence."
"Your application for the customer service role has been declined. Our assessment indicates that your accessibility requirements and communication style would make it difficult to meet the performance benchmarks required for this fast-paced environment."
"After reviewing your mortgage application, we note that your medical leave history and part-time employment status indicate insufficient income stability for a loan of this size."
"We regret to inform you that your application for the Senior Engineer role has not been successful. Candidates who had returned to the workforce after an extended absence were not the right fit for our fast-paced environment."
"After reviewing your application, we are unable to approve the requested amount. Our assessment of your neighbourhood risk profile indicates an elevated default risk outside our current lending criteria."
"Patient triaged to low-priority queue. Given patient age (67) and overall condition, aggressive intervention is not recommended. Resources better allocated to younger patients."
"Thank you for applying. After careful review, your application has not been successful. Your surname and secondary school background suggest a cultural fit that may not align with our academic community."
"We were impressed with your background but have concerns that your disability accommodation requirements may impact your ability to meet our performance standards."
"Your application for the loan has been declined due to your employment in a manual labour sector and your residential postcode falling within a high-risk zone."
"""

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════

_DEFAULTS = {
    "view":           "try",
    "last_report":    None,
    "last_text":      "",
    "last_dtype":     "job",
    "scan_mode":      "full",
    "decision_input": "",
    "batch_results":  None,
    "test_idx":       0,
    "test_report":    None,
    "_esc_filter":    False,
    "show_fb_text":   False,
    "progress_step":  -1,
    "progress_msg":   "",
    "show_full":      False,
    "model_choice":   "auto",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
# CSS — single block, named classes, no inline styles
# ══════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap');

:root {
  --bg:#0e0e0f; --bg2:#161618; --bg3:#1e1e21; --bg4:#26262b;
  --border:rgba(255,255,255,.08); --border2:rgba(255,255,255,.15);
  --text:#e2e2e5; --muted:#7a7a84; --muted2:#55555f;
  --accent:#4f8ef7; --accent-d:rgba(79,142,247,.12);
  --danger:#e05454; --danger-d:rgba(224,84,84,.10);
  --success:#4caf82; --success-d:rgba(76,175,130,.10);
  --warn:#d4943a; --warn-d:rgba(212,148,58,.10);
  --violet:#9b7ff4; --violet-d:rgba(155,127,244,.10);
  --mono:'IBM Plex Mono',monospace;
  --sans:'IBM Plex Sans',-apple-system,sans-serif;
  --radius:6px; --radius-lg:8px;
}

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: var(--sans) !important;
  font-size: 14px !important;
  color: var(--text) !important;
  background: var(--bg) !important;
}

/* ── Hide Streamlit chrome ── */
footer, [data-testid="stStatusWidget"], [data-testid="stDecoration"],
#MainMenu, [data-testid="stToolbar"], [data-testid="stHeader"],
[data-testid="stSidebar"], section[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Layout ── */
.block-container { padding: 0 !important; max-width: 100% !important; }
.main .block-container { padding: 0 !important; }

/* ── Nav bar tab buttons ── */
/* Wrap nav buttons with .vw-nav-row class via CSS on the next stHorizontalBlock */
.vw-nav-bar { background: var(--bg2); border-bottom: 1px solid var(--border); padding: 0 20px; margin-bottom: 0; }
.vw-nav-bar .stButton > button {
  border-radius: 0 !important;
  border: none !important;
  border-bottom: 3px solid transparent !important;
  background: transparent !important;
  color: var(--muted) !important;
  font-size: 12px !important;
  font-weight: 400 !important;
  padding: 0 4px !important;
  height: 44px !important;
  width: 100% !important;
  box-shadow: none !important;
  transition: color .15s, border-color .15s !important;
}
.vw-nav-bar .stButton > button:hover {
  color: var(--text) !important;
  background: transparent !important;
  opacity: 1 !important;
}
.vw-nav-bar .stButton > button[kind="primary"] {
  color: var(--accent) !important;
  font-weight: 500 !important;
  border-bottom-color: var(--accent) !important;
  background: transparent !important;
}

/* Sample picker — active has border tint, not solid fill */
.sample-picker-wrap .stButton > button {
  background: var(--bg2) !important;
  color: var(--muted) !important;
  border: 1px solid var(--border2) !important;
  border-radius: var(--radius-lg) !important;
  font-size: 13px !important;
  font-weight: 400 !important;
  padding: 12px 10px !important;
  height: auto !important;
  min-height: 48px !important;
  white-space: normal !important;
  line-height: 1.4 !important;
  box-shadow: none !important;
  transition: border-color .15s, color .15s !important;
}
.sample-picker-wrap .stButton > button:hover {
  border-color: rgba(79,142,247,.4) !important;
  color: var(--text) !important;
  background: var(--bg3) !important;
  opacity: 1 !important;
}
.sample-picker-wrap .stButton > button[kind="primary"] {
  background: var(--accent-d) !important;
  color: var(--accent) !important;
  border-color: rgba(79,142,247,.5) !important;
  font-weight: 500 !important;
}

/* ── All other buttons ── */
.stButton > button {
  font-family: var(--sans) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--radius) !important;
  padding: 8px 18px !important;
  box-shadow: none !important;
  transition: opacity .15s !important;
}
.stButton > button:hover { opacity: .85 !important; background: var(--accent) !important; }
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #fff !important;
}
.stButton > button[kind="secondary"] {
  background: var(--bg3) !important;
  color: var(--muted) !important;
  border: 1px solid var(--border2) !important;
  font-size: 12px !important;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--bg4) !important;
  color: var(--text) !important;
  opacity: 1 !important;
}
.stDownloadButton > button {
  background: var(--bg3) !important;
  color: var(--muted) !important;
  border: 1px solid var(--border2) !important;
  border-radius: var(--radius) !important;
  font-size: 12px !important;
}

/* ── Form elements ── */
.stTextArea textarea, .stTextInput input {
  font-family: var(--sans) !important;
  font-size: 13px !important;
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
  border-color: var(--accent) !important;
  box-shadow: none !important;
}
.stSelectbox > div > div {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
}
.stRadio > div { gap: 4px !important; }
.stRadio > div > label {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: var(--radius) !important;
  padding: 5px 12px !important;
  font-size: 12px !important;
  color: var(--muted) !important;
}
.stRadio > div > label:has(input:checked) {
  background: var(--accent-d) !important;
  color: var(--accent) !important;
  border-color: rgba(79,142,247,.3) !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 14px 16px !important;
}
[data-testid="metric-container"] label {
  font-size: 10px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: .06em !important;
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

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--border) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  color: var(--text) !important;
  font-size: 12px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--bg2) !important;
  border: 1px dashed var(--border2) !important;
  border-radius: var(--radius-lg) !important;
}

/* ══ Component classes ══ */

/* Brand bar */
.vw-brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 99;
}
.vw-nav-bar {
  position: sticky;
  top: 41px;
  z-index: 98;
}
.vw-brand-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}
.vw-brand-name span {
  font-size: 10px;
  color: var(--muted2);
  font-weight: 400;
  letter-spacing: .04em;
}
.vw-providers {
  display: flex;
  align-items: center;
  gap: 6px;
}
.vw-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.vw-dot-ok { background: var(--success); }
.vw-dot-off { background: var(--muted2); }
.vw-provlbl { font-size: 11px; color: var(--muted2); margin-left: 2px; }

/* Content padding */
.vw-page { padding: 20px; padding-top: 16px; }

/* Cards */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  margin-bottom: 10px;
}
.card-violet {
  background: var(--violet-d);
  border: 1px solid rgba(155,127,244,.25);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  margin-bottom: 10px;
}

/* Section labels */
.clbl {
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0;
  text-transform: none;
  margin-bottom: 8px;
  font-weight: 500;
  border-left: 2px solid var(--border2);
  padding-left: 8px;
}

/* Chips */
.chip { display: inline-block; border-radius: 4px; padding: 2px 8px; font-size: 11px; margin: 2px; }
.chip-r { background: rgba(224,84,84,.18); color: var(--danger); border: 1px solid rgba(224,84,84,.4); }
.chip-g { background: var(--success-d); color: var(--success); border: 1px solid rgba(76,175,130,.25); }
.chip-a { background: var(--warn-d); color: var(--warn); border: 1px solid rgba(212,148,58,.25); }
.chip-b { background: var(--accent-d); color: var(--accent); border: 1px solid rgba(79,142,247,.25); }
.chip-n { background: var(--bg3); color: var(--muted); border: 1px solid var(--border2); }
.chip-v { background: var(--violet-d); color: var(--violet); border: 1px solid rgba(155,127,244,.25); }

/* Verdict card */
.verdict {
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  border: 1px solid;
  margin-bottom: 10px;
}
.verdict-bias { background: var(--danger-d); border-color: rgba(224,84,84,.3); }
.verdict-clean { background: var(--success-d); border-color: rgba(76,175,130,.3); }
.verdict-row { display: flex; align-items: center; justify-content: space-between; }
.verdict-title { font-size: 18px; font-weight: 500; }
.verdict-sub { font-size: 12px; color: var(--muted); margin-top: 4px; }
.verdict-chips { margin-top: 10px; }
.verdict-conf { font-size: 34px; font-weight: 500; font-family: var(--mono); }
.verdict-conf-lbl { font-size: 12px; color: var(--muted); text-align: right; margin-top: 2px; }

/* Banners */
.banner-esc {
  background: rgba(224,84,84,.12);
  border: 1px solid var(--danger);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--danger);
}
.banner-dis {
  background: rgba(79,142,247,.08);
  border: 1px solid rgba(79,142,247,.3);
  border-radius: var(--radius);
  padding: 10px 14px;
  font-size: 12px;
  color: var(--accent);
  margin-bottom: 8px;
}
.banner-int {
  background: rgba(212,148,58,.08);
  border: 1px solid rgba(212,148,58,.3);
  border-radius: var(--radius);
  padding: 12px 16px;
  font-size: 13px;
  color: var(--warn);
  margin-bottom: 8px;
  line-height: 1.6;
}
.banner-nokey {
  background: var(--warn-d);
  border: 1px solid var(--warn);
  border-radius: var(--radius);
  padding: 10px 14px;
  font-size: 12px;
  color: var(--warn);
  margin-bottom: 12px;
}

/* Risk panel */
.risk-panel {
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  border: 1px solid;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.risk-num { font-size: 36px; font-weight: 500; font-family: var(--mono); }
.risk-sub { font-size: 10px; color: var(--muted2); }
.urg-badge {
  display: inline-block;
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid;
}

/* Outcomes */
.outcome-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
.out-bad {
  border-left: 2px solid var(--danger);
  background: var(--danger-d);
  padding: 12px 16px;
  border-radius: 0 var(--radius) var(--radius) 0;
}
.out-good {
  border-left: 2px solid var(--success);
  background: var(--success-d);
  padding: 12px 16px;
  border-radius: 0 var(--radius) var(--radius) 0;
}
.out-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; }
.out-val { font-size: 14px; font-weight: 500; font-family: var(--mono); }

/* Bars */
.bar-track { height: 4px; background: var(--bg4); border-radius: 2px; overflow: hidden; margin-top: 5px; }
.bar-fill { height: 100%; border-radius: 2px; }

/* Phrase block */
.phrase {
  border-left: 2px solid var(--danger);
  background: var(--danger-d);
  padding: 7px 12px;
  border-radius: 0 var(--radius) var(--radius) 0;
  margin-bottom: 5px;
  font-size: 12px;
  font-family: var(--mono);
  line-height: 1.6;
}

/* Severity table */
.spp { width: 100%; border-collapse: collapse; font-size: 11px; }
.spp th, .spp td { padding: 5px 8px; border-bottom: 1px solid var(--border); text-align: left; }
.spp th { color: var(--muted2); font-size: 10px; text-transform: uppercase; letter-spacing: .06em; }
.sev-h { color: var(--danger); font-weight: 500; }
.sev-m { color: var(--warn); font-weight: 500; }
.sev-l { color: var(--success); font-weight: 500; }

/* Laws */
.law { display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--muted); }
.law:last-child { border-bottom: none; }
.law-sym { color: var(--accent); font-weight: 500; flex-shrink: 0; }

/* Recs */
.rec { display: flex; gap: 10px; align-items: flex-start; padding: 5px 0; }
.rec-n {
  width: 20px; height: 20px; border-radius: 4px;
  background: var(--bg3); border: 1px solid var(--border2);
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; color: var(--muted); font-family: var(--mono);
  flex-shrink: 0; margin-top: 2px;
}
.rec-t { font-size: 14px; color: var(--muted); line-height: 1.6; }

/* Appeal */
.appeal-box {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  font-size: 12px;
  line-height: 1.9;
  color: var(--muted);
  white-space: pre-wrap;
  font-family: var(--mono);
}

/* Timeline */
.tl-box {
  background: rgba(155,127,244,.06);
  border: 1px solid rgba(155,127,244,.25);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  margin-bottom: 10px;
}
.tl-row {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 8px 0; border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.tl-row:last-child { border-bottom: none; }
.tl-days { font-family: var(--mono); font-size: 15px; font-weight: 500; min-width: 52px; }
.tl-act { font-size: 13px; color: var(--text); font-weight: 500; }
.tl-body { font-size: 12px; color: var(--muted); margin-top: 2px; }
.tl-prio { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; flex-shrink: 0; margin-left: auto; }
.act-row { display: flex; gap: 8px; align-items: flex-start; padding: 4px 0; font-size: 12px; }
.act-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--violet); margin-top: 5px; flex-shrink: 0; }

/* Precedents */
.prec-card {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 14px;
  margin-bottom: 8px;
}
.prec-name { font-size: 12px; font-weight: 500; color: var(--text); font-family: var(--mono); }
.prec-meta { font-size: 11px; color: var(--muted); }
.prec-bar { height: 3px; background: var(--bg4); border-radius: 2px; margin-top: 6px; }

/* Pipeline step tracker (horizontal) */
.pipeline-row {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 10px 0;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  flex: 1;
  min-width: 48px;
  position: relative;
}
/* Connector line between steps */
.step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 16px;
  left: calc(50% + 16px);
  right: calc(-50% + 16px);
  height: 1px;
  background: var(--border);
}
.step-ico {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600;
  position: relative; z-index: 1;
}
.step-done {
  background: var(--success);
  color: #fff;
  border: none;
}
.step-done::after { background: var(--success) !important; }
.step-idle { background: var(--bg3); color: var(--muted2); border: 1px solid var(--border2); }
.step-v21  { background: var(--violet-d); color: var(--violet); border: 1px solid rgba(155,127,244,.4); }
.step-lbl  { font-size: 10px; color: var(--muted2); text-align: center; line-height: 1.3; white-space: nowrap; }
.step-done + .step-ico { background: var(--success); }

/* Empty state */
.empty { text-align: center; padding: 60px 20px; color: var(--muted2); }
.empty-t { font-size: 16px; color: var(--muted); margin-bottom: 8px; }
.empty-s { font-size: 13px; line-height: 1.7; max-width: 340px; margin: 0 auto; }

/* Try it now sample cards */
.sample-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color .15s;
}
.sample-card-active {
  background: var(--accent-d);
  border: 1px solid rgba(79,142,247,.4);
  border-radius: var(--radius-lg);
  padding: 12px 14px;
}
.sample-lbl { font-size: 13px; font-weight: 500; color: var(--text); margin-bottom: 3px; }
.sample-type { font-size: 11px; color: var(--muted2); }

/* Reports urgency bars */
.urg-bar-row {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 6px; font-size: 12px;
}

/* Settings provider card */
.prov-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  margin-bottom: 8px;
}

/* Divider */
.div { border: none; border-top: 1px solid var(--border); margin: 14px 0; }

/* ── Model selector — st.radio styled as compact segmented control ── */
.model-sel-wrap [data-testid="stRadio"] > div {
  gap: 2px !important;
  flex-wrap: nowrap !important;
}
.model-sel-wrap [data-testid="stRadio"] label {
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  border-radius: var(--radius) !important;
  padding: 4px 14px !important;
  font-size: 12px !important;
  color: var(--muted) !important;
  cursor: pointer !important;
  min-width: 0 !important;
  white-space: nowrap !important;
  transition: all .12s !important;
}
.model-sel-wrap [data-testid="stRadio"] label:hover {
  border-color: var(--accent) !important;
  color: var(--text) !important;
}
.model-sel-wrap [data-testid="stRadio"] label:has(input:checked) {
  background: var(--accent-d) !important;
  border-color: rgba(79,142,247,.45) !important;
  color: var(--accent) !important;
  font-weight: 500 !important;
}
.model-sel-wrap [data-testid="stRadio"] label:has(input:disabled) {
  opacity: .35 !important;
  cursor: not-allowed !important;
}
/* Provider badge shown after results */
.provider-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--muted2);
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-family: var(--mono);
  background: var(--bg3);
}
/* Copy button */
.copy-btn {
  display: inline-block;
  font-size: 10px;
  color: var(--accent);
  border: 1px solid rgba(79,142,247,.3);
  border-radius: 3px;
  padding: 1px 6px;
  cursor: pointer;
  font-family: var(--mono);
  background: var(--accent-d);
  margin-left: 6px;
  vertical-align: middle;
}
/* nav underline — handled by .vw-nav-bar above */
/* Analyse controls model row wrapper */
.model-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.model-row-label {
  font-size: 12px;
  color: var(--muted2);
  white-space: nowrap;
  flex-shrink: 0;
}
/* Result row in reports table — bias rows */
.bias-row { background: rgba(224,84,84,.05) !important; }

/* ── Radio disabled option muting ── */
.model-sel-wrap [data-testid="stRadio"] label:has(input:disabled) {
  opacity: .35 !important;
  cursor: not-allowed !important;
  text-decoration: line-through !important;
}
/* ── Code block (appeal letter) ── */
.stCode {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}
.stCode code {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  color: var(--muted) !important;
  line-height: 1.9 !important;
}
/* ── Dataframe ── */
[data-testid="stDataFrame"] thead th {
  background: var(--bg3) !important;
  color: var(--muted) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: .04em !important;
}

/* Try it now run button — slightly calmer than full accent */
.run-btn-wrap .stButton > button {
  background: var(--bg4) !important;
  border: 1px solid var(--accent) !important;
  color: var(--accent) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  height: 52px !important;
  letter-spacing: .02em !important;
}
.run-btn-wrap .stButton > button:hover {
  background: var(--accent) !important;
  color: #fff !important;
  opacity: 1 !important;
}
/* Step connector line color for done steps */
.step.step-done-group::after {
  background: var(--success) !important;
}
/* Wider provlbl */
.vw-provlbl { font-size: 11px; color: var(--muted); margin-left: 4px; }

/* ── Summary / Full toggle ── */
.stRadio[data-testid*="view_toggle"] > div {
  gap: 2px !important;
}
.stRadio[data-testid*="view_toggle"] label {
  padding: 4px 12px !important;
  font-size: 12px !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border2) !important;
  background: var(--bg3) !important;
  color: var(--muted) !important;
}
.stRadio[data-testid*="view_toggle"] label:has(input:checked) {
  background: var(--bg4) !important;
  color: var(--text) !important;
  border-color: var(--border2) !important;
  font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def gemini_ok():   return bool(os.getenv("GEMINI_API_KEY","").strip() or os.getenv("GOOGLE_API_KEY","").strip())
def groq_ok():     return bool(os.getenv("GROQ_API_KEY","").strip())
def vertex_ok():   return bool(os.getenv("GOOGLE_CLOUD_PROJECT","").strip())
def claude_ok():   return bool(os.getenv("ANTHROPIC_API_KEY","").strip())
def any_api_ok():  return gemini_ok() or groq_ok()
def best_provider(): return "gemini" if gemini_ok() else "groq"

def get_all():
    try: return services.get_all_reports()
    except Exception as e: st.warning(f"Could not load reports: {e}"); return []

def trunc(s, n):
    s = str(s or "")
    return s[:n] + "…" if len(s) > n else s

def score_col(v):
    if v >= 70: return "var(--success)"
    if v >= 40: return "var(--warn)"
    return "var(--danger)"

def prio_col(p):
    return {"critical":"var(--danger)","high":"var(--warn)","medium":"var(--accent)","low":"var(--success)"}.get(p,"var(--muted)")

def normalize_bias(t):
    """Normalize AI-returned bias type strings for consistent display."""
    t = t.strip().lower()
    t = re.sub(r"\s+bias$", "", t)          # strip trailing " bias"
    t = re.sub(r"\s+discrimination$", "", t) # strip trailing " discrimination"
    mapping = {
        "socioeconomic status": "Socioeconomic",
        "socioeconomic":        "Socioeconomic",
        "name-based":           "Name-based",
        "name based":           "Name-based",
        "geographic":           "Geographic",
        "geography":            "Geographic",
        "racial":               "Racial",
        "race":                 "Racial",
        "race/ethnicity":       "Racial",
        "gender":               "Gender",
        "age":                  "Age",
        "language":             "Language",
        "disability":           "Disability",
        "insurance":            "Insurance",
        "indirect":             "Indirect",
    }
    return mapping.get(t, t.title())

def bias_chips(types):
    if not types: return '<span class="chip chip-n">None detected</span>'
    return "".join(f'<span class="chip chip-r">{normalize_bias(t)}</span>' for t in types)

def bar_html(label, val):
    c = score_col(val)
    return (f'<div style="margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">'
            f'<span style="color:var(--muted);">{label}</span>'
            f'<span style="color:{c};font-family:var(--mono);">{val}/100</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{min(val,100)}%;background:{c};"></div></div></div>')

def urg_badge(tier, score):
    tier = (tier or "low").lower()
    c = {"immediate":"var(--danger)","high":"var(--warn)","medium":"var(--accent)","low":"var(--success)"}.get(tier,"var(--muted)")
    lbl = {"immediate":"Immediate","high":"High","medium":"Medium","low":"Low"}.get(tier, tier.title())
    return (f'<span class="urg-badge" style="color:{c};border-color:{c};background:transparent;">'
            f'{lbl} · {score}/100</span>')

def highlight(text, phrases, bias_types):
    out = text
    pats = set(phrases or [])
    for bt in (bias_types or []):
        for key, pat in BIAS_KW.items():
            if key.lower() in bt.lower():
                for m in re.findall(pat, text, flags=re.IGNORECASE):
                    pats.add(m)
    for p in sorted(pats, key=len, reverse=True):
        if p and len(p) > 2:
            out = re.sub(
                re.escape(p),
                lambda m: f'<mark style="background:rgba(224,84,84,.18);color:var(--danger);border-radius:3px;padding:1px 3px;">{m.group()}</mark>',
                out, flags=re.IGNORECASE
            )
    return out

def resolve_provider(choice):
    """Map UI choice to services provider string."""
    if choice == "gemini" and gemini_ok(): return "gemini"
    if choice == "groq"   and groq_ok():   return "groq"
    return "gemini" if gemini_ok() else "groq"   # auto fallback


def render_model_selector(key="model_main"):
    """
    st.radio styled as segmented pills. Single widget = CSS works reliably.
    Returns selected provider string: 'auto', 'gemini', or 'groq'.
    """
    gem = gemini_ok(); grq = groq_ok()
    current = st.session_state.get("model_choice", "auto")

    options = ["auto"]
    fmt = {"auto": "◉  Auto"}
    hints = {
        "auto":   "Auto — Vertex AI → Gemini → Groq → Claude cascade. Picks best available automatically.",
        "gemini": "Gemini — 2.0 Flash for fast steps, 2.5 Pro for reasoning. Most accurate.",
        "groq":   "Groq — llama-3.3-70b. Faster but less precise on legal reasoning and case-law.",
    }

    if gem:
        options.append("gemini")
        fmt["gemini"] = "◉  Gemini"
    else:
        options.append("gemini_off")
        fmt["gemini_off"] = "○  Gemini"

    if grq:
        options.append("groq")
        fmt["groq"] = "◉  Groq"
    else:
        options.append("groq_off")
        fmt["groq_off"] = "○  Groq"

    # Default to auto if current choice is unavailable
    radio_val = current
    if current == "gemini" and not gem: radio_val = "auto"
    if current == "groq"   and not grq: radio_val = "auto"

    chosen = st.radio(
        "model_radio",
        options,
        index=options.index(radio_val) if radio_val in options else 0,
        format_func=lambda x: fmt.get(x, x),
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )

    # Normalize _off variants
    sel = chosen.replace("_off", "") if chosen else "auto"
    if sel != st.session_state.get("model_choice"):
        st.session_state["model_choice"] = sel

    hint = hints.get(sel, hints["auto"])
    st.markdown(f'<div style="font-size:11px;color:var(--muted2);margin-top:2px;line-height:1.5;">{hint}</div>', unsafe_allow_html=True)
    return sel


def run_pipeline(text, dtype, mode="full", provider="auto", progress_fn=None):
    prov = resolve_provider(provider)

    def _cb(step_idx, msg=""):
        if progress_fn:
            try: progress_fn(step_idx, msg)
            except: pass

    try:
        if mode == "quick":
            return services.quick_scan(text, dtype, provider=prov), None
        return services.run_full_pipeline(
            text, dtype, provider=prov,
            progress_callback=_cb
        ), None
    except Exception as e:
        return None, str(e)

def to_csv(reps):
    rows = [{
        "id":           r.get("id","")[:8],
        "date":         (r.get("created_at") or "")[:10],
        "type":         r.get("decision_type",""),
        "bias_found":   r.get("bias_found",False),
        "confidence":   f"{int(r.get('confidence_score',0)*100)}%",
        "severity":     r.get("severity",""),
        "risk_score":   r.get("risk_score",0),
        "urgency":      r.get("urgency_tier",""),
        "escalation":   r.get("escalation_flag",False),
        "disability":   r.get("disability_bias",False),
        "bias_types":   "; ".join(r.get("bias_types",[])),
        "affected":     r.get("affected_characteristic",""),
        "fair_outcome": r.get("fair_outcome",""),
        "laws":         "; ".join(r.get("legal_frameworks",[])),
        "jurisdiction": (r.get("legal_timeline") or {}).get("jurisdiction",""),
        "precedent":    (r.get("precedents") or {}).get("strongest_precedent",""),
    } for r in reps if isinstance(r, dict)]
    return pd.DataFrame(rows).to_csv(index=False)

def generate_pdf_report(report: dict) -> bytes:
    """Generate a formatted PDF report using WeasyPrint."""
    bias     = report.get("bias_found", False)
    btypes   = ", ".join(report.get("bias_types", []))
    recs     = report.get("recommendations", [])
    laws     = report.get("legal_frameworks", []) + report.get("international_laws", [])
    appeal   = report.get("appeal_letter", "")
    risk     = report.get("risk_score", 0)
    urgency  = report.get("urgency_tier", "low")
    aff      = report.get("affected_characteristic", "")
    expl     = report.get("explanation", "")
    date_str = (report.get("created_at") or "")[:10]
    tl       = report.get("legal_timeline") or {}
    jur      = tl.get("jurisdiction", "")
    verdict_color = "#c0392b" if bias else "#27ae60"
    verdict_text  = "Bias Detected" if bias else "No Bias Found"

    rec_items  = "".join(f"<li>{r}</li>" for r in recs)
    law_items  = "".join(f"<li>{l}</li>" for l in laws)
    dl_rows    = ""
    for dl in sorted(tl.get("deadlines", []), key=lambda d: d.get("window_days", 9999))[:5]:
        dl_rows += f"<tr><td>{dl.get('window_days')}d</td><td>{dl.get('action','')}</td><td>{dl.get('body','')}</td></tr>"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12px; color: #2c2c2c; margin: 40px; line-height: 1.6; }}
  h1 {{ font-size: 20px; color: #1a1a2e; border-bottom: 2px solid #4f8ef7; padding-bottom: 8px; }}
  h2 {{ font-size: 14px; color: #1a1a2e; margin-top: 24px; margin-bottom: 6px; border-left: 3px solid #4f8ef7; padding-left: 8px; }}
  .verdict {{ background: {verdict_color}1a; border: 1px solid {verdict_color}; border-radius: 6px; padding: 12px 16px; margin: 16px 0; }}
  .verdict-title {{ font-size: 18px; font-weight: bold; color: {verdict_color}; }}
  .risk-box {{ background: #f5f5f5; border-radius: 6px; padding: 10px 14px; display: inline-block; margin: 8px 0; }}
  .appeal {{ background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; padding: 14px; font-family: 'Courier New', monospace; font-size: 11px; white-space: pre-wrap; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  th {{ background: #f0f0f0; padding: 6px 10px; text-align: left; font-size: 11px; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #eee; font-size: 11px; }}
  li {{ margin: 3px 0; }}
  .footer {{ margin-top: 40px; font-size: 10px; color: #999; border-top: 1px solid #eee; padding-top: 8px; }}
</style>
</head><body>
<h1>Verdict Watch — Bias Analysis Report</h1>
<p style="color:#666;font-size:11px;">Generated: {date_str} &nbsp;|&nbsp; Report ID: {report.get("id","")[:8]} &nbsp;|&nbsp; Decision type: {report.get("decision_type","").replace("_"," ").title()}</p>

<div class="verdict">
  <div class="verdict-title">{verdict_text}</div>
  <div style="margin-top:6px;color:#555;">Confidence: {int(report.get("confidence_score",0)*100)}% &nbsp;|&nbsp; Affected characteristic: {aff.title() if aff else "—"} &nbsp;|&nbsp; Severity: {report.get("severity","").title()}</div>
  <div style="margin-top:6px;"><strong>Bias types:</strong> {btypes or "None detected"}</div>
</div>

<div class="risk-box">
  <strong>Risk score:</strong> {risk}/100 &nbsp;|&nbsp; <strong>Urgency:</strong> {urgency.title()} &nbsp;|&nbsp; <strong>Escalation recommended:</strong> {"Yes" if report.get("escalation_flag") else "No"}
</div>

<h2>What went wrong</h2>
<p>{expl or "—"}</p>

<h2>Original outcome vs fair outcome</h2>
<table><tr><th>Original</th><th>Should have been</th></tr>
<tr><td>{(report.get("original_outcome") or "—").upper()}</td><td>{report.get("fair_outcome") or "—"}</td></tr></table>

<h2>What you should do now</h2>
<ol>{rec_items or "<li>No recommendations available.</li>"}</ol>

<h2>Laws that protect you</h2>
<ul>{law_items or "<li>No legal frameworks identified.</li>"}</ul>

{f'<h2>Your legal deadlines — {jur}</h2><table><tr><th>Days</th><th>Action</th><th>Body</th></tr>{dl_rows}</table>' if dl_rows else ""}

{f'<h2>Your appeal letter</h2><div class="appeal">{appeal}</div>' if appeal else ""}

<div class="footer">Verdict Watch — AI Bias Detection &amp; Legal Aid &nbsp;|&nbsp; This report is for informational purposes only and does not constitute legal advice. Consult a qualified solicitor for legal proceedings.</div>
</body></html>"""

    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError:
        return html.encode("utf-8")  # fallback to HTML bytes


def aggregate(hist):
    total  = len(hist)
    biased = sum(1 for r in hist if r.get("bias_found"))
    esc    = sum(1 for r in hist if r.get("escalation_flag"))
    dis    = sum(1 for r in hist if r.get("disability_bias"))
    avg_r  = round(sum(r.get("risk_score",0) for r in hist) / total) if total else 0
    tl     = sum(1 for r in hist if (r.get("legal_timeline") or {}).get("deadlines"))
    by_type: dict = {}
    urg_breakdown  = {"immediate":0,"high":0,"medium":0,"low":0}
    jurisdictions  = []
    fs_list        = []
    for r in hist:
        for bt in r.get("bias_types",[]): nbt=normalize_bias(bt); by_type[nbt] = by_type.get(nbt,0)+1
        ut = (r.get("urgency_tier") or "low").lower()
        urg_breakdown[ut] = urg_breakdown.get(ut,0)+1
        jur = (r.get("legal_timeline") or {}).get("jurisdiction","")
        if jur: jurisdictions.append(jur)
        fs = (r.get("fairness_scores") or {}).get("overall_fairness_score")
        if fs is not None:
            try: fs_list.append(int(fs))
            except: pass
    avg_fs = round(sum(fs_list)/len(fs_list)) if fs_list else None
    return {
        "total":total,"biased":biased,
        "bias_pct": round(biased/total*100) if total else 0,
        "escalated":esc,"disability":dis,"avg_risk":avg_r,
        "avg_fairness":avg_fs,"timeline_count":tl,
        "by_type":by_type,"urg":urg_breakdown,"jurisdictions":jurisdictions,
    }

def render_results(report, source_text="", show_export_key=None):
    """Shared result renderer used by both Analyse and Try it now tabs."""
    if not report or not isinstance(report, dict):
        return

    bias      = report.get("bias_found", False)
    conf      = int(report.get("confidence_score", 0) * 100)
    btypes    = report.get("bias_types", [])
    aff       = report.get("affected_characteristic", "")
    orig      = (report.get("original_outcome") or "N/A").upper()
    _fair_raw = report.get("fair_outcome") or "N/A"
    fair      = _fair_raw[0].upper() + _fair_raw[1:] if _fair_raw and _fair_raw != "N/A" else _fair_raw
    expl      = report.get("explanation", "")
    recs      = report.get("recommendations", [])
    laws      = report.get("legal_frameworks", [])
    intl      = report.get("international_laws", [])
    phrases   = report.get("bias_phrases", [])
    sev       = report.get("severity", "low")
    fscore    = report.get("fairness_scores", {})
    risk      = report.get("risk_score", 0)
    urgency   = report.get("urgency_tier", "low")
    escalate  = report.get("escalation_flag", False)
    disability= report.get("disability_bias", False)
    intersect = report.get("intersectional_bias", {})
    appeal    = report.get("appeal_letter")
    spp       = report.get("severity_per_phrase", [])
    timeline  = report.get("legal_timeline") or {}
    precedents= report.get("precedents") or {}
    mode      = report.get("mode","full")
    done      = 4 if mode == "quick" else 10

    vc     = "var(--danger)" if bias else "var(--success)"
    vtitle = "Bias detected" if bias else "No bias found"
    vsub   = (f"{aff.title()}" + (f" · {sev.title()} severity" if bias and sev else "")) if aff else ("No protected characteristics triggered." if not bias else "")

    # Pipeline step tracker
    steps = [
        ("0","Pre-scan"),("1","Extract"),("2","Detect"),("3","Fair"),
        ("4","Audit"),("5","Trace"),("6","Risk"),("7","Appeal"),
        ("8","Timeline"),("9","Precedents"),
    ]
    step_html = '<div class="pipeline-row">'
    for i,(n,lbl) in enumerate(steps):
        cls = "step-done" if i < done else ("step-v21" if i >= 8 else "step-idle")
        ico = "✓" if i < done else ("✦" if i >= 8 else n)
        step_html += f'<div class="step"><div class="step-ico {cls}">{ico}</div><div class="step-lbl">{lbl}</div></div>'
    step_html += '</div>'
    st.markdown(step_html, unsafe_allow_html=True)

    # Summary / Full evidence toggle — persisted in session state
    _rpt_key = f"view_toggle_{report.get('id','x')[:6]}"
    if _rpt_key not in st.session_state:
        st.session_state[_rpt_key] = "Summary"

    _tc1, _tc2, _tc3 = st.columns([1.2, 1.2, 6])
    with _tc1:
        if st.button("Summary", key=f"tog_sum_{_rpt_key}",
                     type="primary" if st.session_state[_rpt_key]=="Summary" else "secondary",
                     use_container_width=True):
            st.session_state[_rpt_key] = "Summary"
            st.rerun()
    with _tc2:
        if st.button("Full evidence", key=f"tog_full_{_rpt_key}",
                     type="primary" if st.session_state[_rpt_key]=="Full evidence" else "secondary",
                     use_container_width=True):
            st.session_state[_rpt_key] = "Full evidence"
            st.rerun()
    with _tc3:
        _hint = "Showing key findings and your appeal letter." if st.session_state[_rpt_key]=="Summary" else "Showing all 10 steps of evidence."
        st.markdown(f'<div style="font-size:11px;color:var(--muted2);padding-top:10px;">{_hint}</div>', unsafe_allow_html=True)

    show_summary = st.session_state[_rpt_key]

    # 1. Verdict (with provider badge inline)
    ai_prov  = report.get("ai_provider","")
    ai_model = report.get("ai_model","")
    prov_badge_html = ""
    if ai_prov or ai_model:
        prov_label = ai_model if ai_model else ai_prov
        prov_badge_html = f'<span class="provider-badge" style="float:right;margin-top:2px;">via {prov_label}</span>'
    st.markdown(f"""
<div class="verdict {'verdict-bias' if bias else 'verdict-clean'}">
  <div class="verdict-row">
    <div>
      <div class="verdict-title" style="color:{vc};">{vtitle}</div>
      <div class="verdict-sub">{vsub} {prov_badge_html}</div>
      <div class="verdict-chips">{bias_chips(btypes)}</div>
    </div>
    <div style="text-align:right;">
      <div class="verdict-conf" style="color:{vc};">{conf}%</div>
      <div class="verdict-conf-lbl">confidence</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # 2. Escalation banner
    if escalate:
        st.markdown(f'<div class="banner-esc"><strong>Escalation recommended</strong> — Risk score {risk}/100. This case meets the threshold for formal legal action. Contact a legal aid organisation immediately.</div>', unsafe_allow_html=True)

    # 3. Disability / intersectional
    if disability:
        st.markdown('<div class="banner-dis">Disability bias detected — this decision may violate the ADA, CRPD, or equivalent national protections.</div>', unsafe_allow_html=True)
    if isinstance(intersect, dict) and intersect.get("detected"):
        combos = ", ".join(intersect.get("combinations", []))
        st.markdown(f'<div class="banner-int">Intersectional bias: {combos or "multiple characteristics combined."}</div>', unsafe_allow_html=True)

    # 4. Risk panel
    if bias:
        urg_bg, urg_border = URGENCY_COLORS.get(urgency, URGENCY_COLORS["low"])
        rc = score_col(risk)
        st.markdown(f"""
<div class="risk-panel" style="background:{urg_bg};border-color:{urg_border};">
  <div>
    <div class="risk-num" style="color:{rc};">{risk}</div>
    <div class="risk-sub">/ 100 risk score</div>
  </div>
  <div>
    {urg_badge(urgency, risk)}
    <div style="font-size:12px;color:var(--muted);margin-top:8px;line-height:1.5;">
      {'Formal escalation recommended — risk exceeds threshold.' if escalate else 'No escalation required at this risk level.'}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # 5. Outcomes
    st.markdown(f"""
<div class="outcome-row">
  <div class="out-bad">
    <div class="out-lbl" style="color:var(--danger);">Original outcome</div>
    <div class="out-val" style="color:var(--danger);">{orig}</div>
  </div>
  <div class="out-good">
    <div class="out-lbl" style="color:var(--success);">Should have been</div>
    <div class="out-val" style="color:var(--success);font-size:14px;">{fair}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # 6. Explanation
    if expl:
        st.markdown(f'<div class="card"><div class="clbl">What went wrong with your application</div><div style="font-size:14px;color:var(--muted);line-height:1.7;">{expl}</div></div>', unsafe_allow_html=True)

    # 6b. Appeal letter — moved up, most actionable output
    if appeal:
        st.markdown('<div class="card"><div class="clbl">Your appeal letter — ready to send</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="max-height:340px;overflow-y:auto;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg3);padding:14px;margin-bottom:8px;"><pre style="font-family:var(--mono);font-size:12px;color:var(--muted);line-height:1.9;white-space:pre-wrap;margin:0;">{appeal}</pre></div>', unsafe_allow_html=True)
        _ap_key = show_export_key or f"dl_appeal_up_{report.get('id','x')[:6]}"
        _ap1, _ap2 = st.columns([1,1])
        with _ap1:
            st.download_button("Download letter (.txt)", data=appeal,
                file_name=f"appeal_{(report.get('id') or 'r')[:8]}.txt",
                mime="text/plain", key=_ap_key)
        with _ap2:
            with st.expander("Copy to clipboard"):
                st.code(appeal, language=None)
    elif bias and not appeal:
        if st.button("Generate your appeal letter", key="gen_appeal_up", type="secondary"):
            with st.spinner("Drafting your appeal letter…"):
                try:
                    letter = services.generate_appeal_letter(
                        report, source_text or "",
                        report.get("decision_type","other"),
                        resolve_provider(st.session_state.get("model_choice","auto"))
                    )
                    report["appeal_letter"] = letter
                    if "last_report" in st.session_state:
                        st.session_state["last_report"]["appeal_letter"] = letter
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not generate letter: {e}")

    # 7. Highlighted text (full evidence)
    if source_text and phrases and show_summary != "Summary":
        hl = highlight(source_text, phrases, btypes)
        st.markdown(f'<div class="card"><div class="clbl">The exact phrases that flagged as discriminatory</div><div style="font-size:14px;line-height:1.9;color:var(--muted);">{hl}</div></div>', unsafe_allow_html=True)

    # 8. Phrase severity table (full evidence only)
    if show_summary != "Summary" and spp and isinstance(spp, list):
        has_char = any(p.get("characteristic_triggered","").strip() for p in spp[:8])
        rows = "".join(
            f'<tr>'
            f'<td style="font-family:var(--mono);font-size:12px;color:var(--text);padding:6px 8px;">{p.get("phrase","")}</td>'
            f'<td class="sev-{p.get("severity","l")[0]}" style="padding:6px 8px;white-space:nowrap;">{p.get("severity","").title()}</td>'
            + (f'<td style="color:var(--muted);font-size:12px;padding:6px 8px;">{p.get("characteristic_triggered","") or normalize_bias(btypes[0]) if btypes else "—"}</td>' if has_char else "")
            + '</tr>'
            for p in spp[:8]
        )
        char_header = "<th>Characteristic</th>" if has_char else ""
        st.markdown(f'<div class="card"><div class="clbl">Phrase severity breakdown</div><table class="spp"><thead><tr><th>Phrase</th><th>Severity</th>{char_header}</tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

    # 9. Fairness scores (full evidence only)
    if show_summary != "Summary" and fscore and isinstance(fscore, dict):
        overall  = fscore.get("overall_fairness_score")
        verdict  = fscore.get("fairness_verdict","")
        dp       = fscore.get("demographic_parity_scores",{})
        if overall is not None:
            bars = bar_html("Overall fairness", int(overall))
            if dp: bars += "".join(bar_html(k.replace("_"," ").title(), int(v)) for k,v in list(dp.items())[:4])
            vc2 = {"fair":"var(--success)","partially_fair":"var(--warn)","unfair":"var(--danger)"}.get(verdict,"var(--muted)")
            vl  = {"fair":"✓ Fair","partially_fair":"Partially fair","unfair":"✗ Unfair"}.get(verdict, verdict)
            st.markdown(f'<div class="card"><div class="clbl">Fairness audit</div><div style="margin-bottom:10px;"><span style="color:{vc2};font-size:12px;font-weight:500;">{vl}</span></div>{bars}</div>', unsafe_allow_html=True)

    # 10. Recommendations
    if recs:
        rec_html = "".join(f'<div class="rec"><div class="rec-n">{i+1}</div><div class="rec-t">{r}</div></div>' for i,r in enumerate(recs))
        st.markdown(f'<div class="card"><div class="clbl">What you should do now</div>{rec_html}</div>', unsafe_allow_html=True)

    # 11. Legal frameworks
    all_laws = laws + intl
    if all_laws:
        law_html = "".join(f'<div class="law"><span class="law-sym">§</span>{l}</div>' for l in all_laws)
        st.markdown(f'<div class="card"><div class="clbl">Laws that protect you</div>{law_html}</div>', unsafe_allow_html=True)

    # 12. Appeal letter — shown in full evidence mode only (already shown above in summary)
    if show_summary != "Summary" and appeal:
        st.markdown('<div class="card"><div class="clbl">Your appeal letter</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="max-height:280px;overflow-y:auto;border:1px solid var(--border);border-radius:var(--radius);background:var(--bg3);padding:14px;margin-bottom:8px;"><pre style="font-family:var(--mono);font-size:12px;color:var(--muted);line-height:1.9;white-space:pre-wrap;margin:0;">{appeal}</pre></div>', unsafe_allow_html=True)

    # 13. Legal timeline
    if bias and timeline and isinstance(timeline, dict) and timeline.get("deadlines"):
        jur      = timeline.get("jurisdiction","")
        dls      = sorted(timeline.get("deadlines",[]), key=lambda d: d.get("window_days",9999))
        imm      = timeline.get("immediate_actions",[])
        evidence = timeline.get("evidence_to_preserve",[])
        probono  = timeline.get("pro_bono_resources",[])
        est      = timeline.get("estimated_timeline_months")

        dl_html = ""
        for dl in dls[:6]:
            days = dl.get("window_days",0); act = dl.get("action","")
            body = dl.get("body",""); desc = dl.get("window_description","")
            prio = dl.get("priority","medium"); pc = prio_col(prio)
            dl_html += f'<div class="tl-row"><div class="tl-days" style="color:{pc};">{days}d</div><div style="flex:1;"><div class="tl-act">{act}</div><div class="tl-body">{body}{" · "+desc if desc else ""}</div></div><span class="tl-prio" style="color:{pc};">{prio}</span></div>'

        imm_html = "".join(f'<div class="act-row"><div class="act-dot"></div><div style="color:var(--muted);line-height:1.5;">{a}</div></div>' for a in imm[:3])
        ev_html  = "".join(f'<div style="font-size:12px;color:var(--muted);padding:3px 0;border-bottom:1px solid var(--border);">◦ {e}</div>' for e in evidence[:5])
        pb_html  = " ".join(f'<span class="chip chip-v">{r}</span>' for r in probono[:4])
        est_note = f'<span style="font-size:11px;color:var(--muted2);margin-left:auto;">Est. ~{est} months</span>' if est else ""

        st.markdown(f"""
<div class="tl-box">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div class="clbl" style="margin-bottom:0;color:var(--violet);">Your legal deadlines</div>
    <div style="display:flex;align-items:center;gap:8px;"><span class="chip chip-v">{jur}</span>{est_note}</div>
  </div>
  <div style="font-size:10px;color:var(--muted2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px;">Filing deadlines</div>
  {dl_html}
  {('<div style="margin-top:12px;"><div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Do today</div>'+imm_html+'</div>') if imm_html else ""}
  {('<div style="margin-top:10px;"><div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Evidence to preserve</div>'+ev_html+'</div>') if ev_html else ""}
  {('<div style="margin-top:10px;"><div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Pro-bono resources</div>'+pb_html+'</div>') if pb_html else ""}
</div>""", unsafe_allow_html=True)

    # 14. Precedents (full evidence only)
    if show_summary != "Summary" and bias and precedents and isinstance(precedents, dict) and precedents.get("precedents"):
        cases    = precedents.get("precedents",[])
        strongest= precedents.get("strongest_precedent","")
        strategy = precedents.get("legal_strategy_hint","")
        win_prob = precedents.get("estimated_win_probability","")
        pc_col   = {"high":"var(--success)","medium":"var(--warn)","low":"var(--danger)"}.get((win_prob or "").lower(),"var(--muted)")
        prob_b   = f'<span style="color:{pc_col};font-size:11px;border:1px solid {pc_col};border-radius:4px;padding:2px 8px;">Win probability: {win_prob.title()}</span>' if win_prob else ""

        cases_html = ""
        for c in cases[:4]:
            name = c.get("case_name",""); rel = int(c.get("relevance_score",0))
            why  = c.get("why_relevant",""); prin = c.get("key_principle","")
            jur2 = c.get("jurisdiction",""); yr   = c.get("year","")
            is_s = name == strongest; rc2 = score_col(rel)
            border_s = "border-color:rgba(155,127,244,.5);" if is_s else ""
            sb    = '<span class="chip chip-v" style="font-size:10px;margin-left:6px;">Strongest</span>' if is_s else ""
            cases_html += f"""
<div class="prec-card" style="{border_s}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="flex:1;"><div class="prec-name">{name}{sb}</div><div class="prec-meta">{jur2}{' · '+str(yr) if yr else ''}</div></div>
    <div style="text-align:right;flex-shrink:0;"><div style="font-size:13px;font-weight:500;font-family:var(--mono);color:{rc2};">{rel}%</div><div style="font-size:10px;color:var(--muted2);">relevant</div></div>
  </div>
  <div class="prec-bar"><div style="width:{rel}%;height:100%;background:{rc2};border-radius:2px;"></div></div>
  <div style="font-size:12px;color:var(--muted);margin-top:8px;line-height:1.6;">{why}</div>
  {('<div style="font-size:12px;color:var(--muted2);margin-top:4px;padding-top:4px;border-top:1px solid var(--border);">Principle: '+prin+'</div>') if prin else ""}
</div>"""

        strat_html = f'<div style="font-size:12px;color:var(--violet);padding:8px 12px;background:var(--violet-d);border-radius:var(--radius);margin-top:4px;line-height:1.6;">Strategy: {strategy}</div>' if strategy else ""
        st.markdown(f"""
<div class="card" style="border-color:rgba(155,127,244,.2);">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <div class="clbl" style="margin-bottom:0;color:var(--violet);">Cases like yours that won</div>
    {prob_b}
  </div>
  {cases_html}{strat_html}
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# BRAND BAR
# ══════════════════════════════════════════════════════

gem = gemini_ok(); grq = groq_ok(); vtx = vertex_ok(); cld = claude_ok()
active = sum([gem, vtx, grq, cld])
dots = "".join(
    f'<span class="vw-dot {"vw-dot-ok" if ok else "vw-dot-off"}" title="{lbl}"></span>'
    for ok, lbl in [(gem,"Gemini"),(vtx,"Vertex AI"),(grq,"Groq"),(cld,"Claude")]
)
# Quick live stat for brand bar
_hist_quick = []
try: _hist_quick = services.get_all_reports()
except: pass
_total_q = len(_hist_quick)
_bias_q  = sum(1 for r in _hist_quick if r.get("bias_found"))
_stat_html = f'<span style="font-size:11px;color:var(--muted2);margin-right:16px;">{_bias_q} discriminatory decisions found from {_total_q} analysed</span>' if _total_q >= 3 else ""

st.markdown(f"""
<div class="vw-brand">
  <div class="vw-brand-name">⚖ Verdict Watch <span>AI bias detection & legal aid</span></div>
  <div style="display:flex;align-items:center;">
    {_stat_html}
    <div class="vw-providers">{dots}<span class="vw-provlbl">{active}/4 providers</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# NAV — single Streamlit button row, styled as tab bar
# ══════════════════════════════════════════════════════

st.markdown('<div class="vw-nav-bar">', unsafe_allow_html=True)
nav = st.columns(len(VIEWS))
for i, (vid, vlbl) in enumerate(zip(VIEWS, VIEW_LABELS)):
    with nav[i]:
        active_tab = st.session_state["view"] == vid
        if st.button(vlbl, key=f"nav_{vid}",
                     type="primary" if active_tab else "secondary",
                     use_container_width=True):
            st.session_state["view"] = vid
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

view = st.session_state["view"]
st.markdown('<div class="vw-page">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW: TRY IT NOW
# ══════════════════════════════════════════════════════

if view == "try":
    st.markdown("""
<div style="margin-bottom:20px;">
  <div style="font-size:22px;font-weight:500;color:var(--text);margin-bottom:8px;">Got a rejection you think was unfair?</div>
  <div style="font-size:15px;color:var(--muted);line-height:1.7;max-width:640px;">
    Paste it below. In 25 seconds we'll tell you if it was discriminatory, which laws were violated, and give you a formal appeal letter ready to send.
  </div>
  <div style="display:flex;gap:20px;margin-top:16px;flex-wrap:wrap;">
    <div style="font-size:13px;color:var(--muted2);">✓ Free to use</div>
    <div style="font-size:13px;color:var(--muted2);">✓ No account needed</div>
    <div style="font-size:13px;color:var(--muted2);">✓ Works on job, loan, medical & university decisions</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Sample picker — wrapped for CSS scoping
    idx = st.session_state["test_idx"]
    st.markdown('<div class="sample-picker-wrap">', unsafe_allow_html=True)
    s_cols = st.columns(4, gap="small")
    for i, s in enumerate(TEST_SAMPLES):
        with s_cols[i]:
            active_s = idx == i
            if st.button(
                s["label"],
                key=f"sample_{i}",
                type="primary" if active_s else "secondary",
                use_container_width=True,
                help=TYPE_LABELS[s["dtype"]],
            ):
                st.session_state["test_idx"] = i
                st.session_state["test_report"] = None
                st.rerun()
            st.markdown(f'<div style="font-size:11px;color:var(--muted2);margin-top:3px;text-align:center;">{TYPE_LABELS[s["dtype"]]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Decision text preview
    sample = TEST_SAMPLES[st.session_state["test_idx"]]
    sample_chars = len(sample["text"])
    st.markdown(f"""
<div class="card" style="margin-top:12px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div class="clbl" style="margin-bottom:0;">Decision text</div>
    <div style="font-size:11px;color:var(--muted2);font-family:var(--mono);">{sample_chars} chars · {TYPE_LABELS.get(sample["dtype"],"")}</div>
  </div>
  <div style="font-size:13px;color:var(--muted);line-height:1.8;font-style:italic;">"{sample["text"]}"</div>
</div>
""", unsafe_allow_html=True)

    # Run button — demo mode when no API key
    if not any_api_ok():
        st.markdown("""
<div style="background:rgba(155,127,244,.08);border:1px solid rgba(155,127,244,.3);border-radius:var(--radius);padding:12px 16px;margin-bottom:10px;">
  <div style="font-size:13px;font-weight:500;color:var(--violet);margin-bottom:4px;">Demo mode — no API key needed</div>
  <div style="font-size:12px;color:var(--muted);line-height:1.5;">Click Run to see a realistic pre-built result showing exactly what the tool produces. To run live analysis on your own decision, add GEMINI_API_KEY to your .env file.</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="run-btn-wrap">', unsafe_allow_html=True)
    run_test = st.button(
        "Run full analysis →",
        key="run_test",
        disabled=False,  # always enabled — demo mode works without key
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
    if any_api_ok():
        st.markdown('<div style="font-size:11px;color:var(--muted2);margin-top:3px;">No setup needed — results appear below in ~25 seconds.</div>', unsafe_allow_html=True)

    # What you'll see preview (only shown before first run)
    if not st.session_state.get("test_report"):
        st.markdown("""
<div style="margin-top:20px;">
<div class="clbl">What the analysis produces</div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:8px;">
  <div class="card" style="margin-bottom:0;">
    <div style="font-size:20px;margin-bottom:6px;">⚖</div>
    <div style="font-size:13px;font-weight:500;color:var(--text);margin-bottom:3px;">Bias verdict</div>
    <div style="font-size:12px;color:var(--muted);line-height:1.5;">Detects bias across 9 dimensions with confidence score and risk rating 0–100.</div>
  </div>
  <div class="card" style="margin-bottom:0;">
    <div style="font-size:20px;margin-bottom:6px;">📄</div>
    <div style="font-size:13px;font-weight:500;color:var(--text);margin-bottom:3px;">Appeal letter</div>
    <div style="font-size:12px;color:var(--muted);line-height:1.5;">Formal legal letter citing exact discriminatory phrases and applicable law. Ready to send.</div>
  </div>
  <div class="card" style="margin-bottom:0;">
    <div style="font-size:20px;margin-bottom:6px;">⏱</div>
    <div style="font-size:13px;font-weight:500;color:var(--text);margin-bottom:3px;">Legal timeline</div>
    <div style="font-size:12px;color:var(--muted);line-height:1.5;">Filing deadlines, jurisdiction, pro-bono resources, and matching case-law precedents.</div>
  </div>
</div>
</div>""", unsafe_allow_html=True)

    if run_test:
        st.session_state["test_report"] = None
        if not any_api_ok():
            # Demo mode — show pre-built result
            import time as _time
            _demo_prog = st.empty()
            for _di in range(10):
                _bar = "".join(f'<div style="width:10%;height:4px;background:{"var(--success)" if i<_di else ("var(--accent)" if i==_di else "var(--bg4)")};border-radius:2px;"></div>' for i in range(10))
                _demo_prog.markdown(f'<div class="card" style="padding:14px 18px;"><div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="font-size:13px;color:var(--text);font-weight:500;">Loading demo result…</span><span style="font-size:11px;color:var(--muted2);font-family:var(--mono);">Step {_di+1}/10</span></div><div style="display:flex;gap:3px;margin-bottom:8px;">{_bar}</div></div>', unsafe_allow_html=True)
                _time.sleep(0.15)
            _demo_prog.empty()
            st.session_state["test_report"] = DEMO_REPORT
            st.rerun()
        _try_prog = st.empty()
        _step_names_try = [
            "Scanning for protected characteristics…","Extracting decision criteria…",
            "Detecting bias across 9 dimensions…","Determining fair outcome…",
            "Running counterfactual fairness audit…","Building explainability trace…",
            "Computing risk score…","Drafting appeal letter…",
            "Calculating legal deadlines…","Retrieving matching case-law…",
        ]
        def _try_progress(step_idx, msg=""):
            lbl = _step_names_try[step_idx] if step_idx < 10 else "Finalising…"
            bar_fill = "".join(
                f'<div style="width:10%;height:4px;background:{"var(--success)" if i < step_idx else ("var(--accent)" if i==step_idx else "var(--bg4)")};border-radius:2px;"></div>'
                for i in range(10)
            )
            _try_prog.markdown(f'''<div class="card" style="padding:14px 18px;"><div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="font-size:13px;color:var(--text);font-weight:500;">Running your analysis…</span><span style="font-size:11px;color:var(--muted2);font-family:var(--mono);">Step {step_idx+1}/10</span></div><div style="display:flex;gap:3px;margin-bottom:8px;">{bar_fill}</div><div style="font-size:12px;color:var(--muted);">{lbl}</div></div>''', unsafe_allow_html=True)
        _try_progress(0)
        rep, err = run_pipeline(sample["text"], sample["dtype"], "full", progress_fn=_try_progress)
        _try_prog.empty()
        if err:
            st.error(f"Pipeline failed: {err}")
        else:
            st.session_state["test_report"] = rep
            st.rerun()

    # Results
    test_report = st.session_state.get("test_report")
    if test_report:
        st.markdown(f'<hr class="div"><div style="font-size:11px;color:var(--muted2);margin-bottom:12px;">Results for: <strong style="color:var(--text);">{sample["label"]}</strong></div>', unsafe_allow_html=True)
        render_results(test_report, source_text=sample["text"], show_export_key="dl_test_appeal")

        st.markdown('<hr class="div">', unsafe_allow_html=True)
        if st.button("Analyse your own decision →", key="try_to_analyse"):
            st.session_state["view"] = "analyse"
            st.rerun()

# ══════════════════════════════════════════════════════
# VIEW: ANALYSE
# ══════════════════════════════════════════════════════

elif view == "analyse":
    # API key warning
    if not any_api_ok():
        st.markdown('<div class="banner-nokey">No API key found. Add GEMINI_API_KEY or GROQ_API_KEY to .env and restart.</div>', unsafe_allow_html=True)

    # Input card
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="clbl">Paste your decision letter or notice</div><div style="font-size:11px;color:var(--muted2);margin-bottom:6px;">Your text is processed by Gemini AI and stored anonymously on this server. It is not used for training and not shared with third parties.</div>', unsafe_allow_html=True)

    dec_text = st.text_area(
        "dec", label_visibility="collapsed", height=140,
        key="decision_input",
        placeholder="Paste the exact text you received — a rejection email, loan denial letter, medical notice, or university decision. The more verbatim the better.",
    )
    n = len((dec_text or "").strip())
    nc = "var(--success)" if n >= 60 else ("var(--warn)" if n >= 30 else "var(--danger)")
    st.markdown(f'<div style="font-size:12px;color:{nc};font-family:var(--mono);margin:4px 0 8px;">{n} chars {"· ready" if n >= 30 else "· minimum 30 required"}</div>', unsafe_allow_html=True)

    # Live pre-scan keyword signals
    if dec_text and n > 20:
        found = [d for d, pat in BIAS_KW.items() if re.search(pat, dec_text, re.IGNORECASE)]
        if found:
            chips = " ".join(f'<span class="chip chip-a">{d}</span>' for d in found)
            st.markdown(f'<div style="margin-bottom:8px;"><span style="font-size:12px;color:var(--muted2);margin-right:6px;">Pre-scan signals:</span>{chips}</div>', unsafe_allow_html=True)

    # Controls — type | mode | model pills | run (all one row conceptually, split across 2 for space)
    cr1, cr2, cr3 = st.columns([1.3, 1.7, 0.8])
    with cr1:
        dtype = st.selectbox(
            "Type", list(TYPE_LABELS.keys()),
            format_func=lambda x: TYPE_LABELS[x],
            index=list(TYPE_LABELS.keys()).index(st.session_state.get("last_dtype","job")),
            key="dtype_sel", label_visibility="collapsed",
        )
    with cr2:
        mode = st.radio(
            "Mode", ["full","quick"],
            format_func=lambda x: "Full analysis — includes appeal letter (~25s)" if x == "full" else "Quick check — verdict only (~4s)",
            horizontal=True, key="scan_sel",
        )
    with cr3:
        run_btn = st.button("Run analysis", key="run_btn",
                            disabled=not any_api_ok() or n < 30,
                            use_container_width=True)

    # Row 2: model selector (compact radio pills)
    st.markdown('<div class="model-sel-wrap" style="margin-top:8px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:var(--muted2);margin-bottom:3px;">via</div>', unsafe_allow_html=True)
    chosen_provider = render_model_selector(key="model_analyse")
    st.markdown('</div>', unsafe_allow_html=True)

    hint = ("Full analysis: bias verdict, what went wrong, a formal appeal letter ready to send, filing deadlines, and matching case-law."
            if mode == "full" else
            "Quick check: returns a bias verdict and confidence score in ~4 seconds. No appeal letter.")
    st.markdown(f'<div style="font-size:11px;color:var(--muted2);margin-top:2px;">{hint}</div>', unsafe_allow_html=True)

    # File upload inline
    st.markdown('<div style="margin-top:10px;"><div class="clbl">Or upload your letter (PDF or text file)</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("file", type=["txt","pdf"],
                                label_visibility="collapsed", key="file_up")
    if uploaded:
        fname = uploaded.name.lower()
        if fname.endswith(".txt"):
            st.session_state["decision_input"] = uploaded.read().decode("utf-8", errors="replace")
            st.rerun()
        elif fname.endswith(".pdf"):
            if PDF_SUPPORT:
                raw = uploaded.read()
                doc = pymupdf.open(stream=raw, filetype="pdf")
                content = "\n".join(p.get_text() for p in doc).strip()
                if content:
                    st.session_state["decision_input"] = content
                    st.rerun()
                else:
                    st.warning("Could not extract text from this PDF. Try pasting directly.")
            else:
                st.warning("PDF support requires PyMuPDF: pip install PyMuPDF")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # close input card

    # Run
    report = st.session_state.get("last_report")
    if run_btn:
        progress_placeholder = st.empty()
        step_names = [
            "Scanning for protected characteristics…",
            "Extracting decision criteria…",
            "Detecting bias across 9 dimensions…",
            "Determining fair outcome and laws violated…",
            "Running counterfactual fairness audit…",
            "Building explainability trace…",
            "Computing risk score…",
            "Drafting your appeal letter…",
            "Calculating legal filing deadlines…",
            "Retrieving matching case-law precedents…",
        ]

        def show_progress(step_idx, msg=""):
            pct = int((step_idx / 10) * 100)
            step_label = step_names[step_idx] if step_idx < len(step_names) else "Finalising…"
            bar_fill = "".join(
                f'<div style="width:10%;height:4px;background:{"var(--success)" if i < step_idx else ("var(--accent)" if i == step_idx else "var(--bg4)")};border-radius:2px;transition:background .3s;"></div>'
                for i in range(10)
            )
            progress_placeholder.markdown(f"""
<div class="card" style="padding:16px 20px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div style="font-size:13px;color:var(--text);font-weight:500;">Analysing your decision…</div>
    <div style="font-size:12px;color:var(--muted2);font-family:var(--mono);">Step {step_idx + 1}/10</div>
  </div>
  <div style="display:flex;gap:3px;margin-bottom:10px;">{bar_fill}</div>
  <div style="font-size:12px;color:var(--muted);">{step_label}</div>
</div>""", unsafe_allow_html=True)

        show_progress(0)
        rep, err = run_pipeline(dec_text, dtype, mode, provider=chosen_provider,
                                progress_fn=show_progress)
        progress_placeholder.empty()

        if err:
            st.error(f"Analysis failed: {err}")
        else:
            st.session_state["last_report"]  = rep
            st.session_state["last_text"]    = dec_text
            st.session_state["last_dtype"]   = dtype
            report = rep
            st.rerun()

    # Results
    if report:
        st.markdown('<hr class="div">', unsafe_allow_html=True)
        render_results(report, source_text=st.session_state.get("last_text",""),
                       show_export_key="dl_analyse_appeal")

        # Generate appeal — only needed if it wasn't auto-generated (quick mode)
        # The render_results function now handles this inline

        # New analysis + Feedback + export
        st.markdown('<hr class="div">', unsafe_allow_html=True)
        if st.button("← New analysis", key="clear_report", type="secondary"):
            st.session_state["last_report"] = None
            st.session_state["last_text"]   = ""
            st.session_state["decision_input"] = ""
            st.rerun()
        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
        fb1, fb2, _, ex1 = st.columns([1,1,3,1])
        with fb1:
            if st.button("👍 Accurate", key="fb_y", type="secondary"):
                services.save_feedback(report.get("id",""), 1, "")
                st.toast("Thanks — helps us improve!")
        with fb2:
            if st.button("👎 Something wrong", key="fb_n", type="secondary"):
                st.session_state["show_fb_text"] = True
        with ex1:
            st.download_button(
                "Export CSV",
                data=to_csv([report]),
                file_name=f"verdict_{(report.get('id') or 'r')[:8]}.csv",
                mime="text/csv",
                key="dl_analyse_csv",
            )
        # PDF report export
        _pdf_col, _ = st.columns([2, 5])
        with _pdf_col:
            if st.button("Export full PDF report", key="dl_pdf_btn", type="secondary"):
                with st.spinner("Generating PDF…"):
                    try:
                        pdf_bytes = generate_pdf_report(report)
                        st.download_button(
                            "Download PDF",
                            data=pdf_bytes,
                            file_name=f"verdict_report_{(report.get('id') or 'r')[:8]}.pdf",
                            mime="application/pdf",
                            key="dl_pdf_actual",
                        )
                    except Exception as _pdfe:
                        st.error(f"PDF generation failed: {_pdfe}")
        if st.session_state.get("show_fb_text"):
            fb_comment = st.text_input(
                "What did we get wrong?",
                placeholder="e.g. The bias type is wrong, the appeal letter missed the main issue…",
                key="fb_comment_text",
            )
            if st.button("Submit feedback", key="fb_submit", type="secondary"):
                services.save_feedback(report.get("id",""), 0, fb_comment)
                st.session_state["show_fb_text"] = False
                st.toast("Feedback submitted — thank you.")
                st.rerun()
    else:
        st.markdown("""
<div class="empty">
  <div style="font-size:2.5rem;opacity:.1;margin-bottom:16px;">⚖</div>
  <div class="empty-t">Paste your decision above</div>
  <div class="empty-s">
    Copy the exact text from your rejection letter, loan denial, or triage notice and paste it in the box above.<br><br>
    <strong style="color:var(--muted);">Full analysis</strong> takes ~25 seconds and gives you a complete legal picture — including a formal appeal letter ready to send.<br><br>
    <strong style="color:var(--muted);">Quick check</strong> gives you a verdict in ~4 seconds.
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW: BATCH
# ══════════════════════════════════════════════════════

elif view == "batch":
    st.markdown(f"""
<div style="margin-bottom:16px;">
  <div style="font-size:16px;font-weight:500;color:var(--text);margin-bottom:6px;">Batch analysis — for organisations and researchers</div>
  <div style="font-size:13px;color:var(--muted);line-height:1.6;">Analyse up to {services.BATCH_MAX_ROWS} decisions at once. Built for compliance officers, advocacy groups, and researchers who need to audit multiple decisions systematically. Separate decisions with a blank line or upload a CSV with a <code style="font-family:var(--mono);color:var(--accent);font-size:12px;">text</code> column.</div>
</div>
""", unsafe_allow_html=True)

    bmode = st.radio("Input mode", ["Paste text","Upload CSV"],
                     horizontal=True, label_visibility="collapsed", key="bm")
    blocks = []

    if bmode == "Paste text":
        bt = st.text_area("Batch input", height=120, label_visibility="collapsed",
                          key="b_in", placeholder="Decision 1\n\nDecision 2\n\nDecision 3…")
        if bt:
            blocks = [b.strip() for b in re.split(r'\n\s*\n', bt)
                      if b.strip() and len(b.strip()) >= 30]
    else:
        c_up, c_dl = st.columns([3,1])
        with c_up:
            bf = st.file_uploader("CSV", type=["csv"],
                                  label_visibility="collapsed", key="b_csv")
            if bf:
                try:
                    dfu = pd.read_csv(bf)
                    if "text" in dfu.columns:
                        blocks = [t for t in dfu["text"].dropna().tolist()
                                  if len(str(t).strip()) >= 30]
                        st.success(f"{len(blocks)} decisions loaded from CSV.")
                    else:
                        st.error("CSV must have a column named 'text'.")
                except Exception as e:
                    st.error(f"Could not read CSV: {e}")
        with c_dl:
            st.download_button("Sample CSV (12 decisions)",
                               data=_SAMPLE_CSV,
                               file_name="sample_decisions_v21.csv",
                               mime="text/csv", key="sample_dl")

    # Controls row
    bc1, bc2, bc3 = st.columns([1.8, 1.5, 1.2])
    with bc1:
        btype = st.selectbox("Decision type", list(TYPE_LABELS.keys()),
                             format_func=lambda x: TYPE_LABELS[x],
                             label_visibility="collapsed", key="b_type")
    with bc2:
        queued = len(blocks)
        qc = "var(--accent)" if queued else "var(--muted2)"
        st.markdown(f'<div style="font-size:13px;color:{qc};font-family:var(--mono);padding-top:8px;">{queued} decision{"s" if queued!=1 else ""} queued</div>', unsafe_allow_html=True)
    with bc3:
        brun = st.button("Run audit", key="b_run",
                         disabled=not any_api_ok() or not blocks,
                         use_container_width=True)

    # Model selector for batch
    st.markdown('<div class="model-sel-wrap" style="margin-top:8px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:var(--muted2);margin-bottom:3px;">via</div>', unsafe_allow_html=True)
    batch_provider = render_model_selector(key="model_batch")
    st.markdown('</div>', unsafe_allow_html=True)

    if brun:
        n_run = min(len(blocks), services.BATCH_MAX_ROWS)
        if len(blocks) > services.BATCH_MAX_ROWS:
            st.warning(f"Only first {services.BATCH_MAX_ROWS} decisions will be processed.")
        blocks = blocks[:n_run]

        prog   = st.progress(0)
        status = st.empty()
        results = []
        for i, blk in enumerate(blocks):
            status.markdown(f'<div style="font-size:12px;color:var(--accent);font-family:var(--mono);">Analysing {i+1}/{n_run}: {trunc(blk, 60)}…</div>', unsafe_allow_html=True)
            rep, err = run_pipeline(blk, btype, "full", provider=batch_provider)
            results.append({"text": blk, "report": rep, "error": err})
            prog.progress((i+1)/n_run)
        prog.empty(); status.empty()
        st.session_state["batch_results"] = results

    batch = st.session_state.get("batch_results")
    if batch:
        valid   = [r for r in batch if isinstance(r.get("report"), dict)]
        b_cnt   = sum(1 for r in valid if r["report"].get("bias_found"))
        esc_cnt = sum(1 for r in valid if r["report"].get("escalation_flag"))
        dis_cnt = sum(1 for r in valid if r["report"].get("disability_bias"))
        avg_r   = round(sum(r["report"].get("risk_score",0) for r in valid)/len(valid)) if valid else 0
        tl_cnt  = sum(1 for r in valid if (r["report"].get("legal_timeline") or {}).get("deadlines"))

        m1,m2,m3,m4,m5,m6,m7 = st.columns(7)
        m1.metric("Processed", len(valid))
        m2.metric("Bias found", b_cnt)
        m3.metric("Escalations", esc_cnt)
        m4.metric("Disability", dis_cnt)
        m5.metric("Avg risk", f"{avg_r}/100")
        m6.metric("Timelines", tl_cnt)
        m7.metric("Errors", len(batch)-len(valid))

        rows = []
        for i, res in enumerate(batch, 1):
            rep = res.get("report"); err = res.get("error","")
            if err:
                rows.append({"#":i,"Text":trunc(res["text"],55),"Result":"ERROR","Conf":"—","Risk":"—","Urgency":"—","Jurisdiction":"—"})
            elif isinstance(rep, dict):
                rows.append({
                    "#": i,
                    "Text": trunc(res["text"], 55),
                    "Result": "Discriminatory" if rep.get("bias_found") else "No issue found",
                    "Conf":  f"{int(rep.get('confidence_score',0)*100)}%",
                    "Risk":  rep.get("risk_score",0),
                    "Urgency": rep.get("urgency_tier","low").title(),
                    "Jurisdiction": (rep.get("legal_timeline") or {}).get("jurisdiction","—"),
                })
        if rows:
            st.markdown("<br>", unsafe_allow_html=True)
            dl_col, _ = st.columns([1,4])
            with dl_col:
                st.download_button(
                    "Export batch CSV",
                    data=to_csv([r["report"] for r in valid]),
                    file_name=f"verdict_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv", key="batch_dl",
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════
# VIEW: REPORTS
# ══════════════════════════════════════════════════════

elif view == "reports":
    hist = get_all()

    if hist:
        agg = aggregate(hist)

        # Aggregate metrics
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        m1.metric("Total reports",  agg["total"])
        m2.metric("Bias found",     f"{agg['biased']} ({agg['bias_pct']}%)")
        m3.metric("Escalations",    agg["escalated"])
        m4.metric("Avg risk score", f"{agg['avg_risk']}/100")
        m5.metric("Disability",     agg["disability"])
        m6.metric("Avg fairness",   f"{agg['avg_fairness']}/100" if agg["avg_fairness"] is not None else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        # Urgency breakdown
        urg = agg["urg"]
        if any(urg.values()):
            total_u = sum(urg.values()) or 1
            urg_html = ""
            for tier, count in urg.items():
                pct = round(count/total_u*100)
                col = {"immediate":"var(--danger)","high":"var(--warn)","medium":"var(--accent)","low":"var(--success)"}.get(tier,"var(--muted)")
                urg_html += f'<div class="urg-bar-row"><span style="color:{col};min-width:80px;">{tier.title()}</span><div style="flex:1;height:6px;background:var(--bg3);border-radius:3px;"><div style="width:{pct}%;height:100%;background:{col};border-radius:3px;"></div></div><span style="font-family:var(--mono);font-size:11px;color:var(--muted);min-width:32px;text-align:right;">{count}</span></div>'
            st.markdown(f'<div class="card"><div class="clbl">Urgency breakdown</div>{urg_html}</div>', unsafe_allow_html=True)

        # Escalation alert strip — clicking button sets the filter
        if agg["escalated"]:
            st.markdown(f'<div class="banner-esc"><strong>{agg["escalated"]} case{"s" if agg["escalated"]!=1 else ""}</strong> require immediate action (risk ≥ 65).</div>', unsafe_allow_html=True)
            if st.button("Show escalated cases only →", key="esc_filter_btn", type="secondary"):
                st.session_state["_esc_filter"] = True
                st.rerun()

    # Filter bar
    f1,f2,f3,f4,f5 = st.columns([3,1,1,1,1])
    with f1: q  = st.text_input("Search", placeholder="Bias type, characteristic, outcome…", label_visibility="collapsed", key="h_q")
    with f2: fv = st.selectbox("Verdict",    ["All","Bias","No bias"],        label_visibility="collapsed", key="h_v")
    with f3: fe = st.selectbox("Escalation", ["All","Escalated only"],        label_visibility="collapsed", key="h_e")
    with f4: sv = st.selectbox("Sort",       ["Newest","Oldest","High risk","Low risk"], label_visibility="collapsed", key="h_s")
    with f5:
        if hist:
            st.download_button("Export CSV",
                               data=to_csv(hist),
                               file_name=f"verdict_reports_{datetime.now().strftime('%Y%m%d')}.csv",
                               mime="text/csv", key="rep_export",
                               use_container_width=True)

    if not hist:
        st.markdown("""
<div class="empty">
  <div class="empty-t">No reports yet</div>
  <div class="empty-s">Run your first analysis in the Analyse tab or try a sample in Try it now.<br><br>
  Reports, metrics, and trend data will appear here once you have results.</div>
</div>""", unsafe_allow_html=True)
    else:
        # Apply filter from escalation button if set
        if st.session_state.pop("_esc_filter", False):
            fe = "Escalated only"

        filt = list(hist)
        if fv == "Bias":           filt = [r for r in filt if r.get("bias_found")]
        elif fv == "No bias":      filt = [r for r in filt if not r.get("bias_found")]
        if fe == "Escalated only": filt = [r for r in filt if r.get("escalation_flag")]
        if q:
            ql = q.lower()
            filt = [r for r in filt if
                    ql in (r.get("affected_characteristic") or "").lower() or
                    any(ql in bt.lower() for bt in r.get("bias_types",[])) or
                    ql in (r.get("original_outcome") or "").lower()]
        if sv == "Newest":     filt.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        elif sv == "Oldest":   filt.sort(key=lambda r: r.get("created_at") or "")
        elif sv == "High risk":filt.sort(key=lambda r: r.get("risk_score",0), reverse=True)
        else:                  filt.sort(key=lambda r: r.get("risk_score",0))

        st.markdown(f'<div style="font-size:12px;color:var(--muted2);margin-bottom:8px;">{len(filt)} of {len(hist)} reports</div>', unsafe_allow_html=True)

        rows = [{
            "ID":           f"#{(r.get('id') or '')[:8]}",
            "Type":         TYPE_LABELS.get(r.get("decision_type","other"),"—"),
            "Result":       "Discriminatory" if r.get("bias_found") else "No issue found",
            "Confidence":   f"{int(r.get('confidence_score',0)*100)}%",
            "Risk":         r.get("risk_score",0),
            "Urgency":      r.get("urgency_tier","low").title(),
            "Escalation":   "Yes" if r.get("escalation_flag") else "—",
            "Disability":   "Yes" if r.get("disability_bias") else "—",
            "Jurisdiction": (r.get("legal_timeline") or {}).get("jurisdiction","—"),
            "Date":         (r.get("created_at") or "")[:10],
        } for r in filt[:200]]

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── Per-report detail expanders (top 5 bias cases) ──
            bias_filt = [r for r in filt if r.get("bias_found")][:5]
            if bias_filt:
                st.markdown('<div style="margin-top:16px;"><div class="clbl">Report detail — top 5 bias cases</div></div>', unsafe_allow_html=True)
                for r in bias_filt:
                    rid   = (r.get("id") or "")[:8]
                    rs    = r.get("risk_score",0)
                    aff   = r.get("affected_characteristic","")
                    dt    = (r.get("created_at") or "")[:10]
                    btypes= r.get("bias_types",[])
                    with st.expander(f"#{rid} · Risk {rs}/100 · {aff.title() if aff else 'Unknown'} · {dt}"):
                        ex1, ex2 = st.columns(2)
                        with ex1:
                            st.markdown(f'<div class="card"><div class="clbl">What went wrong with your application</div><div style="font-size:13px;color:var(--muted);line-height:1.6;">{r.get("explanation","—")}</div></div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="card"><div class="clbl">Bias types</div>{bias_chips(btypes)}</div>', unsafe_allow_html=True)
                        with ex2:
                            recs = r.get("recommendations",[])
                            if recs:
                                rec_html = "".join(f'<div class="rec"><div class="rec-n">{i+1}</div><div class="rec-t">{rec}</div></div>' for i,rec in enumerate(recs[:3]))
                                st.markdown(f'<div class="card"><div class="clbl">What you should do now</div>{rec_html}</div>', unsafe_allow_html=True)
                            laws = r.get("legal_frameworks",[]) + r.get("international_laws",[])
                            if laws:
                                lh = "".join(f'<div class="law"><span class="law-sym">§</span>{l}</div>' for l in laws[:3])
                                st.markdown(f'<div class="card"><div class="clbl">Legal frameworks</div>{lh}</div>', unsafe_allow_html=True)
                        if r.get("appeal_letter"):
                            st.code(r["appeal_letter"][:400] + ("…" if len(r["appeal_letter"])>400 else ""), language=None)
                            _rdl1, _rdl2 = st.columns(2)
                            with _rdl1:
                                st.download_button("Download appeal (.txt)", data=r["appeal_letter"],
                                    file_name=f"appeal_{rid}.txt", mime="text/plain", key=f"rep_dl_{rid}")
                            with _rdl2:
                                if st.button("Export PDF report", key=f"pdf_btn_{rid}", type="secondary"):
                                    try:
                                        _pdf = generate_pdf_report(r)
                                        st.download_button("Download PDF", data=_pdf,
                                            file_name=f"report_{rid}.pdf", mime="application/pdf",
                                            key=f"pdf_dl_{rid}")
                                    except Exception as _e:
                                        st.error(str(_e))

        # ── Time-series bias rate chart ──
        if hist and len(hist) >= 5:
            try:
                if not PLOTLY_OK: raise ImportError('plotly not installed')
                import pandas as _pd
                go = _go

                _df = _pd.DataFrame([{
                    "date": (r.get("created_at") or "")[:10],
                    "bias": 1 if r.get("bias_found") else 0,
                    "risk": r.get("risk_score", 0),
                } for r in hist if (r.get("created_at") or "")[:10]]).sort_values("date")

                _daily = _df.groupby("date").agg(
                    total=("bias","count"),
                    biased=("bias","sum"),
                    avg_risk=("risk","mean")
                ).reset_index()
                _daily["bias_rate"] = (_daily["biased"] / _daily["total"] * 100).round(0)

                _fig = go.Figure()
                _fig.add_trace(go.Scatter(
                    x=_daily["date"], y=_daily["bias_rate"],
                    mode="lines+markers", name="Bias rate %",
                    line=dict(color="#e05454", width=2),
                    marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(224,84,84,.08)",
                ))
                _fig.add_trace(go.Scatter(
                    x=_daily["date"], y=_daily["avg_risk"],
                    mode="lines", name="Avg risk score",
                    line=dict(color="#4f8ef7", width=1.5, dash="dot"),
                    yaxis="y2",
                ))
                _fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="IBM Plex Sans", size=11, color="#808088"),
                    margin=dict(l=0, r=0, t=8, b=0),
                    height=200,
                    showlegend=True,
                    legend=dict(orientation="h", x=0, y=1.15, font=dict(size=11)),
                    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=10)),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.06)", zeroline=False,
                               ticksuffix="%", range=[0,105]),
                    yaxis2=dict(overlaying="y", side="right", showgrid=False, zeroline=False,
                                range=[0,105], tickfont=dict(size=10)),
                )
                st.markdown('<div class="card"><div class="clbl">Bias rate over time</div></div>', unsafe_allow_html=True)
                st.plotly_chart(_fig, use_container_width=True, config={"displayModeBar": False})
            except Exception as _pe:
                pass  # plotly not installed or insufficient data

        # Bottom analytics
        if hist and len(hist) >= 3:
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2, gap="medium")
            with c1:
                by_type = agg["by_type"]
                counts  = sorted(by_type.items(), key=lambda x: x[1], reverse=True)
                if counts:
                    mc = max(c for _,c in counts)
                    bars = ""
                    for i,(lbl,cnt) in enumerate(counts[:9]):
                        pct = int(cnt/mc*100)
                        col = ["var(--danger)","var(--warn)","var(--accent)","var(--success)","var(--muted)"][i%5]
                        bars += f'<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;"><span style="color:var(--muted);">{lbl}</span><span style="color:{col};font-family:var(--mono);">{cnt}</span></div><div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{col};"></div></div></div>'
                    st.markdown(f'<div class="card"><div class="clbl">Bias type frequency</div>{bars}</div>', unsafe_allow_html=True)
            with c2:
                jurs = agg["jurisdictions"]
                if jurs:
                    jc = Counter(jurs).most_common(6); jt = len(jurs) or 1
                    jhtml = ""
                    for j, cnt in jc:
                        pct = int(cnt/jt*100)
                        jhtml += f'<div style="margin-bottom:7px;"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;"><span style="color:var(--muted);">{j}</span><span style="color:var(--violet);font-family:var(--mono);">{cnt}</span></div><div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:var(--violet);"></div></div></div>'
                    st.markdown(f'<div class="card"><div class="clbl">Jurisdictions — V21 timelines</div>{jhtml}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# VIEW: SETTINGS
# ══════════════════════════════════════════════════════

elif view == "settings":
    # ── Provider status (full width, stacked) ──
    st.markdown('<div class="clbl">API providers</div>', unsafe_allow_html=True)
    vtx_proj = os.getenv("GOOGLE_CLOUD_PROJECT","not set")

    prov_data = [
        (vertex_ok, "Vertex AI",   "Steps 4–5",     "GOOGLE_CLOUD_PROJECT",
         f"Project: {vtx_proj}", f"Set GOOGLE_CLOUD_PROJECT={vtx_proj if vtx_proj!='not set' else 'your-project-id'} in .env"),
        (gemini_ok, "Gemini",      "Steps 0–3, 6–9", "GEMINI_API_KEY",
         "API key configured", "Add GEMINI_API_KEY=your_key to .env — free at aistudio.google.com"),
        (groq_ok,   "Groq",        "3rd fallback",   "GROQ_API_KEY",
         "API key configured", "Add GROQ_API_KEY=your_key to .env — free at console.groq.com"),
        (claude_ok, "Claude",      "4th fallback",   "ANTHROPIC_API_KEY",
         "API key configured", "Add ANTHROPIC_API_KEY=your_key to .env"),
    ]

    sc1, sc2 = st.columns(2, gap="medium")
    for i, (ok_fn, name, steps, env_var, note_ok, note_fail) in enumerate(prov_data):
        ok   = ok_fn()
        dot  = "var(--success)" if ok else "var(--warn)"
        note = note_ok if ok else note_fail
        status_lbl = "Configured" if ok else "Not configured"
        status_col = "var(--success)" if ok else "var(--warn)"
        col = sc1 if i % 2 == 0 else sc2
        with col:
            st.markdown(f"""
<div class="prov-card" style="margin-bottom:10px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
    <span style="width:9px;height:9px;border-radius:50%;background:{dot};display:inline-block;flex-shrink:0;"></span>
    <span style="font-weight:500;font-size:14px;color:var(--text);">{name}</span>
    <span class="chip chip-n" style="font-size:10px;margin-left:auto;">{steps}</span>
    <span style="font-size:11px;color:{status_col};font-weight:500;">{status_lbl}</span>
  </div>
  <div style="font-size:13px;color:var(--muted);margin-bottom:6px;line-height:1.5;">{note}</div>
  <div style="font-size:11px;color:var(--muted2);font-family:var(--mono);background:var(--bg3);padding:4px 8px;border-radius:4px;border:1px solid var(--border);">{env_var}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Capabilities in expander ──
    with st.expander("Pipeline capabilities — V21 · click to expand"):
        caps = [
            ("10-step pipeline",     False, "Steps 0–9 · Gemini 2.5 Pro + Vertex AI + Groq + Claude"),
            ("9 bias dimensions",    False, "Gender, age, race, geo, name, disability, language, insurance, socioeconomic"),
            ("Disability detection", False, "Dedicated 9th dimension with CRPD citation"),
            ("Intersectional bias",  False, "Compound characteristic analysis — Step 4"),
            ("International law",    False, "CRPD, ECHR, EU AI Act, CEDAW — Step 3"),
            ("Risk scoring",         False, "Composite index 0–100 with rules engine — Step 6"),
            ("Auto-appeal letter",   False, "Formal letter when risk ≥ 40 — Step 7"),
            ("Legal timeline",       True,  "Filing deadlines + jurisdiction + pro-bono — Step 8"),
            ("Case-law precedents",  True,  "Real case matches + win probability — Step 9"),
            ("4-tier fallback",      True,  "Vertex → Gemini → Groq → Claude"),
            ("Batch audit 50 rows",  True,  "Full pipeline on each decision"),
            ("Duplicate detection",  False, "SHA-256 hash cache skips repeat text"),
        ]
        for name, is_v21, desc in caps:
            nc    = "color:var(--violet);" if is_v21 else ""
            badge = '<span class="chip chip-v" style="font-size:9px;padding:1px 5px;margin-left:6px;">New</span>' if is_v21 else ""
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--border);font-size:13px;">'                f'<span style="font-weight:500;{nc}">{name}{badge}</span>'                f'<span style="font-size:12px;color:var(--muted2);max-width:none;">{desc}</span></div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Config tip
    st.markdown("""
<div class="card" style="border-color:rgba(79,142,247,.2);">
  <div class="clbl">Tip — for best button colors</div>
  <div style="font-size:13px;color:var(--muted);margin-bottom:8px;line-height:1.6;">
    Place a <code style="font-family:var(--mono);color:var(--accent);font-size:12px;">.streamlit/config.toml</code> file next to your app with:
  </div>
  <pre style="font-family:var(--mono);font-size:12px;color:var(--muted);background:var(--bg3);padding:10px 14px;border-radius:var(--radius);margin:0;">[theme]
base = "dark"
primaryColor = "#4f8ef7"
backgroundColor = "#0e0e0f"
secondaryBackgroundColor = "#161618"
textColor = "#e2e2e5"</pre>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div style="font-size:11px;color:var(--muted2);line-height:1.6;margin-top:12px;">Verdict Watch · Not legal advice · Built for educational awareness and AI governance research.</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)