"""
FluxLogic - Pydantic Data Models
=================================
Strict schema definitions for every data structure that flows through the
system: API endpoints, processing results, webhook payloads, and logs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ── Enums ────────────────────────────────────────────────────────────


class DataFormat(str, Enum):
    """Supported inbound data formats."""
    CSV = "csv"
    JSON = "json"
    MANUAL = "manual"


class FlowStatus(str, Enum):
    """Lifecycle states for a data-processing flow."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class HttpMethod(str, Enum):
    """HTTP methods supported for outbound API calls."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


# ── API Endpoint Configuration ───────────────────────────────────────


class ApiEndpoint(BaseModel):
    """
    Represents a single target API endpoint to which processed data
    will be pushed.
    """
    name: str = Field(..., min_length=1, max_length=120, description="Human-readable endpoint label")
    url: HttpUrl = Field(..., description="Full URL of the target API")
    method: HttpMethod = Field(default=HttpMethod.POST, description="HTTP method to use")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")
    api_key: Optional[str] = Field(default=None, description="Bearer / API key (sent as Authorization header)")
    timeout: int = Field(default=30, ge=1, le=120, description="Request timeout in seconds")

    @field_validator("headers")
    @classmethod
    def _lower_header_keys(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Normalize header keys to lowercase for consistency."""
        return {k.lower(): val for k, val in v.items()}


# ── Processing Models ────────────────────────────────────────────────


class ProcessingResult(BaseModel):
    """Result of a single record's processing step."""
    index: int = Field(..., ge=0, description="Row/record index in the source data")
    original: Dict[str, Any] = Field(..., description="Original record before processing")
    processed: Optional[Dict[str, Any]] = Field(default=None, description="Cleaned & normalized record")
    errors: List[str] = Field(default_factory=list, description="Validation or cleaning errors")
    is_valid: bool = Field(default=True, description="Whether the record passed validation")


class BatchResult(BaseModel):
    """Aggregated result for a full processing batch."""
    flow_id: UUID = Field(default_factory=uuid4)
    status: FlowStatus = Field(default=FlowStatus.PENDING)
    total_records: int = Field(default=0, ge=0)
    valid_records: int = Field(default=0, ge=0)
    invalid_records: int = Field(default=0, ge=0)
    results: List[ProcessingResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[float] = Field(default=None, ge=0)


# ── API Dispatch Models ──────────────────────────────────────────────


class ApiDispatchResult(BaseModel):
    """Outcome of pushing one batch to a target API."""
    endpoint_name: str
    status_code: Optional[int] = None
    success: bool = False
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = Field(default=None, ge=0)


# ── Webhook Models ───────────────────────────────────────────────────


class WebhookEvent(BaseModel):
    """Inbound or outbound webhook event payload."""
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(..., min_length=1, description="e.g. 'data.received', 'flow.completed'")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="fluxlogic", description="Origin system identifier")
    payload: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = Field(default=None, description="HMAC-SHA256 hex digest for verification")


# ── Flow Log ─────────────────────────────────────────────────────────


class FlowLogEntry(BaseModel):
    """Immutable audit-log entry for one execution of a flow."""
    flow_id: UUID = Field(default_factory=uuid4)
    source_format: DataFormat
    endpoint: str
    status: FlowStatus
    records_sent: int = Field(default=0, ge=0)
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
