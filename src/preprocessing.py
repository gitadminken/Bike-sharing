"""Feature engineering for the bike sharing demand model.

Replicates the transformations from the training notebook so that
the same logic applies at training time and prediction time.
"""

import numpy as np
import pandas as pd

TARGET = "cnt"

DROP_COLUMNS = ["instant", "dteday", "casual", "registered", "atemp"]

RAW_INPUT_COLUMNS = [
    "season", "yr", "mnth", "hr", "holiday", "weekday",
    "workingday", "weathersit", "temp", "hum", "windspeed",
]

FEATURE_COLUMNS = [
    "holiday", "hr", "hr_cos", "hr_sin", "hum", "is_rush_hour",
    "is_weekend", "mnth", "mnth_cos", "mnth_sin", "season", "temp",
    "temp_x_hum", "weathersit", "weekday", "windspeed", "workingday", "yr",
]

SEASON_MAP = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
WEATHER_MAP = {
    1: "Clear / Partly Cloudy",
    2: "Mist / Cloudy",
    3: "Light Rain / Snow",
    4: "Heavy Rain / Snow",
}
WEEKDAY_MAP = {
    0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
    4: "Thursday", 5: "Friday", 6: "Saturday",
}


def engineer_features(data: pd.DataFrame) -> pd.DataFrame:
    """Apply all feature engineering steps.

    Works on both full dataset rows (with columns to drop) and
    single-row prediction inputs (which only have RAW_INPUT_COLUMNS).
    """
    df = data.copy()

    # Cyclical encoding
    df["hr_sin"] = np.sin(2 * np.pi * df["hr"] / 24)
    df["hr_cos"] = np.cos(2 * np.pi * df["hr"] / 24)
    df["mnth_sin"] = np.sin(2 * np.pi * df["mnth"] / 12)
    df["mnth_cos"] = np.cos(2 * np.pi * df["mnth"] / 12)

    # Rush-hour flag (7-9 AM, 5-7 PM)
    df["is_rush_hour"] = df["hr"].isin([7, 8, 9, 17, 18, 19]).astype(int)

    # Weekend flag
    df["is_weekend"] = (df["workingday"] == 0).astype(int)

    # Interaction term
    df["temp_x_hum"] = df["temp"] * df["hum"]

    # Drop columns that exist in the dataframe
    cols_to_drop = [c for c in DROP_COLUMNS if c in df.columns]
    df = df.drop(columns=cols_to_drop)

    return df
