"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, projects, predictions, dashboard, alerts, audit, history, actions, explain

logger = logging.getLogger(__name__)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../.."))
MODEL_FILE   = os.path.join(PROJECT_ROOT, "data/models/xgb_delay_model.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: pre-load the ML model into memory.
    If the model file doesn't exist yet, train it from scratch automatically.
    """
    from app.ml.predictor import predictor

    if not os.path.exists(MODEL_FILE):
        logger.warning("Model file not found — auto-training from CSV data...")
        try:
            from app.ml.trainer import retrain
            retrain(db=None)
            logger.info("Auto-training complete.")
        except Exception as e:
            logger.error(f"Auto-training failed: {e}. Predictions will fail until model is trained.")
    else:
        try:
            predictor.load()
            logger.info(
                f"Model loaded at startup — "
                f"{len(predictor.feature_cols)} features, "
                f"explainer ready."
            )
        except Exception as e:
            logger.error(f"Model load failed at startup: {e}")

    yield
    # Shutdown — nothing to clean up


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "Predictive Analytics System for Early Detection of Land Acquisition Delays"
        " — Ministry of Rural Development, DoLR"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api")
app.include_router(projects.router,    prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(dashboard.router,   prefix="/api")
app.include_router(alerts.router,      prefix="/api")
app.include_router(audit.router,       prefix="/api")
app.include_router(history.router,     prefix="/api")
app.include_router(actions.router,     prefix="/api")
app.include_router(explain.router,     prefix="/api")


@app.get("/")
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.VERSION,
        "docs":    "/docs",
        "status":  "running",
        "model":   "loaded" if os.path.exists(MODEL_FILE) else "not trained",
    }


@app.get("/health")
def health():
    from app.ml.predictor import predictor
    return {
        "status":       "ok",
        "model_loaded": predictor._loaded,
    }
