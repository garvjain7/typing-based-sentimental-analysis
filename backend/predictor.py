import joblib
from pathlib import Path

from backend.features import validate_and_build

MODEL_PATH = Path(__file__).parent / "model" / "model.pkl"

model = None


def load_model():
    global model
    payload = joblib.load(MODEL_PATH)
    # train_model.py saves {'model': clf, 'features': [...]}
    # Handle both the dict format and a bare model object (legacy)
    if isinstance(payload, dict):
        model = payload["model"]
    else:
        model = payload


def predict(features: dict) -> dict:
    df = validate_and_build(features)
    mood = model.predict(df)[0]
    proba = model.predict_proba(df)[0]
    confidence = float(max(proba))
    return {"mood": str(mood), "confidence": round(confidence, 4)}