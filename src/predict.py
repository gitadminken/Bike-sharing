"""Load the trained model and make predictions."""

import os
import joblib
import numpy as np
import pandas as pd

from src.preprocessing import engineer_features

ARTIFACTS_DIR = "artifacts"

# Loaded once and cached at module level
_feature_names = None


def load_model():
    model_path = os.path.join(ARTIFACTS_DIR, "model.pkl")
    return joblib.load(model_path)


def load_feature_names():
    global _feature_names
    if _feature_names is None:
        path = os.path.join(ARTIFACTS_DIR, "feature_names.pkl")
        _feature_names = joblib.load(path)
    return _feature_names


def predict(model, raw_input: dict) -> float:
    """Make a single prediction from raw feature values.

    Parameters
    ----------
    model : sklearn Pipeline
        The trained pipeline (scaler + model).
    raw_input : dict
        Keys matching RAW_INPUT_COLUMNS (season, yr, mnth, hr, ...).

    Returns
    -------
    float
        Predicted bike rental count (clipped to >= 0).
    """
    feature_names = load_feature_names()
    df = pd.DataFrame([raw_input])
    df_fe = engineer_features(df)
    df_fe = df_fe.reindex(columns=feature_names, fill_value=0)
    pred = model.predict(df_fe)[0]
    return float(max(0, pred))
