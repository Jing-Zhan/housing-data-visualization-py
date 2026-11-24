"""数据管理接口：明细、统计、数据源、导入导出。"""

from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.adapters.csv_adapter import CsvAdapter
from backend.adapters.registry import ADAPTERS
from backend.repo.case_repo import CaseRepository
from backend.repo.source_repo import SourceRepository
from backend.runtime import get_adapter, get_profile, get_rows, refresh_rows

bp = Blueprint("data", __name__, url_prefix="/api/data")


@bp.get("/cases")
def list_cases():
    app = current_app
    profile = get_profile(app)
    limit = min(int(request.args.get("limit", 50)), 500)
    offset = max(int(request.args.get("offset", 0)), 0)
    rows = get_rows(app)

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(rows),
                "offset": offset,
                "limit": limit,
                "slots": profile.slots,
                "labels": [profile.label(slot) for slot in profile.slots],
                "items": rows[offset : offset + limit],
            },
        }
    )


@bp.get("/summary")
def summary():
    app = current_app
    adapter = get_adapter(app)
    rows = get_rows(app)
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(rows),
                "source": adapter.describe(),
                "domain": get_profile(app).name,
            },
        }
    )


@bp.get("/sources")
def sources():
    """列出当前数据源与可切换的适配器类型。"""
    app = current_app
    adapter = get_adapter(app)
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "current": adapter.describe(),
                "available": [
                    {"key": key, "label": cls.label} for key, cls in ADAPTERS.items()
                ],
            },
        }
    )


@bp.post("/refresh")
def refresh():
    """重新采集并落库：采集 → 入库（去重+版本快照）→ 更新数据源状态 → 刷新大屏缓存。"""
    app = current_app
    adapter = get_adapter(app)
    db_config = app.config["DB_CONFIG"]
    case_repo = CaseRepository(db_config)
    source_repo = SourceRepository(db_config)
    code = adapter.key

    if not case_repo.ping():
        return jsonify({"code": 503, "message": "数据库不可用，无法入库", "data": None}), 503

    source_repo.upsert_source(
        code,
        adapter.label,
        source_type=adapter.kind,
        description=f"由 /api/data/refresh 触发（DATA_SOURCE={code}）",
    )
    source_repo.record_run(code, "开始采集")

    try:
        rows = adapter.fetch()
    except Exception as exc:
        source_repo.record_failure(code, f"采集失败：{exc}")
        return jsonify({"code": 500, "message": f"采集失败：{exc}", "data": None}), 500

    try:
        result = case_repo.insert_with_version(
            rows, action="refresh", description=f"{code} 采集入库"
        )
    except Exception as exc:
        source_repo.record_failure(code, f"入库失败：{exc}")
        return jsonify({"code": 500, "message": f"入库失败：{exc}", "data": None}), 500

    message = f"采集 {len(rows)} 条，新增 {result.inserted}，跳过 {result.skipped}"
    if result.completeness is not None and result.completeness < 0.9:
        message += f"；字段完整率 {result.completeness:.0%} 低于 90%，请检查数据"
    source_repo.record_success(code, delta=result.inserted, message=message)

    cached_rows = refresh_rows(app)

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(cached_rows),
                "inserted": result.inserted,
                "skipped": result.skipped,
                "source": code,
            },
        }
    )


@bp.get("/export")
def export():
    """按当前领域把数据导出为 CSV。"""
    profile = get_profile(current_app)
    rows = get_rows(current_app)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=profile.slots)
    writer.writeheader()
    writer.writerows(rows)
    payload = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{profile.name}_cases.csv",
    )


