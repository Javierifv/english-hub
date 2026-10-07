/**
 * DUOHUB - Pillar 2: Reading, Highlighting, Translation & Summary Evaluator Controller
 * Supports CEFR Levels (A1, B1, B2, All), Robinson Crusoe Chapters, Audio Narration,
 * Interactive Word & Phrase Highlighting, Spanish Translation Audit, and English Summary Synthesis.
 */

let timerSeconds = 15 * 60; // 15 minutes default
let timerInterval = null;
let isTimerRunning = false;

let currentReadingData = null;
let readingChaptersList = [];
let currentChapterIndex = 0;

// Highlighting state: 'word' | 'phrase'
let highlightMode = 'word';
let currentHighlights = { words: [], phrases: [] };

async function loadReadingData(day) {
  const savedLevel = localStorage.getItem('duohub_reading_lvl_u' + state.currentUser) || state.readingLevel || 'A1';
  await selectReadingLevel(savedLevel, false);
}

async function selectReadingLevel(lvl, loadFirst = true) {
  state.readingLevel = lvl;
  state.readingLevelSetByUser = true;
  localStorage.setItem('duohub_reading_lvl_u' + state.currentUser, lvl);

  // Update active pill button
  document.querySelectorAll(".reading-toolbar .level-pill-btn").forEach(btn => {
    btn.classList.remove("active");
  });

  const btnMap = {
    'A1': 'reading-level-btn-a1',
    'B1': 'reading-level-btn-b1',
    'B2': 'reading-level-btn-b2',
    'all': 'reading-level-btn-all'
  };

  const activeBtn = document.getElementById(btnMap[lvl] || 'reading-level-btn-all');
  if (activeBtn) activeBtn.classList.add("active");

  // Fetch list of chapters for this level
  try {
    const listRes = await fetch(`/api/reading/list?level=${lvl}`);
    readingChaptersList = await listRes.json();

    const select = document.getElementById("reading-chapter-select");
    if (select && readingChaptersList.length > 0) {
      select.innerHTML = readingChaptersList.map((r) => {
        // Clean title
        const cleanName = r.title.replace(/\[.*?\]\s*/, '').replace(/Cap\.\s*\d+\s*[–-]\s*/, '').trim();
        if (lvl === 'all') {
          return `<option value="${r.id}">[${r.level}] Cap. ${r.chapter}: ${cleanName}</option>`;
        }
        return `<option value="${r.id}">Capítulo ${r.chapter}: ${cleanName}</option>`;
      }).join("");

      // Check if user had a saved chapter
      const savedReadingId = parseInt(localStorage.getItem('duohub_reading_id_u' + state.currentUser));
      const foundIdx = readingChaptersList.findIndex(r => r.id === savedReadingId);
      
      if (foundIdx !== -1) {
        currentChapterIndex = foundIdx;
        select.value = savedReadingId;
      } else {
        currentChapterIndex = 0;
        select.value = readingChaptersList[0].id;
      }

      await loadReadingById(select.value);
    }
  } catch (err) {
    console.error("Error loading reading chapter list:", err);
  }
}

async function navReadingChapter(delta) {
  if (!readingChaptersList || readingChaptersList.length === 0) return;
  const newIdx = currentChapterIndex + delta;
  if (newIdx >= 0 && newIdx < readingChaptersList.length) {
    currentChapterIndex = newIdx;
    const select = document.getElementById("reading-chapter-select");
    if (select) select.value = readingChaptersList[currentChapterIndex].id;
    localStorage.setItem('duohub_reading_id_u' + state.currentUser, readingChaptersList[currentChapterIndex].id);
    await loadReadingById(readingChaptersList[currentChapterIndex].id);
  }
}

async function onReadingChapterDropdownChange(readingId) {
  const idx = readingChaptersList.findIndex(r => r.id === parseInt(readingId));
  if (idx !== -1) {
    currentChapterIndex = idx;
    localStorage.setItem('duohub_reading_id_u' + state.currentUser, readingId);
    await loadReadingById(readingId);
  }
}

