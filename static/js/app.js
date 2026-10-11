/**
 * DUOHUB - Global Application Controller (Busuu & Duo Edition)
 */

const state = {
  authUserId: null,
  authUser: null,
  isReadOnly: false,
  currentUser: 1,
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

function getStoredAuthUser() {
  try {
    const raw = localStorage.getItem('duohub_auth_user');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function isReadOnlyMode() {
  if (!state.authUserId) return true;
  return state.currentUser !== state.authUserId;
}

function showReadOnlyToast() {
  alert("⚠️ Modo Solo Lectura: Estás viendo el progreso de tu compañero. Para realizar tareas o guardar cambios, regresa a tu cuenta personal.");
}

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
  const stored = getStoredAuthUser();
  if (stored && stored.id) {
    state.authUserId = stored.id;
    state.authUser = stored;
    state.currentUser = stored.id;
    state.isReadOnly = false;
  }
  fetchUsersAndStatus();
});

const MIN_ALLOWED_DATE = "2026-10-05"; // Launch / Construction baseline date

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
    dateInput.min = MIN_ALLOWED_DATE;
    dateInput.value = state.currentDate;
  }

  // Calculate day index initially
  setDate(state.currentDate, false);
}

function openDatePicker() {
  const dateInput = document.getElementById("calendar-date-input");
  if (dateInput) {
    dateInput.min = MIN_ALLOWED_DATE;
    if (typeof dateInput.showPicker === 'function') {
      dateInput.showPicker();
    } else {
      dateInput.click();
    }
  }
}

