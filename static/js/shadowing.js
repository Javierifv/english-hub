/**
 * DUOHUB - Pillar 4: Shadowing Studio Controller
 * Links directly to the active Listening audio track and complete transcript.
 * Enables simultaneous listening & speech recording for authentic shadowing technique.
 * Features: Pure Audition Mode (collapsible transcript), Master Audio Scrubber, Live Mic VU Meter.
 */

let shadowingTracksList = [];
let currentShadowingTrackIndex = 0;
let currentShadowingClip = null;
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let recordStartTime = 0;
let recordTimerInterval = null;
let isShadowingModelPlaying = false;
let shadowingPlaybackSpeed = 1.0;
let shadowingModelVolume = 1.0;

// Mic Live Audio Analysis
let micAudioCtx = null;
let micAnalyser = null;
let micAnimFrame = null;

function formatShadowingTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "00:00";
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function shadowingRewind(seconds) {
  const masterAudio = document.getElementById("shadowing-master-audio");
  if (masterAudio) {
    masterAudio.currentTime = Math.max(0, masterAudio.currentTime - (seconds || 5));
    const slider = document.getElementById("shadowing-audio-slider");
    if (slider) slider.value = masterAudio.currentTime;
    const curTime = document.getElementById("shadowing-time-current");
    if (curTime) curTime.textContent = formatShadowingTime(masterAudio.currentTime);
  }
}

function shadowingForward(seconds) {
  const masterAudio = document.getElementById("shadowing-master-audio");
  if (masterAudio) {
    masterAudio.currentTime = Math.min(masterAudio.duration || 9999, masterAudio.currentTime + (seconds || 5));
    const slider = document.getElementById("shadowing-audio-slider");
    if (slider) slider.value = masterAudio.currentTime;
    const curTime = document.getElementById("shadowing-time-current");
    if (curTime) curTime.textContent = formatShadowingTime(masterAudio.currentTime);
  }
}

function updateShadowingLevelPills(lvl) {
  const btnMap = {
    'A1': 'shadowing-level-btn-a1',
    'A2': 'shadowing-level-btn-a2',
    'B1': 'shadowing-level-btn-b1',
    'B2': 'shadowing-level-btn-b2',
    'C1': 'shadowing-level-btn-c1',
    'all': 'shadowing-level-btn-all'
  };
  document.querySelectorAll("[id^='shadowing-level-btn-']").forEach(b => b.classList.remove("active"));
  const activeBtn = document.getElementById(btnMap[lvl] || 'shadowing-level-btn-all');
  if (activeBtn) activeBtn.classList.add("active");
}

async function selectShadowingLevel(lvl) {
  state.listeningLevel = lvl;
  updateShadowingLevelPills(lvl);

  try {
    const listRes = await fetch(`/api/listening/list?level=${lvl}&user_id=${state.currentUser}`);
    shadowingTracksList = await listRes.json();

    const select = document.getElementById("shadowing-track-select");
    if (select && shadowingTracksList.length > 0) {
      select.innerHTML = shadowingTracksList.map((t) => {
        const prefix = t.is_completed ? '✅ ' : '🎧 ';
        return `<option value="${t.id}">${prefix}${t.title}</option>`;
      }).join("");

      // Check if user had a saved track ID
      const savedTrackId = parseInt(localStorage.getItem('duohub_listening_id_u' + state.currentUser));
      const foundIdx = shadowingTracksList.findIndex(t => t.id === savedTrackId);

      if (foundIdx !== -1) {
        currentShadowingTrackIndex = foundIdx;
        select.value = savedTrackId;
      } else {
        currentShadowingTrackIndex = 0;
        select.value = shadowingTracksList[0].id;
      }

      await loadShadowingById(select.value);
    }
  } catch (err) {
    console.error("Error loading shadowing track list:", err);
  }
}

