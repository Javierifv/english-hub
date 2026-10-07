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
    const res = await fetch(`/api/users?date=${state.currentDate}`);
    const users = await res.json();
    state.usersList = users;
    
    // Ensure current user is valid
    const savedUserId = parseInt(localStorage.getItem('duohub_active_user_id'));
    if (savedUserId && users.some(u => u.id === savedUserId)) {
      state.currentUser = savedUserId;
    } else if (users.length > 0 && !users.some(u => u.id === state.currentUser)) {
      state.currentUser = users[0].id;
      localStorage.setItem('duohub_active_user_id', state.currentUser);
    }

    renderUserDropdownUI();
    await fetchStatusAndRefresh();
  } catch (err) {
    console.error("Error fetching users:", err);
  }
}

function renderUserDropdownUI() {
  if (!state.usersList || state.usersList.length === 0) return;

  const activeUser = state.usersList.find(u => u.id === state.currentUser) || state.usersList[0];
  
  // Update navbar trigger
  const nameEl = document.getElementById("header-user-name");
  const statsEl = document.getElementById("header-user-stats");
  const badgeEl = document.getElementById("header-avatar-badge");

  if (nameEl) nameEl.textContent = activeUser.display_name;
  const compCount = (state.todayLog && state.todayLog.completed_count !== undefined) 
    ? state.todayLog.completed_count 
    : (activeUser.today_completed || 0);
  if (statsEl) statsEl.textContent = `${compCount}/5`;
  if (badgeEl) {
    badgeEl.textContent = activeUser.display_name ? activeUser.display_name.charAt(0).toUpperCase() : '👤';
    badgeEl.style.backgroundColor = activeUser.avatar_color || 'var(--busuu-blue)';
  }

  // Inside dropdown
  const dropName = document.getElementById("dropdown-current-name");
  const dropLevel = document.getElementById("dropdown-current-level");
  if (dropName) dropName.textContent = activeUser.display_name;
  if (dropLevel) dropLevel.textContent = `Nivel ${activeUser.preferred_level || 'A1'} · Meta: ${activeUser.words_per_day || 5} palabras/día`;

  // Render other group members list
  const usersListEl = document.getElementById("dropdown-users-list");
  if (usersListEl) {
    const otherUsers = state.usersList.filter(u => u.id !== state.currentUser);
    if (otherUsers.length === 0) {
      usersListEl.innerHTML = `
        <div style="font-size: 0.78rem; color: var(--text-muted); padding: 0.45rem 0.65rem; background: #F8FAFC; border-radius: var(--radius-sm);">
          No hay otros compañeros en este grupo aún. ¡Usa el botón de abajo para registrar uno!
        </div>
      `;
    } else {
      usersListEl.innerHTML = otherUsers.map(u => `
        <div class="dropdown-user-item" onclick="selectUserFromDropdown(${u.id})">
          <div class="dropdown-user-item-left">
            <span class="dropdown-user-dot" style="background-color: ${u.avatar_color || '#0B72E7'};"></span>
            <span class="dropdown-user-item-name">${escapeHtml(u.display_name)}</span>
          </div>
          <span class="dropdown-user-item-stat">${u.today_completed || 0}/5</span>
        </div>
      `).join("");
    }
  }
}

function toggleUserDropdown() {
  const menu = document.getElementById("user-dropdown-menu");
  if (!menu) return;
  const isHidden = (menu.style.display === "none" || !menu.style.display);
  menu.style.display = isHidden ? "block" : "none";
}

// Close dropdown on outside click
document.addEventListener("click", (e) => {
  const wrap = document.getElementById("user-profile-menu-wrap");
  const menu = document.getElementById("user-dropdown-menu");
  if (wrap && menu && !wrap.contains(e.target)) {
    menu.style.display = "none";
  }
});

function selectUserFromDropdown(userId) {
  state.currentUser = userId;
  localStorage.setItem('duohub_active_user_id', userId);
  
  const menu = document.getElementById("user-dropdown-menu");
  if (menu) menu.style.display = "none";

  renderUserDropdownUI();
  fetchStatusAndRefresh();
}

function switchUser(userId) {
  selectUserFromDropdown(userId);
}

/* --- AUTH MODAL CONTROLLER (LOGIN & REGISTER) --- */
function openAuthModal(tab = 'login') {
  const menu = document.getElementById("user-dropdown-menu");
  if (menu) menu.style.display = "none";

  const modal = document.getElementById("auth-modal");
  if (modal) {
    modal.style.display = "flex";
    switchAuthTab(tab);
  }
}

function closeAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (modal) modal.style.display = "none";
  
  const errLogin = document.getElementById("login-error-msg");
  const errReg = document.getElementById("register-error-msg");
  if (errLogin) errLogin.style.display = "none";
  if (errReg) errReg.style.display = "none";
}

