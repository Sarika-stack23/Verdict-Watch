"""
services.py — Verdict Watch V7
Database models + 3-chain Groq pipeline + enterprise additions:
  - V7: Schema migration (text_hash fix)
  - V7: Google Cloud / Material Design ready
  - Feedback / rating system
  - Duplicate analysis detection (text hashing)
  - Trend data helpers
  - Retry logic on Groq calls
  - Structured logging
"""

import os
import json
import uuid
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, String, Boolean, Float,
    Text, DateTime, Integer, text as sa_text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from groq import Groq

load_dotenv()

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("verdict_watch")

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./verdict_watch.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    id                = Column(String,   primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_text          = Column(Text,     nullable=False)
    text_hash         = Column(String,   index=True)
    decision_type     = Column(String,   nullable=False)
    extracted_factors = Column(Text)
    submitted_at      = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id                      = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id             = Column(String,  nullable=False)
    bias_found              = Column(Boolean, default=False)
    bias_types              = Column(Text)
    affected_characteristic = Column(String)
    original_outcome        = Column(String)
    fair_outcome            = Column(String)
    explanation             = Column(Text)
    confidence_score        = Column(Float,   default=0.0)
    recommendations         = Column(Text)
    created_at              = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id         = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id  = Column(String,  nullable=False, index=True)
    rating     = Column(Integer, nullable=False)
    comment    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables and run safe column migrations."""
    Base.metadata.create_all(bind=engine)

    # ── V7 Migration: add text_hash if missing (fixes V5→V6 upgrade error)
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(sa_text("PRAGMA table_info(analyses)"))]
        if "text_hash" not in cols:
            conn.execute(sa_text("ALTER TABLE analyses ADD COLUMN text_hash VARCHAR"))
            conn.commit()
            log.info("Migration: added text_hash column to analyses.")

    log.info("Database initialised (V7).")


def get_db() -> Session:
    return SessionLocal()


# ─────────────────────────────────────────────
# TEXT HASHING
# ─────────────────────────────────────────────

def hash_text(text: str) -> str:
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(normalised.encode()).hexdigest()


def find_duplicate(text_hash: str) -> Optional[dict]:
    db = get_db()
    try:
        analysis = (
            db.query(Analysis)
            .filter(Analysis.text_hash == text_hash)
            .order_by(Analysis.submitted_at.desc())
            .first()
        )
        if not analysis:
            return None
        report = db.query(Report).filter(Report.analysis_id == analysis.id).first()
        return build_report_dict(report) if report else None
    finally:
        db.close()


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────

_MODEL       = "llama-3.3-70b-versatile"
_MAX_RETRIES = 3
_RETRY_DELAY = 1.5


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file: GROQ_API_KEY=gsk_..."
        )
    return Groq(api_key=api_key)


def call_groq(prompt: str, system: str, step_label: str = "") -> dict:
    client = get_groq_client()
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            log.info("Groq %s — attempt %d/%d", step_label, attempt, _MAX_RETRIES)
            response = client.chat.completions.create(
                model=_MODEL,
                max_tokens=1024,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            parsed = json.loads(raw)
            log.info("Groq %s succeeded attempt %d", step_label, attempt)
            return parsed
        except json.JSONDecodeError as e:
            log.warning("JSON parse error attempt %d: %s", attempt, e)
            if attempt == _MAX_RETRIES:
                raise ValueError(f"AI returned invalid JSON after {_MAX_RETRIES} attempts.")
        except Exception as e:
            log.warning("Groq error attempt %d: %s", attempt, e)
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_RETRY_DELAY * attempt)
    raise ValueError("Groq pipeline failed — all retries exhausted.")


# ─────────────────────────────────────────────
# GROQ CALL 1 — EXTRACT FACTORS
# ─────────────────────────────────────────────

def extract_factors(decision_text: str, decision_type: str) -> dict:
    system = (
        "You are a decision analysis expert. "
        "Read the automated decision text and extract a JSON object. "
        "Return ONLY valid JSON with these exact keys: "
        "decision_type (string), outcome (accepted/rejected/approved/denied/other), "
        "criteria_used (list of strings), data_points_weighted (list of strings), "
        "protected_characteristics_mentioned (list of strings). "
        "No explanation. No markdown."
    )
    prompt = f"Decision type hint: {decision_type}\n\nDecision text:\n{decision_text}"
    return call_groq(prompt, system, step_label="STEP-1/extract_factors")


# ─────────────────────────────────────────────
# GROQ CALL 2 — DETECT BIAS
# ─────────────────────────────────────────────

def detect_bias(extracted_factors: dict) -> dict:
    system = (
        "You are a fairness and algorithmic bias expert. "
        "Analyse the extracted decision factors for hidden bias against protected "
        "characteristics: gender, age, race, geography, name-based proxies, disability, "
        "or socioeconomic status. "
        "Return ONLY valid JSON with these exact keys: "
        "bias_detected (boolean), bias_types (list of strings), "
        "which_characteristic_affected (string), bias_evidence (string), "
        "confidence (float 0-1), severity (low or medium or high), "
        "bias_phrases (list of up to 5 specific words/phrases from the text that signal bias). "
        "No explanation. No markdown."
    )
    prompt = f"Extracted decision factors:\n{json.dumps(extracted_factors, indent=2)}"
    return call_groq(prompt, system, step_label="STEP-2/detect_bias")


# ─────────────────────────────────────────────
# GROQ CALL 3 — GENERATE FAIR OUTCOME
# ─────────────────────────────────────────────

def generate_fair_outcome(extracted: dict, bias_result: dict) -> dict:
    system = (
        "You are a fair decision expert and civil rights advisor. "
        "Given the original decision outcome and bias evidence, "
        "determine the fair outcome and explain it in plain English. "
        "Return ONLY valid JSON with these exact keys: "
        "fair_outcome (string), fair_reasoning (string), "
        "what_was_wrong (simple plain English string for the affected person), "
        "next_steps (list of exactly 3 actionable strings), "
        "legal_frameworks (list of up to 2 relevant laws or regulations, "
        "e.g. 'Title VII of the Civil Rights Act'). "
        "No explanation. No markdown."
    )
    prompt = (
        f"Original outcome: {extracted.get('outcome', 'unknown')}\n"
        f"Criteria used: {json.dumps(extracted.get('criteria_used', []))}\n"
        f"Bias evidence: {bias_result.get('bias_evidence', 'none')}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Characteristic affected: {bias_result.get('which_characteristic_affected', 'unknown')}"
    )
    return call_groq(prompt, system, step_label="STEP-3/fair_outcome")


# ─────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────

def run_full_pipeline(
    decision_text: str,
    decision_type: str,
    progress_callback=None,
) -> dict:
    text_hash = hash_text(decision_text)
    db: Session = get_db()
    try:
        if progress_callback:
            progress_callback(1, "Extracting decision criteria…")
        extracted = extract_factors(decision_text, decision_type)

        analysis = Analysis(
            raw_text=decision_text,
            text_hash=text_hash,
            decision_type=decision_type,
            extracted_factors=json.dumps(extracted),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        if progress_callback:
            progress_callback(2, "Scanning for bias patterns…")
        bias_result = detect_bias(extracted)

        if progress_callback:
            progress_callback(3, "Generating fair outcome…")
        fair_result = generate_fair_outcome(extracted, bias_result)

        report_extra = {
            "bias_phrases":     bias_result.get("bias_phrases", []),
            "legal_frameworks": fair_result.get("legal_frameworks", []),
            "fair_reasoning":   fair_result.get("fair_reasoning", ""),
            "severity":         bias_result.get("severity", "low"),
            "bias_evidence":    bias_result.get("bias_evidence", ""),
        }
        full_recs_payload = {
            "steps": fair_result.get("next_steps", []),
            "extra": report_extra,
        }

        report = Report(
            analysis_id             = analysis.id,
            bias_found              = bias_result.get("bias_detected", False),
            bias_types              = json.dumps(bias_result.get("bias_types", [])),
            affected_characteristic = bias_result.get("which_characteristic_affected", ""),
            original_outcome        = extracted.get("outcome", ""),
            fair_outcome            = fair_result.get("fair_outcome", ""),
            explanation             = fair_result.get("what_was_wrong", ""),
            confidence_score        = float(bias_result.get("confidence", 0.0)),
            recommendations         = json.dumps(full_recs_payload),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        log.info("Pipeline complete — report_id=%s bias=%s conf=%.2f",
                 report.id, report.bias_found, report.confidence_score)
        return build_report_dict(report)

    finally:
        db.close()


# ─────────────────────────────────────────────
# APPEAL LETTER
# ─────────────────────────────────────────────

def generate_appeal_letter(report: dict, decision_text: str, decision_type: str) -> str:
    client      = get_groq_client()
    bias_types  = ", ".join(report.get("bias_types", [])) or "undisclosed bias"
    affected    = report.get("affected_characteristic", "a protected characteristic")
    explanation = report.get("explanation", "")
    fair_outcome = report.get("fair_outcome", "a fair reassessment")
    frameworks  = report.get("legal_frameworks", [])
    law_ref     = (", ".join(frameworks) + " and related anti-discrimination law") if frameworks else "applicable anti-discrimination law"

    system = (
        "You are an expert legal writer specialising in discrimination and civil rights cases. "
        "Write formal, persuasive appeal letters. "
        "Use [DATE], [YOUR NAME], [YOUR ADDRESS], [RECIPIENT NAME/TITLE], [ORGANISATION] as placeholders."
    )
    prompt = (
        f"Write a formal appeal letter:\n\n"
        f"Decision type: {decision_type}\n"
        f"Original decision: {decision_text[:400]}\n"
        f"Bias detected: {bias_types}\n"
        f"Characteristic affected: {affected}\n"
        f"What was wrong: {explanation}\n"
        f"Fair outcome requested: {fair_outcome}\n"
        f"Legal frameworks to cite: {law_ref}\n\n"
        "The letter should: open professionally, reference the specific decision, "
        "state grounds for appeal citing discriminatory factors and relevant laws, "
        "request a formal review, and close professionally. Under 450 words."
    )
    resp = client.chat.completions.create(
        model=_MODEL,
        max_tokens=900,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────────

def save_feedback(report_id: str, rating: int, comment: str = "") -> bool:
    db = get_db()
    try:
        fb = Feedback(report_id=report_id, rating=rating, comment=comment)
        db.add(fb)
        db.commit()
        log.info("Feedback saved — report_id=%s rating=%d", report_id, rating)
        return True
    except Exception as e:
        log.error("Failed to save feedback: %s", e)
        return False
    finally:
        db.close()


def get_feedback_stats() -> dict:
    db = get_db()
    try:
        all_fb = db.query(Feedback).all()
        if not all_fb:
            return {"total": 0, "helpful_pct": 0}
        helpful = sum(1 for f in all_fb if f.rating == 1)
        return {
            "total":       len(all_fb),
            "helpful_pct": round(helpful / len(all_fb) * 100),
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def build_report_dict(report: Report) -> dict:
    recs_raw = json.loads(report.recommendations or "[]")
    if isinstance(recs_raw, dict):
        recommendations = recs_raw.get("steps", [])
        extra           = recs_raw.get("extra", {})
    else:
        recommendations = recs_raw
        extra           = {}

    return {
        "id":                      report.id,
        "analysis_id":             report.analysis_id,
        "bias_found":              report.bias_found,
        "bias_types":              json.loads(report.bias_types or "[]"),
        "affected_characteristic": report.affected_characteristic,
        "original_outcome":        report.original_outcome,
        "fair_outcome":            report.fair_outcome,
        "explanation":             report.explanation,
        "confidence_score":        report.confidence_score,
        "recommendations":         recommendations,
        "created_at":              report.created_at.isoformat() if report.created_at else None,
        "bias_phrases":            extra.get("bias_phrases", []),
        "legal_frameworks":        extra.get("legal_frameworks", []),
        "fair_reasoning":          extra.get("fair_reasoning", ""),
        "severity":                extra.get("severity", "low"),
        "bias_evidence":           extra.get("bias_evidence", ""),
    }


def get_all_reports() -> list[dict]:
    db = get_db()
    try:
        rows = db.query(Report).order_by(Report.created_at.desc()).all()
        return [build_report_dict(r) for r in rows]
    finally:
        db.close()


def get_report_by_id(report_id: str) -> dict | None:
    db = get_db()
    try:
        row = db.query(Report).filter(Report.id == report_id).first()
        return build_report_dict(row) if row else None
    finally:
        db.close()


def get_trend_data() -> list[dict]:
    db = get_db()
    try:
        rows   = db.query(Report).order_by(Report.created_at.asc()).all()
        by_day: dict[str, dict] = {}
        for r in rows:
            day = (r.created_at or datetime.utcnow()).strftime("%Y-%m-%d")
            if day not in by_day:
                by_day[day] = {"total": 0, "bias": 0}
            by_day[day]["total"] += 1
            if r.bias_found:
                by_day[day]["bias"] += 1
        return [
            {
                "date":      d,
                "total":     v["total"],
                "bias":      v["bias"],
                "bias_rate": round(v["bias"] / v["total"] * 100) if v["total"] else 0,
            }
            for d, v in sorted(by_day.items())
        ]
    finally:
        db.close()


def get_all_analyses_summary() -> list[dict]:
    db = get_db()
    try:
        analyses = db.query(Analysis).order_by(Analysis.submitted_at.desc()).all()
        result   = []
        for a in analyses:
            report = db.query(Report).filter(Report.analysis_id == a.id).first()
            result.append({
                "id":               a.id,
                "decision_type":    a.decision_type,
                "submitted_at":     a.submitted_at.isoformat() if a.submitted_at else None,
                "bias_found":       report.bias_found if report else None,
                "confidence_score": report.confidence_score if report else None,
            })
        return result
    finally:
        db.close()