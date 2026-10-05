/**
 * DUOHUB - Pillar 4: Shadowing Studio Controller
 */

let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let recordStartTime = 0;
let recordTimerInterval = null;

async function loadShadowingData(day) {
  try {
    const res = await fetch(`/api/listening?day=${day}`);
    const data = await res.json();

    const list = document.getElementById("shadowing-chunks-list");
    if (!data.shadowing_chunks || data.shadowing_chunks.length === 0) {
      list.innerHTML = `<div class="empty-state">No hay frases de shadowing registradas para hoy.</div>`;
      return;
    }

    list.innerHTML = data.shadowing_chunks.map((chunk, idx) => `
      <div class="chunk-card">
        <div class="chunk-text"><strong>${idx + 1}.</strong> "${chunk}"</div>
        <button class="btn btn-sm btn-secondary" onclick="playShadowingChunk('${escapeQuotes(chunk)}')">
          🔊 Escuchar Modelo Nativo
        </button>
      </div>
    `).join("");

  } catch (err) {
    console.error("Error loading shadowing chunks:", err);
  }
}

function playShadowingChunk(text) {
  speakEnglish(text, 0.95);
}

// In-browser Microphone Recording
async function toggleRecording() {
  const btn = document.getElementById("btn-record-mic");

  if (!isRecording) {
    // Start Recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunks = [];
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordedChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(recordedChunks, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const player = document.getElementById("user-audio-player");
        player.src = audioUrl;
        document.getElementById("recording-playback-row").style.display = "flex";
      };

      mediaRecorder.start();
      isRecording = true;
      btn.classList.add("recording");
      btn.innerHTML = `<span class="rec-dot"></span> Detener Grabación`;

      // Start Timer
      recordStartTime = Date.now();
      recordTimerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - recordStartTime) / 1000);
        const m = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const s = (elapsed % 60).toString().padStart(2, '0');
        document.getElementById("recording-timer").textContent = `${m}:${s}`;
      }, 1000);

    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("No se pudo acceder al micrófono. Por favor habilita los permisos de audio en tu navegador.");
    }
  } else {
    // Stop Recording
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isRecording = false;
    clearInterval(recordTimerInterval);
    btn.classList.remove("recording");
    btn.innerHTML = `<span class="rec-dot"></span> Grabar de Nuevo`;
  }
}

async function markShadowingDone() {
  try {
    const res = await fetch("/api/shadowing/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        day: state.currentDay
      })
    });
    const data = await res.json();
    if (data.success) {
      speakEnglish("Shadowing session saved! Your tongue and speech muscles are improving.", 1.0);
      fetchStatusAndRefresh();
    }
  } catch (err) {
    console.error("Error marking shadowing done:", err);
  }
}