function switchAuthTab(tab) {
  const btnLogin = document.getElementById("auth-tab-btn-login");
  const btnReg = document.getElementById("auth-tab-btn-register");
  const viewLogin = document.getElementById("auth-view-login");
  const viewReg = document.getElementById("auth-view-register");

  if (tab === 'login') {
    if (btnLogin) btnLogin.classList.add("active");
    if (btnReg) btnReg.classList.remove("active");
    if (viewLogin) viewLogin.style.display = "block";
    if (viewReg) viewReg.style.display = "none";
    setTimeout(() => document.getElementById("login-username")?.focus(), 100);
  } else {
    if (btnLogin) btnLogin.classList.remove("active");
    if (btnReg) btnReg.classList.add("active");
    if (viewLogin) viewLogin.style.display = "none";
    if (viewReg) viewReg.style.display = "block";
    setTimeout(() => document.getElementById("reg-fullname")?.focus(), 100);
  }
}

async function submitLogin() {
  const usernameInput = document.getElementById("login-username");
  const pinInput = document.getElementById("login-pin");
  const errBox = document.getElementById("login-error-msg");

  const username = (usernameInput?.value || "").trim();
  const pin = (pinInput?.value || "").trim();

  if (!username) {
    if (errBox) {
      errBox.textContent = "Por favor ingresa tu nombre de usuario.";
      errBox.style.display = "block";
    }
    return;
  }

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, pin })
    });
    const data = await res.json();

    if (data.success && data.user) {
      state.currentUser = data.user.id;
      localStorage.setItem('duohub_active_user_id', data.user.id);
      closeAuthModal();
      speakEnglish(`Welcome back, ${data.user.display_name}!`, 1.0);
      await fetchUsersAndStatus();
    } else {
      if (errBox) {
        errBox.textContent = data.error || "Error al iniciar sesión.";
        errBox.style.display = "block";
      }
    }
  } catch (err) {
    console.error("Error logging in:", err);
    if (errBox) {
      errBox.textContent = "Error de conexión con el servidor.";
      errBox.style.display = "block";
    }
  }
}

async function submitRegister() {
  const nameInput = document.getElementById("reg-fullname");
  const userInput = document.getElementById("reg-username");
  const pinInput = document.getElementById("reg-pin");
  const lvlInput = document.getElementById("reg-level");
  const wordsInput = document.getElementById("reg-words-count");
  const errBox = document.getElementById("register-error-msg");

  const displayName = (nameInput?.value || "").trim();
  const username = (userInput?.value || "").trim();
  const pin = (pinInput?.value || "1234").trim();
  const preferredLevel = lvlInput?.value || "A1";
  const wordsPerDay = parseInt(wordsInput?.value || "5");

  if (!displayName || !username) {
    if (errBox) {
      errBox.textContent = "Por favor completa el nombre completo y el nombre de usuario.";
      errBox.style.display = "block";
    }
    return;
  }

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        display_name: displayName,
        username: username,
        pin: pin,
        preferred_level: preferredLevel,
        words_per_day: wordsPerDay
      })
    });
    const data = await res.json();

    if (data.success && data.user) {
      state.currentUser = data.user.id;
      localStorage.setItem('duohub_active_user_id', data.user.id);
      closeAuthModal();
      speakEnglish(`Welcome to DuoHub, ${data.user.display_name}!`, 1.0);
      alert(`🎉 ¡Cuenta creada con éxito! Bienvenido al grupo de estudio, ${data.user.display_name}.`);
      await fetchUsersAndStatus();
    } else {
      if (errBox) {
        errBox.textContent = data.error || "Error al registrar usuario.";
        errBox.style.display = "block";
      }
    }
  } catch (err) {
    console.error("Error registering user:", err);
    if (errBox) {
      errBox.textContent = "Error de conexión con el servidor.";
      errBox.style.display = "block";
    }
  }
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
  const activeName = (state.userInfo && state.userInfo.display_name) ? state.userInfo.display_name : 'Estudiante';
  const userLvl = state.preferredLevel || 'A1';
  document.getElementById("active-user-greeting").textContent = `Entrenando como ${activeName} (${userLvl})`;

  // Update tabs label
  const wCount = state.userInfo ? state.userInfo.words_per_day : 5;
  document.getElementById("tab-label-vocab").textContent = `1. Vocabulario (${wCount})`;
  const countBadge = document.getElementById("vocab-count-badge");
  if (countBadge) countBadge.textContent = wCount;

  // Partner status
  const partnerElem = document.getElementById("partner-status-text");
  if (partnerElem) {
    if (state.partnerStatus && state.partnerStatus.name) {
      const isToday = state.currentDate === getTodayDateString();
      const timeRef = isToday ? "hoy" : "en esta fecha";
      partnerElem.textContent = `${state.partnerStatus.name} lleva ${state.partnerStatus.completed_count} de 5 tareas completadas ${timeRef}.`;
    } else {
      partnerElem.textContent = "Estudiando en grupo. Puedes invitar a otros compañeros registrándolos arriba.";
    }
  }

  // Render User Dropdown Pill
  renderUserDropdownUI();

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
