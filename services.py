"""
services.py — Verdict Watch
Database models + all 3 Groq API calls + full pipeline
"""

import os
import json
import uuid
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Boolean, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from groq import Groq

load_dotenv()

# ─────────────────────────────────────────────
# DATABASE SETUP (SQLite — zero config)
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./verdict_watch.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_text = Column(Text, nullable=False)
    decision_type = Column(String, nullable=False)
    extracted_factors = Column(Text)          # JSON string
    submitted_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, nullable=False)
    bias_found = Column(Boolean, default=False)
    bias_types = Column(Text)                 # JSON list as string
    affected_characteristic = Column(String)
    original_outcome = Column(String)
    fair_outcome = Column(String)
    explanation = Column(Text)
    confidence_score = Column(Float, default=0.0)
    recommendations = Column(Text)            # JSON list as string
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


# ✅ FIXED: Removed pointless try/except that could never catch anything
def get_db() -> Session:
    return SessionLocal()


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────

def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env file")
    return Groq(api_key=api_key)


def call_groq(prompt: str, system: str) -> dict:
    """
    Single Groq call. Returns parsed JSON dict.
    Model: llama-3.3-70b-versatile (fast + free on Groq).
    """
    client = get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


# ─────────────────────────────────────────────
# GROQ CALL 1 — EXTRACT FACTORS
# ─────────────────────────────────────────────

def extract_factors(decision_text: str, decision_type: str) -> dict:
    """
    Call 1: Extract what criteria and factors were used in the decision.
    Returns JSON with keys:
      decision_type, outcome, criteria_used, data_points_weighted,
      protected_characteristics_mentioned
    """
    system = (
        "You are a decision analysis expert. "
        "Read the automated decision text the user provides and extract a JSON object. "
        "Return ONLY valid JSON with these exact keys: "
        "decision_type (string), outcome (accepted/rejected/approved/denied), "
        "criteria_used (list of strings), data_points_weighted (list of strings), "
        "protected_characteristics_mentioned (list of strings). "
        "Return ONLY valid JSON. No explanation. No markdown."
    )
    prompt = (
        f"Decision type hint: {decision_type}\n\n"
        f"Decision text:\n{decision_text}"
    )
    return call_groq(prompt, system)


# ─────────────────────────────────────────────
# GROQ CALL 2 — DETECT BIAS
# ─────────────────────────────────────────────

def detect_bias(extracted_factors: dict) -> dict:
    """
    Call 2: Analyse extracted factors for hidden bias.
    Returns JSON with keys:
      bias_detected (bool), bias_types (list), which_characteristic_affected (string),
      bias_evidence (string), confidence (float 0-1), severity (low/medium/high)
    """
    system = (
        "You are a fairness and bias expert. "
        "Analyse the extracted decision factors provided and detect any hidden bias "
        "against protected characteristics such as gender, age, race, geography, "
        "name-based ethnicity proxies, disability, or socioeconomic status. "
        "Return ONLY valid JSON with these exact keys: "
        "bias_detected (boolean), bias_types (list of strings), "
        "which_characteristic_affected (string), bias_evidence (string), "
        "confidence (float between 0 and 1), severity (low or medium or high). "
        "Return ONLY valid JSON. No explanation. No markdown."
    )
    prompt = f"Extracted decision factors:\n{json.dumps(extracted_factors, indent=2)}"
    return call_groq(prompt, system)


# ─────────────────────────────────────────────
# GROQ CALL 3 — GENERATE FAIR OUTCOME
# ─────────────────────────────────────────────

