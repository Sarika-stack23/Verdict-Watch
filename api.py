"""
api.py — Verdict Watch
FastAPI app with all endpoints.
Run with: uvicorn api:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import services

# ── Init DB on startup
services.init_db()

app = FastAPI(
    title="Verdict Watch API",
    description="AI-powered bias detection for automated decisions",
    version="1.0.0",
)

# ── Allow Streamlit frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    decision_text: str
    decision_type: str = "other"  # job / loan / medical / university / other


class AnalyseResponse(BaseModel):
    id: str
    analysis_id: str
    bias_found: bool
    bias_types: list[str]
    affected_characteristic: Optional[str]
    original_outcome: Optional[str]
    fair_outcome: Optional[str]
    explanation: Optional[str]
    confidence_score: float
    recommendations: list[str]
    created_at: Optional[str]


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/api/analyse", response_model=AnalyseResponse, tags=["Analysis"])
def analyse_decision(payload: AnalyseRequest):
    """
    Run the full 3-call Claude pipeline on a pasted decision text.
    Returns the complete bias report.
    """
    if not payload.decision_text.strip():
        raise HTTPException(status_code=400, detail="decision_text cannot be empty")

    try:
        report = services.run_full_pipeline(
            decision_text=payload.decision_text,
            decision_type=payload.decision_type,
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed: {str(e)}"
        )


@app.get("/api/reports", tags=["Reports"])
def list_reports():
    """Return all past bias reports, newest first."""
    try:
        return services.get_all_reports()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}", response_model=AnalyseResponse, tags=["Reports"])
def get_report(report_id: str):
    """Return a single report by ID."""
    report = services.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/health", tags=["Health"])
def health_check():
    """Check API and database status."""
    try:
        # Ping the DB by running a lightweight query
        db = services.get_db()
        db.execute(services.Analysis.__table__.select().limit(1))
        db.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "model": "llama-3.3-70b-versatile",
        "version": "1.0.0",
    }