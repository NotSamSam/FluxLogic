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

    def __init__(self, secret: Optional[str] = None) -> None:
        settings = get_settings()
        self._secret: Optional[str] = secret or settings.webhook_secret
        self._event_log: List[WebhookEvent] = []

    def sign_payload(self, payload: Dict[str, Any]) -> str:
        secret = (self._secret or "fluxlogic-dev-secret").encode()
        body = json.dumps(payload, sort_keys=True, default=str).encode()
        return hmac.new(secret, body, hashlib.sha256).hexdigest()

    def verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        expected = self.sign_payload(payload)
        return hmac.compare_digest(expected, signature)

    def create_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "fluxlogic",
    ) -> WebhookEvent:
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

    def send_webhook(
        self,
        url: str,
        event: WebhookEvent,
        timeout: int = 10,
    ) -> Dict[str, Any]:
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
            logger.info("Webhook %s → %s — %d (%.1f ms)", event.event_id, url, resp.status_code, latency)
            return {
                "success": 200 <= resp.status_code < 300,
                "status_code": resp.status_code,
                "latency_ms": latency,
                "response": resp.text[:1000],
            }

        except requests.exceptions.RequestException as exc:
            logger.error("Webhook delivery failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def simulate_inbound(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> WebhookEvent:
        event = self.create_event(event_type, payload, source="external-simulation")
        verified = self.verify_signature(payload, event.signature or "")
        logger.info("Simulated inbound %s — verified: %s", event.event_id, verified)
        return event

    @property
    def event_log(self) -> List[WebhookEvent]:
        return list(self._event_log)

    def clear_log(self) -> None:
        self._event_log.clear()
