import csv
import os
from datetime import datetime
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "typing_behavior_dataset.csv"

COLUMNS = [
    "timestamp",
    "user_id",
    "wpm",
    "wpm_variance",
    "avg_key_hold_time",
    "avg_inter_key_delay",
    "backspace_rate",
    "error_rate",
    "avg_pause_time",
    "pause_variability",
    "typing_consistency_score",
    "burstiness_score",
    "mood_label",
    "confidence",
]


def append_row(features: dict, mood: str, confidence: float):
    file_exists = CSV_PATH.exists()
    # Ensure directory exists
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": "live_session",
            **{k: features[k] for k in COLUMNS if k in features},
            "mood_label": mood,
            "confidence": confidence,
        })


def get_session_logs(page=1, per_page=50):
    if not CSV_PATH.exists():
        return [], 0
    
    all_data = []
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter: Only show live sessions (ignore synthetic AI data)
            if row.get("user_id") == "live_session":
                all_data.append(row)
    
    # Newest logs first
    all_data.reverse()
    
    total_count = len(all_data)
    start = (page - 1) * per_page
    end = start + per_page
    
    return all_data[start:end], total_count