"""
FastAPI application entry point.

Wires together:
  - Logging
  - CORS
  - API routers
  - Request ID middleware
  - Global error handlers
  - Startup/shutdown lifecycle
"""
from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import artifacts, health, messages, sessions
from app.config import get_settings
from app.logging_config import get_logger, setup_logging
from app.providers.base import ProviderConfigError, ProviderTimeoutError, ProviderUnavailableError

setup_logging()
logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Lenny Growth Assistant API",
    description="AI assistant grounded in Lenny's Podcast transcripts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID Middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http.request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        elapsed_ms=round(elapsed * 1000),
    )
    return response


# ── Global Error Handlers ─────────────────────────────────────────────────────
@app.exception_handler(ProviderUnavailableError)
async def provider_unavailable_handler(request: Request, exc: ProviderUnavailableError):
    return JSONResponse(
        status_code=503,
        content={"error": "LLM provider unavailable", "detail": str(exc)},
    )


@app.exception_handler(ProviderTimeoutError)
async def provider_timeout_handler(request: Request, exc: ProviderTimeoutError):
    return JSONResponse(
        status_code=504,
        content={"error": "LLM request timed out", "detail": str(exc)},
    )


@app.exception_handler(ProviderConfigError)
async def provider_config_handler(request: Request, exc: ProviderConfigError):
    return JSONResponse(
        status_code=422,
        content={"error": "LLM provider configuration error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    # Log the full error but never expose stack traces to clients
    logger.error("unhandled_exception", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(artifacts.router)


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info(
        "app.startup",
        env=settings.app_env,
        llm_provider=settings.llm_provider,
        ollama_model=settings.ollama_model,
    )


@app.on_event("shutdown")
async def shutdown():
    logger.info("app.shutdown")
