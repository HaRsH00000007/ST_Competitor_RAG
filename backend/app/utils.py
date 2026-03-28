"""
Utility helpers for the ST Competitive Intelligence RAG system.
Handles JSON extraction, unit normalization, and table formatting.
"""

from __future__ import annotations

import re
import json
import math
from typing import Optional, Union
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════════════
#  JSON EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_json_block(text: str) -> Optional[dict]:
    """
    Robustly extract and parse the first JSON object from LLM output.
    Tries fenced blocks first, then raw brace-delimited JSON.
    """
    # Strategy 1: ```json ... ``` fenced block
    fence = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        candidate = fence.group(1).strip()
        result = _try_parse(candidate)
        if result:
            return result

    # Strategy 2: ``` ... ``` any fenced block
    fence_any = re.search(r"```\s*([\s\S]*?)\s*```", text)
    if fence_any:
        candidate = fence_any.group(1).strip()
        if candidate.startswith("{"):
            result = _try_parse(candidate)
            if result:
                return result

    # Strategy 3: Raw JSON object — find outermost braces
    start = text.find("{")
    if start != -1:
        depth, end = 0, start
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        candidate = text[start : end + 1]
        result = _try_parse(candidate)
        if result:
            return result

    return None


def _try_parse(s: str) -> Optional[dict]:
    """Attempt JSON parse with basic repair fallback."""
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        repaired = _repair_json(s)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None


def _repair_json(s: str) -> str:
    """Apply common LLM JSON output fixes."""
    # Remove trailing commas before ] or }
    s = re.sub(r",\s*([\]}])", r"\1", s)
    # Fix unquoted keys (very simple heuristic)
    s = re.sub(r"(\w+)\s*:", r'"\1":', s)
    s = re.sub(r'""(\w+)""', r'"\1"', s)  # Fix double-quoted keys
    return s


