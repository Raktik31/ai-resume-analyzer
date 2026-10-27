"""Skills taxonomy loader, alias normalization, and skill extraction engine.

Handles loading of curated skills taxonomy from data/skills.json, alias resolution,
case-insensitive token and phrase extraction with regex boundary handling for special
characters (e.g. C++, C#, .NET), and category aggregation.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


DEFAULT_SKILLS_PATH = Path(__file__).resolve().parent.parent / "data" / "skills.json"


@lru_cache(maxsize=1)
def load_taxonomy(filepath: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load and cache the skills taxonomy JSON file."""
    path = Path(filepath) if filepath else DEFAULT_SKILLS_PATH
    if not path.exists():
        raise FileNotFoundError(f"Skills taxonomy file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories: Dict[str, List[str]] = data.get("categories", {})
    aliases: Dict[str, str] = {k.lower().strip(): v for k, v in data.get("aliases", {}).items()}

    # Build reverse mapping from canonical skill to category
    skill_to_category: Dict[str, str] = {}
    canonical_skills: Set[str] = set()

    for category, skills in categories.items():
        for skill in skills:
            canonical_skills.add(skill)
            skill_to_category[skill] = category

    return {
        "categories": categories,
        "aliases": aliases,
        "skill_to_category": skill_to_category,
        "canonical_skills": canonical_skills,
    }


BOUNDARY_DELIMS = r"[\s,;:()\[\]{}/\\|•\-'\"<>!?.`]"


def _build_skill_pattern(term: str) -> re.Pattern:
    """Build a robust regex pattern for matching a skill term with boundary awareness.
    
    Handles terms with special characters like C++, C#, .NET, Node.js without
    falling prey to standard \\b word boundary quirks or accidental substring matches.
    """
    escaped = re.escape(term)
    
    # If the term is alphanumeric only (e.g. 'js', 'react', 'python')
    if re.fullmatch(r"[A-Za-z0-9]+", term):
        # Do not match if preceded by word character or dot preceded by word character (e.g. Next.js, script.py)
        pattern_str = rf"(?<![A-Za-z0-9]\.)(?<![A-Za-z0-9])\b{escaped}\b(?![A-Za-z0-9])"
        return re.compile(pattern_str, re.IGNORECASE)

    # For terms with symbols (e.g. 'C++', 'C#', '.NET', 'Node.js', 'CI/CD')
    pattern_str = r"(?:(?<=" + BOUNDARY_DELIMS + r")|\A)" + escaped + r"(?:(?=" + BOUNDARY_DELIMS + r")|\Z)"
    return re.compile(pattern_str, re.IGNORECASE)


def extract_skills(text: str, taxonomy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract all matched skills from the provided text.

    Args:
        text: Resume or job description raw text.
        taxonomy: Optional pre-loaded taxonomy dict.

    Returns:
        Dict containing:
            - 'skills': List of unique canonical skill names detected (alphabetical)
            - 'skills_by_category': Dict mapping category name to list of skills
            - 'category_counts': Dict mapping category name to count
            - 'category_totals': Dict mapping category name to total available skills in taxonomy
            - 'matched_terms': Dict mapping matched text term to canonical skill
    """
    if not text or not text.strip():
        return {
            "skills": [],
            "skills_by_category": {},
            "category_counts": {},
            "category_totals": {},
            "matched_terms": {},
        }

    tax = taxonomy or load_taxonomy()
    categories: Dict[str, List[str]] = tax["categories"]
    aliases: Dict[str, str] = tax["aliases"]
    skill_to_category: Dict[str, str] = tax["skill_to_category"]
    canonical_skills: Set[str] = tax["canonical_skills"]

    # Pre-clean text: normalize non-breaking spaces and common punctuation
    normalized_text = text.replace("\u00a0", " ").replace("\u2013", "-").replace("\u2014", "-")
    # Pad with spaces for boundary matching
    padded_text = f" {normalized_text} "

    found_canonical: Set[str] = set()
    matched_terms: Dict[str, str] = {}

    # Sort all target terms by length descending to match multi-word phrases first
    # 1. First, search for canonical skills
    all_canonicals_sorted = sorted(canonical_skills, key=len, reverse=True)
    for skill in all_canonicals_sorted:
        # Special check for single character skills like "C" or "R"
        if len(skill) == 1:
            single_pattern_str = r"(?:(?<=" + BOUNDARY_DELIMS + r")|(?<=\b))" + re.escape(skill) + r"(?:(?=" + BOUNDARY_DELIMS + r")|(?=\b))"
            pattern = re.compile(single_pattern_str, re.IGNORECASE)
            match = pattern.search(padded_text)
            if match:
                # Extra sanity check for single letter 'C' or 'R'
                c_context = re.search(r"\b(c\s*\/|\/\s*c|c\s*\+\+|objective[\s\-]c|languages?|skills?|c\b)", padded_text, re.IGNORECASE)
                if skill == "C" and not c_context:
                    continue
                found_canonical.add(skill)
                matched_terms[match.group(0).strip()] = skill
        else:
            pat = _build_skill_pattern(skill)
            match = pat.search(padded_text)
            if match:
                found_canonical.add(skill)
                matched_terms[match.group(0).strip()] = skill

    # 2. Search for aliases
    all_aliases_sorted = sorted(aliases.keys(), key=len, reverse=True)
    for alias in all_aliases_sorted:
        canonical_target = aliases[alias]
        if canonical_target in found_canonical:
            continue  # Already identified via canonical name

        pat = _build_skill_pattern(alias)
        match = pat.search(padded_text)
        if match:
            found_canonical.add(canonical_target)
            matched_terms[match.group(0).strip()] = canonical_target

    sorted_skills = sorted(found_canonical)

    # Group skills by category
    skills_by_category: Dict[str, List[str]] = {cat: [] for cat in categories}
    category_counts: Dict[str, int] = {cat: 0 for cat in categories}
    category_totals: Dict[str, int] = {cat: len(skills) for cat, skills in categories.items()}

    for skill in sorted_skills:
        cat = skill_to_category.get(skill, "Core Concepts & Architecture")
        if cat in skills_by_category:
            skills_by_category[cat].append(skill)
            category_counts[cat] += 1

    return {
        "skills": sorted_skills,
        "skills_by_category": skills_by_category,
        "category_counts": category_counts,
        "category_totals": category_totals,
        "matched_terms": matched_terms,
    }


def compute_category_coverage(matched_count: int, total_jd_count: int) -> Dict[str, Any]:
    """Compute skill coverage ratio, percentage, and label for a category.

    Guards against division by zero:
    - 0/2 gives 0%
    - 1/2 gives 50%
    - 2/2 gives 100%
    - 0/0 gives n/a
    """
    if total_jd_count <= 0:
        return {
            "ratio": 0.0,
            "percentage": 0,
            "text": "n/a",
            "is_na": True,
        }

    ratio = matched_count / total_jd_count
    percentage = round(ratio * 100)
    return {
        "ratio": round(ratio, 4),
        "percentage": percentage,
        "text": f"{percentage}%",
        "is_na": False,
    }


def compute_skill_overlap(
    resume_skills: List[str],
    jd_skills: List[str],
    taxonomy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compare resume skills with JD skills.

    Returns:
        Dict with:
            - 'matched': Skills present in both resume and JD
            - 'missing': Skills required by JD but absent in resume
            - 'extra': Skills present in resume not explicitly requested by JD
            - 'match_ratio': Matched / JD skills (0.0 to 1.0)
            - 'coverage_by_category': Match breakdown by category
    """
    tax = taxonomy or load_taxonomy()
    skill_to_cat = tax["skill_to_category"]
    categories = tax["categories"]

    resume_set = set(resume_skills)
    jd_set = set(jd_skills)

    matched = sorted(resume_set.intersection(jd_set))
    missing = sorted(jd_set.difference(resume_set))
    extra = sorted(resume_set.difference(jd_set))

    match_ratio = len(matched) / len(jd_set) if jd_set else (1.0 if resume_set else 0.0)

    # Category coverage breakdown
    coverage_by_category: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        cat_jd_skills = [s for s in jd_set if skill_to_cat.get(s) == cat]
        cat_matched_skills = [s for s in matched if skill_to_cat.get(s) == cat]
        cat_missing_skills = [s for s in missing if skill_to_cat.get(s) == cat]
        cat_resume_skills = [s for s in resume_set if skill_to_cat.get(s) == cat]

        cat_total_jd = len(cat_jd_skills)
        cat_matched_count = len(cat_matched_skills)
        cov = compute_category_coverage(cat_matched_count, cat_total_jd)

        coverage_by_category[cat] = {
            "jd_count": cat_total_jd,
            "matched_count": cat_matched_count,
            "missing_count": len(cat_missing_skills),
            "resume_count": len(cat_resume_skills),
            "ratio": round(cov["ratio"], 3),
            "percentage": cov["percentage"],
            "coverage_text": cov["text"],
            "is_na": cov["is_na"],
            "matched_skills": cat_matched_skills,
            "missing_skills": cat_missing_skills,
        }

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "match_ratio": round(match_ratio, 4),
        "coverage_by_category": coverage_by_category,
    }
