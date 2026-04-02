"""
services.py — Verdict Watch V15
UPGRADED: Full AI Governance Layer added.

New in V15 (Phase 1 — closes the 22-point gap):
  STEP 0 — Pre-decision characteristic scan (data audit before analysis)
  STEP 4 — Fairness audit: counterfactual parity across demographics
  STEP 5 — Explainability trace: phrase-level reasoning chain
  DB      — New columns: fairness_scores, explainability_trace, characteristic_weights
  HELPERS — generate_model_bias_report() for batch fairness PDF report
"""

import os, json, uuid, hashlib, logging, time
from datetime import datetime
from typing import Optional, Callable

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, String, Boolean, Float,
    Text, DateTime, Integer, text as sa_text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

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
    ("analyses", "text_hash",             "ALTER TABLE analyses ADD COLUMN text_hash VARCHAR"),
    ("analyses", "decision_type",         "ALTER TABLE analyses ADD COLUMN decision_type VARCHAR"),
    ("reports",  "bias_phrases",          "ALTER TABLE reports  ADD COLUMN bias_phrases TEXT"),
    ("reports",  "timing_ms",             "ALTER TABLE reports  ADD COLUMN timing_ms TEXT"),
    ("reports",  "retry_counts",          "ALTER TABLE reports  ADD COLUMN retry_counts TEXT"),
    ("reports",  "ai_provider",           "ALTER TABLE reports  ADD COLUMN ai_provider VARCHAR"),
    ("reports",  "fairness_scores",       "ALTER TABLE reports  ADD COLUMN fairness_scores TEXT"),
    ("reports",  "explainability_trace",  "ALTER TABLE reports  ADD COLUMN explainability_trace TEXT"),
    ("reports",  "characteristic_weights","ALTER TABLE reports  ADD COLUMN characteristic_weights TEXT"),
    ("feedback", "comment",               "ALTER TABLE feedback ADD COLUMN comment TEXT"),
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
    recommendations         = Column(Text)
    bias_phrases            = Column(Text)
    timing_ms               = Column(Text)
    retry_counts            = Column(Text)
    ai_provider             = Column(String,  default="gemini")
    fairness_scores         = Column(Text)
    explainability_trace    = Column(Text)
    characteristic_weights  = Column(Text)
    created_at              = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id  = Column(String,  nullable=False, index=True)
    rating     = Column(Integer, nullable=False)
    comment    = Column(Text,    default="")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
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
    log.info("Database ready (V15).")


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
# AI PROVIDER CONSTANTS
# ─────────────────────────────────────────────

_GEMINI_MODEL = "gemini-1.5-flash"
_GROQ_MODEL   = "llama-3.3-70b-versatile"
_MAX_RETRIES  = 3
_RETRY_DELAY  = 1.5

PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ   = "groq"


# ─────────────────────────────────────────────
# GEMINI CLIENT
# ─────────────────────────────────────────────

def get_gemini_client():
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
    if not key:
        raise ValueError("GEMINI_API_KEY not set.")
    genai.configure(api_key=key)
    return genai.GenerativeModel(_GEMINI_MODEL)


def _call_gemini_json(prompt: str, label: str) -> tuple[dict, int, int]:
    t0 = time.perf_counter(); retries = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            model    = get_gemini_client()
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 1500,
                                   "response_mime_type": "application/json"}
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.lower().startswith("json"): raw = raw[4:]
            parsed  = json.loads(raw.strip())
            elapsed = int((time.perf_counter() - t0) * 1000)
            return parsed, retries, elapsed
        except json.JSONDecodeError:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise ValueError(f"Gemini invalid JSON after {_MAX_RETRIES} attempts.")
        except Exception as exc:
            retries += 1
            if attempt == _MAX_RETRIES: raise
            time.sleep(_RETRY_DELAY * attempt)
    raise ValueError("Gemini exhausted retries.")


def _call_gemini_text(prompt: str, label: str) -> str:
    model = get_gemini_client()
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = model.generate_content(
                prompt, generation_config={"temperature": 0.3, "max_output_tokens": 1000})
            return response.text.strip()
        except Exception as exc:
            if attempt == _MAX_RETRIES: raise
            time.sleep(_RETRY_DELAY * attempt)
    raise ValueError("Gemini text call failed.")


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────

