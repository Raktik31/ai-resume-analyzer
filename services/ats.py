"""ATS (Applicant Tracking System) friendliness and structure evaluation engine.

Checks:
- Mandatory section headers presence (Contact, Education, Experience, Skills, Projects)
- Contact details validity (valid email, phone number)
- Resume length and word volume (optimal 400-1000 words)
- Suspected table or multi-column layout artifacts (abnormally short line fragmentation)
- Date format consistency across experience and education entries
- Professional links (LinkedIn, GitHub/portfolio) presence
- Calculates a weighted ATS Readiness Score (0-100) and produces an editorial checklist.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def check_date_consistency(text: str) -> Tuple[bool, str]:
    """Detect if the resume mixes disparate date formats arbitrarily."""
    # Pattern A: MM/YYYY or MM/YY (e.g. 05/2021)
    pat_slash = re.findall(r"\b(0[1-9]|1[0-2])\/\d{2,4}\b", text)
    # Pattern B: Month Full/Abbr YYYY (e.g. May 2021, Jan 2022)
    pat_month_year = re.findall(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b",
        text,
        re.IGNORECASE,
    )
    # Pattern C: YYYY-MM (e.g. 2021-05)
    pat_iso = re.findall(r"\b\d{4}-(?:0[1-9]|1[0-2])\b", text)
    # Pattern D: Year only (e.g. 2020 - 2024)
    pat_year_only = re.findall(r"\b(19\d{2}|20\d{2})\s*[-–—]\s*(19\d{2}|20\d{2})\b", text)

    distinct_styles = 0
    if len(pat_slash) >= 2:
        distinct_styles += 1
    if len(pat_month_year) >= 2:
        distinct_styles += 1
    if len(pat_iso) >= 2:
        distinct_styles += 1

    if distinct_styles > 1:
        return False, "Mixed date conventions detected (e.g. both '05/2021' and 'May 2021'). Standardize to one format for optimal ATS parsing."
    return True, "Consistent date format throughout the document."


def check_table_or_column_fragmentation(text: str) -> Tuple[bool, str]:
    """Detect if multi-column tables caused unnatural line fragmentation during extraction."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return True, "Standard line flow detected."

    # Very short lines (< 20 chars) that are not headings or bullets
    short_lines = [l for l in lines if len(l) < 20 and not l.startswith(("-", "•", "*"))]
    ratio = len(short_lines) / len(lines)

    if ratio > 0.40 and len(lines) > 20:
        return (
            False,
            "Suspected complex multi-column or table layout. Text has fragmented into many short disconnected lines, which can confuse ATS parsers.",
        )
    return True, "Clean single-column flow detected with minimal layout fragmentation."