@bp.post("/import")
def import_file():
    """解析上传的 CSV/Excel 并直接入库：去重 + 版本快照 + 更新数据源状态。"""
    app = current_app
    file = request.files.get("file")
    if file is None:
        return jsonify({"code": 400, "message": "未收到文件", "data": None}), 400

    suffix = Path(file.filename).suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        file.save(temp.name)
        temp_path = temp.name

    try:
        adapter = CsvAdapter(get_profile(app), path=temp_path)
        rows = adapter.fetch()
    except Exception as exc:
        return jsonify({"code": 400, "message": f"文件解析失败：{exc}", "data": None}), 400
    finally:
        Path(temp_path).unlink(missing_ok=True)

    case_repo = CaseRepository(app.config["DB_CONFIG"])
    if not case_repo.ping():
        return jsonify({"code": 503, "message": "数据库不可用，无法入库", "data": None}), 503

    source_repo = SourceRepository(app.config["DB_CONFIG"])
    source_repo.upsert_source(
        "csv", "离线文件", source_type="file", description="CSV/Excel 导入"
    )
    source_repo.record_run("csv", f"导入 {file.filename}")

    try:
        result = case_repo.insert_with_version(
            rows, action="import", description=f"上传文件 {file.filename}"
        )
    except Exception as exc:
        source_repo.record_failure("csv", f"入库失败：{exc}")
        return jsonify({"code": 500, "message": f"入库失败：{exc}", "data": None}), 500

    message = f"导入 {len(rows)} 条，新增 {result.inserted}，跳过 {result.skipped}"
    if result.completeness is not None and result.completeness < 0.9:
        message += f"；字段完整率 {result.completeness:.0%} 低于 90%，请检查数据"
    source_repo.record_success("csv", delta=result.inserted, message=message)

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "filename": file.filename,
                "parsed": len(rows),
                "inserted": result.inserted,
                "skipped": result.skipped,
            },
        }
    )


@bp.get("/sources/status")
def sources_status():
    """数据源运行状态列表（来自 data_sources 表）。"""
    repo = SourceRepository(current_app.config["DB_CONFIG"])
    sources = repo.list_sources()
    for src in sources:
        src["last_run_at"] = str(src["last_run_at"])
        src["last_success_at"] = str(src["last_success_at"])
    return jsonify({"code": 200, "message": "success", "data": {"sources": sources}})


@bp.get("/health")
def data_health():
    """数据库健康检查：连通性、数据规模、最新版本、数据源状态。"""
    db_config = current_app.config["DB_CONFIG"]
    case_repo = CaseRepository(db_config)
    source_repo = SourceRepository(db_config)

    db_ok = case_repo.ping()
    payload = {"db": "ok" if db_ok else "down"}
    if db_ok:
        versions = case_repo.list_versions(50)
        sources = source_repo.list_sources()
        now = datetime.now()
        for src in sources:
            success_at = src["last_success_at"]
            src["last_success_seconds_ago"] = (
                int((now - success_at).total_seconds()) if success_at else None
            )
            src["last_run_at"] = str(src["last_run_at"])
            src["last_success_at"] = str(success_at)
        latest = versions[0] if versions else None
        if latest:
            latest["created_at"] = str(latest["created_at"])
        payload.update(
            {
                "cases_total": case_repo.count(),
                "versions_total": len(versions),
                "latest_version": latest,
                "sources": sources,
            }
        )
    return jsonify({"code": 200, "message": "success", "data": payload})


@bp.post("/sources/<code>/enable")
def enable_source(code):
    """启用数据源。"""
    repo = SourceRepository(current_app.config["DB_CONFIG"])
    src = repo.set_enabled(code, 1)
    if src is None:
        return jsonify({"code": 404, "message": "数据源不存在", "data": None}), 404
    return jsonify({"code": 200, "message": "success", "data": {"code": code, "enabled": True}})


@bp.post("/sources/<code>/disable")
def disable_source(code):
    """停用数据源。"""
    repo = SourceRepository(current_app.config["DB_CONFIG"])
    src = repo.set_enabled(code, 0)
    if src is None:
        return jsonify({"code": 404, "message": "数据源不存在", "data": None}), 404
    return jsonify({"code": 200, "message": "success", "data": {"code": code, "enabled": False}})
