"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, projects, predictions, dashboard, alerts, audit

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Predictive Analytics System for Early Detection of Land Acquisition Delays — Ministry of Rural Development, DoLR",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
