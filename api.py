"""
api.py — Verdict Watch V11
FastAPI REST API.

Run with: uvicorn api:app --reload --port 8000

V11 changes:
  - /api/analyse accepts scan_mode = "full" | "quick"
  - /api/appeal endpoint (was in streamlit_app.py)
  - /api/reports/{id}/feedback endpoint
  - /api/trend  — daily trend data for dashboard
  - /api/confidence-trend — sparkline data
  - Cleaner Pydantic models with Optional fields
  - Proper 422 validation errors
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal
import services

services.init_db()

app = FastAPI(
    title="Verdict Watch API",
    description="AI-powered bias detection for automated decisions — V11",
    version="11.0.0",
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
    decision_text: str = Field(..., min_length=30, description="The automated decision text to analyse")
    decision_type: Literal["job", "loan", "medical", "university", "other"] = "other"
    scan_mode:     Literal["full", "quick"] = "full"


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
    bias_phrases:            list[str]           = []
    legal_frameworks:        list[str]           = []
    fair_reasoning:          Optional[str]       = ""
    severity:                Optional[str]       = "low"
    bias_evidence:           Optional[str]       = ""
    timing_ms:               Optional[dict]      = {}
    retry_counts:            Optional[dict]      = {}
    mode:                    Optional[str]       = "full"


class AppealRequest(BaseModel):
    report_id:     str
    decision_text: str
    decision_type: str = "other"


class FeedbackRequest(BaseModel):
    rating:  int   = Field(..., ge=0, le=1)
    comment: str   = ""


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
            )
        else:
            report = services.run_full_pipeline(
                decision_text=payload.decision_text,
                decision_type=payload.decision_type,
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
        reports = services.get_all_reports()
        return reports[:limit]
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

    groq_status = "key_present" if services.os.getenv("GROQ_API_KEY") else "key_missing"

    return {
        "status":   "ok",
        "database": db_status,
        "groq":     groq_status,
        "model":    services._MODEL,
        "version":  "11.0.0",
    }