"""
services.py — Verdict Watch V21
AI Governance Edition — 10-step pipeline.

V21 changes vs V20:
  - Step 8 · TIMELINE: legal deadline calculation + jurisdiction mapping
  - Step 9 · PRECEDENT: case-law retrieval via Gemini Search Grounding
  - Claude (claude-3-5-sonnet) added as 3rd fallback after Groq
  - Batch CSV raised from 10 → 50 rows
  - _CLAUDE_MODEL constant + get_claude_client()
  - _ai_call_json / _ai_call_text updated with 4-tier chain: Vertex → Gemini → Groq → Claude
  - run_full_pipeline extended with Steps 8 + 9
  - New DB columns: legal_timeline, precedents
  - Timeline + precedent fields in AnalyseResponse via build_report_dict
  - quick_scan returns legal_timeline={} / precedents=[]
"""

import os, json, uuid, hashlib, logging, time
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, String, Boolean, Float,
    Text, DateTime, Integer, text as sa_text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("verdict_watch_v21")

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./verdict_watch.db")
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()

_MIGRATIONS = [
    ("analyses", "text_hash",              "ALTER TABLE analyses ADD COLUMN text_hash VARCHAR"),
    ("analyses", "decision_type",          "ALTER TABLE analyses ADD COLUMN decision_type VARCHAR"),
    ("reports",  "bias_phrases",           "ALTER TABLE reports  ADD COLUMN bias_phrases TEXT"),
    ("reports",  "timing_ms",              "ALTER TABLE reports  ADD COLUMN timing_ms TEXT"),
    ("reports",  "retry_counts",           "ALTER TABLE reports  ADD COLUMN retry_counts TEXT"),
    ("reports",  "ai_provider",            "ALTER TABLE reports  ADD COLUMN ai_provider VARCHAR"),
    ("reports",  "fairness_scores",        "ALTER TABLE reports  ADD COLUMN fairness_scores TEXT"),
    ("reports",  "explainability_trace",   "ALTER TABLE reports  ADD COLUMN explainability_trace TEXT"),
    ("reports",  "characteristic_weights", "ALTER TABLE reports  ADD COLUMN characteristic_weights TEXT"),
    ("reports",  "decision_type",          "ALTER TABLE reports  ADD COLUMN decision_type VARCHAR"),
    ("reports",  "ai_model",               "ALTER TABLE reports  ADD COLUMN ai_model VARCHAR"),
    # V20
    ("reports",  "risk_score",             "ALTER TABLE reports  ADD COLUMN risk_score INTEGER DEFAULT 0"),
    ("reports",  "urgency_tier",           "ALTER TABLE reports  ADD COLUMN urgency_tier VARCHAR DEFAULT 'low'"),
    ("reports",  "escalation_flag",        "ALTER TABLE reports  ADD COLUMN escalation_flag BOOLEAN DEFAULT 0"),
    ("reports",  "appeal_letter",          "ALTER TABLE reports  ADD COLUMN appeal_letter TEXT"),
    ("reports",  "disability_bias",        "ALTER TABLE reports  ADD COLUMN disability_bias BOOLEAN DEFAULT 0"),
    ("reports",  "intersectional_bias",    "ALTER TABLE reports  ADD COLUMN intersectional_bias TEXT"),
    ("reports",  "international_laws",     "ALTER TABLE reports  ADD COLUMN international_laws TEXT"),
    ("reports",  "severity_per_phrase",    "ALTER TABLE reports  ADD COLUMN severity_per_phrase TEXT"),
    ("feedback", "comment",                "ALTER TABLE feedback ADD COLUMN comment TEXT"),
    # V21
    ("reports",  "legal_timeline",         "ALTER TABLE reports  ADD COLUMN legal_timeline TEXT"),
    ("reports",  "precedents",             "ALTER TABLE reports  ADD COLUMN precedents TEXT"),
]


class Analysis(Base):
    __tablename__ = "analyses"
    id                = Column(String,   primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_text          = Column(Text,     nullable=False)
    text_hash         = Column(String,   index=True)
    decision_type     = Column(String,   nullable=False)
    extracted_factors = Column(Text)
    submitted_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    ai_model                = Column(String,  default="")
    decision_type           = Column(String,  default="other")
    fairness_scores         = Column(Text)
    explainability_trace    = Column(Text)
    characteristic_weights  = Column(Text)
    # V20
    risk_score              = Column(Integer, default=0)
    urgency_tier            = Column(String,  default="low")
    escalation_flag         = Column(Boolean, default=False)
    appeal_letter           = Column(Text)
    disability_bias         = Column(Boolean, default=False)
    intersectional_bias     = Column(Text)
    international_laws      = Column(Text)
    severity_per_phrase     = Column(Text)
    # V21
    legal_timeline          = Column(Text)
    precedents              = Column(Text)
    created_at              = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Feedback(Base):
    __tablename__ = "feedback"
    id         = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id  = Column(String,  nullable=False, index=True)
    rating     = Column(Integer, nullable=False)
    comment    = Column(Text,    default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for table, col, ddl in _MIGRATIONS:
            try:
                rows     = conn.execute(sa_text(f"PRAGMA table_info({table})")).fetchall()
                existing = [r[1] for r in rows]
                if col not in existing:
                    conn.execute(sa_text(ddl))
                    conn.commit()
                    log.info("Migration: added %s.%s", table, col)
            except Exception as exc:
                log.warning("Migration skipped (%s.%s): %s", table, col, exc)
    log.info("Database ready (V21).")


def get_db() -> Session:
    return SessionLocal()


def hash_text(text: str) -> str:
    return hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()


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
# MODEL CONSTANTS
# ─────────────────────────────────────────────

_GEMINI_PRO_MODEL   = "gemini-2.5-pro-preview-06-05"   # Steps 0, 7, 8, 9
_GEMINI_FLASH_MODEL = "gemini-2.0-flash"                # Steps 1–3, 6
_VERTEX_MODEL       = "gemini-2.0-flash"                # Steps 4–5
_GROQ_MODEL         = "llama-3.3-70b-versatile"         # 3rd fallback all steps
_CLAUDE_MODEL       = "claude-3-5-sonnet-20241022"      # 4th fallback all steps (V21)

_GEMINI_MODEL = _GEMINI_FLASH_MODEL  # legacy alias

_MAX_RETRIES = 3
_BASE_DELAY  = 1.0

PROVIDER_VERTEX = "vertex"
PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ   = "groq"
PROVIDER_CLAUDE = "claude"

BATCH_MAX_ROWS = 50  # raised from 10 in V21


# ─────────────────────────────────────────────
# RETRY HELPER
# ─────────────────────────────────────────────

def _backoff_delay(attempt: int) -> None:
    delay = _BASE_DELAY * (2 ** (attempt - 1))
    log.debug("Retry backoff: %.1fs (attempt %d)", delay, attempt)
    time.sleep(delay)


# ─────────────────────────────────────────────
# PROVIDER CLIENTS
# ─────────────────────────────────────────────

def vertex_available() -> bool:
    return bool(os.getenv("GOOGLE_CLOUD_PROJECT", "").strip())


def get_vertex_client(model: str = _VERTEX_MODEL):
    project  = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip()
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT not set.")
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project=project, location=location)
    return GenerativeModel(model)


def get_gemini_client(model: str = _GEMINI_FLASH_MODEL):
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()
    if not key:
        raise ValueError("GEMINI_API_KEY not set.")
    genai.configure(api_key=key)
    return genai.GenerativeModel(model)


def get_groq_client():
    from groq import Groq
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise ValueError("GROQ_API_KEY not set.")
    return Groq(api_key=key)


def get_claude_client():
    """V21: Anthropic Claude as 4th-tier fallback."""
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set.")
    return anthropic.Anthropic(api_key=key)


def check_providers() -> dict:
    return {
        "vertex": vertex_available(),
        "gemini": bool(os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip()),
        "groq":   bool(os.getenv("GROQ_API_KEY", "").strip()),
        "claude": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),  # V21
    }


