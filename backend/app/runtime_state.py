"""
Shared in-memory runtime state for API routers.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from contextvars import ContextVar, Token
from typing import Any, Dict, List, TypeVar, Generic
import io
import logging
import time

import pandas as pd
import numpy as np
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.eda_engine import EDAEngine
from app.ml_engine import MLEngine
from app.preprocessing import DataPreprocessor
from app.utils.config import settings

logger = logging.getLogger(__name__)

K = TypeVar("K")
V = TypeVar("V")

_CURRENT_TENANT: ContextVar[str] = ContextVar("current_tenant", default="public")


def get_current_tenant() -> str:
    return _CURRENT_TENANT.get()


def set_current_tenant(tenant_id: str) -> Token:
    return _CURRENT_TENANT.set(tenant_id)


def reset_tenant(token: Token) -> None:
    _CURRENT_TENANT.reset(token)


class _CappedChatHistory(list[Dict[str, str]]):
    def append(self, item: Dict[str, str]) -> None:
        if len(self) >= settings.max_chat_messages_per_session:
            raise _capacity_error(
                "chat history",
                f"maximum of {settings.max_chat_messages_per_session} messages per session",
            )
        super().append(item)


class TenantScopedDict(MutableMapping[K, V], Generic[K, V]):
    """Dictionary facade that isolates state per tenant context."""

    def __init__(
        self,
        name: str,
        max_items_setting: str | None = None,
        memory_limited: bool = False,
    ):
        self.name = name
        self.max_items_setting = max_items_setting
        self.memory_limited = memory_limited
        self._store: Dict[str, Dict[K, V]] = {}
        _TENANT_STORES.append(self)

    def _bucket(self) -> Dict[K, V]:
        tenant = get_current_tenant()
        _ensure_tenant(tenant)
        _touch_tenant(tenant)
        if tenant not in self._store:
            self._store[tenant] = {}
        return self._store[tenant]

    def __getitem__(self, key: K) -> V:
        return self._bucket()[key]

    def __setitem__(self, key: K, value: V) -> None:
        bucket = self._bucket()
        is_new = key not in bucket
        if is_new and self.max_items_setting:
            maximum = int(getattr(settings, self.max_items_setting))
            if len(bucket) >= maximum:
                raise _capacity_error(self.name, f"maximum of {maximum} items")
        if self.memory_limited:
            current = sum(
                _dataframe_bytes(item)
                for item in bucket.values()
                if isinstance(item, pd.DataFrame)
            )
            previous = _dataframe_bytes(bucket[key]) if key in bucket else 0
            maximum = int(settings.max_dataset_memory_mb_per_tenant) * 1024 * 1024
            if current - previous + _dataframe_bytes(value) > maximum:
                raise _capacity_error(
                    self.name,
                    f"maximum of {settings.max_dataset_memory_mb_per_tenant} MB per tenant",
                )
        if self.name == "chat sessions" and isinstance(value, list):
            value = _CappedChatHistory(value)
        bucket[key] = value

    def __delitem__(self, key: K) -> None:
        del self._bucket()[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._bucket())

    def __len__(self) -> int:
        return len(self._bucket())

    def clear_all(self) -> None:
        self._store.clear()
        active_tenants = {
            tenant
            for store in _TENANT_STORES
            for tenant, bucket in store._store.items()
            if bucket
        }
        for tenant in list(_TENANT_LAST_USED):
            if tenant not in active_tenants:
                _TENANT_LAST_USED.pop(tenant, None)


_TENANT_STORES: List[TenantScopedDict[Any, Any]] = []
_TENANT_LAST_USED: OrderedDict[str, float] = OrderedDict()


def _capacity_error(store_name: str, limit: str) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"Tenant {store_name} capacity reached ({limit}). Remove unused data or try again later.",
    )


def _dataframe_bytes(value: Any) -> int:
    if not isinstance(value, pd.DataFrame):
        return 0
    return int(value.memory_usage(deep=True).sum())


def _evict_expired() -> None:
    if settings.tenant_eviction_mode != "ttl":
        return
    cutoff = time.monotonic() - settings.tenant_ttl_seconds
    for tenant, last_used in list(_TENANT_LAST_USED.items()):
        if last_used < cutoff:
            _evict_tenant(tenant)


def _evict_tenant(tenant: str) -> None:
    for store in _TENANT_STORES:
        store._store.pop(tenant, None)
    _TENANT_LAST_USED.pop(tenant, None)


def _ensure_tenant(tenant: str) -> None:
    _evict_expired()
    if tenant in _TENANT_LAST_USED:
        return
    if len(_TENANT_LAST_USED) >= settings.max_tenants:
        if settings.tenant_eviction_mode == "lru":
            _evict_tenant(next(iter(_TENANT_LAST_USED)))
        else:
            raise _capacity_error(
                "tenant", f"maximum of {settings.max_tenants} tenants"
            )
    _TENANT_LAST_USED[tenant] = time.monotonic()


def _touch_tenant(tenant: str) -> None:
    _TENANT_LAST_USED.pop(tenant, None)
    _TENANT_LAST_USED[tenant] = time.monotonic()


# In-memory runtime stores
DATASETS: TenantScopedDict[str, pd.DataFrame] = TenantScopedDict(
    "datasets", "max_datasets_per_tenant", memory_limited=True
)
TRAINED_MODELS: TenantScopedDict[str, Dict[str, Any]] = TenantScopedDict(
    "models", "max_models_per_tenant"
)
PREPROCESSORS: TenantScopedDict[str, DataPreprocessor] = TenantScopedDict(
    "preprocessors", "max_preprocessors_per_tenant"
)
CHAT_HISTORY: TenantScopedDict[str, List[Dict[str, str]]] = TenantScopedDict(
    "chat sessions", "max_chat_sessions_per_tenant"
)

# Engines
ml_engine = MLEngine()
eda_engine = EDAEngine()


def read_uploaded_dataframe(file: UploadFile, content: bytes) -> pd.DataFrame:
    """Read CSV/XLSX or JPG/PNG upload into a dataframe."""
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    if filename.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(content))
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid CSV file") from exc
    if filename.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(content))
        except (ValueError, OSError) as exc:
            raise HTTPException(
                status_code=400, detail="Invalid spreadsheet file"
            ) from exc
    if filename.endswith((".jpg", ".jpeg", ".png")):
        return _image_to_dataframe(file, content)

    # Fallback by MIME type when browser uploads omit filename extensions.
    if "csv" in content_type or content_type == "text/plain":
        try:
            return pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            logger.debug("CSV MIME parser rejected upload: %s", type(exc).__name__)
    if "spreadsheet" in content_type or "excel" in content_type:
        try:
            return pd.read_excel(io.BytesIO(content))
        except Exception as exc:
            logger.debug(
                "Spreadsheet MIME parser rejected upload: %s", type(exc).__name__
            )
    if content_type.startswith("image/"):
        return _image_to_dataframe(file, content)

    # Fallback by content sniffing.
    signature = content[:8]
    if signature.startswith(b"\x89PNG") or signature.startswith(b"\xff\xd8"):
        return _image_to_dataframe(file, content)

    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        logger.debug("CSV content parser rejected upload: %s", type(exc).__name__)

    try:
        return pd.read_excel(io.BytesIO(content))
    except Exception as exc:
        logger.debug(
            "Spreadsheet content parser rejected upload: %s", type(exc).__name__
        )

    logger.info(
        "Rejected upload with unsupported format: filename=%r content_type=%r",
        file.filename,
        content_type,
    )
    raise HTTPException(status_code=400, detail="Unsupported or invalid file format")


def _image_to_dataframe(file: UploadFile, content: bytes) -> pd.DataFrame:
    """Convert a single image file into one row of structured numeric features."""
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except Exception as exc:
        logger.error("Image upload parsing failed: error_type=%s", type(exc).__name__)
        raise HTTPException(status_code=400, detail="Invalid image file.") from exc

    rgb_img = image.convert("RGB")
    if rgb_img.width * rgb_img.height > settings.max_image_pixels:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {settings.max_image_pixels} pixel limit.",
        )
    arr = np.array(rgb_img, dtype=np.float32)

    height, width = arr.shape[0], arr.shape[1]
    channels = arr.shape[2] if arr.ndim == 3 else 1

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    gray = np.dot(arr[..., :3], [0.299, 0.587, 0.114])

    hist, _ = np.histogram(gray, bins=256, range=(0, 255), density=True)
    hist = hist + 1e-12
    entropy = float(-(hist * np.log2(hist)).sum())

    row = {
        "source_type": "image",
        "image_name": file.filename or "image",
        "image_mode": image.mode,
        "width": int(width),
        "height": int(height),
        "channels": int(channels),
        "aspect_ratio": float(width / max(height, 1)),
        "pixel_count": int(width * height),
        "mean_r": float(r.mean()),
        "mean_g": float(g.mean()),
        "mean_b": float(b.mean()),
        "std_r": float(r.std()),
        "std_g": float(g.std()),
        "std_b": float(b.std()),
        "brightness_mean": float(gray.mean()),
        "brightness_std": float(gray.std()),
        "min_pixel": float(arr.min()),
        "max_pixel": float(arr.max()),
        "contrast": float(gray.std()),
        "entropy": entropy,
    }

    return pd.DataFrame([row])