def extract_narrative(text: str) -> str:
    """
    Extract the narrative section from the LLM response.
    Removes the JSON block and returns remaining markdown content.
    """
    # Remove fenced JSON block
    cleaned = re.sub(r"```json[\s\S]*?```", "", text, flags=re.IGNORECASE)
    # Remove any raw JSON object
    cleaned = re.sub(r"^\s*\{[\s\S]*?\}\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  UNIT NORMALIZATION
# ══════════════════════════════════════════════════════════════════════════════

def normalize_clock_mhz(value: Union[str, int, float, None]) -> Optional[float]:
    """Normalize any clock speed representation to MHz (float)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().upper().replace(" ", "")
    if m := re.search(r"([\d.]+)\s*GHZ", s):
        return float(m.group(1)) * 1000.0
    if m := re.search(r"([\d.]+)\s*MHZ", s):
        return float(m.group(1))
    if m := re.search(r"([\d.]+)", s):
        return float(m.group(1))
    return None


def normalize_memory_kb(value: Union[str, int, float, None]) -> Optional[float]:
    """Normalize any memory size to KB (float)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().upper().replace(" ", "")
    if m := re.search(r"([\d.]+)\s*MB", s):
        return float(m.group(1)) * 1024.0
    if m := re.search(r"([\d.]+)\s*KB", s):
        return float(m.group(1))
    if m := re.search(r"([\d.]+)", s):
        return float(m.group(1))
    return None


def format_memory(kb: float) -> str:
    """Convert KB float to display string (KB or MB)."""
    if kb >= 1024 and kb % 1024 == 0:
        return f"{int(kb // 1024)} MB"
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{int(kb)} KB"


def normalize_power_ua(value: Union[str, int, float, None]) -> Optional[float]:
    """Normalize power to µA (float)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().upper().replace(" ", "").replace("µ", "U").replace("Μ", "U")
    if m := re.search(r"([\d.]+)\s*NA", s):
        return float(m.group(1)) / 1000.0
    if m := re.search(r"([\d.]+)\s*UA", s):
        return float(m.group(1))
    if m := re.search(r"([\d.]+)\s*MA", s):
        return float(m.group(1)) * 1000.0
    if m := re.search(r"([\d.]+)", s):
        return float(m.group(1))
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  TABLE FORMATTING
# ══════════════════════════════════════════════════════════════════════════════

# Ordered spec rows for the comparison table
SPEC_ROWS: list[tuple[str, str]] = [
    ("core",              "Core Architecture"),
    ("clock_mhz",         "Clock Speed (MHz)"),
    ("dmips",             "Performance (DMIPS)"),
    ("coremark",          "CoreMark Score"),
    ("fpu",               "FPU"),
    ("dsp_extensions",    "DSP Extensions"),
    ("flash_kb",          "Flash Memory (KB)"),
    ("flash_type",        "Flash Type"),
    ("ram_kb",            "RAM (KB)"),
    ("ram_breakdown",     "RAM Breakdown"),
    ("adc",               "ADC"),
    ("dac",               "DAC"),
    ("opamp",             "Op-Amps"),
    ("can_fd",            "CAN-FD"),
    ("ethernet",          "Ethernet"),
    ("usb",               "USB"),
    ("security",          "Security Features"),
    ("power_run_ua_mhz",  "Power — Run (µA/MHz)"),
    ("power_stop_ua",     "Power — Stop (µA)"),
    ("power_standby_ua",  "Power — Standby"),
    ("wakeup_us",         "Wakeup Time (µs)"),
    ("vcc_v",             "Supply Voltage (V)"),
    ("temp_range_c",      "Temperature Range"),
    ("aec_q100",          "AEC-Q100 Automotive"),
    ("packages",          "Package Options"),
    ("price_usd_1k",      "Price @ 1K qty (USD)"),
]


def build_comparison_rows(analysis_dict: dict) -> list[dict]:
    """
    Flatten a ComparisonResponse dict into a list of row dicts
    suitable for st.dataframe() or pd.DataFrame construction.

    Each row: { "Parameter": label, "STMicro <part>": val, "Vendor Part": val, ... }
    """
    st_specs = analysis_dict.get("st_specs", {})
    competitors = analysis_dict.get("competitors", [])
    st_label = f"ST · {analysis_dict.get('st_product', 'N/A')}"

    rows = []
    for key, label in SPEC_ROWS:
        row: dict = {"Parameter": label}
        raw_st = st_specs.get(key)
        row[st_label] = _format_cell(key, raw_st)
        for comp in competitors:
            col = f"{comp.get('vendor', '?')} · {comp.get('part_number', '?')}"
            row[col] = _format_cell(key, comp.get(key))
        rows.append(row)

    return rows


def _format_cell(key: str, value) -> str:
    """Convert raw value to display string."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "✓ Yes" if value else "✗ No"
    if key == "clock_mhz":
        try:
            return f"{float(value):.0f} MHz"
        except (ValueError, TypeError):
            return str(value)
    if key in ("flash_kb", "ram_kb"):
        try:
            kb = float(value)
            return format_memory(kb)
        except (ValueError, TypeError):
            return str(value)
    if key in ("dmips", "coremark"):
        if value == 0 or value is None:
            return "—"
        try:
            return f"{float(value):,.0f}"
        except (ValueError, TypeError):
            return str(value)
    return str(value)


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIDENCE SCORING
# ══════════════════════════════════════════════════════════════════════════════

def confidence_tier(score: int) -> tuple[str, str]:
    """Return (label, hex_color) for a confidence score."""
    if score >= 85:
        return "HIGH",      "#06D6A0"
    elif score >= 65:
        return "MEDIUM",    "#FFB703"
    elif score >= 45:
        return "LOW",       "#FF6D00"
    else:
        return "VERY LOW",  "#EF233C"


def threat_tier_color(level: str) -> str:
    mapping = {
        "LOW":      "#06D6A0",
        "MEDIUM":   "#FFB703",
        "HIGH":     "#FF6D00",
        "CRITICAL": "#EF233C",
    }
    return mapping.get(level.upper(), "#8A95A8")


# ══════════════════════════════════════════════════════════════════════════════
#  PRODUCT FAMILY DETECTION
# ══════════════════════════════════════════════════════════════════════════════

_FAMILY_MAP: list[tuple[str, str]] = [
    ("STM32H7",   "High-Performance (Cortex-M7)"),
    ("STM32H5",   "High-Performance (Cortex-M33)"),
    ("STM32F4",   "Mainstream High-Performance (Cortex-M4)"),
    ("STM32F7",   "High-Performance (Cortex-M7)"),
    ("STM32G4",   "Mixed-Signal (Cortex-M4)"),
    ("STM32G0",   "Mainstream Entry (Cortex-M0+)"),
    ("STM32U5",   "Ultra-Low-Power (Cortex-M33)"),
    ("STM32U0",   "Ultra-Low-Power Entry (Cortex-M0+)"),
    ("STM32L4",   "Ultra-Low-Power (Cortex-M4)"),
    ("STM32L5",   "Ultra-Low-Power + Security (Cortex-M33)"),
    ("STM32L0",   "Ultra-Low-Power Entry (Cortex-M0+)"),
    ("STM32L1",   "Ultra-Low-Power (Cortex-M3)"),
    ("STM32WB",   "Wireless BLE + 802.15.4 (Cortex-M4/M0+)"),
    ("STM32WL",   "Wireless LoRa/FSK (Cortex-M4/M0+)"),
    ("STM32WBA",  "Wireless BLE 5.3 (Cortex-M33)"),
    ("STM32C0",   "Value Line Entry (Cortex-M0+)"),
    ("STM32F0",   "Entry-Level (Cortex-M0)"),
    ("STM32F1",   "Mainstream (Cortex-M3)"),
    ("STM32F2",   "Mainstream (Cortex-M3)"),
    ("STM32F3",   "Mixed-Signal (Cortex-M4)"),
    ("STM32MP1",  "MPU Linux/RTOS (Cortex-A7 + M4)"),
    ("STM32MP2",  "MPU Linux (Cortex-A35 + M33)"),
    ("SPC5",      "Automotive MCU (PowerPC/Cortex-M)"),
]


def detect_product_family(name: str) -> str:
    """Heuristic family detection from ST part number string."""
    upper = name.upper().strip()
    for prefix, family in _FAMILY_MAP:
        if upper.startswith(prefix):
            return family
    if "STM32" in upper:
        return "STM32 Series"
    if "ST" in upper:
        return "ST Semiconductor"
    return "Unknown / Non-ST Product"


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")