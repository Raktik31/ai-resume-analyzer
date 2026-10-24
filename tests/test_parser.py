"""Tests for structured resume section, contact, and entity parser."""

from services.parser import (
    extract_contacts,
    parse_education,
    parse_experience,
    parse_projects,
    parse_resume,
    split_sections,
)


def test_extract_contacts():
    text = """
    Jane Smith
    Email: jane.smith@example.com
    Phone: +1 (555) 345-6789
    LinkedIn: https://www.linkedin.com/in/janesmith-dev
    GitHub: github.com/janesmith-dev
    Portfolio: https://janesmith.io
    """
    contacts = extract_contacts(text)
    assert contacts["email"] == "jane.smith@example.com"
    assert "555" in contacts["phone"]
    assert contacts["linkedin_handle"] == "janesmith-dev"
    assert contacts["github_handle"] == "janesmith-dev"
    assert any("janesmith.io" in w for w in contacts["websites"])


def test_split_sections():
    text = """
    Jane Smith
    jane@example.com

    PROFESSIONAL SUMMARY
    Senior backend architect with 5 years experience.

    TECHNICAL SKILLS
    Python, Flask, PostgreSQL, Docker

    EXPERIENCE
    Software Engineer at Acme Corp (2021 - Present)
    - Built scalable microservices

    EDUCATION
    B.Tech in Computer Science
    BPPIMT, 2017 - 2021
    """
    sections = split_sections(text)
    assert "summary" in sections
    assert "skills" in sections
    assert "experience" in sections
    assert "education" in sections
    assert "Acme Corp" in sections["experience"]


def test_parse_education_details():
    edu_text = """
    B.Tech in Computer Science & Engineering
    B.P. Poddar Institute of Management and Technology, 2018 - 2022
    CGPA: 8.9 / 10.0
    """
    entries = parse_education(edu_text)
    assert len(entries) >= 1
    assert "B.Tech" in entries[0]["degree"]
    assert entries[0]["year"] is not None
    assert "8.9" in entries[0]["gpa"]


def test_parse_experience_details():
    exp_text = """
    Senior Python Developer
    CloudScale Technologies | Jan 2022 - Present
    - Designed REST API microservices with Flask and FastAPI
    - Optimized SQL queries and reduced latency by 30%
    """
    entries = parse_experience(exp_text)
    assert len(entries) >= 1
    assert "Senior Python Developer" in entries[0]["title"]
    assert len(entries[0]["bullets"]) >= 2


def test_parse_resume_graceful_degradation():
    minimal_text = "Just a short paragraph with minimal info and no formal headers."
    parsed = parse_resume(minimal_text)
    assert parsed["contacts"]["email"] is None
    assert parsed["sections"]["has_education"] is False
    assert parsed["sections"]["has_experience"] is False
    assert isinstance(parsed["education"], list)
    assert isinstance(parsed["experience"], list)
