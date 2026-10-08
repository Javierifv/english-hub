/**
 * DUOHUB - Pillar 3: Listening & Dictation Diff Controller
 * Supports CEFR Levels (A1 for Javier, A2 for Partner), British Council Transcripts & HD Neural Audio
 */

let currentListeningClip = null;
let listeningTracksList = [];
let currentTrackIndex = 0;
let isAudioPlaying = false;
let listeningSpeed = 1.0;

async function loadListeningData(day) {
  const savedLevel = localStorage.getItem('duohub_listening_lvl_u' + state.currentUser) || state.listeningLevel || 'A1';
  await selectListeningLevel(savedLevel, false);
}

async function selectListeningLevel(lvl, loadFirst = true) {
  state.listeningLevel = lvl;
  state.listeningLevelSetByUser = true;
  localStorage.setItem('duohub_listening_lvl_u' + state.currentUser, lvl);

  // Update level buttons in toolbar
  document.querySelectorAll(".listening-toolbar .level-pill-btn").forEach(btn => {
    btn.classList.remove("active");
  });

  const btnMap = {
    'A1': 'listening-level-btn-a1',
    'A2': 'listening-level-btn-a2',
    'all': 'listening-level-btn-all'
  };

  const activeBtn = document.getElementById(btnMap[lvl] || 'listening-level-btn-all');
  if (activeBtn) activeBtn.classList.add("active");

  try {
    const listRes = await fetch(`/api/listening/list?level=${lvl}`);
    listeningTracksList = await listRes.json();

    const select = document.getElementById("listening-track-select");
    if (select && listeningTracksList.length > 0) {
      select.innerHTML = listeningTracksList.map((t) => `
        <option value="${t.id}">[${t.level}] ${t.title} (~${t.duration_seconds}s)</option>
      `).join("");

      // Check if user had a saved track
      const savedTrackId = parseInt(localStorage.getItem('duohub_listening_id_u' + state.currentUser));
      const foundIdx = listeningTracksList.findIndex(t => t.id === savedTrackId);

      if (foundIdx !== -1) {
        currentTrackIndex = foundIdx;
        select.value = savedTrackId;
      } else {
        currentTrackIndex = 0;
        select.value = listeningTracksList[0].id;
      }

      await loadListeningById(select.value);
    }
  } catch (err) {
    console.error("Error loading listening track list:", err);
  }
}

async function navListeningTrack(delta) {
  if (!listeningTracksList || listeningTracksList.length === 0) return;
  const newIdx = currentTrackIndex + delta;
  if (newIdx >= 0 && newIdx < listeningTracksList.length) {
    currentTrackIndex = newIdx;
    const select = document.getElementById("listening-track-select");
    if (select) select.value = listeningTracksList[currentTrackIndex].id;
    localStorage.setItem('duohub_listening_id_u' + state.currentUser, listeningTracksList[currentTrackIndex].id);
    await loadListeningById(listeningTracksList[currentTrackIndex].id);
  }
}

async function onListeningTrackDropdownChange(clipId) {
  const idx = listeningTracksList.findIndex(t => t.id === parseInt(clipId));
  if (idx !== -1) {
    currentTrackIndex = idx;
    localStorage.setItem('duohub_listening_id_u' + state.currentUser, clipId);
    await loadListeningById(clipId);
  }
}

async function loadListeningById(clipId) {
  try {
    const res = await fetch(`/api/listening?id=${clipId}`);
    const clip = await res.json();
    currentListeningClip = clip;

    if (clip.error) {
      document.getElementById("listening-title").textContent = "Clip no disponible";
      return;
    }

    document.getElementById("listening-title").textContent = clip.title;
    document.getElementById("listening-level").textContent = `${clip.level} Level`;

    // Configure HTML5 Audio Player
    const audioElem = document.getElementById("listening-html5-audio");
    if (audioElem) {
      audioElem.pause();
      isAudioPlaying = false;
      document.getElementById("btn-play-listening").textContent = "▶ Reproducir";

      if (clip.audio_url) {
        audioElem.src = clip.audio_url;
        audioElem.playbackRate = listeningSpeed;

        audioElem.onended = () => {
          isAudioPlaying = false;
          document.getElementById("btn-play-listening").textContent = "▶ Reproducir";
        };

        audioElem.onerror = () => {
          console.warn("HTML5 audio playback error; fallback to SpeechSynthesis enabled.");
        };
      } else {
        audioElem.src = "";
      }
    }

    // Set existing attempt if already done
    const input = document.getElementById("listening-dictation-input");
    if (state.todayLog && state.todayLog.listening_attempt) {
      input.value = state.todayLog.listening_attempt;
    } else {
      input.value = "";
      const diffResults = document.getElementById("listening-diff-results");
      if (diffResults) diffResults.style.display = "none";
    }

  } catch (err) {
    console.error("Error loading listening clip:", err);
  }
}