async function loadReadingById(readingId) {
  try {
    const res = await fetch(`/api/reading?id=${readingId}`);
    const reading = await res.json();
    currentReadingData = reading;

    if (reading.error) {
      document.getElementById("reading-title").textContent = "No hay lectura disponible.";
      return;
    }

    document.getElementById("reading-title").textContent = reading.title;
    document.getElementById("reading-level").textContent = `${reading.level} Level`;
    document.getElementById("reading-topic").textContent = reading.topic;

    // Audio Player setup
    const audioContainer = document.getElementById("reading-audio-container");
    const audioPlayer = document.getElementById("reading-audio-player");
    if (reading.audio_url && reading.audio_url.trim().length > 0) {
      audioPlayer.src = reading.audio_url;
      audioContainer.style.display = "flex";
    } else {
      audioContainer.style.display = "none";
      if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.src = "";
      }
    }

    // Load saved highlights for this chapter
    loadSavedHighlights();

    // Render content with interactive click-to-pronounce & highlights
    renderHighlightedReadingContent();

    // Render Key Vocabulary pills
    const keywordsBox = document.getElementById("reading-keywords");
    if (reading.key_vocabulary && Array.isArray(reading.key_vocabulary) && reading.key_vocabulary.length > 0) {
      keywordsBox.innerHTML = reading.key_vocabulary.map(kw => `
        <span class="keyword-pill" onclick="speakEnglish('${escapeQuotes(kw)}', 0.9)" title="Escuchar">${kw}</span>
      `).join("");
    } else {
      keywordsBox.innerHTML = `<span class="tag-title" style="color: var(--text-dim); font-size: 0.85rem;">Capítulo literario graduado en MCER</span>`;
    }

    // Load Spanish translation
    loadSavedTranslation();

    // Load English summary
    loadSavedSummary();

  } catch (err) {
    console.error("Error loading reading:", err);
  }
}

// =========================================================
// HIGHLIGHTING ENGINE (YELLOW WORD / PURPLE PHRASE)
// =========================================================

function setHighlightMode(mode) {
  highlightMode = mode;
  const btnWord = document.getElementById("btn-hl-word");
  const btnPhrase = document.getElementById("btn-hl-phrase");
  if (btnWord) btnWord.classList.toggle("active", mode === 'word');
  if (btnPhrase) btnPhrase.classList.toggle("active", mode === 'phrase');
}

function getHighlightsStorageKey() {
  const chapterId = currentReadingData ? currentReadingData.id : 'default';
  const userId = state.currentUser || 1;
  return `duohub_reading_hl_${chapterId}_u${userId}`;
}

function loadSavedHighlights() {
  try {
    const key = getHighlightsStorageKey();
    const saved = localStorage.getItem(key);
    if (saved) {
      currentHighlights = JSON.parse(saved);
      if (!Array.isArray(currentHighlights.words)) currentHighlights.words = [];
      if (!Array.isArray(currentHighlights.phrases)) currentHighlights.phrases = [];
    } else {
      currentHighlights = { words: [], phrases: [] };
    }
  } catch (e) {
    currentHighlights = { words: [], phrases: [] };
  }
  renderMarkedPills();
}

function saveHighlights() {
  try {
    const key = getHighlightsStorageKey();
    localStorage.setItem(key, JSON.stringify(currentHighlights));
  } catch (e) {}
  renderMarkedPills();
  renderHighlightedReadingContent();
}

