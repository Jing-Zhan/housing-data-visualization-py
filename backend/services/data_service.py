"""数据采集落库服务：采集 → 入库（去重+版本快照）→ 更新数据源状态。

供 ``/api/data/refresh`` 接口与定时调度器共用。
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Flask

from backend.repo.case_repo import CaseRepository
from backend.repo.source_repo import SourceRepository
from backend.runtime import get_adapter


class DataCollectionError(RuntimeError):
    """采集或入库失败。"""


class DatabaseUnavailable(DataCollectionError):
    """数据库不可用。"""


def collect_once(app: Flask) -> Dict[str, Any]:
    """执行一次采集并落库，返回 ``{total, inserted, skipped, source}``。

    数据源运行状态（开始/成功/失败）在内部记录；数据库不可用时抛
    :class:`DatabaseUnavailable`，采集/入库失败抛 :class:`DataCollectionError`。
    """
    adapter = get_adapter(app)
    db_config = app.config["DB_CONFIG"]
    case_repo = CaseRepository(db_config)
    source_repo = SourceRepository(db_config)
    code = adapter.key

    if not case_repo.ping():
        raise DatabaseUnavailable("数据库不可用，无法入库")

    source_repo.upsert_source(
        code,
        adapter.label,
        source_type=adapter.kind,
        description=f"定时/手动采集（DATA_SOURCE={code}）",
    )
    source_repo.record_run(code, "开始采集")

    try:
        rows = adapter.fetch()
    except Exception as exc:
        source_repo.record_failure(code, f"采集失败：{exc}")
        raise DataCollectionError(f"采集失败：{exc}") from exc

    try:
        result = case_repo.insert_with_version(
            rows, action="refresh", description=f"{code} 采集入库"
        )
    except Exception as exc:
        source_repo.record_failure(code, f"入库失败：{exc}")
        raise DataCollectionError(f"入库失败：{exc}") from exc

    message = f"采集 {len(rows)} 条，新增 {result.inserted}，重复跳过 {result.skipped}"
    if result.invalid:
        message += f"，数据异常跳过 {result.invalid}"
    if result.completeness is not None and result.completeness < 0.9:
        message += f"；字段完整率 {result.completeness:.0%} 低于 90%，请检查数据"
    source_repo.record_success(code, delta=result.inserted, message=message)

    return {
        "total": len(rows),
        "inserted": result.inserted,
        "skipped": result.skipped,
        "invalid": result.invalid,
        "source": code,
    }
