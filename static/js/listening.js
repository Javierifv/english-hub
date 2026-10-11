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
    const listRes = await fetch(`/api/listening/list?level=${lvl}&user_id=${state.currentUser}`);
    listeningTracksList = await listRes.json();

    const select = document.getElementById("listening-track-select");
    if (select && listeningTracksList.length > 0) {
      // Clean display with completion checkmark
      select.innerHTML = listeningTracksList.map((t) => {
        const prefix = t.is_completed ? '✅ ' : '🎧 ';
        return `<option value="${t.id}">${prefix}${t.title}</option>`;
      }).join("");

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

async function refreshListeningTrackDropdown(keepClipId) {
  try {
    const lvl = state.listeningLevel || 'A1';
    const listRes = await fetch(`/api/listening/list?level=${lvl}&user_id=${state.currentUser}`);
    listeningTracksList = await listRes.json();
    const select = document.getElementById("listening-track-select");
    if (select && listeningTracksList.length > 0) {
      select.innerHTML = listeningTracksList.map((t) => {
        const prefix = t.is_completed ? '✅ ' : '🎧 ';
        return `<option value="${t.id}">${prefix}${t.title}</option>`;
      }).join("");
      if (keepClipId) select.value = keepClipId;
    }
  } catch (e) {}
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
    const res = await fetch(`/api/listening?id=${clipId}&user_id=${state.currentUser}`);
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

    // Update completion pill & status banner based on THIS clip's progress
    const compPill = document.getElementById("listening-completion-pill");
    const statusBanner = document.getElementById("listening-status-banner");
    const statusText = document.getElementById("listening-status-banner-text");
    const input = document.getElementById("listening-dictation-input");
    const diffResults = document.getElementById("listening-diff-results");

    if (clip.user_progress && clip.user_progress.is_completed) {
      const prog = clip.user_progress;
      if (compPill) compPill.style.display = "inline-block";
      if (statusBanner) {
        statusBanner.style.display = "flex";
        if (statusText) {
          const compDate = prog.date || 'Anterior';
          statusText.textContent = `Dictado completado (${prog.accuracy}% de coincidencia en ${prog.time_seconds}s) · ${compDate}`;
        }
      }
      if (input) input.value = prog.user_text || "";
      listeningStopwatchSeconds = prog.time_seconds || 0;
      updateStopwatchDisplay();
      updateStopwatchStatus("paused");

      // Render saved diff results and AI audit without re-calling API!
      renderDiffResults(prog.accuracy, prog.diff_tokens, clip.transcript, prog.time_seconds, prog.ai_audit, prog.user_text);
    } else {
      // Uncompleted clip: clean empty state
      if (compPill) compPill.style.display = "none";
      if (statusBanner) statusBanner.style.display = "none";
      if (input) input.value = "";
      resetListeningStopwatch();
      if (diffResults) diffResults.style.display = "none";
    }

    if (typeof applyReadOnlyLocks === "function") {
      applyReadOnlyLocks(state.isReadOnly);
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

function listeningRewind(seconds = 5) {
  const audioElem = document.getElementById("listening-html5-audio");
  if (audioElem && audioElem.src) {
    audioElem.currentTime = Math.max(0, audioElem.currentTime - seconds);
    const slider = document.getElementById("listening-audio-slider");
    if (slider) slider.value = audioElem.currentTime;
    const curTime = document.getElementById("listening-time-current");
    if (curTime) curTime.textContent = formatAudioTime(audioElem.currentTime);
  }
}

function listeningForward(seconds = 5) {
  const audioElem = document.getElementById("listening-html5-audio");
  if (audioElem && audioElem.src) {
    audioElem.currentTime = Math.min(audioElem.duration || 999, audioElem.currentTime + seconds);
    const slider = document.getElementById("listening-audio-slider");
    if (slider) slider.value = audioElem.currentTime;
    const curTime = document.getElementById("listening-time-current");
    if (curTime) curTime.textContent = formatAudioTime(audioElem.currentTime);
  }
}

// Visual Diff Calculation & Verification
async function verifyListeningDiff(isSilent = false) {
  if (typeof isReadOnlyMode === 'function' && isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
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
    btn.textContent = "Comparando y auditando con IA...";
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
      const compPill = document.getElementById("listening-completion-pill");
      const statusBanner = document.getElementById("listening-status-banner");
      const statusText = document.getElementById("listening-status-banner-text");
      if (compPill) compPill.style.display = "inline-block";
      if (statusBanner) {
        statusBanner.style.display = "flex";
        if (statusText) statusText.textContent = `Dictado completado (${data.accuracy}% de coincidencia en ${data.time_seconds || listeningStopwatchSeconds}s)`;
      }

      renderDiffResults(data.accuracy, data.diff_tokens, data.real_text, data.time_seconds || listeningStopwatchSeconds, data.ai_audit, userText);
      if (!isSilent) {
        speakEnglish(`Accuracy: ${data.accuracy} percent`, 1.0);
      }
      fetchStatusAndRefresh();
      await refreshListeningTrackDropdown(currentListeningClip ? currentListeningClip.id : null);
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

let lastUserTypedText = "";

function toggleUserTypedText() {
  const box = document.getElementById("user-typed-box");
  const btn = document.getElementById("btn-toggle-user-typed");
  if (!box) return;
  if (box.style.display === "none") {
    box.style.display = "block";
    if (btn) btn.textContent = "🙈 Ocultar lo que escribiste";
  } else {
    box.style.display = "none";
    if (btn) btn.textContent = "👁️ Ver lo que escribiste";
  }
}

function renderDiffResults(accuracy, diffTokens, realText, timeSeconds = 0, aiAudit = null, userTypedText = "") {
  const container = document.getElementById("listening-diff-results");
  if (!container) return;
  container.style.display = "block";
  container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // 1. Métricas: Tiempo y Coincidencia
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

  // 2. Transcripción Original Oficial Completa (Limpia y legible)
  const realBox = document.getElementById("original-transcript-box");
  if (realBox) {
    const formatted = escapeHtml(realText).replace(/\n/g, '<br>');
    realBox.innerHTML = `<div style="font-size: 0.98rem; line-height: 1.8; color: var(--text-main); font-weight: 500;">${formatted}</div>`;
  }

  // Texto que escribió el usuario (toggle limpio)
  lastUserTypedText = userTypedText || (document.getElementById("listening-dictation-input")?.value || "");
  const userBox = document.getElementById("user-typed-box");
  if (userBox) {
    userBox.textContent = lastUserTypedText;
    userBox.style.display = "none";
  }
  const btnToggleTyped = document.getElementById("btn-toggle-user-typed");
  if (btnToggleTyped) btnToggleTyped.textContent = "👁️ Ver lo que escribiste";

  // 3. Palabras y Frases Faltantes Clave
  const missingSection = document.getElementById("listening-missing-words-section");
  const missingList = document.getElementById("listening-missing-words-list");
  if (missingSection && missingList) {
    if (aiAudit && Array.isArray(aiAudit.missing_words) && aiAudit.missing_words.length > 0) {
      missingSection.style.display = "block";
      missingList.innerHTML = aiAudit.missing_words.map(item => `
        <div class="missing-word-card">
          <div class="missing-word-target">
            <span>🟡 "${escapeHtml(item.word_or_phrase || '')}"</span>
            <button type="button" class="btn btn-xs btn-ghost" onclick="speakEnglish('${escapeQuotes(item.word_or_phrase || '')}', 0.85)" title="Escuchar pronunciación">🔊</button>
          </div>
          <div class="missing-word-context">${escapeHtml(item.context || '')}</div>
        </div>
      `).join('');
    } else {
      missingSection.style.display = "none";
    }
  }

  // 4. Confusiones Fonéticas & Enlace Británico (Palabras que escribiste mal)
  const phoneticSection = document.getElementById("listening-phonetic-section");
  const phoneticGrid = document.getElementById("listening-phonetic-grid");
  if (phoneticSection && phoneticGrid) {
    if (aiAudit && Array.isArray(aiAudit.phonetic_confusion) && aiAudit.phonetic_confusion.length > 0) {
      phoneticSection.style.display = "block";
      phoneticGrid.innerHTML = aiAudit.phonetic_confusion.map(item => `
        <div class="confusion-chip">
          <div class="chip-header">
            <span>❌ "${escapeHtml(item.heard || '')}"</span>
            <span>👉 ✅ "${escapeHtml(item.spoken || '')}"</span>
          </div>
          <div class="chip-desc">${escapeHtml(item.explanation || '')}</div>
        </div>
      `).join('');
    } else {
      phoneticSection.style.display = "none";
    }
  }

  // 5. Elementos Gramaticales u Omisiones Clave
  const grammarSection = document.getElementById("listening-grammar-section");
  const grammarList = document.getElementById("listening-grammar-list");
  if (grammarSection && grammarList) {
    if (aiAudit && Array.isArray(aiAudit.missed_elements) && aiAudit.missed_elements.length > 0) {
      grammarSection.style.display = "block";
      grammarList.innerHTML = aiAudit.missed_elements.map(m => `<li>${escapeHtml(m)}</li>`).join('');
    } else {
      grammarSection.style.display = "none";
    }
  }

  // 6. Conclusión del Evaluador & Consejos (Al Final)
  const aiSection = document.getElementById("listening-ai-audit-section");
  const aiVerdict = document.getElementById("listening-ai-verdict");
  const aiCoaching = document.getElementById("listening-ai-coaching");
  const aiSourceTag = document.getElementById("listening-ai-source-tag");

  if (aiSection && aiAudit) {
    aiSection.style.display = "block";
    if (aiSourceTag) aiSourceTag.textContent = aiAudit.source || "Auditoría IA";
    if (aiVerdict) aiVerdict.textContent = aiAudit.overall_verdict || "";
    if (aiCoaching) {
      if (aiAudit.coaching_tip) {
        aiCoaching.style.display = "block";
        aiCoaching.innerHTML = `<strong>🎯 Consejo para Entrenar el Oído:</strong> ${escapeHtml(aiAudit.coaching_tip)}`;
      } else {
        aiCoaching.style.display = "none";
      }
    }
  } else if (aiSection) {
    aiSection.style.display = "none";
  }
}

// Function aliases for compatibility
window.verifyListeningDiff = verifyListeningDiff;
window.verifyDictationDiff = verifyListeningDiff;
window.toggleUserTypedText = toggleUserTypedText;
window.onListeningSliderSeek = onListeningSliderSeek;
window.listeningRewind = listeningRewind;
window.listeningForward = listeningForward;
window.toggleListeningStopwatch = toggleListeningStopwatch;
window.resetListeningStopwatch = resetListeningStopwatch;
window.onListeningInputChange = onListeningInputChange;
