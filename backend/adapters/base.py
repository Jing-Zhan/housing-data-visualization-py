"""适配器抽象接口。

约定：适配器只负责"取数 + 对齐槽位"，不做统计与展示。
新增数据源时继承 :class:`DataSourceAdapter` 并实现 ``fetch``，
业务层无需修改，满足开闭原则。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.domain.profile import DomainProfile

Row = Dict[str, Any]


class DataSourceAdapter(ABC):
    """数据源适配器基类。"""

    key: str = "base"
    label: str = "基础适配器"
    kind: str = "base"

    def __init__(self, profile: DomainProfile, **options: Any) -> None:
        self.profile = profile
        self.options = options

    # ------------------------------------------------------------------ 取数
    @abstractmethod
    def fetch(self, limit: Optional[int] = None) -> List[Row]:
        """返回若干行，每行包含 13 个槽位键。"""

    # ------------------------------------------------------------------ 工具
    def normalize(self, row: Dict[str, Any]) -> Row:
        """裁剪到 13 个槽位，空字符串统一成 None。"""
        result: Row = {}
        for slot in self.profile.slots:
            value = row.get(slot)
            if isinstance(value, str):
                value = value.strip()
            result[slot] = value if value not in ("", None) else None
        return result

    def describe(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "options": {k: v for k, v in self.options.items() if k != "profile"},
        }