function renderMarkedPills() {
  const panel = document.getElementById("reading-marked-items-panel");
  const list = document.getElementById("reading-marked-items-list");
  const statWords = document.getElementById("stat-words-count");
  const statPhrases = document.getElementById("stat-phrases-count");

  const words = currentHighlights.words || [];
  const phrases = currentHighlights.phrases || [];

  if (statWords) statWords.textContent = `${words.length} palabra${words.length === 1 ? '' : 's'}`;
  if (statPhrases) statPhrases.textContent = `${phrases.length} frase${phrases.length === 1 ? '' : 's'}`;

  if (!list || !panel) return;

  if (words.length === 0 && phrases.length === 0) {
    panel.style.display = "none";
    list.innerHTML = "";
    return;
  }

  panel.style.display = "block";
  let pillsHtml = "";

  words.forEach(w => {
    pillsHtml += `
      <span class="marked-pill marked-pill-word" title="Palabra desconocida (Clic ✕ para desmarcar)">
        🟡 ${escapeQuotes(w)}
        <span class="marked-pill-del" onclick="removeHighlight('word', '${escapeQuotes(w)}')" title="Quitar">✕</span>
      </span>
    `;
  });

  phrases.forEach(p => {
    pillsHtml += `
      <span class="marked-pill marked-pill-phrase" title="Frase difícil (Clic ✕ para desmarcar)">
        🟣 ${escapeQuotes(p)}
        <span class="marked-pill-del" onclick="removeHighlight('phrase', '${escapeQuotes(p)}')" title="Quitar">✕</span>
      </span>
    `;
  });

  list.innerHTML = pillsHtml;
}

function removeHighlight(type, text) {
  if (type === 'word') {
    currentHighlights.words = (currentHighlights.words || []).filter(w => w.toLowerCase() !== text.toLowerCase());
  } else {
    currentHighlights.phrases = (currentHighlights.phrases || []).filter(p => p.toLowerCase() !== text.toLowerCase());
  }
  saveHighlights();
}

function clearReadingHighlights() {
  const total = (currentHighlights.words?.length || 0) + (currentHighlights.phrases?.length || 0);
  if (total === 0) return;
  if (confirm("¿Deseas desmarcar todas las palabras y frases de este capítulo?")) {
    currentHighlights = { words: [], phrases: [] };
    saveHighlights();
  }
}

function handleReadingTextSelection() {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed) return;

  const rawText = selection.toString().trim();
  if (!rawText || rawText.length < 2) return;

  // Ensure selection occurred inside #reading-content
  const contentBox = document.getElementById("reading-content");
  if (!contentBox || !contentBox.contains(selection.anchorNode)) return;

  // Clean edge punctuation
  const cleanItem = rawText.replace(/^[.,/#!$%^&*;:{}=\-_`~()"'“”—\s]+|[.,/#!$%^&*;:{}=\-_`~()"'“”—\s]+$/g, "").trim();
  if (!cleanItem) return;

  if (highlightMode === 'word') {
    if (!currentHighlights.words.some(w => w.toLowerCase() === cleanItem.toLowerCase())) {
      currentHighlights.words.push(cleanItem);
      saveHighlights();
    }
  } else {
    if (!currentHighlights.phrases.some(p => p.toLowerCase() === cleanItem.toLowerCase())) {
      currentHighlights.phrases.push(cleanItem);
      saveHighlights();
    }
  }

  selection.removeAllRanges();
}

function renderHighlightedReadingContent() {
  const contentBox = document.getElementById("reading-content");
  if (!contentBox || !currentReadingData || !currentReadingData.content) return;

  const paragraphs = currentReadingData.content.split("\n\n");
  const markedWords = (currentHighlights.words || []).map(w => w.trim()).filter(Boolean);
  const markedPhrases = [...(currentHighlights.phrases || [])].map(p => p.trim()).filter(Boolean);

  // Sort phrases by descending length
  markedPhrases.sort((a, b) => b.length - a.length);

  contentBox.innerHTML = paragraphs.map(p => {
    let paragraphText = p;
    const phrasePlaceholders = [];

    // Step 1: Replace phrases with placeholders
    markedPhrases.forEach((phrase, idx) => {
      const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`\\b(${escaped})\\b`, 'gi');
      paragraphText = paragraphText.replace(regex, (match) => {
        const ph = `___PHRASE_HL_${idx}_${phrasePlaceholders.length}___`;
        phrasePlaceholders.push({ placeholder: ph, original: match });
        return ph;
      });
    });

    // Step 2: Split into words, replace words and re-insert phrase marks
    const words = paragraphText.split(/\s+/).map(token => {
      const foundPh = phrasePlaceholders.find(ph => token.includes(ph.placeholder));
      if (foundPh) {
        const renderedPhrase = `<mark class="hl-phrase" onclick="speakEnglish('${escapeQuotes(foundPh.original)}', 0.9)" title="🟣 Frase difícil: Clic para escuchar">${foundPh.original}</mark>`;
        return token.replace(foundPh.placeholder, renderedPhrase);
      }

      const clean = token.replace(/[^a-zA-Z]/g, "");
      const isMarkedWord = markedWords.some(mw => mw.toLowerCase() === clean.toLowerCase());

      if (isMarkedWord) {
        return `<mark class="hl-word" onclick="speakEnglish('${escapeQuotes(clean)}', 0.9)" title="🟡 Palabra desconocida: Clic para escuchar">${token}</mark>`;
      } else if (clean.length > 2) {
        return `<span class="interactive-word" onclick="speakEnglish('${escapeQuotes(clean)}', 0.9)" title="Clic para escuchar">${token}</span>`;
      }
      return token;
    }).join(" ");

    return `<p style="margin-bottom: 1rem; line-height: 1.7;">${words}</p>`;
  }).join("");
}