async function onShadowingTrackDropdownChange(clipId) {
  const cId = parseInt(clipId);
  localStorage.setItem('duohub_listening_id_u' + state.currentUser, cId);
  if (shadowingTracksList.length > 0) {
    const idx = shadowingTracksList.findIndex(t => t.id === cId);
    if (idx !== -1) currentShadowingTrackIndex = idx;
  }
  if (typeof invalidatePillarCache === "function") {
    invalidatePillarCache('listening');
  }
  await loadShadowingById(cId);

  // Sync with Listening dropdown if present
  const listeningSelect = document.getElementById("listening-track-select");
  if (listeningSelect && Array.from(listeningSelect.options).some(o => o.value == cId)) {
    listeningSelect.value = cId;
  }
}

async function navShadowingTrack(direction) {
  if (!shadowingTracksList || shadowingTracksList.length === 0) return;
  currentShadowingTrackIndex += direction;
  if (currentShadowingTrackIndex < 0) currentShadowingTrackIndex = shadowingTracksList.length - 1;
  if (currentShadowingTrackIndex >= shadowingTracksList.length) currentShadowingTrackIndex = 0;

  const targetClip = shadowingTracksList[currentShadowingTrackIndex];
  const select = document.getElementById("shadowing-track-select");
  if (select) select.value = targetClip.id;

  localStorage.setItem('duohub_listening_id_u' + state.currentUser, targetClip.id);
  if (typeof invalidatePillarCache === "function") {
    invalidatePillarCache('listening');
  }
  await loadShadowingById(targetClip.id);

  // Sync with Listening dropdown
  const listeningSelect = document.getElementById("listening-track-select");
  if (listeningSelect && Array.from(listeningSelect.options).some(o => o.value == targetClip.id)) {
    listeningSelect.value = targetClip.id;
  }
}

function onShadowingSliderSeek(val) {
  const masterAudio = document.getElementById("shadowing-master-audio");
  if (masterAudio && masterAudio.src) {
    masterAudio.currentTime = parseFloat(val);
    const curTime = document.getElementById("shadowing-time-current");
    if (curTime) curTime.textContent = formatShadowingTime(parseFloat(val));
  }
}

function changeShadowingModelVolume(val) {
  shadowingModelVolume = parseFloat(val);
  const masterAudio = document.getElementById("shadowing-master-audio");
  if (masterAudio) {
    masterAudio.volume = shadowingModelVolume;
  }
  const label = document.getElementById("shadowing-vol-label");
  if (label) {
    label.textContent = `${Math.round(shadowingModelVolume * 100)}%`;
  }
}

function toggleShadowingTranscript() {
  const box = document.getElementById("shadowing-transcript-collapsible");
  const btn = document.getElementById("btn-toggle-shadowing-transcript");
  if (!box) return;
  if (box.style.display === "none") {
    box.style.display = "block";
    if (btn) btn.textContent = "🙈 Ocultar Transcripción";
  } else {
    box.style.display = "none";
    if (btn) btn.textContent = "👁️ Revelar Transcripción de Apoyo";
  }
}

