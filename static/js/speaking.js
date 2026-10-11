/**
 * DUOHUB - Pillar 5: Speaking Challenge In-App Controller
 * 100% In-App Voice Studio:
 * - Real-time Microphone VU Meter
 * - Live Timer (1 to 5 min recommended)
 * - In-Browser Audio Player
 * - Multimodal AI Speaking Audit (CEFR level, grammar, vocabulary, fluency feedback)
 * - Automatic persistence to daily logs
 */

let speakingMediaRecorder = null;
let speakingRecordedChunks = [];
let isSpeakingRecording = false;
let speakingRecordStartTime = 0;
let speakingRecordTimerInterval = null;
let speakingDurationSeconds = 0;

// Mic Live Audio Analysis
let speakingAudioCtx = null;
let speakingAnalyser = null;
let speakingAnimFrame = null;

async function loadSpeakingData(day) {
  try {
    const res = await fetch(`/api/speaking?day=${day}&date=${state.currentDate}&user_id=${state.currentUser}`);
    const data = await res.json();

    const topicEl = document.getElementById("speaking-topic-name");
    if (topicEl) topicEl.textContent = "Práctica Libre";
    
    const questionEl = document.getElementById("speaking-question");
    if (questionEl) {
      questionEl.textContent = data.prompt_question ? `"${data.prompt_question}"` : `"Habla con libertad sobre tu día, proyectos o ideas."`;
    }
    
    const guidelinesEl = document.getElementById("speaking-guidelines-content");
    if (guidelinesEl) {
      guidelinesEl.textContent = data.suggested_guidelines || 'Sugerencia opcional: puedes contar lo que hiciste hoy, tus planes para la semana o practicar estructurando una historia sencilla con conectores.';
    }

    // Render Target Words Checklist
    const list = document.getElementById("speaking-target-words-list");
    if (data.target_words && data.target_words.length > 0) {
      list.innerHTML = data.target_words.map(w => `
        <div class="target-word-item" onclick="toggleTargetWordCheck(this)">
          <div>
            <span class="target-word-name">${escapeHtml(w.word)}</span>
            <span class="target-word-trans">(${escapeHtml(w.translation)})</span>
          </div>
          <span class="check-icon">○</span>
        </div>
      `).join("");
    } else {
      list.innerHTML = `<div class="empty-state">No hay palabras asignadas para hoy.</div>`;
    }

    const playbackStation = document.getElementById("speaking-playback-station");
    const player = document.getElementById("speaking-user-audio-player");
    const auditContainer = document.getElementById("speaking-ai-audit-container");

    // Check if user already recorded or completed speaking for THIS SELECTED DATE
    const log = data.daily_log;
    if (log && log.speaking_done) {
      if (playbackStation) playbackStation.style.display = "block";
      if (player) {
        player.src = log.speaking_audio_path || "";
      }
      if (log.speaking_ai_feedback) {
        try {
          const feedback = typeof log.speaking_ai_feedback === "string"
            ? JSON.parse(log.speaking_ai_feedback)
            : log.speaking_ai_feedback;
          renderSpeakingAiAudit(feedback);
        } catch (e) {
          console.warn("Could not parse saved speaking AI feedback:", e);
        }
      } else if (auditContainer) {
        auditContainer.style.display = "none";
        auditContainer.innerHTML = "";
      }
    } else {
      // Date has no speaking: clean empty state
      if (playbackStation) playbackStation.style.display = "none";
      if (player) {
        player.pause();
        player.src = "";
      }
      if (auditContainer) {
        auditContainer.style.display = "none";
        auditContainer.innerHTML = "";
      }
    }

    if (typeof applyReadOnlyLocks === "function") {
      applyReadOnlyLocks(state.isReadOnly);
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

// In-app Speaking Recording Studio
async function toggleSpeakingRecording() {
  const btn = document.getElementById("btn-record-speaking");
  const statusDot = document.getElementById("speaking-rec-status-dot");
  const meterContainer = document.getElementById("speaking-mic-meter-container");
  const meterBar = document.getElementById("speaking-mic-meter-bar");
  const meterStatus = document.getElementById("speaking-mic-meter-status");

  if (!isSpeakingRecording) {
    // START RECORDING
    try {
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
      } catch (errFallback) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }

      speakingRecordedChunks = [];

      let recorderOptions = {};
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        recorderOptions = { mimeType: 'audio/webm;codecs=opus' };
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        recorderOptions = { mimeType: 'audio/webm' };
      }

      speakingMediaRecorder = new MediaRecorder(stream, recorderOptions);

      speakingMediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          speakingRecordedChunks.push(e.data);
        }
      };

      speakingMediaRecorder.onstop = () => {
        const mime = speakingMediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(speakingRecordedChunks, { type: mime });
        const audioUrl = URL.createObjectURL(audioBlob);
        const player = document.getElementById("speaking-user-audio-player");
        if (player) {
          player.src = audioUrl;
          player.volume = 1.0;
        }
        const playbackStation = document.getElementById("speaking-playback-station");
        if (playbackStation) {
          playbackStation.style.display = "block";
          playbackStation.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      };

      // Set up real-time Mic VU Meter
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        speakingAudioCtx = new AudioCtx();
        const source = speakingAudioCtx.createMediaStreamSource(stream);
        speakingAnalyser = speakingAudioCtx.createAnalyser();
        speakingAnalyser.fftSize = 256;
        source.connect(speakingAnalyser);

        if (meterContainer) meterContainer.style.display = "block";
        const dataArray = new Uint8Array(speakingAnalyser.frequencyBinCount);

        const updateMeter = () => {
          if (!isSpeakingRecording) return;
          speakingAnalyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          const pct = Math.min(100, Math.round((avg / 128) * 100));
          if (meterBar) meterBar.style.width = pct + "%";
          if (meterStatus) {
            meterStatus.textContent = pct > 8 ? "🎤 Grabando tu voz (Nivel óptimo)" : "🎤 Habla al micrófono...";
          }
          speakingAnimFrame = requestAnimationFrame(updateMeter);
        };
        updateMeter();
      } catch (eVis) {
        console.warn("Could not start visualizer meter for speaking:", eVis);
      }

      speakingMediaRecorder.start();
      isSpeakingRecording = true;
      btn.classList.add("recording");
      btn.innerHTML = `<span class="rec-dot"></span> ⏹️ Detener Grabación de Speaking`;
      if (statusDot) statusDot.classList.add("pulsing");

      // Start Live Timer
      speakingRecordStartTime = Date.now();
      speakingRecordTimerInterval = setInterval(() => {
        speakingDurationSeconds = Math.floor((Date.now() - speakingRecordStartTime) / 1000);
        const m = Math.floor(speakingDurationSeconds / 60).toString().padStart(2, '0');
        const s = (speakingDurationSeconds % 60).toString().padStart(2, '0');
        const timerElem = document.getElementById("speaking-recording-timer");
        if (timerElem) timerElem.textContent = `${m}:${s}`;
      }, 1000);

    } catch (err) {
      console.error("Error accessing microphone for speaking:", err);
      alert("No se pudo acceder al micrófono. Por favor habilita los permisos de audio en tu navegador.");
    }
  } else {
    // STOP RECORDING
    if (speakingMediaRecorder && speakingMediaRecorder.state !== "inactive") {
      speakingMediaRecorder.stop();
      speakingMediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isSpeakingRecording = false;
    clearInterval(speakingRecordTimerInterval);
    if (speakingAnimFrame) cancelAnimationFrame(speakingAnimFrame);
    if (speakingAudioCtx) {
      speakingAudioCtx.close().catch(() => {});
      speakingAudioCtx = null;
    }
    if (meterBar) meterBar.style.width = "0%";
    if (meterStatus) meterStatus.textContent = "Grabación detenida";

    btn.classList.remove("recording");
    btn.innerHTML = `<span class="rec-dot"></span> 🎙️ Grabar Otra Toma de Speaking`;
    if (statusDot) statusDot.classList.remove("pulsing");
  }
}

