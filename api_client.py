from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_settings
from models import ApiDispatchResult, ApiEndpoint

logger = logging.getLogger("fluxlogic.api_client")


class ApiClient:

    def __init__(self) -> None:
        settings = get_settings()
        self._session = self._build_session(
            max_retries=settings.max_retries,
            backoff_factor=settings.retry_backoff_factor,
        )

    @staticmethod
    def _build_session(max_retries: int, backoff_factor: float) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def dispatch(
        self,
        endpoint: ApiEndpoint,
        payload: List[Dict[str, Any]],
    ) -> ApiDispatchResult:
        headers = dict(endpoint.headers)
        headers.setdefault("content-type", "application/json")
        if endpoint.api_key:
            headers["authorization"] = f"Bearer {endpoint.api_key}"

        url = str(endpoint.url)
        method = endpoint.method.value

        logger.info("Dispatching %d records → %s %s", len(payload), method, url)
        t0 = time.perf_counter()

        try:
            response = self._session.request(
                method=method,
                url=url,
                json={"data": payload},
                headers=headers,
                timeout=endpoint.timeout,
            )
            latency = round((time.perf_counter() - t0) * 1000, 2)
            success = 200 <= response.status_code < 300

            result = ApiDispatchResult(
                endpoint_name=endpoint.name,
                status_code=response.status_code,
                success=success,
                response_body=response.text[:2000],
                latency_ms=latency,
            )

            if success:
                logger.info("%s responded %d in %.1f ms", endpoint.name, response.status_code, latency)
            else:
                logger.warning("%s responded %d: %s", endpoint.name, response.status_code, response.text[:500])

            return result

        except requests.exceptions.Timeout:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("Timeout after %.1f ms for %s", latency, endpoint.name)
            return ApiDispatchResult(
                endpoint_name=endpoint.name,
                success=False,
                error_message=f"Request timed out after {endpoint.timeout}s",
                latency_ms=latency,
            )

        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error for %s: %s", endpoint.name, exc)
            return ApiDispatchResult(
                endpoint_name=endpoint.name,
                success=False,
                error_message=f"Connection error: {exc}",
            )

        except requests.exceptions.RequestException as exc:
            logger.error("Request failed for %s: %s", endpoint.name, exc)
            return ApiDispatchResult(
                endpoint_name=endpoint.name,
                success=False,
                error_message=str(exc),
            )

    def dispatch_batch(
        self,
        endpoint: ApiEndpoint,
        records: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
    ) -> List[ApiDispatchResult]:
        if batch_size is None:
            batch_size = get_settings().batch_size

        results: List[ApiDispatchResult] = []
        for i in range(0, len(records), batch_size):
            chunk = records[i : i + batch_size]
            logger.info("Sending batch %d–%d of %d", i, i + len(chunk), len(records))
            results.append(self.dispatch(endpoint, chunk))
        return results

    def close(self) -> None:
        self._session.close()