async function loadShadowingById(clipId) {
  try {
    const res = await fetch(`/api/listening?id=${clipId}&user_id=${state.currentUser}`);
    const clip = await res.json();
    currentShadowingClip = clip;

    if (clip.error) {
      const trackTitle = document.getElementById("shadowing-track-title");
      if (trackTitle) trackTitle.textContent = "Clip no disponible";
      return;
    }

    // Update track badges and title
    const trackTitle = document.getElementById("shadowing-track-title");
    if (trackTitle) trackTitle.textContent = clip.title;
    const lvlBadge = document.getElementById("shadowing-level-badge");
    if (lvlBadge) lvlBadge.textContent = `${clip.level} Level`;

    const select = document.getElementById("shadowing-track-select");
    if (select && select.value != clip.id) {
      select.value = clip.id;
    }

    // Set up Master Model Audio Player & Scrubber
    const masterAudio = document.getElementById("shadowing-master-audio");
    const slider = document.getElementById("shadowing-audio-slider");
    const curTime = document.getElementById("shadowing-time-current");
    const totTime = document.getElementById("shadowing-time-total");

    if (slider) {
      slider.value = 0;
      slider.max = clip.duration_seconds || 100;
    }
    if (curTime) curTime.textContent = "00:00";
    if (totTime) totTime.textContent = formatShadowingTime(clip.duration_seconds || 0);

    if (masterAudio) {
      masterAudio.pause();
      isShadowingModelPlaying = false;
      const playBtn = document.getElementById("btn-play-shadowing-model");
      if (playBtn) playBtn.textContent = "▶ Escuchar Audio Modelo";

      if (clip.audio_url) {
        masterAudio.src = clip.audio_url;
        masterAudio.playbackRate = shadowingPlaybackSpeed;

        masterAudio.onloadedmetadata = () => {
          if (slider && masterAudio.duration) slider.max = masterAudio.duration;
          if (totTime && masterAudio.duration) totTime.textContent = formatShadowingTime(masterAudio.duration);
        };

        masterAudio.ontimeupdate = () => {
          if (slider && !slider.matches(':active')) {
            slider.value = masterAudio.currentTime;
          }
          if (curTime) curTime.textContent = formatShadowingTime(masterAudio.currentTime);
        };

        masterAudio.onended = () => {
          isShadowingModelPlaying = false;
          if (playBtn) playBtn.textContent = "▶ Escuchar Audio Modelo";
          if (slider) slider.value = slider.max;
        };
        masterAudio.volume = shadowingModelVolume;
      } else {
        masterAudio.src = "";
      }
    }

    // Render Complete Transcript
    renderShadowingTranscript(clip.transcript);

    // Check if user already completed shadowing for this track
    if (clip.shadowing_progress && clip.shadowing_progress.is_completed) {
      const sp = clip.shadowing_progress;
      const recDot = document.getElementById("rec-status-dot");
      if (recDot) recDot.classList.add("done");

      if (sp.audio_url) {
        const player = document.getElementById("user-audio-player");
        if (player) player.src = sp.audio_url;
        const playbackRow = document.getElementById("recording-playback-row");
        if (playbackRow) playbackRow.style.display = "block";
      }

      if (sp.ai_feedback) {
        renderShadowingAiAudit(sp.ai_feedback);
      }
    } else {
      // Uncompleted clip: clean empty state
      const recDot = document.getElementById("rec-status-dot");
      if (recDot) recDot.classList.remove("done");
      const player = document.getElementById("user-audio-player");
      if (player) { player.pause(); player.src = ""; }
      const playbackRow = document.getElementById("recording-playback-row");
      if (playbackRow) playbackRow.style.display = "none";
      const auditBox = document.getElementById("shadowing-ai-audit-container");
      if (auditBox) { auditBox.style.display = "none"; auditBox.innerHTML = ""; }
    }

    if (typeof applyReadOnlyLocks === "function") {
      applyReadOnlyLocks(state.isReadOnly);
    }
  } catch (err) {
    console.error("Error loading shadowing track data:", err);
  }
}

async function loadShadowingData(day) {
  const lvl = state.listeningLevel || (state.currentUser === 1 ? 'A1' : 'A2');
  if (!shadowingTracksList || shadowingTracksList.length === 0) {
    await selectShadowingLevel(lvl);
  } else {
    updateShadowingLevelPills(lvl);
    const savedTrackId = parseInt(localStorage.getItem('duohub_listening_id_u' + state.currentUser));
    const targetId = savedTrackId || (currentShadowingClip ? currentShadowingClip.id : shadowingTracksList[0].id);
    const select = document.getElementById("shadowing-track-select");
    if (select) select.value = targetId;
    await loadShadowingById(targetId);
  }
}

