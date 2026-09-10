"""
Unit tests for backend_engine.py — extraction, matching, and scoring logic.

Run with:
    pytest
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend_engine as engine


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------
def test_extract_skills_finds_known_skills():
    text = "Experienced in Python, SQL, and Machine Learning."
    skills = engine.extract_skills(text)
    assert "python" in skills
    assert "sql" in skills
    assert "machine learning" in skills


def test_extract_skills_ignores_unknown_terms():
    text = "Experienced in gardening and pottery."
    skills = engine.extract_skills(text)
    assert skills == []


def test_extract_experience_years_picks_max_value():
    text = "3 years as a junior dev, then 5+ years as a senior engineer."
    assert engine.extract_experience_years(text) == 5.0


def test_extract_experience_years_returns_zero_when_absent():
    assert engine.extract_experience_years("No experience mentioned here.") == 0.0


def test_extract_education_matches_keywords():
    text = "B.Tech in Computer Science from XYZ University."
    edu = engine.extract_education(text)
    assert "b.tech" in edu


def test_extract_github_with_and_without_scheme():
    assert engine.extract_github("Find me at github.com/jdoe") == "https://github.com/jdoe"
    assert engine.extract_github("https://github.com/jdoe") == "https://github.com/jdoe"
    assert engine.extract_github("No github here.") == ""


def test_extract_linkedin():
    text = "Connect: https://www.linkedin.com/in/jane-doe"
    assert "linkedin.com/in/jane-doe" in engine.extract_linkedin(text)
    assert engine.extract_linkedin("No linkedin here.") == ""


def test_extract_summary_uses_header_when_present():
    text = "Objective:\nBuild great software.\n\nSkills\nPython, SQL"
    summary = engine.extract_summary(text)
    assert "Build great software" in summary


# ---------------------------------------------------------------------------
# Matching tests
# ---------------------------------------------------------------------------
def test_match_skills_full_overlap():
    result = engine.match_skills(["python", "sql"], ["python", "sql", "docker"])
    assert result["matched"] == ["python", "sql"]
    assert result["missing"] == []
    assert result["extra_in_resume"] == ["docker"]
    assert result["score_pct"] == 100.0


def test_match_skills_partial_overlap():
    result = engine.match_skills(["python", "sql", "aws"], ["python"])
    assert result["matched"] == ["python"]
    assert result["missing"] == ["aws", "sql"]
    assert round(result["score_pct"], 2) == round(1 / 3 * 100, 2)


def test_match_skills_empty_jd_requirements():
    result = engine.match_skills([], ["python"])
    assert result["score_pct"] == 0.0


def test_match_experience_meets_requirement():
    result = engine.match_experience(3.0, 5.0)
    assert result["meets_requirement"] is True
    assert result["score_pct"] == 100.0


def test_match_experience_below_requirement():
    result = engine.match_experience(4.0, 2.0)
    assert result["meets_requirement"] is False
    assert result["score_pct"] == 50.0


def test_match_experience_no_requirement_specified():
    result = engine.match_experience(0.0, 1.0)
    assert result["score_pct"] == 100.0


def test_match_education_partial():
    result = engine.match_education(["b.tech", "mba"], ["b.tech"])
    assert result["matched"] == ["b.tech"]
    assert result["missing"] == ["mba"]
    assert result["score_pct"] == 50.0


def test_match_summary_identical_text_scores_high():
    text = "Experienced machine learning engineer skilled in NLP and Python."
    result = engine.match_summary(text, text)
    assert result["score_pct"] > 90.0


def test_match_summary_empty_input_scores_zero():
    assert engine.match_summary("", "something") == {"score_pct": 0.0}


# ---------------------------------------------------------------------------
# End-to-end pipeline test
# ---------------------------------------------------------------------------
def test_build_report_produces_expected_shape():
    jd_doc = engine.parse_document(
        "JD", "Requirements: 3+ years Python, SQL. Education: B.Tech."
    )
    resume_doc = engine.parse_document(
        "Candidate", "Summary: 5 years experience in Python. B.Tech graduate."
    )
    report = engine.build_report(jd_doc, resume_doc)

    assert "overall_match_pct" in report
    assert 0 <= report["overall_match_pct"] <= 100
    assert set(report["sections"].keys()) == {"skills", "experience", "education", "summary"}
