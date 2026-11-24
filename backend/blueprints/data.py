"""数据管理接口：明细、统计、数据源、导入导出。"""

from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

import os
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
    """触发一次采集并落库：采集 → 入库（去重+版本快照）→ 更新数据源状态 → 刷新大屏缓存。"""
    from backend.services.data_service import DataCollectionError, DatabaseUnavailable, collect_once

    app = current_app
    try:
        info = collect_once(app)
    except DatabaseUnavailable as exc:
        return jsonify({"code": 503, "message": str(exc), "data": None}), 503
    except DataCollectionError as exc:
        return jsonify({"code": 500, "message": str(exc), "data": None}), 500

    cached_rows = refresh_rows(app)
    info["total"] = len(cached_rows)
    return jsonify({"code": 200, "message": "success", "data": info})


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

    message = f"导入 {len(rows)} 条，新增 {result.inserted}，重复跳过 {result.skipped}"
    if result.invalid:
        message += f"，数据异常跳过 {result.invalid}"
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
                "invalid": result.invalid,
            },
        }
    )


@bp.get("/sources/status")
def sources_status():
    """数据源运行状态列表（来自 data_sources 表）。"""
    repo = SourceRepository(current_app.config["DB_CONFIG"])
    try:
        sources = repo.list_sources()
    except Exception:
        return jsonify({"code": 503, "message": "数据库不可用", "data": None}), 503
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

    try:
        if not case_repo.ping():
            return jsonify({"code": 503, "message": "数据库不可用", "data": None}), 503
        versions = case_repo.list_versions(50)
        sources = source_repo.list_sources()
        cases_total = case_repo.count()
    except Exception:
        return jsonify({"code": 503, "message": "数据库不可用", "data": None}), 503

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
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "db": "ok",
                "cases_total": cases_total,
                "versions_total": len(versions),
                "latest_version": latest,
                "sources": sources,
            },
        }
    )


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


@bp.record
def _setup_scheduler(state):
    """注册蓝图时按配置启动定时采集（默认关闭，演示时在 .env 打开）。"""
    app = state.app
    if not app.config.get("SCHEDULER_ENABLED"):
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return  # debug 热重载的主进程，等子进程再启动，避免双重调度
    from backend.services.scheduler_service import start_scheduler

    start_scheduler(app, interval_seconds=app.config.get("SCHEDULER_INTERVAL", 30))


@bp.get("/versions")
def list_versions():
    """版本列表，按时间倒序（FR-07：版本列表可查到对应记录）。"""
    repo = CaseRepository(current_app.config["DB_CONFIG"])
    if not repo.ping():
        return jsonify({"code": 503, "message": "数据库不可用", "data": None}), 503
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        items = repo.list_versions(limit=limit)
    except Exception:
        return jsonify({"code": 503, "message": "数据库不可用", "data": None}), 503
    for item in items:
        item["created_at"] = str(item["created_at"])
    return jsonify(
        {"code": 200, "message": "success", "data": {"total": len(items), "items": items}}
    )


@bp.post("/versions/<int:version_id>/restore")
def restore_version(version_id):
    """按版本回滚数据（FR-08）。"""
    repo = CaseRepository(current_app.config["DB_CONFIG"])
    try:
        restored = repo.restore_version(version_id)
    except ValueError as exc:
        return jsonify({"code": 404, "message": str(exc), "data": None}), 404
    except Exception as exc:  # noqa: BLE001
        return jsonify({"code": 500, "message": f"回滚失败：{exc}", "data": None}), 500
    return jsonify(
        {"code": 200, "message": "success", "data": {"versionId": version_id, "restored": restored}}
    )
