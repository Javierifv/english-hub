/**
 * DUOHUB - Pillar 3: Listening & Dictation Diff Controller
 */

let currentListeningClip = null;
let isAudioPlaying = false;
let listeningSpeed = 1.0;

async function loadListeningData(day) {
  try {
    const res = await fetch(`/api/listening?day=${day}`);
    const clip = await res.json();
    currentListeningClip = clip;

    if (clip.error) {
      document.getElementById("listening-title").textContent = "Clip no disponible";
      return;
    }

    document.getElementById("listening-title").textContent = clip.title;
    document.getElementById("listening-level").textContent = `${clip.level} Level`;

    // Reset player state
    isAudioPlaying = false;
    document.getElementById("btn-play-listening").textContent = "▶ Reproducir";

    // Set existing attempt if already done
    const input = document.getElementById("listening-dictation-input");
    if (state.todayLog && state.todayLog.listening_attempt) {
      input.value = state.todayLog.listening_attempt;
      if (state.todayLog.listening_accuracy) {
        verifyDictationDiff(); // render existing diff
      }
    } else {
      input.value = "";
      document.getElementById("listening-diff-results").style.display = "none";
    }

  } catch (err) {
    console.error("Error loading listening clip:", err);
  }
}

function togglePlayListening() {
  if (!currentListeningClip || !currentListeningClip.transcript) return;

  if (isAudioPlaying) {
    window.speechSynthesis.cancel();
    isAudioPlaying = false;
    document.getElementById("btn-play-listening").textContent = "▶ Reproducir";
  } else {
    isAudioPlaying = true;
    document.getElementById("btn-play-listening").textContent = "⏸ Pausar";

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(currentListeningClip.transcript);
    utterance.lang = 'en-US';
    utterance.rate = listeningSpeed;
    const voice = getEnglishVoice();
    if (voice) utterance.voice = voice;

    utterance.onend = () => {
      isAudioPlaying = false;
      document.getElementById("btn-play-listening").textContent = "▶ Reproducir";
    };

    utterance.onerror = () => {
      isAudioPlaying = false;
      document.getElementById("btn-play-listening").textContent = "▶ Reproducir";
    };

    window.speechSynthesis.speak(utterance);
  }
}

function changeListeningSpeed(val) {
  listeningSpeed = parseFloat(val);
  if (isAudioPlaying) {
    togglePlayListening(); // pause
    togglePlayListening(); // resume with new speed
  }
}

function listeningRewind(seconds) {
  // Re-trigger from beginning or replay current phrase
  if (isAudioPlaying) {
    window.speechSynthesis.cancel();
    isAudioPlaying = false;
  }
  togglePlayListening();
}

function listeningForward(seconds) {
  // Skip
  if (isAudioPlaying) {
    window.speechSynthesis.cancel();
    isAudioPlaying = false;
    document.getElementById("btn-play-listening").textContent = "▶ Reproducir";
  }
}

async function verifyDictationDiff() {
  const input = document.getElementById("listening-dictation-input");
  const userText = (input.value || "").trim();

  if (!userText) {
    alert("Por favor escribe tu transcripción del audio antes de comparar.");
    return;
  }

  try {
    const res = await fetch("/api/listening/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        day: state.currentDay,
        user_text: userText
      })
    });
    const data = await res.json();

    if (data.success) {
      renderDiffResults(data.accuracy, data.diff_tokens, data.real_text);
      fetchStatusAndRefresh();
    }
  } catch (err) {
    console.error("Error verifying dictation:", err);
  }
}

function renderDiffResults(accuracy, tokens, realText) {
  const container = document.getElementById("listening-diff-results");
  container.style.display = "block";

  const accPill = document.getElementById("listening-accuracy-pill");
  accPill.textContent = `${accuracy}% Exactitud`;
  if (accuracy >= 80) {
    accPill.style.color = "var(--success-emerald)";
  } else if (accuracy >= 50) {
    accPill.style.color = "var(--warning-amber)";
  } else {
    accPill.style.color = "var(--danger-rose)";
  }

  const stream = document.getElementById("diff-tokens-display");
  stream.innerHTML = tokens.map(t => {
    if (t.type === "correct") {
      return `<span class="diff-word-correct">${t.word}</span>`;
    } else if (t.type === "missed") {
      return `<span class="diff-word-missed" title="Omitiste esta palabra: '${t.word}'">[+ ${t.word}]</span>`;
    } else if (t.type === "wrong") {
      return `<span class="diff-word-wrong" title="Esperado: '${t.expected}'">${t.got}</span>`;
    } else if (t.type === "extra") {
      return `<span class="diff-word-extra" title="Palabra extra no presente en el audio">${t.word}</span>`;
    }
    return t.word;
  }).join(" ");

  // Populate original transcript
  const origBox = document.getElementById("original-transcript-box");
  origBox.textContent = realText;
}

function toggleOriginalTranscript() {
  const box = document.getElementById("original-transcript-box");
  box.style.display = (box.style.display === "none") ? "block" : "none";
}
