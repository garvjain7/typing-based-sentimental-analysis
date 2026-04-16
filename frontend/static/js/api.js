// api.js — backend communication only

export async function predictMood(features) {
  const response = await fetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(features),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Prediction failed: ${err}`);
  }

  return response.json(); // { mood: string, confidence: float }
}

export async function fetchParagraph() {
  const response = await fetch("/paragraph");
  if (!response.ok) throw new Error("Failed to fetch paragraph");
  const data = await response.json();
  return data.paragraph;
}