def get_groq_client():
    from groq import Groq
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key: raise ValueError("GROQ_API_KEY is not set.")
    return Groq(api_key=key)


def _call_groq_json(messages: list[dict], label: str) -> tuple[dict, int, int]:
    t0 = time.perf_counter(); retries = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            client = get_groq_client()
            resp   = client.chat.completions.create(
                model=_GROQ_MODEL, max_tokens=1500, temperature=0.1, messages=messages)
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.lower().startswith("json"): raw = raw[4:]
            parsed  = json.loads(raw.strip())
            elapsed = int((time.perf_counter() - t0) * 1000)
            return parsed, retries, elapsed
        except json.JSONDecodeError:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise ValueError(f"Groq invalid JSON after {_MAX_RETRIES} attempts.")
        except Exception as exc:
            retries += 1
            if attempt == _MAX_RETRIES: raise
            time.sleep(_RETRY_DELAY * attempt)
    raise ValueError("Groq exhausted retries.")


def _call_groq_text(messages: list[dict], label: str) -> str:
    client = get_groq_client()
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=_GROQ_MODEL, max_tokens=1000, temperature=0.3, messages=messages)
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            if attempt == _MAX_RETRIES: raise
            time.sleep(_RETRY_DELAY * attempt)
    raise ValueError("Groq text call failed.")


# ─────────────────────────────────────────────
# UNIFIED AI CALL
# ─────────────────────────────────────────────

def _ai_call_json(gemini_prompt, groq_messages, label, provider=PROVIDER_GEMINI):
    if provider in (PROVIDER_GEMINI, "auto"):
        try:
            result, retries, elapsed = _call_gemini_json(gemini_prompt, label)
            return result, retries, elapsed, PROVIDER_GEMINI
        except Exception as gemini_exc:
            log.warning("Gemini failed for %s (%s) — falling back to Groq", label, gemini_exc)
            try:
                result, retries, elapsed = _call_groq_json(groq_messages, label + "-fallback")
                return result, retries, elapsed, PROVIDER_GROQ
            except Exception as groq_exc:
                raise ValueError(f"Both failed.\nGemini: {gemini_exc}\nGroq: {groq_exc}")
    else:
        result, retries, elapsed = _call_groq_json(groq_messages, label)
        return result, retries, elapsed, PROVIDER_GROQ


def _ai_call_text(gemini_prompt, groq_messages, label, provider=PROVIDER_GEMINI):
    if provider in (PROVIDER_GEMINI, "auto"):
        try:
            return _call_gemini_text(gemini_prompt, label), PROVIDER_GEMINI
        except Exception as exc:
            log.warning("Gemini text failed (%s) — Groq fallback", exc)
            return _call_groq_text(groq_messages, label + "-fallback"), PROVIDER_GROQ
    else:
        return _call_groq_text(groq_messages, label), PROVIDER_GROQ


# ═════════════════════════════════════════════════════
# STEP 0 — PRE-DECISION CHARACTERISTIC SCAN  (NEW V15)
# ═════════════════════════════════════════════════════

_SCAN_INSTRUCTION = (
    "You are an AI governance auditor performing a pre-decision data scan. "
    "Before any bias analysis happens, identify which protected characteristics "
    "are present — explicitly or implicitly — in this decision text. "
    "For each characteristic found, assign an influence weight (0–100) indicating "
    "how strongly that characteristic appears to have influenced the decision. "
    "Return ONLY valid JSON with these exact keys: "
    "characteristics_present (list of strings), "
    "influence_weights (object: characteristic -> weight 0-100), "
    "data_quality_flags (list of strings describing any data issues), "
    "pre_scan_risk (low | medium | high). "
    "No markdown, no explanation."
)


def pre_decision_scan(decision_text: str, provider: str = PROVIDER_GEMINI) -> tuple[dict, str]:
    gemini_prompt = f"{_SCAN_INSTRUCTION}\n\nDecision text:\n{decision_text}"
    groq_messages = [
        {"role": "system", "content": _SCAN_INSTRUCTION},
        {"role": "user",   "content": f"Decision text:\n{decision_text}"},
    ]
    result, _, _, prov = _ai_call_json(gemini_prompt, groq_messages, "STEP-0/pre-scan", provider)
    return result, prov


