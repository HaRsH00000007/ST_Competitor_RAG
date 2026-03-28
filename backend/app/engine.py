"""
Core LLM Engine — app/engine.py (v5)

Supports BOTH:
  - .env file key  (dev mode / fallback)
  - Runtime key set by user via /set-key endpoint (exe/production mode)

Runtime key ALWAYS takes priority over .env

v5 fixes:
  - Format-only API key validation (no network call on setup)
  - Zscaler SSL fix using truststore (Windows system cert store)
  - httpx client with SSL verification using system certs
"""

from __future__ import annotations

import os
import ssl
import time
import logging
from typing import Optional, Generator

# ─── Zscaler / Corporate SSL Fix ──────────────────────────────────────────────
# Inject Windows system certificate store into Python's SSL so Zscaler's
# corporate cert is trusted. Must be done before any HTTP imports.
try:
    import truststore
    truststore.inject_into_ssl()
    logging.getLogger(__name__).info("[engine] truststore: Windows system certs injected.")
except ImportError:
    # truststore not available — fall back to certifi only
    pass

import httpx
import certifi

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from app.prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE
from app.utils import (
    extract_json_block,
    extract_narrative,
    build_comparison_rows,
    detect_product_family,
    utc_now_iso,
)

# ─── Bootstrap ────────────────────────────────────────────────────────────────
# Resolve .env path relative to THIS file — works from any launch directory
_HERE     = os.path.dirname(os.path.abspath(__file__))  # backend/app/
_BACKEND  = os.path.dirname(_HERE)                       # backend/
_ENV_PATH = os.path.join(_BACKEND, ".env")               # backend/.env
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logger = logging.getLogger(__name__)

MODEL_NAME      = "llama-3.3-70b-versatile"
TEMPERATURE     = 0.15
MAX_TOKENS      = 4096
REQUEST_TIMEOUT = 120

# ─── Runtime API Key Store ────────────────────────────────────────────────────
# Holds the key entered by the user at runtime via the Setup Page.
# Priority: runtime key > .env key
_RUNTIME_KEY: str = ""


def set_runtime_api_key(key: str) -> None:
    """Store user-supplied key in memory. Called by /set-key endpoint."""
    global _RUNTIME_KEY
    _RUNTIME_KEY = key.strip()
    logger.info("[engine] Runtime API key updated.")


def clear_runtime_api_key() -> None:
    """Clear the runtime key. Called by /clear-key endpoint."""
    global _RUNTIME_KEY
    _RUNTIME_KEY = ""
    logger.info("[engine] Runtime API key cleared.")


def get_active_api_key() -> str:
    """
    Returns the active API key with priority:
      1. Runtime key (set by user via Setup Page)
      2. GROQ_API_KEY from .env / environment variable
    """
    if _RUNTIME_KEY:
        return _RUNTIME_KEY
    return os.getenv("GROQ_API_KEY", "").strip()


def has_api_key() -> bool:
    """True if any API key is currently available."""
    return bool(get_active_api_key())


# ─── HTTP Client Factory ──────────────────────────────────────────────────────

def _make_http_client(streaming: bool = False) -> httpx.Client:
    """
    Build an httpx client that trusts the Windows system cert store.
    This handles Zscaler SSL inspection on corporate networks.
    truststore.inject_into_ssl() (called above) patches ssl.create_default_context()
    so the default SSL context already includes corporate certs.
    """
    ssl_context = ssl.create_default_context()
    try:
        # Also load certifi bundle as extra fallback
        ssl_context.load_verify_locations(certifi.where())
    except Exception:
        pass

    if streaming:
        return httpx.Client(verify=ssl_context, timeout=REQUEST_TIMEOUT)
    return httpx.Client(verify=ssl_context, timeout=REQUEST_TIMEOUT)


# ─── LLM Factory ──────────────────────────────────────────────────────────────