function renderShadowingTranscript(rawTranscript) {
  const container = document.getElementById("shadowing-full-transcript");
  if (!container) return;

  // Always keep transcript hidden initially when loading a track
  const collapsible = document.getElementById("shadowing-transcript-collapsible");
  const toggleBtn = document.getElementById("btn-toggle-shadowing-transcript");
  if (collapsible) collapsible.style.display = "none";
  if (toggleBtn) toggleBtn.textContent = "👁️ Revelar Transcripción de Apoyo";

  if (!rawTranscript || rawTranscript.trim().length === 0) {
    container.innerHTML = `<div class="empty-state">Transcripción no disponible para esta pista.</div>`;
    return;
  }

  // Split lines into speakers or paragraphs
  const lines = rawTranscript.split("\n").filter(l => l.trim().length > 0);
  
  container.innerHTML = lines.map((line, idx) => {
    // Check if line has "Speaker:" format (e.g. "Susannah: Hello, Mario.")
    const colonIdx = line.indexOf(":");
    if (colonIdx > 0 && colonIdx < 30) {
      const speaker = line.substring(0, colonIdx).trim();
      const dialogue = line.substring(colonIdx + 1).trim();
      const words = dialogue.split(/\s+/).map(w => {
        const clean = w.replace(/[^a-zA-Z]/g, "");
        if (clean.length > 2) {
          return `<span class="interactive-word" onclick="speakEnglish('${escapeQuotes(clean)}', 0.9)" title="Clic para escuchar pronunciación">${w}</span>`;
        }
        return w;
      }).join(" ");

      return `
        <div class="transcript-dialogue-row">
          <span class="speaker-tag">${speaker}:</span>
          <div class="dialogue-speech-bubble">${words}</div>
        </div>
      `;
    } else {
      // General paragraph
      const words = line.split(/\s+/).map(w => {
        const clean = w.replace(/[^a-zA-Z]/g, "");
        if (clean.length > 2) {
          return `<span class="interactive-word" onclick="speakEnglish('${escapeQuotes(clean)}', 0.9)" title="Clic para escuchar pronunciación">${w}</span>`;
        }
        return w;
      }).join(" ");

      return `<p class="transcript-narrative-p">${words}</p>`;
    }
  }).join("");
}

// Model Audio Controls
function togglePlayShadowingModel() {
  const audio = document.getElementById("shadowing-master-audio");
  const playBtn = document.getElementById("btn-play-shadowing-model");
  if (!audio) return;

  if (audio.paused) {
    audio.play().then(() => {
      isShadowingModelPlaying = true;
      if (playBtn) playBtn.textContent = "⏸ Pausar Audio Modelo";
    }).catch(e => console.warn("Audio play blocked:", e));
  } else {
    audio.pause();
    isShadowingModelPlaying = false;
    if (playBtn) playBtn.textContent = "▶ Escuchar Audio Modelo";
  }
}

function changeShadowingSpeed(val) {
  shadowingPlaybackSpeed = parseFloat(val);
  const audio = document.getElementById("shadowing-master-audio");
  if (audio) {
    audio.playbackRate = shadowingPlaybackSpeed;
  }
}