# ═════════════════════════════════════════════════════
# STEP 1 — EXTRACT FACTORS (unchanged)
# ═════════════════════════════════════════════════════

_EXTRACT_INSTRUCTION = (
    "You are a decision analysis expert. "
    "Read the automated decision text and extract a JSON object with these exact keys: "
    "decision_type (string), outcome (accepted/rejected/approved/denied/other), "
    "criteria_used (list of strings), data_points_weighted (list of strings), "
    "protected_characteristics_mentioned (list of strings). "
    "Return ONLY valid JSON — no markdown, no explanation."
)


def extract_factors(decision_text, decision_type, provider=PROVIDER_GEMINI):
    gemini_prompt = f"{_EXTRACT_INSTRUCTION}\n\nDecision type hint: {decision_type}\n\nDecision text:\n{decision_text}"
    groq_messages = [
        {"role": "system", "content": _EXTRACT_INSTRUCTION},
        {"role": "user",   "content": f"Decision type hint: {decision_type}\n\nDecision text:\n{decision_text}"},
    ]
    result, retries, elapsed, prov = _ai_call_json(
        gemini_prompt, groq_messages, "STEP-1/extract", provider)
    return result, retries, elapsed, prov


# ═════════════════════════════════════════════════════
# STEP 2 — DETECT BIAS (unchanged)
# ═════════════════════════════════════════════════════

