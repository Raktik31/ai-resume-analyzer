"""Tests for ATS readiness scoring and resume improvement assistant."""

from services.ats import evaluate_ats_readiness
from services.improver import analyze_improvements
from services.parser import parse_resume


def test_ats_readiness_evaluation():
    sample = """
    Alex Chen
    alex@example.com | (555) 123-4567 | linkedin.com/in/alexchen | github.com/alexchen

    SUMMARY
    Experienced engineer with focus on backend distributed systems.

    EDUCATION
    B.Tech in Computer Science, BPPIMT 2018 - 2022

    EXPERIENCE
    Software Engineer at TechCorp (2022 - Present)
    - Architected REST APIs

    SKILLS
    Python, Flask, Docker, PostgreSQL

    PROJECTS
    Redline Analyzer
    - ATS proofing tool
    """
    parsed = parse_resume(sample)
    ats = evaluate_ats_readiness(sample, parsed)

    assert ats["score"] > 60
    assert ats["passed_count"] >= 5
    # Check that contact items passed
    email_check = next(c for c in ats["checklist"] if c["id"] == "contact_email")
    assert email_check["status"] == "pass"


def test_weak_verbs_and_metrics_detection():
    sample_bullets = """
    EXPERIENCE
    - Responsible for writing backend code and fixing bugs.
    - Worked on microservices with the frontend team.
    - Helped maintain PostgreSQL database servers.
    - Engineered high-concurrency ingestion pipeline delivering 45,000 requests per second.
    """
    improver = analyze_improvements(sample_bullets)

    assert improver["weak_verb_count"] >= 3
    phrases = [w["weak_phrase"] for w in improver["weak_verbs_detected"]]
    assert "responsible for" in phrases
    assert "worked on" in phrases
    assert "helped" in phrases

    # Check metrics detection
    assert improver["missing_metrics_count"] >= 1