def generate_fair_outcome(extracted: dict, bias_result: dict) -> dict:
    """
    Call 3: Generate what the fair decision should have been.
    Returns JSON with keys:
      fair_outcome (string), fair_reasoning (string),
      what_was_wrong (string), next_steps (list of 3 strings)
    """
    system = (
        "You are a fair decision expert. "
        "Given the original decision outcome and evidence of bias, "
        "determine what the fair outcome should have been and explain it in plain English. "
        "Return ONLY valid JSON with these exact keys: "
        "fair_outcome (string), fair_reasoning (string), "
        "what_was_wrong (simple plain English string for the affected person), "
        "next_steps (list of exactly 3 strings — actionable steps the person can take). "
        "Return ONLY valid JSON. No explanation. No markdown."
    )
    prompt = (
        f"Original outcome: {extracted.get('outcome', 'unknown')}\n"
        f"Criteria used: {json.dumps(extracted.get('criteria_used', []))}\n"
        f"Bias evidence: {bias_result.get('bias_evidence', 'none')}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Characteristic affected: {bias_result.get('which_characteristic_affected', 'unknown')}"
    )
    return call_groq(prompt, system)


# ─────────────────────────────────────────────
# FULL PIPELINE — CHAINS ALL 3 CALLS + SAVES DB
# ─────────────────────────────────────────────

def run_full_pipeline(decision_text: str, decision_type: str) -> dict:
    """
    Runs the 3-call Groq pipeline, saves to DB, returns full report dict.
    """
    db: Session = get_db()
    try:
        # ── Call 1: Extract
        extracted = extract_factors(decision_text, decision_type)

        # ── Save Analysis row
        analysis = Analysis(
            raw_text=decision_text,
            decision_type=decision_type,
            extracted_factors=json.dumps(extracted),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # ── Call 2: Detect Bias
        bias_result = detect_bias(extracted)

        # ── Call 3: Fair Outcome
        fair_result = generate_fair_outcome(extracted, bias_result)

        # ── Save Report row
        report = Report(
            analysis_id=analysis.id,
            bias_found=bias_result.get("bias_detected", False),
            bias_types=json.dumps(bias_result.get("bias_types", [])),
            affected_characteristic=bias_result.get("which_characteristic_affected", ""),
            original_outcome=extracted.get("outcome", ""),
            fair_outcome=fair_result.get("fair_outcome", ""),
            explanation=fair_result.get("what_was_wrong", ""),
            confidence_score=float(bias_result.get("confidence", 0.0)),
            recommendations=json.dumps(fair_result.get("next_steps", [])),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        return build_report_dict(report)

    finally:
        db.close()


# ─────────────────────────────────────────────
# HELPERS — READ FROM DB
# ─────────────────────────────────────────────

def build_report_dict(report: Report) -> dict:
    return {
        "id": report.id,
        "analysis_id": report.analysis_id,
        "bias_found": report.bias_found,
        "bias_types": json.loads(report.bias_types or "[]"),
        "affected_characteristic": report.affected_characteristic,
        "original_outcome": report.original_outcome,
        "fair_outcome": report.fair_outcome,
        "explanation": report.explanation,
        "confidence_score": report.confidence_score,
        "recommendations": json.loads(report.recommendations or "[]"),
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def get_all_reports() -> list[dict]:
    db: Session = get_db()
    try:
        rows = db.query(Report).order_by(Report.created_at.desc()).all()
        return [build_report_dict(r) for r in rows]
    finally:
        db.close()


def get_report_by_id(report_id: str) -> dict | None:
    db: Session = get_db()
    try:
        row = db.query(Report).filter(Report.id == report_id).first()
        return build_report_dict(row) if row else None
    finally:
        db.close()


def get_all_analyses_summary() -> list[dict]:
    """Used by the Streamlit history table."""
    db: Session = get_db()
    try:
        analyses = db.query(Analysis).order_by(Analysis.submitted_at.desc()).all()
        result = []
        for a in analyses:
            report = db.query(Report).filter(Report.analysis_id == a.id).first()
            result.append({
                "id": a.id,
                "decision_type": a.decision_type,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "bias_found": report.bias_found if report else None,
                "confidence_score": report.confidence_score if report else None,
            })
        return result
    finally:
        db.close()