_DETECT_INSTRUCTION = (
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


def detect_bias(extracted, provider=PROVIDER_GEMINI):
    factors_json  = json.dumps(extracted, indent=2)
    gemini_prompt = f"{_DETECT_INSTRUCTION}\n\nExtracted factors:\n{factors_json}"
    groq_messages = [
        {"role": "system", "content": _DETECT_INSTRUCTION},
        {"role": "user",   "content": f"Extracted factors:\n{factors_json}"},
    ]
    return _ai_call_json(gemini_prompt, groq_messages, "STEP-2/detect", provider)


# ═════════════════════════════════════════════════════
# STEP 3 — FAIR OUTCOME (unchanged)
# ═════════════════════════════════════════════════════

_FAIR_INSTRUCTION = (
    "You are a fair-decision expert and civil-rights advisor. "
    "Given the original decision and bias evidence, determine the fair outcome. "
    "Return ONLY valid JSON with these exact keys: "
    "fair_outcome (string), fair_reasoning (string), "
    "what_was_wrong (plain-English string for the affected person), "
    "next_steps (list of exactly 3 actionable strings), "
    "legal_frameworks (list of up to 2 relevant laws). "
    "No explanation. No markdown."
)


def generate_fair_outcome(extracted, bias_result, provider=PROVIDER_GEMINI):
    context = (
        f"Original outcome: {extracted.get('outcome', 'unknown')}\n"
        f"Criteria used: {json.dumps(extracted.get('criteria_used', []))}\n"
        f"Bias evidence: {bias_result.get('bias_evidence', 'none')}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Characteristic affected: {bias_result.get('which_characteristic_affected', 'unknown')}"
    )
    gemini_prompt = f"{_FAIR_INSTRUCTION}\n\n{context}"
    groq_messages = [
        {"role": "system", "content": _FAIR_INSTRUCTION},
        {"role": "user",   "content": context},
    ]
    return _ai_call_json(gemini_prompt, groq_messages, "STEP-3/fair", provider)


# ═════════════════════════════════════════════════════
# STEP 4 — FAIRNESS AUDIT: COUNTERFACTUAL PARITY (NEW V15)
# ═════════════════════════════════════════════════════

_FAIRNESS_AUDIT_INSTRUCTION = (
    "You are an AI fairness auditor. Your task is counterfactual fairness testing. "
    "Given the original decision text, imagine the SAME decision was made for hypothetical "
    "applicants who differ ONLY in a single protected characteristic. "
    "For each protected characteristic present, estimate whether the outcome would change "
    "if that characteristic were different (e.g. male vs female, young vs old, local name vs foreign name). "
    "Return ONLY valid JSON with these exact keys: "
    "demographic_parity_scores (object: characteristic_name -> score 0-100, where 100=perfectly fair, 0=completely biased), "
    "counterfactual_findings (list of objects each with: characteristic, hypothetical_change, would_outcome_change (boolean), reasoning (string)), "
    "overall_fairness_score (integer 0-100), "
    "fairness_verdict (fair | partially_fair | unfair), "
    "audit_summary (1-2 sentence plain English summary of the fairness audit). "
    "No markdown, no explanation outside JSON."
)


def run_fairness_audit(
    decision_text: str,
    bias_result: dict,
    provider: str = PROVIDER_GEMINI,
) -> tuple[dict, int, int, str]:
    characteristics = bias_result.get("bias_types", [])
    affected        = bias_result.get("which_characteristic_affected", "")
    context = (
        f"Original decision:\n{decision_text}\n\n"
        f"Bias types detected: {json.dumps(characteristics)}\n"
        f"Primarily affected characteristic: {affected}"
    )
    gemini_prompt = f"{_FAIRNESS_AUDIT_INSTRUCTION}\n\n{context}"
    groq_messages = [
        {"role": "system", "content": _FAIRNESS_AUDIT_INSTRUCTION},
        {"role": "user",   "content": context},
    ]
    return _ai_call_json(gemini_prompt, groq_messages, "STEP-4/fairness-audit", provider)


# ═════════════════════════════════════════════════════
# STEP 5 — EXPLAINABILITY TRACE (NEW V15)
# ═════════════════════════════════════════════════════

_EXPLAIN_INSTRUCTION = (
    "You are an AI explainability expert. Produce a full reasoning chain showing EXACTLY "
    "how this decision discriminated — phrase by phrase, law by law. "
    "Return ONLY valid JSON with these exact keys: "
    "reasoning_chain (list of objects each with: step (integer), phrase (exact text from the decision), "
    "characteristic_triggered (string), legal_violation (string), why_this_matters (string)), "
    "root_cause (string — the fundamental reason bias occurred), "
    "corrective_action (string — what the decision-maker should have done instead), "
    "retroactive_correction (string — how this specific decision can be corrected now). "
    "No markdown, no explanation outside JSON."
)


def generate_explainability_trace(
    decision_text: str,
    bias_result: dict,
    fair_result: dict,
    provider: str = PROVIDER_GEMINI,
) -> tuple[dict, int, int, str]:
    context = (
        f"Original decision:\n{decision_text}\n\n"
        f"Bias evidence: {bias_result.get('bias_evidence', '')}\n"
        f"Bias phrases: {json.dumps(bias_result.get('bias_phrases', []))}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Legal frameworks: {json.dumps(fair_result.get('legal_frameworks', []))}\n"
        f"What was wrong: {fair_result.get('what_was_wrong', '')}"
    )
    gemini_prompt = f"{_EXPLAIN_INSTRUCTION}\n\n{context}"
    groq_messages = [
        {"role": "system", "content": _EXPLAIN_INSTRUCTION},
        {"role": "user",   "content": context},
    ]
    return _ai_call_json(gemini_prompt, groq_messages, "STEP-5/explainability", provider)


# ═════════════════════════════════════════════════════
# QUICK SCAN (updated with fairness score)
# ═════════════════════════════════════════════════════

_QUICK_INSTRUCTION = (
    "You are a bias-detection expert. In ONE call, analyse this automated decision for bias. "
    "Return ONLY valid JSON with these keys: "
    "bias_detected (boolean), bias_types (list of strings), "
    "which_characteristic_affected (string), "
    "confidence (float 0-1), severity (low | medium | high), "
    "original_outcome (string), fair_outcome (string), "
    "explanation (plain-English, 1-2 sentences), "
    "next_steps (list of 2 strings), bias_phrases (list of up to 3 strings), "
    "overall_fairness_score (integer 0-100), "
    "fairness_verdict (fair | partially_fair | unfair). "
    "No markdown, no explanation outside JSON."
)


def quick_scan(decision_text, decision_type, provider=PROVIDER_GEMINI):
    t0            = time.perf_counter()
    context       = f"Decision type: {decision_type}\n\n{decision_text}"
    gemini_prompt = f"{_QUICK_INSTRUCTION}\n\n{context}"
    groq_messages = [
        {"role": "system", "content": _QUICK_INSTRUCTION},
        {"role": "user",   "content": context},
    ]
    result, retries, elapsed, prov_used = _ai_call_json(
        gemini_prompt, groq_messages, "QUICK-SCAN", provider)

    fairness_scores = {
        "overall_fairness_score": result.get("overall_fairness_score", 50),
        "fairness_verdict":       result.get("fairness_verdict", "partially_fair"),
    }
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
        "ai_provider":             prov_used,
        "fairness_scores":         fairness_scores,
        "explainability_trace":    {},
        "characteristic_weights":  {},
    }


