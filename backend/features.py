import pandas as pd

# Must match model training column order exactly
FEATURE_ORDER = [
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
]

# Hard clip ranges — match the dataset generation script
FEATURE_RANGES = {
    "wpm":                      (10.0,   130.0),
    "wpm_variance":             (0.0,    5000.0),
    "avg_key_hold_time":        (50.0,   400.0),
    "avg_inter_key_delay":      (50.0,   1000.0),
    "backspace_rate":           (0.0,    1.0),
    "error_rate":               (0.0,    1.0),
    "avg_pause_time":           (50.0,   2000.0),
    "pause_variability":        (0.0,    1.0),
    "typing_consistency_score": (0.0,    1.0),
    "burstiness_score":         (0.0,    1.0),
}


class FeatureValidationError(ValueError):
    """Raised when a feature value is missing or cannot be coerced to float."""
    pass


def validate_and_build(raw: dict) -> pd.DataFrame:
    """
    1. Check all required features are present
    2. Coerce to float — raise FeatureValidationError if not possible
    3. Clip each value to its valid range
    4. Return a single-row DataFrame in the exact column order the model expects

    Args:
        raw: dict of feature_name -> value (comes from Pydantic model in app.py)

    Returns:
        pd.DataFrame with shape (1, 10), columns in FEATURE_ORDER

    Raises:
        FeatureValidationError: if a feature is missing or non-numeric
    """
    cleaned = {}

    for feature in FEATURE_ORDER:
        if feature not in raw:
            raise FeatureValidationError(f"Missing feature: '{feature}'")

        try:
            value = float(raw[feature])
        except (TypeError, ValueError):
            raise FeatureValidationError(
                f"Feature '{feature}' must be numeric, got: {raw[feature]!r}"
            )

        lo, hi = FEATURE_RANGES[feature]
        value = max(lo, min(hi, value))
        cleaned[feature] = value

    return pd.DataFrame([cleaned])[FEATURE_ORDER]