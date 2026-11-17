"""适配器工厂：按配置创建具体数据源，调用方只依赖抽象接口。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from backend.adapters.base import DataSourceAdapter
from backend.adapters.csv_adapter import CsvAdapter
from backend.adapters.crawler_adapter import LianjiaCrawlerAdapter
from backend.adapters.mock_adapter import MockAdapter
from backend.adapters.openapi_adapter import OpenDataApiAdapter
from backend.domain.profile import DomainProfile

ADAPTERS: Dict[str, Type[DataSourceAdapter]] = {
    MockAdapter.key: MockAdapter,
    CsvAdapter.key: CsvAdapter,
    LianjiaCrawlerAdapter.key: LianjiaCrawlerAdapter,
    OpenDataApiAdapter.key: OpenDataApiAdapter,
}


def create_adapter(
    profile: DomainProfile,
    kind: Optional[str] = None,
    **options: Any,
) -> DataSourceAdapter:
    """按类型名创建适配器，未指定时回退到 mock。"""
    key = (kind or "mock").lower()
    adapter_cls = ADAPTERS.get(key)
    if adapter_cls is None:
        raise ValueError(f"未知数据源类型：{key}，可选值为 {', '.join(ADAPTERS)}")
    return adapter_cls(profile, **options)
