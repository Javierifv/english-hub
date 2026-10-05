/**
 * DUOHUB - Global Application Controller
 */

const state = {
  currentUser: 1, // 1: Javier, 2: Compañero
  currentDay: 1,
  maxDays: 7,
  activeTab: 'vocab',
  todayLog: null,
  streak: 0,
  partnerStatus: null
};

// Speech synthesis voice helper
let cachedEnglishVoice = null;
function getEnglishVoice() {
  if (cachedEnglishVoice) return cachedEnglishVoice;
  if (!('speechSynthesis' in window)) return null;

  const voices = window.speechSynthesis.getVoices();
  // Look for high-quality native US/UK voices (Google, Samantha, Daniel, Natural)
  cachedEnglishVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Daniel')))
                    || voices.find(v => v.lang.startsWith('en-US'))
                    || voices.find(v => v.lang.startsWith('en'));
  return cachedEnglishVoice;
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    getEnglishVoice();
  };
}

// Speak text using Web Speech API
function speakEnglish(text, rate = 1.0) {
  if (!('speechSynthesis' in window)) {
    alert("Tu navegador no soporta síntesis de voz Web Speech.");
    return;
  }
  window.speechSynthesis.cancel(); // Stop any ongoing speech
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US';
  utterance.rate = rate;
  const voice = getEnglishVoice();
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
  initDayControls();
  fetchStatusAndRefresh();
});

function initDayControls() {
  document.getElementById("btn-prev-day").addEventListener("click", () => {
    if (state.currentDay > 1) {
      state.currentDay--;
      document.getElementById("current-day-number").textContent = state.currentDay;
      fetchStatusAndRefresh();
    }
  });

  document.getElementById("btn-next-day").addEventListener("click", () => {
    state.currentDay++;
    document.getElementById("current-day-number").textContent = state.currentDay;
    fetchStatusAndRefresh();
  });
}

function switchUser(userId) {
  state.currentUser = userId;
  document.getElementById("user-pill-1").classList.toggle("active", userId === 1);
  document.getElementById("user-pill-2").classList.toggle("active", userId === 2);
  fetchStatusAndRefresh();
}

async function fetchStatusAndRefresh() {
  try {
    const res = await fetch(`/api/status?user_id=${state.currentUser}&day=${state.currentDay}`);
    const data = await res.json();
    
    state.todayLog = data.log;
    state.streak = data.streak;
    state.partnerStatus = data.partner;
    state.maxDays = data.max_days;

    updateHeaderUI();
    loadCurrentPillarData();
  } catch (err) {
    console.error("Error al obtener estado:", err);
  }
}

function updateHeaderUI() {
  // Update Streak
  document.getElementById("streak-count").textContent = state.streak;

  // Active user greeting
  const isJavier = state.currentUser === 1;
  document.getElementById("active-user-greeting").textContent = `Entrenando como ${isJavier ? 'Javier' : 'Compañero'}`;

  // Partner status
  if (state.partnerStatus) {
    document.getElementById("partner-status-text").textContent = 
      `${state.partnerStatus.name} lleva ${state.partnerStatus.completed_count} de 5 tareas completadas hoy.`;
    
    if (isJavier) {
      document.getElementById("user-1-stat").textContent = `${state.todayLog.completed_count}/5`;
      document.getElementById("user-2-stat").textContent = `${state.partnerStatus.completed_count}/5`;
    } else {
      document.getElementById("user-2-stat").textContent = `${state.todayLog.completed_count}/5`;
      document.getElementById("user-1-stat").textContent = `${state.partnerStatus.completed_count}/5`;
    }
  }

  // Update Daily Progress Bar
  const count = state.todayLog.completed_count || 0;
  const pct = Math.round((count / 5) * 100);
  document.getElementById("daily-progress-bar").style.width = `${pct}%`;
  document.getElementById("daily-progress-text").textContent = `${count}/5 Completado`;

  // Update Pillar checkmarks
  updatePillarBadge("vocab", state.todayLog.vocab_done);
  updatePillarBadge("reading", state.todayLog.reading_done);
  updatePillarBadge("listening", state.todayLog.listening_done);
  updatePillarBadge("shadowing", state.todayLog.shadowing_done);
  updatePillarBadge("speaking", state.todayLog.speaking_done);

  // Check for 5/5 celebration
  if (count === 5 && !sessionStorage.getItem(`celebrated_day_${state.currentDay}_u_${state.currentUser}`)) {
    sessionStorage.setItem(`celebrated_day_${state.currentDay}_u_${state.currentUser}`, "true");
    showCelebrationModal();
  }
}

function updatePillarBadge(name, isDone) {
  const checkElem = document.getElementById(`tab-check-${name}`);
  const tabElem = document.querySelector(`.pillar-tab[data-tab="${name}"]`);
  if (checkElem && tabElem) {
    if (isDone) {
      checkElem.textContent = "✓";
      tabElem.classList.add("completed");
    } else {
      checkElem.textContent = "○";
      tabElem.classList.remove("completed");
    }
  }
}

function showPillar(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll(".pillar-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
  document.querySelectorAll(".pillar-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === `panel-${tabName}`);
  });
  loadCurrentPillarData();
}

function loadCurrentPillarData() {
  switch (state.activeTab) {
    case 'vocab':
      loadVocabData(state.currentDay);
      break;
    case 'reading':
      loadReadingData(state.currentDay);
      break;
    case 'listening':
      loadListeningData(state.currentDay);
      break;
    case 'shadowing':
      loadShadowingData(state.currentDay);
      break;
    case 'speaking':
      loadSpeakingData(state.currentDay);
      break;
  }
}

function showCelebrationModal() {
  document.getElementById("celebration-modal").style.display = "flex";
}

function closeCelebrationModal() {
  document.getElementById("celebration-modal").style.display = "none";
}
