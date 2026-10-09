/**
 * DUOHUB - Pillar 3: Listening & Dictation Diff Controller
 * Supports CEFR Levels (A1 to C1), British Council Transcripts & HD Neural Audio
 * Features: Audio Seek Scrubber, Live Dictation Stopwatch, Word Diff Verification
 */

let currentListeningClip = null;
let listeningTracksList = [];
let currentTrackIndex = 0;
let isAudioPlaying = false;
let listeningSpeed = 1.0;

// Stopwatch State
let listeningStopwatchSeconds = 0;
let listeningStopwatchInterval = null;
let isListeningStopwatchRunning = false;

function formatAudioTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "00:00";
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function startListeningStopwatch() {
  if (isListeningStopwatchRunning) return;
  isListeningStopwatchRunning = true;
  updateStopwatchStatus("running");
  listeningStopwatchInterval = setInterval(() => {
    listeningStopwatchSeconds++;
    updateStopwatchDisplay();
  }, 1000);
}

function pauseListeningStopwatch() {
  if (!isListeningStopwatchRunning) return;
  isListeningStopwatchRunning = false;
  clearInterval(listeningStopwatchInterval);
  updateStopwatchStatus("paused");
}

function toggleListeningStopwatch() {
  if (isListeningStopwatchRunning) {
    pauseListeningStopwatch();
  } else {
    startListeningStopwatch();
  }
}

function resetListeningStopwatch() {
  pauseListeningStopwatch();
  listeningStopwatchSeconds = 0;
  updateStopwatchDisplay();
  updateStopwatchStatus("idle");
}

function updateStopwatchDisplay() {
  const el = document.getElementById("listening-stopwatch-display");
  if (el) el.textContent = formatAudioTime(listeningStopwatchSeconds);
}

function updateStopwatchStatus(status) {
  const badge = document.getElementById("listening-stopwatch-badge");
  const toggleBtn = document.getElementById("btn-stopwatch-toggle");
  if (!badge) return;
  badge.className = "stopwatch-badge";
  if (status === "running") {
    badge.classList.add("badge-running");
    badge.textContent = "🟢 En curso";
    if (toggleBtn) toggleBtn.textContent = "⏸ Pausar";
  } else if (status === "paused") {
    badge.classList.add("badge-paused");
    badge.textContent = "⏸ Pausado";
    if (toggleBtn) toggleBtn.textContent = "▶ Reanudar";
  } else {
    badge.classList.add("badge-idle");
    badge.textContent = "Listo para iniciar";
    if (toggleBtn) toggleBtn.textContent = "▶ Iniciar";
  }
}

function onListeningInputChange() {
  if (!isListeningStopwatchRunning && listeningStopwatchSeconds === 0) {
    startListeningStopwatch();
  }
}

