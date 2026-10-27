"""Tests for skills taxonomy loading, alias resolution, and skill extraction."""

import pytest
from services.skills import (
    compute_category_coverage,
    compute_skill_overlap,
    extract_skills,
    load_taxonomy,
)


def test_taxonomy_loading():
    tax = load_taxonomy()
    assert "categories" in tax
    assert "aliases" in tax
    assert len(tax["canonical_skills"]) >= 300
    assert "Programming Languages" in tax["categories"]
    assert "Cloud & DevOps" in tax["categories"]


def test_alias_resolution():
    text = "Proficient in JS, TS, py, k8s, and ML frameworks."
    result = extract_skills(text)
    skills = result["skills"]

    assert "JavaScript" in skills
    assert "TypeScript" in skills
    assert "Python" in skills
    assert "Kubernetes" in skills
    assert "Machine Learning" in skills


def test_special_symbols_and_boundaries():
    text = "Developed applications using C++, C#, .NET, Node.js, and CI/CD pipelines."
    result = extract_skills(text)
    skills = result["skills"]

    assert "C++" in skills
    assert "C#" in skills
    assert "Node.js" in skills
    assert "CI/CD" in skills


def test_category_coverage_calculation():
    """Verify category coverage calculations for required ratios.

    0/2 gives 0%
    1/2 gives 50%
    2/2 gives 100%
    0/0 gives n/a
    """
    # 0/2 gives 0%
    res_0_2 = compute_category_coverage(0, 2)
    assert res_0_2["ratio"] == 0.0
    assert res_0_2["percentage"] == 0
    assert res_0_2["text"] == "0%"
    assert res_0_2["is_na"] is False

    # 1/2 gives 50%
    res_1_2 = compute_category_coverage(1, 2)
    assert res_1_2["ratio"] == 0.5
    assert res_1_2["percentage"] == 50
    assert res_1_2["text"] == "50%"
    assert res_1_2["is_na"] is False

    # 2/2 gives 100%
    res_2_2 = compute_category_coverage(2, 2)
    assert res_2_2["ratio"] == 1.0
    assert res_2_2["percentage"] == 100
    assert res_2_2["text"] == "100%"
    assert res_2_2["is_na"] is False

    # 0/0 gives n/a
    res_0_0 = compute_category_coverage(0, 0)
    assert res_0_0["ratio"] == 0.0
    assert res_0_0["percentage"] == 0
    assert res_0_0["text"] == "n/a"
    assert res_0_0["is_na"] is True


def test_skill_overlap_computation():
    resume_skills = ["Python", "Flask", "PostgreSQL", "Docker", "Git"]
    jd_skills = ["Python", "Flask", "PostgreSQL", "Kubernetes", "AWS"]

    overlap = compute_skill_overlap(resume_skills, jd_skills)

    assert set(overlap["matched"]) == {"Python", "Flask", "PostgreSQL"}
    assert set(overlap["missing"]) == {"Kubernetes", "AWS"}
    assert set(overlap["extra"]) == {"Docker", "Git"}
    # Matched 3 out of 5 JD skills = 60% ratio
    assert pytest.approx(overlap["match_ratio"], 0.01) == 0.60
    assert "Programming Languages" in overlap["coverage_by_category"]

    prog = overlap["coverage_by_category"]["Programming Languages"]
    assert prog["jd_count"] == 1
    assert prog["matched_count"] == 1
    assert prog["ratio"] == 1.0
    assert prog["percentage"] == 100
    assert prog["coverage_text"] == "100%"

    # For a category where JD has 0 skills but resume has skills (e.g. Docker/Git in DevOps):
    # If JD had 0 cloud skills, coverage should be n/a, NOT 100%
    devops = overlap["coverage_by_category"]["Cloud & DevOps"]
    # JD had Kubernetes and AWS (2 skills), resume had Docker (0 matched out of 2)
    assert devops["jd_count"] == 2
    assert devops["matched_count"] == 0
    assert devops["ratio"] == 0.0
    assert devops["percentage"] == 0
    assert devops["coverage_text"] == "0%"


def test_skill_overlap_zero_jd_category():
    """Verify that if JD has 0 skills in a category, coverage is n/a, never 100%."""
    resume_skills = ["Python", "JavaScript"]  # Has Programming Languages
    jd_skills = ["Docker", "Kubernetes"]      # Only Cloud & DevOps

    overlap = compute_skill_overlap(resume_skills, jd_skills)
    cov = overlap["coverage_by_category"]

    # Programming Languages: JD has 0, Resume has 2
    prog = cov["Programming Languages"]
    assert prog["jd_count"] == 0
    assert prog["matched_count"] == 0
    assert prog["is_na"] is True
    assert prog["coverage_text"] == "n/a"
    assert prog["ratio"] == 0.0
    assert prog["percentage"] == 0
