"""
FluxLogic - Webhook Manager
=============================
Simulate inbound and outbound webhook events to demonstrate
event-driven automation workflows.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from config import get_settings
from models import WebhookEvent

logger = logging.getLogger("fluxlogic.webhooks")


class WebhookManager:
    """
    Handles creation, signing, sending, and verification of webhook events.

    In a production system this would run its own HTTP server; here we
    simulate the lifecycle so that FluxLogic can demonstrate the pattern
    in a Streamlit context without requiring a separate process.
    """

    def __init__(self, secret: Optional[str] = None) -> None:
        settings = get_settings()
        self._secret: Optional[str] = secret or settings.webhook_secret
        self._event_log: List[WebhookEvent] = []

    # ── Signing ──────────────────────────────────────────────────────

    def sign_payload(self, payload: Dict[str, Any]) -> str:
        """Return HMAC-SHA256 hex digest for *payload*."""
        secret = (self._secret or "fluxlogic-dev-secret").encode()
        body = json.dumps(payload, sort_keys=True, default=str).encode()
        return hmac.new(secret, body, hashlib.sha256).hexdigest()

    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """Verify an inbound webhook's HMAC signature."""
        expected = self.sign_payload(payload)
        return hmac.compare_digest(expected, signature)

    # ── Event creation ───────────────────────────────────────────────

    def create_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "fluxlogic",
    ) -> WebhookEvent:
        """Build a signed :class:`WebhookEvent`."""
        signature = self.sign_payload(payload)
        event = WebhookEvent(
            event_id=uuid4(),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            source=source,
            payload=payload,
            signature=signature,
        )
        self._event_log.append(event)
        logger.info("Created webhook event %s [%s]", event.event_id, event_type)
        return event

    # ── Outbound dispatch ────────────────────────────────────────────

    def send_webhook(
        self,
        url: str,
        event: WebhookEvent,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        POST a webhook event to *url* and return a result dict.
        """
        headers = {
            "Content-Type": "application/json",
            "X-FluxLogic-Event": event.event_type,
            "X-FluxLogic-Signature": event.signature or "",
            "X-FluxLogic-Delivery": str(event.event_id),
        }

        body = event.model_dump(mode="json")
        t0 = time.perf_counter()

        try:
            resp = requests.post(url, json=body, headers=headers, timeout=timeout)
            latency = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(
                "Webhook %s sent to %s → %d (%.1f ms)",
                event.event_id,
                url,
                resp.status_code,
                latency,
            )
            return {
                "success": 200 <= resp.status_code < 300,
                "status_code": resp.status_code,
                "latency_ms": latency,
                "response": resp.text[:1000],
            }

        except requests.exceptions.RequestException as exc:
            logger.error("Webhook delivery failed: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── Inbound simulation ───────────────────────────────────────────

    def simulate_inbound(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> WebhookEvent:
        """
        Simulate receiving an external webhook. Creates the event,
        verifies the signature, and logs the result.
        """
        event = self.create_event(event_type, payload, source="external-simulation")
        verified = self.verify_signature(payload, event.signature or "")
        logger.info(
            "Simulated inbound webhook %s – signature verified: %s",
            event.event_id,
            verified,
        )
        return event

    # ── History ──────────────────────────────────────────────────────

    @property
    def event_log(self) -> List[WebhookEvent]:
        """Return a copy of the internal event log."""
        return list(self._event_log)

    def clear_log(self) -> None:
        self._event_log.clear()
