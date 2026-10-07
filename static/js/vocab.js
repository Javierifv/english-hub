/**
 * DUOHUB - Pillar 1: Vocabulary Controller (Busuu & Tobo Edition)
 */

let currentDayWords = [];
let currentQuizRound = 1;
let quizQuestions = [];
let currentQuizIdx = 0;
let quizScore = 0;
let quizWordResults = {}; // { [wordId]: boolean }

function getMasteryBadge(lvl) {
  switch (lvl) {
    case 5: return '🏆 Nivel 5/5';
    case 4: return '🔥 Nivel 4/5';
    case 3: return '⭐ Nivel 3/5';
    case 2: return '📖 Nivel 2/5';
    default: return '🌱 Nivel 1/5';
  }
}

function getMasteryHint(lvl) {
  switch (lvl) {
    case 5: return '¡Dominada al 100%! Superó Ronda 2 (Deletreo activo).';
    case 4: return 'Alta retención en repasos espaciados.';
    case 3: return 'Ronda 1 superada (Significado y Reconocimiento).';
    case 2: return 'En progreso de aprendizaje.';
    default: return 'Pendiente de evaluar en el Test de Dominio.';
  }
}

function renderMasteryStars(lvl) {
  const currentLvl = Math.max(1, Math.min(5, lvl || 1));
  return [1, 2, 3, 4, 5].map(starNum => {
    const isFilled = starNum <= currentLvl;
    const cls = isFilled ? "mastery-star-filled" : "mastery-star-empty";
    return `<span class="${cls}">★</span>`;
  }).join("");
}

async function loadVocabData(day) {
  const container = document.getElementById("vocab-cards-grid");
  try {
    const res = await fetch(`/api/vocab?day=${day}&user_id=${state.currentUser}`);
    const words = await res.json();
    currentDayWords = words;

    if (!words || words.length === 0) {
      container.innerHTML = `<div class="empty-state">No hay palabras disponibles para esta fecha.</div>`;
      return;
    }

    // Update count badge
    const badge = document.getElementById("vocab-count-badge");
    if (badge) badge.textContent = words.length;

    container.innerHTML = words.map(w => renderVocabCard(w)).join("");

  } catch (err) {
    console.error("Error loading vocab:", err);
    container.innerHTML = `<div class="error-state">Error al cargar vocabulario.</div>`;
  }
}

function renderVocabCard(w) {
  const lvl = w.user_mastery || 1;

  const partnerQuote = w.partner_sentence ? `
    <div class="partner-sentence-quote">
      <span class="partner-quote-label">💡 Frase de ${escapeHtml(w.partner_name || 'Compañero')}:</span>
      "${escapeHtml(w.partner_sentence)}"
    </div>
  ` : "";

  return `
    <div class="vocab-card" data-word-id="${w.id}">
      <div class="vocab-card-header">
        <div>
          <div class="vocab-word-title">${escapeHtml(w.word)}</div>
          <div class="vocab-ipa">${w.ipa || ''}</div>
        </div>
        <button class="btn-speak-word" onclick="speakEnglish('${escapeQuotes(w.word)}', 0.9)" title="Escuchar pronunciación nativa">
          🔊
        </button>
      </div>

      <div class="vocab-translation">${escapeHtml(w.translation)}</div>
      <div class="vocab-definition">${escapeHtml(w.definition || '')}</div>

      <div class="vocab-example-box">
        <div class="vocab-example-en">"${escapeHtml(w.example_en || '')}"</div>
        <div class="vocab-example-es">${escapeHtml(w.example_es || '')}</div>
      </div>

      <!-- Automated Tobo Mastery (System Calibrated 1 to 5) -->
      <div class="mastery-system-box" title="Calificación calculada automáticamente por el sistema tras rendir los Tests de Dominio">
        <div class="mastery-title-row">
          <span class="mastery-system-label">
            <span class="tobo-tag">TOBO SRS</span> Retención:
          </span>
          <span class="mastery-badge badge-lvl-${lvl}">
            ${getMasteryBadge(lvl)}
          </span>
        </div>
        <div class="mastery-stars-bar">
          ${renderMasteryStars(lvl)}
        </div>
        <div class="mastery-system-hint">
          ${getMasteryHint(lvl)}
        </div>
      </div>

      <!-- Personal Sentence & Partner Quote -->
      <div class="personal-sentence-box">
        <div class="sentence-input-label">✍️ Tu frase personal de práctica:</div>
        <div class="sentence-input-wrap">
          <textarea id="sentence-input-${w.id}" 
                    class="sentence-textarea"
                    rows="2"
                    placeholder="Escribe aquí tu propia frase con '${escapeHtml(w.word)}'..."
                    onkeydown="if(event.key === 'Enter' && !event.shiftKey){ event.preventDefault(); savePersonalSentence(${w.id}); }">${escapeHtml(w.user_sentence || '')}</textarea>
        </div>
        <div class="sentence-btn-row">
          <button class="btn btn-save-sentence" onclick="savePersonalSentence(${w.id})" title="Guardar frase (visible para tu compañero)">
            💾 Guardar Frase
          </button>
        </div>
        ${partnerQuote}
      </div>
    </div>
  `;
}

