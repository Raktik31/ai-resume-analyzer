"""Resume improvement assistant: weak verb analysis, missing metrics, and action-verb enhancement.

Identifies passive or weak phrasing (e.g. "responsible for", "worked on", "helped")
and flags bullet points lacking measurable metrics or quantified outcomes.
Provides concrete replacements using strong action verbs and quantified impact formulas.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


WEAK_VERBS_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "responsible for": {
        "alternatives": ["Spearheaded", "Directed", "Executed", "Orchestrated", "Delivered"],
        "advice": "Replace passive responsibility with proactive ownership and specific scope.",
    },
    "worked on": {
        "alternatives": ["Engineered", "Architected", "Developed", "Implemented", "Constructed"],
        "advice": "State exactly what you built, optimized, or delivered instead of general participation.",
    },
    "helped": {
        "alternatives": ["Collaborated to deliver", "Facilitated", "Accelerated", "Partnered with"],
        "advice": "Highlight your distinct contribution to the team effort rather than minimizing it.",
    },
    "assisted with": {
        "alternatives": ["Co-engineered", "Bolstered", "Facilitated", "Reinforced"],
        "advice": "Specify your concrete deliverable rather than describing yourself as an assistant.",
    },
    "handled": {
        "alternatives": ["Managed", "Resolved", "Administered", "Streamlined", "Processed"],
        "advice": "Use a verb that specifies how you improved or maintained the process.",
    },
    "participated in": {
        "alternatives": ["Contributed to", "Co-developed", "Spearheaded workstreams in", "Delivered"],
        "advice": "Focus on the specific milestones or modules you authored.",
    },
    "duties included": {
        "alternatives": ["Led", "Owned", "Executed", "Delivered", "Maintained"],
        "advice": "Avoid job description language. State accomplishments, not assigned tasks.",
    },
    "tasked with": {
        "alternatives": ["Commissioned to", "Appointed to engineer", "Delivered", "Pioneered"],
        "advice": "Frame assignments as successful missions completed rather than passive tasks.",
    },
    "involved in": {
        "alternatives": ["Built key components of", "Steered", "Designed", "Shipped"],
        "advice": "Clarify your direct architectural or code ownership.",
    },
    "supported": {
        "alternatives": ["Maintained", "Sustained", "Bolstered", "Optimized infrastructure for"],
        "advice": "Clarify whether support meant troubleshooting, automation, or feature development.",
    },
    "utilized": {
        "alternatives": ["Leveraged", "Employed", "Applied", "Integrated"],
        "advice": "'Utilized' is filler; state why you chose the tool and the resulting outcome.",
    },
    "attempted to": {
        "alternatives": ["Pioneered", "Prototyped", "Researched and evaluated"],
        "advice": "Highlight experimental findings or prototypes rather than implying incomplete work.",
    },
}

# Regex to detect metrics, percentages, numbers, units
METRIC_REGEX = re.compile(
    r"(?:\b\d+(?:\.\d+)?%|\$\s*\d+|\b\d+(?:,\d{3})*(?:\+)?\s*(?:users|clients|requests|ms|seconds|minutes|hours|days|percent|gb|tb|qps|x\b)|reduced\s+by\s+\d+|increased\s+by\s+\d+|\b\d+\+?\b)",
    re.IGNORECASE,
)


def extract_bullet_points(text: str) -> List[str]:
    """Extract individual bullet points or distinct achievement lines from text."""
    lines = [l.strip() for l in text.split("\n")]
    bullets: List[str] = []

    for line in lines:
        if not line:
            continue
        # Check standard bullet markers or numbered list
        if line.startswith(("-", "•", "*", "–", "—", "+", "»", "›")) or re.match(r"^\d+[\.\)]\s+", line):
            cleaned = re.sub(r"^[-•*–—+»›\d\.\)]+\s*", "", line).strip()
            if len(cleaned) >= 15:
                bullets.append(cleaned)
        elif len(line) >= 30 and len(line) <= 300 and not line.isupper() and not line.endswith(":"):
            # Could be a narrative bullet without marker
            bullets.append(line)

    return bullets


def analyze_improvements(full_text: str, experience_text: str = "") -> Dict[str, Any]:
    """Scan resume text for weak verbs, missing metrics, and generate editor recommendations.

    Args:
        full_text: Full resume plain text.
        experience_text: Optional subset of text focusing on experience/projects.

    Returns:
        Structured improvement report.
    """
    target_text = experience_text if experience_text and len(experience_text) > 100 else full_text
    bullets = extract_bullet_points(target_text)

    weak_verb_findings: List[Dict[str, Any]] = []
    bullets_missing_metrics: List[Dict[str, Any]] = []
    strong_bullets_count = 0

    seen_verbs = set()

    for idx, bullet in enumerate(bullets):
        bullet_lower = bullet.lower()
        has_metric = bool(METRIC_REGEX.search(bullet))

        # Check for weak verbs
        for weak_verb, meta in WEAK_VERBS_TAXONOMY.items():
            pattern = re.compile(rf"\b{re.escape(weak_verb)}\b", re.IGNORECASE)
            match = pattern.search(bullet)
            if match:
                weak_verb_findings.append({
                    "weak_phrase": weak_verb,
                    "sentence_snippet": bullet,
                    "suggested_alternatives": meta["alternatives"],
                    "advice": meta["advice"],
                    "index": idx + 1,
                })
                seen_verbs.add(weak_verb)

        # Check metric presence
        if not has_metric and len(bullet) > 35:
            bullets_missing_metrics.append({
                "bullet": bullet,
                "index": idx + 1,
                "suggestion": "Quantify this statement with measurable impact (e.g. latency reduced by X%, team of Y members, or Z daily requests served).",
            })
        elif has_metric:
            strong_bullets_count += 1

    total_bullets = len(bullets)
    metric_coverage_pct = round((strong_bullets_count / total_bullets * 100), 1) if total_bullets > 0 else 0.0

    return {
        "weak_verbs_detected": weak_verb_findings[:8],
        "weak_verb_count": len(weak_verb_findings),
        "bullets_missing_metrics": bullets_missing_metrics[:8],
        "missing_metrics_count": len(bullets_missing_metrics),
        "total_bullets_analyzed": total_bullets,
        "metric_coverage_percentage": metric_coverage_pct,
        "editor_summary": (
            f"Found {len(weak_verb_findings)} passive/weak verb occurrences and "
            f"{len(bullets_missing_metrics)} bullet points lacking quantified metrics across "
            f"{total_bullets} evaluated statements."
        ),
    }
