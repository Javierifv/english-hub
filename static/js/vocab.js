/**
 * DUOHUB - Pillar 1: Vocabulary Controller (Busuu & Tobo Edition)
 */

let currentDayWords = [];
let quizQuestions = [];
let currentQuizIdx = 0;
let quizScore = 0;

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

    container.innerHTML = words.map(w => renderVocabCard(w)).join("");

  } catch (err) {
    console.error("Error loading vocab:", err);
    container.innerHTML = `<div class="error-state">Error al cargar vocabulario.</div>`;
  }
}

function renderVocabCard(w) {
  const starsHtml = [1, 2, 3, 4, 5].map(starNum => {
    const isActive = (w.user_mastery || 1) >= starNum ? "active" : "";
    return `<button class="star-btn ${isActive}" onclick="rateWordMastery(${w.id}, ${starNum}, this)" title="Calificar nivel ${starNum} de 5">★</button>`;
  }).join("");

  const partnerQuote = w.partner_sentence ? `
    <div class="partner-sentence-quote">
      <span class="partner-quote-label">💡 Frase de ${w.partner_name || 'Compañero'}:</span>
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

      <!-- Mastery Rating (Scale 1 to 5) -->
      <div class="mastery-rating-box">
        <div class="mastery-title-row">
          <span>Nivel de Retención:</span>
          <span class="rating-label-text" id="rating-text-${w.id}">Nivel ${w.user_mastery || 1}/5</span>
        </div>
        <div class="stars-selector" id="stars-row-${w.id}">
          ${starsHtml}
        </div>
      </div>

      <!-- Personal Sentence & Partner Quote -->
      <div class="personal-sentence-box">
        <div class="sentence-input-row">
          <input type="text" id="sentence-input-${w.id}" placeholder="Tu frase con '${escapeHtml(w.word)}'..." value="${escapeHtml(w.user_sentence || '')}">
          <button class="btn btn-secondary btn-sm" onclick="savePersonalSentence(${w.id})" title="Guardar frase (visible para tu compañero)">
            Guardar
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

/* --- RATE MASTERY (1 TO 5 STARS) --- */
async function rateWordMastery(wordId, rating, btn) {
  try {
    const res = await fetch("/api/vocab/rate-mastery", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        word_id: wordId,
        rating: rating
      })
    });
    const data = await res.json();
    if (data.success) {
      // Update stars visually
      const row = document.getElementById(`stars-row-${wordId}`);
      if (row) {
        const starButtons = row.querySelectorAll(".star-btn");
        starButtons.forEach((sBtn, idx) => {
          sBtn.classList.toggle("active", idx < rating);
        });
      }
      const label = document.getElementById(`rating-text-${wordId}`);
      if (label) label.textContent = `Nivel ${rating}/5`;
    }
  } catch (err) {
    console.error("Error rating word:", err);
  }
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
function switchVocabView(viewName) {
  document.querySelectorAll(".subnav-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(`subnav-${viewName}`).classList.add("active");

  document.getElementById("vocab-view-cards").style.display = (viewName === 'cards') ? 'block' : 'none';
  document.getElementById("vocab-view-quiz").style.display = (viewName === 'quiz') ? 'block' : 'none';
  document.getElementById("vocab-view-srs").style.display = (viewName === 'srs') ? 'block' : 'none';

  if (viewName === 'quiz') {
    startVocabQuiz();
  } else if (viewName === 'srs') {
    loadSrsView();
  }
}

/* --- INTERACTIVE QUIZ ENGINE (TOBO / BUSUU STYLE) --- */
async function startVocabQuiz() {
  quizScore = 0;
  currentQuizIdx = 0;
  document.getElementById("quiz-score-indicator").textContent = "Aciertos: 0";
  document.getElementById("btn-next-quiz").style.display = "none";

  try {
    const res = await fetch(`/api/vocab/quiz?day=${state.currentDay}&user_id=${state.currentUser}`);
    const questions = await res.json();
    quizQuestions = questions;

    if (!questions || questions.length === 0) {
      document.getElementById("quiz-prompt-box").textContent = "No hay preguntas disponibles para el quiz de hoy.";
      return;
    }

    renderQuizQuestion(0);
  } catch (err) {
    console.error("Error loading quiz:", err);
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
      <button class="quiz-option-btn" onclick="handleQuizAnswer(this, '${escapeQuotes(opt)}', '${escapeQuotes(q.correct)}')">
        ${escapeHtml(opt)}
      </button>
    `).join("");

  } else if (q.type === "scramble") {
    grid.style.display = "none"; // Hide default 2-col button grid
    initScramblePuzzle(q);

  } else {
    // Standard multiple choice
    grid.style.display = "grid";
    promptBox.innerHTML = `<div>${q.prompt}</div>`;

    grid.innerHTML = q.options.map(opt => `
      <button class="quiz-option-btn" onclick="handleQuizAnswer(this, '${escapeQuotes(opt)}', '${escapeQuotes(q.correct)}')">
        ${escapeHtml(opt)}
      </button>
    `).join("");
  }
}

