// metrics.js — computes all 10 features from raw typing event arrays
// All time values kept in milliseconds to match model training data

import { mean, stddev, round } from "./utils.js";

const PAUSE_THRESHOLD_MS = 500; // gap > 500ms counts as a pause

/**
 * @param {object} state - raw arrays collected by typing.js
 * state.holdTimes       : ms each key was held down
 * state.keyDownTimes    : timestamps of each keydown event
 * state.wordTimestamps  : timestamp when each word was completed
 * state.backspaceCount  : integer
 * state.totalKeys       : integer (all keydown events)
 * state.typedText       : final string the user typed
 * state.originalText    : the paragraph string
 * state.startTime       : timestamp of first keydown
 * state.endTime         : timestamp of finish click
 */
export function computeFeatures(state) {
  const {
    holdTimes,
    keyDownTimes,
    wordTimestamps,
    backspaceCount,
    totalKeys,
    typedText,
    originalText,
    startTime,
    endTime,
  } = state;

  const elapsedMin = (endTime - startTime) / 60000;
  const wordCount = typedText.trim().split(/\s+/).filter(Boolean).length;

  // 1. WPM
  const wpm = elapsedMin > 0 ? round(wordCount / elapsedMin) : 0;

  // 2. WPM variance — variance across per-word WPM values
  let wpmVariance = 0;
  if (wordTimestamps.length > 1) {
    const perWordWpms = [];
    for (let i = 1; i < wordTimestamps.length; i++) {
      const dt = (wordTimestamps[i] - wordTimestamps[i - 1]) / 60000;
      if (dt > 0) perWordWpms.push(1 / dt); // 1 word over dt minutes
    }
    const m = mean(perWordWpms);
    const variance =
      perWordWpms.reduce((s, v) => s + (v - m) ** 2, 0) /
      Math.max(1, perWordWpms.length);
    wpmVariance = round(variance);
  }

  // 3. Avg key hold time (ms)
  const avgKeyHoldTime = round(mean(holdTimes) || 0);

  // 4. Avg inter-key delay (ms) — gaps between consecutive keydowns
  const interKeyDelays = [];
  for (let i = 1; i < keyDownTimes.length; i++) {
    const gap = keyDownTimes[i] - keyDownTimes[i - 1];
    if (gap > 0 && gap < 5000) interKeyDelays.push(gap); // ignore huge gaps
  }
  const avgInterKeyDelay = round(mean(interKeyDelays));

  // 5. Backspace rate
  const backspaceRate = totalKeys > 0 ? round(backspaceCount / totalKeys, 4) : 0;

  // 6. Error rate — true typing errors made during the session
  const errors = state.accumulatedErrors || 0;
  // Divide against totalKeys to keep 0 to 1 domain consistent with ML baseline
  const errorRate = totalKeys > 0 ? round(errors / totalKeys, 4) : 0;

  // 7. Avg pause time (ms) — mean of gaps > PAUSE_THRESHOLD
  const pauseGaps = interKeyDelays.filter((g) => g > PAUSE_THRESHOLD_MS);
  const avgPauseTime = round(mean(pauseGaps) || 0);

  // 8. Pause variability — std dev of pause gaps, normalized 0-1
  const pauseStd = stddev(pauseGaps);
  const pauseVariability =
    pauseGaps.length > 1
      ? round(Math.min(1, pauseStd / (mean(pauseGaps) + 1)), 4)
      : 0;

  // 9. Typing consistency score (0-1)
  // Built from per-second WPM: 1 - (stddev / mean), clipped 0-1
  const perSecondWpms = _getPerSecondWpms(keyDownTimes, startTime, endTime);
  let typingConsistencyScore = 0;
  if (perSecondWpms.length > 1) {
    const m = mean(perSecondWpms);
    const s = stddev(perSecondWpms);
    typingConsistencyScore = m > 0 ? round(Math.max(0, Math.min(1, 1 - s / m)), 4) : 0;
  }

  // 10. Burstiness score (0-1) — std/mean of inter-key delays, clipped 0-1
  const burstinessScore =
    avgInterKeyDelay > 0
      ? round(Math.min(1, stddev(interKeyDelays) / (avgInterKeyDelay + 1)), 4)
      : 0;

  return {
    wpm,
    wpm_variance: wpmVariance,
    avg_key_hold_time: avgKeyHoldTime,
    avg_inter_key_delay: avgInterKeyDelay,
    backspace_rate: backspaceRate,
    error_rate: errorRate,
    avg_pause_time: avgPauseTime,
    pause_variability: pauseVariability,
    typing_consistency_score: typingConsistencyScore,
    burstiness_score: burstinessScore,
  };
}

function _getPerSecondWpms(keyDownTimes, startTime, endTime) {
  const totalSecs = Math.ceil((endTime - startTime) / 1000);
  const result = [];
  for (let sec = 0; sec < totalSecs; sec++) {
    const lo = startTime + sec * 1000;
    const hi = lo + 1000;
    const keysInSec = keyDownTimes.filter((t) => t >= lo && t < hi).length;
    // rough wpm: keys in second / 5 chars per word * 60 seconds
    result.push((keysInSec / 5) * 60);
  }
  return result.filter((v) => v > 0);
}

// UI-only stats (not sent to backend)
export function computeDisplayStats(state) {
  const { backspaceCount, totalKeys, holdTimes, keyDownTimes } = state;
  const interKeyDelays = [];
  for (let i = 1; i < keyDownTimes.length; i++) {
    const gap = keyDownTimes[i] - keyDownTimes[i - 1];
    if (gap > 0 && gap < 5000) interKeyDelays.push(gap);
  }
  const pauseCount = interKeyDelays.filter((g) => g > 500).length;

  return {
    backspaceCount,
    totalKeys,
    avgHoldMs: round(mean(holdTimes) || 0),
    pauseCount,
  };
}