# ═════════════════════════════════════════════════════
# FULL PIPELINE (V15 — 5 steps)
# ═════════════════════════════════════════════════════

def run_full_pipeline(
    decision_text:     str,
    decision_type:     str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    provider:          str = PROVIDER_GEMINI,
) -> dict:
    text_hash   = hash_text(decision_text)
    db: Session = get_db()
    prov_used   = provider

    try:
        # ── STEP 0: Pre-decision scan
        if progress_callback: progress_callback(0, "Scanning decision for protected characteristics…")
        pre_scan, p0 = pre_decision_scan(decision_text, provider)
        characteristic_weights = pre_scan.get("influence_weights", {})

        # ── STEP 1: Extract
        if progress_callback: progress_callback(1, "Extracting decision criteria…")
        extracted, r1, t1, p1 = extract_factors(decision_text, decision_type, provider)
        prov_used = p1

        analysis = Analysis(
            raw_text=decision_text, text_hash=text_hash,
            decision_type=decision_type, extracted_factors=json.dumps(extracted),
        )
        db.add(analysis); db.commit(); db.refresh(analysis)

        # ── STEP 2: Detect bias
        if progress_callback: progress_callback(2, "Scanning for bias patterns…")
        bias_result, r2, t2, p2 = detect_bias(extracted, provider)

        # ── STEP 3: Fair outcome
        if progress_callback: progress_callback(3, "Generating fair outcome…")
        fair_result, r3, t3, p3 = generate_fair_outcome(extracted, bias_result, provider)

        # ── STEP 4: Fairness audit (only if bias found)
        fairness_data = {}
        t4 = 0
        if bias_result.get("bias_detected", False):
            if progress_callback: progress_callback(4, "Running fairness audit…")
            try:
                fairness_data, _, t4, _ = run_fairness_audit(decision_text, bias_result, provider)
            except Exception as exc:
                log.warning("Fairness audit failed (non-fatal): %s", exc)
                fairness_data = {"overall_fairness_score": 0, "fairness_verdict": "unfair"}

        # ── STEP 5: Explainability trace (only if bias found)
        explain_data = {}
        t5 = 0
        if bias_result.get("bias_detected", False):
            if progress_callback: progress_callback(5, "Building explainability trace…")
            try:
                explain_data, _, t5, _ = generate_explainability_trace(
                    decision_text, bias_result, fair_result, provider)
            except Exception as exc:
                log.warning("Explainability trace failed (non-fatal): %s", exc)
                explain_data = {}

        # Provider tracking
        providers_used = {p0, p1, p2, p3}
        if PROVIDER_GROQ in providers_used and PROVIDER_GEMINI in providers_used:
            prov_used = "gemini+groq"
        elif PROVIDER_GROQ in providers_used:
            prov_used = PROVIDER_GROQ

        extra = {
            "bias_phrases":     bias_result.get("bias_phrases", []),
            "legal_frameworks": fair_result.get("legal_frameworks", []),
            "fair_reasoning":   fair_result.get("fair_reasoning", ""),
            "severity":         bias_result.get("severity", "low"),
            "bias_evidence":    bias_result.get("bias_evidence", ""),
        }
        recs_payload = {"steps": fair_result.get("next_steps", []), "extra": extra}
        timing       = {"pre_scan": 0, "extract": t1, "detect": t2, "fair": t3,
                        "fairness_audit": t4, "explainability": t5,
                        "total": t1 + t2 + t3 + t4 + t5}
        retries      = {"extract": r1, "detect": r2, "fair": r3}

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
            ai_provider             = prov_used,
            fairness_scores         = json.dumps(fairness_data),
            explainability_trace    = json.dumps(explain_data),
            characteristic_weights  = json.dumps(characteristic_weights),
        )
        db.add(report); db.commit(); db.refresh(report)

        log.info("V15 pipeline complete — id=%s bias=%s fairness=%s total=%dms provider=%s",
                 report.id, report.bias_found,
                 fairness_data.get("overall_fairness_score", "N/A"),
                 timing["total"], prov_used)
        return build_report_dict(report)
    finally:
        db.close()