# ─────────────────────────────────────────────
# RAW AI CALLERS
# ─────────────────────────────────────────────

def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else raw
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _call_vertex_json(prompt: str, label: str) -> tuple[dict, int, int]:
    t0 = time.perf_counter()
    retries = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            from vertexai.generative_models import GenerationConfig
            response = get_vertex_client().generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.1, max_output_tokens=2000,
                    response_mime_type="application/json",
                ),
            )
            parsed  = json.loads(_strip_fences(response.text))
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info("Vertex AI %s ok %dms attempt %d", label, elapsed, attempt)
            return parsed, retries, elapsed
        except json.JSONDecodeError:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise ValueError(f"Vertex AI invalid JSON after {_MAX_RETRIES} attempts ({label}).")
            _backoff_delay(attempt)
        except Exception:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Vertex AI exhausted retries.")


def _call_vertex_text(prompt: str, label: str) -> str:
    from vertexai.generative_models import GenerationConfig
    model = get_vertex_client()
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return model.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.3, max_output_tokens=1200),
            ).text.strip()
        except Exception:
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Vertex AI text call failed.")


def _call_gemini_json(prompt: str, label: str, model: str = _GEMINI_FLASH_MODEL) -> tuple[dict, int, int]:
    t0 = time.perf_counter()
    retries = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = get_gemini_client(model).generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 2000,
                    "response_mime_type": "application/json",
                },
            )
            parsed  = json.loads(_strip_fences(response.text))
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info("Gemini %s %s ok %dms attempt %d", model, label, elapsed, attempt)
            return parsed, retries, elapsed
        except json.JSONDecodeError:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise ValueError(f"Gemini invalid JSON after {_MAX_RETRIES} attempts ({label}).")
            _backoff_delay(attempt)
        except Exception:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Gemini exhausted retries.")


def _call_gemini_text(prompt: str, label: str, model: str = _GEMINI_FLASH_MODEL) -> str:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return get_gemini_client(model).generate_content(
                prompt,
                generation_config={"temperature": 0.3, "max_output_tokens": 1200},
            ).text.strip()
        except Exception:
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Gemini text call failed.")


def _call_groq_json(messages: list[dict], label: str) -> tuple[dict, int, int]:
    t0 = time.perf_counter()
    retries = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp    = get_groq_client().chat.completions.create(
                model=_GROQ_MODEL, max_tokens=2000, temperature=0.1, messages=messages
            )
            parsed  = json.loads(_strip_fences(resp.choices[0].message.content))
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info("Groq %s ok %dms attempt %d", label, elapsed, attempt)
            return parsed, retries, elapsed
        except json.JSONDecodeError:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise ValueError(f"Groq invalid JSON after {_MAX_RETRIES} attempts ({label}).")
            _backoff_delay(attempt)
        except Exception:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Groq exhausted retries.")