function togglePlayListening() {
  if (!currentListeningClip) return;
  const audioElem = document.getElementById("listening-html5-audio");
  const playBtn = document.getElementById("btn-play-listening");

  // Prefer HTML5 Audio Player (Local MP3 generated by Edge Neural Voices)
  if (audioElem && audioElem.src && audioElem.src.includes(".mp3")) {
    if (isAudioPlaying) {
      audioElem.pause();
      isAudioPlaying = false;
      playBtn.textContent = "▶ Reproducir";
    } else {
      audioElem.playbackRate = listeningSpeed;
      audioElem.play().then(() => {
        isAudioPlaying = true;
        playBtn.textContent = "⏸ Pausar";
      }).catch(err => {
        console.warn("Could not autoplay HTML5 audio; using speech synthesis fallback:", err);
        fallbackSpeechSynthesis();
      });
    }
    return;
  }

  // Fallback to Web Speech API
  fallbackSpeechSynthesis();
}

function fallbackSpeechSynthesis() {
  if (!currentListeningClip || !currentListeningClip.transcript) return;
  const playBtn = document.getElementById("btn-play-listening");

  if (isAudioPlaying) {
    window.speechSynthesis.cancel();
    isAudioPlaying = false;
    playBtn.textContent = "▶ Reproducir";
  } else {
    isAudioPlaying = true;
    playBtn.textContent = "⏸ Pausar";

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(currentListeningClip.transcript);
    utterance.lang = 'en-US';
    utterance.rate = listeningSpeed;
    const voice = getEnglishVoice();
    if (voice) utterance.voice = voice;

    utterance.onend = () => {
      isAudioPlaying = false;
      playBtn.textContent = "▶ Reproducir";
    };
    utterance.onerror = () => {
      isAudioPlaying = false;
      playBtn.textContent = "▶ Reproducir";
    };

    window.speechSynthesis.speak(utterance);
  }
}

function changeListeningSpeed(val) {
  listeningSpeed = parseFloat(val);
  const audioElem = document.getElementById("listening-html5-audio");
  if (audioElem) {
    audioElem.playbackRate = listeningSpeed;
  }
  if (isAudioPlaying && (!audioElem || !audioElem.src || !audioElem.src.includes(".mp3"))) {
    fallbackSpeechSynthesis();
    fallbackSpeechSynthesis();
  }
}

function listeningRewind(seconds) {
  const audioElem = document.getElementById("listening-html5-audio");
  if (audioElem && audioElem.src && audioElem.src.includes(".mp3")) {
    audioElem.currentTime = Math.max(0, audioElem.currentTime - seconds);
  } else {
    togglePlayListening();
  }
}

function listeningForward(seconds) {
  const audioElem = document.getElementById("listening-html5-audio");
  if (audioElem && audioElem.src && audioElem.src.includes(".mp3")) {
    audioElem.currentTime = Math.min(audioElem.duration || 999, audioElem.currentTime + seconds);
  }
}