// =========================================================
// PHASE SWITCHER (SPANISH TRANSLATION vs ENGLISH SUMMARY)
// =========================================================

function switchReadingPhase(phase) {
  const tabTranslation = document.getElementById("tab-phase-translation");
  const tabSummary = document.getElementById("tab-phase-summary");
  const viewTranslation = document.getElementById("phase-view-translation");
  const viewSummary = document.getElementById("phase-view-summary");

  if (phase === 'translation') {
    if (tabTranslation) tabTranslation.classList.add("active");
    if (tabSummary) tabSummary.classList.remove("active");
    if (viewTranslation) viewTranslation.style.display = "block";
    if (viewSummary) viewSummary.style.display = "none";
  } else {
    if (tabTranslation) tabTranslation.classList.remove("active");
    if (tabSummary) tabSummary.classList.add("active");
    if (viewTranslation) viewTranslation.style.display = "none";
    if (viewSummary) viewSummary.style.display = "block";
  }
}

// =========================================================
// SPANISH TRANSLATION WORKSPACE & GEMINI FLASH AUDIT
// =========================================================

function loadSavedTranslation() {
  const textarea = document.getElementById("translation-textarea");
  const resultsBox = document.getElementById("translation-evaluation-results");
  if (!textarea) return;

  const chapterId = currentReadingData ? currentReadingData.id : 'default';
  const savedLocal = localStorage.getItem(`duohub_trans_ch_${chapterId}_u${state.currentUser}`);
  
  if (savedLocal) {
    textarea.value = savedLocal;
  } else if (state.todayLog && state.todayLog.reading_translation) {
    textarea.value = state.todayLog.reading_translation;
  } else {
    textarea.value = "";
  }

  updateTranslationWordCount();

  // Load saved evaluation feedback if any
  const savedFbLocal = localStorage.getItem(`duohub_trans_fb_ch_${chapterId}_u${state.currentUser}`);
  if (savedFbLocal) {
    try {
      renderTranslationFeedback(JSON.parse(savedFbLocal));
    } catch (e) {}
  } else if (state.todayLog && state.todayLog.reading_translation_feedback) {
    try {
      renderTranslationFeedback(JSON.parse(state.todayLog.reading_translation_feedback));
    } catch (e) {}
  } else if (resultsBox) {
    resultsBox.style.display = "none";
    resultsBox.innerHTML = "";
  }
}

function updateTranslationWordCount() {
  const textarea = document.getElementById("translation-textarea");
  const counter = document.getElementById("translation-word-count");
  if (!textarea || !counter) return;

  const text = textarea.value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  counter.textContent = `${words} palabras`;

  if (currentReadingData) {
    localStorage.setItem(`duohub_trans_ch_${currentReadingData.id}_u${state.currentUser}`, textarea.value);
  }
}

