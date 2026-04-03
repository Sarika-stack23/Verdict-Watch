"""
api.py — Verdict Watch V15
FastAPI REST API — AI Governance Edition.

New V15 endpoints:
  GET  /api/fairness          — aggregate fairness metrics across all reports
  GET  /api/fairness/{id}     — fairness data for a single report
  POST /api/audit/batch       — run fairness audit on a list of decision texts
  GET  /api/governance/report — full AI governance summary (for pitch demo)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal
import services

services.init_db()

app = FastAPI(
    title="Verdict Watch API",
    description="AI Governance & Bias Detection — Gemini PRIMARY + Groq FALLBACK — V15",
    version="15.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    decision_text: str  = Field(..., min_length=30)
    decision_type: Literal["job", "loan", "medical", "university", "other"] = "other"
    scan_mode:     Literal["full", "quick"] = "full"
    ai_provider:   Literal["gemini", "groq", "auto"] = "gemini"


class AnalyseResponse(BaseModel):
    id:                      str
    analysis_id:             str
    bias_found:              bool
    bias_types:              list[str]
    affected_characteristic: Optional[str]
    original_outcome:        Optional[str]
    fair_outcome:            Optional[str]
    explanation:             Optional[str]
    confidence_score:        float
    recommendations:         list[str]
    created_at:              Optional[str]
    bias_phrases:            list[str]       = []
    legal_frameworks:        list[str]       = []
    fair_reasoning:          Optional[str]   = ""
    severity:                Optional[str]   = "low"
    bias_evidence:           Optional[str]   = ""
    timing_ms:               Optional[dict]  = {}
    retry_counts:            Optional[dict]  = {}
    mode:                    Optional[str]   = "full"
    ai_provider:             Optional[str]   = "gemini"
    fairness_scores:         Optional[dict]  = {}
    explainability_trace:    Optional[dict]  = {}
    characteristic_weights:  Optional[dict]  = {}


class AppealRequest(BaseModel):
    report_id:     str
    decision_text: str
    decision_type: str  = "other"
    ai_provider:   Literal["gemini", "groq", "auto"] = "gemini"


class FeedbackRequest(BaseModel):
    rating:  int  = Field(..., ge=0, le=1)
    comment: str  = ""


class BatchAuditRequest(BaseModel):
    decisions: list[str] = Field(..., min_length=1, max_length=10)
    decision_type: Literal["job", "loan", "medical", "university", "other"] = "other"
    ai_provider:   Literal["gemini", "groq", "auto"] = "gemini"


# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────

@app.post("/api/analyse", response_model=AnalyseResponse, tags=["Analysis"])
def analyse_decision(payload: AnalyseRequest):
    if not payload.decision_text.strip():
        raise HTTPException(status_code=400, detail="decision_text cannot be empty")
    try:
        if payload.scan_mode == "quick":
            report = services.quick_scan(
                decision_text=payload.decision_text,
                decision_type=payload.decision_type,
                provider=payload.ai_provider,
            )
        else:
            report = services.run_full_pipeline(
                decision_text=payload.decision_text,
                decision_type=payload.decision_type,
                provider=payload.ai_provider,
            )
        return report
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}")


# ─────────────────────────────────────────────
# APPEAL
# ─────────────────────────────────────────────

@app.post("/api/appeal", tags=["Analysis"])
def generate_appeal(payload: AppealRequest):
    report = services.get_report_by_id(payload.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        letter = services.generate_appeal_letter(
            report=report,
            decision_text=payload.decision_text,
            decision_type=payload.decision_type,
            provider=payload.ai_provider,
        )
        return {"letter": letter}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

@app.get("/api/reports", tags=["Reports"])
def list_reports(limit: int = Query(default=200, le=500)):
    try:
        return services.get_all_reports()[:limit]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/reports/{report_id}", response_model=AnalyseResponse, tags=["Reports"])
def get_report(report_id: str):
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/api/reports/{report_id}/feedback", tags=["Reports"])
def submit_feedback(report_id: str, payload: FeedbackRequest):
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    ok = services.save_feedback(report_id, payload.rating, payload.comment)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save feedback")
    return {"status": "saved"}


# ─────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────

@app.get("/api/trend", tags=["Analytics"])
def trend_data():
    try:
        return services.get_trend_data()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/confidence-trend", tags=["Analytics"])
def confidence_trend(n: int = Query(default=20, le=100)):
    try:
        return {"scores": services.get_confidence_trend(n)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────
# FAIRNESS & GOVERNANCE (NEW V15)
# ─────────────────────────────────────────────

@app.get("/api/fairness", tags=["Governance"])
def aggregate_fairness():
    """
    Aggregate fairness metrics across all stored reports.
    Returns the AI governance summary — demographic parity scores,
    fairness verdicts, characteristic influence weights.
    """
    try:
        reports = services.get_all_reports()
        return services.generate_model_bias_report(reports)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/fairness/{report_id}", tags=["Governance"])
def report_fairness(report_id: str):
    """Fairness audit data for a single report."""
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id":              report_id,
        "fairness_scores":        report.get("fairness_scores", {}),
        "explainability_trace":   report.get("explainability_trace", {}),
        "characteristic_weights": report.get("characteristic_weights", {}),
    }


@app.post("/api/audit/batch", tags=["Governance"])
def batch_fairness_audit(payload: BatchAuditRequest):
    """
    Run full pipeline on multiple decisions and return aggregate fairness report.
    Useful for auditing an organisation's historical decisions in bulk.
    """
    results = []
    errors  = []
    for i, text in enumerate(payload.decisions):
        try:
            report = services.run_full_pipeline(
                decision_text=text,
                decision_type=payload.decision_type,
                provider=payload.ai_provider,
            )
            results.append(report)
        except Exception as exc:
            errors.append({"index": i, "error": str(exc)})

    aggregate = services.generate_model_bias_report(results)
    return {
        "processed":  len(results),
        "errors":     len(errors),
        "error_list": errors,
        "aggregate":  aggregate,
        "reports":    results,
    }


@app.get("/api/governance/report", tags=["Governance"])
def governance_report():
    """
    Full AI governance summary for presentation / demo.
    Combines bias analytics, fairness metrics and provider stats.
    """
    try:
        reports  = services.get_all_reports()
        trend    = services.get_trend_data()
        fairness = services.generate_model_bias_report(reports)
        providers= services.check_providers()

        biased   = [r for r in reports if r.get("bias_found")]
        all_bt   = [bt for r in reports for bt in r.get("bias_types", [])]
        from collections import Counter
        top_bias = Counter(all_bt).most_common(5)

        return {
            "version":              "V15 — AI Governance Edition",
            "total_decisions":      len(reports),
            "bias_rate":            round(len(biased) / len(reports) * 100) if reports else 0,
            "top_bias_types":       [{"type": b, "count": c} for b, c in top_bias],
            "fairness_summary":     fairness,
            "trend":                trend,
            "providers_available":  providers,
            "pipeline_steps":       [
                "STEP 0 — Pre-decision characteristic scan",
                "STEP 1 — Decision criteria extraction",
                "STEP 2 — Bias pattern detection (7 dimensions)",
                "STEP 3 — Fair outcome generation + legal frameworks",
                "STEP 4 — Counterfactual fairness audit",
                "STEP 5 — Explainability trace (phrase-level)",
            ],
            "bias_dimensions": [
                "Gender", "Age", "Racial/Ethnic",
                "Geographic", "Socioeconomic", "Language", "Insurance",
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────
# PROVIDERS
# ─────────────────────────────────────────────

@app.get("/api/providers", tags=["Health"])
def provider_status():
    status = services.check_providers()
    return {
        "gemini": {"available": status["gemini"], "model": services._GEMINI_MODEL, "role": "primary"},
        "groq":   {"available": status["groq"],   "model": services._GROQ_MODEL,   "role": "fallback"},
    }


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
def health_check():
    db_status = "ok"
    try:
        db = services.get_db()
        db.query(services.Analysis).limit(1).all()
        db.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    providers = services.check_providers()

    return {
        "status":         "ok",
        "version":        "15.0.0",
        "database":       db_status,
        "gemini":         "key_present" if providers["gemini"] else "key_missing",
        "groq":           "key_present" if providers["groq"]   else "key_missing",
        "primary_model":  services._GEMINI_MODEL,
        "fallback_model": services._GROQ_MODEL,
        "pipeline_steps": 6,
        "governance_layer": True,
    }