/**
 * Redline - Core Frontend Application Controller
 * Handles file drop, live validation, asynchronous analysis, Chart.js visualization,
 * theme management, and rendering of all manuscript sections.
 */

import { saveToHistory, openHistoryModal, closeHistoryModal } from "./history.js";
import { downloadReport, triggerPrint } from "./report.js";

// Global application state
let currentAnalysisData = null;
let categoryChartInstance = null;
let progressInterval = null;

const PROGRESS_PHRASES = [
  "Reading the page…",
  "Finding the skills…",
  "Comparing with the role…",
  "Auditing ATS structure…",
  "Proofing action verbs…",
  "Consulting the editorial desk…",
];

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initFormInteractions();
  initHistoryControls();
  initReportControls();
});

/* --------------------------------------------------------------------------
   Theme Management (Light / Dark Mode, respects prefers-color-scheme)
   -------------------------------------------------------------------------- */
function initTheme() {
  const themeToggle = document.getElementById("theme-toggle");
  const storedTheme = localStorage.getItem("redline_theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  const currentTheme = storedTheme || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", currentTheme);
  updateThemeButtonLabel(currentTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const active = document.documentElement.getAttribute("data-theme");
      const next = active === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("redline_theme", next);
      updateThemeButtonLabel(next);
      // Re-render chart if active so palette updates
      if (currentAnalysisData && currentAnalysisData.match) {
        renderCategoryChart(currentAnalysisData.match.skills.coverage_by_category);
      }
    });
  }

  // Listen for system OS changes if user hasn't explicitly set preference
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem("redline_theme")) {
      const next = e.matches ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      updateThemeButtonLabel(next);
      if (currentAnalysisData) {
        renderCategoryChart(currentAnalysisData.match.skills.coverage_by_category);
      }
    }
  });
}

