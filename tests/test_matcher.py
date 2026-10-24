"""Tests for matching engine: TF-IDF cosine similarity and weighted scoring."""

import pytest
from services.matcher import (
    analyze_match,
    compute_tfidf_similarity,
    generate_verdict,
    WEIGHT_COSINE,
    WEIGHT_SKILLS,
)


def test_weights_formula_documentation():
    # Verify weights add up to 1.0 (100%)
    assert WEIGHT_SKILLS + WEIGHT_COSINE == 1.0
    assert WEIGHT_SKILLS == 0.60
    assert WEIGHT_COSINE == 0.40


def test_tfidf_cosine_similarity():
    resume = "Experienced Python backend engineer specializing in Flask, PostgreSQL, Docker, and REST APIs."
    jd = "Seeking a Python developer with solid experience in Flask, PostgreSQL, and cloud deployments with Docker."

    tfidf_result = compute_tfidf_similarity(resume, jd)
    score = tfidf_result["cosine_score"]

    assert 0.0 <= score <= 1.0
    assert score > 0.10  # Should show substantial semantic overlap
    assert len(tfidf_result["shared_terms"]) > 0


def test_analyze_match_end_to_end():
    resume = """
    Alex Chen - alex@example.com
    Proficient in Python, Flask, FastAPI, PostgreSQL, Docker, Kubernetes, Git, Redis.
    Built high-throughput REST APIs and microservices. Experience with PyTest and CI/CD.
    """
    jd = """
    Senior Python Developer needed.
    Requirements:
    - 3+ years experience with Python and Flask or FastAPI
    - Strong database skills in PostgreSQL and caching with Redis
    - Containerization with Docker and Kubernetes
    - Good communication and leadership skills
    """

    res = analyze_match(resume, jd)

    assert "overall_score" in res
    assert 0 <= res["overall_score"] <= 100
    assert res["overall_score"] >= 60  # High alignment
    assert "verdict" in res
    assert len(res["skills"]["matched"]) >= 4
    assert "Python" in res["skills"]["matched"]
    assert "PostgreSQL" in res["skills"]["matched"]


def test_verdict_generation():
    v100 = generate_verdict(90, 8, 0)
    assert "Outstanding" in v100

    v75 = generate_verdict(75, 6, 2)
    assert "Strong" in v75

    v30 = generate_verdict(30, 1, 8)
    assert "Low" in v30
