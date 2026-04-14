"""
test_v21.py — Verdict Watch V21 Test Suite
==========================================
Tests every layer of the system:
  - Unit tests for all 10 pipeline step functions (mocked AI calls)
  - Rules engine deterministic logic
  - DB persistence round-trips
  - 4-tier fallback chain routing
  - FastAPI endpoint contracts
  - V21-specific: TIMELINE, PRECEDENTS, Claude fallback, BATCH_MAX_ROWS=50

Run:
    pip install pytest pytest-mock httpx --break-system-packages
    pytest test_v21.py -v
"""

import json
import os
import sys
import types
import uuid
from unittest.mock import MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────
# 0.  Stub heavy optional dependencies before importing
# ──────────────────────────────────────────────────────────

# google-generativeai stub
genai_mod = types.ModuleType("google.generativeai")
genai_mod.configure = lambda **kw: None
genai_mod.GenerativeModel = MagicMock()
sys.modules["google"] = types.ModuleType("google")
sys.modules["google.generativeai"] = genai_mod

# vertexai stubs
vtx_mod = types.ModuleType("vertexai")
vtx_mod.init = lambda **kw: None
sys.modules["vertexai"] = vtx_mod
vtx_gen_mod = types.ModuleType("vertexai.generative_models")
vtx_gen_mod.GenerativeModel = MagicMock()
vtx_gen_mod.GenerationConfig = MagicMock(return_value={})
sys.modules["vertexai.generative_models"] = vtx_gen_mod

# anthropic stub
anthropic_mod = types.ModuleType("anthropic")
anthropic_mod.Anthropic = MagicMock()
sys.modules["anthropic"] = anthropic_mod

# groq stub
groq_mod = types.ModuleType("groq")
groq_mod.Groq = MagicMock()
sys.modules["groq"] = groq_mod

# dotenv stub
dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv_mod

# ── Force a shared temp-file SQLite so all test modules see the same DB ──
import tempfile, atexit as _atexit, pathlib as _pathlib
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_DB_PATH = _tmp_db.name
def _cleanup_db():
    try:
        _pathlib.Path(_DB_PATH).unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows holds the file lock until process exits — safe to ignore
_atexit.register(_cleanup_db)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["GROQ_API_KEY"]   = "test-groq-key"
os.environ["ANTHROPIC_API_KEY"] = "test-claude-key"

# Now safe to import
sys.path.insert(0, os.path.dirname(__file__))
import services
from services import (
    PROVIDER_GEMINI, PROVIDER_GROQ, PROVIDER_VERTEX, PROVIDER_CLAUDE,
    _rules_engine_risk, hash_text, find_duplicate, build_report_dict,
    BATCH_MAX_ROWS,
)

services.init_db()


# ──────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────

LOAN_DENIAL = (
    "Your loan application has been declined. Primary reasons: insufficient credit history, "
    "residential area risk score, employment sector classification. You may reapply after 6 months."
)

JOB_GENDER = (
    "Thank you for applying to the Marketing Manager role. We felt the demands of the role — "
    "including frequent travel — may not align with your current family obligations. "
    "We have moved forward with another candidate."
)

DISABILITY_REJECTION = (
    "Your application for the customer service role has been declined. Our assessment indicates "
    "that your accessibility requirements and communication style would make it difficult to meet "
    "the performance benchmarks required for this fast-paced environment."
)

MEDICAL_TRIAGE = (
    "Patient triaged to low-priority queue. Factors: age group (67), primary language (non-English), "
    "insurance classification (Medicaid). High-priority slots reserved for Priority 1–2."
)

CLEAN_DECISION = (
    "After a thorough review of all qualified applicants, we have selected a candidate whose "
    "technical skills and relevant experience most closely match the requirements of this role. "
    "We appreciate your interest and encourage you to apply for future openings."
)


def _make_json_result(**kw) -> tuple:
    """Return (dict, retries=0, elapsed=100, provider)."""
    return kw, 0, 100, PROVIDER_GEMINI


# ──────────────────────────────────────────────────────────
# 1.  CONSTANTS & CONFIGURATION
# ──────────────────────────────────────────────────────────

class TestConstants:
    def test_batch_max_rows_v21(self):
        assert BATCH_MAX_ROWS == 50, "V21 must raise batch limit to 50"

    def test_claude_model_constant(self):
        assert hasattr(services, "_CLAUDE_MODEL")
        assert "claude" in services._CLAUDE_MODEL.lower()

    def test_provider_constants_all_four(self):
        assert PROVIDER_VERTEX == "vertex"
        assert PROVIDER_GEMINI == "gemini"
        assert PROVIDER_GROQ   == "groq"
        assert PROVIDER_CLAUDE == "claude"

    def test_gemini_pro_model_set(self):
        assert "2.5" in services._GEMINI_PRO_MODEL or "pro" in services._GEMINI_PRO_MODEL.lower()

    def test_gemini_flash_model_set(self):
        assert "flash" in services._GEMINI_FLASH_MODEL.lower()


# ──────────────────────────────────────────────────────────
# 2.  HASH & DEDUP
# ──────────────────────────────────────────────────────────

class TestHashAndDedup:
    def test_hash_deterministic(self):
        assert hash_text(LOAN_DENIAL) == hash_text(LOAN_DENIAL)

    def test_hash_normalises_whitespace(self):
        a = hash_text("hello   world")
        b = hash_text("hello world")
        assert a == b

    def test_hash_case_insensitive(self):
        assert hash_text("LOAN DENIAL") == hash_text("loan denial")

    def test_hash_differs_for_different_texts(self):
        assert hash_text(LOAN_DENIAL) != hash_text(JOB_GENDER)

    def test_find_duplicate_returns_none_when_empty(self):
        result = find_duplicate("deadbeef" * 8)
        assert result is None


