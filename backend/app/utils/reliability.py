"""Shared validation, retry, duplicate-operation, and error-reporting helpers."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

import pandas as pd
from fastapi import HTTPException

T = TypeVar("T")


def validate_non_empty_text(
    value: str, field_name: str, max_length: int | None = None
) -> str:
    """Validate text at service boundaries that do not use a Pydantic model."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    normalized = value.strip()
    if max_length is not None and len(normalized) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return normalized


def validate_dataframe(
    dataframe: Any,
    *,
    field_name: str = "dataset",
    max_rows: int | None = None,
    max_columns: int | None = None,
) -> pd.DataFrame:
    """Validate the dataframe contract shared by EDA, ML, and preprocessing."""
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError(f"{field_name} must be a pandas DataFrame")
    if dataframe.empty:
        raise ValueError(f"{field_name} must contain at least one data row")
    if dataframe.columns.empty:
        raise ValueError(f"{field_name} must contain at least one column")
    if not dataframe.columns.is_unique:
        raise ValueError(f"{field_name} columns must be unique")
    if max_rows is not None and len(dataframe) > max_rows:
        raise ValueError(f"{field_name} exceeds the {max_rows} row limit")
    if max_columns is not None and len(dataframe.columns) > max_columns:
        raise ValueError(f"{field_name} exceeds the {max_columns} column limit")
    return dataframe


def log_failure(
    logger: logging.Logger,
    event: str,
    exc: BaseException,
    **context: Any,
) -> None:
    """Log safe diagnostics without serializing exception messages or payloads."""
    safe_context = {
        key: value
        for key, value in context.items()
        if key not in {"api_key", "secret", "token", "password", "request_body"}
    }
    logger.error(
        "%s failed: error_type=%s context=%s",
        event,
        type(exc).__name__,
        safe_context,
    )


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 2,
    retryable: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError),
    delay_seconds: float = 0.1,
    logger: logging.Logger | None = None,
    operation_name: str = "operation",
) -> T:
    """Retry transient failures a bounded number of times, never indefinitely."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must not be negative")

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retryable as exc:
            if attempt == attempts:
                raise
            if logger:
                logger.warning(
                    "%s transient failure: attempt=%s/%s error_type=%s",
                    operation_name,
                    attempt,
                    attempts,
                    type(exc).__name__,
                )
            await asyncio.sleep(delay_seconds * attempt)
    raise RuntimeError("retry operation did not complete")


class InFlightOperationGuard:
    """Thread-safe guard that prevents duplicate concurrent operations by key."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: set[str] = set()

    def try_acquire(self, key: str) -> bool:
        with self._lock:
            if key in self._active:
                return False
            self._active.add(key)
            return True

    def release(self, key: str) -> None:
        with self._lock:
            self._active.discard(key)

    @contextmanager
    def hold(self, key: str) -> Iterator[None]:
        if not self.try_acquire(key):
            raise HTTPException(
                status_code=409,
                detail="An identical operation is already in progress.",
            )
        try:
            yield
        finally:
            self.release(key)