function updateThemeButtonLabel(theme) {
  const btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.textContent = theme === "dark" ? "Light theme" : "Dark theme";
    btn.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} theme`);
  }
}

/* --------------------------------------------------------------------------
   Form Interactions, Live Word Counter & Drag-and-Drop
   -------------------------------------------------------------------------- */
function initFormInteractions() {
  const jdInput = document.getElementById("jd-input");
  const wordCountBadge = document.getElementById("word-count-badge");
  const dropSlot = document.getElementById("drop-slot");
  const fileInput = document.getElementById("file-input");
  const fileSelectedLabel = document.getElementById("file-selected-label");
  const analyzeBtn = document.getElementById("analyze-btn");
  const form = document.getElementById("analysis-form");
  const statusBanner = document.getElementById("status-banner");

  // 1. Live Job Description Word Counter
  if (jdInput && wordCountBadge) {
    jdInput.addEventListener("input", () => {
      const text = jdInput.value.trim();
      const words = text ? text.split(/\s+/).length : 0;
      wordCountBadge.textContent = `${words} / 40 words min`;

      if (words >= 40) {
        wordCountBadge.className = "word-count-badge valid";
      } else {
        wordCountBadge.className = "word-count-badge invalid";
      }
    });
  }

  // 2. Drag & Drop Handling
  if (dropSlot && fileInput) {
    // Click to select
    dropSlot.addEventListener("click", () => fileInput.click());

    // Keyboard support (Enter / Space)
    dropSlot.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInput.click();
      }
    });

    // Dragover & dragleave
    ["dragenter", "dragover"].forEach(evt => {
      dropSlot.addEventListener(evt, (e) => {
        e.preventDefault();
        dropSlot.classList.add("dragover");
      });
    });

    ["dragleave", "dragend", "drop"].forEach(evt => {
      dropSlot.addEventListener(evt, (e) => {
        e.preventDefault();
        dropSlot.classList.remove("dragover");
      });
    });

    // Drop file
    dropSlot.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    // File input change
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });
  }

  function handleFileSelection(file) {
    clearStatusMessage();

    // Client-side extension validation
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      showStatusMessage(`"${file.name}" is not a PDF file. Please select a .pdf resume.`, "error");
      fileInput.value = "";
      return;
    }

    // Client-side MIME validation (if reported by browser)
    if (file.type && file.type !== "application/pdf" && file.type !== "application/x-pdf") {
      showStatusMessage(`Invalid file type (${file.type}). Redline only accepts PDF documents.`, "error");
      fileInput.value = "";
      return;
    }

    // Client-side size validation (5 MB max)
    const maxBytes = 5 * 1024 * 1024;
    if (file.size > maxBytes) {
      const mb = (file.size / (1024 * 1024)).toFixed(2);
      showStatusMessage(`File exceeds 5 MB limit (${mb} MB). Please choose a smaller PDF.`, "error");
      fileInput.value = "";
      return;
    }

    // Display selected file name
    fileSelectedLabel.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    fileSelectedLabel.style.display = "block";
  }

  // 3. Form Submit
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearStatusMessage();

      const file = fileInput.files[0];
      const jdText = jdInput.value.trim();
      const jdWords = jdText ? jdText.split(/\s+/).length : 0;

      // Validation
      if (!file) {
        showStatusMessage("Please attach a PDF resume to begin analysis.", "error");
        return;
      }

      if (!jdText) {
        showStatusMessage("Please paste the target job description.", "error");
        return;
      }

      if (jdWords < 40) {
        showStatusMessage(`Job description is too brief (${jdWords} words). Please provide at least 40 words for an accurate analysis.`, "error");
        return;
      }

      // Start asynchronous analysis
      await submitAnalysis(file, jdText);
    });
  }
}

/* --------------------------------------------------------------------------
   Submit Analysis API Call & Rotating Progress
   -------------------------------------------------------------------------- */
async function submitAnalysis(file, jdText) {
  const analyzeBtn = document.getElementById("analyze-btn");
  const progressBox = document.getElementById("reading-progress");
  const progressLine = document.getElementById("progress-line");

  // Disable submit button & start calm rotating progress lines
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analysing…";

  let phraseIdx = 0;
  progressLine.textContent = PROGRESS_PHRASES[0];
  progressBox.classList.add("active");

  progressInterval = setInterval(() => {
    phraseIdx = (phraseIdx + 1) % PROGRESS_PHRASES.length;
    progressLine.textContent = PROGRESS_PHRASES[phraseIdx];
  }, 1600);

  const formData = new FormData();
  formData.append("resume", file);
  formData.append("job_description", jdText);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      const errMsg = data.error || `Server returned error (${response.status})`;
      showStatusMessage(errMsg, "error");
      return;
    }

    // Success: store state, save to history, and populate UI
    currentAnalysisData = data;
    saveToHistory(data);
    renderResults(data);

    // Smooth scroll to 02 Verdict
    const verdictSection = document.getElementById("section-verdict");
    if (verdictSection) {
      verdictSection.scrollIntoView({ behavior: "smooth" });
    }

  } catch (err) {
    console.error("Analysis request error:", err);
    showStatusMessage("A network or server connection error occurred. Please check your connection and retry.", "error");
  } finally {
    // Teardown progress
    clearInterval(progressInterval);
    progressBox.classList.remove("active");
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyse Resume";
  }
}

/* --------------------------------------------------------------------------
   Result Rendering Engine: Sections 02 through 07
   -------------------------------------------------------------------------- */
export function renderResults(data) {
  if (!data) return;

  // Reveal all result sections
  const resultSections = document.querySelectorAll(".results-revealed");
  resultSections.forEach(sec => sec.style.display = "grid");

  // Also reveal footer ribbon
  const footerRibbon = document.getElementById("footer-ribbon");
  if (footerRibbon) footerRibbon.style.display = "flex";

  // 02 Verdict
  renderVerdictSection(data.match, data.ats_check);

  // 03 Skills
  renderSkillsSection(data.match.skills);

  // 04 Profile Read
  renderProfileSection(data.profile);

  // 05 Annotated Resume
  renderAnnotatedResume(data.annotated_resume);

  // 06 Editor's Notes
  renderEditorsNotes(data.ai_suggestions);

  // 07 ATS Checklist
  renderAtsChecklist(data.ats_check);
}

// 02 Verdict
function renderVerdictSection(match, ats) {
  const scoreEl = document.getElementById("verdict-score");
  const headlineEl = document.getElementById("verdict-headline");
  const formulaEl = document.getElementById("verdict-formula");
  const statMatched = document.getElementById("stat-matched-skills");
  const statMissing = document.getElementById("stat-missing-skills");
  const statAts = document.getElementById("stat-ats-score");

  if (scoreEl) scoreEl.textContent = `${match.overall_score}%`;
  if (headlineEl) headlineEl.textContent = match.verdict;
  if (formulaEl) {
    const bd = match.scoring_breakdown;
    formulaEl.textContent = `Weighted Composite: ${bd.skill_coverage_score}% Skill Overlap (60%) + ${bd.tfidf_cosine_score}% TF-IDF Cosine Similarity (40%)`;
  }

  if (statMatched) statMatched.textContent = match.skills.matched_count;
  if (statMissing) statMissing.textContent = match.skills.missing_count;
  if (statAts) statAts.textContent = `${ats.score}%`;
}

// 03 Skills
function renderSkillsSection(skills) {
  const matchedContainer = document.getElementById("matched-skills-list");
  const missingContainer = document.getElementById("missing-skills-list");
  const extraContainer = document.getElementById("extra-skills-list");
  const barsContainer = document.getElementById("category-bars-list");

  // Matched Skills
  if (matchedContainer) {
    matchedContainer.innerHTML = "";
    if (skills.matched && skills.matched.length > 0) {
      skills.matched.forEach(skill => {
        const tag = document.createElement("span");
        tag.className = "skill-tag matched";
        tag.textContent = skill;
        matchedContainer.appendChild(tag);
      });
    } else {
      matchedContainer.innerHTML = `<span style="color: var(--ink-2); font-family: var(--font-mono); font-size: 0.8125rem;">No direct matching skills detected.</span>`;
    }
  }

  // Missing Skills
  if (missingContainer) {
    missingContainer.innerHTML = "";
    if (skills.missing && skills.missing.length > 0) {
      skills.missing.forEach(skill => {
        const tag = document.createElement("span");
        tag.className = "skill-tag missing";
        tag.textContent = skill;
        missingContainer.appendChild(tag);
      });
    } else {
      missingContainer.innerHTML = `<span style="color: var(--good); font-family: var(--font-mono); font-size: 0.8125rem;">All target skills listed in the job description are covered!</span>`;
    }
  }

  // Extra Skills
  if (extraContainer) {
    extraContainer.innerHTML = "";
    if (skills.extra && skills.extra.length > 0) {
      skills.extra.slice(0, 25).forEach(skill => {
        const tag = document.createElement("span");
        tag.className = "skill-tag extra";
        tag.textContent = skill;
        extraContainer.appendChild(tag);
      });
    } else {
      extraContainer.innerHTML = `<span style="color: var(--ink-2); font-family: var(--font-mono); font-size: 0.8125rem;">None</span>`;
    }
  }

  // Category coverage thin bars
  if (barsContainer && skills.coverage_by_category) {
    barsContainer.innerHTML = "";
    Object.entries(skills.coverage_by_category).forEach(([category, data]) => {
      // Only display categories relevant to the JD or resume
      if (data.jd_count > 0 || data.resume_count > 0) {
        const row = document.createElement("div");
        row.className = "bar-row";

        const pct = Math.round(data.ratio * 100);
        row.innerHTML = `
          <div class="bar-label">${escapeHtml(category)}</div>
          <div class="thin-track">
            <div class="thin-fill" style="width: ${pct}%;"></div>
          </div>
          <div class="bar-val">${data.matched_count}/${data.jd_count || data.resume_count}</div>
        `;
        barsContainer.appendChild(row);
      }
    });
  }

  // Render the single Chart.js bar chart
  renderCategoryChart(skills.coverage_by_category);
}

// Exactly one Chart.js visual (Neobrutalist horizontal bars with bold borders)
function renderCategoryChart(categoryData) {
  const canvas = document.getElementById("category-chart");
  if (!canvas || !window.Chart || !categoryData) return;

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const textColor = isDark ? "#FFFFFF" : "#000000";
  const barBg = isDark ? "#4ADE80" : "#A3E635";
  const barBorder = isDark ? "#FFFFFF" : "#000000";
  const gridColor = isDark ? "#282830" : "#E2DDD2";

  const categories = Object.keys(categoryData).filter(c => {
    const d = categoryData[c];
    return d.jd_count > 0 || d.resume_count > 0;
  });

  const ratios = categories.map(c => Math.round(categoryData[c].ratio * 100));

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  const ctx = canvas.getContext("2d");
  categoryChartInstance = new window.Chart(ctx, {
    type: "bar",
    data: {
      labels: categories,
      datasets: [{
        label: "Skill Coverage (%)",
        data: ratios,
        backgroundColor: barBg,
        borderColor: barBorder,
        borderWidth: 2.5,
        borderRadius: 2,
        barThickness: 16,
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: isDark ? "#1E1E24" : "#FFE600",
          titleColor: isDark ? "#FFFFFF" : "#000000",
          bodyColor: isDark ? "#FFFFFF" : "#000000",
          titleFont: { family: "'IBM Plex Mono', monospace", size: 12, weight: "bold" },
          bodyFont: { family: "'IBM Plex Mono', monospace", size: 12, weight: "bold" },
          borderColor: isDark ? "#FFFFFF" : "#000000",
          borderWidth: 2,
          padding: 10,
          cornerRadius: 3,
          callbacks: {
            label: (ctx) => `  Coverage: ${ctx.raw}%`
          }
        }
      },
      scales: {
        x: {
          min: 0,
          max: 100,
          grid: {
            color: gridColor,
            lineWidth: 1.5,
            drawBorder: true,
          },
          ticks: {
            color: textColor,
            font: { family: "'IBM Plex Mono', monospace", size: 11, weight: "bold" },
            callback: (val) => `${val}%`
          }
        },
        y: {
          grid: { display: false },
          ticks: {
            color: textColor,
            font: { family: "'Space Grotesk', sans-serif", size: 12, weight: "bold" }
          }
        }
      }
    }
  });
}

// 04 Profile Read (Tidy Ledger)
function renderProfileSection(profile) {
  const container = document.getElementById("profile-ledger");
  if (!container || !profile) return;

  container.innerHTML = "";

  // Contact Information
  const c = profile.contacts || {};
  const contactLines = [];
  if (c.email) contactLines.push(`Email: ${escapeHtml(c.email)}`);
  if (c.phone) contactLines.push(`Phone: ${escapeHtml(c.phone)}`);
  if (c.linkedin) contactLines.push(`LinkedIn: ${escapeHtml(c.linkedin)}`);
  if (c.github) contactLines.push(`GitHub: ${escapeHtml(c.github)}`);
  if (c.websites && c.websites.length > 0) contactLines.push(`Portfolio: ${c.websites.map(escapeHtml).join(", ")}`);

  container.appendChild(createLedgerBlock("Contact Dossier", [
    { label: "Credentials", val: contactLines.join(" &bull; ") || "None extracted" }
  ]));

  // Education
  if (profile.education && profile.education.length > 0) {
    const eduItems = profile.education.map(edu => ({
      label: edu.year || "Graduation Record",
      val: `<strong>${escapeHtml(edu.degree || "Degree")}</strong> ${escapeHtml(edu.institution || "")} ${edu.gpa ? `(GPA/Score: ${escapeHtml(edu.gpa)})` : ""}`
    }));
    container.appendChild(createLedgerBlock("Academic Qualifications", eduItems));
  }

  // Work Experience
  if (profile.experience && profile.experience.length > 0) {
    const expItems = profile.experience.map(exp => {
      let bulletsHtml = "";
      if (exp.bullets && exp.bullets.length > 0) {
        bulletsHtml = `<ul>${exp.bullets.map(b => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`;
      }
      return {
        label: exp.duration || "Experience",
        val: `<strong>${escapeHtml(exp.title || "Role")}</strong> ${exp.company ? `<span>${escapeHtml(exp.company)}</span>` : ""}${bulletsHtml}`
      };
    });
    container.appendChild(createLedgerBlock("Professional Experience & Internships", expItems));
  }

  // Projects
  if (profile.projects && profile.projects.length > 0) {
    const projItems = profile.projects.map(proj => {
      let bulletsHtml = "";
      if (proj.bullets && proj.bullets.length > 0) {
        bulletsHtml = `<ul>${proj.bullets.map(b => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`;
      }
      return {
        label: proj.technologies ? escapeHtml(proj.technologies) : "Project",
        val: `<strong>${escapeHtml(proj.title || "Project")}</strong> ${proj.link ? `<a href="${escapeHtml(proj.link)}" target="_blank" rel="noopener">Link</a>` : ""}${bulletsHtml}`
      };
    });
    container.appendChild(createLedgerBlock("Technical Projects", projItems));
  }

  // Certifications
  if (profile.certifications && profile.certifications.length > 0) {
    const certItems = profile.certifications.map(cert => ({
      label: "Credential",
      val: `<strong>${escapeHtml(cert.name || cert.raw)}</strong> ${cert.issuer ? `<span>Issued by ${escapeHtml(cert.issuer)}</span>` : ""}`
    }));
    container.appendChild(createLedgerBlock("Certifications & Accreditations", certItems));
  }
}

function createLedgerBlock(title, items) {
  const block = document.createElement("div");
  block.className = "ledger-section";

  const header = document.createElement("div");
  header.className = "ledger-header";
  header.textContent = title;
  block.appendChild(header);

  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "ledger-item";
    row.innerHTML = `
      <div class="ledger-key">${item.label}</div>
      <div class="ledger-val">${item.val}</div>
    `;
    block.appendChild(row);
  });

  return block;
}

// 05 Annotated Resume (Document View + Margin Notes)
function renderAnnotatedResume(annotated) {
  const pageContainer = document.getElementById("annotated-page");
  const notesContainer = document.getElementById("margin-notes");
  if (!pageContainer || !notesContainer || !annotated) return;

  const rawText = annotated.raw_text || "";
  let markup = escapeHtml(rawText);

  // Highlight matched keywords
  if (annotated.annotations) {
    annotated.annotations.forEach(ann => {
      const escapedTerm = escapeRegExp(ann.term);
      const regex = new RegExp(`\\b(${escapedTerm})\\b`, "gi");
      markup = markup.replace(regex, `<span class="annotated-highlight">$1</span>`);
    });
  }

  pageContainer.innerHTML = markup;

  // Margin Notes
  notesContainer.innerHTML = "";
  if (annotated.margin_notes && annotated.margin_notes.length > 0) {
    annotated.margin_notes.forEach(note => {
      const card = document.createElement("div");
      card.className = "margin-note-card";
      card.innerHTML = `
        <div class="note-numeral">[Note #${note.id}]</div>
        <div class="note-target">${escapeHtml(note.target)}</div>
        <div class="note-text">${escapeHtml(note.note)}</div>
      `;
      notesContainer.appendChild(card);
    });
  } else {
    notesContainer.innerHTML = `
      <div style="font-family: var(--font-mono); font-size: 0.8125rem; color: var(--good);">
        Clean manuscript flow. No structural margins flagged.
      </div>
    `;
  }
}

// 06 Editor's Notes (AI Suggestions & Bullets)
function renderEditorsNotes(ai) {
  const summaryBox = document.getElementById("ai-executive-summary");
  const suggestionsList = document.getElementById("ai-suggestions-list");
  const bulletsContainer = document.getElementById("ai-bullet-revisions");
  const tailoredBox = document.getElementById("ai-tailored-summary");
  const aiNotice = document.getElementById("ai-fallback-notice");

  if (summaryBox) summaryBox.textContent = `"${ai.executive_summary || "Evaluation pending."}"`;

  // Fallback Notice (if API key missing or fallback engaged)
  if (aiNotice) {
    if (ai.notice) {
      aiNotice.textContent = ai.notice;
      aiNotice.style.display = "block";
    } else {
      aiNotice.style.display = "none";
    }
  }

  // Actionable Suggestions (5-7)
  if (suggestionsList) {
    suggestionsList.innerHTML = "";
    (ai.actionable_suggestions || []).forEach(sug => {
      const li = document.createElement("li");
      li.textContent = sug;
      suggestionsList.appendChild(li);
    });
  }

  // Rewritten Bullets (3-5)
  if (bulletsContainer) {
    bulletsContainer.innerHTML = "";
    (ai.rewritten_bullets || []).forEach(b => {
      const card = document.createElement("div");
      card.className = "revision-card";
      card.innerHTML = `
        <div class="rev-header">Original Phrasing</div>
        <div class="rev-original">${escapeHtml(b.original)}</div>
        <div class="rev-header" style="color: var(--good);">Editor's Revision</div>
        <div class="rev-improved">${escapeHtml(b.rewritten)}</div>
        <div class="rev-rationale">Rationale: ${escapeHtml(b.rationale)}</div>
      `;
      bulletsContainer.appendChild(card);
    });
  }

  // Tailored Summary
  if (tailoredBox) {
    tailoredBox.textContent = ai.tailored_professional_summary || "N/A";
  }
}

// 07 ATS Checklist
function renderAtsChecklist(ats) {
  const scoreNum = document.getElementById("ats-score-num");
  const summaryEl = document.getElementById("ats-summary-text");
  const tbody = document.getElementById("ats-checklist-body");

  if (scoreNum) scoreNum.textContent = `${ats.score}%`;
  if (summaryEl) summaryEl.textContent = ats.summary;

  if (tbody && ats.checklist) {
    tbody.innerHTML = "";
    ats.checklist.forEach(item => {
      const tr = document.createElement("tr");

      const badgeClass = item.status === "pass" ? "pass" : (item.status === "warn" ? "warn" : "fail");
      const badgeIcon = item.status === "pass" ? "PASS" : (item.status === "warn" ? "WARN" : "FAIL");

      tr.innerHTML = `
        <td style="width: 80px;"><span class="status-badge ${badgeClass}">${badgeIcon}</span></td>
        <td style="font-weight: 500; width: 200px;">${escapeHtml(item.title)}</td>
        <td>${escapeHtml(item.message)}</td>
        <td style="font-family: var(--font-mono); font-size: 0.8125rem; color: var(--ink-2);">${escapeHtml(item.recommendation)}</td>
      `;
      tbody.appendChild(tr);
    });
  }
}

/* --------------------------------------------------------------------------
   History Controls
   -------------------------------------------------------------------------- */
function initHistoryControls() {
  const historyLink = document.getElementById("history-link");
  const closeBtn = document.getElementById("history-close-btn");
  const modal = document.getElementById("history-modal");

  if (historyLink) {
    historyLink.addEventListener("click", (e) => {
      e.preventDefault();
      openHistoryModal((selectedData) => {
        currentAnalysisData = selectedData;
        renderResults(selectedData);
        const verdictSection = document.getElementById("section-verdict");
        if (verdictSection) verdictSection.scrollIntoView({ behavior: "smooth" });
      });
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", () => closeHistoryModal());
  }

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeHistoryModal();
    });
  }
}

/* --------------------------------------------------------------------------
   Report Controls & Footer
   -------------------------------------------------------------------------- */
function initReportControls() {
  const downloadBtn = document.getElementById("download-report-btn");
  const printBtn = document.getElementById("print-report-btn");
  const resetBtn = document.getElementById("reset-btn");

  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      if (currentAnalysisData) {
        downloadReport(currentAnalysisData);
      }
    });
  }

  if (printBtn) {
    printBtn.addEventListener("click", () => {
      triggerPrint();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      const fileInput = document.getElementById("file-input");
      const jdInput = document.getElementById("jd-input");
      const fileSelectedLabel = document.getElementById("file-selected-label");
      if (fileInput) fileInput.value = "";
      if (jdInput) jdInput.value = "";
      if (fileSelectedLabel) fileSelectedLabel.style.display = "none";
      clearStatusMessage();
    });
  }
}

/* --------------------------------------------------------------------------
   Helpers & Utility Functions
   -------------------------------------------------------------------------- */
function showStatusMessage(message, type = "error") {
  const banner = document.getElementById("status-banner");
  if (!banner) return;
  banner.textContent = message;
  banner.className = `status-banner ${type}`;
}

function clearStatusMessage() {
  const banner = document.getElementById("status-banner");
  if (!banner) return;
  banner.textContent = "";
  banner.className = "status-banner";
  banner.style.display = "none";
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[m]));
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
