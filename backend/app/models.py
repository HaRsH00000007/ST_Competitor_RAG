"""
Pydantic Schemas for ST Competitive Intelligence API
Ensures strict JSON contract between engine, FastAPI, and frontend clients.
"""

from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ─── Leaf Schemas ──────────────────────────────────────────────────────────────

class STSpecs(BaseModel):
    """Full technical specification profile for the ST product."""
    core: str = Field(..., description="ARM Cortex-M variant or RISC-V")
    dmips: Optional[float] = Field(None, description="Dhrystone MIPS score")
    coremark: Optional[float] = Field(None, description="CoreMark benchmark score")
    clock_mhz: float = Field(..., description="Maximum CPU clock speed in MHz")
    fpu: str = Field(..., description="FPU type: SP, DP, or None")
    dsp_extensions: bool = Field(False, description="DSP/SIMD instruction support")
    flash_kb: float = Field(..., description="Flash memory size in KB")
    flash_type: str = Field(..., description="Flash architecture (dual-bank, ECC, etc.)")
    ram_kb: float = Field(..., description="Total RAM in KB")
    ram_breakdown: Optional[str] = Field(None, description="SRAM/DTCM/ITCM breakdown")
    adc: str = Field(..., description="ADC spec: resolution/channels/rate")
    dac: str = Field(..., description="DAC spec: channels/resolution")
    opamp: Optional[str] = Field(None, description="Integrated Op-Amp count and specs")
    can_fd: str = Field(..., description="CAN-FD instance count")
    ethernet: str = Field(..., description="Ethernet capability")
    usb: str = Field(..., description="USB capability (FS/HS/OTG)")
    timers: Optional[str] = Field(None, description="Timer count and types")
    security: str = Field(..., description="Security features summary")
    power_run_ua_mhz: str = Field(..., description="Run-mode power in µA/MHz")
    power_stop_ua: str = Field(..., description="Stop-mode current in µA")
    power_standby_ua: str = Field(..., description="Standby/Shutdown current in µA")
    wakeup_us: Optional[str] = Field(None, description="Wakeup time from Stop mode in µs")
    vcc_v: str = Field(..., description="Supply voltage range in V")
    temp_range_c: str = Field(..., description="Operating temperature range")
    aec_q100: bool = Field(False, description="AEC-Q100 automotive qualification")
    packages: str = Field(..., description="Available package options")
    price_usd_1k: str = Field(..., description="Approximate price at 1K quantity USD")


class CompetitorSpec(BaseModel):
    """Technical specification + gap analysis for a single competitor product."""
    vendor: str = Field(..., description="Competitor company name")
    part_number: str = Field(..., description="Specific competing part number")
    data_confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    core: str
    dmips: Optional[float] = None
    coremark: Optional[float] = None
    clock_mhz: float
    fpu: str
    dsp_extensions: bool = False
    flash_kb: float
    flash_type: str
    ram_kb: float
    adc: str
    dac: str
    opamp: Optional[str] = None
    can_fd: str
    ethernet: str
    usb: str
    security: str
    power_run_ua_mhz: str
    power_stop_ua: str
    power_standby_ua: str
    vcc_v: str
    temp_range_c: str
    aec_q100: bool = False
    packages: str
    price_usd_1k: str
    st_advantages: List[str] = Field(
        default_factory=list,
        description="Areas where ST outperforms this competitor"
    )
    competitor_advantages: List[str] = Field(
        default_factory=list,
        description="Areas where this competitor outperforms ST (honest gaps)"
    )
    gap_severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        "MEDIUM",
        description="Overall competitive threat severity"
    )


class AnalysisSummary(BaseModel):
    """High-level strategic summary of the competitive landscape."""
    st_strengths: List[str] = Field(..., description="Key ST advantages in this category")
    critical_gaps: List[str] = Field(..., description="Honest ST weaknesses vs competitors")
    market_positioning: str = Field(..., description="Marketing positioning statement")
    target_applications: List[str] = Field(..., description="Recommended target verticals")
    competitive_threat_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Overall competitive threat assessment"
    )


# ─── Top-Level Response Schema ─────────────────────────────────────────────────

class ComparisonResponse(BaseModel):
    """
    Root response schema for a full competitive analysis.
    Returned by engine.py and serialized by FastAPI.
    """
    st_product: str = Field(..., description="ST product name/part number analyzed")
    category: str = Field(..., description="Market category classification")
    data_confidence: int = Field(..., ge=0, le=100, description="Overall confidence score")
    analysis_timestamp: Optional[str] = Field(None, description="ISO8601 UTC timestamp")
    st_specs: STSpecs
    competitors: List[CompetitorSpec] = Field(..., min_length=1, max_length=5)
    summary: AnalysisSummary

    class Config:
        json_schema_extra = {
            "example": {
                "st_product": "STM32G474",
                "category": "Mixed-Signal / High-Performance",
                "data_confidence": 92,
                "analysis_timestamp": "2025-01-15T10:30:00Z",
            }
        }


# ─── API Request/Response Wrappers ─────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    """Request body for POST /analyze endpoint."""
    product_name: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="ST product name or part number (e.g., STM32G474, STM32H7, STM32U5)",
        examples=["STM32G474", "STM32H743", "STM32U575"]
    )
    include_raw_response: bool = Field(
        False,
        description="Include raw LLM text in response for debugging"
    )


class AnalysisResponse(BaseModel):
    """Full API response envelope."""
    success: bool
    data: Optional[ComparisonResponse] = None
    narrative: Optional[str] = Field(None, description="Marketing intelligence brief narrative")
    raw_llm_response: Optional[str] = Field(None, description="Raw LLM output (debug only)")
    latency_ms: int = Field(..., description="Total inference latency in milliseconds")
    model_used: str = Field(..., description="LLM model identifier")
    error: Optional[str] = Field(None, description="Error message if success=False")


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    groq_connected: bool
    model: str
    message: str