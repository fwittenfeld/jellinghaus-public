"use strict";

const state = { entries: [], meta: {}, query: "", letter: "Alle", topic: "", audioOnly: false, currentAudioButton: null };
const collator = new Intl.Collator("de-DE", { sensitivity: "base" });
const elements = {};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function normalize(value) {
  return String(value ?? "").toLocaleLowerCase("de-DE")
    .replaceAll("ſ", "s").replaceAll("ß", "ss").replaceAll("æ", "ae")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9äöü]+/g, " ").trim();
}

function letterKey(value) {
  const first = normalize(value).charAt(0).toLocaleUpperCase("de-DE");
  return /^[A-ZÄÖÜ]$/u.test(first) ? first : "#";
}

function levenshtein(a, b, limit) {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  let previous = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i += 1) {
    const current = [i];
    let rowMinimum = i;
    for (let j = 1; j <= b.length; j += 1) {
      const value = Math.min(
        current[j - 1] + 1,
        previous[j] + 1,
        previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
      current.push(value);
      rowMinimum = Math.min(rowMinimum, value);
    }
    if (rowMinimum > limit) return limit + 1;
    previous = current;
  }
  return previous[b.length];
}

function prepareEntry(entry) {
  const source = normalize(entry.source);
  const target = normalize(entry.target);
  const bookSource = normalize(entry.bookSource);
  const modern = normalize(entry.modernMeaning || entry.target);
  const search = [source, target, bookSource, normalize(entry.bookTarget), modern, ...(entry.searchAliases || []).map(normalize)].join(" ");
  const semantic = [...(entry.semanticTerms || []), ...(entry.topics || []).map(id => state.meta.topics?.[id] || "")].map(normalize);
  const words = [...new Set(search.split(" ").filter(Boolean))];
  return { ...entry, _source: source, _target: target, _modern: modern, _search: search, _semantic: semantic, _words: words, _letter: letterKey(entry.source) };
}

function searchScore(entry, query) {
  if (!query) return { score: 0, fuzzy: false };
  if (entry._source === query || entry._target === query || entry._modern === query) return { score: 0, fuzzy: false };
  if (entry._source.startsWith(query)) return { score: 1, fuzzy: false };
  if (entry._target.startsWith(query)) return { score: 2, fuzzy: false };
  if (entry._search.includes(query)) return { score: 3, fuzzy: false };
  const queryWords = query.split(" ");
  if (entry._semantic.some(term => term === query)
      || queryWords.every(word => entry._semantic.some(term => term.split(" ").includes(word)))) {
    return { score: 5, fuzzy: false, semantic: true };
  }
  if (query.length < 3) return null;

  const limit = query.length <= 5 ? 1 : query.length <= 9 ? 2 : 3;
  let best = limit + 1;
  for (const word of entry._words) best = Math.min(best, levenshtein(query, word, limit));
  return best <= limit ? { score: 10 + best, fuzzy: true } : null;
}

function sourceHtml(entry) {
  return entry.sourceParts.map((part, index) => {
    const separator = index ? ", " : "";
    if (!part.wbck) return `${separator}<span>${escapeHtml(part.text)}</span>`;
    return `${separator}<strong>${escapeHtml(part.text)}</strong>`;
  }).join("");
}

function populateStats() {
  const date = state.meta.updatedAt ? new Date(state.meta.updatedAt) : null;
  elements.statEntries.textContent = Number(state.meta.entryCount).toLocaleString("de-DE");
  elements.statAudio.textContent = `${Number(state.meta.audioCount).toLocaleString("de-DE")} (${state.meta.audioPercent} %)`;
  elements.statPages.textContent = Number(state.meta.pageCount).toLocaleString("de-DE");
  elements.statUpdated.textContent = date && !Number.isNaN(date.valueOf())
    ? new Intl.DateTimeFormat("de-DE", { month: "long", year: "numeric" }).format(date)
    : "–";
  elements.archiveSourceLink.href = state.meta.archiveUrl;
}

function renderAlphabet() {
  const letters = [...new Set(state.entries.map((entry) => entry._letter))].sort(collator.compare);
  const values = ["Alle", ...letters];
  elements.alphabet.innerHTML = values.map((letter) => (
    `<button type="button" data-letter="${escapeHtml(letter)}" class="${state.letter === letter ? "active" : ""}" aria-pressed="${state.letter === letter}">${escapeHtml(letter)}</button>`
  )).join("");
}

function visibleEntries() {
  const query = normalize(state.query);
  return state.entries
    .filter((entry) => !state.audioOnly || entry.hasAudio)
    .filter((entry) => !state.topic || (entry.topics || []).includes(state.topic))
    .filter((entry) => state.letter === "Alle" || entry._letter === state.letter)
    .map((entry) => ({ entry, match: searchScore(entry, query) }))
    .filter((item) => item.match)
    .sort((a, b) => (
      a.match.score - b.match.score
      || collator.compare(a.entry._letter, b.entry._letter)
      || collator.compare(a.entry.source, b.entry.source)
      || a.entry.id.localeCompare(b.entry.id)
    ));
}