// Multimodal AI Speaking Audit
async function auditSpeakingWithAI() {
  if (typeof isReadOnlyMode === 'function' && isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  if (!speakingRecordedChunks || speakingRecordedChunks.length === 0) {
    alert("Primero graba tu respuesta de speaking antes de auditarla con IA.");
    return;
  }

  const btn = document.getElementById("btn-audit-speaking");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "⏳ Evaluando tu speaking oral con IA...";
  }

  // Get checked target words
  const checkedWords = Array.from(document.querySelectorAll(".target-word-item.checked .target-word-name"))
    .map(el => el.textContent.trim());

  try {
    const mime = (speakingMediaRecorder && speakingMediaRecorder.mimeType) ? speakingMediaRecorder.mimeType : 'audio/webm';
    const audioBlob = new Blob(speakingRecordedChunks, { type: mime });
    const formData = new FormData();
    formData.append("audio", audioBlob, "speaking_challenge.webm");
    formData.append("user_id", state.currentUser);
    formData.append("date", state.currentDate);
    formData.append("day", state.currentDay);
    formData.append("used_words", checkedWords.join(", "));
    formData.append("duration_seconds", speakingDurationSeconds || 30);

    const res = await fetch("/api/speaking/record", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.success && data.feedback) {
      renderSpeakingAiAudit(data.feedback);
      speakEnglish(`Speaking audit completed! Estimated level: ${data.feedback.estimated_cefr || 'A2'}`, 1.0);
      fetchStatusAndRefresh();
    } else {
      alert(data.error || "No se pudo completar la auditoría de speaking.");
    }
  } catch (err) {
    console.error("Error evaluating speaking with AI:", err);
    alert("Error al conectar con el servidor para la auditoría de speaking.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "✨ Auditar Mi Speaking con IA";
    }
  }
}