# ──────────────────────────────────────────────────────────
# 3.  RULES ENGINE (deterministic, no AI calls)
# ──────────────────────────────────────────────────────────

class TestRulesEngine:
    def _bias(self, severity="low", disability=False):
        return {"severity": severity, "disability_bias_detected": disability, "bias_detected": True}

    def _fairness(self, overall=50, intersect=False):
        return {
            "overall_fairness_score": overall,
            "intersectional_bias":    {"detected": intersect},
        }

    def test_high_severity_floor(self):
        ai_risk = {"risk_score": 30, "urgency_tier": "low", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias("high"), self._fairness(), ai_risk)
        assert result["risk_score"] >= 60

    def test_disability_floor(self):
        ai_risk = {"risk_score": 20, "urgency_tier": "low", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias("low", disability=True), self._fairness(), ai_risk)
        assert result["risk_score"] >= 55

    def test_intersectional_floor(self):
        ai_risk = {"risk_score": 10, "urgency_tier": "low", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias(), self._fairness(intersect=True), ai_risk)
        assert result["risk_score"] >= 50

    def test_very_low_fairness_floor(self):
        ai_risk = {"risk_score": 5, "urgency_tier": "low", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias(), self._fairness(overall=10), ai_risk)
        assert result["risk_score"] >= 85

    def test_escalation_at_65(self):
        ai_risk = {"risk_score": 65, "urgency_tier": "low", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias(), self._fairness(), ai_risk)
        assert result["escalation_recommended"] is True
        assert result["urgency_tier"] == "high"

    def test_escalation_false_below_65(self):
        ai_risk = {"risk_score": 40, "urgency_tier": "medium", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias(), self._fairness(), ai_risk)
        assert result["escalation_recommended"] is False

    def test_immediate_tier_at_80(self):
        ai_risk = {"risk_score": 80, "urgency_tier": "low", "escalation_recommended": False}
        result = _rules_engine_risk(self._bias("high"), self._fairness(), ai_risk)
        assert result["urgency_tier"] == "immediate"

    def test_score_capped_at_100(self):
        ai_risk = {"risk_score": 99, "urgency_tier": "immediate", "escalation_recommended": True}
        result = _rules_engine_risk(self._bias("high"), self._fairness(overall=5), ai_risk)
        assert result["risk_score"] <= 100


# ──────────────────────────────────────────────────────────
# 4.  STEP FUNCTIONS (mocked _ai_call_json / _ai_call_text)
# ──────────────────────────────────────────────────────────

SCAN_RESPONSE = {
    "characteristics_present": ["age", "geography"],
    "influence_weights": {"age": 40, "geography": 60},
    "disability_signals": [],
    "data_quality_flags": [],
    "pre_scan_risk": "medium",
}

EXTRACT_RESPONSE = {
    "decision_type": "loan",
    "outcome": "rejected",
    "criteria_used": ["credit_history", "residential_area"],
    "data_points_weighted": ["credit_score", "zip_code"],
    "protected_characteristics_mentioned": ["geography"],
    "confidence_in_extraction": 0.9,
}

BIAS_RESPONSE = {
    "bias_detected": True,
    "bias_types": ["geographic", "socioeconomic"],
    "disability_bias_detected": False,
    "which_characteristic_affected": "geography",
    "bias_evidence": "Zip code used as proxy for race.",
    "confidence": 0.85,
    "severity": "high",
    "bias_phrases": ["residential area risk score", "employment sector classification"],
}

FAIR_RESPONSE = {
    "fair_outcome": "approved",
    "fair_reasoning": "Creditworthiness should not be judged by geography.",
    "what_was_wrong": "Geographic redlining used as discriminatory proxy.",
    "next_steps": ["File CFPB complaint", "Request written denial reasons", "Consult HUD"],
    "legal_frameworks": ["Equal Credit Opportunity Act", "Fair Housing Act"],
    "international_frameworks": ["ECHR Article 14"],
}

FAIRNESS_RESPONSE = {
    "demographic_parity_scores": {"geography": 20},
    "counterfactual_findings": [
        {"characteristic": "geography", "hypothetical_change": "Different zip",
         "would_outcome_change": True, "reasoning": "Score would improve."}
    ],
    "intersectional_bias": {"detected": True, "combinations": ["age+geography"],
                            "description": "Combined disadvantage."},
    "overall_fairness_score": 25,
    "fairness_verdict": "unfair",
    "audit_summary": "Severe geographic bias detected.",
}

EXPLAIN_RESPONSE = {
    "reasoning_chain": [
        {"step": 1, "phrase": "residential area risk score",
         "characteristic_triggered": "geography", "legal_violation": "Fair Housing Act",
         "why_this_matters": "Redlining proxy.", "severity_per_phrase": "high"},
    ],
    "root_cause": "Geographic proxy for racial discrimination.",
    "retroactive_correction": "Remove zip from model.",
    "corrective_action": "Re-evaluate without geographic factors.",
}

RISK_RESPONSE = {
    "risk_score": 72,
    "urgency_tier": "high",
    "escalation_recommended": True,
    "risk_factors": ["high severity bias", "intersectional bias"],
    "estimated_harm_severity": "Significant financial harm.",
    "time_sensitivity": "Act within 180 days.",
    "protective_factors": [],
}

