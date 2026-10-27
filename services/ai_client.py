"""Google Gemini AI integration service using the google-genai SDK.

Features:
- Reads model from GEMINI_MODEL (default: "gemini-2.5-flash")
- Enforces strict JSON response format
- Defensive parsing with markdown fence stripping
- Comprehensive rule-based fallback engine if API key is missing or call fails/times out
- Guarantees that the app never crashes due to external AI API failures.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.5-flash-lite"


def map_error_to_notice(status_code: Optional[int], exc: Optional[Exception]) -> str:
    """Map exception details to a concise, non-generic, user-facing notice."""
    if not exc:
        return "Request was rejected by the API"
    msg = str(exc).lower()
    if status_code in (401, 403) or "api_key_invalid" in msg or "invalid api key" in msg or "unauthenticated" in msg or "permission_denied" in msg:
        return "Invalid API key"
    if status_code == 404 or "not_found" in msg or "not found" in msg or "no longer available" in msg:
        return "Model not found"
    if status_code in (429, 503) or "resource_exhausted" in msg or "rate limit" in msg or "quota" in msg or "high demand" in msg:
        return "Rate limit reached, try again in a minute"
    if status_code == 400 or "invalid_argument" in msg:
        return "Request was rejected by the API"
    return "Request was rejected by the API"


def build_rule_based_fallback(
    matched_skills: List[str],
    missing_skills: List[str],
    weak_verbs: List[Dict[str, Any]],
    candidate_bullets: List[str],
    ats_checklist: List[Dict[str, Any]],
    score: int,
) -> Dict[str, Any]:
    """Generate high-utility editorial suggestions using local heuristic engines."""
    # 1. Actionable suggestions
    suggestions: List[str] = []

    if missing_skills:
        top_missing = missing_skills[:4]
        suggestions.append(
            f"Bridge Priority Skill Gaps: Incorporate evidence of {', '.join(top_missing)} in your recent projects or work experience sections."
        )

    if weak_verbs:
        first_weak = weak_verbs[0]
        suggestions.append(
            f"Elevate Action Verbs: Replace passive phrasing like '{first_weak['weak_phrase']}' with decisive power verbs such as {', '.join(first_weak['suggested_alternatives'][:3])}."
        )

    # ATS check suggestions
    failed_ats = [c for c in ats_checklist if c.get("status") in ("fail", "warn")]
    if failed_ats:
        for item in failed_ats[:2]:
            suggestions.append(f"ATS Optimization: {item['recommendation']}")

    suggestions.append(
        "Quantify Technical Impact: Benchmark your contributions with metrics (e.g. latency, throughput, scale, efficiency %, or team size)."
    )

    if len(suggestions) < 5:
        suggestions.append(
            "Mirror Keyword Density: Align your technical section headings and project bullet points with the exact terminology in the job description."
        )
    if len(suggestions) < 6:
        suggestions.append(
            "Lead With Results: Re-structure experience bullets to place the outcome first, followed by the technical methodology used."
        )

    # 2. Rewritten bullet points
    rewritten_bullets: List[Dict[str, str]] = []

    # If we found weak verbs in actual bullets, rewrite those
    if weak_verbs:
        for idx, item in enumerate(weak_verbs[:4]):
            orig = item["sentence_snippet"]
            phrase = item["weak_phrase"]
            alt = item["suggested_alternatives"][0]
            # Replace weak verb with strong alternative
            revised = re.sub(rf"\b{re.escape(phrase)}\b", alt, orig, count=1, flags=re.IGNORECASE)
            # Add metric prompt if lacking metrics
            if not re.search(r"\d+", revised):
                revised = f"{revised}, achieving a 25% improvement in delivery speed and operational reliability"
            rewritten_bullets.append({
                "original": orig,
                "rewritten": revised,
                "rationale": f"Replaced passive '{phrase}' with '{alt}' and anchored the claim with quantified business impact.",
            })

    # If not enough bullets, provide standard before/after examples based on matched skills
    if len(rewritten_bullets) < 3:
        top_skill = matched_skills[0] if matched_skills else "software engineering"
        sample_bullets = [
            (
                f"Worked on {top_skill} backend services and fixed bugs.",
                f"Architected and deployed high-throughput {top_skill} services, reducing average response latency by 35% and improving uptime to 99.9%.",
                f"Transformed generic maintenance task into a measurable architectural achievement.",
            ),
            (
                "Responsible for team code reviews and writing tests.",
                "Championed code review standards and test-driven workflows across 6 engineers, boosting test coverage to 88% and cutting production rollbacks.",
                "Replaced passive duty with engineering leadership and measurable quality indicators.",
            ),
            (
                "Helped build data pipelines and database models.",
                "Spearheaded end-to-end data pipeline automation, accelerating daily sync intervals from 4 hours to 18 minutes across 2M+ records.",
                "Emphasized personal ownership, pipeline scale, and direct operational latency reductions.",
            ),
        ]
        for orig, rew, rat in sample_bullets[len(rewritten_bullets):3]:
            rewritten_bullets.append({
                "original": orig,
                "rewritten": rew,
                "rationale": rat,
            })

    # 3. Suggested professional summary
    skills_lead = ", ".join(matched_skills[:3]) if matched_skills else "Modern Software Engineering"
    tailored_summary = (
        f"Results-driven software professional with hands-on proficiency in {skills_lead}. "
        f"Demonstrated history of delivering scalable solutions, architecting reliable systems, "
        f"and collaborating with cross-functional teams to exceed operational milestones. "
        f"Eager to leverage strong technical capabilities to drive measurable impact for this role."
    )

    # 4. Executive summary
    if score >= 75:
        exec_sum = (
            "The candidate possesses a competitive foundation for this position with high alignment "
            "across core proficiencies. Emphasizing quantified metrics and closing secondary skill gaps will finalize interview readiness."
        )
    elif score >= 50:
        exec_sum = (
            "The candidate shows demonstrable aptitude and transferable skills, but lacks direct emphasis "
            "on several critical competencies highlighted in the role requirements."
        )
    else:
        exec_sum = (
            "Significant foundational gaps currently exist between the resume profile and the target job description. "
            "Strategic repositioning and skill alignment are strongly advised."
        )

    return {
        "executive_summary": exec_sum,
        "actionable_suggestions": suggestions[:7],
        "rewritten_bullets": rewritten_bullets[:5],
        "tailored_professional_summary": tailored_summary,
        "ai_powered": False,
        "notice": "Provided via the local analysis engine",
    }


def generate_ai_suggestions(
    resume_text: str,
    jd_text: str,
    matched_skills: List[str],
    missing_skills: List[str],
    weak_verbs: List[Dict[str, Any]],
    candidate_bullets: List[str],
    ats_checklist: List[Dict[str, Any]],
    score: int,
) -> Dict[str, Any]:
    """Call Google Gemini API using google-genai SDK with strict JSON response handling.

    Falls back to heuristic rules if API key is missing or call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    configured_model = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL

    # If no API key is provided, gracefully return local editorial rules
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Using editorial fallback engine.")
        fallback = build_rule_based_fallback(
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            weak_verbs=weak_verbs,
            candidate_bullets=candidate_bullets,
            ats_checklist=ats_checklist,
            score=score,
        )
        fallback["notice"] = "Invalid API key"
        return fallback

    # Candidate models to try in priority order:
    candidate_models: List[str] = []
    for m in [
        configured_model,
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    # Build compact, information-dense prompt
    compact_resume = resume_text[:3500].strip()
    compact_jd = jd_text[:2000].strip()

    weak_samples = [w["sentence_snippet"] for w in weak_verbs[:4]]
    candidate_sample_bullets = candidate_bullets[:5]

    prompt = f"""
You are an exacting hiring manager and executive resume editor.
Evaluate the candidate's resume against the target job description and provide structured JSON improvements.

Target Job Description (Excerpt):
{compact_jd}

Candidate Resume (Excerpt):
{compact_resume}

Match Analysis Context:
- Overall Alignment Score: {score}%
- Matched Skills: {', '.join(matched_skills[:12]) if matched_skills else 'None identified'}
- Missing Required Skills: {', '.join(missing_skills[:12]) if missing_skills else 'None identified'}
- Identified Weak Phrasing / Bullets: {json.dumps(weak_samples or candidate_sample_bullets[:3])}

Output MUST be a single, valid JSON object with EXACTLY this structure:
{{
  "executive_summary": "2-3 sentences evaluating the candidate's alignment from an editor's proofing desk perspective.",
  "actionable_suggestions": [
    "5 to 7 specific, highly concrete suggestions addressing skill gaps, keyword alignment, and positioning."
  ],
  "rewritten_bullets": [
    {{
      "original": "Original weak bullet from candidate resume or weak phrasing",
      "rewritten": "Strong revision using power verb + task + technical tool + quantified metric [X% or numbers]",
      "rationale": "One concise sentence explaining why this edit significantly increases impact."
    }}
  ],
  "tailored_professional_summary": "A 3-4 sentence high-impact professional summary specifically tailored to this job description."
}}
Ensure exactly 5-7 actionable suggestions and 3-5 rewritten bullets. No extra text or conversational filler.
"""

    last_exc: Optional[Exception] = None
    last_status: Optional[int] = None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        for current_model in candidate_models:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2,
                        ),
                    )

                    response_text = response.text or ""
                    # Strip potential markdown formatting if wrapped
                    clean_text = re.sub(r"^```(?:json)?\s*", "", response_text.strip())
                    clean_text = re.sub(r"\s*```$", "", clean_text.strip())

                    parsed = json.loads(clean_text)

                    # Validate expected keys
                    req_keys = [
                        "executive_summary",
                        "actionable_suggestions",
                        "rewritten_bullets",
                        "tailored_professional_summary",
                    ]
                    if not all(k in parsed for k in req_keys):
                        raise ValueError(f"Gemini response missing required keys: {req_keys}")

                    logger.info("Successfully generated AI suggestions using model '%s'.", current_model)
                    return {
                        "executive_summary": str(parsed["executive_summary"]),
                        "actionable_suggestions": list(parsed["actionable_suggestions"])[:7],
                        "rewritten_bullets": list(parsed["rewritten_bullets"])[:5],
                        "tailored_professional_summary": str(parsed["tailored_professional_summary"]),
                        "ai_powered": True,
                        "model_used": current_model,
                        "notice": None,
                    }

                except Exception as exc:
                    last_exc = exc
                    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                    if status_code is not None:
                        try:
                            last_status = int(status_code)
                        except (ValueError, TypeError):
                            last_status = None

                    msg_lower = str(exc).lower()

                    # Handle 429 or 503 rate limiting / temporary spikes: retry with backoff, then fall back
                    if last_status in (429, 503) or "resource_exhausted" in msg_lower or "high demand" in msg_lower:
                        if attempt < max_retries - 1:
                            sleep_time = 1.5 * (attempt + 1)
                            logger.warning(
                                "Rate limit or temporary overload on model %s (status %s). Retrying in %.1fs...",
                                current_model,
                                last_status,
                                sleep_time,
                            )
                            time.sleep(sleep_time)
                            continue
                        else:
                            logger.warning(
                                "Model %s rate limit exceeded. Falling back to next available model.",
                                current_model,
                            )
                            break  # Try next fallback model

                    # Handle 404 (model deprecated or unavailable): immediately fall back to next model
                    elif last_status == 404 or "not_found" in msg_lower or "no longer available" in msg_lower:
                        logger.warning(
                            "Model %s returned 404 NOT_FOUND. Falling back to next model.",
                            current_model,
                        )
                        break

                    # Other client or server errors: break to try next model or report error
                    else:
                        logger.warning(
                            "Model %s failed with %s (status %s).",
                            current_model,
                            type(exc).__name__,
                            last_status,
                        )
                        break

    except Exception as setup_exc:
        last_exc = setup_exc
        last_status = getattr(setup_exc, "status_code", None) or getattr(setup_exc, "code", None)

    # All attempts failed: log real status and message to console (never key or resume text)
    safe_msg = str(last_exc) if last_exc else "Unknown failure"
    if api_key and api_key in safe_msg:
        safe_msg = safe_msg.replace(api_key, "[REDACTED_API_KEY]")
    if resume_text and len(resume_text) > 40 and resume_text[:40] in safe_msg:
        safe_msg = safe_msg.split(resume_text[:30])[0] + " [RESUME_TEXT_REDACTED]"

    logger.error(
        "Gemini AI API call failed. Status code: %s, Message: %s",
        last_status,
        safe_msg,
    )

    specific_reason = map_error_to_notice(last_status, last_exc)
    fallback = build_rule_based_fallback(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        weak_verbs=weak_verbs,
        candidate_bullets=candidate_bullets,
        ats_checklist=ats_checklist,
        score=score,
    )
    fallback["notice"] = specific_reason
    return fallback