function onDateInputChange(val) {
  if (val) {
    if (val < MIN_ALLOWED_DATE) val = MIN_ALLOWED_DATE;
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
  let targetDate = `${year}-${month}-${day}`;
  if (targetDate < MIN_ALLOWED_DATE) {
    targetDate = MIN_ALLOWED_DATE;
  }
  setDate(targetDate);
}

function setDate(dateStr, triggerRefresh = true) {
  if (dateStr < MIN_ALLOWED_DATE) {
    dateStr = MIN_ALLOWED_DATE;
  }
  state.currentDate = dateStr;
  const anchor = new Date(2026, 9, 1); // Baseline: Oct 1, 2026
  const parts = dateStr.split("-").map(Number);
  const cur = new Date(parts[0], parts[1] - 1, parts[2]);
  const diffDays = Math.round((cur - anchor) / (1000 * 60 * 60 * 24));
  state.currentDay = Math.max(1, diffDays + 1);

  const dateInput = document.getElementById("calendar-date-input");
  if (dateInput) {
    dateInput.min = MIN_ALLOWED_DATE;
    dateInput.value = dateStr;
  }

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

  const prevBtn = document.getElementById("btn-prev-day");
  if (prevBtn) {
    const isAtMin = state.currentDate <= MIN_ALLOWED_DATE;
    prevBtn.disabled = isAtMin;
    prevBtn.style.opacity = isAtMin ? "0.35" : "1";
    prevBtn.style.cursor = isAtMin ? "not-allowed" : "pointer";
  }
}

async function fetchUsersAndStatus() {
  try {
    const res = await fetch(`/api/users?date=${state.currentDate}`);
    const users = await res.json();
    state.usersList = users;
    
    // Check if authenticated user exists
    const stored = getStoredAuthUser();
    if (!stored || !users.some(u => u.id === stored.id)) {
      // Must log in first!
      openAuthModal('login', true);
      renderAuthQuickUsers(users);
      return;
    } else {
      state.authUserId = stored.id;
      state.authUser = stored;
      if (!state.currentUser) {
        state.currentUser = stored.id;
      }
      state.isReadOnly = (state.currentUser !== state.authUserId);
    }

    renderUserDropdownUI();
    renderAuthQuickUsers(users);
    await fetchStatusAndRefresh();
  } catch (err) {
    console.error("Error fetching users:", err);
  }
}

function renderAuthQuickUsers(users) {
  const container = document.getElementById("auth-quick-users");
  const listEl = document.getElementById("auth-quick-list");
  if (!container || !listEl) return;

  if (!users || users.length === 0) {
    container.style.display = "none";
    return;
  }

  container.style.display = "block";
  listEl.innerHTML = users.map(u => `
    <button type="button" class="auth-quick-user-btn" onclick="quickFillLogin('${escapeHtml(u.username)}')">
      <span class="auth-quick-avatar" style="background-color: ${u.avatar_color || '#0B72E7'};">
        ${escapeHtml(u.display_name ? u.display_name.charAt(0).toUpperCase() : '👤')}
      </span>
      <span>${escapeHtml(u.display_name)}</span>
    </button>
  `).join("");
}

function quickFillLogin(username) {
  const input = document.getElementById("login-username");
  const pinInput = document.getElementById("login-pin");
  if (input) input.value = username;
  if (pinInput) {
    pinInput.focus();
    pinInput.select();
  }
}

function renderUserDropdownUI() {
  if (!state.usersList || state.usersList.length === 0) return;

  const activeUser = state.usersList.find(u => u.id === state.currentUser) || state.usersList[0];
  const isViewingPartner = state.isReadOnly;

  // Update navbar trigger
  const nameEl = document.getElementById("header-user-name");
  const statsEl = document.getElementById("header-user-stats");
  const badgeEl = document.getElementById("header-avatar-badge");

  if (nameEl) {
    nameEl.textContent = isViewingPartner 
      ? `${activeUser.display_name} (👁️ Solo Lectura)` 
      : activeUser.display_name;
  }
  const compCount = (state.todayLog && state.todayLog.completed_count !== undefined) 
    ? state.todayLog.completed_count 
    : (activeUser.today_completed || 0);
  if (statsEl) statsEl.textContent = `${compCount}/5`;
  if (badgeEl) {
    badgeEl.textContent = activeUser.display_name ? activeUser.display_name.charAt(0).toUpperCase() : '👤';
    badgeEl.style.backgroundColor = isViewingPartner ? '#D97706' : (activeUser.avatar_color || 'var(--busuu-blue)');
  }

  // Inside dropdown
  const dropName = document.getElementById("dropdown-current-name");
  const dropLevel = document.getElementById("dropdown-current-level");
  if (dropName) {
    dropName.textContent = isViewingPartner 
      ? `${activeUser.display_name} (Modo Espectador)` 
      : activeUser.display_name;
  }
  if (dropLevel) dropLevel.textContent = `Nivel ${activeUser.preferred_level || 'A1'} · Meta: ${activeUser.words_per_day || 5} palabras/día`;

  // Render other group members list
  const usersListEl = document.getElementById("dropdown-users-list");
  if (usersListEl) {
    const otherUsers = state.usersList.filter(u => u.id !== state.currentUser);
    if (otherUsers.length === 0) {
      usersListEl.innerHTML = `
        <div style="font-size: 0.78rem; color: var(--text-muted); padding: 0.45rem 0.65rem; background: #F8FAFC; border-radius: var(--radius-sm);">
          No hay otros compañeros en este grupo aún.
        </div>
      `;
    } else {
      usersListEl.innerHTML = otherUsers.map(u => {
        const isMyAccount = state.authUserId && u.id === state.authUserId;
        return `
          <div class="dropdown-user-item" onclick="${isMyAccount ? 'exitReadOnlyMode()' : `viewPartnerAsReadOnly(${u.id})`}">
            <div class="dropdown-user-item-left">
              <span class="dropdown-user-dot" style="background-color: ${u.avatar_color || '#0B72E7'};"></span>
              <span class="dropdown-user-item-name">
                ${isMyAccount ? `🔙 Mi Cuenta (${escapeHtml(u.display_name)})` : `👁️ ${escapeHtml(u.display_name)}`}
              </span>
            </div>
            <span class="dropdown-user-item-stat">${u.today_completed || 0}/5</span>
          </div>
        `;
      }).join("");
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

function viewPartnerAsReadOnly(partnerId) {
  state.currentUser = partnerId;
  state.isReadOnly = (state.currentUser !== state.authUserId);
  
  const menu = document.getElementById("user-dropdown-menu");
  if (menu) menu.style.display = "none";

  state.readingLevelSetByUser = false;
  state.listeningLevelSetByUser = false;

  renderUserDropdownUI();
  fetchStatusAndRefresh();
}

function exitReadOnlyMode() {
  if (state.authUserId) {
    state.currentUser = state.authUserId;
    state.isReadOnly = false;
    state.readingLevelSetByUser = false;
    state.listeningLevelSetByUser = false;

    const menu = document.getElementById("user-dropdown-menu");
    if (menu) menu.style.display = "none";

    renderUserDropdownUI();
    fetchStatusAndRefresh();
  }
}

function selectUserFromDropdown(userId) {
  viewPartnerAsReadOnly(userId);
}

function switchUser(userId) {
  viewPartnerAsReadOnly(userId);
}

/* --- AUTH MODAL CONTROLLER (LOGIN & REGISTER) --- */
function openAuthModal(tab = 'login', forced = false) {
  const menu = document.getElementById("user-dropdown-menu");
  if (menu) menu.style.display = "none";

  const modal = document.getElementById("auth-modal");
  const closeBtn = document.getElementById("btn-close-auth-modal");
  if (closeBtn) {
    closeBtn.style.display = forced ? "none" : "block";
  }

  if (modal) {
    modal.style.display = "flex";
    switchAuthTab(tab);
  }
}

function closeAuthModal() {
  if (!state.authUserId) {
    alert("Por favor inicia sesión con tu cuenta o regístrate para comenzar a estudiar.");
    return;
  }
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
      state.authUserId = data.user.id;
      state.authUser = data.user;
      state.currentUser = data.user.id;
      state.isReadOnly = false;
      localStorage.setItem('duohub_auth_user', JSON.stringify(data.user));
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
      state.authUserId = data.user.id;
      state.authUser = data.user;
      state.currentUser = data.user.id;
      state.isReadOnly = false;
      localStorage.setItem('duohub_auth_user', JSON.stringify(data.user));
      localStorage.setItem('duohub_active_user_id', data.user.id);
      closeAuthModal();
      speakEnglish(`Welcome to EnglishHub, ${data.user.display_name}!`, 1.0);
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

async function logoutUser() {
  localStorage.removeItem('duohub_auth_user');
  state.authUserId = null;
  state.authUser = null;
  state.isReadOnly = false;
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (e) {}

  const menu = document.getElementById("user-dropdown-menu");
  if (menu) menu.style.display = "none";

  openAuthModal('login', true);
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
  const streakEl = document.getElementById("streak-count");
  if (streakEl) streakEl.textContent = state.streak;

  // Active user greeting (if present)
  const activeName = (state.userInfo && state.userInfo.display_name) ? state.userInfo.display_name : 'Estudiante';
  const userLvl = state.preferredLevel || 'A1';
  const greetingEl = document.getElementById("active-user-greeting");
  if (greetingEl) {
    greetingEl.textContent = state.isReadOnly 
      ? `👁️ Viendo progreso de ${activeName} (${userLvl}) · SOLO LECTURA`
      : `Entrenando como ${activeName} (${userLvl})`;
  }

  // Update tabs label
  const wCount = state.userInfo ? state.userInfo.words_per_day : 5;
  const tabLbl = document.getElementById("tab-label-vocab");
  if (tabLbl) tabLbl.textContent = "1. Vocabulary";
  const countBadge = document.getElementById("vocab-count-badge");
  if (countBadge) countBadge.textContent = wCount;

  // Partner status (if present)
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

  // Read-Only Inspector Banner Toggle
  const roBanner = document.getElementById("read-only-banner");
  if (roBanner) {
    if (state.isReadOnly) {
      roBanner.style.display = "block";
      const partnerName = (state.userInfo && state.userInfo.display_name) ? state.userInfo.display_name : "Compañero";
      const authName = (state.authUser && state.authUser.display_name) ? state.authUser.display_name : "Mi Cuenta";
      const pEl = document.getElementById("read-only-partner-name");
      const aEl = document.getElementById("read-only-auth-user-name");
      if (pEl) pEl.textContent = partnerName;
      if (aEl) aEl.textContent = authName;
    } else {
      roBanner.style.display = "none";
    }
  }

  // Apply visual locks to all interactive elements
  applyReadOnlyLocks(state.isReadOnly);

  // Render User Dropdown Pill
  renderUserDropdownUI();

  // Update Daily Progress Bar (slim bar under tabs)
  const count = (state.todayLog && state.todayLog.completed_count !== undefined) ? state.todayLog.completed_count : 0;
  const pct = Math.round((count / 5) * 100);
  const pb = document.getElementById("daily-progress-bar");
  if (pb) pb.style.width = `${pct}%`;
  const pt = document.getElementById("daily-progress-text");
  if (pt) pt.textContent = `${count}/5 Completado`;

  // Update navbar user stats pill
  const headerStats = document.getElementById("header-user-stats");
  if (headerStats) headerStats.textContent = `${count}/5`;

  // Update Pillar checkmarks
  const tLog = state.todayLog || {};
  const currentWords = window.currentDayWords || [];
  const hasIncompleteWords = currentWords.length > 0 && currentWords.some(w => (w.user_mastery || 1) < 5);
  const vocabDone = (tLog.vocab_done === 1) && !hasIncompleteWords;

  updatePillarBadge("vocab", vocabDone ? 1 : 0);
  updatePillarBadge("reading", tLog.reading_done);
  updatePillarBadge("listening", tLog.listening_done);
  updatePillarBadge("shadowing", tLog.shadowing_done);
  updatePillarBadge("speaking", tLog.speaking_done);

  // Update vocab status pill (Automated completion)
  if (typeof updateVocabStatusPill === "function") {
    updateVocabStatusPill();
  }

  // Check for 5/5 celebration
  if (count === 5 && !state.isReadOnly && !sessionStorage.getItem(`celebrated_day_${state.currentDay}_u_${state.currentUser}`)) {
    sessionStorage.setItem(`celebrated_day_${state.currentDay}_u_${state.currentUser}`, "true");
    showCelebrationModal();
  }
}

function applyReadOnlyLocks(isReadOnly) {
  // Toggle global class on body
  document.body.classList.toggle("read-only-mode", isReadOnly);

  // 1. Vocabulary
  document.querySelectorAll(".sentence-textarea").forEach(tx => {
    tx.readOnly = isReadOnly;
  });
  document.querySelectorAll(".btn-save-sentence").forEach(btn => {
    btn.disabled = isReadOnly;
  });

  // 2. Reading
  const transTextarea = document.getElementById("translation-textarea");
  if (transTextarea) transTextarea.readOnly = isReadOnly;
  const summaryTextarea = document.getElementById("summary-textarea");
  if (summaryTextarea) summaryTextarea.readOnly = isReadOnly;
  const evalTransBtn = document.getElementById("btn-evaluate-translation");
  if (evalTransBtn) evalTransBtn.disabled = isReadOnly;
  const evalSummBtn = document.getElementById("btn-evaluate-summary");
  if (evalSummBtn) evalSummBtn.disabled = isReadOnly;
  const timerToggle = document.getElementById("btn-timer-toggle");
  if (timerToggle) timerToggle.disabled = isReadOnly;
  const timerReset = document.getElementById("btn-timer-reset");
  if (timerReset) timerReset.disabled = isReadOnly;

  // 3. Listening
  const dictInp = document.getElementById("listening-dictation-input");
  if (dictInp) dictInp.readOnly = isReadOnly;
  const verifyBtn = document.getElementById("btn-verify-listening");
  if (verifyBtn) verifyBtn.disabled = isReadOnly;
  const stopwatchToggle = document.getElementById("btn-stopwatch-toggle");
  if (stopwatchToggle) stopwatchToggle.disabled = isReadOnly;

  // 4. Shadowing
  const recMicBtn = document.getElementById("btn-record-mic");
  if (recMicBtn) recMicBtn.disabled = isReadOnly;
  const auditShadBtn = document.getElementById("btn-audit-shadowing");
  if (auditShadBtn) auditShadBtn.disabled = isReadOnly;
  document.querySelectorAll('button[onclick*="markShadowingDone"]').forEach(b => {
    b.disabled = isReadOnly;
  });

  // 5. Speaking
  const recSpkBtn = document.getElementById("btn-record-speaking");
  if (recSpkBtn) recSpkBtn.disabled = isReadOnly;
  const auditSpkBtn = document.getElementById("btn-audit-speaking");
  if (auditSpkBtn) auditSpkBtn.disabled = isReadOnly;
  const compSpkBtn = document.getElementById("btn-complete-speaking");
  if (compSpkBtn) compSpkBtn.disabled = isReadOnly;
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
  setTimeout(() => applyReadOnlyLocks(state.isReadOnly), 50);
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

/* --- USER PROFILE SETTINGS MODAL --- */
function openSettingsModal() {
  if (isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  const user = state.usersList.find(u => u.id === state.currentUser) || state.userInfo;
  if (user) {
    const nameInput = document.getElementById("setting-display-name");
    const pinInput = document.getElementById("setting-pin");
    if (nameInput) nameInput.value = user.display_name || "";
    if (pinInput) pinInput.value = user.pin || "1234";
    selectPreferredLevel(user.preferred_level || 'A1');
  }
  document.getElementById("settings-modal").style.display = "flex";
}

function closeSettingsModal() {
  document.getElementById("settings-modal").style.display = "none";
}

function selectPreferredLevel(lvl) {
  state.selectedPreferredLevel = lvl;
  document.querySelectorAll("#setting-preferred-level-pills .pill-opt").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.val === lvl);
  });
}

async function saveUserSettings() {
  if (isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  const newName = (document.getElementById("setting-display-name").value || "").trim();
  const newPin = (document.getElementById("setting-pin").value || "1234").trim();

  if (!newName) {
    alert("Por favor ingresa un nombre para tu perfil.");
    return;
  }

  try {
    const res = await fetch("/api/users/profile", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-Auth-User-Id": state.authUserId ? String(state.authUserId) : ""
      },
      body: JSON.stringify({
        user_id: state.currentUser,
        display_name: newName,
        pin: newPin,
        preferred_level: state.selectedPreferredLevel
      })
    });
    const data = await res.json();
    if (data.success) {
      closeSettingsModal();
      if (state.authUser) {
        state.authUser.display_name = newName;
        state.authUser.preferred_level = state.selectedPreferredLevel;
        localStorage.setItem('duohub_auth_user', JSON.stringify(state.authUser));
      }
      state.readingLevelSetByUser = false;
      state.listeningLevelSetByUser = false;
      await fetchUsersAndStatus();
    } else {
      alert(data.error || "Error al guardar perfil.");
    }
  } catch (err) {
    console.error("Error saving profile settings:", err);
  }
}

/* --- VOCABULARY DEDICATED SETTINGS MODAL --- */
function openVocabSettingsModal() {
  if (isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  const user = state.usersList.find(u => u.id === state.currentUser) || state.userInfo;
  if (user) {
    selectVocabWordsPerDay(user.words_per_day || 5);
    selectVocabSelectionMode(user.selection_mode || "progressive");
  }
  document.getElementById("vocab-settings-modal").style.display = "flex";
}

function closeVocabSettingsModal() {
  document.getElementById("vocab-settings-modal").style.display = "none";
}

function selectVocabWordsPerDay(num) {
  state.selectedWordsPerDay = num;
  document.querySelectorAll("#vocab-words-per-day-pills .pill-opt").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.val) === num);
  });
}

function selectVocabSelectionMode(mode) {
  state.selectedSelectionMode = mode;
  document.querySelectorAll("#vocab-selection-mode-pills .pill-opt").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.val === mode);
  });
}

async function saveVocabSettings() {
  if (isReadOnlyMode()) {
    showReadOnlyToast();
    return;
  }
  try {
    const res = await fetch("/api/users/profile", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-Auth-User-Id": state.authUserId ? String(state.authUserId) : ""
      },
      body: JSON.stringify({
        user_id: state.currentUser,
        words_per_day: state.selectedWordsPerDay,
        selection_mode: state.selectedSelectionMode
      })
    });
    const data = await res.json();
    if (data.success) {
      closeVocabSettingsModal();
      await fetchUsersAndStatus();
      if (typeof loadVocabData === 'function') {
        loadVocabData(state.currentDay);
      }
    } else {
      alert(data.error || "Error al guardar configuración de vocabulario.");
    }
  } catch (err) {
    console.error("Error saving vocab settings:", err);
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
        <p style="color: var(--text-muted); margin-top: 0.5rem;">Cuando guarde y evalúe su texto con IA, podrás leer su redacción y ver sus correcciones aquí.</p>
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