function escapeQuotes(str) {
  return (str || '').replace(/'/g, "\\'");
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/* --- SAVE PERSONAL EXAMPLE SENTENCE --- */
async function savePersonalSentence(wordId) {
  const input = document.getElementById(`sentence-input-${wordId}`);
  const sentence = (input.value || "").trim();

  if (!sentence) return;

  try {
    const res = await fetch("/api/vocab/save-sentence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        word_id: wordId,
        sentence: sentence
      })
    });
    const data = await res.json();
    if (data.success) {
      speakEnglish("Sentence saved for your partner to see!", 1.0);
      alert("✓ ¡Frase guardada! Tu compañero la verá en su panel como ejemplo.");
    }
  } catch (err) {
    console.error("Error saving sentence:", err);
  }
}

/* --- SUB-VIEWS TOGGLE (CARDS vs QUIZ vs SRS) --- */
function setVocabSubView(viewName) {
  document.querySelectorAll(".subnav-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById(`subnav-${viewName}`);
  if (btn) btn.classList.add("active");

  document.getElementById("vocab-view-cards").style.display = (viewName === 'cards') ? 'block' : 'none';
  document.getElementById("vocab-view-quiz").style.display = (viewName === 'quiz') ? 'block' : 'none';
  document.getElementById("vocab-view-srs").style.display = (viewName === 'srs') ? 'block' : 'none';
}

function switchVocabView(viewName) {
  setVocabSubView(viewName);
  if (viewName === 'quiz') {
    startDailyVocabQuiz(1);
  } else if (viewName === 'srs') {
    loadSrsView();
  } else if (viewName === 'cards') {
    loadVocabData(state.currentDay);
  }
}

/* --- UNIFIED QUIZ ENGINE & CONTEXT CONTROLLER --- */
let currentQuizContext = {
  mode: 'daily',          // 'daily' | 'srs_queue' | 'srs_single'
  targetWordIds: [],
  wordLabels: [],
  round: 1
};
let srsReviewQueueItems = [];
let srsAllStudiedWords = [];
let srsCurrentFilter = 'all';

async function startDailyVocabQuiz(round = 1) {
  // Ensure currentDayWords is populated
  if (!currentDayWords || currentDayWords.length === 0) {
    try {
      const res = await fetch(`/api/vocab?day=${state.currentDay}&user_id=${state.currentUser}`);
      currentDayWords = await res.json();
    } catch (e) {
      console.error("Error prefetching words for quiz:", e);
    }
  }

  const ids = (currentDayWords || []).map(w => w.id);
  const labels = (currentDayWords || []).map(w => w.word);

  currentQuizContext = {
    mode: 'daily',
    targetWordIds: ids,
    wordLabels: labels,
    round: round
  };

  await startQuizWithContext(round);
}

function startVocabQuiz(round = 1) {
  return startDailyVocabQuiz(round);
}

function startSrsQueueQuiz() {
  if (!srsReviewQueueItems || srsReviewQueueItems.length === 0) return;
  setVocabSubView('quiz');

  currentQuizContext = {
    mode: 'srs_queue',
    targetWordIds: srsReviewQueueItems.map(w => w.id),
    wordLabels: srsReviewQueueItems.map(w => w.word),
    round: 1
  };

  startQuizWithContext(1);
}

function startSingleWordSrsQuiz(wordId, wordName) {
  if (!wordId) return;
  setVocabSubView('quiz');

  currentQuizContext = {
    mode: 'srs_single',
    targetWordIds: [parseInt(wordId)],
    wordLabels: [wordName || 'Palabra'],
    round: 1
  };

  startQuizWithContext(1);
}

async function startQuizWithContext(round = 1) {
  currentQuizRound = round;
  currentQuizContext.round = round;
  quizScore = 0;
  currentQuizIdx = 0;
  quizWordResults = {};

  const badge = document.getElementById("quiz-round-badge");
  if (badge) {
    if (currentQuizContext.mode === 'srs_single') {
      const wName = currentQuizContext.wordLabels[0] || 'Palabra';
      badge.textContent = `🎯 REPASO INDIVIDUAL: "${wName.toUpperCase()}" (RONDA ${round} DE 2)`;
    } else if (currentQuizContext.mode === 'srs_queue') {
      const count = currentQuizContext.targetWordIds.length;
      badge.textContent = `⚡ REPASO ESPACIADO: ${count} PALABRAS (RONDA ${round} DE 2)`;
    } else {
      badge.textContent = (round === 1) 
        ? "RONDA 1: RECONOCIMIENTO (NIVEL 3/5)" 
        : "RONDA 2: MAYOR DIFICULTAD (NIVEL 5/5)";
    }
  }

  document.getElementById("quiz-score-indicator").textContent = "Aciertos: 0";
  document.getElementById("btn-next-quiz").style.display = "none";
  document.getElementById("quiz-progress-bar").style.width = "0%";

  if (!currentQuizContext.targetWordIds || currentQuizContext.targetWordIds.length === 0) {
    document.getElementById("quiz-prompt-box").textContent = "No hay palabras seleccionadas para evaluar.";
    return;
  }

  // Initialize per-word success tracker to true
  currentQuizContext.targetWordIds.forEach(id => {
    quizWordResults[id] = true;
  });

  const wordIdsParam = currentQuizContext.targetWordIds.join(",");

  try {
    const res = await fetch(`/api/vocab/quiz?word_ids=${wordIdsParam}&round=${round}&user_id=${state.currentUser}&day=${state.currentDay}`);
    const questions = await res.json();
    quizQuestions = questions;

    if (!questions || questions.length === 0) {
      document.getElementById("quiz-prompt-box").textContent = "No hay preguntas disponibles para esta evaluación.";
      return;
    }

    renderQuizQuestion(0);
  } catch (err) {
    console.error("Error loading quiz:", err);
    document.getElementById("quiz-prompt-box").textContent = "Error de conexión al cargar las preguntas del test.";
  }
}

let currentScramble = null;

function renderQuizQuestion(idx) {
  if (idx >= quizQuestions.length) {
    finishQuiz();
    return;
  }

  const q = quizQuestions[idx];
  currentQuizIdx = idx;

  document.getElementById("quiz-question-title").textContent = `Pregunta ${idx + 1} de ${quizQuestions.length}`;
  const pct = Math.round(((idx + 1) / quizQuestions.length) * 100);
  document.getElementById("quiz-progress-bar").style.width = `${pct}%`;

  const promptBox = document.getElementById("quiz-prompt-box");
  const grid = document.getElementById("quiz-options-grid");
  document.getElementById("btn-next-quiz").style.display = "none";

  if (q.type === "listening") {
    grid.style.display = "grid";
    promptBox.innerHTML = `
      <div style="margin-bottom: 0.5rem;">🎧 ${q.prompt}</div>
      <button class="btn btn-secondary btn-sm" onclick="speakEnglish('${escapeQuotes(q.correct)}', 0.9)" style="margin: 0.5rem auto;">
        🔊 Reproducir Audio
      </button>
    `;
    speakEnglish(q.correct, 0.9);

    grid.innerHTML = q.options.map(opt => `
      <button class="quiz-option-btn" onclick="handleQuizAnswer(this, '${escapeQuotes(opt)}', '${escapeQuotes(q.correct)}', ${q.word_id})">
        ${escapeHtml(opt)}
      </button>
    `).join("");

  } else if (q.type === "scramble") {
    grid.style.display = "none"; // Hide default 2-col button grid
    initScramblePuzzle(q);

  } else {
    // Standard multiple choice (meaning or reverse_meaning)
    grid.style.display = "grid";
    promptBox.innerHTML = `<div>${q.prompt}</div>`;

    grid.innerHTML = q.options.map(opt => `
      <button class="quiz-option-btn" onclick="handleQuizAnswer(this, '${escapeQuotes(opt)}', '${escapeQuotes(q.correct)}', ${q.word_id})">
        ${escapeHtml(opt)}
      </button>
    `).join("");
  }
}

/* --- SCRAMBLE PUZZLE CONTROLLER (Round 2: Horizontal & Badge Inventory) --- */
function initScramblePuzzle(q) {
  const promptBox = document.getElementById("quiz-prompt-box");

  // Count occurrences of each character in target (including spaces)
  const charCounts = {};
  for (const char of q.target) {
    charCounts[char] = (charCounts[char] || 0) + 1;
  }

  // Generate unique character tiles
  const uniqueChars = Object.keys(charCounts);
  
  // Shuffle unique tiles so they are not in sequential word order
  for (let i = uniqueChars.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [uniqueChars[i], uniqueChars[j]] = [uniqueChars[j], uniqueChars[i]];
  }

  const tiles = uniqueChars.map(char => ({
    char: char,
    total: charCounts[char],
    available: charCounts[char]
  }));

  currentScramble = {
    wordId: q.word_id,
    target: q.target,
    displayWord: q.display_word,
    translation: q.translation,
    slots: Array(q.target.length).fill(null), // stores char placed at each slot index
    tiles: tiles
  };

  promptBox.innerHTML = `
    <div class="scramble-puzzle-wrap">
      <div class="scramble-translation-prompt">🇪🇸 Traduce y Ordena en inglés: <strong>"${escapeHtml(q.translation)}"</strong></div>
      
      <!-- Horizontal slots where letters land side-by-side -->
      <div class="scramble-slots-row" id="scramble-slots-row"></div>

      <!-- Horizontal unique character tiles with count badges -->
      <div class="scramble-tiles-row" id="scramble-tiles-row"></div>

      <div class="scramble-actions">
        <button type="button" class="btn btn-secondary btn-sm" onclick="resetScramble()">🔄 Deshacer Todo</button>
        <button type="button" class="btn btn-ghost btn-sm" onclick="speakEnglish('${escapeQuotes(q.display_word)}', 0.9)">🔊 Escuchar Pista</button>
      </div>
    </div>
  `;

  renderScrambleBoard();
  attachScrambleKeyboardListener();
}

function renderScrambleBoard() {
  const slotsRow = document.getElementById("scramble-slots-row");
  const tilesRow = document.getElementById("scramble-tiles-row");
  if (!slotsRow || !tilesRow || !currentScramble) return;

  // Render Horizontal Slots
  slotsRow.innerHTML = currentScramble.slots.map((char, slotIdx) => {
    if (char !== null) {
      const isSpace = (char === " ");
      const displayContent = isSpace ? "␣" : escapeHtml(char);
      const spaceClass = isSpace ? "space-slot" : "";
      return `<div class="scramble-slot filled ${spaceClass}" onclick="removeScrambleSlot(${slotIdx})" title="Clic para quitar letra">${displayContent}</div>`;
    }
    return `<div class="scramble-slot" title="Casilla vacía"></div>`;
  }).join("");

  // Render Horizontal Unique Tiles with inventory count badge
  tilesRow.innerHTML = currentScramble.tiles.map(tile => {
    const isSpace = (tile.char === " ");
    const isDepleted = tile.available <= 0;
    const spaceClass = isSpace ? "tile-space" : "";
    const depletedClass = isDepleted ? "depleted" : "";
    const displayLabel = isSpace ? "␣ Espacio" : escapeHtml(tile.char);

    // Show badge on top if this letter repeats (total > 1)
    const badgeHtml = (tile.total > 1) 
      ? `<span class="tile-count-badge ${isDepleted ? 'zero' : ''}">${tile.available}</span>` 
      : "";

    return `
      <button type="button" class="scramble-tile ${spaceClass} ${depletedClass}" 
              onclick="tapScrambleTile('${isSpace ? ' ' : escapeQuotes(tile.char)}')"
              ${isDepleted ? 'disabled' : ''}
              title="${isSpace ? 'Espacio (Disponibles: ' + tile.available + ')' : 'Letra ' + tile.char + ' (Disponibles: ' + tile.available + ')'}">
        <span>${displayLabel}</span>
        ${badgeHtml}
      </button>
    `;
  }).join("");
}

function tapScrambleTile(char) {
  if (!currentScramble) return;
  const tile = currentScramble.tiles.find(t => t.char === char);
  if (!tile || tile.available <= 0) return;

  // Find first empty slot
  const emptyIdx = currentScramble.slots.findIndex(s => s === null);
  if (emptyIdx === -1) return;

  tile.available--;
  currentScramble.slots[emptyIdx] = char;
  renderScrambleBoard();

  // Check if all slots filled
  if (!currentScramble.slots.includes(null)) {
    checkScrambleAnswer();
  }
}

function removeScrambleSlot(slotIdx) {
  if (!currentScramble) return;
  const char = currentScramble.slots[slotIdx];
  if (char === null) return;

  // Restore inventory count
  const tile = currentScramble.tiles.find(t => t.char === char);
  if (tile) {
    tile.available = Math.min(tile.total, tile.available + 1);
  }

  currentScramble.slots[slotIdx] = null;
  renderScrambleBoard();
}

function resetScramble() {
  if (!currentScramble) return;
  currentScramble.slots = Array(currentScramble.target.length).fill(null);
  currentScramble.tiles.forEach(t => {
    t.available = t.total;
  });
  renderScrambleBoard();
}

function checkScrambleAnswer() {
  const assembled = currentScramble.slots.map(s => s || "").join("");
  const slotsRow = document.getElementById("scramble-slots-row");
  const slotElements = slotsRow ? slotsRow.querySelectorAll(".scramble-slot") : [];

  if (assembled.toUpperCase() === currentScramble.target.toUpperCase()) {
    slotElements.forEach(el => el.classList.add("correct-all"));
    quizScore++;
    document.getElementById("quiz-score-indicator").textContent = `Aciertos: ${quizScore}`;
    speakEnglish(currentScramble.displayWord, 1.0);
    document.getElementById("btn-next-quiz").style.display = "inline-flex";
  } else {
    slotElements.forEach(el => el.classList.add("wrong-all"));
    if (currentScramble.wordId) {
      quizWordResults[currentScramble.wordId] = false;
    }
    setTimeout(() => {
      resetScramble();
    }, 750);
  }
}

function attachScrambleKeyboardListener() {
  window.removeEventListener("keydown", handleScrambleKeydown);
  window.addEventListener("keydown", handleScrambleKeydown);
}

function handleScrambleKeydown(e) {
  const slotsRow = document.getElementById("scramble-slots-row");
  if (!slotsRow || !currentScramble) return;

  // Do not intercept if user is typing into any input or textarea
  if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;

  if (e.key === "Backspace") {
    e.preventDefault();
    for (let i = currentScramble.slots.length - 1; i >= 0; i--) {
      if (currentScramble.slots[i] !== null) {
        removeScrambleSlot(i);
        break;
      }
    }
  } else if (e.key === " ") {
    e.preventDefault();
    tapScrambleTile(" ");
  } else if (e.key.length === 1 && /[a-zA-Z]/.test(e.key)) {
    const upper = e.key.toUpperCase();
    tapScrambleTile(upper);
  }
}

function handleQuizAnswer(btn, chosen, correct, wordId) {
  const allBtns = document.querySelectorAll(".quiz-option-btn");
  allBtns.forEach(b => b.disabled = true);

  if (chosen.toLowerCase() === correct.toLowerCase()) {
    btn.classList.add("correct");
    quizScore++;
    document.getElementById("quiz-score-indicator").textContent = `Aciertos: ${quizScore}`;
    speakEnglish("Correct!", 1.1);
  } else {
    btn.classList.add("wrong");
    if (wordId) {
      quizWordResults[wordId] = false;
    }
    allBtns.forEach(b => {
      if (b.textContent.trim().toLowerCase() === correct.toLowerCase()) {
        b.classList.add("correct");
      }
    });
    speakEnglish(correct, 0.95);
  }

  document.getElementById("btn-next-quiz").style.display = "inline-flex";
}

function nextQuizQuestion() {
  renderQuizQuestion(currentQuizIdx + 1);
}

async function finishQuiz() {
  const promptBox = document.getElementById("quiz-prompt-box");
  const grid = document.getElementById("quiz-options-grid");
  const nextBtn = document.getElementById("btn-next-quiz");
  nextBtn.style.display = "none";

  const total = quizQuestions.length;

  // Submit results to backend for automated Tobo mastery calculation
  try {
    await fetch("/api/vocab/quiz/submit-results", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        round: currentQuizRound,
        word_results: quizWordResults,
        date: state.currentDateStr,
        day: state.currentDay
      })
    });
  } catch (e) {
    console.error("Error submitting quiz results:", e);
  }

  // Update header progress in real-time
  if (typeof updateStatusHeader === "function") {
    updateStatusHeader();
  }

  if (currentQuizRound === 1) {
    const isSrs = currentQuizContext.mode && currentQuizContext.mode.startsWith('srs');
    const wordLabelText = currentQuizContext.mode === 'srs_single' 
      ? `la palabra "${currentQuizContext.wordLabels[0]}"`
      : (isSrs ? `las palabras de repaso (${currentQuizContext.targetWordIds.length})` : 'las palabras de hoy');

    promptBox.innerHTML = `
      <div style="font-size: 2.2rem; margin-bottom: 0.35rem;">⭐</div>
      <div style="color: var(--busuu-emerald); font-size: 1.55rem; font-weight: 800;">¡Ronda 1 Completada con Éxito!</div>
      <div style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.35rem;">
        Obtuviste <strong>${quizScore}</strong> de <strong>${total}</strong> aciertos. Has alcanzado <strong>Nivel 3/5</strong> en ${wordLabelText}.
      </div>
      <div style="background: #EFF6FF; border: 1.5px solid #BFDBFE; border-radius: var(--radius-sm); padding: 0.85rem 1rem; margin: 1.25rem auto 0; max-width: 520px; color: #1E40AF; font-size: 0.88rem; text-align: left; line-height: 1.45;">
        💡 <strong>Sistema Tobo SRS:</strong> Has superado el test de reconocimiento inicial. Para desbloquear el <strong>Nivel 5/5 (Dominio Total 🏆)</strong>, rinde la <strong>Ronda 2</strong> con mayor dificultad (deletreo activo y traducción).
      </div>
    `;

    grid.style.display = "grid";
    grid.innerHTML = `
      <div style="grid-column: span 2; display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; margin-top: 0.5rem;">
        <button class="btn btn-primary btn-lg" onclick="startQuizWithContext(2)">
          🚀 Iniciar Ronda 2 (Mayor Dificultad - Desbloquear Nivel 5/5)
        </button>
        ${isSrs ? `
          <button class="btn btn-secondary btn-lg" onclick="switchVocabView('srs');">
            📊 Volver al Banco de Repaso
          </button>
        ` : `
          <button class="btn btn-secondary btn-lg" onclick="loadVocabData(state.currentDay); switchVocabView('cards');">
            🗂️ Ver Tarjetas Actualizadas (Nivel 3/5)
          </button>
        `}
      </div>
    `;
  } else {
    // Round 2 completed!
    const isSrs = currentQuizContext.mode && currentQuizContext.mode.startsWith('srs');
    const wordLabelText = currentQuizContext.mode === 'srs_single' 
      ? `la palabra "${currentQuizContext.wordLabels[0]}"`
      : (isSrs ? `las palabras evaluadas` : 'las palabras de hoy');

    promptBox.innerHTML = `
      <div style="font-size: 2.4rem; margin-bottom: 0.35rem;">🏆</div>
      <div style="color: var(--busuu-emerald); font-size: 1.6rem; font-weight: 800;">¡Dominio Total Desbloqueado!</div>
      <div style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.35rem;">
        Obtuviste <strong>${quizScore}</strong> de <strong>${total}</strong> aciertos. Has alcanzado el <strong>Nivel 5/5 (⭐⭐⭐⭐⭐)</strong> en ${wordLabelText}.
      </div>
      <div style="background: #ECFDF5; border: 1.5px solid #A7F3D0; border-radius: var(--radius-sm); padding: 0.85rem 1rem; margin: 1.25rem auto 0; max-width: 520px; color: #065F46; font-size: 0.88rem; text-align: left; line-height: 1.45;">
        🎉 <strong>¡Excelente trabajo!</strong> Has demostrado retención activa en deletreo y traducción. Las palabras han sido registradas como dominadas al 100% en tu banco de repaso espaciado.
      </div>
    `;

    grid.style.display = "grid";
    grid.innerHTML = `
      <div style="grid-column: span 2; display: flex; gap: 0.75rem; justify-content: center; margin-top: 0.5rem;">
        ${isSrs ? `
          <button class="btn btn-success btn-lg" onclick="switchVocabView('srs');">
            📊 Volver al Banco de Repaso (Ver Nivel 5/5)
          </button>
        ` : `
          <button class="btn btn-success btn-lg" onclick="loadVocabData(state.currentDay); switchVocabView('cards');">
            🗂️ Volver a Tarjetas (Ver Nivel 5/5)
          </button>
        `}
      </div>
    `;
  }
}

