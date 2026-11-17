"""数据源适配层：把不同来源的数据统一成 13 个槽位的行。"""

from backend.adapters.base import DataSourceAdapter
from backend.adapters.csv_adapter import CsvAdapter
from backend.adapters.crawler_adapter import LianjiaCrawlerAdapter
from backend.adapters.mock_adapter import MockAdapter
from backend.adapters.openapi_adapter import OpenDataApiAdapter
from backend.adapters.registry import ADAPTERS, create_adapter

__all__ = [
    "DataSourceAdapter",
    "CsvAdapter",
    "LianjiaCrawlerAdapter",
    "MockAdapter",
    "OpenDataApiAdapter",
    "ADAPTERS",
    "create_adapter",
]