/* --- SCRAMBLE PUZZLE CONTROLLER --- */
function initScramblePuzzle(q) {
  const promptBox = document.getElementById("quiz-prompt-box");
  currentScramble = {
    target: q.target,
    displayWord: q.display_word,
    slots: Array(q.target.length).fill(null), // will store { char, tileIdx }
    tiles: q.letters.map((char, idx) => ({ char, idx, used: false }))
  };

  promptBox.innerHTML = `
    <div class="scramble-puzzle-wrap">
      <div class="scramble-translation-prompt">🇪🇸 Traduce y Ordena: <strong>"${escapeHtml(q.translation)}"</strong></div>
      
      <!-- Slots where letters will land -->
      <div class="scramble-slots-row" id="scramble-slots-row"></div>

      <!-- Letter Tiles to tap -->
      <div class="scramble-tiles-row" id="scramble-tiles-row"></div>

      <div class="scramble-actions">
        <button class="btn btn-secondary btn-sm" onclick="resetScramble()">🔄 Deshacer</button>
        <button class="btn btn-ghost btn-sm" onclick="speakEnglish('${escapeQuotes(q.display_word)}', 0.9)">🔊 Escuchar Pista</button>
      </div>
    </div>
  `;

  renderScrambleBoard();
}

function renderScrambleBoard() {
  const slotsRow = document.getElementById("scramble-slots-row");
  const tilesRow = document.getElementById("scramble-tiles-row");
  if (!slotsRow || !tilesRow || !currentScramble) return;

  // Render Slots
  slotsRow.innerHTML = currentScramble.slots.map((s, slotIdx) => {
    if (s) {
      return `<div class="scramble-slot filled" onclick="removeScrambleSlot(${slotIdx})" title="Clic para quitar letra">${s.char}</div>`;
    }
    return `<div class="scramble-slot"></div>`;
  }).join("");

  // Render Tiles
  tilesRow.innerHTML = currentScramble.tiles.map((t, tileIdx) => {
    const usedClass = t.used ? "used" : "";
    return `<button class="scramble-tile ${usedClass}" onclick="tapScrambleTile(${tileIdx})">${t.char}</button>`;
  }).join("");
}

function tapScrambleTile(tileIdx) {
  if (!currentScramble) return;
  const tile = currentScramble.tiles[tileIdx];
  if (tile.used) return;

  // Find first empty slot
  const emptyIdx = currentScramble.slots.findIndex(s => s === null);
  if (emptyIdx === -1) return;

  tile.used = true;
  currentScramble.slots[emptyIdx] = { char: tile.char, tileIdx: tile.idx };
  renderScrambleBoard();

  // Check if all slots filled
  if (!currentScramble.slots.includes(null)) {
    checkScrambleAnswer();
  }
}

function removeScrambleSlot(slotIdx) {
  if (!currentScramble) return;
  const item = currentScramble.slots[slotIdx];
  if (!item) return;

  // Restore tile
  const tile = currentScramble.tiles[item.tileIdx];
  if (tile) tile.used = false;

  currentScramble.slots[slotIdx] = null;
  renderScrambleBoard();
}

