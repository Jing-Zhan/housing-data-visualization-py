"""领域配置：把 13 个通用字段槽位解释为具体业务的语义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - 依赖缺失时给出明确提示
    yaml = None


DEFAULT_PROFILE_DIR = Path(__file__).resolve().parent / "profiles"


@dataclass(frozen=True)
class FieldMeta:
    """单个字段槽位的语义。"""

    key: str
    label: str
    example: str = ""
    numeric: bool = False
    unit: str = ""


@dataclass
class DomainProfile:
    """一个领域的完整配置。"""

    name: str
    title: str
    description: str = ""
    fields: Dict[str, FieldMeta] = field(default_factory=dict)
    charts: Dict[str, str] = field(default_factory=dict)
    split_field: str = ""
    split_values: List[str] = field(default_factory=list)
    bins: List[Dict[str, Any]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ 读取
    @classmethod
    def load(cls, name: str, directory: Optional[Path] = None) -> "DomainProfile":
        """按名称加载 ``profiles/<name>.yaml``。"""
        if yaml is None:
            raise RuntimeError("缺少 PyYAML，请执行 pip install -r requirements.txt")

        base = Path(directory) if directory else DEFAULT_PROFILE_DIR
        path = base / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"领域配置不存在：{path}")

        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

        fields: Dict[str, FieldMeta] = {}
        for key, value in (raw.get("fields") or {}).items():
            value = value or {}
            fields[key] = FieldMeta(
                key=key,
                label=str(value.get("label", key)),
                example=str(value.get("example", "")),
                numeric=bool(value.get("numeric", False)),
                unit=str(value.get("unit", "")),
            )

        split = raw.get("split") or {}
        return cls(
            name=str(raw.get("name", name)),
            title=str(raw.get("title", name)),
            description=str(raw.get("description", "")),
            fields=fields,
            charts={str(k): str(v) for k, v in (raw.get("charts") or {}).items()},
            split_field=str(split.get("field", "")),
            split_values=[str(v) for v in (split.get("values") or [])],
            bins=list(raw.get("bins") or []),
            keywords=[str(v) for v in (raw.get("keywords") or [])],
        )

    # ------------------------------------------------------------------ 查询
    @property
    def slots(self) -> List[str]:
        """13 个槽位的键，顺序与建表语句一致。"""
        return list(self.fields)

    def meta(self, key: str) -> FieldMeta:
        return self.fields.get(key, FieldMeta(key=key, label=key))

    def label(self, key: str) -> str:
        return self.meta(key).label

    def numeric_keys(self) -> List[str]:
        return [k for k, v in self.fields.items() if v.numeric]

    def chart_title(self, key: str, default: str = "") -> str:
        return self.charts.get(key, default or key)

    def example_row(self) -> Dict[str, Any]:
        """给前端联调用的示例行。"""
        return {k: v.example for k, v in self.fields.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "charts": self.charts,
            "split": {"field": self.split_field, "values": self.split_values},
            "bins": self.bins,
            "fields": [
                {
                    "key": m.key,
                    "label": m.label,
                    "example": m.example,
                    "numeric": m.numeric,
                    "unit": m.unit,
                }
                for m in self.fields.values()
            ],
        }
