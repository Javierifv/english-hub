/**
 * DUOHUB - Global Application Controller (Busuu & Duo Edition)
 */

const state = {
  currentUser: 1, // 1: Javier, 2: Compañero
  currentDate: getTodayDateString(),
  currentDay: 1,
  maxDays: 107,
  activeTab: 'vocab',
  todayLog: null,
  streak: 0,
  partnerStatus: null,
  userInfo: null,
  usersList: [],
  selectedWordsPerDay: 5,
  selectedSelectionMode: 'progressive',
  preferredLevel: 'A1',
  selectedPreferredLevel: 'A1',
  readingLevel: 'A1',
  readingLevelSetByUser: false,
  readingChapter: 1,
  listeningLevel: 'A1',
  listeningLevelSetByUser: false,
  listeningTrack: 1
};

function getTodayDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Speech synthesis voice helper
let cachedEnglishVoice = null;
function getEnglishVoice() {
  if (cachedEnglishVoice) return cachedEnglishVoice;
  if (!('speechSynthesis' in window)) return null;

  const voices = window.speechSynthesis.getVoices();
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

function speakEnglish(text, rate = 1.0) {
  if (!('speechSynthesis' in window)) {
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US';
  utterance.rate = rate;
  const voice = getEnglishVoice();
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
  initDateControls();
  fetchUsersAndStatus();
});

function initDateControls() {
  const prevBtn = document.getElementById("btn-prev-day");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => shiftDate(-1));
  }

  const nextBtn = document.getElementById("btn-next-day");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => shiftDate(1));
  }

  const dateInput = document.getElementById("calendar-date-input");
  if (dateInput) {
    dateInput.value = state.currentDate;
  }

  // Calculate day index initially
  setDate(state.currentDate, false);
}

function openDatePicker() {
  const dateInput = document.getElementById("calendar-date-input");
  if (dateInput) {
    if (typeof dateInput.showPicker === 'function') {
      dateInput.showPicker();
    } else {
      dateInput.click();
    }
  }
}

function onDateInputChange(val) {
  if (val) {
    setDate(val);
  }
}

function shiftDate(deltaDays) {
  const parts = state.currentDate.split("-").map(Number);
  const cur = new Date(parts[0], parts[1] - 1, parts[2]);
  cur.setDate(cur.getDate() + deltaDays);
  const year = cur.getFullYear();
  const month = String(cur.getMonth() + 1).padStart(2, '0');
  const day = String(cur.getDate()).padStart(2, '0');
  setDate(`${year}-${month}-${day}`);
}

function setDate(dateStr, triggerRefresh = true) {
  state.currentDate = dateStr;
  const anchor = new Date(2026, 9, 1); // Baseline: Oct 1, 2026
  const parts = dateStr.split("-").map(Number);
  const cur = new Date(parts[0], parts[1] - 1, parts[2]);
  const diffDays = Math.round((cur - anchor) / (1000 * 60 * 60 * 24));
  state.currentDay = Math.max(1, diffDays + 1);

  const dateInput = document.getElementById("calendar-date-input");
  if (dateInput) dateInput.value = dateStr;

  renderDateDisplay();

  if (triggerRefresh) {
    fetchStatusAndRefresh();
  }
}

function goToTodayDate() {
  setDate(getTodayDateString());
}

function renderDateDisplay() {
  const parts = state.currentDate.split("-").map(Number);
  const cur = new Date(parts[0], parts[1] - 1, parts[2]);
  const todayStr = getTodayDateString();
  const isToday = state.currentDate === todayStr;

  const dayNameElem = document.getElementById("calendar-day-name");
  const fullDateElem = document.getElementById("calendar-full-date");

  const weekdayNames = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
  const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

  if (dayNameElem) {
    dayNameElem.textContent = isToday ? `Hoy (${weekdayNames[cur.getDay()]})` : weekdayNames[cur.getDay()];
  }
  if (fullDateElem) {
    fullDateElem.textContent = `${cur.getDate()} de ${monthNames[cur.getMonth()]}`;
  }

  const todayBtn = document.getElementById("btn-today");
  if (todayBtn) {
    todayBtn.classList.toggle("active-today", isToday);
  }
}

async function fetchUsersAndStatus() {
  try {
    const res = await fetch("/api/users");
    const users = await res.json();
    state.usersList = users;
    
    if (users.length >= 2) {
      document.getElementById("user-1-name").textContent = users[0].display_name;
      document.getElementById("user-2-name").textContent = users[1].display_name;
    }

    await fetchStatusAndRefresh();
  } catch (err) {
    console.error("Error fetching users:", err);
  }
}

function switchUser(userId) {
  state.currentUser = userId;
  document.getElementById("user-pill-1").classList.toggle("active", userId === 1);
  document.getElementById("user-pill-2").classList.toggle("active", userId === 2);
  fetchStatusAndRefresh();
}