# ─────────────────────────────────────────────
# APPEAL LETTER
# ─────────────────────────────────────────────

def generate_appeal_letter(report, decision_text, decision_type, provider=PROVIDER_GEMINI):
    bias_types   = ", ".join(report.get("bias_types", [])) or "undisclosed bias"
    affected     = report.get("affected_characteristic", "a protected characteristic")
    explanation  = report.get("explanation", "")
    fair_outcome = report.get("fair_outcome", "a fair reassessment")
    frameworks   = report.get("legal_frameworks", [])
    law_ref      = (", ".join(frameworks) + " and related anti-discrimination law") if frameworks else "applicable anti-discrimination law"

    # Include fairness score in appeal if available
    fairness_scores = report.get("fairness_scores", {})
    fairness_score  = fairness_scores.get("overall_fairness_score", None)
    fairness_line   = f"\nA fairness audit of this decision returned an overall fairness score of {fairness_score}/100, indicating the decision was not applied equitably." if fairness_score is not None else ""

    system_inst = (
        "You are an expert legal writer specialising in discrimination and civil-rights cases. "
        "Write formal, persuasive appeal letters. "
        "Use [DATE], [YOUR NAME], [YOUR ADDRESS], [RECIPIENT NAME/TITLE], [ORGANISATION] as placeholders."
    )
    user_content = (
        f"Write a formal appeal letter:\n\n"
        f"Decision type: {decision_type}\n"
        f"Original decision: {decision_text[:400]}\n"
        f"Bias detected: {bias_types}\n"
        f"Characteristic affected: {affected}\n"
        f"What was wrong: {explanation}{fairness_line}\n"
        f"Fair outcome requested: {fair_outcome}\n"
        f"Legal frameworks: {law_ref}\n\n"
        "The letter should: open professionally, reference the specific decision, "
        "state grounds for appeal citing discriminatory factors, relevant laws, and the fairness audit result, "
        "request a formal review, and close professionally. Under 450 words."
    )
    gemini_prompt = f"{system_inst}\n\n{user_content}"
    groq_messages = [
        {"role": "system", "content": system_inst},
        {"role": "user",   "content": user_content},
    ]
    text, _ = _ai_call_text(gemini_prompt, groq_messages, "APPEAL", provider)
    return text


# ─────────────────────────────────────────────
# MODEL BIAS REPORT (NEW V15)
# ─────────────────────────────────────────────

def generate_model_bias_report(reports: list[dict]) -> dict:
    """
    Aggregate fairness metrics across multiple reports.
    Returns a summary suitable for the Fairness Metrics dashboard.
    """
    if not reports:
        return {}

    total          = len(reports)
    biased         = sum(1 for r in reports if r.get("bias_found"))
    fairness_scores_all = []
    dim_scores     = {}  # characteristic -> list of parity scores
    verdicts       = {"fair": 0, "partially_fair": 0, "unfair": 0}
    char_weights   = {}  # characteristic -> list of weights

    for r in reports:
        fs = r.get("fairness_scores", {})
        if isinstance(fs, str):
            try: fs = json.loads(fs)
            except: fs = {}

        if "overall_fairness_score" in fs:
            fairness_scores_all.append(fs["overall_fairness_score"])

        verdict = fs.get("fairness_verdict", "")
        if verdict in verdicts:
            verdicts[verdict] += 1

        parity = fs.get("demographic_parity_scores", {})
        for char, score in parity.items():
            dim_scores.setdefault(char, []).append(score)

        cw = r.get("characteristic_weights", {})
        if isinstance(cw, str):
            try: cw = json.loads(cw)
            except: cw = {}
        for char, w in cw.items():
            char_weights.setdefault(char, []).append(w)

    avg_fairness = round(sum(fairness_scores_all) / len(fairness_scores_all)) if fairness_scores_all else None
    avg_dim = {char: round(sum(v) / len(v)) for char, v in dim_scores.items()}
    avg_cw  = {char: round(sum(v) / len(v)) for char, v in char_weights.items()}

    return {
        "total_decisions":      total,
        "biased_decisions":     biased,
        "bias_rate":            round(biased / total * 100) if total else 0,
        "avg_fairness_score":   avg_fairness,
        "fairness_verdicts":    verdicts,
        "dim_parity_scores":    avg_dim,
        "avg_char_weights":     avg_cw,
    }