// In-browser Microphone Recording with simultaneous audio playback
async function toggleRecording() {
  const btn = document.getElementById("btn-record-mic");
  const statusDot = document.getElementById("rec-status-dot");
  const masterAudio = document.getElementById("shadowing-master-audio");
  const shouldAutoPlay = document.getElementById("chk-auto-play-audio") ? document.getElementById("chk-auto-play-audio").checked : true;
  const meterContainer = document.getElementById("mic-meter-container");
  const meterBar = document.getElementById("mic-meter-bar");
  const meterStatus = document.getElementById("mic-meter-status");

  if (!isRecording) {
    // START RECORDING
    try {
      // Use clean unsuppressed audio constraints so speaker playback does not cause aggressive browser AEC gating/muting
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: true
          }
        });
      } catch (errFallback) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }

      recordedChunks = [];

      // Select optimal supported MIME type
      let recorderOptions = {};
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        recorderOptions = { mimeType: 'audio/webm;codecs=opus' };
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        recorderOptions = { mimeType: 'audio/webm' };
      }

      mediaRecorder = new MediaRecorder(stream, recorderOptions);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordedChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const mime = mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(recordedChunks, { type: mime });
        const audioUrl = URL.createObjectURL(audioBlob);
        const player = document.getElementById("user-audio-player");
        if (player) {
          player.src = audioUrl;
          player.volume = 1.0;
        }
        const playbackRow = document.getElementById("recording-playback-row");
        if (playbackRow) {
          playbackRow.style.display = "block";
          playbackRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      };

      // Set up real-time Mic VU Meter
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        micAudioCtx = new AudioCtx();
        const source = micAudioCtx.createMediaStreamSource(stream);
        micAnalyser = micAudioCtx.createAnalyser();
        micAnalyser.fftSize = 256;
        source.connect(micAnalyser);

        if (meterContainer) meterContainer.style.display = "block";
        const dataArray = new Uint8Array(micAnalyser.frequencyBinCount);

        const updateMeter = () => {
          if (!isRecording) return;
          micAnalyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          const pct = Math.min(100, Math.round((avg / 128) * 100));
          if (meterBar) meterBar.style.width = pct + "%";
          if (meterStatus) {
            meterStatus.textContent = pct > 10 ? "🎤 Captando voz (OK)" : "🎤 Esperando voz...";
          }
          micAnimFrame = requestAnimationFrame(updateMeter);
        };
        updateMeter();
      } catch (eVis) {
        console.warn("Could not start visualizer meter:", eVis);
      }

      mediaRecorder.start();
      isRecording = true;
      btn.classList.add("recording");
      btn.innerHTML = `<span class="rec-dot"></span> ⏹️ Detener Shadowing & Grabación`;
      if (statusDot) statusDot.classList.add("pulsing");

      // Auto-play native audio if checked
      if (shouldAutoPlay && masterAudio && masterAudio.src) {
        masterAudio.currentTime = 0;
        masterAudio.volume = shadowingModelVolume;
        masterAudio.play().then(() => {
          isShadowingModelPlaying = true;
          const playBtn = document.getElementById("btn-play-shadowing-model");
          if (playBtn) playBtn.textContent = "⏸ Pausar Audio Modelo";
        }).catch(e => console.warn("Model audio autoplay blocked:", e));
      }

      // Start Live Timer
      recordStartTime = Date.now();
      recordTimerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordStartTime) / 1000);
        const m = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const s = (elapsed % 60).toString().padStart(2, '0');
        const timerElem = document.getElementById("recording-timer");
        if (timerElem) timerElem.textContent = `${m}:${s}`;
      }, 1000);

    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("No se pudo acceder al micrófono. Por favor habilita los permisos de audio en tu navegador.");
    }
  } else {
    // STOP RECORDING
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isRecording = false;
    clearInterval(recordTimerInterval);
    if (micAnimFrame) cancelAnimationFrame(micAnimFrame);
    if (micAudioCtx) {
      micAudioCtx.close().catch(() => {});
      micAudioCtx = null;
    }
    if (meterBar) meterBar.style.width = "0%";
    if (meterStatus) meterStatus.textContent = "Grabación detenida";

    btn.classList.remove("recording");
    btn.innerHTML = `<span class="rec-dot"></span> 🎙️ Grabar Otra Toma de Shadowing`;
    if (statusDot) statusDot.classList.remove("pulsing");

    // Pause master audio if playing
    if (masterAudio && !masterAudio.paused) {
      masterAudio.pause();
      isShadowingModelPlaying = false;
      const playBtn = document.getElementById("btn-play-shadowing-model");
      if (playBtn) playBtn.textContent = "▶ Escuchar Audio Modelo";
    }
  }
}

async function auditShadowingWithAI() {
  if (typeof isReadOnlyMode === 'function' && isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  if (!recordedChunks || recordedChunks.length === 0) {
    alert("Primero graba tu toma de Shadowing antes de solicitar la auditoría con IA.");
    return;
  }

  const btn = document.getElementById("btn-audit-shadowing");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "⏳ Evaluando pronunciación y cadencia con IA...";
  }

  try {
    const mime = (mediaRecorder && mediaRecorder.mimeType) ? mediaRecorder.mimeType : 'audio/webm';
    const audioBlob = new Blob(recordedChunks, { type: mime });
    const formData = new FormData();
    formData.append("audio", audioBlob, "shadowing_practice.webm");
    formData.append("user_id", state.currentUser);
    formData.append("date", state.currentDate);
    formData.append("day", state.currentDay);
    if (currentShadowingClip && currentShadowingClip.id) {
      formData.append("clip_id", currentShadowingClip.id);
    }

    const res = await fetch("/api/shadowing/evaluate", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.success && data.feedback) {
      renderShadowingAiAudit(data.feedback);
      speakEnglish(`Shadowing evaluated! Fluency score: ${data.feedback.fluency_score || 80}`, 1.0);
      fetchStatusAndRefresh();
    } else {
      alert(data.error || "No se pudo completar la evaluación con IA.");
    }
  } catch (err) {
    console.error("Error evaluating shadowing with AI:", err);
    alert("Error al conectar con el servidor para la auditoría de pronunciación.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "✨ Auditar Mi Pronunciación & Cadencia con IA";
    }
  }
}