async function submitTranslationForEvaluation() {
  const textarea = document.getElementById("translation-textarea");
  const translationText = (textarea?.value || "").trim();

  if (!translationText) {
    alert("Por favor escribe tu traducción al español antes de solicitar la auditoría.");
    return;
  }

  const btn = document.getElementById("btn-evaluate-translation");
  btn.disabled = true;
  btn.textContent = "Auditando fidelidad con Gemini Flash...";

  try {
    const res = await fetch("/api/reading/evaluate-translation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        date: state.currentDate,
        day: state.currentDay,
        reading_id: currentReadingData ? currentReadingData.id : null,
        translation_text: translationText,
        highlighted_words: currentHighlights.words || [],
        highlighted_phrases: currentHighlights.phrases || []
      })
    });
    const data = await res.json();

    if (data.success && data.feedback) {
      renderTranslationFeedback(data.feedback);
      speakEnglish("Translation evaluated successfully!", 1.0);
      if (currentReadingData) {
        localStorage.setItem(`duohub_trans_fb_ch_${currentReadingData.id}_u${state.currentUser}`, JSON.stringify(data.feedback));
      }
      fetchStatusAndRefresh();
    } else {
      alert(data.error || "Ocurrió un error al auditar la traducción.");
    }
  } catch (err) {
    console.error("Error evaluating translation:", err);
    alert("Error de conexión al evaluar la traducción.");
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ Auditar Mi Traducción con Gemini Flash";
  }
}

function renderTranslationFeedback(f) {
  const container = document.getElementById("translation-evaluation-results");
  if (!container) return;
  container.style.display = "block";

  // Highlighted explanations section
  let explanationsHtml = "";
  if (f.highlighted_explanations && f.highlighted_explanations.length > 0) {
    explanationsHtml = `
      <div class="eval-explanations-list">
        <div style="font-weight: 800; font-size: 0.85rem; margin-bottom: 0.65rem; color: var(--text-main);">
          🔍 Explicación contextual de lo que marcaste:
        </div>
        ${f.highlighted_explanations.map(item => `
          <div class="explanation-item">
            <div style="font-weight: 700; font-size: 0.88rem; color: ${item.type === 'phrase' ? '#5B21B6' : '#92400E'};">
              ${item.type === 'phrase' ? '🟣 Frase / Modismo:' : '🟡 Palabra:'} <em>"${escapeQuotes(item.item)}"</em>
            </div>
            <div style="font-size: 0.82rem; margin-top: 0.2rem; color: var(--text-main);">
              <strong>Significado en la historia:</strong> ${item.meaning_in_context}
            </div>
            ${item.usage_tip ? `
              <div style="font-size: 0.78rem; margin-top: 0.15rem; color: var(--text-muted);">
                💡 <em>Tip pedagógico:</em> ${item.usage_tip}
              </div>
            ` : ''}
          </div>
        `).join("")}
      </div>
    `;
  }

  // Corrections section
  let correctionsHtml = "";
  if (f.corrections && f.corrections.length > 0) {
    correctionsHtml = `
      <div class="eval-corrections-list">
        <strong>⚠️ Puntos de Traducción a Pulir:</strong>
        ${f.corrections.map(c => `
          <div class="correction-item">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">Original en inglés: "${c.original_en}"</div>
            <span class="correction-wrong">"${c.student_translation}"</span> ➔ <span class="correction-good">"${c.suggested_translation}"</span>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.15rem;">${c.explanation}</div>
          </div>
        `).join("")}
      </div>
    `;
  } else {
    correctionsHtml = `
      <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; margin-bottom: 0.85rem; font-size: 0.82rem; color: var(--busuu-emerald);">
        ✓ ¡Excelente fidelidad! No se detectaron malinterpretaciones graves ni falsos amigos.
      </div>
    `;
  }

  // Reference model translation
  let referenceHtml = "";
  if (f.reference_translation) {
    referenceHtml = `
      <details class="reference-accordion" style="margin-top: 0.85rem; cursor: pointer;">
        <summary style="font-weight: 700; font-size: 0.84rem; color: var(--busuu-blue);">
          📖 Ver Traducción Modelo de Referencia (Español)
        </summary>
        <div class="reference-translation-box">
          ${f.reference_translation.replace(/\n/g, '<br>')}
        </div>
      </details>
    `;
  }

  // Advance to summary CTA
  const nextCtaHtml = `
    <div style="margin-top: 1rem; padding-top: 0.85rem; border-top: 1px dashed var(--border-subtle); display: flex; justify-content: flex-end;">
      <button type="button" class="btn btn-secondary btn-sm" onclick="switchReadingPhase('summary')">
        Continuar al Paso 2.2: Resumen en Inglés ➔
      </button>
    </div>
  `;

  container.innerHTML = `
    <h4 style="margin-bottom: 0.75rem; color: var(--text-main);">Auditoría de Traducción (${f.source || 'IA'}):</h4>
    <div class="eval-metric-pills">
      <span class="eval-pill eval-pill-accuracy">🎯 Fidelidad: ${f.accuracy_percentage}%</span>
    </div>
    <p style="font-size: 0.84rem; color: var(--text-main); margin-bottom: 0.75rem;">
      ${f.overall_verdict}
    </p>
    ${explanationsHtml}
    ${correctionsHtml}
    ${referenceHtml}
    ${nextCtaHtml}
  `;
}

