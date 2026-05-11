from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


class DataFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    MANUAL = "manual"


class FlowStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ApiEndpoint(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    url: HttpUrl
    method: HttpMethod = Field(default=HttpMethod.POST)
    headers: Dict[str, str] = Field(default_factory=dict)
    api_key: Optional[str] = Field(default=None)
    timeout: int = Field(default=30, ge=1, le=120)

    @field_validator("headers")
    @classmethod
    def _lower_header_keys(cls, v: Dict[str, str]) -> Dict[str, str]:
        return {k.lower(): val for k, val in v.items()}


class ProcessingResult(BaseModel):
    index: int = Field(..., ge=0)
    original: Dict[str, Any]
    processed: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    is_valid: bool = True


class BatchResult(BaseModel):
    flow_id: UUID = Field(default_factory=uuid4)
    status: FlowStatus = FlowStatus.PENDING
    total_records: int = Field(default=0, ge=0)
    valid_records: int = Field(default=0, ge=0)
    invalid_records: int = Field(default=0, ge=0)
    results: List[ProcessingResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = Field(default=None, ge=0)


class ApiDispatchResult(BaseModel):
    endpoint_name: str
    status_code: Optional[int] = None
    success: bool = False
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = Field(default=None, ge=0)


class WebhookEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="fluxlogic")
    payload: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = None


class FlowLogEntry(BaseModel):
    flow_id: UUID = Field(default_factory=uuid4)
    source_format: DataFormat
    endpoint: str
    status: FlowStatus
    records_sent: int = Field(default=0, ge=0)
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
