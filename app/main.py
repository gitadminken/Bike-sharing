"""FastAPI application for the Bike Sharing Demand Prediction dashboard.

Artifacts are loaded at startup. If any artifact is missing or was built with
an incompatible library version (e.g. after a pandas/sklearn upgrade), the app
automatically retrains the model and saves fresh artifacts before continuing.
"""

import logging
import os
import random
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)

import joblib
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.predict import predict, load_model
from src.preprocessing import (
    SEASON_MAP, WEATHER_MAP, WEEKDAY_MAP, RAW_INPUT_COLUMNS,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "artifacts")

app = FastAPI(title="Bike Sharing Demand Prediction")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ---------------------------------------------------------------------------
# Artifact loading with auto-retrain fallback
# ---------------------------------------------------------------------------
_REQUIRED_ARTIFACTS = [
    "model.pkl",
    "train_data.pkl",
    "test_data.pkl",
    "test_predictions.pkl",
    "feature_names.pkl",
]


def _artifacts_exist() -> bool:
    """Return True only if every required artifact file is present."""
    return all(
        os.path.isfile(os.path.join(ARTIFACTS_DIR, fname))
        for fname in _REQUIRED_ARTIFACTS
    )


def _retrain() -> None:
    """Run the training pipeline to (re)generate all artifacts."""
    logging.warning(
        "Artifacts missing or incompatible — retraining model. "
        "This may take a minute..."
    )
    # Make sure the project root is on sys.path so src.train can be imported
    project_root = os.path.dirname(BASE_DIR)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.train import train_model  # imported here to avoid circular deps
    train_model()
    logging.info("Retraining complete — artifacts saved to %s", ARTIFACTS_DIR)


def _load_artifacts():
    """Load all artifacts, auto-retraining if they are absent or incompatible."""
    global model, train_data, test_data, test_predictions

    # ── First attempt ────────────────────────────────────────────────────────
    if _artifacts_exist():
        try:
            logging.info("Loading artifacts from %s ...", ARTIFACTS_DIR)
            model = load_model()
            train_data = joblib.load(os.path.join(ARTIFACTS_DIR, "train_data.pkl"))
            test_data = joblib.load(os.path.join(ARTIFACTS_DIR, "test_data.pkl"))
            test_predictions = joblib.load(
                os.path.join(ARTIFACTS_DIR, "test_predictions.pkl")
            )
            logging.info("Artifacts loaded successfully.")
            return
        except Exception as exc:  # noqa: BLE001
            logging.warning(
                "Failed to load artifacts (%s: %s). Will retrain.",
                type(exc).__name__,
                exc,
            )

    # ── Retrain then retry ───────────────────────────────────────────────────
    _retrain()
    try:
        model = load_model()
        train_data = joblib.load(os.path.join(ARTIFACTS_DIR, "train_data.pkl"))
        test_data = joblib.load(os.path.join(ARTIFACTS_DIR, "test_data.pkl"))
        test_predictions = joblib.load(
            os.path.join(ARTIFACTS_DIR, "test_predictions.pkl")
        )
        logging.info("Artifacts loaded successfully after retraining.")
    except Exception as exc:  # noqa: BLE001
        logging.error(
            "Could not load artifacts even after retraining: %s", exc
        )
        raise RuntimeError(
            "Startup failed: unable to load model artifacts. "
            "Check the training logs above for details."
        ) from exc


# Initialise globals (populated by _load_artifacts)
model = None
train_data = None
test_data = None
test_predictions = None

_load_artifacts()

# Pre-compute model comparison data (from training notebook results)
MODEL_LEADERBOARD = [
    {"model": "Gradient Boosting", "mae": 46.08, "rmse": 70.65, "r2": 0.8966, "best": True},
    {"model": "Random Forest", "mae": 50.25, "rmse": 76.77, "r2": 0.8779, "best": False},
    {"model": "Decision Tree", "mae": 58.24, "rmse": 91.24, "r2": 0.8275, "best": False},
    {"model": "Linear Regression", "mae": 108.64, "rmse": 144.19, "r2": 0.5692, "best": False},
    {"model": "Ridge", "mae": 108.65, "rmse": 144.21, "r2": 0.5691, "best": False},
    {"model": "Lasso", "mae": 108.64, "rmse": 144.63, "r2": 0.5666, "best": False},
]


def _df_to_records(df, limit=500):
    """Convert DataFrame to list of dicts, capped at `limit` rows."""
    return df.head(limit).to_dict(orient="records")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "leaderboard": MODEL_LEADERBOARD,
        "train_count": len(train_data),
        "test_count": len(test_data),
        "total_count": len(train_data) + len(test_data),
        "feature_count": 18,
        "best_r2": 0.8966,
        "best_mae": 46.08,
        "best_rmse": 70.65,
    })


@app.get("/predict", response_class=HTMLResponse)
async def predict_page(request: Request):
    return templates.TemplateResponse("predict.html", {
        "request": request,
        "season_map": SEASON_MAP,
        "weather_map": WEATHER_MAP,
        "weekday_map": WEEKDAY_MAP,
        "leaderboard": MODEL_LEADERBOARD,
        "total_count": len(train_data) + len(test_data),
        "best_r2": 0.8966,
        "best_mae": 46.08,
    })




# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.post("/api/predict")
async def api_predict(request: Request):
    body = await request.json()
    # yr is hardcoded to 1 (mature demand level) — not exposed in the UI
    body.setdefault("yr", 1)
    raw_input = {}
    for col in RAW_INPUT_COLUMNS:
        val = body.get(col)
        if val is None:
            return JSONResponse({"error": f"Missing field: {col}"}, status_code=400)
        raw_input[col] = float(val)

    prediction = predict(model, raw_input)
    result = {"prediction": round(prediction, 1)}

    # If actual value was provided (from test data), include comparison
    actual = body.get("actual")
    if actual is not None:
        actual = float(actual)
        result["actual"] = actual
        result["error_abs"] = round(abs(prediction - actual), 1)
        result["error_pct"] = round(abs(prediction - actual) / max(actual, 1) * 100, 1)

    return JSONResponse(result)


@app.get("/api/test-sample")
async def api_test_sample():
    idx = random.randint(0, len(test_data) - 1)
    row = test_data.iloc[idx]
    sample = {col: _convert(row[col]) for col in test_data.columns}
    sample["_index"] = idx
    return JSONResponse(sample)


@app.get("/api/train-data")
async def api_train_data(offset: int = 0, limit: int = 100):
    limit = min(limit, 500)
    subset = train_data.iloc[offset:offset + limit]
    return JSONResponse({
        "data": _df_to_records(subset, limit),
        "total": len(train_data),
        "offset": offset,
        "limit": limit,
    })


@app.get("/api/test-data")
async def api_test_data(offset: int = 0, limit: int = 100):
    limit = min(limit, 500)
    subset = test_data.iloc[offset:offset + limit]
    return JSONResponse({
        "data": _df_to_records(subset, limit),
        "total": len(test_data),
        "offset": offset,
        "limit": limit,
    })


@app.get("/api/actual-vs-predicted")
async def api_actual_vs_predicted(limit: int = 200):
    """Return actual and predicted values for the test set (for charting)."""
    limit = min(limit, len(test_predictions["actual"]))
    return JSONResponse({
        "actual": test_predictions["actual"][:limit].tolist(),
        "predicted": test_predictions["predicted"][:limit].tolist(),
        "total": len(test_predictions["actual"]),
    })


def _convert(val):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 4)
    return val