// =========================================================
// ENGLISH SUMMARY WORKSPACE & EVALUATION
// =========================================================

function loadSavedSummary() {
  const summaryTextarea = document.getElementById("summary-textarea");
  const resultsBox = document.getElementById("summary-evaluation-results");
  if (!summaryTextarea) return;

  if (state.todayLog && state.todayLog.reading_summary) {
    summaryTextarea.value = state.todayLog.reading_summary;
    updateWordCount();
    if (state.todayLog.reading_feedback) {
      try {
        const feedback = JSON.parse(state.todayLog.reading_feedback);
        renderSummaryFeedback(feedback);
      } catch (e) {}
    }
  } else {
    summaryTextarea.value = "";
    updateWordCount();
    if (resultsBox) resultsBox.style.display = "none";
  }
}

function updateWordCount() {
  const textarea = document.getElementById("summary-textarea");
  const counter = document.getElementById("summary-word-count");
  if (!textarea || !counter) return;

  const text = textarea.value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  counter.textContent = `${words} palabras (Mínimo recomendado: 50)`;

  if (words >= 50) {
    counter.style.color = "var(--busuu-emerald)";
  } else {
    counter.style.color = "var(--text-dim)";
  }
}

async function submitSummaryForEvaluation() {
  const textarea = document.getElementById("summary-textarea");
  const summaryText = (textarea.value || "").trim();

  if (!summaryText) {
    alert("Por favor escribe tu resumen en inglés antes de solicitar la auditoría.");
    return;
  }

  const btn = document.getElementById("btn-evaluate-summary");
  btn.disabled = true;
  btn.textContent = "Evaluando gramática y vocabulario...";

  try {
    const res = await fetch("/api/reading/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        date: state.currentDate,
        day: state.currentDay,
        summary_text: summaryText
      })
    });
    const data = await res.json();

    if (data.success && data.feedback) {
      renderSummaryFeedback(data.feedback);
      speakEnglish("Summary evaluated successfully!", 1.0);
      fetchStatusAndRefresh();
    } else {
      alert(data.error || "Ocurrió un error al evaluar el resumen.");
    }
  } catch (err) {
    console.error("Error evaluating summary:", err);
    alert("Error de conexión al evaluar.");
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ Auditar y Evaluar con Gemini Flash";
  }
}

