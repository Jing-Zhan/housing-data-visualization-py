"""运行时上下文：领域配置、数据源与演示数据的加载与缓存。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Flask

from backend.adapters.base import DataSourceAdapter
from backend.adapters.registry import create_adapter
from backend.domain.profile import DomainProfile

PROFILE_KEY = "domain_profile"
ADAPTER_KEY = "data_adapter"
ROWS_KEY = "data_rows"


def init_runtime(app: Flask) -> DomainProfile:
    """应用启动时加载领域配置与数据源适配器。"""
    profile = DomainProfile.load(app.config["DOMAIN"], app.config["DOMAIN_DIR"])
    adapter = create_adapter(
        profile,
        app.config.get("DATA_SOURCE", "mock"),
        rows=app.config.get("MOCK_ROWS", 300),
    )
    app.extensions[PROFILE_KEY] = profile
    app.extensions[ADAPTER_KEY] = adapter
    app.extensions[ROWS_KEY] = None
    return profile


def get_profile(app: Flask) -> DomainProfile:
    profile = app.extensions.get(PROFILE_KEY)
    if profile is None:
        profile = init_runtime(app)
    return profile


def get_adapter(app: Flask) -> DataSourceAdapter:
    adapter = app.extensions.get(ADAPTER_KEY)
    if adapter is None:
        init_runtime(app)
        adapter = app.extensions[ADAPTER_KEY]
    return adapter


def get_rows(app: Flask, limit: Optional[int] = None, refresh: bool = False) -> List[Dict[str, Any]]:
    """读取数据行，默认缓存一次，避免每次请求都重新生成。"""
    cached = app.extensions.get(ROWS_KEY)
    if cached is None or refresh:
        cached = get_adapter(app).fetch(limit=limit)
        app.extensions[ROWS_KEY] = cached
    return cached if limit is None else cached[:limit]


def refresh_rows(app: Flask, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    return get_rows(app, limit=limit, refresh=True)
