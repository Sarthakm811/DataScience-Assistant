import asyncio
import pandas as pd
import pytest
from fastapi import HTTPException

from app.utils.reliability import (
    InFlightOperationGuard,
    retry_async,
    validate_dataframe,
    validate_non_empty_text,
)


def test_validate_non_empty_text_normalizes_and_bounds():
    assert validate_non_empty_text("  query  ", "query", 10) == "query"
    with pytest.raises(ValueError, match="must not be empty"):
        validate_non_empty_text("   ", "query")
    with pytest.raises(ValueError, match="at most"):
        validate_non_empty_text("too long", "query", 3)


def test_validate_dataframe_rejects_invalid_contracts():
    with pytest.raises(ValueError, match="pandas DataFrame"):
        validate_dataframe([{"value": 1}])
    with pytest.raises(ValueError, match="at least one data row"):
        validate_dataframe(pd.DataFrame())
    with pytest.raises(ValueError, match="columns must be unique"):
        validate_dataframe(pd.DataFrame([[1, 2]], columns=["value", "value"]))


def test_retry_async_retries_only_transient_failures():
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("temporary")
        return "ok"

    assert asyncio.run(retry_async(flaky, attempts=3, delay_seconds=0)) == "ok"
    assert attempts == 3


def test_retry_async_does_not_retry_permanent_failures():
    attempts = 0

    async def broken():
        nonlocal attempts
        attempts += 1
        raise ValueError("invalid")

    with pytest.raises(ValueError):
        asyncio.run(retry_async(broken, attempts=3, delay_seconds=0))
    assert attempts == 1


def test_operation_guard_releases_after_failure():
    guard = InFlightOperationGuard()
    with pytest.raises(HTTPException) as error:
        with guard.hold("same"):
            with guard.hold("same"):
                pass
    assert error.value.status_code == 409
    with guard.hold("same"):
        pass
