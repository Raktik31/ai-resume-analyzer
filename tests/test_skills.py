"""Tests for skills taxonomy loading, alias resolution, and skill extraction."""

import pytest
from services.skills import compute_skill_overlap, extract_skills, load_taxonomy


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
