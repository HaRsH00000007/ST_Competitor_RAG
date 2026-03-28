"""
ST Competitive Intelligence RAG — Streamlit Dashboard
Internal validation UI that calls engine.py directly (no HTTP overhead).

Run: streamlit run testing/streamlit_app.py
"""

from __future__ import annotations

import sys
import os

# Ensure repo root is on path so `backend` imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import json
import pandas as pd
import streamlit as st

from backend.app.engine import get_competitive_analysis, check_groq_health, MODEL_NAME
from backend.app.utils import (
    confidence_tier,
    threat_tier_color,
    detect_product_family,
    build_comparison_rows,
)

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ST Intelligence · Competitive RAG",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS — Industrial Dark Theme
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@500;600;700&display=swap');

:root {
    --red:       #E63946;
    --red-glow:  rgba(230, 57, 70, 0.18);
    --bg0:       #070A0F;
    --bg1:       #0C1018;
    --bg2:       #111824;
    --bg3:       #1A2233;
    --border:    #1E2D42;
    --border2:   #253347;
    --t1:        #E8EFF8;
    --t2:        #8FA3BF;
    --t3:        #4A6080;
    --green:     #06D6A0;
    --amber:     #FFB703;
    --orange:    #FB8500;
    --blue:      #3A86FF;
    --blue-dim:  rgba(58,134,255,0.12);
}

/* Global */
.stApp { background: var(--bg0); font-family: 'Barlow', sans-serif; color: var(--t1); }
#MainMenu, footer, .stDeployButton { display: none !important; }
.block-container { padding: 1.5rem 2.5rem 3rem; max-width: 1440px; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg1); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg1) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    font-size: 0.82rem;
    color: var(--t2);
}

/* Input */
.stTextInput > div > div > input {
    background: var(--bg2) !important;
    border: 1px solid var(--border2) !important;
    color: var(--t1) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.05rem !important;
    border-radius: 6px !important;
    padding: 0.65rem 1rem !important;
    letter-spacing: 0.05em;
}
.stTextInput > div > div > input::placeholder { color: var(--t3) !important; }
.stTextInput > div > div > input:focus {
    border-color: var(--red) !important;
    box-shadow: 0 0 0 3px var(--red-glow) !important;
}

/* Button */
.stButton > button {
    background: var(--red) !important;
    color: #fff !important;
    border: none !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 2rem !important;
    border-radius: 5px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #c1121f !important;
    box-shadow: 0 4px 24px var(--red-glow) !important;
    transform: translateY(-1px) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg1) !important;
    border-bottom: 2px solid var(--border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--t3) !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 0.65rem 1.5rem !important;
    border-radius: 0 !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--t1) !important;
    border-bottom: 2px solid var(--red) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--t1) !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
}
.streamlit-expanderContent {
    background: var(--bg1) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 6px 6px !important;
}

/* DataFrame */
.stDataFrame { border-radius: 6px !important; overflow: hidden; }
[data-testid="stDataFrame"] table { background: var(--bg2) !important; }
[data-testid="stDataFrame"] thead th {
    background: var(--bg3) !important;
    color: var(--t2) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-bottom: 2px solid var(--red) !important;
    padding: 0.65rem 0.85rem !important;
}
[data-testid="stDataFrame"] tbody td {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important;
    color: var(--t1) !important;
    border-color: var(--border) !important;
    padding: 0.5rem 0.85rem !important;
    background: var(--bg2) !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: var(--bg3) !important;
}

/* Alerts */
.stAlert { border-radius: 6px !important; }

/* Spinner */
.stSpinner > div { border-top-color: var(--red) !important; }

/* Code blocks */
.stCodeBlock { border-radius: 6px !important; }
pre { background: var(--bg1) !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _badge(text: str, color: str, bg_alpha: float = 0.15) -> str:
    """Generate a small HTML badge span."""
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<span style="'
        f'display:inline-block;'
        f'background:rgba({r},{g},{b},{bg_alpha});'
        f'border:1px solid rgba({r},{g},{b},0.4);'
        f'color:{color};'
        f'font-family:IBM Plex Mono,monospace;'
        f'font-size:0.65rem;'
        f'font-weight:600;'
        f'letter-spacing:0.1em;'
        f'padding:0.15em 0.65em;'
        f'border-radius:3px;'
        f'text-transform:uppercase;'
        f'">{text}</span>'
    )