TIMELINE_RESPONSE = {
    "jurisdiction": "United States",
    "applicable_tribunals": ["CFPB", "HUD", "Federal District Court"],
    "deadlines": [
        {
            "body": "CFPB",
            "action": "File consumer complaint",
            "window_days": 180,
            "window_description": "180 days from discriminatory act",
            "priority": "critical",
        },
        {
            "body": "HUD",
            "action": "File fair housing complaint",
            "window_days": 365,
            "window_description": "1 year from discriminatory act",
            "priority": "high",
        },
    ],
    "immediate_actions": [
        "Document all communications with the lender",
        "Request a written statement of denial reasons",
        "Contact a HUD-approved housing counsellor",
    ],
    "evidence_to_preserve": ["Denial letter", "Application form", "Email correspondence"],
    "estimated_timeline_months": 18,
    "pro_bono_resources": ["NFHA", "ACLU", "Local Legal Aid"],
}

PRECEDENT_RESPONSE = {
    "precedents": [
        {
            "case_name": "Griggs v. Duke Power Co., 401 U.S. 424 (1971)",
            "year": 1971,
            "jurisdiction": "United States Supreme Court",
            "relevance_score": 92,
            "why_relevant": "Established disparate impact theory for facially neutral criteria.",
            "outcome": "Ruled in favour of plaintiffs — neutral criteria with discriminatory effect is unlawful.",
            "key_principle": "Disparate impact liability under Title VII.",
        },
        {
            "case_name": "Texas Department of Housing v. Inclusive Communities, 576 U.S. 519 (2015)",
            "year": 2015,
            "jurisdiction": "United States Supreme Court",
            "relevance_score": 88,
            "why_relevant": "Confirmed disparate impact claims under the Fair Housing Act.",
            "outcome": "Upheld FHA disparate impact liability.",
            "key_principle": "Geographic bias can constitute housing discrimination.",
        },
    ],
    "strongest_precedent": "Griggs v. Duke Power Co., 401 U.S. 424 (1971)",
    "legal_strategy_hint": "Emphasise disparate impact — no intent to discriminate required.",
    "estimated_win_probability": "medium",
}