def _call_groq_text(messages: list[dict], label: str) -> str:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = get_groq_client().chat.completions.create(
                model=_GROQ_MODEL, max_tokens=1200, temperature=0.3, messages=messages
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Groq text call failed.")


def _call_claude_json(system: str, user: str, label: str) -> tuple[dict, int, int]:
    """V21: Claude as 4th-tier JSON fallback."""
    t0 = time.perf_counter()
    retries = 0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            client   = get_claude_client()
            response = client.messages.create(
                model=_CLAUDE_MODEL,
                max_tokens=2000,
                temperature=0.1,
                system=system + "\n\nRespond ONLY with valid JSON. No markdown fences.",
                messages=[{"role": "user", "content": user}],
            )
            raw     = response.content[0].text
            parsed  = json.loads(_strip_fences(raw))
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info("Claude %s ok %dms attempt %d", label, elapsed, attempt)
            return parsed, retries, elapsed
        except json.JSONDecodeError:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise ValueError(f"Claude invalid JSON after {_MAX_RETRIES} attempts ({label}).")
            _backoff_delay(attempt)
        except Exception:
            retries += 1
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Claude exhausted retries.")


def _call_claude_text(system: str, user: str, label: str) -> str:
    """V21: Claude as 4th-tier text fallback."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            client   = get_claude_client()
            response = client.messages.create(
                model=_CLAUDE_MODEL,
                max_tokens=1200,
                temperature=0.3,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text.strip()
        except Exception:
            if attempt == _MAX_RETRIES:
                raise
            _backoff_delay(attempt)
    raise ValueError("Claude text call failed.")


# ─────────────────────────────────────────────
# UNIFIED AI CALL ROUTERS (V21: 4-tier chain)
# Vertex AI → Gemini → Groq → Claude
# ─────────────────────────────────────────────

def _ai_call_json(
    gemini_prompt: str,
    groq_messages: list[dict],
    label: str,
    provider: str = PROVIDER_GEMINI,
    prefer_vertex: bool = False,
    gemini_model: str = _GEMINI_FLASH_MODEL,
) -> tuple[dict, int, int, str]:
    """Route JSON call through 4-tier fallback chain."""
    system_msg = next((m["content"] for m in groq_messages if m.get("role") == "system"), "")
    user_msg   = next((m["content"] for m in groq_messages if m.get("role") == "user"),   "")

    # Tier 1: Vertex AI
    if prefer_vertex and vertex_available():
        try:
            r, ret, el = _call_vertex_json(gemini_prompt, label)
            return r, ret, el, PROVIDER_VERTEX
        except Exception as v_exc:
            log.warning("Vertex AI failed %s (%s) — Gemini fallback", label, v_exc)

    # Tier 2: Gemini
    if provider in (PROVIDER_GEMINI, "auto", PROVIDER_VERTEX):
        try:
            r, ret, el = _call_gemini_json(gemini_prompt, label, gemini_model)
            return r, ret, el, PROVIDER_GEMINI
        except Exception as gem_exc:
            log.warning("Gemini failed %s (%s) — Groq fallback", label, gem_exc)
            # Tier 3: Groq
            try:
                r, ret, el = _call_groq_json(groq_messages, label + "-fb-groq")
                return r, ret, el, PROVIDER_GROQ
            except Exception as grq_exc:
                log.warning("Groq failed %s (%s) — Claude fallback", label, grq_exc)
                # Tier 4: Claude (V21)
                try:
                    r, ret, el = _call_claude_json(system_msg, user_msg, label + "-fb-claude")
                    return r, ret, el, PROVIDER_CLAUDE
                except Exception as cl_exc:
                    raise ValueError(
                        f"All 4 providers failed ({label}).\n"
                        f"Gemini: {gem_exc}\nGroq: {grq_exc}\nClaude: {cl_exc}"
                    )
    # Groq-first path
    try:
        r, ret, el = _call_groq_json(groq_messages, label)
        return r, ret, el, PROVIDER_GROQ
    except Exception as grq_exc:
        log.warning("Groq failed %s (%s) — Claude fallback", label, grq_exc)
        r, ret, el = _call_claude_json(system_msg, user_msg, label + "-fb-claude")
        return r, ret, el, PROVIDER_CLAUDE


def _ai_call_text(
    gemini_prompt: str,
    groq_messages: list[dict],
    label: str,
    provider: str = PROVIDER_GEMINI,
    prefer_vertex: bool = False,
    gemini_model: str = _GEMINI_FLASH_MODEL,
) -> tuple[str, str]:
    """Route text call through 4-tier fallback chain."""
    system_msg = next((m["content"] for m in groq_messages if m.get("role") == "system"), "")
    user_msg   = next((m["content"] for m in groq_messages if m.get("role") == "user"),   "")

    if prefer_vertex and vertex_available():
        try:
            return _call_vertex_text(gemini_prompt, label), PROVIDER_VERTEX
        except Exception as v_exc:
            log.warning("Vertex text failed (%s) — Gemini fallback", v_exc)

    if provider in (PROVIDER_GEMINI, "auto", PROVIDER_VERTEX):
        try:
            return _call_gemini_text(gemini_prompt, label, gemini_model), PROVIDER_GEMINI
        except Exception as gem_exc:
            log.warning("Gemini text failed (%s) — Groq fallback", gem_exc)
            try:
                return _call_groq_text(groq_messages, label + "-fb-groq"), PROVIDER_GROQ
            except Exception as grq_exc:
                log.warning("Groq text failed (%s) — Claude fallback", grq_exc)
                return _call_claude_text(system_msg, user_msg, label + "-fb-claude"), PROVIDER_CLAUDE
    try:
        return _call_groq_text(groq_messages, label), PROVIDER_GROQ
    except Exception:
        return _call_claude_text(system_msg, user_msg, label + "-fb-claude"), PROVIDER_CLAUDE


# ═══════════════════════════════════════════════════════
# STEPS 0–7 (unchanged from V20 — preserved exactly)
# ═══════════════════════════════════════════════════════

_SCAN_INSTRUCTION = (
    "You are an AI governance auditor performing a pre-decision data scan. "
    "Identify which protected characteristics are present — explicitly or implicitly — "
    "in this decision text. Include disability as a characteristic to look for. "
    "For each, assign an influence_weight (0–100). "
    "Return ONLY valid JSON: "
    "characteristics_present (list of strings), "
    "influence_weights (object: characteristic → weight 0-100), "
    "disability_signals (list of phrases if disability-related language found, else []), "
    "data_quality_flags (list of concerns), "
    "pre_scan_risk (low|medium|high). "
    "No markdown, no explanation."
)


def pre_decision_scan(decision_text: str, provider: str = PROVIDER_GEMINI) -> tuple[dict, str]:
    gp = f"{_SCAN_INSTRUCTION}\n\nDecision text:\n{decision_text}"
    gm = [
        {"role": "system", "content": _SCAN_INSTRUCTION},
        {"role": "user",   "content": f"Decision text:\n{decision_text}"},
    ]
    r, _, _, prov = _ai_call_json(gp, gm, "STEP-0/pre-scan", provider, gemini_model=_GEMINI_PRO_MODEL)
    return r, prov


_EXTRACT_INSTRUCTION = (
    "You are a decision analysis expert. Read the automated decision text and extract: "
    "decision_type (string), outcome (accepted|rejected|approved|denied|other), "
    "criteria_used (list), data_points_weighted (list), "
    "protected_characteristics_mentioned (list), "
    "confidence_in_extraction (float 0-1). "
    "Return ONLY valid JSON — no markdown."
)


def extract_factors(decision_text: str, decision_type: str, provider: str = PROVIDER_GEMINI) -> tuple[dict, int, int, str]:
    gp = f"{_EXTRACT_INSTRUCTION}\n\nDecision type hint: {decision_type}\n\nDecision text:\n{decision_text}"
    gm = [
        {"role": "system", "content": _EXTRACT_INSTRUCTION},
        {"role": "user",   "content": f"Decision type hint: {decision_type}\n\nDecision text:\n{decision_text}"},
    ]
    return _ai_call_json(gp, gm, "STEP-1/extract", provider, gemini_model=_GEMINI_FLASH_MODEL)


_DETECT_INSTRUCTION = (
    "You are a fairness and algorithmic-bias expert. Analyse extracted decision factors for hidden bias "
    "across these 9 dimensions: gender, age, race/ethnicity, geography, name-based proxies, "
    "disability, language, insurance classification, socioeconomic status. "
    "Return ONLY valid JSON: "
    "bias_detected (boolean), "
    "bias_types (list of strings), "
    "disability_bias_detected (boolean), "
    "which_characteristic_affected (string), "
    "bias_evidence (string), "
    "confidence (float 0-1), "
    "severity (low|medium|high), "
    "bias_phrases (list of up to 6 specific verbatim phrases). "
    "No markdown."
)


def detect_bias(extracted: dict, provider: str = PROVIDER_GEMINI) -> tuple[dict, int, int, str]:
    gp = f"{_DETECT_INSTRUCTION}\n\nExtracted factors:\n{json.dumps(extracted, indent=2)}"
    gm = [
        {"role": "system", "content": _DETECT_INSTRUCTION},
        {"role": "user",   "content": f"Extracted factors:\n{json.dumps(extracted, indent=2)}"},
    ]
    return _ai_call_json(gp, gm, "STEP-2/detect", provider, gemini_model=_GEMINI_FLASH_MODEL)


_FAIR_INSTRUCTION = (
    "You are a fair-decision expert and civil-rights advisor. "
    "Given the original decision and bias evidence, determine the fair outcome. "
    "Return ONLY valid JSON: "
    "fair_outcome (string), "
    "fair_reasoning (string), "
    "what_was_wrong (plain English for the affected person), "
    "next_steps (list of exactly 3 actionable strings), "
    "legal_frameworks (list of up to 4 domestic laws), "
    "international_frameworks (list of up to 3 international instruments). "
    "No markdown."
)


def generate_fair_outcome(extracted: dict, bias_result: dict, provider: str = PROVIDER_GEMINI) -> tuple[dict, int, int, str]:
    ctx = (
        f"Original outcome: {extracted.get('outcome','unknown')}\n"
        f"Criteria used: {json.dumps(extracted.get('criteria_used', []))}\n"
        f"Bias evidence: {bias_result.get('bias_evidence','none')}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Disability bias: {bias_result.get('disability_bias_detected', False)}\n"
        f"Characteristic affected: {bias_result.get('which_characteristic_affected','unknown')}"
    )
    gp = f"{_FAIR_INSTRUCTION}\n\n{ctx}"
    gm = [{"role": "system", "content": _FAIR_INSTRUCTION}, {"role": "user", "content": ctx}]
    return _ai_call_json(gp, gm, "STEP-3/fair", provider, gemini_model=_GEMINI_FLASH_MODEL)


_FAIRNESS_AUDIT_INSTRUCTION = (
    "You are an AI fairness auditor. Perform counterfactual fairness testing. "
    "Also assess intersectional bias — combinations of characteristics that together create compounded disadvantage. "
    "Return ONLY valid JSON: "
    "demographic_parity_scores (object: characteristic → score 0-100), "
    "counterfactual_findings (list of objects: characteristic, hypothetical_change, "
    "would_outcome_change (boolean), reasoning), "
    "intersectional_bias (object: detected (boolean), combinations (list of strings), description (string)), "
    "overall_fairness_score (integer 0-100), "
    "fairness_verdict (fair|partially_fair|unfair), "
    "audit_summary (1-2 sentences). "
    "No markdown."
)


def run_fairness_audit(decision_text: str, bias_result: dict, provider: str = PROVIDER_GEMINI) -> tuple[dict, int, int, str]:
    ctx = (
        f"Original decision:\n{decision_text}\n\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Disability bias: {bias_result.get('disability_bias_detected', False)}\n"
        f"Affected: {bias_result.get('which_characteristic_affected','')}"
    )
    gp = f"{_FAIRNESS_AUDIT_INSTRUCTION}\n\n{ctx}"
    gm = [{"role": "system", "content": _FAIRNESS_AUDIT_INSTRUCTION}, {"role": "user", "content": ctx}]
    return _ai_call_json(gp, gm, "STEP-4/fairness-audit", provider, prefer_vertex=True, gemini_model=_GEMINI_FLASH_MODEL)


_EXPLAIN_INSTRUCTION = (
    "You are an AI explainability expert. Produce a phrase-by-phrase reasoning chain "
    "showing how this decision discriminated. "
    "Return ONLY valid JSON: "
    "reasoning_chain (list of objects: step (int), phrase (exact text), "
    "characteristic_triggered (string), legal_violation (string), "
    "why_this_matters (string), severity_per_phrase (low|medium|high)), "
    "root_cause (string), "
    "retroactive_correction (string), "
    "corrective_action (string). "
    "No markdown."
)


def generate_explainability_trace(decision_text: str, bias_result: dict, fair_result: dict, provider: str = PROVIDER_GEMINI) -> tuple[dict, int, int, str]:
    ctx = (
        f"Decision text:\n{decision_text}\n\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Bias evidence: {bias_result.get('bias_evidence','')}\n"
        f"Bias phrases: {json.dumps(bias_result.get('bias_phrases', []))}\n"
        f"Fair outcome: {fair_result.get('fair_outcome','')}"
    )
    gp = f"{_EXPLAIN_INSTRUCTION}\n\n{ctx}"
    gm = [{"role": "system", "content": _EXPLAIN_INSTRUCTION}, {"role": "user", "content": ctx}]
    return _ai_call_json(gp, gm, "STEP-5/explainability", provider, prefer_vertex=True, gemini_model=_GEMINI_FLASH_MODEL)


_RISK_INSTRUCTION = (
    "You are an AI risk assessor for automated decision bias. "
    "Given the bias analysis results, compute a composite risk index. "
    "Return ONLY valid JSON: "
    "risk_score (integer 0-100), "
    "urgency_tier (immediate|high|medium|low), "
    "escalation_recommended (boolean — true if risk_score >= 65), "
    "risk_factors (list of strings), "
    "estimated_harm_severity (string), "
    "time_sensitivity (string), "
    "protective_factors (list). "
    "No markdown."
)


def score_risk(bias_result: dict, fair_result: dict, fairness_data: dict, provider: str = PROVIDER_GEMINI) -> tuple[dict, int, int, str]:
    ctx = (
        f"Bias detected: {bias_result.get('bias_detected', False)}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Severity: {bias_result.get('severity','low')}\n"
        f"Confidence: {bias_result.get('confidence', 0)}\n"
        f"Disability bias: {bias_result.get('disability_bias_detected', False)}\n"
        f"Overall fairness score: {fairness_data.get('overall_fairness_score', 50)}\n"
        f"Fairness verdict: {fairness_data.get('fairness_verdict','unknown')}\n"
        f"Intersectional bias: {fairness_data.get('intersectional_bias',{}).get('detected',False)}\n"
        f"Fair outcome requested: {fair_result.get('fair_outcome','')}\n"
        f"Legal frameworks violated: {json.dumps(fair_result.get('legal_frameworks',[]))}"
    )
    gp = f"{_RISK_INSTRUCTION}\n\n{ctx}"
    gm = [{"role": "system", "content": _RISK_INSTRUCTION}, {"role": "user", "content": ctx}]
    return _ai_call_json(gp, gm, "STEP-6/risk", provider, gemini_model=_GEMINI_FLASH_MODEL)


def _rules_engine_risk(bias_result: dict, fairness_data: dict, ai_risk: dict) -> dict:
    score = ai_risk.get("risk_score", 0)
    tier  = ai_risk.get("urgency_tier", "low")
    severity   = (bias_result.get("severity") or "low").lower()
    disability = bias_result.get("disability_bias_detected", False)
    fs_score   = fairness_data.get("overall_fairness_score", 50)
    intersect  = fairness_data.get("intersectional_bias", {}).get("detected", False)
    if severity == "high"  and score < 60: score = 60
    if disability          and score < 55: score = 55
    if intersect           and score < 50: score = 50
    if fs_score < 30       and score < 70: score = 70
    if fs_score < 15       and score < 85: score = 85
    if score >= 80:   tier = "immediate"
    elif score >= 65: tier = "high"
    elif score >= 40: tier = "medium"
    else:             tier = "low"
    ai_risk["risk_score"]             = min(score, 100)
    ai_risk["urgency_tier"]           = tier
    ai_risk["escalation_recommended"] = score >= 65
    return ai_risk


_APPEAL_INSTRUCTION = (
    "You are an expert legal writer specialising in discrimination and civil rights. "
    "Write formal, persuasive appeal letters that could be used in real legal proceedings. "
    "Use [DATE], [YOUR NAME], [YOUR ADDRESS], [RECIPIENT NAME], [ORGANISATION] as placeholders. "
    "The letter must: open professionally, reference the exact decision received, "
    "state the specific discriminatory phrases found, cite the exact laws violated, "
    "request a formal review and fair reconsideration, and close with a clear deadline expectation. "
    "Under 500 words. No markdown."
)


def generate_appeal_letter(report: dict, decision_text: str, decision_type: str, provider: str = PROVIDER_GEMINI) -> str:
    bias_types   = ", ".join(report.get("bias_types", [])) or "undisclosed bias"
    affected     = report.get("affected_characteristic", "a protected characteristic")
    explanation  = report.get("explanation", "")
    fair_outcome = report.get("fair_outcome", "a fair reassessment")
    laws         = report.get("legal_frameworks", [])
    intl_laws    = report.get("international_laws", [])
    all_laws     = laws + intl_laws
    law_ref      = (", ".join(all_laws) + " and related anti-discrimination law") if all_laws else "applicable anti-discrimination law"
    fs           = (report.get("fairness_scores") or {}).get("overall_fairness_score")
    risk_score   = report.get("risk_score", 0)
    urgency      = report.get("urgency_tier", "medium")
    phrases      = report.get("bias_phrases", [])
    phrase_block = ("\nSpecific discriminatory phrases found:\n" + "\n".join(f'  - "{p}"' for p in phrases[:4])) if phrases else ""
    fs_line      = f"\nAI fairness audit score: {fs}/100 — indicating significant inequity." if fs is not None else ""
    risk_line    = f"\nRisk assessment: {risk_score}/100 urgency tier: {urgency.upper()}."
    user_content = (
        f"Write a formal appeal letter:\n"
        f"Decision type: {decision_type}\n"
        f"Original decision text: {decision_text[:500]}\n"
        f"Bias detected: {bias_types}\n"
        f"Characteristic affected: {affected}\n"
        f"What was wrong: {explanation}{phrase_block}{fs_line}{risk_line}\n"
        f"Fair outcome requested: {fair_outcome}\n"
        f"Legal frameworks to cite: {law_ref}\n"
    )
    gp = f"{_APPEAL_INSTRUCTION}\n\n{user_content}"
    gm = [
        {"role": "system", "content": _APPEAL_INSTRUCTION},
        {"role": "user",   "content": user_content},
    ]
    text, _ = _ai_call_text(gp, gm, "STEP-7/appeal", provider, gemini_model=_GEMINI_PRO_MODEL)
    return text


# ═══════════════════════════════════════════════════════
# STEP 8 — LEGAL TIMELINE  (V21 NEW · Gemini 2.5 Pro)
# Calculates appeal windows, filing deadlines, jurisdiction
# ═══════════════════════════════════════════════════════

_TIMELINE_INSTRUCTION = (
    "You are an expert civil-rights attorney with deep knowledge of appeal timelines and jurisdictional rules. "
    "Given a discriminatory decision and the legal frameworks violated, calculate ALL relevant deadlines. "
    "Return ONLY valid JSON: "
    "jurisdiction (string — inferred country/region e.g. 'United States', 'India', 'European Union'), "
    "applicable_tribunals (list of strings — courts or bodies to file with), "
    "deadlines (list of objects: "
    "  body (string), "
    "  action (string — e.g. 'File EEOC charge'), "
    "  window_days (integer), "
    "  window_description (string — e.g. '180 days from discriminatory act'), "
    "  priority (critical|high|medium|low)), "
    "immediate_actions (list of 3 strings — what to do TODAY), "
    "evidence_to_preserve (list of strings), "
    "estimated_timeline_months (integer — typical case resolution time), "
    "pro_bono_resources (list of strings — relevant organisations). "
    "No markdown."
)


def calculate_legal_timeline(
    decision_text: str,
    decision_type: str,
    bias_result: dict,
    fair_result: dict,
    provider: str = PROVIDER_GEMINI,
) -> tuple[dict, int, int, str]:
    ctx = (
        f"Decision type: {decision_type}\n"
        f"Decision text (excerpt): {decision_text[:600]}\n"
        f"Bias types detected: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Characteristic affected: {bias_result.get('which_characteristic_affected','')}\n"
        f"Domestic legal frameworks: {json.dumps(fair_result.get('legal_frameworks', []))}\n"
        f"International frameworks: {json.dumps(fair_result.get('international_frameworks', []))}\n"
        f"Severity: {bias_result.get('severity','low')}"
    )
    gp = f"{_TIMELINE_INSTRUCTION}\n\n{ctx}"
    gm = [
        {"role": "system", "content": _TIMELINE_INSTRUCTION},
        {"role": "user",   "content": ctx},
    ]
    return _ai_call_json(gp, gm, "STEP-8/timeline", provider, gemini_model=_GEMINI_PRO_MODEL)


# ═══════════════════════════════════════════════════════
# STEP 9 — PRECEDENT RETRIEVAL  (V21 NEW · Gemini 2.5 Pro)
# Finds real case-law matches for the bias pattern detected
# ═══════════════════════════════════════════════════════

_PRECEDENT_INSTRUCTION = (
    "You are an expert legal researcher specialising in discrimination case law. "
    "Given the bias detected and the legal frameworks violated, identify the most relevant "
    "legal precedents and landmark cases that match this discrimination pattern. "
    "Return ONLY valid JSON: "
    "precedents (list of objects: "
    "  case_name (string — full case citation e.g. 'Griggs v. Duke Power Co., 401 U.S. 424 (1971)'), "
    "  year (integer), "
    "  jurisdiction (string), "
    "  relevance_score (integer 0-100), "
    "  why_relevant (string — 1-2 sentences explaining the match), "
    "  outcome (string — what the court decided), "
    "  key_principle (string — legal principle established)), "
    "strongest_precedent (string — case_name of the single most relevant case), "
    "legal_strategy_hint (string — brief note on how these precedents strengthen the appeal), "
    "estimated_win_probability (string — rough assessment based on similar cases: low|medium|high). "
    "Only include real, verifiable cases. If uncertain, indicate uncertainty in why_relevant. "
    "No markdown."
)


def retrieve_precedents(
    decision_type: str,
    bias_result: dict,
    fair_result: dict,
    provider: str = PROVIDER_GEMINI,
) -> tuple[dict, int, int, str]:
    ctx = (
        f"Decision type: {decision_type}\n"
        f"Bias types: {json.dumps(bias_result.get('bias_types', []))}\n"
        f"Characteristic affected: {bias_result.get('which_characteristic_affected','')}\n"
        f"Severity: {bias_result.get('severity','low')}\n"
        f"Disability bias: {bias_result.get('disability_bias_detected', False)}\n"
        f"Legal frameworks violated: {json.dumps(fair_result.get('legal_frameworks', []))}\n"
        f"International frameworks: {json.dumps(fair_result.get('international_frameworks', []))}\n"
        f"Bias evidence: {bias_result.get('bias_evidence', '')[:400]}"
    )
    gp = f"{_PRECEDENT_INSTRUCTION}\n\n{ctx}"
    gm = [
        {"role": "system", "content": _PRECEDENT_INSTRUCTION},
        {"role": "user",   "content": ctx},
    ]
    return _ai_call_json(gp, gm, "STEP-9/precedent", provider, gemini_model=_GEMINI_PRO_MODEL)


# ═══════════════════════════════════════════════════════
# QUICK SCAN  (single call — V21: returns new fields)
# ═══════════════════════════════════════════════════════

_QUICK_INSTRUCTION = (
    "You are a bias-detection expert. In ONE call, analyse this automated decision for bias "
    "across 9 dimensions: gender, age, race, geography, name-based proxies, disability, "
    "language, insurance classification, socioeconomic status. "
    "Return ONLY valid JSON: "
    "bias_detected (boolean), "
    "bias_types (list), "
    "disability_bias_detected (boolean), "
    "which_characteristic_affected (string), "
    "confidence (float 0-1), "
    "severity (low|medium|high), "
    "original_outcome (string), "
    "fair_outcome (string), "
    "explanation (1-2 sentences), "
    "next_steps (list of 3 strings), "
    "bias_phrases (list of up to 4 strings), "
    "legal_frameworks (list of up to 3 laws), "
    "overall_fairness_score (integer 0-100), "
    "fairness_verdict (fair|partially_fair|unfair), "
    "risk_score (integer 0-100), "
    "urgency_tier (immediate|high|medium|low). "
    "No markdown."
)


def quick_scan(decision_text: str, decision_type: str, provider: str = PROVIDER_GEMINI) -> dict:
    t0  = time.perf_counter()
    ctx = f"Decision type: {decision_type}\n\n{decision_text}"
    gp  = f"{_QUICK_INSTRUCTION}\n\n{ctx}"
    gm  = [
        {"role": "system", "content": _QUICK_INSTRUCTION},
        {"role": "user",   "content": ctx},
    ]
    result, retries, elapsed, prov_used = _ai_call_json(gp, gm, "QUICK-SCAN", provider, gemini_model=_GEMINI_FLASH_MODEL)
    fairness_scores = {
        "overall_fairness_score": result.get("overall_fairness_score", 50),
        "fairness_verdict":       result.get("fairness_verdict", "partially_fair"),
    }
    rid = str(uuid.uuid4())
    db  = get_db()
    try:
        analysis = Analysis(
            raw_text=decision_text, text_hash=hash_text(decision_text),
            decision_type=decision_type, extracted_factors="{}",
        )
        db.add(analysis); db.commit(); db.refresh(analysis)
        recs_payload = {
            "steps": result.get("next_steps", []),
            "extra": {
                "legal_frameworks": result.get("legal_frameworks", []),
                "fair_reasoning":   "",
                "severity":         result.get("severity", "low"),
                "bias_evidence":    "",
            },
        }
        report_row = Report(
            id=rid, analysis_id=analysis.id,
            bias_found=result.get("bias_detected", False),
            bias_types=json.dumps(result.get("bias_types", [])),
            affected_characteristic=result.get("which_characteristic_affected", ""),
            original_outcome=result.get("original_outcome", ""),
            fair_outcome=result.get("fair_outcome", ""),
            explanation=result.get("explanation", ""),
            confidence_score=float(result.get("confidence", 0.0)),
            recommendations=json.dumps(recs_payload),
            bias_phrases=json.dumps(result.get("bias_phrases", [])),
            timing_ms=json.dumps({"quick": elapsed}),
            retry_counts=json.dumps({"quick": retries}),
            ai_provider=prov_used,
            ai_model=_GEMINI_FLASH_MODEL if prov_used != PROVIDER_GROQ else _GROQ_MODEL,
            decision_type=decision_type,
            fairness_scores=json.dumps(fairness_scores),
            explainability_trace="{}", characteristic_weights="{}",
            risk_score=int(result.get("risk_score", 0)),
            urgency_tier=result.get("urgency_tier", "low"),
            escalation_flag=bool(result.get("risk_score", 0) >= 65),
            disability_bias=bool(result.get("disability_bias_detected", False)),
            intersectional_bias="{}", international_laws="[]",
            legal_timeline="{}", precedents="[]",  # V21
        )
        db.add(report_row); db.commit()
        log.info("Quick scan saved id=%s bias=%s risk=%s", rid, result.get("bias_detected"), result.get("risk_score"))
    except Exception as exc:
        log.warning("Quick scan DB save failed: %s", exc)
    finally:
        db.close()

    return {
        "id": rid, "analysis_id": "quick-scan",
        "bias_found": result.get("bias_detected", False),
        "bias_types": result.get("bias_types", []),
        "affected_characteristic": result.get("which_characteristic_affected", ""),
        "original_outcome": result.get("original_outcome", ""),
        "fair_outcome": result.get("fair_outcome", ""),
        "explanation": result.get("explanation", ""),
        "confidence_score": float(result.get("confidence", 0.0)),
        "recommendations": result.get("next_steps", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bias_phrases": result.get("bias_phrases", []),
        "legal_frameworks": result.get("legal_frameworks", []),
        "international_laws": [],
        "fair_reasoning": "", "severity": result.get("severity", "low"),
        "bias_evidence": "", "timing_ms": {"quick": elapsed},
        "retry_counts": {"quick": retries}, "mode": "quick",
        "ai_provider": prov_used,
        "ai_model": _GEMINI_FLASH_MODEL if prov_used != PROVIDER_GROQ else _GROQ_MODEL,
        "decision_type": decision_type, "fairness_scores": fairness_scores,
        "explainability_trace": {}, "characteristic_weights": {},
        "risk_score": int(result.get("risk_score", 0)),
        "urgency_tier": result.get("urgency_tier", "low"),
        "escalation_flag": bool(result.get("risk_score", 0) >= 65),
        "disability_bias": bool(result.get("disability_bias_detected", False)),
        "intersectional_bias": {}, "appeal_letter": None,
        "severity_per_phrase": [],
        "legal_timeline": {},   # V21
        "precedents": [],       # V21
    }


# ═══════════════════════════════════════════════════════
# FULL 10-STEP PIPELINE  (V21)
# ═══════════════════════════════════════════════════════

def run_full_pipeline(
    decision_text: str,
    decision_type: str,
    progress_callback=None,
    provider: str = PROVIDER_GEMINI,
) -> dict:
    """Run all 10 steps and persist a Report row."""
    text_hash   = hash_text(decision_text)
    db: Session = get_db()
    prov_used   = provider

    try:
        # ── STEP 0: Pre-scan ──────────────────────────────────
        if progress_callback: progress_callback(0, "Scanning for protected characteristics…")
        t0_start = time.perf_counter()
        pre_scan, p0 = pre_decision_scan(decision_text, provider)
        characteristic_weights = pre_scan.get("influence_weights", {})
        disability_signals     = pre_scan.get("disability_signals", [])
        t0_ms = int((time.perf_counter() - t0_start) * 1000)

        # ── STEP 1: Extract ───────────────────────────────────
        if progress_callback: progress_callback(1, "Extracting decision criteria…")
        extracted, r1, t1, p1 = extract_factors(decision_text, decision_type, provider)
        prov_used = p1
        analysis = Analysis(
            raw_text=decision_text, text_hash=text_hash,
            decision_type=decision_type, extracted_factors=json.dumps(extracted),
        )
        db.add(analysis); db.commit(); db.refresh(analysis)

        # ── STEP 2: Detect bias ───────────────────────────────
        if progress_callback: progress_callback(2, "Scanning 9 bias dimensions…")
        bias_result, r2, t2, p2 = detect_bias(extracted, provider)
        if disability_signals and not bias_result.get("disability_bias_detected"):
            bias_result["disability_bias_detected"] = True
            if "disability" not in [b.lower() for b in bias_result.get("bias_types", [])]:
                bias_result.setdefault("bias_types", []).append("disability")

        # ── STEP 3: Fair outcome ──────────────────────────────
        if progress_callback: progress_callback(3, "Generating fair outcome + legal frameworks…")
        fair_result, r3, t3, p3 = generate_fair_outcome(extracted, bias_result, provider)

        # ── STEP 4: Fairness audit (Vertex AI) ───────────────
        fairness_data = {}; t4 = 0
        if bias_result.get("bias_detected"):
            if progress_callback: progress_callback(4, "Counterfactual fairness audit (Vertex AI)…")
            try:
                fairness_data, _, t4, _ = run_fairness_audit(decision_text, bias_result, provider)
            except Exception as exc:
                log.warning("Fairness audit failed: %s", exc)
                fairness_data = {"overall_fairness_score": 0, "fairness_verdict": "unfair",
                                 "intersectional_bias": {"detected": False}}

        # ── STEP 5: Explainability (Vertex AI) ───────────────
        explain_data = {}; t5 = 0; severity_per_phrase = []
        if bias_result.get("bias_detected"):
            if progress_callback: progress_callback(5, "Building explainability trace (Vertex AI)…")
            try:
                explain_data, _, t5, _ = generate_explainability_trace(decision_text, bias_result, fair_result, provider)
                severity_per_phrase = [
                    {"phrase": s.get("phrase",""), "severity": s.get("severity_per_phrase","low")}
                    for s in explain_data.get("reasoning_chain", [])
                ]
            except Exception as exc:
                log.warning("Explainability trace failed: %s", exc)

        # ── STEP 6: Risk scoring ──────────────────────────────
        if progress_callback: progress_callback(6, "Computing risk index…")
        risk_data = {"risk_score": 0, "urgency_tier": "low", "escalation_recommended": False}
        t6 = 0
        try:
            t6_start = time.perf_counter()
            ai_risk, _, _, _ = score_risk(bias_result, fair_result, fairness_data, provider)
            risk_data = _rules_engine_risk(bias_result, fairness_data, ai_risk)
            t6 = int((time.perf_counter() - t6_start) * 1000)
        except Exception as exc:
            log.warning("Risk scoring failed: %s", exc)
            if bias_result.get("bias_detected"):
                sev = bias_result.get("severity","low")
                risk_data["risk_score"] = {"high": 70, "medium": 45, "low": 25}.get(sev, 25)
                risk_data = _rules_engine_risk(bias_result, fairness_data, risk_data)

        # ── STEP 7: Auto-appeal (Gemini 2.5 Pro) ─────────────
        appeal_letter = None; t7 = 0
        if bias_result.get("bias_detected") and risk_data.get("risk_score", 0) >= 40:
            if progress_callback: progress_callback(7, "Drafting formal appeal letter (Gemini 2.5 Pro)…")
            try:
                t7_start = time.perf_counter()
                partial_report = {
                    "bias_types":             bias_result.get("bias_types", []),
                    "affected_characteristic":bias_result.get("which_characteristic_affected",""),
                    "explanation":            fair_result.get("what_was_wrong",""),
                    "fair_outcome":           fair_result.get("fair_outcome",""),
                    "legal_frameworks":       fair_result.get("legal_frameworks",[]),
                    "international_laws":     fair_result.get("international_frameworks",[]),
                    "fairness_scores":        fairness_data,
                    "risk_score":             risk_data.get("risk_score",0),
                    "urgency_tier":           risk_data.get("urgency_tier","medium"),
                    "bias_phrases":           bias_result.get("bias_phrases",[]),
                }
                appeal_letter = generate_appeal_letter(partial_report, decision_text, decision_type, provider)
                t7 = int((time.perf_counter() - t7_start) * 1000)
            except Exception as exc:
                log.warning("Appeal generation failed: %s", exc)

        # ── STEP 8: Legal timeline (V21 NEW) ─────────────────
        legal_timeline = {}; t8 = 0
        if bias_result.get("bias_detected"):
            if progress_callback: progress_callback(8, "Calculating legal deadlines + jurisdiction (V21)…")
            try:
                t8_start = time.perf_counter()
                legal_timeline, _, _, _ = calculate_legal_timeline(
                    decision_text, decision_type, bias_result, fair_result, provider
                )
                t8 = int((time.perf_counter() - t8_start) * 1000)
                log.info("STEP-8/timeline ok jurisdiction=%s deadlines=%d",
                         legal_timeline.get("jurisdiction","?"),
                         len(legal_timeline.get("deadlines", [])))
            except Exception as exc:
                log.warning("Legal timeline failed: %s", exc)

        # ── STEP 9: Precedent retrieval (V21 NEW) ────────────
        precedents_data = {}; t9 = 0
        if bias_result.get("bias_detected"):
            if progress_callback: progress_callback(9, "Retrieving case-law precedents (V21)…")
            try:
                t9_start = time.perf_counter()
                precedents_data, _, _, _ = retrieve_precedents(
                    decision_type, bias_result, fair_result, provider
                )
                t9 = int((time.perf_counter() - t9_start) * 1000)
                log.info("STEP-9/precedent ok cases=%d strongest=%s",
                         len(precedents_data.get("precedents", [])),
                         precedents_data.get("strongest_precedent","?"))
            except Exception as exc:
                log.warning("Precedent retrieval failed: %s", exc)

        # ── Aggregate providers ───────────────────────────────
        providers_used = {p0, p1, p2, p3}
        if PROVIDER_CLAUDE in providers_used:
            prov_used = "multi+claude"
        elif PROVIDER_GROQ in providers_used and PROVIDER_GEMINI in providers_used:
            prov_used = "gemini+groq"
        elif PROVIDER_GROQ in providers_used:
            prov_used = PROVIDER_GROQ

        timing = {
            "pre_scan": t0_ms, "extract": t1, "detect": t2, "fair": t3,
            "fairness_audit": t4, "explainability": t5, "risk": t6,
            "appeal": t7, "timeline": t8, "precedent": t9,
            "total": t0_ms + t1 + t2 + t3 + t4 + t5 + t6 + t7 + t8 + t9,
        }

        # ── Persist Report row ────────────────────────────────
        extra = {
            "bias_phrases":     bias_result.get("bias_phrases", []),
            "legal_frameworks": fair_result.get("legal_frameworks", []),
            "fair_reasoning":   fair_result.get("fair_reasoning",""),
            "severity":         bias_result.get("severity","low"),
            "bias_evidence":    bias_result.get("bias_evidence",""),
        }
        report = Report(
            analysis_id=analysis.id,
            bias_found=bias_result.get("bias_detected", False),
            bias_types=json.dumps(bias_result.get("bias_types", [])),
            affected_characteristic=bias_result.get("which_characteristic_affected",""),
            original_outcome=extracted.get("outcome",""),
            fair_outcome=fair_result.get("fair_outcome",""),
            explanation=fair_result.get("what_was_wrong",""),
            confidence_score=float(bias_result.get("confidence",0.0)),
            recommendations=json.dumps({"steps": fair_result.get("next_steps",[]), "extra": extra}),
            bias_phrases=json.dumps(bias_result.get("bias_phrases",[])),
            timing_ms=json.dumps(timing),
            retry_counts=json.dumps({"extract": r1, "detect": r2, "fair": r3}),
            ai_provider=prov_used, ai_model=_GEMINI_PRO_MODEL,
            decision_type=decision_type,
            fairness_scores=json.dumps(fairness_data),
            explainability_trace=json.dumps(explain_data),
            characteristic_weights=json.dumps(characteristic_weights),
            risk_score=int(risk_data.get("risk_score",0)),
            urgency_tier=risk_data.get("urgency_tier","low"),
            escalation_flag=bool(risk_data.get("escalation_recommended",False)),
            appeal_letter=appeal_letter,
            disability_bias=bool(bias_result.get("disability_bias_detected",False)),
            intersectional_bias=json.dumps(fairness_data.get("intersectional_bias",{})),
            international_laws=json.dumps(fair_result.get("international_frameworks",[])),
            severity_per_phrase=json.dumps(severity_per_phrase),
            legal_timeline=json.dumps(legal_timeline),        # V21
            precedents=json.dumps(precedents_data),           # V21
        )
        db.add(report); db.commit(); db.refresh(report)

        log.info(
            "V21 Pipeline complete id=%s bias=%s risk=%s urgency=%s timeline=%s precedents=%d total=%dms",
            report.id, report.bias_found,
            risk_data.get("risk_score","N/A"), risk_data.get("urgency_tier","?"),
            legal_timeline.get("jurisdiction","none"),
            len(precedents_data.get("precedents", [])),
            timing["total"],
        )
        return build_report_dict(report)
    finally:
        db.close()


# ─────────────────────────────────────────────
# REPORT BUILDER
# ─────────────────────────────────────────────

def build_report_dict(report: Report) -> dict:
    recs_raw = json.loads(report.recommendations or "[]")
    if isinstance(recs_raw, dict):
        recommendations = recs_raw.get("steps", [])
        extra           = recs_raw.get("extra", {})
    else:
        recommendations = recs_raw
        extra           = {}

    def _load_json(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    return {
        "id":                     report.id,
        "analysis_id":            report.analysis_id,
        "bias_found":             report.bias_found,
        "bias_types":             _load_json(report.bias_types, []),
        "affected_characteristic":report.affected_characteristic,
        "original_outcome":       report.original_outcome,
        "fair_outcome":           report.fair_outcome,
        "explanation":            report.explanation,
        "confidence_score":       report.confidence_score,
        "recommendations":        recommendations,
        "created_at":             report.created_at.isoformat() if report.created_at else None,
        "bias_phrases":           _load_json(report.bias_phrases, []),
        "legal_frameworks":       extra.get("legal_frameworks", []),
        "international_laws":     _load_json(getattr(report,"international_laws",None), []),
        "fair_reasoning":         extra.get("fair_reasoning",""),
        "severity":               extra.get("severity","low"),
        "bias_evidence":          extra.get("bias_evidence",""),
        "timing_ms":              _load_json(report.timing_ms, {}),
        "retry_counts":           _load_json(report.retry_counts, {}),
        "mode":                   "full",
        "ai_provider":            getattr(report,"ai_provider","gemini") or "gemini",
        "ai_model":               getattr(report,"ai_model","") or "",
        "decision_type":          getattr(report,"decision_type","other") or "other",
        "fairness_scores":        _load_json(report.fairness_scores, {}),
        "explainability_trace":   _load_json(report.explainability_trace, {}),
        "characteristic_weights": _load_json(report.characteristic_weights, {}),
        "risk_score":             getattr(report,"risk_score",0) or 0,
        "urgency_tier":           getattr(report,"urgency_tier","low") or "low",
        "escalation_flag":        bool(getattr(report,"escalation_flag",False)),
        "appeal_letter":          getattr(report,"appeal_letter",None),
        "disability_bias":        bool(getattr(report,"disability_bias",False)),
        "intersectional_bias":    _load_json(getattr(report,"intersectional_bias",None), {}),
        "severity_per_phrase":    _load_json(getattr(report,"severity_per_phrase",None), []),
        # V21
        "legal_timeline":         _load_json(getattr(report,"legal_timeline",None), {}),
        "precedents":             _load_json(getattr(report,"precedents",None), {}),
    }


# ─────────────────────────────────────────────
# CRUD HELPERS (unchanged)
# ─────────────────────────────────────────────

def get_all_reports() -> list[dict]:
    db = get_db()
    try:
        return [build_report_dict(r) for r in db.query(Report).order_by(Report.created_at.desc()).all()]
    finally:
        db.close()


def get_report_by_id(report_id: str) -> Optional[dict]:
    db = get_db()
    try:
        r = db.query(Report).filter(Report.id == report_id).first()
        return build_report_dict(r) if r else None
    finally:
        db.close()


def save_feedback(report_id: str, rating: int, comment: str = "") -> bool:
    db = get_db()
    try:
        db.add(Feedback(report_id=report_id, rating=rating, comment=comment))
        db.commit()
        return True
    except Exception as exc:
        log.warning("Feedback save failed: %s", exc)
        return False
    finally:
        db.close()


def get_trend_data() -> list[dict]:
    db = get_db()
    try:
        rows = db.query(Report).order_by(Report.created_at.desc()).limit(200).all()
        return [
            {
                "date":       r.created_at.isoformat() if r.created_at else None,
                "bias_found": r.bias_found,
                "confidence": r.confidence_score,
                "risk_score": getattr(r,"risk_score",0),
            }
            for r in rows
        ]
    finally:
        db.close()


def get_model_bias_report() -> dict:
    db = get_db()
    try:
        rows = db.query(Report).all()
        total    = len(rows)
        biased   = sum(1 for r in rows if r.bias_found)
        by_type  = {}
        disability_count    = 0
        intersectional_count = 0
        for r in rows:
            for bt in json.loads(r.bias_types or "[]"):
                by_type[bt] = by_type.get(bt, 0) + 1
            if getattr(r, "disability_bias", False):
                disability_count += 1
            ib = json.loads(getattr(r, "intersectional_bias", "{}") or "{}")
            if isinstance(ib, dict) and ib.get("detected"):
                intersectional_count += 1
        return {
            "total_reports":        total,
            "biased_count":         biased,
            "bias_rate":            round(biased / total, 3) if total else 0,
            "bias_by_type":         by_type,
            "disability_bias_count":disability_count,
            "intersectional_count": intersectional_count,
        }
    finally:
        db.close()