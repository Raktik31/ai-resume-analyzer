/**
 * Redline - Analysis History Manager (localStorage)
 * Saves analysis results (never resume file/PDF), enables viewing, restoring, and deleting history.
 */

const HISTORY_STORAGE_KEY = "redline_analysis_history";
const MAX_HISTORY_ITEMS = 25;

export function getHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error("Failed to read history from localStorage", e);
    return [];
  }
}

export function saveToHistory(analysisResult) {
  if (!analysisResult || !analysisResult.match) return;

  const history = getHistory();
  const newItem = {
    id: "redline_" + Date.now(),
    timestamp: analysisResult.timestamp || new Date().toISOString(),
    filename: analysisResult.metadata?.filename || "Resume",
    score: analysisResult.match?.overall_score ?? 0,
    verdict: analysisResult.match?.verdict || "",
    jdSnippet: (analysisResult.metadata?.jd_word_count ? `${analysisResult.metadata.jd_word_count} words` : "Target JD"),
    data: analysisResult,
  };

  // Prepend newest item, limit to MAX_HISTORY_ITEMS
  const updated = [newItem, ...history.filter(h => h.id !== newItem.id)].slice(0, MAX_HISTORY_ITEMS);

  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.warn("localStorage quota exceeded, trimming older history items", e);
    try {
      const trimmed = updated.slice(0, 10);
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(trimmed));
    } catch (_) {}
  }
}

export function deleteHistoryItem(id) {
  const history = getHistory().filter(item => item.id !== id);
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  } catch (e) {
    console.error("Failed to delete history item", e);
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
  } catch (e) {
    console.error("Failed to clear history", e);
  }
}

export function renderHistoryModal(onSelectHistoryItem) {
  const modal = document.getElementById("history-modal");
  const listContainer = document.getElementById("history-list");
  if (!modal || !listContainer) return;

  const items = getHistory();
  listContainer.innerHTML = "";

  if (items.length === 0) {
    listContainer.innerHTML = `
      <div style="padding: 2rem 0; text-align: center; color: var(--ink-2); font-family: var(--font-mono); font-size: 0.875rem;">
        No previous resume analyses recorded yet.
      </div>
    `;
    return;
  }

  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "history-item";

    const dateStr = new Date(item.timestamp).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

    row.innerHTML = `
      <div style="flex: 1; min-width: 0;">
        <div style="font-weight: 600; font-size: 0.9375rem; color: var(--ink);">${escapeHtml(item.filename)}</div>
        <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--ink-2); margin-top: 0.2rem;">
          ${dateStr} &bull; ${item.jdSnippet}
        </div>
      </div>
      <div class="history-score">${item.score}%</div>
      <div style="display: flex; gap: 0.5rem;">
        <button class="btn-ghost btn-load-history" data-id="${item.id}" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">Reopen</button>
        <button class="btn-ghost btn-del-history" data-id="${item.id}" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; color: var(--bad);">&times;</button>
      </div>
    `;

    // Reopen listener
    row.querySelector(".btn-load-history").addEventListener("click", () => {
      onSelectHistoryItem(item.data);
      closeHistoryModal();
    });

    // Delete listener
    row.querySelector(".btn-del-history").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteHistoryItem(item.id);
      renderHistoryModal(onSelectHistoryItem);
    });

    listContainer.appendChild(row);
  });
}

export function openHistoryModal(onSelectHistoryItem) {
  const modal = document.getElementById("history-modal");
  if (modal) {
    renderHistoryModal(onSelectHistoryItem);
    modal.classList.add("active");
  }
}

export function closeHistoryModal() {
  const modal = document.getElementById("history-modal");
  if (modal) {
    modal.classList.remove("active");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[m]));
}