// Visual Diff Calculation & Verification
async function verifyListeningDiff(isSilent = false) {
  const input = document.getElementById("listening-dictation-input");
  const userText = (input?.value || "").trim();

  if (!userText) {
    if (!isSilent) alert("Por favor escribe en el cuadro lo que escuchaste antes de comparar.");
    return;
  }

  if (!currentListeningClip) {
    if (!isSilent) alert("Clip de audio no cargado.");
    return;
  }

  const btn = document.getElementById("btn-verify-listening");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Comparando...";
  }

  try {
    const res = await fetch("/api/listening/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        date: state.currentDate,
        day: state.currentDay,
        clip_id: currentListeningClip.id,
        user_text: userText
      })
    });
    const data = await res.json();

    if (data.success) {
      renderDiffResults(data.accuracy, data.diff_tokens, data.real_text);
      if (!isSilent) {
        speakEnglish(`Accuracy: ${data.accuracy} percent`, 1.0);
      }
      fetchStatusAndRefresh();
    } else if (!isSilent) {
      alert(data.error || "No se pudo realizar la comparación.");
    }
  } catch (err) {
    console.error("Error verifying listening transcription:", err);
    if (!isSilent) {
      alert("Error al conectar con el servidor para la comparación.");
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "🔍 Comparar con Transcripción Original";
    }
  }
}

function renderDiffResults(accuracy, diffTokens, realText) {
  const container = document.getElementById("listening-diff-results");
  if (!container) return;
  container.style.display = "block";

  const pill = document.getElementById("listening-accuracy-pill");
  if (pill) {
    pill.textContent = `${accuracy}% Coincidencia`;
    if (accuracy >= 80) {
      pill.style.background = "rgba(0, 196, 140, 0.2)";
      pill.style.color = "var(--busuu-emerald)";
      pill.style.borderColor = "var(--busuu-emerald)";
    } else if (accuracy >= 50) {
      pill.style.background = "rgba(255, 176, 32, 0.2)";
      pill.style.color = "var(--busuu-amber)";
      pill.style.borderColor = "var(--busuu-amber)";
    } else {
      pill.style.background = "rgba(255, 90, 95, 0.2)";
      pill.style.color = "var(--busuu-coral)";
      pill.style.borderColor = "var(--busuu-coral)";
    }
  }

  // Word-by-word diff display using proper CSS classes
  const streamBox = document.getElementById("diff-tokens-display");
  if (streamBox && Array.isArray(diffTokens)) {
    streamBox.innerHTML = diffTokens.map(tok => {
      if (tok.type === "correct") {
        return `<span class="diff-word-correct">${escapeHtml(tok.word)}</span>`;
      } else if (tok.type === "missed") {
        return `<span class="diff-word-missed" title="Omitida">[+${escapeHtml(tok.word)}]</span>`;
      } else if (tok.type === "extra") {
        return `<span class="diff-word-extra" title="Palabra extra"><s>${escapeHtml(tok.word)}</s></span>`;
      } else if (tok.type === "wrong") {
        return `<span class="diff-word-wrong" title="Esperaba: ${escapeHtml(tok.expected)}"><s>${escapeHtml(tok.got)}</s> <small>(${escapeHtml(tok.expected)})</small></span>`;
      }
      return "";
    }).join(" ");
  }

  // Real full transcript display
  const realBox = document.getElementById("original-transcript-box");
  if (realBox) {
    realBox.style.display = "block";
    const formatted = escapeHtml(realText).replace(/\n/g, '<br>');
    realBox.innerHTML = `<div style="font-size: 0.95rem; line-height: 1.8; color: var(--text-main); font-weight: 500;">${formatted}</div>`;
  }

  const toggleBtn = document.getElementById("btn-toggle-transcript");
  if (toggleBtn) {
    toggleBtn.textContent = "🙈 Ocultar Transcripción";
  }
}

function toggleOriginalTranscript() {
  const box = document.getElementById("original-transcript-box");
  const btn = document.getElementById("btn-toggle-transcript");
  if (!box) return;
  if (box.style.display === "none") {
    box.style.display = "block";
    if (btn) btn.textContent = "🙈 Ocultar Transcripción";
  } else {
    box.style.display = "none";
    if (btn) btn.textContent = "👁️ Mostrar Transcripción";
  }
}

// Function aliases for compatibility
window.verifyListeningDiff = verifyListeningDiff;
window.verifyDictationDiff = verifyListeningDiff;
window.toggleOriginalTranscript = toggleOriginalTranscript;
window.toggleFullTranscript = toggleOriginalTranscript;
