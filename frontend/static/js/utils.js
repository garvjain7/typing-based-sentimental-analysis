// utils.js — pure helper functions, no side effects

export function round(val, decimals = 2) {
  return Math.round(val * 10 ** decimals) / 10 ** decimals;
}

export function mean(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

export function stddev(arr) {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  const variance = arr.reduce((sum, v) => sum + (v - m) ** 2, 0) / arr.length;
  return Math.sqrt(variance);
}

export function formatTime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}

export const MOOD_SUGGESTIONS = {
  Happy: [
    "Great energy! Keep it up.",
    "Your typing flow is excellent today.",
    "You seem focused and relaxed — ideal state.",
  ],
  Neutral: [
    "Steady session. Try a short break to refresh.",
    "Consistent performance. Push a little more.",
    "You're in a balanced state — good baseline.",
  ],
  Stressed: [
    "Take a deep breath before continuing.",
    "Slow down slightly — accuracy over speed.",
    "Consider a 5-minute break to reset.",
  ],
};

export function getSuggestions(mood) {
  const list = MOOD_SUGGESTIONS[mood] || MOOD_SUGGESTIONS.Neutral;
  return list;
}

export const MOOD_EMOJI = { Happy: "😊", Neutral: "😐", Stressed: "😟" };