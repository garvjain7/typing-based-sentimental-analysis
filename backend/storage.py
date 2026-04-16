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