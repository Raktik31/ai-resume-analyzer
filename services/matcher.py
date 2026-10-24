"""Matching engine using Scikit-Learn TF-IDF cosine similarity and skill-keyword overlap.

Scoring methodology:
- TF-IDF Cosine Similarity (40% weight): Measures overall semantic and contextual vocabulary alignment
  between the candidate's resume and the job description using unigram and bigram representations.
- Skill Coverage Overlap (60% weight): Evaluates the direct match between required skills in the job
  description and those present in the resume.

Final Score = (0.60 * Skill Coverage) + (0.40 * TF-IDF Cosine)
Documented and transparently broken down in the response payload.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.skills import compute_skill_overlap, extract_skills, load_taxonomy


# Scoring weights: 60% skill coverage, 40% TF-IDF cosine similarity
WEIGHT_SKILLS = 0.60
WEIGHT_COSINE = 0.40


def preprocess_text(text: str) -> str:
    """Preprocess text for TF-IDF vectorization.

    Cleans URLs, bullet symbols, excessive whitespace, and standardizes casing.
    """
    if not text:
        return ""
    # Remove URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", text)
    # Remove bullet markers and decorative symbols
    cleaned = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219•*–—\-\|\/]", " ", cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.lower()


def compute_tfidf_similarity(resume_text: str, jd_text: str) -> Dict[str, Any]:
    """Compute TF-IDF cosine similarity between resume and job description.

    Returns:
        Dict containing:
            - 'cosine_score': float in [0.0, 1.0]
            - 'shared_terms': List of top terms contributing to the match
    """
    clean_resume = preprocess_text(resume_text)
    clean_jd = preprocess_text(jd_text)

    if not clean_resume or not clean_jd:
        return {"cosine_score": 0.0, "shared_terms": []}

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=5000,
        token_pattern=r"(?u)\b[a-zA-Z0-9_.#+]{2,}\b",
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([clean_resume, clean_jd])
        similarity_val = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        # Clip to [0.0, 1.0]
        similarity_val = max(0.0, min(1.0, similarity_val))

        # Identify top shared words/phrases
        feature_names = np.array(vectorizer.get_feature_names_out())
        resume_vec = tfidf_matrix[0].toarray()[0]
        jd_vec = tfidf_matrix[1].toarray()[0]
        # Multiply weights to find shared salient vocabulary
        shared_product = resume_vec * jd_vec
        top_indices = np.argsort(shared_product)[::-1]

        shared_terms: List[str] = []
        for idx in top_indices[:15]:
            if shared_product[idx] > 0.0:
                shared_terms.append(str(feature_names[idx]))

        return {
            "cosine_score": round(similarity_val, 4),
            "shared_terms": shared_terms,
        }
    except Exception:
        # Graceful fallback if vectorizer cannot find terms
        return {"cosine_score": 0.0, "shared_terms": []}


def generate_verdict(score: int, matched_count: int, missing_count: int) -> str:
    """Generate a sharp, editorial verdict sentence reflecting the match quality."""
    if score >= 85:
        return "Outstanding match. The candidate demonstrates comprehensive coverage of core role competencies with negligible gaps."
    if score >= 70:
        return "Strong alignment. Core technical competencies are well represented, with a small number of addressable gaps."
    if score >= 55:
        return "Moderate match. Foundational skills are present, but key role requirements and targeted tooling are missing."
    if score >= 40:
        return "Partial alignment. The profile touches on related concepts but falls short of several primary prerequisites."
    return "Low alignment. Significant disconnect between candidate experience and role expectations."


def analyze_match(
    resume_text: str,
    jd_text: str,
    taxonomy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute complete match analysis between resume and job description.

    Args:
        resume_text: Extracted resume text.
        jd_text: Target job description text.
        taxonomy: Optional preloaded skills taxonomy.

    Returns:
        Structured match results with overall score, sub-scores, skills, and verdict.
    """
    tax = taxonomy or load_taxonomy()

    # 1. Extract skills from both documents
    resume_skills_info = extract_skills(resume_text, taxonomy=tax)
    jd_skills_info = extract_skills(jd_text, taxonomy=tax)

    # 2. Compute skill overlap
    overlap = compute_skill_overlap(
        resume_skills=resume_skills_info["skills"],
        jd_skills=jd_skills_info["skills"],
        taxonomy=tax,
    )

    # 3. Compute TF-IDF cosine similarity
    tfidf_res = compute_tfidf_similarity(resume_text, jd_text)
    cosine_score = tfidf_res["cosine_score"]

    # 4. Compute composite blended score
    # Skill coverage ratio: matched / required
    skill_coverage = overlap["match_ratio"]

    # If JD lists no recognizable skills from taxonomy, fall back to pure cosine similarity
    if len(jd_skills_info["skills"]) == 0:
        blended = cosine_score
    else:
        blended = (WEIGHT_SKILLS * skill_coverage) + (WEIGHT_COSINE * cosine_score)

    # Scale to 0-100 integer
    overall_score = int(round(blended * 100))
    overall_score = max(0, min(100, overall_score))

    # Match verdict
    verdict = generate_verdict(
        score=overall_score,
        matched_count=len(overlap["matched"]),
        missing_count=len(overlap["missing"]),
    )

    return {
        "overall_score": overall_score,
        "verdict": verdict,
        "scoring_breakdown": {
            "formula": "Final = (60% * Skill Coverage) + (40% * TF-IDF Cosine Similarity)",
            "weights": {
                "skills_weight": WEIGHT_SKILLS,
                "cosine_weight": WEIGHT_COSINE,
            },
            "skill_coverage_score": round(skill_coverage * 100, 1),
            "tfidf_cosine_score": round(cosine_score * 100, 1),
        },
        "skills": {
            "matched": overlap["matched"],
            "missing": overlap["missing"],
            "extra": overlap["extra"],
            "matched_count": len(overlap["matched"]),
            "missing_count": len(overlap["missing"]),
            "extra_count": len(overlap["extra"]),
            "jd_total_skills": len(jd_skills_info["skills"]),
            "resume_total_skills": len(resume_skills_info["skills"]),
            "coverage_by_category": overlap["coverage_by_category"],
        },
        "vocabulary": {
            "shared_salient_terms": tfidf_res["shared_terms"],
        },
    }