function entryHtml({ entry, match }) {
  return `
    <article class="entry" id="wort-${escapeHtml(entry.id)}">
      <button class="entry-main" type="button" data-entry-id="${escapeHtml(entry.id)}"
              aria-label="Details zu ${escapeHtml(entry.source)} anzeigen">
        <span class="entry-line">
          <span class="entry-source">${sourceHtml(entry)}</span>
          <span class="entry-separator" aria-hidden="true"> – </span>
          <span class="entry-target">${escapeHtml(entry.target || "–")}</span>
        </span>
        ${match.fuzzy ? '<span class="match-note">Ähnlicher Treffer</span>' : ""}
        ${match.semantic ? '<span class="match-note">Thematisch passend</span>' : ""}
      </button>
      ${entry.hasAudio ? `<button class="icon-button audio-button" type="button" data-audio-id="${escapeHtml(entry.id)}" aria-label="Aussprache von ${escapeHtml(entry.source)} abspielen" title="Aussprache abspielen">▶</button>` : ""}
    </article>`;
}

function renderDictionary() {
  const items = visibleEntries();
  const groups = new Map();
  for (const item of items) {
    const letter = item.entry._letter;
    if (!groups.has(letter)) groups.set(letter, []);
    groups.get(letter).push(item);
  }

  elements.resultCount.textContent = `${items.length.toLocaleString("de-DE")} ${items.length === 1 ? "Eintrag" : "Einträge"}`;
  elements.clearSearch.hidden = !state.query;
  if (!items.length) {
    elements.dictionary.innerHTML = '<p class="empty-state">Keine passenden Wörter gefunden. Versuche eine andere oder kürzere Schreibweise.</p>';
    return;
  }
  elements.dictionary.innerHTML = [...groups.entries()].map(([letter, entries]) => `
    <section class="letter-group" aria-labelledby="letter-${escapeHtml(letter)}">
      <h3 class="letter-heading" id="letter-${escapeHtml(letter)}">${escapeHtml(letter)}</h3>
      <div class="entry-list">${entries.map(entryHtml).join("")}</div>
    </section>`).join("");
}

function playEntry(entry, button) {
  const player = elements.audioPlayer;
  if (state.currentAudioButton) state.currentAudioButton.classList.remove("playing");
  if (player.dataset.entryId === entry.id && !player.paused) {
    player.pause();
    player.currentTime = 0;
    player.dataset.entryId = "";
    state.currentAudioButton = null;
    return;
  }
  player.src = entry.audioUrl;
  player.dataset.entryId = entry.id;
  state.currentAudioButton = button;
  button?.classList.add("playing");
  player.play().catch(() => {
    button?.classList.remove("playing");
    state.currentAudioButton = null;
    window.alert("Diese Aufnahme ist derzeit nicht abspielbar.");
  });
}

function relatedEntries(entry, limit = 5) {
  const topics = new Set(entry.topics || []);
  const terms = new Set((entry.semanticTerms || []).map(normalize));
  if (!topics.size && !terms.size) return [];
  const frequency = new Map();
  state.entries.forEach(item => new Set((item.semanticTerms || []).map(normalize))
    .forEach(term => frequency.set(term, (frequency.get(term) || 0) + 1)));
  const seen = new Set([entry._source]);
  return state.entries.filter(item => item.id !== entry.id)
    .map(item => {
      const sharedTopics = (item.topics || []).filter(id => topics.has(id)).length;
      const sharedTerms = [...new Set((item.semanticTerms || []).map(normalize))].filter(term => terms.has(term));
      const score = sharedTopics + sharedTerms.reduce((sum, term) => sum + 2 + Math.log(1 + state.entries.length / frequency.get(term)), 0);
      return { entry: item, score };
    })
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score || collator.compare(a.entry.source, b.entry.source) || a.entry.id.localeCompare(b.entry.id))
    .filter(item => {
      if (seen.has(item.entry._source)) return false;
      seen.add(item.entry._source); return true;
    }).slice(0, limit).map(item => item.entry);
}

function semanticDetailsHtml(entry) {
  const topics = (entry.topics || []).map(id => state.meta.topics?.[id]).filter(Boolean);
  const related = relatedEntries(entry);
  if (!topics.length && !related.length) return "";
  return `<section class="semantic-details" aria-label="Thematische Einordnung">
    ${topics.length ? `<h3>Themen</h3><p class="topic-tags">${topics.map(label => `<span>${escapeHtml(label)}</span>`).join("")}</p>` : ""}
    ${related.length ? `<h3>Thematisch ähnliche Wörter</h3><ul class="related-words">${related.map(item => `<li>
      <button type="button" data-related-id="${escapeHtml(item.id)}"><span>${sourceHtml(item)} <span class="related-target">– ${escapeHtml(item.target)}</span></span>
      <small>${escapeHtml((item.topics || []).map(id => state.meta.topics?.[id]).filter(Boolean).join(" · "))}</small></button>
      ${item.hasAudio ? `<button class="icon-button audio-button" type="button" data-audio-id="${escapeHtml(item.id)}" aria-label="Aussprache von ${escapeHtml(item.source)} abspielen">▶</button>` : ""}
    </li>`).join("")}</ul>` : ""}
    <p class="semantic-note">Automatische thematische Zuordnung — keine zusätzliche Buchangabe.</p>
  </section>`;
}

