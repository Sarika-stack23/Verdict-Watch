"""
streamlit_app.py — Verdict Watch
Full Streamlit UI — improved version.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import httpx
from datetime import datetime

API_BASE = "http://localhost:8000"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Verdict Watch",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    .vw-title {
        font-size: 3.8rem;
        font-weight: 700;
        letter-spacing: -2px;
        line-height: 1;
        background: linear-gradient(135deg, #ffffff 0%, #a78bfa 60%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .vw-subtitle {
        font-size: 1.05rem;
        color: #8888aa;
        margin-top: 0.4rem;
        font-weight: 300;
    }

    .banner-bias {
        background: linear-gradient(135deg, #7f1d1d, #991b1b);
        border: 1px solid #ef4444;
        color: #fecaca;
        font-size: 1.6rem;
        font-weight: 700;
        padding: 1.2rem 2rem;
        border-radius: 14px;
        text-align: center;
        letter-spacing: 1px;
        box-shadow: 0 0 30px rgba(239,68,68,0.25);
    }

    .banner-clean {
        background: linear-gradient(135deg, #052e16, #14532d);
        border: 1px solid #22c55e;
        color: #bbf7d0;
        font-size: 1.6rem;
        font-weight: 700;
        padding: 1.2rem 2rem;
        border-radius: 14px;
        text-align: center;
        letter-spacing: 1px;
        box-shadow: 0 0 30px rgba(34,197,94,0.2);
    }

    .card {
        background: #13131f;
        border: 1px solid #2a2a3f;
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
    }
    .card-orig    { border-left: 4px solid #f87171; }
    .card-fair    { border-left: 4px solid #4ade80; }
    .card-explain { border-left: 4px solid #fbbf24; }

    .card-label {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #6666aa;
        margin-bottom: 0.6rem;
    }

    .card-value {
        font-size: 1.05rem;
        color: #ddddf0;
        line-height: 1.6;
    }

    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 3px 3px 3px 0;
    }
    .badge-red    { background: #3f1010; color: #fca5a5; border: 1px solid #7f2020; }
    .badge-purple { background: #1e1030; color: #c4b5fd; border: 1px solid #5b3fa0; }
    .badge-blue   { background: #0c1a30; color: #93c5fd; border: 1px solid #1e3a6e; }
    .badge-amber  { background: #1c1200; color: #fcd34d; border: 1px solid #78540a; }

    .rec {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
        background: #13131f;
        border: 1px solid #2a2a3f;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
    }
    .rec-num {
        background: #a78bfa;
        color: #0a0a0f;
        border-radius: 50%;
        min-width: 26px;
        height: 26px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .rec-text { color: #cccce0; font-size: 0.95rem; line-height: 1.5; }

    .sec-head {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #6666aa;
        margin-bottom: 0.5rem;
    }

    .div { border: none; border-top: 1px solid #1e1e30; margin: 2rem 0; }

    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #4f46e5);
        color: white;
        border: none;
        border-radius: 10px;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.65rem 1.8rem;
        width: 100%;
        letter-spacing: 0.3px;
    }
    .stButton > button:hover { opacity: 0.85; }

    .footer {
        text-align: center;
        color: #3a3a5a;
        font-size: 0.78rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #1a1a2e;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# EXAMPLE TEXTS
# ─────────────────────────────────────────────

EXAMPLES = [
    {
        "tag": "Job",
        "type": "job",
        "text": (
            "Thank you for applying to the Software Engineer position. "
            "After careful review we have decided not to move forward. "
            "We felt other candidates were a stronger fit for our team culture at this time."
        ),
    },
    {
        "tag": "Loan",
        "type": "loan",
        "text": (
            "Your loan application has been declined. Primary reasons: insufficient credit history, "
            "residential area risk score, employment sector classification. "
            "You may reapply after 6 months."
        ),
    },
    {
        "tag": "Medical",
        "type": "medical",
        "text": (
            "Based on your intake assessment you have been assigned Priority Level 3. "
            "Factors considered: age group, reported pain level, primary language, insurance classification."
        ),
    },
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def call_api(endpoint: str, method: str = "GET", payload: dict = None):
    try:
        with httpx.Client(timeout=90.0) as client:
            if method == "POST":
                r = client.post(f"{API_BASE}{endpoint}", json=payload)
            else:
                r = client.get(f"{API_BASE}{endpoint}")
            r.raise_for_status()
            return r.json(), None
    except httpx.ConnectError:
        return None, "api_down"
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return None, str(e)


def check_api_health() -> bool:
    data, err = call_api("/api/health")
    return err is None


BADGE_COLORS = ["badge-red", "badge-purple", "badge-blue", "badge-amber"]

def badges_html(items: list) -> str:
    html = ""
    for i, item in enumerate(items):
        cls = BADGE_COLORS[i % len(BADGE_COLORS)]
        html += f'<span class="badge {cls}">{item}</span>'
    return html


def build_txt_report(report: dict, text: str, dtype: str) -> str:
    lines = [
        "=" * 62,
        "         VERDICT WATCH — BIAS ANALYSIS REPORT",
        "=" * 62,
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Type      : {dtype.upper()}",
        f"Report ID : {report.get('id', 'N/A')}",
        "",
        "── ORIGINAL DECISION TEXT ──────────────────────────────────",
        text,
        "",
        "── VERDICT ─────────────────────────────────────────────────",
        "BIAS DETECTED" if report.get("bias_found") else "NO BIAS FOUND",
        f"Confidence: {int(report.get('confidence_score', 0) * 100)}%",
        "",
        "── BIAS TYPES ──────────────────────────────────────────────",
        ", ".join(report.get("bias_types", [])) or "None detected",
        "",
        "── CHARACTERISTIC AFFECTED ─────────────────────────────────",
        report.get("affected_characteristic", "N/A"),
        "",
        "── ORIGINAL OUTCOME ────────────────────────────────────────",
        report.get("original_outcome", "N/A"),
        "",
        "── FAIR OUTCOME ────────────────────────────────────────────",
        report.get("fair_outcome", "N/A"),
        "",
        "── EXPLANATION ─────────────────────────────────────────────",
        report.get("explanation", "N/A"),
        "",
        "── YOUR NEXT STEPS ─────────────────────────────────────────",
    ]
    for i, rec in enumerate(report.get("recommendations", []), 1):
        lines.append(f"  {i}. {rec}")
    lines += [
        "",
        "=" * 62,
        "  Verdict Watch v1.0 · Powered by Groq (Llama 3.3 70B)",
        "  Not legal advice.",
        "=" * 62,
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚖️ Verdict Watch")
    st.markdown(
        '<div style="color:#8888aa; font-size:0.85rem; margin-bottom:1rem;">'
        "AI-powered bias detection for automated decisions."
        "</div>",
        unsafe_allow_html=True,
    )

    api_ok = check_api_health()
    if api_ok:
        st.success("🟢 API connected")
    else:
        st.error("🔴 API offline")
        st.code("uvicorn api:app --reload", language="bash")

    st.markdown("---")
    st.markdown("**Try an example:**")

    for ex in EXAMPLES:
        if st.button(f"💡 {ex['tag']} Example", key=f"ex_{ex['type']}"):
            st.session_state["prefill_text"] = ex["text"]
            st.session_state["prefill_type"] = ex["type"]
            st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.8rem; color:#6666aa; line-height:1.8;">'
        "<b>How it works:</b><br>"
        "① Extract decision criteria<br>"
        "② Detect hidden bias<br>"
        "③ Generate fair outcome<br><br>"
        "Model: <b>Llama 3.3 70B</b> via Groq"
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────

st.markdown('<div class="vw-title">⚖️ Verdict Watch</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="vw-subtitle">Paste any automated decision — we\'ll tell you if bias caused it.</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION 1 — INPUT
# ─────────────────────────────────────────────

prefill_text = st.session_state.get("prefill_text", "")
prefill_type = st.session_state.get("prefill_type", "job")

col_form, _ = st.columns([3, 1])

with col_form:
    st.markdown('<div class="sec-head">Your Decision Letter</div>', unsafe_allow_html=True)

    decision_text = st.text_area(
        label="Decision letter",
        label_visibility="collapsed",
        value=prefill_text,
        placeholder=(
            "Paste the rejection letter, denial notice, triage result, or any "
            "automated decision you received here...\n\n"
            "Tip: Use the sidebar examples to try it instantly."
        ),
        height=200,
        key="decision_input",
    )

    st.markdown('<div class="sec-head" style="margin-top:1rem;">Decision Type</div>', unsafe_allow_html=True)

    type_options = ["job", "loan", "medical", "university", "other"]
    type_labels = {
        "job": "💼 Job Application",
        "loan": "🏦 Bank Loan",
        "medical": "🏥 Medical / Triage",
        "university": "🎓 University Admission",
        "other": "📄 Other",
    }
    default_idx = type_options.index(prefill_type) if prefill_type in type_options else 0

    decision_type = st.selectbox(
        label="Decision type",
        label_visibility="collapsed",
        options=type_options,
        format_func=lambda x: type_labels[x],
        index=default_idx,
        key="decision_type",
    )

    analyse_btn = st.button("🔍 Analyse This Decision", key="analyse_btn")


# ─────────────────────────────────────────────
# SECTION 2 — RESULTS
# ─────────────────────────────────────────────

if analyse_btn:
    st.session_state.pop("prefill_text", None)
    st.session_state.pop("prefill_type", None)

    if not decision_text.strip():
        st.warning("⚠️ Please paste a decision text first.")
    elif not api_ok:
        st.error("❌ API is offline. Start it with: `uvicorn api:app --reload`")
    else:
        st.markdown('<hr class="div">', unsafe_allow_html=True)

        prog = st.progress(0)
        status = st.empty()

        status.info("⚙️ Step 1/3 — Extracting decision criteria...")
        prog.progress(20)

        report, err = call_api(
            "/api/analyse",
            method="POST",
            payload={"decision_text": decision_text, "decision_type": decision_type},
        )

        prog.progress(70)
        status.info("⚙️ Step 2/3 — Detecting bias patterns...")
        prog.progress(90)
        status.info("⚙️ Step 3/3 — Generating fair outcome...")
        prog.progress(100)

        status.empty()
        prog.empty()

        if err:
            if err == "api_down":
                st.error("❌ API went offline during analysis. Restart uvicorn and try again.")
            else:
                st.error(f"❌ Analysis failed: {err}")

        elif report:
            # Bias Banner
            if report.get("bias_found"):
                st.markdown('<div class="banner-bias">⚠️ BIAS DETECTED</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="banner-clean">✅ NO BIAS FOUND</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Confidence + Badges
            c1, c2 = st.columns([1, 2])
            with c1:
                conf = report.get("confidence_score", 0.0)
                st.markdown(f'<div class="sec-head">Confidence — {int(conf * 100)}%</div>', unsafe_allow_html=True)
                st.progress(conf)
            with c2:
                bias_types = report.get("bias_types", [])
                if bias_types:
                    st.markdown('<div class="sec-head">Bias Types</div>', unsafe_allow_html=True)
                    st.markdown(badges_html(bias_types), unsafe_allow_html=True)
                affected = report.get("affected_characteristic", "")
                if affected:
                    st.markdown(
                        f'<div style="margin-top:0.5rem; color:#6666aa; font-size:0.82rem;">'
                        f'Characteristic: <strong style="color:#a78bfa">{affected}</strong></div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # Original vs Fair
            oc, fc = st.columns(2)
            with oc:
                st.markdown(
                    f'<div class="card card-orig">'
                    f'<div class="card-label">Original Decision</div>'
                    f'<div class="card-value">{report.get("original_outcome", "N/A").upper()}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with fc:
                st.markdown(
                    f'<div class="card card-fair">'
                    f'<div class="card-label">Fair Decision Should Have Been</div>'
                    f'<div class="card-value">{report.get("fair_outcome", "N/A")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Explanation
            st.markdown(
                f'<div class="card card-explain">'
                f'<div class="card-label">What Happened — Plain English</div>'
                f'<div class="card-value">{report.get("explanation", "No explanation.")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Recommendations
            recs = report.get("recommendations", [])
            if recs:
                st.markdown('<div class="sec-head" style="margin-top:0.5rem;">Your Next Steps</div>', unsafe_allow_html=True)
                for i, rec in enumerate(recs, 1):
                    st.markdown(
                        f'<div class="rec"><div class="rec-num">{i}</div><div class="rec-text">{rec}</div></div>',
                        unsafe_allow_html=True,
                    )

            # Download
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                label="📥 Download Full Report (.txt)",
                data=build_txt_report(report, decision_text, decision_type),
                file_name=f"verdict_watch_{report.get('id', 'report')[:8]}.txt",
                mime="text/plain",
            )


# ─────────────────────────────────────────────
# SECTION 3 — PAST ANALYSES
# ─────────────────────────────────────────────

st.markdown('<hr class="div">', unsafe_allow_html=True)
st.markdown(
    '<div style="font-size:1.3rem; font-weight:700; margin-bottom:0.3rem;">📋 Past Analyses</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="vw-subtitle" style="font-size:0.85rem; margin-bottom:1rem;">All decisions analysed across sessions</div>',
    unsafe_allow_html=True,
)

if api_ok:
    history, _ = call_api("/api/reports")
    if history and len(history) > 0:
        rows = []
        for r in history:
            verdict = "⚠️ BIAS" if r.get("bias_found") else "✅ CLEAN"
            conf = f"{int(r.get('confidence_score', 0) * 100)}%"
            created = r.get("created_at", "")[:16].replace("T", " ") if r.get("created_at") else "—"
            rows.append({
                "Verdict": verdict,
                "Affected": r.get("affected_characteristic", "—") or "—",
                "Confidence": conf,
                "Date": created,
                "ID": r.get("id", "")[:8] + "...",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No analyses yet. Paste a decision above to get started.")
else:
    st.warning("Start the API server to see past analyses here.")


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.markdown(
    '<div class="footer">Verdict Watch v1.0 &nbsp;·&nbsp; Powered by Groq (Llama 3.3 70B) &nbsp;·&nbsp; Not legal advice</div>',
    unsafe_allow_html=True,
)