def _card_html(label: str, value: str, color: str = "#3A86FF", sub: str = "") -> str:
    return f"""
    <div style="
        background:#111824;
        border:1px solid #1E2D42;
        border-left:3px solid {color};
        border-radius:6px;
        padding:1rem 1.25rem;
        height:100%;
    ">
        <div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#4A6080;
                    text-transform:uppercase;letter-spacing:0.18em;margin-bottom:0.3rem;">
            {label}
        </div>
        <div style="font-family:Barlow Condensed,sans-serif;font-size:1.65rem;
                    font-weight:700;color:#E8EFF8;line-height:1;">
            {value}
        </div>
        {"<div style='font-size:0.72rem;color:#8FA3BF;margin-top:0.25rem;'>"+sub+"</div>" if sub else ""}
    </div>"""


def _section_title(text: str):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;margin:2rem 0 1rem;">
        <div style="flex:1;height:1px;background:#1E2D42;"></div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;
                    color:#4A6080;text-transform:uppercase;letter-spacing:0.22em;
                    white-space:nowrap;">
            {text}
        </div>
        <div style="flex:1;height:1px;background:#1E2D42;"></div>
    </div>""", unsafe_allow_html=True)


def _pill_list(items: list[str], color: str = "#3A86FF"):
    pills = " ".join(_badge(i, color) for i in items)
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;">{pills}</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:1rem 0 1.5rem;">
            <div style="font-family:Barlow Condensed,sans-serif;font-size:1.5rem;
                        font-weight:700;color:#E8EFF8;letter-spacing:0.08em;">
                <span style="color:#E63946;">ST</span> Intelligence
            </div>
            <div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;
                        color:#4A6080;letter-spacing:0.15em;text-transform:uppercase;
                        margin-top:0.3rem;">
                Competitive RAG · v1.0
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Groq health ──
        st.markdown("**System Status**")
        healthy, msg = check_groq_health()
        if healthy:
            st.success(f"🟢 Groq Connected", icon=None)
        else:
            st.error(f"🔴 Groq Offline")
        st.caption(f"`{MODEL_NAME}`")

        st.divider()

        # ── Quick launch chips ──
        st.markdown("**Quick Launch**")
        st.caption("Click to auto-fill the search bar:")

        quick_parts = [
            "STM32G474", "STM32H743", "STM32U575",
            "STM32F407", "STM32L476", "STM32WB55",
        ]
        cols = st.columns(2)
        for i, part in enumerate(quick_parts):
            if cols[i % 2].button(part, key=f"quick_{part}", use_container_width=True):
                # Write to the SAME key the text_input widget uses
                st.session_state["product_text_input"] = part
                st.session_state["_auto_analyze"] = part  # flag to trigger analysis
                st.rerun()

        st.divider()

        st.markdown("**About**")
        st.markdown("""
        This tool uses **Synthetic RAG** architecture:
        the LLM's internal semiconductor knowledge
        is structured as if retrieved from a curated
        spec database — giving you high-fidelity
        competitive analysis with zero external data.

        **Engine:** LangChain + Groq  
        **Backend:** FastAPI (port 8000)  
        **Docs:** `/docs`
        """)


# ══════════════════════════════════════════════════════════════════════════════
#  RESULTS RENDERING
# ══════════════════════════════════════════════════════════════════════════════

def render_kpi_bar(result: dict):
    """Top metrics row."""
    data = result.get("data", {})
    conf = data.get("data_confidence", 0)
    conf_label, conf_color = confidence_tier(conf)
    threat = data.get("summary", {}).get("competitive_threat_level", "N/A")
    threat_color = threat_tier_color(threat)
    num_rivals = len(data.get("competitors", []))

    cols = st.columns(5)
    with cols[0]:
        st.markdown(_card_html(
            "ST Product", data.get("st_product", "—"), "#E63946",
            result.get("product_family", "")
        ), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_card_html(
            "Category", data.get("category", "—"), "#3A86FF"
        ), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_card_html(
            "Rivals Analyzed", str(num_rivals), "#FFB703", "Direct competitors"
        ), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(_card_html(
            "Threat Level", threat, threat_color, "vs competitors"
        ), unsafe_allow_html=True)
    with cols[4]:
        st.markdown(_card_html(
            "Data Confidence", f"{conf}%", conf_color, conf_label
        ), unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align:right;margin-top:0.5rem;font-family:IBM Plex Mono,monospace;
                font-size:0.62rem;color:#4A6080;">
        ⏱ {result.get('latency_ms', 0):,} ms · {result.get('model_used', '')}
        · {data.get('analysis_timestamp', '')}
    </div>""", unsafe_allow_html=True)


