// api.js — backend communication only

export async function startSession() {
  const response = await fetch("/session/start");
  if (!response.ok) throw new Error("Could not initialize session");
  const data = await response.json();
  return data.session_id;
}

export async function predictMood(features, metadata) {
  const response = await fetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...features,
      ...metadata, // session_id, total_keys, text_length
    }),
  });

  if (!response.ok) {
    let errorMsg = "Server error";
    try {
      const errorData = await response.json();
      errorMsg = errorData.detail || errorData.message || errorMsg;
    } catch {
      errorMsg = await response.text();
    }
    throw new Error(errorMsg);
  }

  return response.json(); // { mood: string, confidence: float }
}

export async function fetchParagraph() {
  const response = await fetch("/paragraph");
  if (!response.ok) throw new Error("Failed to fetch paragraph");
  const data = await response.json();
  return data.paragraph;
}