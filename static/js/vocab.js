/**
 * DUOHUB - Pillar 1: Vocabulary Controller
 */

let currentDayWords = [];

async function loadVocabData(day) {
  const container = document.getElementById("vocab-cards-grid");
  try {
    const res = await fetch(`/api/vocab?day=${day}`);
    const words = await res.json();
    currentDayWords = words;

    if (!words || words.length === 0) {
      container.innerHTML = `<div class="empty-state">No hay palabras cargadas para el Día ${day}. Puedes importar más con el script de PDF.</div>`;
      return;
    }

    container.innerHTML = words.map(w => `
      <div class="vocab-card">
        <div class="vocab-card-header">
          <div>
            <div class="vocab-word-title">${w.word}</div>
            <div class="vocab-ipa">${w.ipa || ''}</div>
          </div>
          <button class="btn-speak-word" onclick="speakEnglish('${escapeQuotes(w.word)}', 0.9)" title="Escuchar pronunciación nativa">
            🔊
          </button>
        </div>

        <div class="vocab-translation">${w.translation}</div>
        <div class="vocab-definition">${w.definition || ''}</div>

        <div class="vocab-example-box">
          <div class="vocab-example-en">"${w.example_en || ''}"</div>
          <div class="vocab-example-es">${w.example_es || ''}</div>
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error("Error loading vocab:", err);
    container.innerHTML = `<div class="error-state">Error al cargar vocabulario.</div>`;
  }
}

function escapeQuotes(str) {
  return (str || '').replace(/'/g, "\\'");
}

function checkVocabPractice() {
  const input = document.getElementById("vocab-practice-input");
  const feedback = document.getElementById("vocab-practice-feedback");
  const text = (input.value || "").trim().toLowerCase();

  if (!text) {
    feedback.textContent = "Por favor escribe una oración en inglés primero.";
    feedback.style.color = "var(--warning-amber)";
    return;
  }

  const detected = currentDayWords.filter(w => {
    const regex = new RegExp(`\\b${w.word.toLowerCase()}\\b`, 'i');
    return regex.test(text);
  });

  if (detected.length >= 2) {
    feedback.innerHTML = `🎉 <strong>¡Brillante!</strong> Has utilizado ${detected.length} palabras de hoy: <em>${detected.map(d => d.word).join(", ")}</em>. Excelente activación mental.`;
    feedback.style.color = "var(--success-emerald)";
  } else if (detected.length === 1) {
    feedback.innerHTML = `👍 Bien, detectamos <em>"${detected[0].word}"</em>. Intenta agregar una segunda palabra de la lista para completar el reto.`;
    feedback.style.color = "var(--warning-amber)";
  } else {
    feedback.innerHTML = `Intenta incluir alguna de las 5 palabras de hoy: ${currentDayWords.map(w => `<strong>${w.word}</strong>`).join(", ")}.`;
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
