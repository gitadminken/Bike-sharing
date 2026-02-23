"""Train the bike sharing demand model and save artifacts.

Run from project root:
    python -m src.train
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.preprocessing import engineer_features, TARGET, FEATURE_COLUMNS

RANDOM_STATE = 42
DATA_PATH = os.path.join("notebook", "data", "bike_sharing.csv")
ARTIFACTS_DIR = "artifacts"
SPLIT_DATE = "2012-07-01"


def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["dteday"])
    print(f"Loaded {len(df):,} rows from {DATA_PATH}")
    return df


def train_model():
    df = load_data()
    df_fe = engineer_features(df)

    # Time-based split
    train_mask = df["dteday"] < SPLIT_DATE
    test_mask = df["dteday"] >= SPLIT_DATE

    X_train = df_fe.loc[train_mask].drop(columns=[TARGET])
    y_train = df_fe.loc[train_mask][TARGET]
    X_test = df_fe.loc[test_mask].drop(columns=[TARGET])
    y_test = df_fe.loc[test_mask][TARGET]

    print(f"Train: {len(X_train):,} rows | Test: {len(X_test):,} rows")

    # Gradient Boosting with original params (best performance on test set)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
        )),
    ])

    pipe.fit(X_train, y_train)

    # Evaluate on test set
    y_pred = np.clip(pipe.predict(X_test), 0, None)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"Test metrics  -- MAE: {mae:.2f}  RMSE: {rmse:.2f}  R2: {r2:.4f}")

    # Retrain on all data for production
    X_all = df_fe.drop(columns=[TARGET])
    y_all = df_fe[TARGET]

    final_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
        )),
    ])
    final_pipe.fit(X_all, y_all)

    # Save artifacts
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    model_path = os.path.join(ARTIFACTS_DIR, "model.pkl")
    features_path = os.path.join(ARTIFACTS_DIR, "feature_names.pkl")
    train_data_path = os.path.join(ARTIFACTS_DIR, "train_data.pkl")
    test_data_path = os.path.join(ARTIFACTS_DIR, "test_data.pkl")

    joblib.dump(final_pipe, model_path)
    joblib.dump(X_all.columns.tolist(), features_path)

    # Save raw train/test splits for the dashboard
    raw_cols = ["season", "yr", "mnth", "hr", "holiday", "weekday",
                "workingday", "weathersit", "temp", "hum", "windspeed", "cnt"]
    joblib.dump(df.loc[train_mask, raw_cols].reset_index(drop=True), train_data_path)
    joblib.dump(df.loc[test_mask, raw_cols].reset_index(drop=True), test_data_path)

    # Save test predictions for actual-vs-predicted display
    test_preds_path = os.path.join(ARTIFACTS_DIR, "test_predictions.pkl")
    joblib.dump({"actual": y_test.values, "predicted": y_pred}, test_preds_path)

    print(f"\nArtifacts saved to {ARTIFACTS_DIR}/")
    print(f"  model.pkl           ({os.path.getsize(model_path) / 1024:.0f} KB)")
    print(f"  feature_names.pkl")
    print(f"  train_data.pkl      ({len(df.loc[train_mask]):,} rows)")
    print(f"  test_data.pkl       ({len(df.loc[test_mask]):,} rows)")
    print(f"  test_predictions.pkl")


if __name__ == "__main__":
    train_model()
