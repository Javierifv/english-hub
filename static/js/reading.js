/**
 * DUOHUB - Pillar 2: Reading & Summary Evaluator Controller
 */

let timerSeconds = 15 * 60; // 15 minutes default
let timerInterval = null;
let isTimerRunning = false;

async function loadReadingData(day) {
  try {
    const res = await fetch(`/api/reading?day=${day}`);
    const reading = await res.json();

    if (reading.error) {
      document.getElementById("reading-title").textContent = "No hay lectura disponible para este día.";
      return;
    }

    document.getElementById("reading-title").textContent = reading.title;
    document.getElementById("reading-level").textContent = `${reading.level} Level`;
    document.getElementById("reading-topic").textContent = reading.topic;

    // Render content with interactive click-to-pronounce
    const contentBox = document.getElementById("reading-content");
    const paragraphs = reading.content.split("\n\n");
    contentBox.innerHTML = paragraphs.map(p => {
      const words = p.split(/\s+/).map(w => {
        const clean = w.replace(/[^a-zA-Z]/g, "");
        if (clean.length > 2) {
          return `<span class="interactive-word" onclick="speakEnglish('${escapeQuotes(clean)}', 0.9)" title="Clic para escuchar pronunciación">${w}</span>`;
        }
        return w;
      }).join(" ");
      return `<p style="margin-bottom: 1rem;">${words}</p>`;
    }).join("");

    // Render Key Vocabulary pills
    const keywordsBox = document.getElementById("reading-keywords");
    if (reading.key_vocabulary && Array.isArray(reading.key_vocabulary)) {
      keywordsBox.innerHTML = reading.key_vocabulary.map(kw => `
        <span class="keyword-pill" onclick="speakEnglish('${escapeQuotes(kw)}', 0.9)" title="Escuchar">${kw}</span>
      `).join("");
    } else {
      keywordsBox.innerHTML = `<span class="tag-title">Lectura general</span>`;
    }

    // Load existing summary if already written
    const summaryTextarea = document.getElementById("summary-textarea");
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
      document.getElementById("summary-evaluation-results").style.display = "none";
    }

  } catch (err) {
    console.error("Error loading reading:", err);
  }
}

// 15-Minute Countdown Timer
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
        speakEnglish("Fifteen minutes completed! Time to write your summary.", 1.0);
        alert("⏱️ ¡15 minutos cumplidos! Es hora de escribir tu resumen en inglés.");
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

// Summary Word Counter
document.addEventListener("DOMContentLoaded", () => {
  const textarea = document.getElementById("summary-textarea");
  if (textarea) {
    textarea.addEventListener("input", updateWordCount);
  }
});

function updateWordCount() {
  const textarea = document.getElementById("summary-textarea");
  const counter = document.getElementById("summary-word-count");
  if (!textarea || !counter) return;

  const text = textarea.value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  counter.textContent = `${words} palabras (Mínimo recomendado: 50)`;

  if (words >= 50) {
    counter.style.color = "var(--success-emerald)";
  } else {
    counter.style.color = "var(--text-dim)";
  }
}

// Submit Summary for Evaluation
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
    btn.textContent = "✨ Auditar y Evaluar Mi Resumen";
  }
}

function renderSummaryFeedback(f) {
  const container = document.getElementById("summary-evaluation-results");
  container.style.display = "block";

  const matchedHtml = f.matched_vocab && f.matched_vocab.length > 0
    ? `<span class="eval-pill eval-pill-vocab">🎯 Palabras del día usadas: ${f.matched_vocab.join(", ")} (+Bonus)</span>`
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
      <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: var(--radius-sm); padding: 0.65rem; margin-bottom: 0.85rem; font-size: 0.82rem; color: var(--success-emerald);">
        ✓ No se detectaron errores comunes de preposiciones ni concordancia básica. ¡Gran redacción!
      </div>
    `;
  }

  container.innerHTML = `
    <h4 style="margin-bottom: 0.75rem; color: #FFF;">Resultados de la Auditoría:</h4>
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
