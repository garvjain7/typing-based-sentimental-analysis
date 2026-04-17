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
    // Specific check for 403 Session Used
    if (response.status === 403 && errorMsg.includes("already used")) {
        throw new Error("Session locked. This result was already submitted.");
    }
    throw new Error(errorMsg);
  }

  const data = await response.json();
  if (!data) throw new Error("Server returned empty response");
  return data;
}

export async function fetchParagraph() {
  const response = await fetch("/paragraph");
  if (!response.ok) throw new Error("Failed to fetch paragraph");
  const data = await response.json();
  return data.paragraph;
}