function renderSummaryFeedback(f) {
  const container = document.getElementById("summary-evaluation-results");
  if (!container) return;
  container.style.display = "block";

  const matchedHtml = f.matched_vocab && f.matched_vocab.length > 0
    ? `<span class="eval-pill eval-pill-vocab">🎯 Palabras usadas: ${f.matched_vocab.join(", ")}</span>`
    : `<span class="eval-pill" style="background: rgba(255,255,255,0.05); color: var(--text-dim);">No usaste palabras del vocabulario de hoy</span>`;

  let correctionsHtml = "";
  if (f.corrections && f.corrections.length > 0) {
    correctionsHtml = `
      <div class="eval-corrections-list">
        <strong>⚠️ Sugerencias de Corrección Gramatical:</strong>
        ${f.corrections.map(c => `
          <div class="correction-item">
            <span class="correction-wrong">"${c.original}"</span> ➔ <span class="correction-good">"${c.suggestion}"</span>
            <div style="font-size: 0.76rem; color: var(--text-muted);">${c.explanation}</div>
          </div>
        `).join("")}
      </div>
    `;
  } else {
    correctionsHtml = `
      <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; margin-bottom: 0.85rem; font-size: 0.82rem; color: var(--busuu-emerald);">
        ✓ No se detectaron errores comunes de preposiciones ni concordancia básica. ¡Gran redacción!
      </div>
    `;
  }

  container.innerHTML = `
    <h4 style="margin-bottom: 0.75rem; color: var(--text-main);">Resultados de la Auditoría (${f.source || 'IA'}):</h4>
    <div class="eval-metric-pills">
      <span class="eval-pill eval-pill-cefr">Nivel Estimado: ${f.estimated_cefr}</span>
      <span class="eval-pill" style="background: rgba(255,255,255,0.08); color: var(--text-main);">${f.word_count} palabras</span>
      ${matchedHtml}
    </div>
    ${correctionsHtml}
    <div class="native-tip-card">
      <strong>💡 Consejo de Naturalidad Nativa:</strong>
      <p style="margin-top: 0.25rem;">${f.native_phrasing_tip}</p>
    </div>
  `;
}

// =========================================================
// 15-MINUTE COUNTDOWN TIMER
// =========================================================

function updateTimerDisplay() {
  const m = Math.floor(timerSeconds / 60).toString().padStart(2, '0');
  const s = (timerSeconds % 60).toString().padStart(2, '0');
  document.getElementById("reading-timer-display").textContent = `${m}:${s}`;
}

function toggleReadingTimer() {
  const btn = document.getElementById("btn-timer-toggle");
  if (isTimerRunning) {
    clearInterval(timerInterval);
    isTimerRunning = false;
    btn.textContent = "Reanudar";
  } else {
    isTimerRunning = true;
    btn.textContent = "Pausar";
    timerInterval = setInterval(() => {
      if (timerSeconds > 0) {
        timerSeconds--;
        updateTimerDisplay();
      } else {
        clearInterval(timerInterval);
        isTimerRunning = false;
        btn.textContent = "Completado";
        speakEnglish("Fifteen minutes completed! Time to write your translation and summary.", 1.0);
        alert("⏱️ ¡15 minutos cumplidos! Es hora de traducir y resumir.");
      }
    }, 1000);
  }
}

function resetReadingTimer() {
  clearInterval(timerInterval);
  isTimerRunning = false;
  timerSeconds = 15 * 60;
  updateTimerDisplay();
  document.getElementById("btn-timer-toggle").textContent = "Iniciar";
}

// =========================================================
// EVENT LISTENERS INITIALIZATION
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
  // Summary word counter
  const summaryArea = document.getElementById("summary-textarea");
  if (summaryArea) {
    summaryArea.addEventListener("input", updateWordCount);
  }

  // Translation word counter & auto-save
  const transArea = document.getElementById("translation-textarea");
  if (transArea) {
    transArea.addEventListener("input", updateTranslationWordCount);
  }

  // Text selection listener for in-text highlighter
  const contentBox = document.getElementById("reading-content");
  if (contentBox) {
    contentBox.addEventListener("mouseup", handleReadingTextSelection);
    contentBox.addEventListener("touchend", handleReadingTextSelection);
  }
});
