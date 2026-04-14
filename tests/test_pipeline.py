"""
tests/test_pipeline.py — Verdict Watch V20
pytest suite for the 8-step pipeline, DB, and helper functions.

Run:
    pytest tests/ -v

These tests mock the AI provider layer so they run without API keys.
"""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Make sure the parent dir is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set a test DB before importing services
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_verdict_v20.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import services


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Each test gets a clean in-memory-like SQLite DB."""
    import os
    test_db = str(tmp_path / "test.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"
    # Reinitialise engine/session for the temp db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    services.engine = engine
    services.SessionLocal = sessionmaker(bind=engine)
    services.Base.metadata.create_all(bind=engine)
    yield
    services.Base.metadata.drop_all(bind=engine)


# ─────────────────────────────────────────────
# HELPERS — mock AI responses
# ─────────────────────────────────────────────

MOCK_PRESCAN = {
    "characteristics_present": ["gender","age"],
    "influence_weights": {"gender":70,"age":40},
    "disability_signals": [],
    "data_quality_flags": [],
    "pre_scan_risk": "medium",
}

MOCK_EXTRACT = {
    "decision_type": "job",
    "outcome": "rejected",
    "criteria_used": ["experience","cultural fit"],
    "data_points_weighted": ["gender","parental status"],
    "protected_characteristics_mentioned": ["gender"],
    "confidence_in_extraction": 0.88,
}

MOCK_DETECT = {
    "bias_detected": True,
    "bias_types": ["Gender","Socioeconomic"],
    "disability_bias_detected": False,
    "which_characteristic_affected": "gender",
    "bias_evidence": "Mentions family obligations as a reason.",
    "confidence": 0.85,
    "severity": "high",
    "bias_phrases": ["family obligations","frequent travel"],
}

MOCK_FAIR = {
    "fair_outcome": "The candidate should have been shortlisted for interview.",
    "fair_reasoning": "No job-relevant reason was given.",
    "what_was_wrong": "The decision was based on gender stereotypes.",
    "next_steps": ["File a complaint with the EEOC","Contact a discrimination lawyer","Keep copies of all correspondence"],
    "legal_frameworks": ["Title VII of the Civil Rights Act","Pregnancy Discrimination Act"],
    "international_frameworks": ["ECHR Article 14","ILO Discrimination Convention 111"],
}

MOCK_FAIRNESS = {
    "demographic_parity_scores": {"gender":30,"age":70,"race":60},
    "counterfactual_findings": [
        {"characteristic":"gender","hypothetical_change":"applicant identified as male","would_outcome_change":True,"reasoning":"Role offered to male applicant with same qualifications."}
    ],
    "intersectional_bias": {"detected":False,"combinations":[],"description":""},
    "overall_fairness_score": 40,
    "fairness_verdict": "unfair",
    "audit_summary": "Gender disparity confirmed by counterfactual testing.",
}

MOCK_EXPLAIN = {
    "reasoning_chain": [
        {"step":1,"phrase":"family obligations","characteristic_triggered":"gender","legal_violation":"Title VII","why_this_matters":"Assumes parenting duties fall on female candidate.","severity_per_phrase":"high"},
        {"step":2,"phrase":"frequent travel","characteristic_triggered":"gender","legal_violation":"Title VII","why_this_matters":"Used to penalise assumed caregiving role.","severity_per_phrase":"medium"},
    ],
    "root_cause": "Stereotyped assumption about gender and caregiving.",
    "retroactive_correction": "Remove all references to family obligations and re-evaluate on job-relevant criteria only.",
    "corrective_action": "Assess all candidates on identical job-specific criteria.",
}

MOCK_RISK = {
    "risk_score": 72,
    "urgency_tier": "high",
    "escalation_recommended": True,
    "risk_factors": ["High-severity gender bias","Counterfactual parity confirmed disparity"],
    "estimated_harm_severity": "Denial of employment opportunity based on protected characteristic.",
    "time_sensitivity": "File within 180 days of the discriminatory act.",
    "protective_factors": [],
}

MOCK_APPEAL = "Dear Hiring Manager,\n\nI write to formally appeal the decision regarding my application for [POSITION]...\n\nYours faithfully,\n[YOUR NAME]"

MOCK_QUICK = {
    "bias_detected": True,
    "bias_types": ["Gender"],
    "disability_bias_detected": False,
    "which_characteristic_affected": "gender",
    "confidence": 0.80,
    "severity": "medium",
    "original_outcome": "rejected",
    "fair_outcome": "Candidate should have been interviewed.",
    "explanation": "Decision was based on gender stereotypes.",
    "next_steps": ["Contact EEOC","Seek legal advice","Document evidence"],
    "bias_phrases": ["family obligations"],
    "legal_frameworks": ["Title VII"],
    "overall_fairness_score": 45,
    "fairness_verdict": "partially_fair",
    "risk_score": 55,
    "urgency_tier": "medium",
}


def _make_ai_mock(result_dict):
    """Return a (result, retries=0, elapsed=100, provider='gemini') tuple."""
    return result_dict, 0, 100, services.PROVIDER_GEMINI


# ─────────────────────────────────────────────
# UNIT TESTS — helper functions
# ─────────────────────────────────────────────

class TestHelpers:
    def test_hash_text_deterministic(self):
        h1 = services.hash_text("Hello World")
        h2 = services.hash_text("Hello World")
        assert h1 == h2

    def test_hash_text_case_insensitive(self):
        h1 = services.hash_text("hello world")
        h2 = services.hash_text("HELLO WORLD")
        assert h1 == h2

    def test_hash_text_normalises_whitespace(self):
        h1 = services.hash_text("hello   world")
        h2 = services.hash_text("hello world")
        assert h1 == h2

    def test_strip_fences_clean(self):
        raw = '{"key": "value"}'
        assert services._strip_fences(raw) == raw

    def test_strip_fences_markdown(self):
        raw = '```json\n{"key": "value"}\n```'
        result = services._strip_fences(raw)
        assert '"key"' in result
        assert "```" not in result

    def test_strip_fences_no_json_tag(self):
        raw = '```\n{"key": "value"}\n```'
        result = services._strip_fences(raw)
        assert '"key"' in result


# ─────────────────────────────────────────────
# UNIT TESTS — DB operations
# ─────────────────────────────────────────────

class TestDatabase:
    def test_get_all_reports_empty(self):
        assert services.get_all_reports() == []

    def test_get_report_by_id_missing(self):
        assert services.get_report_by_id("nonexistent-id") is None

    def test_save_feedback(self):
        # Need a report first
        db = services.get_db()
        a  = services.Analysis(raw_text="test", text_hash="h1", decision_type="job", extracted_factors="{}")
        db.add(a); db.commit(); db.refresh(a)
        r = services.Report(analysis_id=a.id, bias_found=False, bias_types="[]", recommendations="[]")
        db.add(r); db.commit(); db.refresh(r)
        db.close()
        ok = services.save_feedback(r.id, 1, "Great tool")
        assert ok is True

    def test_save_feedback_returns_true(self):
        ok = services.save_feedback("fake-id-123", 0, "Not helpful")
        assert ok is True  # No foreign key constraint on SQLite

    def test_find_duplicate_no_match(self):
        result = services.find_duplicate("nonexistent-hash")
        assert result is None

    def test_find_duplicate_match(self):
        text = "This is a test decision text that should be deduplicated."
        h    = services.hash_text(text)
        db   = services.get_db()
        a    = services.Analysis(raw_text=text, text_hash=h, decision_type="job", extracted_factors="{}")
        db.add(a); db.commit(); db.refresh(a)
        r = services.Report(
            analysis_id=a.id, bias_found=True,
            bias_types=json.dumps(["Gender"]),
            recommendations=json.dumps({"steps":["Step 1"],"extra":{}}),
        )
        db.add(r); db.commit()
        db.close()
        found = services.find_duplicate(h)
        assert found is not None
        assert found["bias_found"] is True


# ─────────────────────────────────────────────
# UNIT TESTS — risk rules engine
# ─────────────────────────────────────────────

class TestRulesEngine:
    def _bias(self, **kwargs):
        base = {"bias_detected":True,"severity":"low","disability_bias_detected":False}
        base.update(kwargs)
        return base

    def _fairness(self, **kwargs):
        base = {"overall_fairness_score":50,"intersectional_bias":{"detected":False}}
        base.update(kwargs)
        return base

    def test_high_severity_floor(self):
        ai   = {"risk_score":20,"urgency_tier":"low","escalation_recommended":False}
        bias = self._bias(severity="high")
        fair = self._fairness()
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["risk_score"] >= 60

    def test_disability_floor(self):
        ai   = {"risk_score":10,"urgency_tier":"low","escalation_recommended":False}
        bias = self._bias(disability_bias_detected=True)
        fair = self._fairness()
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["risk_score"] >= 55

    def test_low_fairness_score_floor(self):
        ai   = {"risk_score":40,"urgency_tier":"medium","escalation_recommended":False}
        bias = self._bias()
        fair = self._fairness(overall_fairness_score=10)
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["risk_score"] >= 85

    def test_escalation_flag_set_above_65(self):
        ai   = {"risk_score":70,"urgency_tier":"high","escalation_recommended":False}
        bias = self._bias()
        fair = self._fairness()
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["escalation_recommended"] is True

    def test_no_escalation_below_65(self):
        ai   = {"risk_score":50,"urgency_tier":"medium","escalation_recommended":True}
        bias = self._bias()
        fair = self._fairness()
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["escalation_recommended"] is False

    def test_urgency_tier_immediate_at_80(self):
        ai   = {"risk_score":82,"urgency_tier":"low","escalation_recommended":True}
        bias = self._bias()
        fair = self._fairness()
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["urgency_tier"] == "immediate"

    def test_score_capped_at_100(self):
        ai   = {"risk_score":95,"urgency_tier":"immediate","escalation_recommended":True}
        bias = self._bias(severity="high",disability_bias_detected=True)
        fair = self._fairness(overall_fairness_score=5, intersectional_bias={"detected":True})
        result = services._rules_engine_risk(bias, fair, ai)
        assert result["risk_score"] <= 100


# ─────────────────────────────────────────────
# INTEGRATION TESTS — pipeline steps (mocked AI)
# ─────────────────────────────────────────────

DECISION_TEXT = (
    "Thank you for applying to the Marketing Manager role. "
    "We felt the demands of the role — including frequent travel — "
    "may not align with your current family obligations. "
    "We have moved forward with another candidate."
)


class TestPipelineSteps:
    @patch("services._ai_call_json")
    def test_pre_decision_scan(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_PRESCAN)
        result, prov = services.pre_decision_scan(DECISION_TEXT)
        assert "influence_weights" in result
        assert prov == services.PROVIDER_GEMINI

    @patch("services._ai_call_json")
    def test_extract_factors(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_EXTRACT)
        result, r, t, prov = services.extract_factors(DECISION_TEXT, "job")
        assert result["outcome"] == "rejected"
        assert "criteria_used" in result

    @patch("services._ai_call_json")
    def test_detect_bias_9_dims(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_DETECT)
        result, r, t, prov = services.detect_bias(MOCK_EXTRACT)
        assert result["bias_detected"] is True
        assert "Gender" in result["bias_types"]
        assert "disability_bias_detected" in result

    @patch("services._ai_call_json")
    def test_generate_fair_outcome_international(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_FAIR)
        result, r, t, prov = services.generate_fair_outcome(MOCK_EXTRACT, MOCK_DETECT)
        assert "legal_frameworks" in result
        assert "international_frameworks" in result

    @patch("services._ai_call_json")
    def test_fairness_audit_intersectional(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_FAIRNESS)
        result, r, t, prov = services.run_fairness_audit(DECISION_TEXT, MOCK_DETECT)
        assert "overall_fairness_score" in result
        assert "intersectional_bias" in result

    @patch("services._ai_call_json")
    def test_explainability_severity_per_phrase(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_EXPLAIN)
        result, r, t, prov = services.generate_explainability_trace(DECISION_TEXT, MOCK_DETECT, MOCK_FAIR)
        chain = result.get("reasoning_chain",[])
        assert len(chain) > 0
        assert "severity_per_phrase" in chain[0]

    @patch("services._ai_call_json")
    def test_risk_scoring(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_RISK)
        result, r, t, prov = services.score_risk(MOCK_DETECT, MOCK_FAIR, MOCK_FAIRNESS)
        assert "risk_score" in result
        assert "urgency_tier" in result
        assert "escalation_recommended" in result

    @patch("services._ai_call_text")
    def test_appeal_letter_generation(self, mock_ai):
        mock_ai.return_value = (MOCK_APPEAL, services.PROVIDER_GEMINI)
        report = {
            "bias_types": ["Gender"],
            "affected_characteristic": "gender",
            "explanation": "Gender bias detected.",
            "fair_outcome": "Candidate should have been interviewed.",
            "legal_frameworks": ["Title VII"],
            "international_laws": ["ECHR Article 14"],
            "fairness_scores": {"overall_fairness_score": 40},
            "risk_score": 72,
            "urgency_tier": "high",
            "bias_phrases": ["family obligations"],
        }
        letter = services.generate_appeal_letter(report, DECISION_TEXT, "job")
        assert len(letter) > 50
        assert "Dear" in letter


class TestQuickScan:
    @patch("services._ai_call_json")
    def test_quick_scan_returns_dict(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_QUICK)
        result = services.quick_scan(DECISION_TEXT, "job")
        assert isinstance(result, dict)
        assert result["bias_found"] is True
        assert "risk_score" in result
        assert "urgency_tier" in result

    @patch("services._ai_call_json")
    def test_quick_scan_saved_to_db(self, mock_ai):
        mock_ai.return_value = _make_ai_mock(MOCK_QUICK)
        result = services.quick_scan(DECISION_TEXT, "job")
        report_id = result.get("id")
        assert report_id is not None
        fetched = services.get_report_by_id(report_id)
        assert fetched is not None
        assert fetched["bias_found"] is True

    @patch("services._ai_call_json")
    def test_quick_scan_disability_field(self, mock_ai):
        mock = dict(MOCK_QUICK); mock["disability_bias_detected"] = True
        mock_ai.return_value = _make_ai_mock(mock)
        result = services.quick_scan(DECISION_TEXT, "job")
        assert result["disability_bias"] is True


class TestFullPipeline:
    @patch("services._ai_call_text")
    @patch("services._ai_call_json")
    def test_full_pipeline_returns_complete_report(self, mock_json, mock_text):
        """Full pipeline with all 8 steps mocked."""
        mock_json.side_effect = [
            _make_ai_mock(MOCK_PRESCAN),   # Step 0
            _make_ai_mock(MOCK_EXTRACT),   # Step 1
            _make_ai_mock(MOCK_DETECT),    # Step 2
            _make_ai_mock(MOCK_FAIR),      # Step 3
            _make_ai_mock(MOCK_FAIRNESS),  # Step 4
            _make_ai_mock(MOCK_EXPLAIN),   # Step 5
            _make_ai_mock(MOCK_RISK),      # Step 6
        ]
        mock_text.return_value = (MOCK_APPEAL, services.PROVIDER_GEMINI)  # Step 7

        result = services.run_full_pipeline(DECISION_TEXT, "job")

        assert result["bias_found"] is True
        assert result["risk_score"] > 0
        assert result["urgency_tier"] in ("immediate","high","medium","low")
        assert isinstance(result["fairness_scores"], dict)
        assert isinstance(result["explainability_trace"], dict)
        assert result["appeal_letter"] is not None

    @patch("services._ai_call_text")
    @patch("services._ai_call_json")
    def test_full_pipeline_saved_to_db(self, mock_json, mock_text):
        mock_json.side_effect = [
            _make_ai_mock(MOCK_PRESCAN), _make_ai_mock(MOCK_EXTRACT),
            _make_ai_mock(MOCK_DETECT),  _make_ai_mock(MOCK_FAIR),
            _make_ai_mock(MOCK_FAIRNESS),_make_ai_mock(MOCK_EXPLAIN),
            _make_ai_mock(MOCK_RISK),
        ]
        mock_text.return_value = (MOCK_APPEAL, services.PROVIDER_GEMINI)

        result = services.run_full_pipeline(DECISION_TEXT, "job")
        report_id = result.get("id")
        fetched   = services.get_report_by_id(report_id)
        assert fetched is not None
        assert fetched["risk_score"] > 0

    @patch("services._ai_call_text")
    @patch("services._ai_call_json")
    def test_progress_callback_called(self, mock_json, mock_text):
        mock_json.side_effect = [
            _make_ai_mock(MOCK_PRESCAN), _make_ai_mock(MOCK_EXTRACT),
            _make_ai_mock(MOCK_DETECT),  _make_ai_mock(MOCK_FAIR),
            _make_ai_mock(MOCK_FAIRNESS),_make_ai_mock(MOCK_EXPLAIN),
            _make_ai_mock(MOCK_RISK),
        ]
        mock_text.return_value = (MOCK_APPEAL, services.PROVIDER_GEMINI)

        calls = []
        def cb(step, label): calls.append((step, label))

        services.run_full_pipeline(DECISION_TEXT, "job", progress_callback=cb)
        assert len(calls) >= 6
        assert calls[0][0] == 0  # Step 0 first


class TestAggregateReporting:
    @patch("services._ai_call_json")
    def test_generate_model_bias_report_empty(self, _):
        result = services.generate_model_bias_report([])
        assert result == {}

    def test_generate_model_bias_report_basic(self):
        reports = [
            {"bias_found":True,"severity":"high","bias_types":["Gender"],"fairness_scores":{"overall_fairness_score":30,"fairness_verdict":"unfair"},"characteristic_weights":{},"risk_score":72,"urgency_tier":"high","created_at":"2025-01-01T10:00:00","disability_bias":False,"escalation_flag":True},
            {"bias_found":False,"severity":"low","bias_types":[],"fairness_scores":{},"characteristic_weights":{},"risk_score":0,"urgency_tier":"low","created_at":"2025-01-02T10:00:00","disability_bias":False,"escalation_flag":False},
        ]
        result = services.generate_model_bias_report(reports)
        assert result["total_decisions"] == 2
        assert result["biased_decisions"] == 1
        assert result["bias_rate"] == 50
        assert result["escalated_cases"] == 1

    def test_sample_dataset_v20_has_disability_cases(self):
        csv_data = services.generate_sample_dataset()
        assert "disability" in csv_data.lower() or "accessibility" in csv_data.lower()
        assert "medical leave" in csv_data.lower()


# ─────────────────────────────────────────────
# PROVIDER / RESILIENCE TESTS
# ─────────────────────────────────────────────

class TestProviderFallback:
    def test_backoff_delay_values(self):
        """Verify exponential backoff doubles each attempt."""
        import time
        delays = []
        original_sleep = time.sleep
        captured = []
        def mock_sleep(n): captured.append(n)
        time.sleep = mock_sleep

        try:
            services._backoff_delay(1)
            services._backoff_delay(2)
            services._backoff_delay(3)
        finally:
            time.sleep = original_sleep

        assert len(captured) == 3
        assert captured[0] == 1.0    # 1.0 * 2^0
        assert captured[1] == 2.0    # 1.0 * 2^1
        assert captured[2] == 4.0    # 1.0 * 2^2

    def test_vertex_available_false_when_no_project(self):
        original = os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        try:
            assert services.vertex_available() is False
        finally:
            if original: os.environ["GOOGLE_CLOUD_PROJECT"] = original

    def test_vertex_available_true_when_project_set(self):
        os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"
        try:
            assert services.vertex_available() is True
        finally:
            del os.environ["GOOGLE_CLOUD_PROJECT"]