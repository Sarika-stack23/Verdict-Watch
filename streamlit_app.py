"""
streamlit_app.py — Verdict Watch V2
Complete UI + Feature overhaul. Backend unchanged.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import httpx
import plotly.graph_objects as go
import pandas as pd
import re
from datetime import datetime
from collections import Counter

API_BASE = "http://localhost:8000"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch V2",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# DESIGN SYSTEM — CSS
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

/* Tabs */
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
    padding: 8px 18px;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: #080b12 !important;
    font-weight: 700;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.5rem; }

/* Buttons */
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

/* Inputs */
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

/* Metrics */
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

/* Custom components */
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
.vw-v2-badge {
    display: inline-block;
    background: var(--accent);
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

.info-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.5rem;
}
.info-card.red   { border-left: 3px solid var(--red); }
.info-card.green { border-left: 3px solid var(--green); }
.info-card.amber { border-left: 3px solid var(--amber); }
.info-card.blue  { border-left: 3px solid var(--blue); }
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
.chip-red    { background: var(--red-dim);   color: #ff9090; border: 1px solid rgba(255,77,77,0.3); }
.chip-green  { background: var(--green-dim); color: #80ffd0; border: 1px solid rgba(77,255,176,0.3); }
.chip-blue   { background: var(--blue-dim);  color: #80c4ff; border: 1px solid rgba(77,159,255,0.3); }
.chip-amber  { background: var(--amber-dim); color: #ffd480; border: 1px solid rgba(255,184,77,0.3); }
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

.api-pill-ok {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--green-dim);
    border: 1px solid rgba(77,255,176,0.3);
    color: var(--green);
    border-radius: 999px;
    padding: 4px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 1px;
}
.api-pill-err {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--red-dim);
    border: 1px solid rgba(255,77,77,0.3);
    color: var(--red);
    border-radius: 999px;
    padding: 4px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 1px;
}

.how-step {
    display: flex;
    gap: 0.8rem;
    align-items: flex-start;
    margin-bottom: 0.7rem;
}
.how-num { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: var(--accent); min-width: 18px; padding-top: 2px; }
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
    "job": "💼 Job Application",
    "loan": "🏦 Bank Loan",
    "medical": "🏥 Medical / Triage",
    "university": "🎓 University Admission",
    "other": "📄 Other",
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

CHIP_STYLES = ["chip-red", "chip-amber", "chip-blue", "chip-green"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

@st.cache_data(ttl=10)
def check_api_health() -> bool:
    try:
        with httpx.Client(timeout=5.0) as c:
            return c.get(f"{API_BASE}/api/health").status_code == 200
    except Exception:
        return False


def call_api(endpoint, method="GET", payload=None):
    try:
        with httpx.Client(timeout=90.0) as c:
            r = c.post(f"{API_BASE}{endpoint}", json=payload) if method == "POST" \
                else c.get(f"{API_BASE}{endpoint}")
            r.raise_for_status()
            return r.json(), None
    except httpx.ConnectError:
        return None, "api_down"
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return None, str(e)


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
                {"range": [0, 33],   "color": "rgba(77,255,176,0.05)"},
                {"range": [33, 66],  "color": "rgba(255,184,77,0.05)"},
                {"range": [66, 100], "color": "rgba(255,77,77,0.05)"},
            ],
            "threshold": {"line": {"color": color, "width": 2.5},
                          "thickness": 0.7, "value": value * 100},
        },
    ))
    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Syne"},
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
        text=list(values), textfont=dict(family="DM Mono", size=11, color="#eef0f8"),
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
        hovertemplate="~%{x:.0f}%: %{y} analyses<extra></extra>",
    ))
    fig.update_layout(
        height=220, margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title=dict(text="Confidence %", font=dict(family="DM Mono", size=10, color="#4a5268")),
                   tickfont=dict(family="DM Mono", size=10, color="#4a5268"),
                   gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(tickfont=dict(family="DM Mono", size=10, color="#4a5268"),
                   gridcolor="rgba(255,255,255,0.04)"),
    )
    return fig


def timeline_chart(dates, bias_flags):
    if not dates:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(dates))),
        y=[1 if b else 0 for b in bias_flags],
        mode="markers+lines",
        marker=dict(color=["#ff4d4d" if b else "#4dffb0" for b in bias_flags],
                    size=10, line=dict(color="#080b12", width=2)),
        line=dict(color="rgba(255,255,255,0.07)", width=1.5),
        hovertemplate="#%{x}<br>%{text}<extra></extra>",
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


def build_txt_report(report, text, dtype):
    recs = report.get("recommendations", [])
    lines = [
        "=" * 64, "      VERDICT WATCH V2 — BIAS ANALYSIS REPORT", "=" * 64,
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
        "── EXPLANATION (PLAIN ENGLISH) ─────────────────────────────",
        report.get("explanation", "N/A"), "",
        "── YOUR NEXT STEPS ─────────────────────────────────────────",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    lines += ["", "=" * 64,
              "  Verdict Watch V2  ·  Groq / Llama 3.3 70B  ·  Not legal advice",
              "=" * 64]
    return "\n".join(lines)


def build_compare_txt(r1, r2, t1, t2):
    def fmt(r, t, lbl):
        return [f"── Decision {lbl} ──────────────────────────────────────────",
                f"Text    : {t[:120]}...",
                f"Verdict : {'BIAS DETECTED' if r.get('bias_found') else 'NO BIAS FOUND'}",
                f"Confidence: {int(r.get('confidence_score', 0) * 100)}%",
                f"Bias Types: {', '.join(r.get('bias_types', [])) or 'None'}",
                f"Fair Outcome: {r.get('fair_outcome', 'N/A')}", ""]
    lines = ["=" * 64, "  VERDICT WATCH V2 — COMPARISON REPORT", "=" * 64,
             f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    lines += fmt(r1, t1, "A")
    lines += fmt(r2, t2, "B")
    lines += ["=" * 64, "  Not legal advice.", "=" * 64]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

api_ok = check_api_health()

with st.sidebar:
    st.markdown(
        '<div style="font-family:Syne,sans-serif; font-size:1.05rem; font-weight:700; color:#eef0f8;">'
        '⚖️ Verdict Watch <span style="background:#e8ff47; color:#080b12; font-family:DM Mono,monospace; '
        'font-size:0.55rem; padding:2px 6px; border-radius:3px; letter-spacing:1px; '
        'vertical-align:middle; position:relative; top:-2px;">V2</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-family:DM Sans,sans-serif; font-size:0.78rem; color:#4a5268; '
        'margin-bottom:1rem; line-height:1.5; margin-top:0.3rem;">'
        'AI-powered bias detection for automated decisions.</div>',
        unsafe_allow_html=True,
    )

    if api_ok:
        st.markdown('<div class="api-pill-ok">● API ONLINE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="api-pill-err">● API OFFLINE</div>', unsafe_allow_html=True)
        st.code("uvicorn api:app --reload", language="bash")

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
    steps = [
        ("01", "Paste any rejection or denial letter"),
        ("02", "AI extracts the criteria used"),
        ("03", "Scans for 7+ bias patterns"),
        ("04", "Generates what was fair"),
        ("05", "Shows actionable next steps"),
    ]
    for n, t in steps:
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
    '<span class="vw-v2-badge">V2</span></div>'
    '<div class="vw-tagline">AI-powered bias detection for automated decisions</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab_analyse, tab_dashboard, tab_history, tab_compare, tab_about = st.tabs([
    "⚡ Analyse", "📊 Dashboard", "📋 History", "⚖️ Compare", "ℹ About",
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
            type_opts = ["job", "loan", "medical", "university", "other"]
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
        elif not api_ok:
            st.error("❌ API offline. Run: `uvicorn api:app --reload`")
        else:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            with st.status("Running 3-step AI analysis...", expanded=True) as status_box:
                st.write("🔍 Step 1 — Extracting decision criteria...")
                report, err = call_api("/api/analyse", "POST",
                                       {"decision_text": decision_text,
                                        "decision_type": decision_type})
                st.write("🧠 Step 2 — Detecting bias patterns...")
                st.write("⚖️ Step 3 — Generating fair outcome...")
                status_box.update(
                    label="Analysis failed" if err else "Analysis complete ✓",
                    state="error" if err else "complete",
                )

            if err:
                st.error("❌ API went offline. Restart uvicorn." if err == "api_down"
                         else f"❌ {err}")
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
                r1, r2, r3 = st.columns([1.2, 1.4, 1.4])

                with r1:
                    st.markdown('<div class="sec-label">Confidence Score</div>', unsafe_allow_html=True)
                    st.plotly_chart(gauge_chart(confidence, bias_found),
                                    use_container_width=True, config={"displayModeBar": False})

                with r2:
                    st.markdown('<div class="sec-label">Bias Types Found</div>', unsafe_allow_html=True)
                    st.markdown(chips_html(bias_types, "auto") if bias_types
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

                with r3:
                    st.markdown(
                        f'<div class="info-card red" style="margin-bottom:0.6rem;">'
                        f'<div class="ic-label">Original Decision</div>'
                        f'<div class="ic-value mono">{orig.upper()}</div></div>'
                        f'<div class="info-card green">'
                        f'<div class="ic-label">Should Have Been</div>'
                        f'<div class="ic-value">{fair}</div></div>',
                        unsafe_allow_html=True,
                    )

                # ── Bias Phrase Highlighter (V2 new feature)
                if bias_types and decision_text.strip():
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(
                        '<div class="sec-label">🔍 Bias Phrase Highlighter — New in V2</div>',
                        unsafe_allow_html=True,
                    )
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

                # ── Download
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Full Report (.txt)",
                        data=build_txt_report(report, decision_text, decision_type),
                        file_name=f"verdict_watch_{report.get('id','report')[:8]}.txt",
                        mime="text/plain",
                    )

                st.session_state["last_report"] = report
                st.session_state["last_text"] = decision_text


# ═══════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ═══════════════════════════════════════════════

with tab_dashboard:
    if not api_ok:
        st.warning("⚠️ API offline. Start the server to see analytics.")
    else:
        hist, _ = call_api("/api/reports")
        hist = hist or []

        bias_reps  = [r for r in hist if r.get("bias_found")]
        clean_reps = [r for r in hist if not r.get("bias_found")]
        all_types  = [bt for r in hist for bt in r.get("bias_types", [])]
        scores     = [r.get("confidence_score", 0) for r in hist]
        dates      = [r.get("created_at") for r in hist if r.get("created_at")]
        bflags     = [r.get("bias_found", False) for r in hist if r.get("created_at")]
        bias_rate  = (len(bias_reps) / len(hist) * 100) if hist else 0
        avg_conf   = (sum(scores) / len(scores) * 100) if scores else 0
        top_bias   = Counter(all_types).most_common(1)[0][0] if all_types else "N/A"

        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Analyses", len(hist))
        m2.metric("Bias Rate", f"{bias_rate:.0f}%")
        m3.metric("Avg Confidence", f"{avg_conf:.0f}%")
        m4.metric("Top Bias Type", top_bias)

        st.markdown("<br>", unsafe_allow_html=True)

        # Charts row 1
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
                st.info("Run analyses to populate this chart.")

        # Charts row 2
        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="sec-label">Confidence Distribution</div>',
                        unsafe_allow_html=True)
            if scores:
                st.plotly_chart(histogram_chart(scores),
                                use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No data yet.")
        with c4:
            st.markdown('<div class="sec-label">Analysis Timeline</div>',
                        unsafe_allow_html=True)
            if dates:
                st.plotly_chart(timeline_chart(dates, bflags),
                                use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No data yet.")

        # Characteristics table
        if hist:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">Affected Characteristics</div>',
                        unsafe_allow_html=True)
            chars = [r.get("affected_characteristic") for r in hist
                     if r.get("affected_characteristic")]
            if chars:
                cdf = pd.DataFrame(
                    [{"Characteristic": k, "Count": v,
                      "% of Analyses": f"{v/len(hist)*100:.0f}%"}
                     for k, v in Counter(chars).most_common()]
                )
                st.dataframe(cdf, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════
# TAB 3 — HISTORY
# ═══════════════════════════════════════════════

with tab_history:
    if not api_ok:
        st.warning("⚠️ API offline.")
    else:
        hist, _ = call_api("/api/reports")
        hist = hist or []

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
                    "sort", ["Newest First", "Oldest First",
                             "Highest Confidence", "Lowest Confidence"],
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

            st.markdown(
                f'<div style="font-family:DM Mono,monospace; font-size:0.68rem; '
                f'color:#4a5268; margin-bottom:1rem; letter-spacing:1px;">'
                f'SHOWING {len(filtered)} OF {len(hist)}</div>',
                unsafe_allow_html=True,
            )

            for r in filtered:
                bias    = r.get("bias_found", False)
                conf    = int(r.get("confidence_score", 0) * 100)
                affected = r.get("affected_characteristic") or "—"
                b_types = r.get("bias_types", [])
                created = (r.get("created_at") or "")[:16].replace("T", " ")

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
                            f'<div class="ic-value">{chips_html(b_types, "auto") if b_types else "None"}</div></div>'
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
# TAB 4 — COMPARE  (New in V2)
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
        cmp_type1 = st.selectbox("Type A", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type1")
    with cc2:
        st.markdown('<div class="compare-header">Decision B</div>', unsafe_allow_html=True)
        cmp_text2 = st.text_area("Text B", height=150, label_visibility="collapsed",
                                  placeholder="Paste second decision here...", key="cmp2")
        cmp_type2 = st.selectbox("Type B", ["job","loan","medical","university","other"],
                                  format_func=lambda x: TYPE_LABELS[x],
                                  label_visibility="collapsed", key="cmp_type2")

    cmp_btn = st.button("⚡ Compare Both Decisions", key="compare_btn")

    if cmp_btn:
        if not cmp_text1.strip() or not cmp_text2.strip():
            st.warning("⚠️ Paste text for both Decision A and B.")
        elif not api_ok:
            st.error("❌ API offline.")
        else:
            with st.status("Analysing both decisions...", expanded=True) as cs:
                st.write("🔍 Analysing Decision A...")
                r1, e1 = call_api("/api/analyse", "POST",
                                   {"decision_text": cmp_text1, "decision_type": cmp_type1})
                st.write("🔍 Analysing Decision B...")
                r2, e2 = call_api("/api/analyse", "POST",
                                   {"decision_text": cmp_text2, "decision_type": cmp_type2})
                cs.update(label="Comparison complete ✓" if not e1 and not e2
                          else "One or more failed", state="complete" if not e1 and not e2 else "error")

            if e1: st.error(f"Decision A: {e1}")
            if e2: st.error(f"Decision B: {e2}")

            if r1 and r2:
                st.markdown('<hr class="divider">', unsafe_allow_html=True)
                v1, v2 = st.columns(2)

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
                        st.plotly_chart(gauge_chart(conf, bias),
                                        use_container_width=True, config={"displayModeBar": False})
                        st.markdown(chips_html(r.get("bias_types", []), "auto"),
                                    unsafe_allow_html=True)
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

                # Summary
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="sec-label">Comparison Summary</div>',
                            unsafe_allow_html=True)
                b1, b2 = r1.get("bias_found"), r2.get("bias_found")
                c1v, c2v = r1.get("confidence_score", 0), r2.get("confidence_score", 0)
                if b1 and b2:
                    winner = "A" if c1v >= c2v else "B"
                    summary = (f"Both decisions show bias. Decision {winner} has higher "
                               f"confidence ({int(max(c1v, c2v)*100)}%).")
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

                st.markdown("<br>", unsafe_allow_html=True)
                dl1, _ = st.columns([1, 2])
                with dl1:
                    st.download_button(
                        "📥 Download Comparison Report (.txt)",
                        data=build_compare_txt(r1, r2, cmp_text1, cmp_text2),
                        file_name=f"verdict_compare_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                    )


# ═══════════════════════════════════════════════
# TAB 5 — ABOUT
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
            ("Gender Bias", "Decisions influenced by gender, name, or parental status"),
            ("Age Discrimination", "Unfair weighting of age group or seniority proxies"),
            ("Racial / Ethnic Bias", "Name-based or origin-based ethnic profiling"),
            ("Geographic Redlining", "Residential area or zip code used as a proxy"),
            ("Socioeconomic Bias", "Employment sector or credit history weighting"),
            ("Language Discrimination", "Primary language used against applicants"),
            ("Insurance / Class Bias", "Insurance tier used to rank medical priority"),
        ]
        for name, desc in bias_info:
            st.markdown(
                f'<div class="info-card blue" style="margin-bottom:0.5rem;">'
                f'<div class="ic-label">{name}</div>'
                f'<div class="ic-value" style="font-size:0.87rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

    with ab2:
        st.markdown('<div class="sec-label">V2 New Features</div>',
                    unsafe_allow_html=True)
        v2_feats = [
            ("📊", "Analytics Dashboard", "Live charts of all analyses"),
            ("🔍", "Bias Phrase Highlighter", "Marks suspicious words in your text"),
            ("⚖️", "Decision Comparator", "Side-by-side analysis of two decisions"),
            ("📋", "Filterable History", "Search, sort, and filter past analyses"),
            ("🎯", "Confidence Gauge", "Visual circular confidence meter"),
            ("🏷️", "Colour-coded Chips", "Smart bias type labelling"),
            ("📥", "Richer Reports", "Improved downloadable .txt reports"),
            ("🖥️", "Full UI Redesign", "New Syne + DM Sans design system"),
        ]
        for icon, name, desc in v2_feats:
            st.markdown(
                f'<div class="info-card" style="margin-bottom:0.5rem;">'
                f'<div class="ic-label">{icon} {name}</div>'
                f'<div class="ic-value" style="font-size:0.87rem;">{desc}</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Tech Stack</div>', unsafe_allow_html=True)
        stack = [
            ("⚡ Groq", "LLM inference"),
            ("🦙 Llama 3.3 70B", "Language model"),
            ("🚀 FastAPI", "REST API backend"),
            ("🎈 Streamlit", "Frontend UI"),
            ("🗄️ SQLite", "Database"),
            ("📊 Plotly", "Interactive charts"),
        ]
        for name, desc in stack:
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
    'Verdict Watch V2  ·  Powered by Groq / Llama 3.3 70B  ·  Not Legal Advice'
    '</div>',
    unsafe_allow_html=True,
)