/* --- SPACED REPETITION (SRS) VIEW --- */
async function loadSrsView() {
  try {
    const res = await fetch(`/api/vocab/srs?user_id=${state.currentUser}`);
    const data = await res.json();

    srsReviewQueueItems = data.review_queue || [];
    srsAllStudiedWords = data.all_studied || [];

    document.getElementById("srs-total-val").textContent = data.stats.total_studied || 0;
    document.getElementById("srs-mastered-val").textContent = data.stats.mastered || 0;
    document.getElementById("srs-progress-val").textContent = data.stats.in_progress || 0;
    document.getElementById("srs-review-val").textContent = data.stats.needs_review || 0;

    // Apply currently selected filter (defaults to 'all')
    filterSrsWords(srsCurrentFilter);
  } catch (err) {
    console.error("Error loading SRS stats:", err);
  }
}

function filterSrsWords(filterType) {
  srsCurrentFilter = filterType || 'all';

  // Highlight active filter card
  const cards = {
    'all': 'srs-card-all',
    'mastered': 'srs-card-mastered',
    'progress': 'srs-card-progress',
    'review': 'srs-card-review'
  };

  Object.entries(cards).forEach(([key, elemId]) => {
    const elem = document.getElementById(elemId);
    if (elem) {
      if (key === srsCurrentFilter) {
        elem.classList.add("active-filter");
      } else {
        elem.classList.remove("active-filter");
      }
    }
  });

  // Filter words
  let filtered = [];
  let title = "";
  let subtitle = "";

  if (srsCurrentFilter === 'mastered') {
    filtered = srsAllStudiedWords.filter(w => (w.mastery_level || 1) === 5);
    title = `🏆 Palabras Dominadas - Nivel 5 (${filtered.length})`;
    subtitle = "Palabras aprendidas al 100% que dominas tanto en deletreo como en traducción.";
  } else if (srsCurrentFilter === 'progress') {
    filtered = srsAllStudiedWords.filter(w => (w.mastery_level || 1) === 3 || (w.mastery_level || 1) === 4);
    title = `⚡ Palabras en Proceso - Nivel 3 y 4 (${filtered.length})`;
    subtitle = "Palabras que reconoces pero aún necesitan consolidar la Ronda 2 (escritura/deletreo).";
  } else if (srsCurrentFilter === 'review') {
    filtered = srsAllStudiedWords.filter(w => (w.mastery_level || 1) <= 2);
    title = `🔄 Palabras por Repasar - Nivel 1 y 2 (${filtered.length})`;
    subtitle = "Palabras con dificultad o recién introducidas que requieren refuerzo prioritario.";
  } else {
    // 'all'
    filtered = srsAllStudiedWords;
    title = `📚 Todas las Palabras Estudiadas (${filtered.length})`;
    subtitle = "Historial acumulado de todas las palabras aprendidas a lo largo de tus sesiones.";
  }

  // Update header text
  const titleEl = document.getElementById("srs-section-title");
  const subEl = document.getElementById("srs-section-subtitle");
  if (titleEl) titleEl.textContent = title;
  if (subEl) subEl.textContent = subtitle;

  // Action button container: show batch test button if there are words in review queue
  const actionContainer = document.getElementById("srs-queue-action-container");
  if (actionContainer) {
    if (srsReviewQueueItems && srsReviewQueueItems.length > 0) {
      actionContainer.innerHTML = `
        <button class="btn btn-primary btn-sm" onclick="startSrsQueueQuiz()" title="Evaluar todas las palabras pendientes en test">
          ⚡ Practicar ${srsReviewQueueItems.length} pendientes en Test
        </button>
      `;
    } else {
      actionContainer.innerHTML = "";
    }
  }

  renderSrsWordList(filtered, srsCurrentFilter);
}