class TestPipelineStepFunctions:
    @patch("services._ai_call_json")
    def test_step0_pre_decision_scan(self, mock_ai):
        mock_ai.return_value = (SCAN_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, prov = services.pre_decision_scan(LOAN_DENIAL)
        assert result["pre_scan_risk"] == "medium"
        assert "age" in result["characteristics_present"]
        assert prov == PROVIDER_GEMINI
        # Confirm Gemini Pro model used for Step 0
        call_kwargs = mock_ai.call_args
        assert call_kwargs[1].get("gemini_model") == services._GEMINI_PRO_MODEL

    @patch("services._ai_call_json")
    def test_step1_extract_factors(self, mock_ai):
        mock_ai.return_value = (EXTRACT_RESPONSE, 0, 80, PROVIDER_GEMINI)
        result, r, t, prov = services.extract_factors(LOAN_DENIAL, "loan")
        assert result["outcome"] == "rejected"
        assert "credit_history" in result["criteria_used"]
        assert t == 80

    @patch("services._ai_call_json")
    def test_step2_detect_bias(self, mock_ai):
        mock_ai.return_value = (BIAS_RESPONSE, 0, 90, PROVIDER_GEMINI)
        result, r, t, prov = services.detect_bias(EXTRACT_RESPONSE)
        assert result["bias_detected"] is True
        assert "geographic" in result["bias_types"]
        assert result["severity"] == "high"
        assert len(result["bias_phrases"]) > 0

    @patch("services._ai_call_json")
    def test_step3_generate_fair_outcome(self, mock_ai):
        mock_ai.return_value = (FAIR_RESPONSE, 0, 120, PROVIDER_GEMINI)
        result, r, t, prov = services.generate_fair_outcome(EXTRACT_RESPONSE, BIAS_RESPONSE)
        assert result["fair_outcome"] == "approved"
        assert "Equal Credit Opportunity Act" in result["legal_frameworks"]
        assert len(result["next_steps"]) == 3

    @patch("services._ai_call_json")
    def test_step4_run_fairness_audit(self, mock_ai):
        mock_ai.return_value = (FAIRNESS_RESPONSE, 0, 200, PROVIDER_VERTEX)
        result, r, t, prov = services.run_fairness_audit(LOAN_DENIAL, BIAS_RESPONSE)
        assert result["overall_fairness_score"] == 25
        assert result["intersectional_bias"]["detected"] is True

    @patch("services._ai_call_json")
    def test_step5_explainability_trace(self, mock_ai):
        mock_ai.return_value = (EXPLAIN_RESPONSE, 0, 180, PROVIDER_VERTEX)
        result, r, t, prov = services.generate_explainability_trace(
            LOAN_DENIAL, BIAS_RESPONSE, FAIR_RESPONSE
        )
        assert len(result["reasoning_chain"]) == 1
        chain = result["reasoning_chain"][0]
        assert chain["severity_per_phrase"] == "high"
        assert chain["characteristic_triggered"] == "geography"

    @patch("services._ai_call_json")
    def test_step6_score_risk(self, mock_ai):
        mock_ai.return_value = (RISK_RESPONSE, 0, 60, PROVIDER_GEMINI)
        result, r, t, prov = services.score_risk(BIAS_RESPONSE, FAIR_RESPONSE, FAIRNESS_RESPONSE)
        assert result["risk_score"] == 72
        assert result["urgency_tier"] == "high"
        assert result["escalation_recommended"] is True

    @patch("services._ai_call_text")
    def test_step7_appeal_letter(self, mock_ai):
        mock_ai.return_value = ("Dear [RECIPIENT NAME],\n\nI am writing to formally appeal...", PROVIDER_GEMINI)
        partial_report = {
            "bias_types": ["geographic"], "affected_characteristic": "geography",
            "explanation": "Geographic redlining", "fair_outcome": "approved",
            "legal_frameworks": ["Fair Housing Act"], "international_laws": [],
            "fairness_scores": {}, "risk_score": 72, "urgency_tier": "high",
            "bias_phrases": ["residential area risk score"],
        }
        letter = services.generate_appeal_letter(partial_report, LOAN_DENIAL, "loan")
        assert isinstance(letter, str)
        assert len(letter) > 20
        # Confirm Gemini Pro used for Step 7
        call_kwargs = mock_ai.call_args
        assert call_kwargs[1].get("gemini_model") == services._GEMINI_PRO_MODEL

    @patch("services._ai_call_json")
    def test_step8_legal_timeline_v21(self, mock_ai):
        """V21: Step 8 TIMELINE returns deadlines + jurisdiction."""
        mock_ai.return_value = (TIMELINE_RESPONSE, 0, 300, PROVIDER_GEMINI)
        result, r, t, prov = services.calculate_legal_timeline(
            LOAN_DENIAL, "loan", BIAS_RESPONSE, FAIR_RESPONSE
        )
        assert result["jurisdiction"] == "United States"
        assert len(result["deadlines"]) == 2
        assert result["deadlines"][0]["body"] == "CFPB"
        assert result["deadlines"][0]["window_days"] == 180
        assert len(result["immediate_actions"]) == 3
        # Confirm Gemini Pro used for Step 8
        call_kwargs = mock_ai.call_args
        assert call_kwargs[1].get("gemini_model") == services._GEMINI_PRO_MODEL

    @patch("services._ai_call_json")
    def test_step9_retrieve_precedents_v21(self, mock_ai):
        """V21: Step 9 PRECEDENT returns case-law with relevance scores."""
        mock_ai.return_value = (PRECEDENT_RESPONSE, 0, 400, PROVIDER_GEMINI)
        result, r, t, prov = services.retrieve_precedents("loan", BIAS_RESPONSE, FAIR_RESPONSE)
        assert len(result["precedents"]) == 2
        first = result["precedents"][0]
        assert "Griggs" in first["case_name"]
        assert first["relevance_score"] == 92
        assert result["strongest_precedent"] == "Griggs v. Duke Power Co., 401 U.S. 424 (1971)"
        assert result["estimated_win_probability"] == "medium"
        # Confirm Gemini Pro used for Step 9
        call_kwargs = mock_ai.call_args
        assert call_kwargs[1].get("gemini_model") == services._GEMINI_PRO_MODEL


# ──────────────────────────────────────────────────────────
# 5.  4-TIER FALLBACK CHAIN
# ──────────────────────────────────────────────────────────

class TestFallbackChain:
    def test_gemini_succeeds_first_tier(self):
        with patch("services._call_gemini_json") as mock_g:
            mock_g.return_value = ({"ok": True}, 0, 50)
            r, ret, el, prov = services._ai_call_json(
                "prompt", [{"role":"user","content":"q"}], "test"
            )
        assert prov == PROVIDER_GEMINI
        assert r["ok"] is True

    def test_groq_fallback_when_gemini_fails(self):
        with patch("services._call_gemini_json", side_effect=Exception("Gemini down")):
            with patch("services._call_groq_json") as mock_groq:
                mock_groq.return_value = ({"ok": True}, 0, 80)
                r, ret, el, prov = services._ai_call_json(
                    "prompt", [{"role":"user","content":"q"}], "test"
                )
        assert prov == PROVIDER_GROQ
        assert r["ok"] is True

    def test_claude_fallback_when_gemini_and_groq_fail(self):
        """V21: Claude is 4th tier fallback."""
        with patch("services._call_gemini_json", side_effect=Exception("Gemini down")):
            with patch("services._call_groq_json", side_effect=Exception("Groq down")):
                with patch("services._call_claude_json") as mock_claude:
                    mock_claude.return_value = ({"ok": True}, 0, 200)
                    r, ret, el, prov = services._ai_call_json(
                        "prompt",
                        [{"role":"system","content":"sys"},{"role":"user","content":"q"}],
                        "test",
                    )
        assert prov == PROVIDER_CLAUDE
        assert r["ok"] is True

    def test_vertex_preferred_when_available(self):
        with patch("services.vertex_available", return_value=True):
            with patch("services._call_vertex_json") as mock_vtx:
                mock_vtx.return_value = ({"ok": True}, 0, 120)
                r, ret, el, prov = services._ai_call_json(
                    "prompt", [{"role":"user","content":"q"}], "test", prefer_vertex=True
                )
        assert prov == PROVIDER_VERTEX

    def test_all_four_fail_raises(self):
        with patch("services._call_gemini_json", side_effect=Exception("Gemini down")):
            with patch("services._call_groq_json",   side_effect=Exception("Groq down")):
                with patch("services._call_claude_json", side_effect=Exception("Claude down")):
                    with pytest.raises(ValueError, match="All 4 providers failed"):
                        services._ai_call_json(
                            "prompt",
                            [{"role":"system","content":"sys"},{"role":"user","content":"q"}],
                            "test",
                        )

    def test_text_claude_fallback(self):
        with patch("services._call_gemini_text", side_effect=Exception("Gemini text down")):
            with patch("services._call_groq_text", side_effect=Exception("Groq text down")):
                with patch("services._call_claude_text") as mock_ct:
                    mock_ct.return_value = "Claude wrote this"
                    text, prov = services._ai_call_text(
                        "prompt",
                        [{"role":"system","content":"sys"},{"role":"user","content":"q"}],
                        "test",
                    )
        assert prov == PROVIDER_CLAUDE
        assert text == "Claude wrote this"


# ──────────────────────────────────────────────────────────
# 6.  DB PERSISTENCE
# ──────────────────────────────────────────────────────────

def _insert_report(**overrides) -> services.Report:
    db = services.get_db()
    try:
        analysis = services.Analysis(
            raw_text=LOAN_DENIAL, text_hash=hash_text(LOAN_DENIAL),
            decision_type="loan", extracted_factors="{}",
        )
        db.add(analysis); db.commit(); db.refresh(analysis)

        defaults = dict(
            analysis_id=analysis.id,
            bias_found=True,
            bias_types=json.dumps(["geographic"]),
            affected_characteristic="geography",
            original_outcome="rejected",
            fair_outcome="approved",
            explanation="Geographic redlining.",
            confidence_score=0.85,
            recommendations=json.dumps({"steps": ["File CFPB"], "extra": {
                "legal_frameworks": ["Equal Credit Opportunity Act"],
                "fair_reasoning": "ECOA violated.",
                "severity": "high",
                "bias_evidence": "Zip code proxy.",
            }}),
            bias_phrases=json.dumps(["residential area risk score"]),
            timing_ms=json.dumps({"total": 1000}),
            retry_counts=json.dumps({}),
            ai_provider="gemini", ai_model="gemini-2.5-pro", decision_type="loan",
            fairness_scores=json.dumps({"overall_fairness_score": 25, "fairness_verdict": "unfair"}),
            explainability_trace=json.dumps({}),
            characteristic_weights=json.dumps({"geography": 60}),
            risk_score=72, urgency_tier="high", escalation_flag=True,
            appeal_letter="Dear Sir, I appeal...",
            disability_bias=False,
            intersectional_bias=json.dumps({"detected": True, "combinations": ["age+geo"]}),
            international_laws=json.dumps(["ECHR Article 14"]),
            severity_per_phrase=json.dumps([{"phrase": "residential area risk score", "severity": "high"}]),
            legal_timeline=json.dumps(TIMELINE_RESPONSE),
            precedents=json.dumps(PRECEDENT_RESPONSE),
        )
        defaults.update(overrides)
        report = services.Report(**defaults)
        db.add(report); db.commit(); db.refresh(report)
        return report
    finally:
        db.close()


class TestDBPersistence:
    def test_insert_and_retrieve_report(self):
        r = _insert_report()
        retrieved = services.get_report_by_id(r.id)
        assert retrieved is not None
        assert retrieved["bias_found"] is True
        assert retrieved["risk_score"] == 72

    def test_build_report_dict_has_v21_fields(self):
        r = _insert_report()
        d = build_report_dict(r)
        assert "legal_timeline" in d, "V21: legal_timeline must be in report dict"
        assert "precedents"     in d, "V21: precedents must be in report dict"

    def test_legal_timeline_deserialised_correctly(self):
        r = _insert_report()
        d = build_report_dict(r)
        tl = d["legal_timeline"]
        assert tl["jurisdiction"] == "United States"
        assert len(tl["deadlines"]) == 2

    def test_precedents_deserialised_correctly(self):
        r = _insert_report()
        d = build_report_dict(r)
        prec = d["precedents"]
        assert len(prec["precedents"]) == 2
        assert "Griggs" in prec["strongest_precedent"]

    def test_severity_per_phrase_deserialised(self):
        r = _insert_report()
        d = build_report_dict(r)
        assert isinstance(d["severity_per_phrase"], list)
        assert d["severity_per_phrase"][0]["severity"] == "high"

    def test_get_all_reports_returns_list(self):
        _insert_report()
        all_r = services.get_all_reports()
        assert isinstance(all_r, list)
        assert len(all_r) >= 1

    def test_save_feedback(self):
        r = _insert_report()
        ok = services.save_feedback(r.id, 1, "Great tool!")
        assert ok is True

    def test_missing_report_returns_none(self):
        result = services.get_report_by_id("does-not-exist-" + str(uuid.uuid4()))
        assert result is None

    def test_get_trend_data_returns_list(self):
        _insert_report()
        trends = services.get_trend_data()
        assert isinstance(trends, list)
        assert "risk_score" in trends[0]

    def test_model_bias_report_counts(self):
        _insert_report(bias_found=True)
        _insert_report(bias_found=False, bias_types=json.dumps([]), risk_score=0)
        report = services.get_model_bias_report()
        assert report["total_reports"] >= 2
        assert report["biased_count"] >= 1


# ──────────────────────────────────────────────────────────
# 7.  QUICK SCAN
# ──────────────────────────────────────────────────────────

QUICK_AI_RESPONSE = {
    "bias_detected": True,
    "bias_types": ["gender"],
    "disability_bias_detected": False,
    "which_characteristic_affected": "gender",
    "confidence": 0.8,
    "severity": "medium",
    "original_outcome": "rejected",
    "fair_outcome": "reconsidered",
    "explanation": "Family obligation language is gender-biased.",
    "next_steps": ["File EEOC", "Contact attorney", "Document decision"],
    "bias_phrases": ["family obligations"],
    "legal_frameworks": ["Title VII"],
    "overall_fairness_score": 35,
    "fairness_verdict": "unfair",
    "risk_score": 50,
    "urgency_tier": "medium",
}


class TestQuickScan:
    @patch("services._ai_call_json")
    def test_quick_scan_returns_all_v21_fields(self, mock_ai):
        mock_ai.return_value = (QUICK_AI_RESPONSE, 0, 80, PROVIDER_GEMINI)
        result = services.quick_scan(JOB_GENDER, "job")
        assert result["bias_found"] is True
        assert result["risk_score"] == 50
        assert result["mode"] == "quick"
        assert "legal_timeline" in result, "V21: quick_scan must return legal_timeline"
        assert "precedents"     in result, "V21: quick_scan must return precedents"

    @patch("services._ai_call_json")
    def test_quick_scan_escalation_flag(self, mock_ai):
        high = {**QUICK_AI_RESPONSE, "risk_score": 70, "urgency_tier": "high"}
        mock_ai.return_value = (high, 0, 80, PROVIDER_GEMINI)
        result = services.quick_scan(JOB_GENDER, "job")
        assert result["escalation_flag"] is True

    @patch("services._ai_call_json")
    def test_quick_scan_no_escalation_below_65(self, mock_ai):
        low = {**QUICK_AI_RESPONSE, "risk_score": 40, "urgency_tier": "medium"}
        mock_ai.return_value = (low, 0, 80, PROVIDER_GEMINI)
        result = services.quick_scan(JOB_GENDER, "job")
        assert result["escalation_flag"] is False


# ──────────────────────────────────────────────────────────
# 8.  FULL PIPELINE (mocked step functions)
# ──────────────────────────────────────────────────────────

class TestFullPipeline:
    def _patch_all_steps(self):
        """Return context manager that patches all 10 AI step calls."""
        patches = [
            patch("services.pre_decision_scan",         return_value=(SCAN_RESPONSE, PROVIDER_GEMINI)),
            patch("services.extract_factors",           return_value=(EXTRACT_RESPONSE, 0, 80, PROVIDER_GEMINI)),
            patch("services.detect_bias",               return_value=(BIAS_RESPONSE, 0, 90, PROVIDER_GEMINI)),
            patch("services.generate_fair_outcome",     return_value=(FAIR_RESPONSE, 0, 120, PROVIDER_GEMINI)),
            patch("services.run_fairness_audit",        return_value=(FAIRNESS_RESPONSE, 0, 200, PROVIDER_VERTEX)),
            patch("services.generate_explainability_trace", return_value=(EXPLAIN_RESPONSE, 0, 180, PROVIDER_VERTEX)),
            patch("services.score_risk",                return_value=(RISK_RESPONSE, 0, 60, PROVIDER_GEMINI)),
            patch("services.generate_appeal_letter",    return_value="Dear Sir, I appeal formally."),
            patch("services.calculate_legal_timeline",  return_value=(TIMELINE_RESPONSE, 0, 300, PROVIDER_GEMINI)),
            patch("services.retrieve_precedents",       return_value=(PRECEDENT_RESPONSE, 0, 400, PROVIDER_GEMINI)),
        ]
        return patches

    def test_full_pipeline_runs_all_10_steps(self):
        patches = self._patch_all_steps()
        active = [p.start() for p in patches]
        try:
            result = services.run_full_pipeline(LOAN_DENIAL, "loan")
        finally:
            for p in patches:
                p.stop()

        assert result["bias_found"] is True
        assert result["risk_score"] == 72
        assert result["appeal_letter"] == "Dear Sir, I appeal formally."
        assert result["legal_timeline"]["jurisdiction"] == "United States"
        assert len(result["precedents"]["precedents"]) == 2

    def test_full_pipeline_timing_has_10_keys(self):
        patches = self._patch_all_steps()
        for p in patches:
            p.start()
        try:
            result = services.run_full_pipeline(LOAN_DENIAL, "loan")
        finally:
            for p in patches:
                p.stop()
        timing = result["timing_ms"]
        expected_keys = {"pre_scan","extract","detect","fair","fairness_audit",
                         "explainability","risk","appeal","timeline","precedent","total"}
        assert expected_keys.issubset(set(timing.keys()))

    def test_full_pipeline_progress_callback(self):
        calls = []
        def cb(step, label):
            calls.append((step, label))

        patches = self._patch_all_steps()
        for p in patches:
            p.start()
        try:
            services.run_full_pipeline(LOAN_DENIAL, "loan", progress_callback=cb)
        finally:
            for p in patches:
                p.stop()

        step_indices = [c[0] for c in calls]
        assert 8 in step_indices, "Step 8 (TIMELINE) callback must fire"
        assert 9 in step_indices, "Step 9 (PRECEDENT) callback must fire"

    def test_step8_skipped_when_no_bias(self):
        no_bias = {**BIAS_RESPONSE, "bias_detected": False, "bias_types": []}
        patches = [
            patch("services.pre_decision_scan",     return_value=(SCAN_RESPONSE, PROVIDER_GEMINI)),
            patch("services.extract_factors",       return_value=(EXTRACT_RESPONSE, 0, 80, PROVIDER_GEMINI)),
            patch("services.detect_bias",           return_value=(no_bias, 0, 90, PROVIDER_GEMINI)),
            patch("services.generate_fair_outcome", return_value=(FAIR_RESPONSE, 0, 120, PROVIDER_GEMINI)),
            patch("services.score_risk",            return_value=({"risk_score":5,"urgency_tier":"low","escalation_recommended":False}, 0, 60, PROVIDER_GEMINI)),
            patch("services.calculate_legal_timeline"),
            patch("services.retrieve_precedents"),
        ]
        for p in patches:
            p.start()
        try:
            result = services.run_full_pipeline(CLEAN_DECISION, "job")
        finally:
            for p in patches:
                try: p.stop()
                except Exception: pass

        assert result["bias_found"] is False

    def test_step8_gracefully_handles_failure(self):
        patches = self._patch_all_steps()
        # Override step 8 to raise
        for p in patches:
            p.start()
        timeline_patch = patch("services.calculate_legal_timeline", side_effect=Exception("Timeline API down"))
        timeline_patch.start()
        try:
            result = services.run_full_pipeline(LOAN_DENIAL, "loan")
            # Should not raise; legal_timeline falls back to {}
            assert isinstance(result.get("legal_timeline"), dict)
        finally:
            for p in patches:
                try: p.stop()
                except Exception: pass
            timeline_patch.stop()


# ──────────────────────────────────────────────────────────
# 9.  FASTAPI ENDPOINTS
# ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    try:
        from fastapi.testclient import TestClient
        import api as api_module
        # Ensure the API's services instance has tables created in the test DB
        api_module.services.init_db()
        return TestClient(api_module.app)
    except ImportError:
        pytest.skip("httpx not installed — skip API tests")


class TestAPIHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "21.0.0"
        assert data["pipeline_steps"] == 10
        assert data["legal_timeline"]  is True
        assert data["precedent_retrieval"] is True
        assert data["batch_limit"] == 50

    def test_providers_endpoint_has_claude(self, client):
        r = client.get("/api/providers")
        assert r.status_code == 200
        data = r.json()
        assert "claude" in data, "V21: /api/providers must include claude provider"
        assert data["claude"]["role"] == "4th fallback all steps [V21]"

    def test_governance_report_lists_10_steps(self, client):
        r = client.get("/api/governance/report")
        assert r.status_code == 200
        data = r.json()
        assert data["version"].startswith("V21")
        assert len(data["pipeline_steps"]) == 10
        steps_text = " ".join(data["pipeline_steps"]).lower()
        assert "timeline" in steps_text, f"timeline not found in steps: {data['pipeline_steps']}"
        assert "precedent" in steps_text
        assert data["batch_limit"] == 50
        assert len(data["fallback_chain"]) == 4

    def test_reports_list(self, client):
        r = client.get("/api/reports")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestAPIAnalyse:
    @patch("services.quick_scan")
    def test_quick_scan_endpoint(self, mock_qs, client):
        mock_qs.return_value = {
            **{k: None for k in ["id","analysis_id","bias_found","bias_types",
                                  "affected_characteristic","original_outcome","fair_outcome",
                                  "explanation","confidence_score","recommendations","created_at"]},
            "id": str(uuid.uuid4()), "analysis_id": "quick-scan",
            "bias_found": True, "bias_types": ["gender"],
            "confidence_score": 0.8, "recommendations": [],
            "bias_phrases": [], "legal_frameworks": [], "international_laws": [],
            "fair_reasoning": "", "severity": "medium", "bias_evidence": "",
            "timing_ms": {}, "retry_counts": {}, "mode": "quick",
            "ai_provider": "gemini", "fairness_scores": {}, "explainability_trace": {},
            "characteristic_weights": {}, "risk_score": 50, "urgency_tier": "medium",
            "escalation_flag": False, "appeal_letter": None, "disability_bias": False,
            "intersectional_bias": {}, "severity_per_phrase": [],
            "legal_timeline": {}, "precedents": {},
        }
        r = client.post("/api/analyse", json={
            "decision_text": JOB_GENDER,
            "decision_type": "job",
            "scan_mode": "quick",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["bias_found"] is True
        assert data["risk_score"] == 50

    def test_analyse_rejects_short_text(self, client):
        r = client.post("/api/analyse", json={"decision_text": "short", "decision_type": "job"})
        assert r.status_code == 422


class TestAPIV21Endpoints:
    def test_timeline_404_for_unknown_report(self, client):
        r = client.get("/api/timeline/nonexistent-report-id")
        assert r.status_code == 404

    def test_precedents_404_for_unknown_report(self, client):
        r = client.get("/api/precedents/nonexistent-report-id")
        assert r.status_code == 404

    def test_timeline_returns_data_for_existing_report(self, client):
        report = _insert_report()
        r = client.get(f"/api/timeline/{report.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["timeline"]["jurisdiction"] == "United States"
        assert len(data["timeline"]["deadlines"]) == 2

    def test_precedents_returns_data_for_existing_report(self, client):
        report = _insert_report()
        r = client.get(f"/api/precedents/{report.id}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["precedents"]) == 2
        assert "Griggs" in data["strongest_precedent"]
        assert data["estimated_win_probability"] == "medium"

    def test_risk_endpoint(self, client):
        report = _insert_report()
        r = client.get(f"/api/risk/{report.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["risk_score"] == 72
        assert data["urgency_tier"] == "high"

    def test_fairness_endpoint_has_v21_fields(self, client):
        report = _insert_report()
        r = client.get(f"/api/fairness/{report.id}")
        assert r.status_code == 200
        data = r.json()
        assert "legal_timeline" in data
        assert "precedents"     in data

    def test_batch_audit_rejects_over_50(self, client):
        payload = {
            "decisions": [LOAN_DENIAL] * 51,
            "decision_type": "loan",
        }
        r = client.post("/api/audit/batch", json=payload)
        assert r.status_code == 422, "Should reject batch > 50"

    def test_batch_audit_accepts_50(self, client):
        """Batch of exactly 50 must pass schema validation (may fail on AI calls)."""
        with patch("services.run_full_pipeline", side_effect=Exception("no AI")):
            payload = {
                "decisions": [LOAN_DENIAL] * 50,
                "decision_type": "loan",
            }
            r = client.post("/api/audit/batch", json=payload)
            # 200 with errors list, not 422
            assert r.status_code == 200
            data = r.json()
            assert data["errors"] == 50


# ──────────────────────────────────────────────────────────
# 10. TIMELINE CONTENT VALIDATION
# ──────────────────────────────────────────────────────────

class TestTimelineStructure:
    @patch("services._ai_call_json")
    def test_timeline_deadline_priorities(self, mock_ai):
        mock_ai.return_value = (TIMELINE_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, *_ = services.calculate_legal_timeline(LOAN_DENIAL, "loan", BIAS_RESPONSE, FAIR_RESPONSE)
        priorities = [d["priority"] for d in result["deadlines"]]
        valid = {"critical", "high", "medium", "low"}
        assert all(p in valid for p in priorities)

    @patch("services._ai_call_json")
    def test_timeline_has_pro_bono_resources(self, mock_ai):
        mock_ai.return_value = (TIMELINE_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, *_ = services.calculate_legal_timeline(LOAN_DENIAL, "loan", BIAS_RESPONSE, FAIR_RESPONSE)
        assert isinstance(result.get("pro_bono_resources"), list)
        assert len(result["pro_bono_resources"]) > 0

    @patch("services._ai_call_json")
    def test_timeline_evidence_to_preserve(self, mock_ai):
        mock_ai.return_value = (TIMELINE_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, *_ = services.calculate_legal_timeline(LOAN_DENIAL, "loan", BIAS_RESPONSE, FAIR_RESPONSE)
        assert isinstance(result.get("evidence_to_preserve"), list)


# ──────────────────────────────────────────────────────────
# 11. PRECEDENT CONTENT VALIDATION
# ──────────────────────────────────────────────────────────

class TestPrecedentStructure:
    @patch("services._ai_call_json")
    def test_precedent_cases_have_required_fields(self, mock_ai):
        mock_ai.return_value = (PRECEDENT_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, *_ = services.retrieve_precedents("loan", BIAS_RESPONSE, FAIR_RESPONSE)
        for case in result["precedents"]:
            assert "case_name"        in case
            assert "year"             in case
            assert "relevance_score"  in case
            assert "why_relevant"     in case
            assert "key_principle"    in case

    @patch("services._ai_call_json")
    def test_precedent_win_probability_valid(self, mock_ai):
        mock_ai.return_value = (PRECEDENT_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, *_ = services.retrieve_precedents("loan", BIAS_RESPONSE, FAIR_RESPONSE)
        valid = {"low", "medium", "high"}
        assert result.get("estimated_win_probability") in valid

    @patch("services._ai_call_json")
    def test_precedent_relevance_scores_in_range(self, mock_ai):
        mock_ai.return_value = (PRECEDENT_RESPONSE, 0, 100, PROVIDER_GEMINI)
        result, *_ = services.retrieve_precedents("loan", BIAS_RESPONSE, FAIR_RESPONSE)
        for case in result["precedents"]:
            assert 0 <= case["relevance_score"] <= 100


# ──────────────────────────────────────────────────────────
# 12. STRIP_FENCES UTILITY
# ──────────────────────────────────────────────────────────

class TestStripFences:
    def test_strips_json_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        assert services._strip_fences(raw) == '{"key": "value"}'

    def test_strips_plain_fences(self):
        raw = '```\n{"key": "value"}\n```'
        assert services._strip_fences(raw) == '{"key": "value"}'

    def test_no_fences_unchanged(self):
        raw = '{"key": "value"}'
        assert services._strip_fences(raw) == '{"key": "value"}'

    def test_handles_whitespace(self):
        raw = '  {"key": "value"}  '
        assert services._strip_fences(raw) == '{"key": "value"}'


# ──────────────────────────────────────────────────────────
# 13. PROVIDER AVAILABILITY CHECKS
# ──────────────────────────────────────────────────────────

class TestProviderAvailability:
    def test_gemini_available_with_key(self):
        os.environ["GEMINI_API_KEY"] = "abc"
        status = services.check_providers()
        assert status["gemini"] is True

    def test_claude_available_with_key(self):
        os.environ["ANTHROPIC_API_KEY"] = "abc"
        status = services.check_providers()
        assert status["claude"] is True

    def test_vertex_unavailable_without_project(self):
        old = os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        status = services.check_providers()
        assert status["vertex"] is False
        if old:
            os.environ["GOOGLE_CLOUD_PROJECT"] = old

    def test_vertex_available_with_project(self):
        os.environ["GOOGLE_CLOUD_PROJECT"] = "my-project"
        assert services.vertex_available() is True
        del os.environ["GOOGLE_CLOUD_PROJECT"]