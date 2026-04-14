"""
api.py — Verdict Watch V21
FastAPI REST API — 10-step AI Governance Edition.

New endpoints vs V20:
  GET  /api/timeline/{report_id}    — legal deadlines + jurisdiction (Step 8)
  GET  /api/precedents/{report_id}  — case-law matches (Step 9)
  GET  /api/governance/report       — updated to reference 10 steps + Claude provider

Batch limit raised to 50 rows.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal
import services

services.init_db()

app = FastAPI(
    title="Verdict Watch API",
    description=(
        "AI Governance & Bias Detection — V21 · 10-step pipeline · "
        "Vertex AI + Gemini 2.5 Pro + Groq + Claude fallback"
    ),
    version="21.0.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    decision_text: str  = Field(..., min_length=30)
    decision_type: Literal["job","loan","medical","university","other"] = "other"
    scan_mode:     Literal["full","quick"] = "full"
    ai_provider:   Literal["gemini","groq","auto"] = "gemini"


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
    bias_phrases:            list[str]     = []
    legal_frameworks:        list[str]     = []
    international_laws:      list[str]     = []
    fair_reasoning:          Optional[str] = ""
    severity:                Optional[str] = "low"
    bias_evidence:           Optional[str] = ""
    timing_ms:               Optional[dict] = {}
    retry_counts:            Optional[dict] = {}
    mode:                    Optional[str]  = "full"
    ai_provider:             Optional[str]  = "gemini"
    fairness_scores:         Optional[dict] = {}
    explainability_trace:    Optional[dict] = {}
    characteristic_weights:  Optional[dict] = {}
    # V20 fields
    risk_score:              Optional[int]  = 0
    urgency_tier:            Optional[str]  = "low"
    escalation_flag:         Optional[bool] = False
    appeal_letter:           Optional[str]  = None
    disability_bias:         Optional[bool] = False
    intersectional_bias:     Optional[dict] = {}
    severity_per_phrase:     Optional[list] = []
    # V21 fields
    legal_timeline:          Optional[dict] = {}
    precedents:              Optional[dict] = {}


class AppealRequest(BaseModel):
    report_id:     str
    decision_text: str
    decision_type: str = "other"
    ai_provider:   Literal["gemini","groq","auto"] = "gemini"


class FeedbackRequest(BaseModel):
    rating:  int = Field(..., ge=0, le=1)
    comment: str = ""


class BatchAuditRequest(BaseModel):
    decisions:     list[str] = Field(..., min_length=1, max_length=services.BATCH_MAX_ROWS)
    decision_type: Literal["job","loan","medical","university","other"] = "other"
    ai_provider:   Literal["gemini","groq","auto"] = "gemini"


class ExportPDFRequest(BaseModel):
    report_id: str


# ─────────────────────────────────────────────
# ANALYSIS
# ─────────────────────────────────────────────

@app.post("/api/analyse", response_model=AnalyseResponse, tags=["Analysis"])
def analyse_decision(payload: AnalyseRequest):
    if not payload.decision_text.strip():
        raise HTTPException(status_code=400, detail="decision_text cannot be empty")
    try:
        if payload.scan_mode == "quick":
            report = services.quick_scan(payload.decision_text, payload.decision_type, payload.ai_provider)
        else:
            report = services.run_full_pipeline(
                payload.decision_text, payload.decision_type, provider=payload.ai_provider
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
def generate_appeal_manual(payload: AppealRequest):
    report = services.get_report_by_id(payload.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        letter = services.generate_appeal_letter(
            report, payload.decision_text, payload.decision_type, payload.ai_provider
        )
        return {"letter": letter}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/appeal/{report_id}", tags=["Analysis"])
def get_appeal_letter(report_id: str):
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    letter = report.get("appeal_letter")
    if not letter:
        raise HTTPException(status_code=404, detail="No appeal letter. Re-run with full scan mode.")
    return {"report_id": report_id, "letter": letter}


# ─────────────────────────────────────────────
# V21: TIMELINE + PRECEDENTS
# ─────────────────────────────────────────────

@app.get("/api/timeline/{report_id}", tags=["V21"])
def get_legal_timeline(report_id: str):
    """V21: Legal deadlines, jurisdiction, and immediate actions for a report."""
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    timeline = report.get("legal_timeline", {})
    if not timeline:
        raise HTTPException(
            status_code=404,
            detail="No legal timeline for this report. Re-run with full scan mode.",
        )
    return {
        "report_id":  report_id,
        "timeline":   timeline,
        "bias_found": report.get("bias_found"),
        "urgency":    report.get("urgency_tier"),
    }


@app.get("/api/precedents/{report_id}", tags=["V21"])
def get_precedents(report_id: str):
    """V21: Relevant case-law precedents retrieved for a report."""
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    precedents = report.get("precedents", {})
    if not precedents:
        raise HTTPException(
            status_code=404,
            detail="No precedents for this report. Re-run with full scan mode.",
        )
    return {
        "report_id":         report_id,
        "precedents":        precedents.get("precedents", []),
        "strongest_precedent": precedents.get("strongest_precedent"),
        "legal_strategy_hint": precedents.get("legal_strategy_hint"),
        "estimated_win_probability": precedents.get("estimated_win_probability"),
    }


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


# ─────────────────────────────────────────────
# GOVERNANCE (V20 + V21 updates)
# ─────────────────────────────────────────────

@app.get("/api/risk/{report_id}", tags=["Governance"])
def get_risk_data(report_id: str):
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id":           report_id,
        "risk_score":          report.get("risk_score", 0),
        "urgency_tier":        report.get("urgency_tier", "low"),
        "escalation_flag":     report.get("escalation_flag", False),
        "disability_bias":     report.get("disability_bias", False),
        "intersectional_bias": report.get("intersectional_bias", {}),
        "severity_per_phrase": report.get("severity_per_phrase", []),
    }


@app.get("/api/escalations", tags=["Governance"])
def escalation_reports():
    try:
        return services.get_reports_by_escalation()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/disability", tags=["Governance"])
def disability_reports():
    try:
        return services.get_reports_by_disability()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/intersectional", tags=["Governance"])
def intersectional_reports():
    try:
        all_r = services.get_all_reports()
        return [
            r for r in all_r
            if isinstance(r.get("intersectional_bias"), dict)
            and r["intersectional_bias"].get("detected")
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/fairness", tags=["Governance"])
def aggregate_fairness():
    try:
        return services.get_model_bias_report()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/fairness/{report_id}", tags=["Governance"])
def report_fairness(report_id: str):
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id":             report_id,
        "fairness_scores":       report.get("fairness_scores", {}),
        "explainability_trace":  report.get("explainability_trace", {}),
        "characteristic_weights":report.get("characteristic_weights", {}),
        "risk_score":            report.get("risk_score", 0),
        "urgency_tier":          report.get("urgency_tier", "low"),
        "intersectional_bias":   report.get("intersectional_bias", {}),
        "international_laws":    report.get("international_laws", []),
        # V21
        "legal_timeline":        report.get("legal_timeline", {}),
        "precedents":            report.get("precedents", {}),
    }


@app.post("/api/audit/batch", tags=["Governance"])
def batch_fairness_audit(payload: BatchAuditRequest):
    """Batch audit — up to 50 decisions (V21). Runs full pipeline on each."""
    results = []
    errors  = []
    for i, text in enumerate(payload.decisions):
        try:
            results.append(
                services.run_full_pipeline(text, payload.decision_type, provider=payload.ai_provider)
            )
        except Exception as exc:
            errors.append({"index": i, "error": str(exc)})
    return {
        "processed":  len(results),
        "errors":     len(errors),
        "error_list": errors,
        "aggregate":  services.get_model_bias_report(),
        "reports":    results,
    }


@app.get("/api/governance/report", tags=["Governance"])
def governance_report():
    """V21: Full AI governance summary — 10 steps, all providers incl. Claude."""
    try:
        reports   = services.get_all_reports()
        fairness  = services.get_model_bias_report()
        providers = services.check_providers()
        return {
            "version":          "V21 — Google-Scale Hackathon Edition",
            "total_decisions":  len(reports),
            "bias_rate":        round(sum(1 for r in reports if r.get("bias_found")) / len(reports) * 100) if reports else 0,
            "escalated":        sum(1 for r in reports if r.get("escalation_flag")),
            "disability_cases": sum(1 for r in reports if r.get("disability_bias")),
            "fairness_summary": fairness,
            "providers":        providers,
            "vertex_enabled":   providers.get("vertex", False),
            "pipeline_steps": [
                "STEP 0 — Pre-decision scan · protected characteristics + disability (Gemini 2.5 Pro)",
                "STEP 1 — Criteria extraction (Gemini 2.0 Flash)",
                "STEP 2 — Bias detection · 9 dimensions incl. disability (Gemini 2.0 Flash)",
                "STEP 3 — Fair outcome + domestic + international law (Gemini 2.0 Flash)",
                "STEP 4 — Counterfactual fairness audit + intersectional bias (Vertex AI)",
                "STEP 5 — Explainability trace with severity_per_phrase (Vertex AI)",
                "STEP 6 — Risk scoring + rules engine · composite index 0–100 (Gemini Flash)",
                "STEP 7 — Auto-appeal letter · auto-runs when risk >= 40 (Gemini 2.5 Pro)",
                "STEP 8 — Legal timeline · deadlines + jurisdiction (Gemini 2.5 Pro) [V21]",
                "STEP 9 — Precedent retrieval · case-law match (Gemini 2.5 Pro) [V21]",
            ],
            "fallback_chain": [
                "Tier 1: Vertex AI (governance steps)",
                "Tier 2: Gemini (primary all steps)",
                "Tier 3: Groq llama-3.3-70b (fallback)",
                "Tier 4: Claude claude-3-5-sonnet (final fallback) [V21]",
            ],
            "batch_limit": services.BATCH_MAX_ROWS,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────
# PROVIDERS & HEALTH
# ─────────────────────────────────────────────

@app.get("/api/providers", tags=["Health"])
def provider_status():
    status = services.check_providers()
    return {
        "vertex": {
            "available": status["vertex"],
            "model":     services._VERTEX_MODEL,
            "role":      "governance (Steps 4+5)",
        },
        "gemini_pro": {
            "available": status["gemini"],
            "model":     services._GEMINI_PRO_MODEL,
            "role":      "high-stakes Steps 0, 7, 8, 9",
        },
        "gemini_flash": {
            "available": status["gemini"],
            "model":     services._GEMINI_FLASH_MODEL,
            "role":      "primary Steps 1–3, 6",
        },
        "groq": {
            "available": status["groq"],
            "model":     services._GROQ_MODEL,
            "role":      "3rd fallback all steps",
        },
        "claude": {
            "available": status["claude"],    # V21
            "model":     services._CLAUDE_MODEL,
            "role":      "4th fallback all steps [V21]",
        },
    }


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
        "status":                   "ok",
        "version":                  "21.0.0",
        "database":                 db_status,
        "vertex":                   "enabled"      if providers["vertex"] else "not_configured",
        "gemini":                   "key_present"  if providers["gemini"] else "key_missing",
        "groq":                     "key_present"  if providers["groq"]   else "key_missing",
        "claude":                   "key_present"  if providers["claude"] else "key_missing",
        "primary_pro_model":        services._GEMINI_PRO_MODEL,
        "primary_flash_model":      services._GEMINI_FLASH_MODEL,
        "governance_model":         services._VERTEX_MODEL,
        "fallback_model_3":         services._GROQ_MODEL,
        "fallback_model_4":         services._CLAUDE_MODEL,
        "pipeline_steps":           10,
        "governance_layer":         True,
        "vertex_ai":                True,
        "disability_detection":     True,
        "intersectional_bias":      True,
        "auto_appeal":              True,
        "risk_scoring":             True,
        "legal_timeline":           True,   # V21
        "precedent_retrieval":      True,   # V21
        "pdf_export":               True,
        "batch_limit":              services.BATCH_MAX_ROWS,
    }