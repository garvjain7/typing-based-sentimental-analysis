import joblib
import pandas as pd
import numpy as np
from pathlib import Path

from backend.features import validate_and_build

MODEL_PATH = Path(__file__).parent / "model" / "model.pkl"

model = None
class_means = None


def load_model():
    global model, class_means
    payload = joblib.load(MODEL_PATH)
    if isinstance(payload, dict):
        model = payload["model"]
        class_means = payload.get("class_means", None)
    else:
        model = payload


def get_driving_factors(user_features: pd.DataFrame, predicted_mood: str, overall_means: pd.Series) -> list:
    if not class_means or predicted_mood not in class_means:
        return []
        
    target_profile = class_means[predicted_mood]
    
    factors = []
    for feature in user_features.columns:
        user_val = user_features[feature].iloc[0]
        target_val = target_profile[feature]
        overall_val = overall_means[feature]
        
        # Which direction does this mood typically skew compared to average?
        direction = 1 if target_val > overall_val else -1
        
        if overall_val != 0:
            user_deviation = (user_val - overall_val) / overall_val
            target_deviation = (target_val - overall_val) / overall_val
            
            # If the user's deviation aligns with the mood's typical profile
            if np.sign(user_deviation) == np.sign(target_deviation):
                score = abs(user_deviation)
                
                direction_str = "High" if user_val > overall_val else "Low"
                # Make the names read like human features
                name_str = feature.replace("_", " ").replace("avg", "Average").title()
                
                factors.append({
                    "name": f"{direction_str} {name_str}",
                    "score": score
                })
                
    # Sort finding the most extreme deviations that align with the decision
    factors = sorted(factors, key=lambda x: x["score"], reverse=True)
    return [f["name"] for f in factors[:3]]


def predict(features: dict) -> dict:
    df = validate_and_build(features)
    mood = model.predict(df)[0]
    proba = model.predict_proba(df)[0]
    confidence = float(max(proba))
    
    # Calculate overall dataset means for each feature to establish a baseline
    overall_means = pd.DataFrame(class_means).mean(axis=1)
    
    # DEBUG LOG
    print(f"[DEBUG] Calculated overall_means for radar: {overall_means.to_dict()}")
    
    driving_factors = get_driving_factors(df, str(mood), overall_means)
    
    return {
        "mood": str(mood), 
        "confidence": round(confidence, 4),
        "driving_factors": driving_factors,
        "overall_means": overall_means.to_dict()
    }