function onListeningSliderSeek(val) {
  const audioElem = document.getElementById("listening-html5-audio");
  if (audioElem && audioElem.src) {
    audioElem.currentTime = parseFloat(val);
    const curTime = document.getElementById("listening-time-current");
    if (curTime) curTime.textContent = formatAudioTime(parseFloat(val));
  }
}

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
    'B1': 'listening-level-btn-b1',
    'B2': 'listening-level-btn-b2',
    'C1': 'listening-level-btn-c1',
    'all': 'listening-level-btn-all'
  };

  const activeBtn = document.getElementById(btnMap[lvl] || 'listening-level-btn-all');
  if (activeBtn) activeBtn.classList.add("active");

  try {
    const listRes = await fetch(`/api/listening/list?level=${lvl}`);
    listeningTracksList = await listRes.json();

    const select = document.getElementById("listening-track-select");
    if (select && listeningTracksList.length > 0) {
      // Clean display without level brackets or extra noise, allowing full title display
      select.innerHTML = listeningTracksList.map((t) => `
        <option value="${t.id}">${t.title}</option>
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

    // Configure HTML5 Audio Player & Scrubber Slider
    const audioElem = document.getElementById("listening-html5-audio");
    const slider = document.getElementById("listening-audio-slider");
    const curTime = document.getElementById("listening-time-current");
    const totTime = document.getElementById("listening-time-total");

    if (slider) {
      slider.value = 0;
      slider.max = clip.duration_seconds || 100;
    }
    if (curTime) curTime.textContent = "00:00";
    if (totTime) totTime.textContent = formatAudioTime(clip.duration_seconds || 0);

    if (audioElem) {
      audioElem.pause();
      isAudioPlaying = false;
      document.getElementById("btn-play-listening").textContent = "▶ Reproducir";

      if (clip.audio_url) {
        audioElem.src = clip.audio_url;
        audioElem.playbackRate = listeningSpeed;

        audioElem.onloadedmetadata = () => {
          if (slider && audioElem.duration) slider.max = audioElem.duration;
          if (totTime && audioElem.duration) totTime.textContent = formatAudioTime(audioElem.duration);
        };

        audioElem.ontimeupdate = () => {
          if (slider && !slider.matches(':active')) {
            slider.value = audioElem.currentTime;
          }
          if (curTime) curTime.textContent = formatAudioTime(audioElem.currentTime);
        };

        audioElem.onended = () => {
          isAudioPlaying = false;
          document.getElementById("btn-play-listening").textContent = "▶ Reproducir";
          if (slider) slider.value = slider.max;
        };

        audioElem.onerror = () => {
          console.warn("HTML5 audio playback error; fallback to SpeechSynthesis enabled.");
        };
      } else {
        audioElem.src = "";
      }
    }

    // Set existing attempt & time if already done
    const input = document.getElementById("listening-dictation-input");
    if (state.todayLog && state.todayLog.listening_attempt) {
      input.value = state.todayLog.listening_attempt;
      if (state.todayLog.listening_time_seconds) {
        listeningStopwatchSeconds = state.todayLog.listening_time_seconds;
        updateStopwatchDisplay();
        updateStopwatchStatus("paused");
      }
    } else {
      input.value = "";
      resetListeningStopwatch();
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

  // Auto-start stopwatch when user starts listening
  startListeningStopwatch();

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

  // Pause stopwatch upon verification
  pauseListeningStopwatch();

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
        user_text: userText,
        time_seconds: listeningStopwatchSeconds
      })
    });
    const data = await res.json();

    if (data.success) {
      renderDiffResults(data.accuracy, data.diff_tokens, data.real_text, data.time_seconds || listeningStopwatchSeconds, data.ai_audit);
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

function renderDiffResults(accuracy, diffTokens, realText, timeSeconds = 0, aiAudit = null) {
  const container = document.getElementById("listening-diff-results");
  if (!container) return;
  container.style.display = "block";

  const timePill = document.getElementById("listening-time-spent-pill");
  if (timePill) {
    const totalSecs = timeSeconds || listeningStopwatchSeconds;
    const m = Math.floor(totalSecs / 60);
    const s = totalSecs % 60;
    timePill.textContent = `⏱️ ${m > 0 ? m + 'm ' : ''}${s}s`;
    timePill.style.display = "inline-block";
  }

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

  // AI Listening Audit Report Section
  const auditSection = document.getElementById("listening-ai-audit-section");
  if (auditSection) {
    if (aiAudit) {
      auditSection.style.display = "block";
      let confusionHtml = "";
      if (aiAudit.phonetic_confusion && aiAudit.phonetic_confusion.length > 0) {
        confusionHtml = `
          <div class="audit-section-subtitle">👂 Confusiones Fonéticas & Enlace Británico:</div>
          <div class="confusion-grid">
            ${aiAudit.phonetic_confusion.map(item => `
              <div class="confusion-chip">
                <div class="chip-header">
                  <span>❌ "${escapeHtml(item.heard || '')}"</span>
                  <span>👉 ✅ "${escapeHtml(item.spoken || '')}"</span>
                </div>
                <div class="chip-desc">${escapeHtml(item.explanation || '')}</div>
              </div>
            `).join('')}
          </div>
        `;
      }

      let missedHtml = "";
      if (aiAudit.missed_elements && aiAudit.missed_elements.length > 0) {
        missedHtml = `
          <div class="audit-section-subtitle">🔍 Elementos Gramaticales u Omisiones Clave:</div>
          <ul class="audit-missed-list">
            ${aiAudit.missed_elements.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
          </ul>
        `;
      }

      let coachingHtml = "";
      if (aiAudit.coaching_tip) {
        coachingHtml = `
          <div class="audit-coaching-box">
            <strong>🎯 Consejo para Entrenar el Oído:</strong> ${escapeHtml(aiAudit.coaching_tip)}
          </div>
        `;
      }

      auditSection.innerHTML = `
        <div class="audit-header">
          <div class="audit-title">⚡ Auditoría IA de Comprensión Auditiva</div>
          <span class="audit-source-tag">${escapeHtml(aiAudit.source || 'Auditoría IA')}</span>
        </div>
        <p class="audit-verdict-p">${escapeHtml(aiAudit.overall_verdict || '')}</p>
        ${confusionHtml}
        ${missedHtml}
        ${coachingHtml}
      `;
    } else {
      auditSection.style.display = "none";
    }
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
window.onListeningSliderSeek = onListeningSliderSeek;
window.toggleListeningStopwatch = toggleListeningStopwatch;
window.resetListeningStopwatch = resetListeningStopwatch;
window.onListeningInputChange = onListeningInputChange;