function renderShadowingAiAudit(feedback) {
  const container = document.getElementById("shadowing-ai-audit-container");
  if (!container || !feedback) return;
  container.style.display = "block";

  let strengthsHtml = "";
  if (feedback.strengths && feedback.strengths.length > 0) {
    strengthsHtml = `
      <div class="audit-section-subtitle">💪 Aciertos y Fortalezas:</div>
      <ul class="audit-missed-list">
        ${feedback.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
      </ul>
    `;
  }

  let polishHtml = "";
  if (feedback.words_to_polish && feedback.words_to_polish.length > 0) {
    polishHtml = `
      <div class="audit-section-subtitle">🎯 Palabras a Pulir (Pronunciación / Enlace):</div>
      <div class="confusion-grid">
        ${feedback.words_to_polish.map(item => `
          <div class="confusion-chip">
            <div class="chip-header">
              <span>🔊 "${escapeHtml(item.word || '')}"</span>
              <button type="button" class="btn btn-xs btn-ghost" onclick="speakEnglish('${escapeQuotes(item.word || '')}', 0.85)" title="Escuchar pronunciación nativa">🔊</button>
            </div>
            <div class="chip-desc">${escapeHtml(item.note || '')}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  let cadenceHtml = "";
  if (feedback.cadence_tip) {
    cadenceHtml = `
      <div class="audit-coaching-box">
        <strong>🌊 Consejo de Cadencia y Sincronía:</strong> ${escapeHtml(feedback.cadence_tip)}
      </div>
    `;
  }

  const score = feedback.fluency_score || 80;
  const scoreColor = score >= 85 ? 'var(--busuu-emerald)' : (score >= 65 ? 'var(--busuu-amber)' : 'var(--busuu-coral)');

  container.innerHTML = `
    <div class="audit-header">
      <div class="audit-title">🎙️ Evaluación IA de Pronunciación & Cadencia</div>
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="audit-source-tag">${escapeHtml(feedback.source || 'Auditoría IA')}</span>
        <span class="badge" style="background: ${scoreColor}; color: #FFF; font-weight: 800;">${score}/100 Puntos</span>
      </div>
    </div>
    <p class="audit-verdict-p">${escapeHtml(feedback.pronunciation_verdict || '')}</p>
    ${strengthsHtml}
    ${polishHtml}
    ${cadenceHtml}
  `;
}

async function markShadowingDone() {
  if (typeof isReadOnlyMode === 'function' && isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  try {
    const res = await fetch("/api/shadowing/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        date: state.currentDate,
        day: state.currentDay
      })
    });
    const data = await res.json();
    if (data.success) {
      speakEnglish("Shadowing session completed and saved!", 1.0);
      fetchStatusAndRefresh();
    }
  } catch (err) {
    console.error("Error marking shadowing done:", err);
  }
}

// Window global exports
window.onShadowingSliderSeek = onShadowingSliderSeek;
window.toggleShadowingTranscript = toggleShadowingTranscript;
window.togglePlayShadowingModel = togglePlayShadowingModel;
window.changeShadowingSpeed = changeShadowingSpeed;
window.changeShadowingModelVolume = changeShadowingModelVolume;
window.toggleRecording = toggleRecording;
window.auditShadowingWithAI = auditShadowingWithAI;
window.markShadowingDone = markShadowingDone;
window.loadShadowingData = loadShadowingData;
window.selectShadowingLevel = selectShadowingLevel;
window.onShadowingTrackDropdownChange = onShadowingTrackDropdownChange;
window.navShadowingTrack = navShadowingTrack;
window.shadowingRewind = shadowingRewind;
window.shadowingForward = shadowingForward;
