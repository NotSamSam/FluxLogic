from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

import pandas as pd

from models import BatchResult, FlowStatus, ProcessingResult

logger = logging.getLogger("fluxlogic.processor")


class DataProcessor:

    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        custom_transforms: Optional[List[Callable[[Dict[str, Any]], Dict[str, Any]]]] = None,
        drop_duplicates: bool = True,
    ) -> None:
        self._required_fields: List[str] = required_fields or []
        self._custom_transforms: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = custom_transforms or []
        self._drop_duplicates = drop_duplicates

    def process(self, records: Sequence[Dict[str, Any]]) -> BatchResult:
        t0 = time.perf_counter()
        batch = BatchResult(total_records=len(records))
        batch.status = FlowStatus.PROCESSING

        results: List[ProcessingResult] = []
        valid = 0
        invalid = 0

        for idx, raw in enumerate(records):
            pr = self._process_single(idx, raw)
            results.append(pr)
            if pr.is_valid:
                valid += 1
            else:
                invalid += 1

        batch.results = results
        batch.valid_records = valid
        batch.invalid_records = invalid
        batch.completed_at = datetime.utcnow()
        batch.duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        if invalid == 0:
            batch.status = FlowStatus.SUCCESS
        elif valid > 0:
            batch.status = FlowStatus.PARTIAL_FAILURE
        else:
            batch.status = FlowStatus.FAILED

        logger.info(
            "Batch %s — %d valid / %d invalid in %.1f ms",
            batch.flow_id, valid, invalid, batch.duration_ms,
        )
        return batch

    def process_dataframe(self, df: pd.DataFrame) -> BatchResult:
        if self._drop_duplicates:
            before = len(df)
            df = df.drop_duplicates()
            dropped = before - len(df)
            if dropped:
                logger.info("Dropped %d duplicate rows", dropped)

        records = df.to_dict(orient="records")
        return self.process(records)

    def _process_single(self, idx: int, raw: Dict[str, Any]) -> ProcessingResult:
        errors: List[str] = []
        record = dict(raw)

        try:
            record = self._strip_whitespace(record)
            record = self._normalize_keys(record)
            record = self._coerce_types(record)

            if self._is_empty_row(record):
                errors.append("Empty row – all values are null or blank")
                return ProcessingResult(index=idx, original=raw, errors=errors, is_valid=False)

            for transform_fn in self._custom_transforms:
                record = transform_fn(record)

            field_errors = self._validate(record)
            errors.extend(field_errors)

        except Exception as exc:
            logger.exception("Unexpected error processing record %d", idx)
            errors.append(f"Processing exception: {exc}")

        is_valid = len(errors) == 0
        return ProcessingResult(
            index=idx,
            original=raw,
            processed=record if is_valid else None,
            errors=errors,
            is_valid=is_valid,
        )

    @staticmethod
    def _strip_whitespace(record: Dict[str, Any]) -> Dict[str, Any]:
        return {k: (v.strip() if isinstance(v, str) else v) for k, v in record.items()}

    @staticmethod
    def _normalize_keys(record: Dict[str, Any]) -> Dict[str, Any]:
        def _snake(key: str) -> str:
            key = key.strip().lower()
            key = re.sub(r"[\s\-]+", "_", key)
            key = re.sub(r"[^\w]", "", key)
            return key
        return {_snake(k): v for k, v in record.items()}

    @staticmethod
    def _coerce_types(record: Dict[str, Any]) -> Dict[str, Any]:
        coerced: Dict[str, Any] = {}
        for k, v in record.items():
            if isinstance(v, str):
                low = v.lower()
                if low in ("true", "false"):
                    coerced[k] = low == "true"
                    continue
                try:
                    coerced[k] = int(v)
                    continue
                except ValueError:
                    pass
                try:
                    coerced[k] = float(v)
                    continue
                except ValueError:
                    pass
            coerced[k] = v
        return coerced

    @staticmethod
    def _is_empty_row(record: Dict[str, Any]) -> bool:
        return all(
            v is None or (isinstance(v, str) and v.strip() == "")
            for v in record.values()
        )

    def _validate(self, record: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for field in self._required_fields:
            if field not in record or record[field] is None or record[field] == "":
                errors.append(f"Missing required field: '{field}'")
        return errors
