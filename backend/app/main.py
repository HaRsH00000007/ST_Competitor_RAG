"""
FastAPI entry point — app/main.py (v4)

New in v4:
  POST /set-key       — store user API key in engine at runtime
  POST /validate-key  — validate a key before storing it
  POST /clear-key     — clear the stored key (user wants to change it)
  Static file serving — serves React dist/ at root URL for PyWebview
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.engine import (
    get_competitive_analysis,
    stream_competitive_analysis,
    check_groq_health,
    set_runtime_api_key,
    clear_runtime_api_key,
    validate_api_key,
    has_api_key,
    MODEL_NAME,
)
from app.models import AnalysisRequest, AnalysisResponse, ComparisonResponse
from app.utils import utc_now_iso

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────
import sys

def _get_dist_dir() -> Path:
    """Works whether running as script, PyInstaller exe, or from any cwd."""
    if getattr(sys, 'frozen', False):
        # PyInstaller exe — _internal/ is next to the exe
        base = Path(sys.executable).parent / "_internal"
    else:
        # Normal Python — relative to this file
        base = Path(__file__).parent.parent
    return base / "dist"

_DIST_DIR = _get_dist_dir()
# ─── Paths ────────────────────────────────────────────────────────────────────
import sys

def _get_dist_dir() -> Path:
    """Works whether running as script, PyInstaller exe, or from any cwd."""
    if getattr(sys, 'frozen', False):
        # PyInstaller exe — _internal/ is next to the exe
        base = Path(sys.executable).parent / "_internal"
    else:
        # Normal Python — relative to this file
        base = Path(__file__).parent.parent
    return base / "dist"

_DIST_DIR = _get_dist_dir()
# ─── Paths ────────────────────────────────────────────────────────────────────
import sys

def _get_dist_dir() -> Path:
    """Works whether running as script, PyInstaller exe, or from any cwd."""
    if getattr(sys, 'frozen', False):
        # PyInstaller exe — _internal/ is next to the exe
        base = Path(sys.executable).parent / "_internal"
    else:
        # Normal Python — relative to this file
        base = Path(__file__).parent.parent
    return base / "dist"

_DIST_DIR = _get_dist_dir()
# ─── Paths ────────────────────────────────────────────────────────────────────
import sys

def _get_dist_dir() -> Path:
    """Works whether running as script, PyInstaller exe, or from any cwd."""
    if getattr(sys, 'frozen', False):
        # PyInstaller exe — _internal/ is next to the exe
        base = Path(sys.executable).parent / "_internal"
    else:
        # Normal Python — relative to this file
        base = Path(__file__).parent.parent
    return base / "dist"

_DIST_DIR = _get_dist_dir()


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 55)
    logger.info("  ST Competitive Intelligence RAG — Starting v4")
    logger.info(f"  Model : {MODEL_NAME}")
    logger.info(f"  Dist  : {_DIST_DIR} {'✓' if _DIST_DIR.exists() else '✗ NOT FOUND'}")
    logger.info("=" * 55)
    yield
    logger.info("FastAPI shutting down.")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ST Competitive Intelligence RAG",
    description="Synthetic RAG API for STMicroelectronics competitive analysis.",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Exception Handler ────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"Internal server error: {type(exc).__name__}: {exc}",
            "latency_ms": 0,
            "model_used": MODEL_NAME,
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  API KEY MANAGEMENT ENDPOINTS (new in v4)
# ══════════════════════════════════════════════════════════════════════════════

class SetKeyRequest(BaseModel):
    api_key: str


class ValidateKeyRequest(BaseModel):
    api_key: str


@app.post("/set-key", tags=["Setup"])
async def set_key(req: SetKeyRequest):
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    set_runtime_api_key(key)
    return {"success": True, "message": "API key stored successfully.", "has_key": True}


@app.post("/validate-key", tags=["Setup"])
async def validate_key_endpoint(req: ValidateKeyRequest):
    key = req.api_key.strip()
    if not key:
        return {"valid": False, "message": "No key provided."}
    is_valid, message = validate_api_key(key)
    if is_valid:
        set_runtime_api_key(key)
    return {"valid": is_valid, "message": message}


@app.post("/clear-key", tags=["Setup"])
async def clear_key():
    clear_runtime_api_key()
    return {"success": True, "message": "API key cleared."}


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["Operations"])
def health():
    has_key = has_api_key()
    if has_key:
        groq_ok, msg = check_groq_health()
    else:
        groq_ok, msg = False, "No API key set. Please complete setup."

    return JSONResponse(
        status_code=200 if groq_ok else 503,
        content={
            "status":         "healthy" if groq_ok else "unhealthy",
            "groq_connected": groq_ok,
            "has_api_key":    has_key,
            "model":          MODEL_NAME,
            "message":        msg,
        },
    )


@app.post("/analyze", tags=["Analysis"])
async def analyze(request: AnalysisRequest):
    if not has_api_key():
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": "No API key configured. Please complete the setup screen first.",
                "latency_ms": 0,
                "model_used": MODEL_NAME,
            },
        )

    logger.info(f"[POST /analyze] product_name={request.product_name!r}")
    result = get_competitive_analysis(request.product_name)

    data_model = None
    if result["success"] and result["data"]:
        try:
            data_model = ComparisonResponse(**result["data"])
        except Exception as e:
            logger.warning(f"Pydantic validation warning: {e}")

    response = AnalysisResponse(
        success=result["success"],
        data=data_model,
        narrative=result.get("narrative"),
        raw_llm_response=result.get("raw_response") if request.include_raw_response else None,
        latency_ms=result["latency_ms"],
        model_used=result["model_used"],
        error=result.get("error"),
    )

    if not result["success"]:
        status_code = 422 if "JSON" in (result.get("error") or "") else 500
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(mode="json"),
        )

    return response


@app.post("/analyze/stream", tags=["Analysis"])
async def analyze_stream(request: AnalysisRequest):
    if not has_api_key():
        async def _err():
            yield "data: {\"error\": \"No API key set\"}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    def _gen():
        for chunk in stream_competitive_analysis(request.product_name):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/analyze/sample", tags=["Analysis"])
async def sample_response():
    return {
        "success": True,
        "latency_ms": 0,
        "model_used": MODEL_NAME,
        "note": "Sample data — not real analysis.",
        "data": {
            "st_product": "STM32G474",
            "category": "Mixed-Signal / High-Performance",
            "data_confidence": 92,
            "analysis_timestamp": utc_now_iso(),
            "st_specs": {
                "core": "Cortex-M4", "clock_mhz": 170, "flash_kb": 512,
                "ram_kb": 128, "adc": "12-bit/5ch", "dac": "3ch/12-bit",
                "can_fd": "3 instances", "ethernet": "None", "usb": "FS OTG",
                "security": "AES-256, RNG", "power_run_ua_mhz": "100 µA/MHz",
                "power_stop_ua": "400 µA", "power_standby_ua": "2 µA",
                "vcc_v": "1.71–3.6 V", "temp_range_c": "-40 to +85°C",
                "packages": "LQFP48–LQFP128", "price_usd_1k": "~$3.50",
            },
            "competitors": [],
            "summary": {
                "st_strengths": ["Best analog integration in class"],
                "critical_gaps": ["No TrustZone on G4"],
                "market_positioning": "Best for motor control and digital power.",
                "target_applications": ["Motor drives", "Digital power"],
                "competitive_threat_level": "MEDIUM",
            },
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC FILE SERVING  — serves React dist/ for PyWebview
#  MUST be mounted LAST so API routes take priority
# ══════════════════════════════════════════════════════════════════════════════

if _DIST_DIR.exists():
    # Serve /assets folder (JS, CSS bundles)
    app.mount("/assets", StaticFiles(directory=str(_DIST_DIR / "assets")), name="assets")

    # ── Serve root-level static files explicitly ──────────────────────────────
    # These sit in dist/ root and won't be caught by the /assets mount above.
    # Add any other root-level files here if needed (e.g. robots.txt).

    @app.get("/image.png", include_in_schema=False)
    async def serve_logo():
        logo = _DIST_DIR / "image.png"
        if logo.exists():
            return FileResponse(str(logo))
        raise HTTPException(status_code=404, detail="Logo not found")

    @app.get("/favicon.ico", include_in_schema=False)
    async def serve_favicon():
        favicon = _DIST_DIR / "favicon.ico"
        if favicon.exists():
            return FileResponse(str(favicon))
        raise HTTPException(status_code=404, detail="Favicon not found")

    # ── Catch-all: serve index.html for all React routes ─────────────────────
    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react(full_path: str = ""):
        """
        Serve index.html for all non-API routes so React Router works.
        Known static files are excluded so they don't fall through to here.
        """
        api_prefixes = (
            "analyze", "health", "set-key", "validate-key",
            "clear-key", "docs", "redoc", "openapi.json",
            "image.png", "favicon.ico",
        )
        if full_path.startswith(api_prefixes):
            raise HTTPException(status_code=404, detail="API route not found")

        index_file = _DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="React app not built yet. Run: npm run build")

else:
    @app.get("/", tags=["Root"])
    async def root_no_dist():
        return {
            "service": "ST Competitive Intelligence RAG",
            "version": "4.0.0",
            "warning": "React dist/ not found. Run npm run build and copy dist/ to backend/",
            "api_docs": "/docs",
        }