function renderSrsWordList(words, filterType) {
  const container = document.getElementById("srs-queue-list");
  if (!container) return;

  if (!words || words.length === 0) {
    let emptyMsg = "No hay palabras registradas en esta categoría.";
    if (filterType === 'review') {
      emptyMsg = "🎉 ¡Excelente! No tienes palabras pendientes de repasar (Nivel 1-2).";
    } else if (filterType === 'progress') {
      emptyMsg = "No tienes palabras en proceso intermedio (Nivel 3-4).";
    } else if (filterType === 'mastered') {
      emptyMsg = "Aún no tienes palabras dominadas al Nivel 5. ¡Rinde la Ronda 2 en el Test de Dominio para desbloquearlas!";
    }

    container.innerHTML = `
      <div class="empty-state" style="text-align: center; padding: 2rem; color: var(--text-muted); background: #F8FAFC; border: 1.5px dashed var(--border-subtle); border-radius: var(--radius-sm);">
        <div style="font-size: 1.8rem; margin-bottom: 0.35rem;">✨</div>
        <strong>${emptyMsg}</strong>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="srs-queue-items-wrap">
      ${words.map(item => `
        <div class="srs-queue-item">
          <div class="srs-item-left">
            <div class="srs-item-header">
              <span class="srs-queue-word">${escapeHtml(item.word)}</span>
              ${item.ipa ? `<span class="srs-queue-ipa">${escapeHtml(item.ipa)}</span>` : ''}
              <button class="btn-speak-word" onclick="speakEnglish('${escapeQuotes(item.word)}', 0.9)" title="Escuchar pronunciación de la palabra">🔊</button>
            </div>
            <div class="srs-queue-trans">${escapeHtml(item.translation)}</div>
            ${item.example_en ? `
              <div class="srs-queue-example-box">
                <span class="srs-queue-ex-en">"${escapeHtml(item.example_en)}"</span>
                <button class="btn-speak-sentence-mini" onclick="speakEnglish('${escapeQuotes(item.example_en)}', 0.9)" title="Escuchar frase de ejemplo">🎧</button>
                ${item.example_es ? `
                  <span class="srs-queue-ex-es">${escapeHtml(item.example_es)}</span>
                ` : ''}
              </div>
            ` : ''}
            ${item.personal_sentence ? `
              <div class="srs-queue-personal" style="font-size: 0.78rem; color: var(--busuu-emerald); margin-top: 0.35rem;">
                ✍️ Tu frase personal: <em>"${escapeHtml(item.personal_sentence)}"</em>
              </div>
            ` : ''}
          </div>
          <div class="srs-item-right">
            <span class="mastery-badge badge-lvl-${item.mastery_level || 1}">${getMasteryBadge(item.mastery_level || 1)}</span>
            ${(item.mastery_level || 1) < 5 ? `
              <button class="btn btn-secondary btn-sm" onclick="startSingleWordSrsQuiz(${item.id}, '${escapeQuotes(item.word)}')" title="Evaluar solo esta palabra en test">🎯 Test</button>
            ` : `
              <span class="srs-mastered-check" title="Dominio total al 100%">🏆 Dominada</span>
            `}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

/* --- QUICK ACTIVATION MINI PRACTICE --- */
function checkVocabPractice() {
  const input = document.getElementById("vocab-practice-input");
  const feedback = document.getElementById("vocab-practice-feedback");
  const text = (input.value || "").trim().toLowerCase();

  if (!text) {
    feedback.textContent = "Por favor escribe una oración en inglés primero.";
    feedback.style.color = "var(--busuu-amber)";
    return;
  }

  const detected = currentDayWords.filter(w => {
    const regex = new RegExp(`\\b${w.word.toLowerCase()}\\b`, 'i');
    return regex.test(text);
  });

  if (detected.length >= 2) {
    feedback.innerHTML = `🎉 <strong>¡Brillante!</strong> Has utilizado ${detected.length} palabras de hoy: <em>${detected.map(d => d.word).join(", ")}</em>. Excelente activación mental.`;
    feedback.style.color = "var(--busuu-emerald)";
  } else if (detected.length === 1) {
    feedback.innerHTML = `👍 Bien, detectamos <em>"${detected[0].word}"</em>. Intenta agregar una segunda palabra de la lista para completar el reto.`;
    feedback.style.color = "var(--busuu-amber)";
  } else {
    feedback.innerHTML = `Intenta incluir alguna de las palabras de hoy: ${currentDayWords.map(w => `<strong>${w.word}</strong>`).join(", ")}.`;
    feedback.style.color = "var(--text-muted)";
  }
}

async function markVocabDone() {
  try {
    const res = await fetch("/api/vocab/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        date: state.currentDate,
        day: state.currentDay,
        notes: document.getElementById("vocab-practice-input").value
      })
    });
    const data = await res.json();
    if (data.success) {
      speakEnglish("Vocabulary completed! Great job.", 1.0);
      fetchStatusAndRefresh();
    }
  } catch (err) {
    console.error("Error completing vocab:", err);
  }
}
