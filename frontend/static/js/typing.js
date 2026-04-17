// typing.js — game state, keydown/keyup events, timer, live WPM + accuracy

import { computeFeatures, computeDisplayStats } from "./metrics.js";
import { predictMood, startSession, fetchParagraph } from "./api.js";
import { getSuggestions, MOOD_EMOJI, formatTime } from "./utils.js";

// ── State ────────────────────────────────────────────────────────────────────

const state = {
  originalText: "",
  typedText: "",
  startTime: null,
  endTime: null,
  holdTimes: [],
  keyDownTimes: [],
  keyDownMap: {},      // key -> timestamp of most recent keydown
  wordTimestamps: [],
  backspaceCount: 0,
  totalKeys: 0,
  timerInterval: null,
  liveWpms: [],        // one entry per second for chart
  liveAccuracies: [],
  chartInterval: null,
  autoFinishInterval: null,
  started: false,
  finished: false,
  accumulatedErrors: 0,
  sessionId: null,
  isSubmitting: false,
  correctionOffset: 0,
  lastPauseStart: null,
  isWaitingForResume: false,
};

// ── DOM refs ─────────────────────────────────────────────────────────────────

const paragraphEl   = document.getElementById("paragraph");
const inputEl       = document.getElementById("typing-input");
const startBtn      = document.getElementById("start-btn");
const finishBtn     = document.getElementById("finish-btn");
const resetBtn      = document.getElementById("reset-btn");
const timerEl       = document.getElementById("timer");
const liveWpmEl     = document.getElementById("live-wpm");
const liveAccEl     = document.getElementById("live-acc");
const resultSection = document.getElementById("result-section");
const moodEl        = document.getElementById("mood-label");
const confidenceEl  = document.getElementById("confidence");
const suggestionsEl = document.getElementById("suggestions");
const statsEl       = document.getElementById("stats-grid");
const errorMsgEl    = document.getElementById("error-msg");

// ── Chart (Chart.js) ─────────────────────────────────────────────────────────

let chart = null;

function initChart() {
  const ctx = document.getElementById("typing-chart").getContext("2d");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "WPM",
          data: [],
          borderColor: "#6ee7b7",
          backgroundColor: "rgba(110,231,183,0.08)",
          tension: 0.4,
          pointRadius: 2,
          yAxisID: "y",
        },
        {
          label: "Accuracy %",
          data: [],
          borderColor: "#93c5fd",
          backgroundColor: "rgba(147,197,253,0.08)",
          tension: 0.4,
          pointRadius: 2,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 200 },
      plugins: { legend: { labels: { color: "#94a3b8", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#64748b" }, grid: { color: "#1e293b" } },
        y: {
          type: "linear",
          position: "left",
          ticks: { color: "#6ee7b7" },
          grid: { color: "#1e293b" },
          title: { display: true, text: "WPM", color: "#6ee7b7" },
        },
        y1: {
          type: "linear",
          position: "right",
          min: 0,
          max: 100,
          ticks: { color: "#93c5fd" },
          grid: { drawOnChartArea: false },
          title: { display: true, text: "Accuracy %", color: "#93c5fd" },
        },
      },
    },
  });
}

function updateChart() {
  if (!chart || !state.started || state.finished) return;

  const now = Date.now();
  const elapsedSec = Math.floor((now - state.startTime) / 1000);
  const elapsedMin = (now - state.startTime) / 60000;
  const wordCount = state.typedText.trim().split(/\s+/).filter(Boolean).length;
  const wpm = elapsedMin > 0 ? Math.round(wordCount / elapsedMin) : 0;

  // accuracy — match the true accumulated errors
  const total = state.totalKeys;
  const errors = state.accumulatedErrors;
  const acc = total > 0 ? Math.round((1 - errors / total) * 100) : 100;

  state.liveWpms.push(wpm);
  state.liveAccuracies.push(acc);

  chart.data.labels.push(`${elapsedSec}s`);
  chart.data.datasets[0].data.push(wpm);
  chart.data.datasets[1].data.push(acc);
  chart.update("none");

  liveWpmEl.textContent = wpm;
  liveAccEl.textContent = acc + "%";
}

// ── Highlighted paragraph rendering ─────────────────────────────────────────

