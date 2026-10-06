/**
 * DUOHUB - Pillar 5: Speaking Challenge Controller
 */

let speakingTimerSeconds = 5 * 60; // 5 minutes default
let speakingTimerInterval = null;
let isSpeakingTimerRunning = false;

async function loadSpeakingData(day) {
  try {
    const res = await fetch(`/api/speaking?day=${day}`);
    const data = await res.json();

    document.getElementById("speaking-topic-name").textContent = data.topic || "General";
    document.getElementById("speaking-question").textContent = `"${data.prompt_question || ''}"`;
    document.getElementById("speaking-guidelines-content").textContent = data.suggested_guidelines || '';

    // Render Target Words Checklist
    const list = document.getElementById("speaking-target-words-list");
    if (data.target_words && data.target_words.length > 0) {
      list.innerHTML = data.target_words.map(w => `
        <div class="target-word-item" onclick="toggleTargetWordCheck(this)">
          <div>
            <span class="target-word-name">${w.word}</span>
            <span class="target-word-trans">(${w.translation})</span>
          </div>
          <span class="check-icon">○</span>
        </div>
      `).join("");
    } else {
      list.innerHTML = `<div class="empty-state">No hay palabras asignadas para hoy.</div>`;
    }

  } catch (err) {
    console.error("Error loading speaking prompt:", err);
  }
}

function toggleTargetWordCheck(elem) {
  elem.classList.toggle("checked");
  const icon = elem.querySelector(".check-icon");
  if (elem.classList.contains("checked")) {
    icon.textContent = "✓";
  } else {
    icon.textContent = "○";
  }
}

// 5-Minute Speaking Timer
function updateSpeakingTimerDisplay() {
  const m = Math.floor(speakingTimerSeconds / 60).toString().padStart(2, '0');
  const s = (speakingTimerSeconds % 60).toString().padStart(2, '0');
  document.getElementById("speaking-timer-display").textContent = `${m}:${s}`;
}

function toggleSpeakingTimer() {
  const btn = document.getElementById("btn-speaking-timer-toggle");
  if (isSpeakingTimerRunning) {
    clearInterval(speakingTimerInterval);
    isSpeakingTimerRunning = false;
    btn.textContent = "Reanudar";
  } else {
    isSpeakingTimerRunning = true;
    btn.textContent = "Pausar";
    speakingTimerInterval = setInterval(() => {
      if (speakingTimerSeconds > 0) {
        speakingTimerSeconds--;
        updateSpeakingTimerDisplay();
      } else {
        clearInterval(speakingTimerInterval);
        isSpeakingTimerRunning = false;
        btn.textContent = "5 Minutos Cumplidos";
        speakEnglish("Five minutes completed! Awesome speaking practice.", 1.0);
        alert("🎉 ¡Completaste los 5 minutos de speaking! Envía tu audio por WhatsApp a tu compañero.");
      }
    }, 1000);
  }
}

function resetSpeakingTimer() {
  clearInterval(speakingTimerInterval);
  isSpeakingTimerRunning = false;
  speakingTimerSeconds = 5 * 60;
  updateSpeakingTimerDisplay();
  document.getElementById("btn-speaking-timer-toggle").textContent = "Iniciar Temporizador";
}

async function markSpeakingDone() {
  // Collect checked target words
  const checkedWords = Array.from(document.querySelectorAll(".target-word-item.checked .target-word-name"))
    .map(el => el.textContent.trim());

  try {
    const res = await fetch("/api/speaking/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        date: state.currentDate,
        day: state.currentDay,
        notes: `Used words: ${checkedWords.join(", ")}`
      })
    });
    const data = await res.json();
    if (data.success) {
      speakEnglish("Speaking challenge marked as complete! Accountability pact fulfilled.", 1.0);
      fetchStatusAndRefresh();
    }
  } catch (err) {
    console.error("Error marking speaking done:", err);
  }
}