def render_comparison_table(result: dict):
    """Spec-by-spec comparison table."""
    _section_title("Spec-by-Spec Comparison")

    rows = result.get("table_rows", [])
    if not rows:
        st.warning("No table data available.")
        return

    df = pd.DataFrame(rows)
    if "Parameter" in df.columns:
        df = df.set_index("Parameter")

    st.dataframe(df, use_container_width=True, height=620)


def render_gap_analysis(result: dict):
    """Per-competitor gap analysis in expanders."""
    _section_title("Gap Analysis · Per Competitor")

    competitors = result.get("data", {}).get("competitors", [])
    if not competitors:
        st.info("No competitor data found.")
        return

    for comp in competitors:
        vendor  = comp.get("vendor", "Unknown")
        part    = comp.get("part_number", "Unknown")
        conf    = comp.get("data_confidence", 0)
        severity = comp.get("gap_severity", "MEDIUM")
        _, cconf_color = confidence_tier(conf)
        sev_color = threat_tier_color(severity)

        header = (
            f"{vendor} · {part}  |  "
            f"Confidence: {conf}%  |  Gap Severity: {severity}"
        )

        with st.expander(header, expanded=False):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown(
                    f'<div style="color:#06D6A0;font-family:Barlow Condensed,sans-serif;'
                    f'font-size:1rem;font-weight:700;letter-spacing:0.06em;margin-bottom:0.6rem;">'
                    f'✓ ST ADVANTAGES</div>',
                    unsafe_allow_html=True
                )
                advantages = comp.get("st_advantages", [])
                if advantages:
                    for adv in advantages:
                        st.markdown(
                            f'<div style="background:rgba(6,214,160,0.07);'
                            f'border-left:3px solid #06D6A0;'
                            f'padding:0.45rem 0.75rem;margin-bottom:0.35rem;'
                            f'border-radius:0 4px 4px 0;'
                            f'font-size:0.82rem;color:#8FA3BF;">{adv}</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No specific advantages listed.")

            with c2:
                st.markdown(
                    f'<div style="color:#E63946;font-family:Barlow Condensed,sans-serif;'
                    f'font-size:1rem;font-weight:700;letter-spacing:0.06em;margin-bottom:0.6rem;">'
                    f'✗ ST GAPS / WEAKNESSES</div>',
                    unsafe_allow_html=True
                )
                gaps = comp.get("competitor_advantages", [])
                if gaps:
                    for gap in gaps:
                        st.markdown(
                            f'<div style="background:rgba(230,57,70,0.07);'
                            f'border-left:3px solid #E63946;'
                            f'padding:0.45rem 0.75rem;margin-bottom:0.35rem;'
                            f'border-radius:0 4px 4px 0;'
                            f'font-size:0.82rem;color:#8FA3BF;">{gap}</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.caption("No critical gaps identified.")

            # Mini spec quick-view
            st.markdown("---")
            mc = st.columns(4)
            mc[0].metric("Clock", f"{comp.get('clock_mhz', '—')} MHz")
            mc[1].metric("Flash", f"{comp.get('flash_kb', '—')} KB")
            mc[2].metric("RAM",   f"{comp.get('ram_kb', '—')} KB")
            mc[3].metric("Price", comp.get("price_usd_1k", "—"))


def render_summary(result: dict):
    """Strategic summary section."""
    _section_title("Strategic Intelligence Summary")

    summary = result.get("data", {}).get("summary", {})
    if not summary:
        st.info("No summary data available.")
        return

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            '<div style="font-family:Barlow Condensed,sans-serif;font-weight:700;'
            'font-size:1.05rem;color:#06D6A0;letter-spacing:0.06em;margin-bottom:0.75rem;">'
            '🏆 ST STRENGTHS</div>',
            unsafe_allow_html=True
        )
        for s in summary.get("st_strengths", []):
            st.markdown(
                f'<div style="background:rgba(6,214,160,0.06);border-left:3px solid #06D6A0;'
                f'padding:0.5rem 0.85rem;margin-bottom:0.4rem;border-radius:0 5px 5px 0;'
                f'font-size:0.85rem;color:#8FA3BF;">{s}</div>',
                unsafe_allow_html=True
            )

    with c2:
        st.markdown(
            '<div style="font-family:Barlow Condensed,sans-serif;font-weight:700;'
            'font-size:1.05rem;color:#E63946;letter-spacing:0.06em;margin-bottom:0.75rem;">'
            '⚠ CRITICAL GAPS</div>',
            unsafe_allow_html=True
        )
        for g in summary.get("critical_gaps", []):
            st.markdown(
                f'<div style="background:rgba(230,57,70,0.06);border-left:3px solid #E63946;'
                f'padding:0.5rem 0.85rem;margin-bottom:0.4rem;border-radius:0 5px 5px 0;'
                f'font-size:0.85rem;color:#8FA3BF;">{g}</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # Market positioning statement
    st.markdown(
        '<div style="font-family:Barlow Condensed,sans-serif;font-weight:700;'
        'font-size:1rem;color:#3A86FF;letter-spacing:0.06em;margin-bottom:0.5rem;">'
        '📌 MARKET POSITIONING</div>',
        unsafe_allow_html=True
    )
    positioning = summary.get("market_positioning", "")
    if positioning:
        st.markdown(
            f'<div style="background:#111824;border:1px solid #253347;'
            f'border-radius:6px;padding:1rem 1.25rem;font-size:0.9rem;'
            f'color:#8FA3BF;line-height:1.7;font-style:italic;">'
            f'"{positioning}"</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    apps = summary.get("target_applications", [])
    if apps:
        st.markdown(
            '<div style="font-family:Barlow Condensed,sans-serif;font-weight:700;'
            'font-size:1rem;color:#FFB703;letter-spacing:0.06em;margin-bottom:0.5rem;">'
            '🎯 TARGET APPLICATIONS</div>',
            unsafe_allow_html=True
        )
        _pill_list(apps, "#FFB703")


def render_narrative(narrative: str):
    """Marketing intelligence brief tab."""
    _section_title("Marketing Intelligence Brief")
    if not narrative:
        st.info("No narrative generated.")
        return
    st.markdown(
        f'<div style="background:#0C1018;border:1px solid #1E2D42;border-radius:8px;'
        f'padding:1.75rem 2rem;font-size:0.9rem;line-height:1.85;color:#8FA3BF;">'
        f'{narrative}</div>',
        unsafe_allow_html=True
    )


def render_raw_json(result: dict):
    """Debug tab: raw JSON and response."""
    _section_title("Raw Data · Debug View")
    data = result.get("data")
    if data:
        st.json(data, expanded=False)
    raw = result.get("raw_response", "")
    if raw:
        with st.expander("Full LLM Response (raw text)", expanded=False):
            st.code(raw, language="markdown")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def main():
    render_sidebar()

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:1.5rem 0 1rem;">
        <div style="font-family:Barlow Condensed,sans-serif;font-size:2.2rem;
                    font-weight:700;letter-spacing:0.06em;color:#E8EFF8;">
            <span style="
                color:#E63946;
                background:rgba(230,57,70,0.1);
                border:1px solid rgba(230,57,70,0.3);
                padding:0.05em 0.3em;
                border-radius:4px;
            ">ST</span>
            Competitive Intelligence · Synthetic RAG
        </div>
        <div style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;
                    color:#4A6080;letter-spacing:0.18em;text-transform:uppercase;
                    margin-top:0.4rem;">
            LangChain · Groq · llama-3.3-70b-versatile · FastAPI Backend
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Search bar ──────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
        'color:#4A6080;text-transform:uppercase;letter-spacing:0.18em;margin-bottom:0.5rem;">'
        'Enter ST Product Name or Part Number</div>',
        unsafe_allow_html=True
    )

    # Initialise widget key on first run
    if "product_text_input" not in st.session_state:
        st.session_state["product_text_input"] = ""

    col_in, col_btn = st.columns([4, 1])
    with col_in:
        # key= only — value is managed exclusively via st.session_state["product_text_input"]
        product_input = st.text_input(
            label="product_search",
            placeholder="e.g.  STM32G474   STM32H743   STM32U575   STM32F407",
            label_visibility="collapsed",
            key="product_text_input",
        )
    with col_btn:
        analyze_clicked = st.button(
            "⚡ Analyze",
            use_container_width=True,
            type="primary",
        )

    st.caption(
        "💡 Try: `STM32G474` (Mixed-Signal) · `STM32H743` (High-Performance) · "
        "`STM32U575` (Ultra-Low-Power) · `STM32WB55` (Wireless)"
    )

    # ── Trigger analysis ────────────────────────────────────────────────────
    # Fires on manual Analyze click OR after a Quick Launch button sets _auto_analyze
    auto_part = st.session_state.pop("_auto_analyze", None)
    if auto_part:
        product_input = auto_part          # override with the button-chosen part

    trigger = bool(auto_part) or (analyze_clicked and product_input.strip())

    if trigger:
        st.session_state["last_product"] = product_input.strip()
        st.session_state["result"] = None  # Reset

        with st.spinner(f"🔍 Analyzing **{product_input.strip().upper()}** — querying Groq…"):
            result = get_competitive_analysis(product_input.strip())

        st.session_state["result"] = result

    # ── Render results ──────────────────────────────────────────────────────
    result = st.session_state.get("result")

    if result is None:
        # Landing state
        st.markdown("<br>" * 2, unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;padding:3rem;
                    background:#0C1018;border:1px dashed #1E2D42;border-radius:10px;">
            <div style="font-size:3rem;margin-bottom:1rem;">⚡</div>
            <div style="font-family:Barlow Condensed,sans-serif;font-size:1.4rem;
                        font-weight:600;color:#E8EFF8;letter-spacing:0.05em;
                        margin-bottom:0.5rem;">
                Enter an ST part number to begin
            </div>
            <div style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#4A6080;">
                The Synthetic RAG engine will identify the product category, select 3 rivals,<br>
                and generate a spec-by-spec competitive intelligence report.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Error state ──────────────────────────────────────────────────────────
    if not result.get("success") or result.get("error"):
        st.error(f"**Analysis Error:** {result.get('error', 'Unknown error')}")
        if result.get("raw_response"):
            with st.expander("Raw LLM Response (debug)"):
                st.code(result["raw_response"], language="markdown")
        return

    # ── KPI bar ──────────────────────────────────────────────────────────────
    render_kpi_bar(result)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabbed report ─────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊  Spec Comparison",
        "🔍  Gap Analysis",
        "📌  Strategic Summary",
        "📝  Marketing Brief",
        "🛠  Raw Data",
    ])

    with tab1:
        render_comparison_table(result)

    with tab2:
        render_gap_analysis(result)

    with tab3:
        render_summary(result)

    with tab4:
        render_narrative(result.get("narrative", ""))

    with tab5:
        render_raw_json(result)


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()