function renderParagraph() {
  const typed = state.typedText;
  const orig = state.originalText;
  let html = "";
  for (let i = 0; i < orig.length; i++) {
    if (i < typed.length) {
      const cls = typed[i] === orig[i] ? "char-correct" : "char-wrong";
      html += `<span class="${cls}">${orig[i]}</span>`;
    } else if (i === typed.length) {
      html += `<span class="char-cursor">${orig[i]}</span>`;
    } else {
      html += `<span class="char-pending">${orig[i]}</span>`;
    }
  }
  paragraphEl.innerHTML = html;
}

// ── Timer ────────────────────────────────────────────────────────────────────

function startTimer() {
  state.timerInterval = setInterval(() => {
    if (!state.startTime) return;
    const elapsed = Date.now() - state.startTime;
    const remaining = Math.max(0, ONE_MINUTE_MS - elapsed);
    
    timerEl.textContent = formatTime(remaining) + " left";
    
    updateFinishButton();

    // Turn red in last 10 seconds
    timerEl.style.color = remaining <= 10000 ? "var(--danger)" : "";
  }, 500);
}

function updateFinishButton() {
  if (state.finished || !state.started) return;
  
  const now = Date.now();
  const elapsed = now - state.startTime;
  const MIN_REQ_MS = 45000;
  
  const isTimeMet = elapsed >= MIN_REQ_MS;
  const isContentDone = state.typedText.length >= state.originalText.length;

  if (isTimeMet || isContentDone) {
    if (finishBtn.disabled) {
      finishBtn.disabled = false;
      errorMsgEl.textContent = "Stable data collected. You can finish whenever you're ready.";
      errorMsgEl.style.color = "#6ee7b7";
      console.log(`[SECURITY] Finish button enabled. (TimeMet: ${isTimeMet}, ContentDone: ${isContentDone})`);
    }
  } else {
    if (!finishBtn.disabled) finishBtn.disabled = true;
    const wait = Math.ceil((MIN_REQ_MS - elapsed) / 1000);
    errorMsgEl.textContent = `Gathering behavioral data... ${wait}s remaining.`;
    errorMsgEl.style.color = "#94a3b8";
  }
}

// ── Keyboard events ──────────────────────────────────────────────────────────

const ONE_MINUTE_MS = 60000;

function checkAutoFinish() {
  if (state.finished) return;
  // Auto-finish on 1 minute
  if (Date.now() - state.startTime >= ONE_MINUTE_MS) {
    onFinish();
    return;
  }
  // Auto-finish when full paragraph is typed
  if (state.typedText.length >= state.originalText.length) {
    onFinish();
  }
}

function onKeyDown(e) {
  if (state.finished) return;

  const realNow = Date.now();
  
  // Virtual Clock Correction
  if (state.isWaitingForResume) {
    const gap = realNow - state.lastPauseStart;
    state.correctionOffset += gap;
    state.isWaitingForResume = false;
    console.log(`[SECURITY] Virtual Clock Resumed. Corrected for ${gap}ms gap.`);
  }

  const now = realNow - state.correctionOffset;

  // Start on first keystroke
  if (!state.started) {
    state.started = true;
    state.startTime = now;
    startTimer();
    state.chartInterval = setInterval(updateChart, 1000);
    state.autoFinishInterval = setInterval(checkAutoFinish, 500);
    startBtn.disabled = true; // Lockdown start button once typing begins
    // Note: finishBtn remains disabled by updateFinishButton until thresholds met
  }

  state.totalKeys++;
  state.keyDownTimes.push(now);
  state.keyDownMap[e.code] = now;

  if (e.key === "Backspace") state.backspaceCount++;
}

function onKeyUp(e) {
  if (!state.started || state.finished) return;
  const now = Date.now() - state.correctionOffset;
  const downTime = state.keyDownMap[e.code];
  if (downTime) {
    const hold = now - downTime;
    if (hold > 0 && hold < 2000) state.holdTimes.push(hold);
    delete state.keyDownMap[e.code];
  }
}

function onInput(e) {
  if (state.finished) return;
  
  const newText = inputEl.value;
  const oldText = state.typedText;

  // Track raw errors (even if they backspace and correct later)
  if (newText.length > oldText.length) {
    for (let i = oldText.length; i < newText.length; i++) {
      if (newText[i] !== state.originalText[i]) {
        state.accumulatedErrors++;
      }
    }
  }

  state.typedText = newText;

  // Track word completions (space after a word)
  const words = state.typedText.split(" ");
  if (words.length > state.wordTimestamps.length) {
    state.wordTimestamps.push(Date.now() - state.correctionOffset);
  }

  updateFinishButton();
  renderParagraph();
}

