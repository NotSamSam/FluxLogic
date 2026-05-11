"""
FluxLogic | Universal Data Connector
======================================
Streamlit-based dashboard for uploading data, configuring API endpoints,
processing records, and dispatching them to external services.

Launch:
    streamlit run fluxlogic_app.py
"""

from __future__ import annotations

import io
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# ── Local imports ────────────────────────────────────────────────────
from config import get_settings
from models import ApiEndpoint, DataFormat, FlowLogEntry, FlowStatus, HttpMethod
from processor import DataProcessor
from api_client import ApiClient
from webhooks import WebhookManager

# ── Logging setup ────────────────────────────────────────────────────
settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format=settings.log_format,
    stream=sys.stdout,
)
logger = logging.getLogger("fluxlogic.app")

# ── Page configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="FluxLogic | Universal Data Connector",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for premium look ──────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ──────────────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* ── Hero header ─────────────────────────────────────────── */
    .hero-container {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #a78bfa, #38bdf8, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        font-weight: 400;
        margin-top: 0.5rem;
    }

    /* ── Metric cards ────────────────────────────────────────── */
    .metric-card {
        background: linear-gradient(145deg, #1e1b4b 0%, #1e293b 100%);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 28px rgba(139, 92, 246, 0.15);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #a78bfa;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.2rem;
    }

    /* ── Status badges ───────────────────────────────────────── */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .badge-success { background: #065f46; color: #34d399; }
    .badge-warning { background: #78350f; color: #fbbf24; }
    .badge-error   { background: #7f1d1d; color: #f87171; }
    .badge-info    { background: #1e3a5f; color: #38bdf8; }

    /* ── Log table ───────────────────────────────────────────── */
    .log-row {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
        color: #e2e8f0;
    }

    /* ── Sidebar ─────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #1a1a2e 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #a78bfa;
    }

    /* ── Dividers ────────────────────────────────────────────── */
    .section-divider {
        border: none;
        border-top: 1px solid rgba(139, 92, 246, 0.15);
        margin: 1.5rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════
# SESSION STATE HELPERS
# ══════════════════════════════════════════════════════════════════════

def _init_state() -> None:
    """Initialise session-state keys if absent."""
    defaults: Dict[str, Any] = {
        "endpoints": [],
        "flow_log": [],
        "uploaded_df": None,
        "batch_result": None,
        "webhook_events": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR – Endpoint Configuration
# ══════════════════════════════════════════════════════════════════════

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## ⚙️ API Endpoints")
        st.caption("Configure the target APIs where processed data will be dispatched.")

        with st.expander("➕ Add New Endpoint", expanded=len(st.session_state.endpoints) == 0):
            name = st.text_input("Endpoint Name", placeholder="e.g. CRM Webhook", key="ep_name")
            url = st.text_input("URL", placeholder="https://api.example.com/data", key="ep_url")
            method = st.selectbox("HTTP Method", [m.value for m in HttpMethod], key="ep_method")
            api_key = st.text_input("API Key (optional)", type="password", key="ep_key")
            timeout = st.slider("Timeout (s)", 1, 120, 30, key="ep_timeout")

            custom_headers_raw = st.text_area(
                "Custom Headers (JSON)",
                placeholder='{"X-Custom": "value"}',
                height=80,
                key="ep_headers",
            )

            if st.button("💾 Save Endpoint", use_container_width=True):
                if not name or not url:
                    st.error("Name and URL are required.")
                else:
                    headers: Dict[str, str] = {}
                    if custom_headers_raw.strip():
                        try:
                            headers = json.loads(custom_headers_raw)
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in custom headers.")
                            return

                    try:
                        ep = ApiEndpoint(
                            name=name,
                            url=url,
                            method=HttpMethod(method),
                            headers=headers,
                            api_key=api_key or None,
                            timeout=timeout,
                        )
                        st.session_state.endpoints.append(ep)
                        st.success(f"✓ Endpoint **{name}** saved.")
                        logger.info("Endpoint added: %s → %s", name, url)
                    except Exception as exc:
                        st.error(f"Validation error: {exc}")

        if st.session_state.endpoints:
            st.markdown("### 📡 Active Endpoints")
            for i, ep in enumerate(st.session_state.endpoints):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"**{ep.name}**  \n"
                        f"`{ep.method.value}` → `{ep.url}`"
                    )
                with col2:
                    if st.button("🗑️", key=f"del_ep_{i}"):
                        st.session_state.endpoints.pop(i)
                        st.rerun()

        st.markdown("---")
        st.markdown("### 🔧 Settings")
        st.caption(f"App version: **{settings.app_version}**")
        st.caption(f"Batch size: **{settings.batch_size}**")
        st.caption(f"Max retries: **{settings.max_retries}**")
        st.caption(f"Timeout: **{settings.default_timeout}s**")


# ══════════════════════════════════════════════════════════════════════
# HERO HEADER
# ══════════════════════════════════════════════════════════════════════

def _render_header() -> None:
    st.markdown(
        """
        <div class="hero-container">
            <p class="hero-title">⚡ FluxLogic</p>
            <p class="hero-subtitle">Universal Data Connector — Upload, Process & Dispatch in Seconds</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
# METRICS BAR
# ══════════════════════════════════════════════════════════════════════

def _render_metrics() -> None:
    c1, c2, c3, c4 = st.columns(4)
    total_flows = len(st.session_state.flow_log)
    total_records = sum(f.records_sent for f in st.session_state.flow_log)
    success_flows = sum(1 for f in st.session_state.flow_log if f.status == FlowStatus.SUCCESS)
    endpoints_count = len(st.session_state.endpoints)

    for col, value, label in [
        (c1, total_flows, "Flows Executed"),
        (c2, total_records, "Records Sent"),
        (c3, success_flows, "Successful"),
        (c4, endpoints_count, "Endpoints"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{value}</div>'
                f'<div class="metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════
# TAB 1 – Data Upload & Processing
# ══════════════════════════════════════════════════════════════════════

def _tab_data_upload() -> None:
    st.markdown("### 📂 Data Ingestion")

    input_mode = st.radio(
        "Choose input method",
        ["Upload File (CSV / JSON)", "Manual Entry (JSON)"],
        horizontal=True,
        key="input_mode",
    )

    df: pd.DataFrame | None = None

    if input_mode == "Upload File (CSV / JSON)":
        uploaded = st.file_uploader(
            "Drop a file here",
            type=["csv", "json"],
            key="file_uploader",
        )
        if uploaded is not None:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    raw = json.loads(uploaded.read().decode())
                    df = pd.json_normalize(raw if isinstance(raw, list) else [raw])
                st.session_state.uploaded_df = df
            except Exception as exc:
                st.error(f"Failed to parse file: {exc}")

    else:
        sample = json.dumps(
            [{"name": "Alice", "email": "alice@example.com", "score": "95"}],
            indent=2,
        )
        manual_json = st.text_area(
            "Paste JSON data",
            value=sample,
            height=200,
            key="manual_json",
        )
        if st.button("📥 Load JSON", key="load_json"):
            try:
                parsed = json.loads(manual_json)
                df = pd.json_normalize(parsed if isinstance(parsed, list) else [parsed])
                st.session_state.uploaded_df = df
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON: {exc}")

    if st.session_state.uploaded_df is not None:
        df = st.session_state.uploaded_df
        st.markdown("#### 👁️ Data Preview")
        st.dataframe(df.head(50), use_container_width=True)
        st.caption(f"{len(df)} rows × {len(df.columns)} columns")

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("### 🔄 Process Data")

        req_fields_raw = st.text_input(
            "Required fields (comma-separated)",
            placeholder="name, email",
            key="req_fields",
        )
        required_fields = [f.strip() for f in req_fields_raw.split(",") if f.strip()] if req_fields_raw else []

        if st.button("▶️ Run Processing Pipeline", type="primary", use_container_width=True):
            with st.spinner("Processing…"):
                processor = DataProcessor(required_fields=required_fields)
                batch = processor.process_dataframe(df)
                st.session_state.batch_result = batch

            if batch.status == FlowStatus.SUCCESS:
                st.success(f"✅ All **{batch.valid_records}** records are valid — ready to dispatch.")
            elif batch.status == FlowStatus.PARTIAL_FAILURE:
                st.warning(
                    f"⚠️ {batch.valid_records} valid / {batch.invalid_records} invalid records."
                )
            else:
                st.error(f"❌ Processing failed — {batch.invalid_records} invalid records.")

            # Show invalid record details
            invalid = [r for r in batch.results if not r.is_valid]
            if invalid:
                with st.expander(f"🔍 {len(invalid)} validation errors", expanded=False):
                    for r in invalid[:20]:
                        st.markdown(f"**Row {r.index}**: {', '.join(r.errors)}")
                        st.json(r.original)


# ══════════════════════════════════════════════════════════════════════
# TAB 2 – API Dispatch
# ══════════════════════════════════════════════════════════════════════

def _tab_dispatch() -> None:
    st.markdown("### 🚀 Dispatch to APIs")

    batch = st.session_state.batch_result
    if batch is None:
        st.info("💡 Process some data first (see the **Data Upload** tab).")
        return

    valid_records = [r.processed for r in batch.results if r.is_valid and r.processed]
    if not valid_records:
        st.warning("No valid records to dispatch.")
        return

    st.success(f"**{len(valid_records)}** records ready for dispatch.")

    if not st.session_state.endpoints:
        st.warning("No endpoints configured. Use the sidebar to add one.")
        return

    selected_ep_name = st.selectbox(
        "Target endpoint",
        [ep.name for ep in st.session_state.endpoints],
        key="dispatch_ep",
    )

    if st.button("📤 Dispatch Now", type="primary", use_container_width=True):
        endpoint = next(ep for ep in st.session_state.endpoints if ep.name == selected_ep_name)
        client = ApiClient()

        with st.spinner(f"Dispatching to **{endpoint.name}**…"):
            results = client.dispatch_batch(endpoint, valid_records)

        for res in results:
            if res.success:
                st.success(
                    f"✓ **{res.endpoint_name}** — HTTP {res.status_code} "
                    f"({res.latency_ms} ms)"
                )
            else:
                st.error(
                    f"✗ **{res.endpoint_name}** — "
                    f"{res.error_message or f'HTTP {res.status_code}'}"
                )

        # Log
        log_entry = FlowLogEntry(
            source_format=DataFormat.CSV,
            endpoint=str(endpoint.url),
            status=FlowStatus.SUCCESS if all(r.success for r in results) else FlowStatus.PARTIAL_FAILURE,
            records_sent=len(valid_records),
            errors=[r.error_message for r in results if r.error_message],
        )
        st.session_state.flow_log.append(log_entry)
        client.close()


# ══════════════════════════════════════════════════════════════════════
# TAB 3 – Webhooks
# ══════════════════════════════════════════════════════════════════════

def _tab_webhooks() -> None:
    st.markdown("### 🔔 Webhook Simulation")
    st.caption(
        "Simulate inbound and outbound webhook events to test "
        "event-driven automation workflows."
    )

    wh = WebhookManager()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📩 Simulate Inbound Webhook")
        event_type = st.selectbox(
            "Event type",
            ["data.received", "flow.completed", "error.raised", "custom"],
            key="wh_event_type",
        )
        if event_type == "custom":
            event_type = st.text_input("Custom event type", key="wh_custom_type")

        payload_raw = st.text_area(
            "Payload (JSON)",
            value='{"source": "external-crm", "action": "contact.created", "id": 42}',
            height=120,
            key="wh_payload",
        )

        if st.button("⚡ Receive Webhook", use_container_width=True):
            try:
                payload = json.loads(payload_raw)
                event = wh.simulate_inbound(event_type, payload)
                st.session_state.webhook_events.append(event)
                st.success(f"✓ Webhook received — ID: `{event.event_id}`")
                st.json(event.model_dump(mode="json"))
            except json.JSONDecodeError:
                st.error("Invalid JSON payload.")

    with col2:
        st.markdown("#### 📤 Send Outbound Webhook")
        target_url = st.text_input(
            "Target URL",
            placeholder="https://webhook.site/your-uuid",
            key="wh_target",
        )
        out_payload_raw = st.text_area(
            "Payload (JSON)",
            value='{"flow_id": "demo-123", "status": "completed", "records": 50}',
            height=120,
            key="wh_out_payload",
        )

        if st.button("🚀 Send Webhook", use_container_width=True):
            if not target_url:
                st.error("Target URL is required.")
            else:
                try:
                    payload = json.loads(out_payload_raw)
                    event = wh.create_event("flow.dispatched", payload)
                    result = wh.send_webhook(target_url, event)
                    st.session_state.webhook_events.append(event)
                    if result.get("success"):
                        st.success(
                            f"✓ Delivered — HTTP {result['status_code']} "
                            f"({result['latency_ms']} ms)"
                        )
                    else:
                        st.error(f"Delivery failed: {result.get('error', 'Unknown')}")
                except json.JSONDecodeError:
                    st.error("Invalid JSON payload.")

    # Event history
    if st.session_state.webhook_events:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("#### 📋 Event History")
        for evt in reversed(st.session_state.webhook_events[-20:]):
            badge_class = "badge-info" if evt.source == "fluxlogic" else "badge-success"
            st.markdown(
                f'<div class="log-row">'
                f'<span class="badge {badge_class}">{evt.event_type}</span> '
                f'&nbsp; <code>{evt.event_id}</code> '
                f'&nbsp; from <strong>{evt.source}</strong> '
                f'&nbsp; at {evt.timestamp.strftime("%H:%M:%S")}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════
# TAB 4 – Flow Log / Audit
# ══════════════════════════════════════════════════════════════════════

def _tab_flow_log() -> None:
    st.markdown("### 📜 Flow Execution Log")

    if not st.session_state.flow_log:
        st.info("No flows executed yet. Process and dispatch data to generate entries.")
        return

    for entry in reversed(st.session_state.flow_log):
        status_badge = {
            FlowStatus.SUCCESS: "badge-success",
            FlowStatus.PARTIAL_FAILURE: "badge-warning",
            FlowStatus.FAILED: "badge-error",
        }.get(entry.status, "badge-info")

        st.markdown(
            f'<div class="log-row">'
            f'<span class="badge {status_badge}">{entry.status.value}</span> '
            f'&nbsp; <strong>{entry.records_sent}</strong> records → '
            f'<code>{entry.endpoint}</code> '
            f'&nbsp; ({entry.source_format.value.upper()}) '
            f'&nbsp; at {entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
            f'</div>',
            unsafe_allow_html=True,
        )

    if st.button("🗑️ Clear Log", key="clear_log"):
        st.session_state.flow_log.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    _render_sidebar()
    _render_header()
    _render_metrics()

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📂 Data Upload",
        "🚀 API Dispatch",
        "🔔 Webhooks",
        "📜 Flow Log",
    ])

    with tab1:
        _tab_data_upload()
    with tab2:
        _tab_dispatch()
    with tab3:
        _tab_webhooks()
    with tab4:
        _tab_flow_log()

    # Footer
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.caption(
        f"FluxLogic v{settings.app_version} · Built with Streamlit · "
        f"© {datetime.now().year} FluxLogic Engineering"
    )


if __name__ == "__main__":
    main()