def evaluate_ats_readiness(
    full_text: str,
    parsed_resume: Dict[str, Any],
) -> Dict[str, Any]:
    """Run comprehensive ATS friendliness audit.

    Args:
        full_text: Plain text of resume.
        parsed_resume: Structured dictionary output from parse_resume.

    Returns:
        Dict with overall ATS score (0-100), breakdown checklist, and summary.
    """
    contacts = parsed_resume.get("contacts", {})
    sections = parsed_resume.get("sections", {})
    words = full_text.split()
    word_count = len(words)

    checklist: List[Dict[str, Any]] = []
    points_earned = 0
    total_possible_points = 100

    # 1. Contact Information - Email (15 pts)
    if contacts.get("email"):
        points_earned += 15
        checklist.append({
            "id": "contact_email",
            "title": "Email Address",
            "status": "pass",
            "message": f"Found valid contact email: {contacts['email']}",
            "recommendation": "Keep email clearly visible near the top of page one.",
        })
    else:
        checklist.append({
            "id": "contact_email",
            "title": "Email Address",
            "status": "fail",
            "message": "No standard email address detected.",
            "recommendation": "Add a professional email address (e.g. name@domain.com) in your header.",
        })

    # 2. Contact Information - Phone (10 pts)
    if contacts.get("phone"):
        points_earned += 10
        checklist.append({
            "id": "contact_phone",
            "title": "Phone Number",
            "status": "pass",
            "message": f"Found valid phone number: {contacts['phone']}",
            "recommendation": "Ensure your country code is included for international/remote applications.",
        })
    else:
        checklist.append({
            "id": "contact_phone",
            "title": "Phone Number",
            "status": "fail",
            "message": "No phone number detected.",
            "recommendation": "Include a standard 10-digit or international formatted telephone number.",
        })

    # 3. Professional Profiles (LinkedIn / GitHub) (10 pts)
    has_linkedin = bool(contacts.get("linkedin"))
    has_github = bool(contacts.get("github") or contacts.get("websites"))
    if has_linkedin and has_github:
        points_earned += 10
        checklist.append({
            "id": "online_profiles",
            "title": "Online Profiles & Portfolio",
            "status": "pass",
            "message": "Both LinkedIn and GitHub/portfolio profiles detected.",
            "recommendation": "Keep public repositories and profile headlines up to date.",
        })
    elif has_linkedin or has_github:
        points_earned += 6
        checklist.append({
            "id": "online_profiles",
            "title": "Online Profiles & Portfolio",
            "status": "warn",
            "message": "Only one professional profile detected (missing either LinkedIn or GitHub).",
            "recommendation": "Add both your LinkedIn URL and GitHub profile or personal portfolio.",
        })
    else:
        checklist.append({
            "id": "online_profiles",
            "title": "Online Profiles & Portfolio",
            "status": "fail",
            "message": "Neither LinkedIn nor GitHub profile URLs were found.",
            "recommendation": "Include clickable hyperlinks to your LinkedIn and GitHub profiles.",
        })

    # 4. Core Standard Sections (25 pts - 5 pts each)
    section_checks = [
        ("has_education", "Education Section", "Education section with degrees and academic background."),
        ("has_experience", "Work Experience", "Professional work or internship experience section."),
        ("has_skills", "Skills Section", "Categorized technical or domain skills section."),
        ("has_projects", "Projects Section", "Key projects or portfolio showcase section."),
        ("has_summary", "Professional Summary", "Introductory summary or career objective block."),
    ]

    for key, name, desc in section_checks:
        present = sections.get(key, False)
        if present:
            points_earned += 5
            checklist.append({
                "id": f"sec_{key}",
                "title": name,
                "status": "pass",
                "message": f"{name} detected with standard naming.",
                "recommendation": "Maintain conventional heading terminology for seamless indexing.",
            })
        else:
            status = "warn" if key == "has_summary" else "fail"
            checklist.append({
                "id": f"sec_{key}",
                "title": name,
                "status": status,
                "message": f"{name} could not be identified using standard heading keywords.",
                "recommendation": f"Add an explicit '{name}' heading to avoid ATS parser misclassification.",
            })

    # 5. Length & Word Count Check (15 pts)
    if 350 <= word_count <= 1100:
        points_earned += 15
        checklist.append({
            "id": "word_count",
            "title": "Document Length",
            "status": "pass",
            "message": f"Ideal document length ({word_count} words, approx 1-2 standard pages).",
            "recommendation": "Maintain concise, high-density bullet points.",
        })
    elif word_count < 250:
        checklist.append({
            "id": "word_count",
            "title": "Document Length",
            "status": "fail",
            "message": f"Resume is unusually brief ({word_count} words).",
            "recommendation": "Expand your project details, technical skills, and key accomplishments to at least 350 words.",
        })
    elif word_count < 350:
        points_earned += 8
        checklist.append({
            "id": "word_count",
            "title": "Document Length",
            "status": "warn",
            "message": f"Resume is on the shorter side ({word_count} words).",
            "recommendation": "Consider elaborating on project impacts and methodologies.",
        })
    else:
        points_earned += 10
        checklist.append({
            "id": "word_count",
            "title": "Document Length",
            "status": "warn",
            "message": f"Document is fairly long ({word_count} words).",
            "recommendation": "Keep the resume under 1000 words unless you have 8+ years of relevant experience.",
        })

    # 6. Date Consistency (15 pts)
    date_ok, date_msg = check_date_consistency(full_text)
    if date_ok:
        points_earned += 15
        checklist.append({
            "id": "date_consistency",
            "title": "Date Format Consistency",
            "status": "pass",
            "message": date_msg,
            "recommendation": "Consistent chronologies prevent timeline calculation errors in ATS systems.",
        })
    else:
        points_earned += 6
        checklist.append({
            "id": "date_consistency",
            "title": "Date Format Consistency",
            "status": "warn",
            "message": date_msg,
            "recommendation": "Adopt a single standard date format across all roles (e.g., 'MMM YYYY' or 'YYYY').",
        })

    # 7. Layout & Column Flow Check (10 pts)
    flow_ok, flow_msg = check_table_or_column_fragmentation(full_text)
    if flow_ok:
        points_earned += 10
        checklist.append({
            "id": "layout_flow",
            "title": "Layout & Flow Structure",
            "status": "pass",
            "message": flow_msg,
            "recommendation": "Standard single-column flow ensures the highest reliability in ATS parsers.",
        })
    else:
        points_earned += 3
        checklist.append({
            "id": "layout_flow",
            "title": "Layout & Flow Structure",
            "status": "warn",
            "message": flow_msg,
            "recommendation": "Avoid nested tables or multi-column grids that fracture text ordering when parsed.",
        })

    ats_score = max(0, min(100, points_earned))

    # Pass / Warn / Fail count
    passed_count = sum(1 for c in checklist if c["status"] == "pass")
    warn_count = sum(1 for c in checklist if c["status"] == "warn")
    fail_count = sum(1 for c in checklist if c["status"] == "fail")

    summary_text = (
        f"ATS readiness score: {ats_score}/100. "
        f"{passed_count} checks passed, {warn_count} warnings, {fail_count} critical fixes required."
    )

    return {
        "score": ats_score,
        "checklist": checklist,
        "passed_count": passed_count,
        "warning_count": warn_count,
        "fail_count": fail_count,
        "summary": summary_text,
    }