function preventPasteAction(e) {
  e.preventDefault();
  const type = e.type;
  console.warn(`[SECURITY] Blocked unexpected data intervention: ${type} attempt.`);
  errorMsgEl.textContent = "⚠ Manual typing required. Copy-paste and drag-drop are disabled.";
  errorMsgEl.style.color = "var(--danger)";
}

// ── Finish ───────────────────────────────────────────────────────────────────

async function onFinish() {
  if (!state.started || state.finished || state.isSubmitting) return;
  
  // Non-destructive submission lock
  state.isSubmitting = true;
  const virtualEndTime = Date.now() - state.correctionOffset;
  
  // Cache state for current submission attempt
  const currentText = state.typedText;
  const currentOriginal = state.originalText;

  errorMsgEl.textContent = "Analyzing patterns... (You can keep typing)";
  errorMsgEl.style.color = "var(--primary)";

  const features = computeFeatures({ ...state, endTime: virtualEndTime });
  const display = computeDisplayStats({ ...state, endTime: virtualEndTime });

  const metadata = {
    session_id: state.sessionId,
    total_keys: state.totalKeys,
    text_length: currentOriginal.length
  };

  try {
    const result = await predictMood(features, metadata);
    
    if (result.stored === false) {
      // Rejection (Low Trust) - NON-BLOCKING
      console.warn("[SECURITY] Attempt rejected. Continuing session...", result.warning);
      errorMsgEl.textContent = `⚠ ${result.warning || "Not enough data yet. Continue typing!"}`;
      errorMsgEl.style.color = "var(--danger)";
      
      // Trigger Time Freeze
      state.lastPauseStart = Date.now();
      state.isWaitingForResume = true;
    } else {
      // SUCCESS - LOCK UI
      state.finished = true;
      state.endTime = virtualEndTime;
      
      clearInterval(state.timerInterval);
      clearInterval(state.chartInterval);
      clearInterval(state.autoFinishInterval);

      inputEl.disabled = true;
      finishBtn.disabled = true;
      
      console.log("[SECURITY] Session closed successfully.");
      renderStats(features, display);
      renderResult(result);
      errorMsgEl.textContent = "Analysis complete. Data stored safely.";
      errorMsgEl.style.color = "var(--success)";
    }
  } catch (err) {
    // 403, 429, 422 errors caught here
    console.error("[SECURITY] Submission failed.", err.message);
    
    if (err.message.includes("403") || err.message.toLowerCase().includes("session")) {
      errorMsgEl.textContent = "⚠ Session lost / Server restarted. Please click RESET.";
      // Visual cue: Pulsate reset button
      resetBtn.style.transform = "scale(1.1)";
      resetBtn.style.boxShadow = "0 0 15px var(--primary)";
      setTimeout(() => {
        resetBtn.style.transform = "";
        resetBtn.style.boxShadow = "";
      }, 1000);
    } else {
      errorMsgEl.textContent = `⚠ ${err.message}. Continue typing and click finish again.`;
    }
    
    errorMsgEl.style.color = "var(--danger)";
    
    // Trigger Time Freeze
    state.lastPauseStart = Date.now();
    state.isWaitingForResume = true;
  } finally {
    state.isSubmitting = false;
    resetBtn.disabled = false; // Recovery path: Always allow reset
  }
}

// ── Render results ───────────────────────────────────────────────────────────

function renderStats(features, display) {
  const items = [
    ["WPM", features.wpm],
    ["Accuracy", `${Math.round((1 - features.error_rate) * 100)}%`],
    ["Backspaces", display.backspaceCount],
    ["Total Keystrokes", display.totalKeys],
    ["Avg Key Hold", `${features.avg_key_hold_time} ms`],
    ["Avg Inter-Key Gap", `${features.avg_inter_key_delay} ms`],
    ["Pause Count", display.pauseCount],
    ["Avg Pause", `${features.avg_pause_time} ms`],
    ["Consistency", features.typing_consistency_score],
    ["Burstiness", features.burstiness_score],
  ];

  statsEl.innerHTML = items
    .map(
      ([label, val]) => `
      <div class="stat-card">
        <span class="stat-label">${label}</span>
        <span class="stat-value">${val}</span>
      </div>`
    )
    .join("");
}

