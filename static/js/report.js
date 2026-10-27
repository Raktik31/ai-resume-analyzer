/**
 * AI Resume Analyzer - Editorial Report Generator & Export Utilities
 * Produces structured Markdown / Plain Text proofing desk reports and triggers print.
 */

export function buildMarkdownReport(data) {
  if (!data) return "";

  const filename = data.metadata?.filename || "Resume";
  const dateStr = new Date(data.timestamp || Date.now()).toUTCString();
  const score = data.match?.overall_score ?? 0;
  const verdict = data.match?.verdict || "";
  const breakdown = data.match?.scoring_breakdown || {};
  const skills = data.match?.skills || {};
  const ats = data.ats_check || {};
  const improver = data.improvement_assistant || {};
  const ai = data.ai_suggestions || {};

  let md = `# AI RESUME ANALYZER EDITORIAL REPORT
================================================================================
Document: ${filename}
Generated: ${dateStr}
Evaluation: ${verdict}
Overall Alignment Score: ${score}%

--------------------------------------------------------------------------------
01. SCORING METHODOLOGY & BREAKDOWN
--------------------------------------------------------------------------------
Formula: ${breakdown.formula || "60% Skill Overlap + 40% TF-IDF Cosine Similarity"}
- Skill Coverage Overlap: ${breakdown.skill_coverage_score ?? 0}% (Weight: 60%)
- TF-IDF Cosine Similarity: ${breakdown.tfidf_cosine_score ?? 0}% (Weight: 40%)
- Matched Skills Count: ${skills.matched_count ?? 0}
- Missing Required Skills: ${skills.missing_count ?? 0}
- Additional Candidate Skills: ${skills.extra_count ?? 0}

--------------------------------------------------------------------------------
02. KEYWORD & SKILLS AUDIT
--------------------------------------------------------------------------------
[✓] Matched Skills:
${(skills.matched || []).map(s => `  * ${s}`).join("\n") || "  None detected."}

[✗] Missing Required Skills:
${(skills.missing || []).map(s => `  * ${s}`).join("\n") || "  None! All JD skills matched."}

[+] Additional Skills Present:
${(skills.extra || []).slice(0, 15).map(s => `  * ${s}`).join("\n") || "  None"}

--------------------------------------------------------------------------------
03. ATS (APPLICANT TRACKING SYSTEM) AUDIT
--------------------------------------------------------------------------------
Overall ATS Score: ${ats.score ?? 0}/100
Status Summary: ${ats.summary || "Complete"}

Checklist:
${(ats.checklist || []).map(item => `  [${item.status.toUpperCase()}] ${item.title}: ${item.message}\n    Recommendation: ${item.recommendation}`).join("\n\n")}

--------------------------------------------------------------------------------
04. RESUME IMPROVEMENT ASSISTANT
--------------------------------------------------------------------------------
Metric Coverage: ${improver.metric_coverage_percentage ?? 0}% of analyzed statements contain quantified metrics.
Passive / Weak Phrasing Detected: ${improver.weak_verb_count ?? 0} occurrences.

Weak Verb Findings:
${(improver.weak_verbs_detected || []).map(wv => `  * Found "${wv.weak_phrase}":\n    Sentence: "${wv.sentence_snippet}"\n    Actionable replacement: ${wv.suggested_alternatives.join(", ")}`).join("\n\n") || "  No weak action verbs detected."}

--------------------------------------------------------------------------------
05. EDITOR'S NOTES & AI SUGGESTIONS
--------------------------------------------------------------------------------
Executive Summary:
${ai.executive_summary || "N/A"}

Actionable Recommendations:
${(ai.actionable_suggestions || []).map((s, i) => `  ${i + 1}. ${s}`).join("\n") || "  N/A"}

Rewritten Bullet Points (Before vs After):
${(ai.rewritten_bullets || []).map((b, i) => `  Revision #${i + 1}:
    [BEFORE] ${b.original}
    [AFTER ] ${b.rewritten}
    [NOTE  ] ${b.rationale}`).join("\n\n") || "  N/A"}

Suggested Tailored Professional Summary:
${ai.tailored_professional_summary || "N/A"}

================================================================================
Report produced by AI Resume Analyzer - A second pair of eyes on your resume.
`;

  return md;
}

export function downloadReport(data) {
  const content = buildMarkdownReport(data);
  const filename = (data.metadata?.filename?.replace(/\.pdf$/i, "") || "resume") + "_ai_resume_analyzer_report.md";

  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function triggerPrint() {
  window.print();
}