def _get_llm(streaming: bool = False) -> ChatGroq:
    """Initialize a ChatGroq instance using the active API key."""
    key = get_active_api_key()
    if not key:
        raise EnvironmentError(
            "No Groq API key found. Please enter your key in the Setup screen."
        )
    return ChatGroq(
        api_key=key,
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        streaming=streaming,
        http_client=_make_http_client(streaming=streaming),
    )


# ─── Key Validation ───────────────────────────────────────────────────────────

def validate_api_key(key: str) -> tuple[bool, str]:
    """
    Validate a Groq API key by format only — no network call.
    This avoids Zscaler/proxy blocking during setup.
    Real API errors will surface when the user runs their first analysis.
    """
    key = key.strip()
    if not key:
        return False, "No key provided."
    if not key.startswith("gsk_"):
        return False, "Invalid format. Groq API keys start with 'gsk_'."
    if len(key) < 40:
        return False, "Key looks too short. Please check and try again."
    # Format looks valid — store it and let the first analysis confirm it works
    return True, f"Key accepted. Model: {MODEL_NAME}"


# ─── Primary Entry Point ───────────────────────────────────────────────────────

def get_competitive_analysis(product_name: str) -> dict:
    """
    Main Synthetic RAG pipeline.
    Returns a structured dict with full competitive analysis data.
    """
    result: dict = {
        "success":        False,
        "st_product":     product_name.strip().upper(),
        "product_family": detect_product_family(product_name),
        "data":           None,
        "table_rows":     [],
        "narrative":      "",
        "raw_response":   "",
        "latency_ms":     0,
        "model_used":     MODEL_NAME,
        "error":          None,
    }

    try:
        llm = _get_llm(streaming=False)

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            product_name=result["st_product"]
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"[engine] Requesting analysis for {result['st_product']}")
        t0 = time.time()
        response = llm.invoke(messages)
        result["latency_ms"] = int((time.time() - t0) * 1000)

        raw_text = response.content or ""
        result["raw_response"] = raw_text

        json_data = extract_json_block(raw_text)
        if json_data:
            if not json_data.get("analysis_timestamp"):
                json_data["analysis_timestamp"] = utc_now_iso()
            result["data"]       = json_data
            result["table_rows"] = build_comparison_rows(json_data)
            result["success"]    = True
            logger.info(f"[engine] JSON parsed successfully for {result['st_product']}")
        else:
            result["error"] = "Model returned a response but structured JSON could not be extracted."
            logger.warning(f"[engine] JSON extraction failed for {result['st_product']}")

        result["narrative"] = extract_narrative(raw_text)

    except EnvironmentError as e:
        result["error"] = str(e)
        logger.error(f"[engine] Config error: {e}")
    except Exception as e:
        result["error"] = f"LLM inference error: {type(e).__name__}: {str(e)}"
        logger.exception(f"[engine] Unexpected error for {result['st_product']}")

    return result


# ─── Streaming Variant ────────────────────────────────────────────────────────

def stream_competitive_analysis(product_name: str) -> Generator[str, None, None]:
    """Streaming version — yields text tokens as they arrive from Groq."""
    try:
        llm = _get_llm(streaming=True)
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            product_name=product_name.strip().upper()
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        chain = llm | StrOutputParser()
        yield from chain.stream(messages)
    except EnvironmentError as e:
        yield f"\n\n**⚠ Configuration Error:** {e}"
    except Exception as e:
        yield f"\n\n**⚠ Streaming Error:** {type(e).__name__}: {e}"


# ─── Health Check ─────────────────────────────────────────────────────────────

def check_groq_health() -> tuple[bool, str]:
    """Quick connectivity probe. Returns (is_healthy, message)."""
    try:
        llm = _get_llm()
        resp = llm.invoke([HumanMessage(content="Respond with exactly: READY")])
        if resp and resp.content:
            return True, f"Groq API connected · Model: {MODEL_NAME}"
        return False, "Groq API responded but returned empty content."
    except EnvironmentError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Connection failed: {type(e).__name__}: {e}"