function renderResult(result) {
  const { mood, confidence, driving_factors } = result;
  const emoji = MOOD_EMOJI[mood] || "🧠";
  const pct = Math.round(confidence * 100);

  moodEl.textContent = `${emoji} ${mood}`;
  moodEl.className = `mood-${mood.toLowerCase()}`;
  confidenceEl.textContent = `Model confidence: ${pct}%`;

  const drivingBlock = document.getElementById("driving-factors");
  if (driving_factors && driving_factors.length > 0) {
    drivingBlock.innerHTML = driving_factors
      .map(f => `<span class="driving-pill">⚡ ${f}</span>`)
      .join("");
  } else {
    drivingBlock.innerHTML = "";
  }

  const suggestions = getSuggestions(mood);
  suggestionsEl.innerHTML = suggestions
    .map((s) => `<li>${s}</li>`)
    .join("");

  resultSection.classList.remove("hidden");
  resultSection.scrollIntoView({ behavior: "smooth" });
}

// ── Reset ────────────────────────────────────────────────────────────────────

async function onReset() {
  clearInterval(state.timerInterval);
  clearInterval(state.chartInterval);
  clearInterval(state.autoFinishInterval);

  // Lockdown while reloading
  startBtn.disabled = true;
  resetBtn.disabled = true;
  errorMsgEl.textContent = "Preparing new session...";
  errorMsgEl.style.color = "var(--primary)";

  Object.assign(state, {
    originalText: "",
    typedText: "",
    startTime: null,
    endTime: null,
    holdTimes: [],
    keyDownTimes: [],
    keyDownMap: {},
    wordTimestamps: [],
    backspaceCount: 0,
    totalKeys: 0,
    timerInterval: null,
    liveWpms: [],
    liveAccuracies: [],
    chartInterval: null,
    autoFinishInterval: null,
    started: false,
    finished: false,
    accumulatedErrors: 0,
    sessionId: null,
    isSubmitting: false,
    correctionOffset: 0,
    lastPauseStart: null,
    isWaitingForResume: false,
  });

  inputEl.value = "";
  inputEl.disabled = true;
  finishBtn.disabled = true;
  timerEl.textContent = "0s";
  liveWpmEl.textContent = "0";
  liveAccEl.textContent = "100%";
  resultSection.classList.add("hidden");
  statsEl.innerHTML = "";

  try {
    // Atomically fetch new paragraph and session ID
    const [p, s] = await Promise.all([fetchParagraph(), startSession()]);
    state.originalText = p;
    state.sessionId = s;
    
    paragraphEl.dataset.original = state.originalText;
    renderParagraph();
    errorMsgEl.textContent = "Session ready. Click Start Typing.";
    errorMsgEl.style.color = "var(--success)";
    
    // Reset chart
    chart.data.labels = [];
    chart.data.datasets[0].data = [];
    chart.data.datasets[1].data = [];
    chart.update();
  } catch (err) {
    errorMsgEl.textContent = "Connection error. Please try clicking Reset again.";
    errorMsgEl.style.color = "var(--danger)";
  } finally {
    startBtn.disabled = false;
    resetBtn.disabled = false;
  }
}

// ── Start button ─────────────────────────────────────────────────────────────

async function onStart() {
  try {
    errorMsgEl.textContent = "Establishing session...";
    state.sessionId = await startSession();
    errorMsgEl.textContent = "Connected. Begin typing to start the analysis timer.";
    errorMsgEl.style.color = "var(--success)";
    
    inputEl.disabled = false;
    inputEl.focus();
    startBtn.disabled = true;
  } catch (err) {
    errorMsgEl.textContent = "Error: Blocked by server or connection failed.";
    errorMsgEl.style.color = "var(--danger)";
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

export function init(originalText) {
  state.originalText = originalText;
  paragraphEl.dataset.original = originalText;
  renderParagraph();
  initChart();

  startBtn.addEventListener("click", onStart);
  finishBtn.addEventListener("click", onFinish);
  resetBtn.addEventListener("click", onReset);
  inputEl.addEventListener("keydown", onKeyDown);
  inputEl.addEventListener("keyup", onKeyUp);
  inputEl.addEventListener("input", onInput);
  
  // Secure Anti-Cheat Lockdown
  inputEl.addEventListener("paste", preventPasteAction);
  inputEl.addEventListener("drop", preventPasteAction);
  inputEl.addEventListener("contextmenu", preventPasteAction);
}