function resetScramble() {
  if (!currentScramble) return;
  currentScramble.slots = Array(currentScramble.target.length).fill(null);
  currentScramble.tiles.forEach(t => t.used = false);
  renderScrambleBoard();
}

function checkScrambleAnswer() {
  const assembled = currentScramble.slots.map(s => s.char).join("");
  const slotsRow = document.getElementById("scramble-slots-row");
  const slotElements = slotsRow.querySelectorAll(".scramble-slot");

  if (assembled.toUpperCase() === currentScramble.target.toUpperCase()) {
    slotElements.forEach(el => el.classList.add("correct-all"));
    quizScore++;
    document.getElementById("quiz-score-indicator").textContent = `Aciertos: ${quizScore}`;
    speakEnglish(currentScramble.displayWord, 1.0);
    document.getElementById("btn-next-quiz").style.display = "inline-flex";
  } else {
    slotElements.forEach(el => el.classList.add("wrong-all"));
    setTimeout(() => {
      resetScramble();
    }, 800);
  }
}

function handleQuizAnswer(btn, chosen, correct) {
  const allBtns = document.querySelectorAll(".quiz-option-btn");
  allBtns.forEach(b => b.disabled = true);

  if (chosen.toLowerCase() === correct.toLowerCase()) {
    btn.classList.add("correct");
    quizScore++;
    document.getElementById("quiz-score-indicator").textContent = `Aciertos: ${quizScore}`;
    speakEnglish("Correct!", 1.1);
  } else {
    btn.classList.add("wrong");
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
  promptBox.innerHTML = `
    <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🎉</div>
    <div style="color: var(--busuu-emerald); font-size: 1.6rem; font-weight: 800;">¡Quiz Completado!</div>
    <div style="color: var(--text-muted); font-size: 1rem; margin-top: 0.25rem;">
      Obtuviste <strong>${quizScore}</strong> de <strong>${total}</strong> aciertos.
    </div>
  `;

  grid.innerHTML = `
    <div style="grid-column: span 2; text-align: center;">
      <button class="btn btn-success btn-lg" onclick="markVocabDone(); switchVocabView('cards');">
        ✓ Confirmar Vocabulario de Hoy
      </button>
    </div>
  `;

  // Auto-mark vocab as completed
  await markVocabDone();
}

/* --- SPACED REPETITION (SRS) VIEW --- */
async function loadSrsView() {
  try {
    const res = await fetch(`/api/vocab/srs?user_id=${state.currentUser}`);
    const data = await res.json();

    document.getElementById("srs-total-val").textContent = data.stats.total_studied || 0;
    document.getElementById("srs-mastered-val").textContent = data.stats.mastered || 0;
    document.getElementById("srs-progress-val").textContent = data.stats.in_progress || 0;
    document.getElementById("srs-review-val").textContent = data.stats.needs_review || 0;

    const queueList = document.getElementById("srs-queue-list");
    if (!data.review_queue || data.review_queue.length === 0) {
      queueList.innerHTML = `
        <div class="empty-state" style="text-align: center; padding: 1.5rem; color: var(--busuu-emerald);">
          ✓ ¡No tienes palabras pendientes de repaso urgente! Todas están en nivel 4 o 5.
        </div>
      `;
      return;
    }

    queueList.innerHTML = data.review_queue.map(item => `
      <div class="srs-queue-item">
        <div>
          <div class="srs-queue-word">${escapeHtml(item.word)}</div>
          <div class="srs-queue-trans">${escapeHtml(item.translation)}</div>
          <div style="font-size: 0.78rem; color: var(--text-dim); margin-top: 0.2rem;">"${escapeHtml(item.example_en || '')}"</div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <button class="btn-speak-word" onclick="speakEnglish('${escapeQuotes(item.word)}', 0.9)" title="Escuchar">🔊</button>
          <button class="btn btn-sm btn-outline" onclick="rateWordMastery(${item.id}, ${Math.min(5, (item.mastery_level || 1) + 1)}, this); loadSrsView();">
            ⭐ Subir Nivel (+1)
          </button>
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error("Error loading SRS stats:", err);
  }
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