function showDetails(entry) {
  const rows = [
    ["Seitenzahl", entry.page],
    ["Plattdeutsch", entry.bookSource],
    ["Übersetzung", entry.bookTarget],
  ].filter(([, value]) => value);
  elements.dialogContent.innerHTML = `
    <div class="dialog-body">
      <p class="eyebrow">Wörterbucheintrag · Seite ${escapeHtml(entry.page)}</p>
      <h2 id="dialogTitle">${sourceHtml(entry)}</h2>
      <p class="dialog-target">${escapeHtml(entry.target || "–")}</p>
      <h3>Schreibweise in der Buchvorlage</h3>
      <dl class="detail-grid">${rows.map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`).join("")}</dl>
      <a class="text-link" href="${escapeHtml(entry.archiveUrl)}" target="_blank" rel="noopener">Buchseite im Internet Archive öffnen <span aria-hidden="true">↗</span></a>
      ${semanticDetailsHtml(entry)}
    </div>`;
  if (!elements.entryDialog.open) elements.entryDialog.showModal();
  history.replaceState(null, "", `#wort-${entry.id}`);
}

function bindEvents() {
  elements.search.addEventListener("input", () => { state.query = elements.search.value; state.letter = "Alle"; renderAlphabet(); renderDictionary(); });
  elements.clearSearch.addEventListener("click", () => { elements.search.value = ""; state.query = ""; renderDictionary(); elements.search.focus(); });
  elements.audioOnly.addEventListener("change", () => { state.audioOnly = elements.audioOnly.checked; renderDictionary(); });
  elements.topicFilter.addEventListener("change", () => {
    state.topic = elements.topicFilter.value; state.letter = "Alle"; renderAlphabet(); renderDictionary();
  });
  elements.alphabet.addEventListener("click", (event) => {
    const button = event.target.closest("[data-letter]");
    if (!button) return;
    state.letter = button.dataset.letter;
    renderAlphabet(); renderDictionary();
  });
  elements.dictionary.addEventListener("click", (event) => {
    const audioButton = event.target.closest("[data-audio-id]");
    if (audioButton) {
      const entry = state.entries.find((item) => item.id === audioButton.dataset.audioId);
      if (entry) playEntry(entry, audioButton);
      return;
    }
    const detailButton = event.target.closest("[data-entry-id]");
    if (detailButton) {
      const entry = state.entries.find((item) => item.id === detailButton.dataset.entryId);
      if (entry) showDetails(entry);
    }
  });
  elements.audioPlayer.addEventListener("ended", () => {
    state.currentAudioButton?.classList.remove("playing");
    state.currentAudioButton = null;
  });
  elements.dialogContent.addEventListener("click", (event) => {
    const audioButton = event.target.closest("[data-audio-id]");
    if (audioButton) {
      const entry = state.entries.find(item => item.id === audioButton.dataset.audioId);
      if (entry) playEntry(entry, audioButton);
      return;
    }
    const relatedButton = event.target.closest("[data-related-id]");
    if (!relatedButton) return;
    const entry = state.entries.find(item => item.id === relatedButton.dataset.relatedId);
    if (entry) {
      showDetails(entry);
      elements.entryDialog.scrollTop = 0;
      elements.entryDialog.querySelector(".dialog-close").focus();
    }
  });
  elements.entryDialog.addEventListener("click", (event) => {
    if (event.target === elements.entryDialog) elements.entryDialog.close();
  });
  elements.entryDialog.addEventListener("close", () => history.replaceState(null, "", `${location.pathname}${location.search}`));
}

async function init() {
  for (const id of ["search", "clearSearch", "audioOnly", "topicFilter", "resultCount", "alphabet", "dictionary", "loadError", "entryDialog", "dialogContent", "audioPlayer", "statEntries", "statAudio", "statPages", "statUpdated", "archiveSourceLink"]) elements[id] = document.getElementById(id);
  bindEvents();
  try {
    const response = await fetch("data/dictionary.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.meta = payload.meta;
    state.entries = payload.entries.map(prepareEntry);
    const topicCounts = new Map();
    state.entries.forEach(entry => (entry.topics || []).forEach(id => topicCounts.set(id, (topicCounts.get(id) || 0) + 1)));
    elements.topicFilter.innerHTML = '<option value="">Alle Themen</option>' + Object.entries(state.meta.topics || {})
      .filter(([id]) => topicCounts.has(id))
      .map(([id, label]) => `<option value="${escapeHtml(id)}">${escapeHtml(label)} (${topicCounts.get(id)})</option>`).join("");
    populateStats(); renderAlphabet(); renderDictionary();
    const match = location.hash.match(/^#wort-(.+)$/);
    if (match) {
      const entry = state.entries.find((item) => item.id === match[1]);
      if (entry) showDetails(entry);
    }
  } catch (error) {
    console.error(error);
    elements.resultCount.textContent = "Nicht verfügbar";
    elements.loadError.hidden = false;
  }
}

document.addEventListener("DOMContentLoaded", init);
