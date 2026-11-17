"""图表数据组装：输出与前端图表位一一对应的结构。

每个函数返回 ECharts / DataV 可直接消费的数据，标题取自领域配置。
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.domain.profile import DomainProfile
from backend.services.kpi_service import Row, _to_number, count_by


def age_pie(rows: List[Row], profile: DomainProfile) -> List[Dict[str, Any]]:
    """按领域配置的分箱统计数量。"""
    bins = profile.bins or [{"label": "全部", "max": 999}]
    result = [{"name": item["label"], "value": 0} for item in bins]
    for row in rows:
        value = _to_number(row.get("age"))
        if value is None:
            continue
        for index, item in enumerate(bins):
            if value <= float(item.get("max", 999)):
                result[index]["value"] += 1
                break
    return result


def type_capsule(rows: List[Row], top: int = 8) -> List[Dict[str, Any]]:
    return count_by(rows, "type")[:top]


def department_ring(rows: List[Row], top: int = 8) -> List[Dict[str, Any]]:
    return count_by(rows, "department")[:top]


def split_ratio(rows: List[Row], profile: DomainProfile) -> Dict[str, Any]:
    """按配置的二分字段（如装修的 精装 / 简装）统计两组对比。"""
    field = profile.split_field or "gender"
    values = profile.split_values or ["A", "B"]
    left, right = values[0], values[-1]
    left_rows = [row for row in rows if str(row.get(field)) == left]
    right_rows = [row for row in rows if str(row.get(field)) == right]
    total = len(left_rows) + len(right_rows) or 1
    return {
        "left": {"name": left, "count": len(left_rows), "ratio": round(len(left_rows) / total * 100)},
        "right": {"name": right, "count": len(right_rows), "ratio": round(len(right_rows) / total * 100)},
        "series": {
            "left": count_by(left_rows, "type"),
            "right": count_by(right_rows, "type"),
        },
    }


def mean_by_type(rows: List[Row], profile: DomainProfile) -> Dict[str, Any]:
    """按类型统计两个数值字段的均值（前端双轴图）。"""
    buckets: Dict[str, Dict[str, float]] = {}
    for row in rows:
        key = str(row.get("type") or "未填写")
        height = _to_number(row.get("height"))
        weight = _to_number(row.get("weight"))
        item = buckets.setdefault(key, {"height": 0.0, "weight": 0.0, "count": 0})
        if height is not None and weight is not None:
            item["height"] += height
            item["weight"] += weight
            item["count"] += 1

    ordered = sorted(buckets.items(), key=lambda kv: kv[1]["count"], reverse=True)[:8]
    return {
        "xData": [name for name, _ in ordered],
        "y1Data": [round(v["height"] / v["count"]) if v["count"] else 0 for _, v in ordered],
        "y2Data": [round(v["weight"] / v["count"]) if v["count"] else 0 for _, v in ordered],
        "units": [profile.meta("height").unit, profile.meta("weight").unit],
    }


def word_cloud(rows: List[Row], profile: DomainProfile) -> List[Dict[str, Any]]:
    """关键词词云：优先统计描述文本命中的领域关键词，缺失时回退到类型分布。"""
    keywords = profile.keywords or []
    counter: Dict[str, int] = {word: 0 for word in keywords}
    for row in rows:
        text = str(row.get("content") or "")
        for word in keywords:
            if word and word in text:
                counter[word] += 1
    hits = [{"name": k, "value": v} for k, v in counter.items() if v > 0]
    if hits:
        return sorted(hits, key=lambda item: item["value"], reverse=True)
    return count_by(rows, "type")[:10]


def build_all(rows: List[Row], profile: DomainProfile) -> Dict[str, Any]:
    """大屏所需的全部图表数据。"""
    return {
        "age": {"title": profile.chart_title("age"), "data": age_pie(rows, profile)},
        "type": {"title": profile.chart_title("type"), "data": type_capsule(rows)},
        "ring": {"title": profile.chart_title("ring"), "data": department_ring(rows)},
        "split": {"title": profile.chart_title("split"), "data": split_ratio(rows, profile)},
        "mean": {"title": profile.chart_title("mean"), "data": mean_by_type(rows, profile)},
        "word": {"title": profile.chart_title("word"), "data": word_cloud(rows, profile)},
    }
