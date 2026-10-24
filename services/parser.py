"""Resume information extraction service.

Extracts structured sections from raw resume text:
- Contact information (email, phone, LinkedIn, GitHub, portfolio)
- Section segmenter (Education, Experience, Projects, Skills, Certifications, Summary)
- Detailed entity extractors for Education (degree, institution, graduation year, GPA)
- Work experience and internships
- Projects (titles, descriptions, tech used)
- Certifications and credentials

Degrades gracefully when sections or entities are missing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Regex patterns for contact information
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}|\b\d{10}\b"
)
LINKEDIN_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|profile)\/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
GITHUB_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?github\.com\/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
URL_REGEX = re.compile(
    r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
    re.IGNORECASE,
)

# Standard degree patterns
DEGREE_PATTERNS = [
    r"\bB\.?\s?Tech(?:nology)?\b",
    r"\bB\.?\s?E\.?\b",
    r"\bB\.?\s?S\.?(?:c)?\b",
    r"\bBachelor(?:'s)?(?:\s+of\s+[A-Za-z\s]+)?\b",
    r"\bM\.?\s?Tech(?:nology)?\b",
    r"\bM\.?\s?E\.?\b",
    r"\bM\.?\s?S\.?(?:c)?\b",
    r"\bMaster(?:'s)?(?:\s+of\s+[A-Za-z\s]+)?\b",
    r"\bPh\.?D\.?\b",
    r"\bDoctorate\b",
    r"\bB\.?\s?C\.?\s?A\.?\b",
    r"\bM\.?\s?C\.?\s?A\.?\b",
    r"\bDiploma\b",
    r"\bAssociate(?:'s)?\b",
    r"\bHigher\s+Secondary\b",
    r"\bClass\s+(?:XII|X|12|10)(?:th)?\b",
]

# Section heading keywords
SECTION_KEYWORDS: Dict[str, List[str]] = {
    "summary": [
        "summary", "professional summary", "executive summary", "profile",
        "about me", "objective", "career objective"
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment history",
        "work history", "internships", "internship experience", "industrial experience"
    ],
    "education": [
        "education", "academic background", "academics", "educational qualification",
        "qualifications", "academic credentials"
    ],
    "projects": [
        "projects", "personal projects", "academic projects", "key projects",
        "technical projects", "selected projects", "open source contributions"
    ],
    "skills": [
        "skills", "technical skills", "skills & tools", "core competencies",
        "technologies", "tech stack", "tools & technologies", "competencies"
    ],
    "certifications": [
        "certifications", "certificates", "licenses & certifications",
        "credentials", "courses", "achievements", "honors & awards"
    ],
}


def extract_contacts(text: str) -> Dict[str, Any]:
    """Extract contact information (email, phone, LinkedIn, GitHub, websites)."""
    email_match = EMAIL_REGEX.search(text)
    phone_match = PHONE_REGEX.search(text)
    linkedin_match = LINKEDIN_REGEX.search(text)
    github_match = GITHUB_REGEX.search(text)

    # Extract all URLs to find personal websites / portfolios
    all_urls = URL_REGEX.findall(text)
    portfolio_urls: List[str] = []
    for u in all_urls:
        u_lower = u.lower()
        if "linkedin.com" not in u_lower and "github.com" not in u_lower:
            portfolio_urls.append(u)

    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "linkedin_handle": linkedin_match.group(1) if linkedin_match else None,
        "github": github_match.group(0) if github_match else None,
        "github_handle": github_match.group(1) if github_match else None,
        "websites": portfolio_urls[:3],
    }


def split_sections(text: str) -> Dict[str, str]:
    """Segment resume text into recognized standard sections.

    Uses a heading detection algorithm that scans line-by-line for header patterns.
    """
    lines = [line.strip() for line in text.split("\n")]
    sections: Dict[str, List[str]] = {k: [] for k in SECTION_KEYWORDS}
    sections["header"] = []  # Content before first known heading

    # Build regexes for each category
    heading_patterns: List[Tuple[str, re.Pattern]] = []
    for cat, aliases in SECTION_KEYWORDS.items():
        sorted_aliases = sorted(aliases, key=len, reverse=True)
        alias_group = "|".join(re.escape(a) for a in sorted_aliases)
        # Heading is either a short standalone line or enclosed in separators/bullets
        pattern = re.compile(
            rf"^(?:[-_=\*#•\s]{{0,4}})?({alias_group})(?:[:\-_=\*#\s]{{0,4}})?$",
            re.IGNORECASE,
        )
        heading_patterns.append((cat, pattern))

    current_section = "header"

    for line in lines:
        if not line:
            if current_section in sections:
                sections[current_section].append("")
            continue

        # Check if line is a section heading (typically short: <= 50 chars)
        matched_category = None
        if len(line) <= 50:
            for cat, pattern in heading_patterns:
                if pattern.match(line):
                    matched_category = cat
                    break

        if matched_category:
            current_section = matched_category
        else:
            sections[current_section].append(line)

    # Convert list of lines to strings
    result: Dict[str, str] = {}
    for cat, line_list in sections.items():
        joined = "\n".join(line_list).strip()
        if joined:
            result[cat] = joined

    return result


def parse_education(section_text: str) -> List[Dict[str, Any]]:
    """Parse education entries from education section text."""
    if not section_text:
        return []

    entries: List[Dict[str, Any]] = []
    # Split text into chunks separated by double newlines or lines containing degrees
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]

    current_entry: Dict[str, Any] = {
        "degree": None,
        "institution": None,
        "year": None,
        "gpa": None,
        "details": [],
    }

    year_regex = re.compile(r"\b(19\d{2}|20\d{2})\s*(?:[-–—to]+\s*(19\d{2}|20\d{2}|present|expected|current))?", re.IGNORECASE)
    gpa_regex = re.compile(r"\b(?:gpa|cgpa|percentage|score)?\s*:?\s*(\d(?:\.\d{1,2})?\s*(?:\/\s*(?:4|5|10))?|\d{2}(?:\.\d{1,2})?\s*%)", re.IGNORECASE)
    inst_regex = re.compile(r"(university|institute|college|school|academy|bppimt|polytechnic)", re.IGNORECASE)

    for line in lines:
        # Check degree
        found_degree = None
        for deg_pat in DEGREE_PATTERNS:
            m = re.search(deg_pat, line, re.IGNORECASE)
            if m:
                found_degree = m.group(0).strip()
                break

        # Check year
        y_match = year_regex.search(line)
        found_year = y_match.group(0).strip() if y_match else None

        # Check GPA
        g_match = gpa_regex.search(line)
        found_gpa = g_match.group(0).strip() if g_match else None

        # Check institution
        is_inst = bool(inst_regex.search(line))

        # If we encounter a new degree or institution when current entry already has one, push entry
        if (found_degree and current_entry["degree"]) or (is_inst and current_entry["institution"]):
            if current_entry["degree"] or current_entry["institution"]:
                entries.append(current_entry)
            current_entry = {
                "degree": None,
                "institution": None,
                "year": None,
                "gpa": None,
                "details": [],
            }

        if found_degree:
            current_entry["degree"] = found_degree
        if is_inst and not current_entry["institution"]:
            current_entry["institution"] = line
        elif not current_entry["institution"] and not found_degree and not found_year:
            # First non-degree line might be the institution
            if any(w in line.lower() for w in ["technology", "engineering", "science", "arts"]):
                current_entry["institution"] = line

        if found_year and not current_entry["year"]:
            current_entry["year"] = found_year
        if found_gpa and not current_entry["gpa"]:
            current_entry["gpa"] = found_gpa

        if not found_degree and not is_inst:
            current_entry["details"].append(line)

    if current_entry["degree"] or current_entry["institution"]:
        entries.append(current_entry)

    # Fallback: if no structured entry could be separated but section exists
    if not entries and section_text:
        first_few = lines[:3]
        entries.append({
            "degree": first_few[0] if first_few else "Education record",
            "institution": first_few[1] if len(first_few) > 1 else None,
            "year": None,
            "gpa": None,
            "details": lines[2:] if len(lines) > 2 else [],
        })

    return entries


def parse_experience(section_text: str) -> List[Dict[str, Any]]:
    """Parse work experience and internships into structured entries."""
    if not section_text:
        return []

    entries: List[Dict[str, Any]] = []
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]

    date_regex = re.compile(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?\s*'?\b(19\d{2}|20\d{2})\s*[-–—to]+\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)?\s*'?\b(19\d{2}|20\d{2})|present|current)\b",
        re.IGNORECASE,
    )
    role_regex = re.compile(
        r"\b(engineer|developer|intern|lead|architect|analyst|manager|specialist|consultant|associate|programmer|scientist|designer)\b",
        re.IGNORECASE,
    )

    current_entry: Dict[str, Any] = {
        "title": None,
        "company": None,
        "duration": None,
        "bullets": [],
    }

    for line in lines:
        is_date = bool(date_regex.search(line))
        is_role = bool(role_regex.search(line))
        is_bullet = line.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+\.", line)

        # Detect new role boundary
        if (is_date or is_role) and len(line) < 100 and not is_bullet:
            if current_entry["title"] or current_entry["bullets"]:
                entries.append(current_entry)
                current_entry = {
                    "title": None,
                    "company": None,
                    "duration": None,
                    "bullets": [],
                }

            if is_date and not current_entry["duration"]:
                current_entry["duration"] = line
            elif is_role and not current_entry["title"]:
                current_entry["title"] = line
            else:
                if not current_entry["company"]:
                    current_entry["company"] = line
        elif is_bullet:
            clean_bullet = re.sub(r"^[-•*–—\d\.]+\s*", "", line).strip()
            if clean_bullet:
                current_entry["bullets"].append(clean_bullet)
        else:
            if not current_entry["title"] and len(line) < 80:
                current_entry["title"] = line
            elif not current_entry["company"] and len(line) < 80:
                current_entry["company"] = line
            else:
                current_entry["bullets"].append(line)

    if current_entry["title"] or current_entry["bullets"]:
        entries.append(current_entry)

    # Fallback
    if not entries and lines:
        entries.append({
            "title": lines[0],
            "company": lines[1] if len(lines) > 1 else None,
            "duration": None,
            "bullets": lines[2:],
        })

    return entries


def parse_projects(section_text: str) -> List[Dict[str, Any]]:
    """Parse projects into structured objects."""
    if not section_text:
        return []

    entries: List[Dict[str, Any]] = []
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]

    current_project: Dict[str, Any] = {
        "title": None,
        "technologies": None,
        "link": None,
        "bullets": [],
    }

    for line in lines:
        is_bullet = line.startswith(("-", "•", "*", "–", "—")) or re.match(r"^\d+\.", line)
        has_url = URL_REGEX.search(line)

        # Pipe or separator often used for project titles e.g. "Redline | Flask, PyMuPDF | github.com/..."
        if ("|" in line or ":" in line) and len(line) < 120 and not is_bullet:
            if current_project["title"] or current_project["bullets"]:
                entries.append(current_project)
                current_project = {
                    "title": None,
                    "technologies": None,
                    "link": None,
                    "bullets": [],
                }
            parts = [p.strip() for p in (line.split("|") if "|" in line else line.split(":"))]
            current_project["title"] = parts[0]
            if len(parts) > 1:
                current_project["technologies"] = parts[1]
            if has_url:
                current_project["link"] = has_url.group(0)
        elif is_bullet:
            clean_bullet = re.sub(r"^[-•*–—\d\.]+\s*", "", line).strip()
            if clean_bullet:
                current_project["bullets"].append(clean_bullet)
        elif len(line) < 70 and not current_project["title"]:
            current_project["title"] = line
        else:
            current_project["bullets"].append(line)

    if current_project["title"] or current_project["bullets"]:
        entries.append(current_project)

    if not entries and lines:
        entries.append({
            "title": lines[0],
            "technologies": None,
            "link": None,
            "bullets": lines[1:],
        })

    return entries


def parse_certifications(section_text: str) -> List[Dict[str, Any]]:
    """Parse certifications, courses, and licenses."""
    if not section_text:
        return []

    entries: List[Dict[str, Any]] = []
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]

    for line in lines:
        clean = re.sub(r"^[-•*–—\d\.]+\s*", "", line).strip()
        if not clean:
            continue
        # Check if year or issuer in line
        parts = re.split(r"[-–|:]", clean)
        name = parts[0].strip()
        issuer = parts[1].strip() if len(parts) > 1 else None
        entries.append({
            "name": name,
            "issuer": issuer,
            "raw": clean,
        })

    return entries


def parse_resume(full_text: str) -> Dict[str, Any]:
    """Complete resume parser: contacts, sections, education, experience, projects, certs.

    Args:
        full_text: Plain text of resume.

    Returns:
        Structured dictionary representation of the resume.
    """
    contacts = extract_contacts(full_text)
    sections = split_sections(full_text)

    education = parse_education(sections.get("education", ""))
    experience = parse_experience(sections.get("experience", ""))
    projects = parse_projects(sections.get("projects", ""))
    certifications = parse_certifications(sections.get("certifications", ""))
    summary = sections.get("summary", "")

    return {
        "contacts": contacts,
        "sections": {
            "has_summary": bool(summary),
            "has_experience": bool(experience or sections.get("experience")),
            "has_education": bool(education or sections.get("education")),
            "has_projects": bool(projects or sections.get("projects")),
            "has_skills": bool(sections.get("skills")),
            "has_certifications": bool(certifications or sections.get("certifications")),
        },
        "summary": summary,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "raw_sections": sections,
    }