async function fetchStatusAndRefresh() {
  try {
    renderDateDisplay();
    const res = await fetch(`/api/status?user_id=${state.currentUser}&date=${state.currentDate}&day=${state.currentDay}`);
    const data = await res.json();
    
    state.todayLog = data.log;
    state.streak = data.streak;
    state.partnerStatus = data.partner;
    state.maxDays = data.max_days;
    state.userInfo = data.user;
    state.selectedWordsPerDay = data.user ? data.user.words_per_day : 5;
    state.selectedSelectionMode = data.user ? data.user.selection_mode : 'progressive';
    state.preferredLevel = (data.user && data.user.preferred_level) ? data.user.preferred_level : (state.currentUser === 1 ? 'A1' : 'A2');
    state.selectedPreferredLevel = state.preferredLevel;

    if (!state.readingLevelSetByUser) {
      state.readingLevel = state.preferredLevel;
    }
    if (!state.listeningLevelSetByUser) {
      state.listeningLevel = state.preferredLevel;
    }

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
  const activeName = (state.userInfo && state.userInfo.display_name) ? state.userInfo.display_name : (state.currentUser === 1 ? 'Javier' : 'Compañero');
  const userLvl = state.preferredLevel || (state.currentUser === 1 ? 'A1' : 'A2');
  document.getElementById("active-user-greeting").textContent = `Entrenando como ${activeName} (${userLvl})`;

  // Update tabs label
  const wCount = state.userInfo ? state.userInfo.words_per_day : 5;
  document.getElementById("tab-label-vocab").textContent = `1. Vocabulario (${wCount})`;
  const countBadge = document.getElementById("vocab-count-badge");
  if (countBadge) countBadge.textContent = wCount;

  // Partner status
  if (state.partnerStatus) {
    const isToday = state.currentDate === getTodayDateString();
    const timeRef = isToday ? "hoy" : "en esta fecha";
    document.getElementById("partner-status-text").textContent = 
      `${state.partnerStatus.name} lleva ${state.partnerStatus.completed_count} de 5 tareas completadas ${timeRef}.`;
    
    if (state.currentUser === 1) {
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

/* --- SETTINGS MODAL --- */
function openSettingsModal() {
  if (state.userInfo) {
    document.getElementById("setting-display-name").value = state.userInfo.display_name || "";
    selectWordsPerDay(state.userInfo.words_per_day || 5);
    selectSelectionMode(state.userInfo.selection_mode || "progressive");
    selectPreferredLevel(state.userInfo.preferred_level || (state.currentUser === 1 ? 'A1' : 'A2'));
  }
  document.getElementById("settings-modal").style.display = "flex";
}

function closeSettingsModal() {
  document.getElementById("settings-modal").style.display = "none";
}

function selectWordsPerDay(num) {
  state.selectedWordsPerDay = num;
  document.querySelectorAll("#setting-words-per-day-pills .pill-opt").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.val) === num);
  });
}

function selectSelectionMode(mode) {
  state.selectedSelectionMode = mode;
  document.querySelectorAll("#setting-selection-mode-pills .pill-opt").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.val === mode);
  });
}

function selectPreferredLevel(lvl) {
  state.selectedPreferredLevel = lvl;
  document.querySelectorAll("#setting-preferred-level-pills .pill-opt").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.val === lvl);
  });
}

async function saveUserSettings() {
  const newName = (document.getElementById("setting-display-name").value || "").trim();
  try {
    const res = await fetch("/api/users/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser,
        display_name: newName,
        words_per_day: state.selectedWordsPerDay,
        selection_mode: state.selectedSelectionMode,
        preferred_level: state.selectedPreferredLevel
      })
    });
    const data = await res.json();
    if (data.success) {
      closeSettingsModal();
      state.readingLevelSetByUser = false;
      state.listeningLevelSetByUser = false;
      await fetchUsersAndStatus();
    }
  } catch (err) {
    console.error("Error saving settings:", err);
  }
}

/* --- PARTNER SUMMARY READ-ONLY MODAL --- */
function openPartnerSummaryModal() {
  const modal = document.getElementById("partner-summary-modal");
  const title = document.getElementById("partner-summary-modal-title");
  const body = document.getElementById("partner-summary-modal-body");

  const partnerName = state.partnerStatus ? state.partnerStatus.name : "Compañero";
  title.textContent = `Resumen Escrito de ${partnerName}`;

  if (!state.partnerStatus || !state.partnerStatus.tasks || !state.partnerStatus.tasks.reading_summary) {
    body.innerHTML = `
      <div class="empty-state" style="text-align: center; padding: 2rem;">
        <span style="font-size: 2.5rem; display: block; margin-bottom: 0.5rem;">⏳</span>
        <strong style="color: #FFF; font-size: 1.1rem;">Tu compañero aún no ha completado el resumen de hoy.</strong>
        <p style="color: var(--text-muted); margin-top: 0.5rem;">Cuando guarde y evalúe su texto con Gemini Flash, podrás leer su redacción y ver sus correcciones aquí.</p>
      </div>
    `;
  } else {
    const pTasks = state.partnerStatus.tasks;
    let feedbackHtml = "";
    if (pTasks.reading_feedback) {
      try {
        const fb = JSON.parse(pTasks.reading_feedback);
        feedbackHtml = `
          <div style="margin-top: 1.25rem; background: rgba(0,0,0,0.3); border-radius: var(--radius-sm); padding: 1rem; border: 1px solid var(--border-subtle);">
            <strong style="color: #38BDF8; font-size: 0.88rem;">Feedback de Gemini para ${partnerName}:</strong>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.35rem;">Nivel estimado: <span class="badge badge-accent">${fb.estimated_cefr || 'B1'}</span></p>
            <p style="color: #FEF08A; font-size: 0.85rem; margin-top: 0.5rem; font-style: italic;">"${fb.native_phrasing_tip || ''}"</p>
          </div>
        `;
      } catch (e) {}
    }

    body.innerHTML = `
      <div style="background: rgba(0,0,0,0.3); border-radius: var(--radius-md); padding: 1.25rem; border: 1px solid var(--border-subtle);">
        <p style="font-size: 1rem; line-height: 1.7; color: #F1F5F9; white-space: pre-wrap;">${pTasks.reading_summary}</p>
      </div>
      ${feedbackHtml}
    `;
  }

  modal.style.display = "flex";
}

function closePartnerSummaryModal() {
  document.getElementById("partner-summary-modal").style.display = "none";
}

function showCelebrationModal() {
  document.getElementById("celebration-modal").style.display = "flex";
}

function closeCelebrationModal() {
  document.getElementById("celebration-modal").style.display = "none";
}