# ─────────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────────

def save_feedback(report_id, rating, comment=""):
    db = get_db()
    try:
        fb = Feedback(report_id=report_id, rating=rating, comment=comment.strip())
        db.add(fb); db.commit()
        return True
    except Exception as exc:
        log.error("Feedback save failed: %s", exc)
        return False
    finally:
        db.close()


def get_feedback_stats():
    db = get_db()
    try:
        rows = db.query(Feedback).all()
        if not rows: return {"total": 0, "helpful_pct": 0, "recent_comments": []}
        helpful  = sum(1 for f in rows if f.rating == 1)
        comments = [f.comment for f in sorted(rows, key=lambda x: x.created_at, reverse=True) if f.comment][:5]
        return {"total": len(rows), "helpful_pct": round(helpful / len(rows) * 100), "recent_comments": comments}
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

    timing   = json.loads(report.timing_ms    or "{}") if report.timing_ms    else {}
    retries  = json.loads(report.retry_counts or "{}") if report.retry_counts else {}
    phrases  = json.loads(report.bias_phrases or "[]") if report.bias_phrases else []

    fairness_raw = getattr(report, "fairness_scores", None)
    fairness_scores = {}
    if fairness_raw:
        try: fairness_scores = json.loads(fairness_raw)
        except: pass

    explain_raw = getattr(report, "explainability_trace", None)
    explainability_trace = {}
    if explain_raw:
        try: explainability_trace = json.loads(explain_raw)
        except: pass

    cw_raw = getattr(report, "characteristic_weights", None)
    characteristic_weights = {}
    if cw_raw:
        try: characteristic_weights = json.loads(cw_raw)
        except: pass

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
        "ai_provider":             getattr(report, "ai_provider", "gemini") or "gemini",
        "fairness_scores":         fairness_scores,
        "explainability_trace":    explainability_trace,
        "characteristic_weights":  characteristic_weights,
    }


def get_all_reports():
    db = get_db()
    try:
        rows = db.query(Report).order_by(Report.created_at.desc()).all()
        return [build_report_dict(r) for r in rows]
    finally:
        db.close()


def get_report_by_id(report_id):
    db = get_db()
    try:
        row = db.query(Report).filter(Report.id == report_id).first()
        return build_report_dict(row) if row else None
    finally:
        db.close()


def get_trend_data():
    db = get_db()
    try:
        rows   = db.query(Report).order_by(Report.created_at.asc()).all()
        by_day = {}
        for r in rows:
            day = (r.created_at or datetime.utcnow()).strftime("%Y-%m-%d")
            if day not in by_day:
                by_day[day] = {"total": 0, "bias": 0, "conf_sum": 0.0}
            by_day[day]["total"]    += 1
            by_day[day]["conf_sum"] += r.confidence_score or 0.0
            if r.bias_found: by_day[day]["bias"] += 1
        return [
            {"date": d, "total": v["total"], "bias": v["bias"],
             "bias_rate": round(v["bias"] / v["total"] * 100) if v["total"] else 0,
             "avg_conf":  round(v["conf_sum"] / v["total"] * 100) if v["total"] else 0}
            for d, v in sorted(by_day.items())
        ]
    finally:
        db.close()


def get_confidence_trend(n=20):
    db = get_db()
    try:
        rows = (db.query(Report.confidence_score)
                .order_by(Report.created_at.desc()).limit(n).all())
        return [round((r[0] or 0) * 100) for r in reversed(rows)]
    finally:
        db.close()


def check_providers():
    status = {"gemini": False, "groq": False}
    try: get_gemini_client(); status["gemini"] = True
    except: pass
    try: get_groq_client();   status["groq"]   = True
    except: pass
    return status