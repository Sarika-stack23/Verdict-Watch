"""
services.py — Verdict Watch V11
Database models + 3-chain Groq pipeline.

V11 changes:
  - Timing metadata per pipeline step
  - Quick-scan mode (single Groq call)
  - Per-step retry counter stored in report
  - Cleaner structured logging
  - Feedback comments stored
  - get_confidence_trend() for sparkline
  - Safe schema migration (idempotent)
"""

import os
import json
import uuid
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional, Callable

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, String, Boolean, Float,
    Text, DateTime, Integer, text as sa_text,
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
# DATABASE
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./verdict_watch.db")
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()

_MIGRATIONS = [
    ("analyses",  "text_hash",      "ALTER TABLE analyses ADD COLUMN text_hash VARCHAR"),
    ("analyses",  "decision_type",  "ALTER TABLE analyses ADD COLUMN decision_type VARCHAR"),
    ("reports",   "bias_phrases",   "ALTER TABLE reports  ADD COLUMN bias_phrases TEXT"),
    ("reports",   "timing_ms",      "ALTER TABLE reports  ADD COLUMN timing_ms TEXT"),
    ("reports",   "retry_counts",   "ALTER TABLE reports  ADD COLUMN retry_counts TEXT"),
    ("feedback",  "comment",        "ALTER TABLE feedback ADD COLUMN comment TEXT"),
]


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
    recommendations         = Column(Text)   # JSON blob
    bias_phrases            = Column(Text)   # JSON list
    timing_ms               = Column(Text)   # JSON {"extract":ms,"detect":ms,"fair":ms}
    retry_counts            = Column(Text)   # JSON {"extract":n,"detect":n,"fair":n}
    created_at              = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id  = Column(String,  nullable=False, index=True)
    rating     = Column(Integer, nullable=False)   # 1 = helpful, 0 = not helpful
    comment    = Column(Text,    default="")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    """Create tables then run idempotent column migrations."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for table, col, ddl in _MIGRATIONS:
            try:
                rows = conn.execute(sa_text(f"PRAGMA table_info({table})")).fetchall()
                existing = [r[1] for r in rows]
                if col not in existing:
                    conn.execute(sa_text(ddl))
                    conn.commit()
                    log.info("Migration: added %s.%s", table, col)
            except Exception as exc:
                log.warning("Migration skipped (%s.%s): %s", table, col, exc)
    log.info("Database ready (V11).")


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
# GROQ CLIENT + CALL HELPERS
# ─────────────────────────────────────────────

_MODEL       = "llama-3.3-70b-versatile"
_MAX_RETRIES = 3
_RETRY_DELAY = 1.5


def get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to .env: GROQ_API_KEY=gsk_..."
        )
    return Groq(api_key=key)


def _call_groq_json(messages: list[dict], label: str) -> tuple[dict, int, int]:
    """
    Call Groq expecting JSON back.
    Returns (parsed_dict, retry_count, elapsed_ms).
    """
    client     = get_groq_client()
    retries    = 0
    t0         = time.perf_counter()

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            log.info("Groq %s — attempt %d", label, attempt)
            resp = client.chat.completions.create(
                model=_MODEL,
                max_tokens=1024,
                temperature=0.1,
                messages=messages,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.lower().startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info("Groq %s — ok in %dms (attempt %d)", label, elapsed, attempt)
            return parsed, retries, elapsed
        except json.JSONDecodeError as exc:
            retries += 1
            log.warning("JSON parse error attempt %d: %s", attempt, exc)
            if attempt == _MAX_RETRIES:
                raise ValueError(f"AI returned invalid JSON after {_MAX_RETRIES} attempts.")
        except Exception as exc:
            retries += 1
            log.warning("Groq error attempt %d: %s", attempt, exc)
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_RETRY_DELAY * attempt)

    raise ValueError("Groq pipeline failed — all retries exhausted.")


def _call_groq_text(messages: list[dict], label: str) -> str:
    """Call Groq expecting plain text back."""
    client = get_groq_client()
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=_MODEL,
                max_tokens=900,
                temperature=0.3,
                messages=messages,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            log.warning("Groq text %s attempt %d: %s", label, attempt, exc)
            if attempt == _MAX_RETRIES:
                raise
            time.sleep(_RETRY_DELAY * attempt)
    raise ValueError("Groq text call failed.")


# ─────────────────────────────────────────────
# PIPELINE STEP 1 — EXTRACT FACTORS
# ─────────────────────────────────────────────

_SYS_EXTRACT = (
    "You are a decision analysis expert. "
    "Read the automated decision text and extract a JSON object with these exact keys: "
    "decision_type (string), outcome (accepted/rejected/approved/denied/other), "
    "criteria_used (list of strings), data_points_weighted (list of strings), "
    "protected_characteristics_mentioned (list of strings). "
    "Return ONLY valid JSON — no markdown, no explanation."
)


def extract_factors(decision_text: str, decision_type: str) -> tuple[dict, int, int]:
    messages = [
        {"role": "system", "content": _SYS_EXTRACT},
        {"role": "user",   "content": f"Decision type hint: {decision_type}\n\nDecision text:\n{decision_text}"},
    ]
    return _call_groq_json(messages, "STEP-1/extract")


# ─────────────────────────────────────────────
# PIPELINE STEP 2 — DETECT BIAS
# ─────────────────────────────────────────────

_SYS_DETECT = (
    "You are a fairness and algorithmic-bias expert. "
    "Analyse the extracted decision factors for hidden bias against protected characteristics: "
    "gender, age, race, geography, name-based proxies, disability, or socioeconomic status. "
    "Return ONLY valid JSON with these exact keys: "
    "bias_detected (boolean), bias_types (list of strings), "
    "which_characteristic_affected (string), bias_evidence (string), "
    "confidence (float 0-1), severity (low | medium | high), "
    "bias_phrases (list of up to 5 specific words/phrases from the text that signal bias). "
    "No explanation. No markdown."
)


def detect_bias(extracted: dict) -> tuple[dict, int, int]:
    messages = [
        {"role": "system", "content": _SYS_DETECT},
        {"role": "user",   "content": f"Extracted factors:\n{json.dumps(extracted, indent=2)}"},
    ]
    return _call_groq_json(messages, "STEP-2/detect")


# ─────────────────────────────────────────────
# PIPELINE STEP 3 — FAIR OUTCOME
# ─────────────────────────────────────────────

_SYS_FAIR = (
    "You are a fair-decision expert and civil-rights advisor. "
    "Given the original decision and bias evidence, determine the fair outcome. "
    "Return ONLY valid JSON with these exact keys: "
    "fair_outcome (string), fair_reasoning (string), "
    "what_was_wrong (plain-English string for the affected person), "
    "next_steps (list of exactly 3 actionable strings), "
    "legal_frameworks (list of up to 2 relevant laws, "
    "e.g. 'Title VII of the Civil Rights Act'). "
    "No explanation. No markdown."
)


def generate_fair_outcome(extracted: dict, bias_result: dict) -> tuple[dict, int, int]:
    messages = [
        {"role": "system", "content": _SYS_FAIR},
        {"role": "user",   "content": (
            f"Original outcome: {extracted.get('outcome', 'unknown')}\n"
            f"Criteria used: {json.dumps(extracted.get('criteria_used', []))}\n"
            f"Bias evidence: {bias_result.get('bias_evidence', 'none')}\n"
            f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
            f"Characteristic affected: {bias_result.get('which_characteristic_affected', 'unknown')}"
        )},
    ]
    return _call_groq_json(messages, "STEP-3/fair")


# ─────────────────────────────────────────────
# QUICK SCAN — single call (faster, less detail)
# ─────────────────────────────────────────────

_SYS_QUICK = (
    "You are a bias-detection expert. In ONE call, analyse this automated decision for bias. "
    "Return ONLY valid JSON with these keys: "
    "bias_detected (boolean), bias_types (list of strings), "
    "which_characteristic_affected (string), "
    "confidence (float 0-1), severity (low | medium | high), "
    "original_outcome (string), fair_outcome (string), "
    "explanation (plain-English, 1-2 sentences), "
    "next_steps (list of 2 strings), bias_phrases (list of up to 3 strings). "
    "No markdown, no explanation outside JSON."
)


def quick_scan(decision_text: str, decision_type: str) -> dict:
    t0 = time.perf_counter()
    result, retries, elapsed = _call_groq_json(
        [
            {"role": "system", "content": _SYS_QUICK},
            {"role": "user",   "content": f"Decision type: {decision_type}\n\n{decision_text}"},
        ],
        "QUICK-SCAN",
    )
    return {
        "id":                      str(uuid.uuid4()),
        "analysis_id":             "quick-scan",
        "bias_found":              result.get("bias_detected", False),
        "bias_types":              result.get("bias_types", []),
        "affected_characteristic": result.get("which_characteristic_affected", ""),
        "original_outcome":        result.get("original_outcome", ""),
        "fair_outcome":            result.get("fair_outcome", ""),
        "explanation":             result.get("explanation", ""),
        "confidence_score":        float(result.get("confidence", 0.0)),
        "recommendations":         result.get("next_steps", []),
        "created_at":              datetime.utcnow().isoformat(),
        "bias_phrases":            result.get("bias_phrases", []),
        "legal_frameworks":        [],
        "fair_reasoning":          "",
        "severity":                result.get("severity", "low"),
        "bias_evidence":           "",
        "timing_ms":               {"quick": elapsed},
        "retry_counts":            {"quick": retries},
        "mode":                    "quick",
    }


# ─────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────

def run_full_pipeline(
    decision_text:     str,
    decision_type:     str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> dict:
    text_hash = hash_text(decision_text)
    db: Session = get_db()
    try:
        if progress_callback:
            progress_callback(1, "Extracting decision criteria…")
        extracted, r1, t1 = extract_factors(decision_text, decision_type)

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
        bias_result, r2, t2 = detect_bias(extracted)

        if progress_callback:
            progress_callback(3, "Generating fair outcome…")
        fair_result, r3, t3 = generate_fair_outcome(extracted, bias_result)

        extra = {
            "bias_phrases":     bias_result.get("bias_phrases", []),
            "legal_frameworks": fair_result.get("legal_frameworks", []),
            "fair_reasoning":   fair_result.get("fair_reasoning", ""),
            "severity":         bias_result.get("severity", "low"),
            "bias_evidence":    bias_result.get("bias_evidence", ""),
        }
        recs_payload = {
            "steps": fair_result.get("next_steps", []),
            "extra": extra,
        }
        timing  = {"extract": t1, "detect": t2, "fair": t3, "total": t1 + t2 + t3}
        retries = {"extract": r1, "detect": r2, "fair": r3}

        report = Report(
            analysis_id             = analysis.id,
            bias_found              = bias_result.get("bias_detected", False),
            bias_types              = json.dumps(bias_result.get("bias_types", [])),
            affected_characteristic = bias_result.get("which_characteristic_affected", ""),
            original_outcome        = extracted.get("outcome", ""),
            fair_outcome            = fair_result.get("fair_outcome", ""),
            explanation             = fair_result.get("what_was_wrong", ""),
            confidence_score        = float(bias_result.get("confidence", 0.0)),
            recommendations         = json.dumps(recs_payload),
            bias_phrases            = json.dumps(bias_result.get("bias_phrases", [])),
            timing_ms               = json.dumps(timing),
            retry_counts            = json.dumps(retries),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        log.info(
            "Pipeline complete — id=%s bias=%s conf=%.2f total=%dms",
            report.id, report.bias_found, report.confidence_score, timing["total"],
        )
        return build_report_dict(report)
    finally:
        db.close()


# ─────────────────────────────────────────────
# APPEAL LETTER
# ─────────────────────────────────────────────

def generate_appeal_letter(report: dict, decision_text: str, decision_type: str) -> str:
    bias_types  = ", ".join(report.get("bias_types", [])) or "undisclosed bias"
    affected    = report.get("affected_characteristic", "a protected characteristic")
    explanation = report.get("explanation", "")
    fair_outcome = report.get("fair_outcome", "a fair reassessment")
    frameworks  = report.get("legal_frameworks", [])
    law_ref     = (", ".join(frameworks) + " and related anti-discrimination law") if frameworks else "applicable anti-discrimination law"

    return _call_groq_text(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert legal writer specialising in discrimination and civil-rights cases. "
                    "Write formal, persuasive appeal letters. "
                    "Use [DATE], [YOUR NAME], [YOUR ADDRESS], [RECIPIENT NAME/TITLE], [ORGANISATION] as placeholders."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Write a formal appeal letter:\n\n"
                    f"Decision type: {decision_type}\n"
                    f"Original decision: {decision_text[:400]}\n"
                    f"Bias detected: {bias_types}\n"
                    f"Characteristic affected: {affected}\n"
                    f"What was wrong: {explanation}\n"
                    f"Fair outcome requested: {fair_outcome}\n"
                    f"Legal frameworks: {law_ref}\n\n"
                    "The letter should: open professionally, reference the specific decision, "
                    "state grounds for appeal citing discriminatory factors and relevant laws, "
                    "request a formal review, and close professionally. Under 450 words."
                ),
            },
        ],
        "APPEAL",
    )


# ─────────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────────

def save_feedback(report_id: str, rating: int, comment: str = "") -> bool:
    db = get_db()
    try:
        fb = Feedback(report_id=report_id, rating=rating, comment=comment.strip())
        db.add(fb)
        db.commit()
        log.info("Feedback saved — report_id=%s rating=%d", report_id, rating)
        return True
    except Exception as exc:
        log.error("Feedback save failed: %s", exc)
        return False
    finally:
        db.close()


def get_feedback_stats() -> dict:
    db = get_db()
    try:
        rows = db.query(Feedback).all()
        if not rows:
            return {"total": 0, "helpful_pct": 0, "recent_comments": []}
        helpful  = sum(1 for f in rows if f.rating == 1)
        comments = [f.comment for f in sorted(rows, key=lambda x: x.created_at, reverse=True) if f.comment][:5]
        return {
            "total":           len(rows),
            "helpful_pct":     round(helpful / len(rows) * 100),
            "recent_comments": comments,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────
# QUERY HELPERS
# ─────────────────────────────────────────────

def build_report_dict(report: "Report") -> dict:
    recs_raw = json.loads(report.recommendations or "[]")
    if isinstance(recs_raw, dict):
        recommendations = recs_raw.get("steps", [])
        extra           = recs_raw.get("extra", {})
    else:
        recommendations = recs_raw
        extra           = {}

    timing  = json.loads(report.timing_ms    or "{}") if report.timing_ms    else {}
    retries = json.loads(report.retry_counts or "{}") if report.retry_counts else {}
    phrases = json.loads(report.bias_phrases or "[]") if report.bias_phrases else []

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
        "bias_phrases":            phrases,
        "legal_frameworks":        extra.get("legal_frameworks", []),
        "fair_reasoning":          extra.get("fair_reasoning", ""),
        "severity":                extra.get("severity", "low"),
        "bias_evidence":           extra.get("bias_evidence", ""),
        "timing_ms":               timing,
        "retry_counts":            retries,
        "mode":                    "full",
    }


def get_all_reports() -> list[dict]:
    db = get_db()
    try:
        rows = db.query(Report).order_by(Report.created_at.desc()).all()
        return [build_report_dict(r) for r in rows]
    finally:
        db.close()


def get_report_by_id(report_id: str) -> Optional[dict]:
    db = get_db()
    try:
        row = db.query(Report).filter(Report.id == report_id).first()
        return build_report_dict(row) if row else None
    finally:
        db.close()


def get_trend_data() -> list[dict]:
    """Aggregate reports by day for trend chart."""
    db = get_db()
    try:
        rows   = db.query(Report).order_by(Report.created_at.asc()).all()
        by_day: dict[str, dict] = {}
        for r in rows:
            day = (r.created_at or datetime.utcnow()).strftime("%Y-%m-%d")
            if day not in by_day:
                by_day[day] = {"total": 0, "bias": 0, "conf_sum": 0.0}
            by_day[day]["total"]    += 1
            by_day[day]["conf_sum"] += r.confidence_score or 0.0
            if r.bias_found:
                by_day[day]["bias"] += 1
        return [
            {
                "date":      d,
                "total":     v["total"],
                "bias":      v["bias"],
                "bias_rate": round(v["bias"] / v["total"] * 100) if v["total"] else 0,
                "avg_conf":  round(v["conf_sum"] / v["total"] * 100) if v["total"] else 0,
            }
            for d, v in sorted(by_day.items())
        ]
    finally:
        db.close()


def get_confidence_trend(n: int = 20) -> list[float]:
    """Last n confidence scores for sparkline."""
    db = get_db()
    try:
        rows = (
            db.query(Report.confidence_score)
            .order_by(Report.created_at.desc())
            .limit(n)
            .all()
        )
        return [round((r[0] or 0) * 100) for r in reversed(rows)]
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