function renderSpeakingAiAudit(feedback) {
  const container = document.getElementById("speaking-ai-audit-container");
  if (!container || !feedback) return;
  container.style.display = "block";

  let grammarHtml = "";
  if (feedback.grammar_observations && feedback.grammar_observations.length > 0) {
    grammarHtml = `
      <div class="audit-section-subtitle">📝 Observaciones Gramaticales & Estructura:</div>
      <ul class="audit-missed-list">
        ${feedback.grammar_observations.map(g => `<li>${escapeHtml(g)}</li>`).join('')}
      </ul>
    `;
  }

  let vocabHtml = "";
  if (feedback.vocab_usage_feedback) {
    vocabHtml = `
      <div class="audit-section-subtitle">🎯 Uso de Vocabulario:</div>
      <p style="font-size: 0.88rem; color: #334155; margin-bottom: 0.75rem; line-height: 1.5;">${escapeHtml(feedback.vocab_usage_feedback)}</p>
    `;
  }

  let snippetHtml = "";
  if (feedback.transcription_snippet) {
    snippetHtml = `
      <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: var(--radius-sm); padding: 0.65rem 0.85rem; margin-bottom: 0.85rem;">
        <span style="font-size: 0.76rem; font-weight: 800; color: #64748B; text-transform: uppercase;">Fragmento Transcrito de tu Audio:</span>
        <p style="font-size: 0.88rem; font-style: italic; color: #1E293B; margin: 0.25rem 0 0 0;">"${escapeHtml(feedback.transcription_snippet)}"</p>
      </div>
    `;
  }

  let coachingHtml = "";
  if (feedback.fluency_coaching_tip) {
    coachingHtml = `
      <div class="audit-coaching-box">
        <strong>🚀 Consejo para Próximas Respuestas:</strong> ${escapeHtml(feedback.fluency_coaching_tip)}
      </div>
    `;
  }

  let tipsHtml = "";
  if (feedback.pronunciation_and_vocab_tips && feedback.pronunciation_and_vocab_tips.length > 0) {
    tipsHtml = `
      <div class="audit-section-subtitle">🗣️ Puntos de Pronunciación & Expresión a Pulir:</div>
      <ul class="audit-missed-list">
        ${feedback.pronunciation_and_vocab_tips.map(t => `<li>${escapeHtml(t)}</li>`).join('')}
      </ul>
    `;
  }

  const cefr = feedback.estimated_cefr || "A2";

  container.innerHTML = `
    <div class="audit-header">
      <div class="audit-title">🗣️ Auditoría Técnica de Speaking Oral</div>
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <span class="audit-source-tag">${escapeHtml(feedback.source || 'Auditoría IA')}</span>
        <span class="badge badge-accent" style="font-weight: 800;">Nivel Detectado: ${escapeHtml(cefr)}</span>
      </div>
    </div>
    <p class="audit-verdict-p">${escapeHtml(feedback.overall_verdict || '')}</p>
    ${snippetHtml}
    ${grammarHtml}
    ${tipsHtml}
    ${vocabHtml}
    ${coachingHtml}
  `;

  setTimeout(() => {
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, 100);
}

async function saveAndFinishSpeaking() {
  if (typeof isReadOnlyMode === 'function' && isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
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
        notes: `Recorded audio in hub. Target words: ${checkedWords.join(", ")}`
      })
    });
    const data = await res.json();
    if (data.success) {
      speakEnglish("Speaking challenge successfully saved and completed!", 1.0);
      fetchStatusAndRefresh();
    }
  } catch (err) {
    console.error("Error marking speaking done:", err);
  }
}

// Global Exports
window.loadSpeakingData = loadSpeakingData;
window.toggleTargetWordCheck = toggleTargetWordCheck;
window.toggleSpeakingRecording = toggleSpeakingRecording;
window.auditSpeakingWithAI = auditSpeakingWithAI;
window.saveAndFinishSpeaking = saveAndFinishSpeaking;
window.markSpeakingDone = saveAndFinishSpeaking;
