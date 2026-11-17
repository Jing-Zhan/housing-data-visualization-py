"""指标计算：只做纯函数计算，不依赖 Flask 与数据库。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from backend.domain.profile import DomainProfile

Row = Dict[str, Any]


def _to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("㎡", "").replace("万", ""))
    except (TypeError, ValueError):
        return None


def count_by(rows: List[Row], key: str) -> List[Dict[str, Any]]:
    counter = Counter(str(row.get(key) or "未填写") for row in rows)
    return [{"name": name, "value": value} for name, value in counter.most_common()]


def average(rows: List[Row], key: str) -> Optional[float]:
    values = [v for v in (_to_number(row.get(key)) for row in rows) if v is not None]
    return round(sum(values) / len(values), 1) if values else None


def summarize(rows: List[Row], profile: DomainProfile) -> Dict[str, Any]:
    """大屏顶部的关键指标。"""
    total = len(rows)
    type_counter = Counter(str(row.get("type") or "未填写") for row in rows)
    dept_counter = Counter(str(row.get("department") or "未填写") for row in rows)
    ages = [v for v in (_to_number(row.get("age")) for row in rows) if v is not None]

    return {
        "total": total,
        "topType": type_counter.most_common(1)[0][0] if type_counter else None,
        "topTypeCount": type_counter.most_common(1)[0][1] if type_counter else 0,
        "topDepartment": dept_counter.most_common(1)[0][0] if dept_counter else None,
        "avgAge": average(rows, "age"),
        "avgHeight": average(rows, "height"),
        "avgWeight": average(rows, "weight"),
        "minAge": min(ages) if ages else None,
        "maxAge": max(ages) if ages else None,
        "labels": {
            "total": "总量",
            "age": profile.label("age"),
            "height": profile.label("height"),
            "weight": profile.label("weight"),
        },
    }
