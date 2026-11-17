"""数据管理接口：明细、统计、数据源、导入导出。"""

from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.adapters.csv_adapter import CsvAdapter
from backend.adapters.registry import ADAPTERS
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
    """重新拉取一次数据，用于演示"实时更新"。"""
    rows = refresh_rows(current_app)
    return jsonify({"code": 200, "message": "success", "data": {"total": len(rows)}})


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
    """解析上传文件并返回预览条数。

    待实现：解析成功后经 ``CaseRepository.insert_many`` 落库，
    并调用 ``save_version`` 记录版本快照。
    """
    file = request.files.get("file")
    if file is None:
        return jsonify({"code": 400, "message": "未收到文件", "data": None}), 400

    suffix = Path(file.filename).suffix or ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        file.save(temp.name)
        temp_path = temp.name

    try:
        adapter = CsvAdapter(get_profile(current_app), path=temp_path)
        rows = adapter.fetch()
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return jsonify(
        {
            "code": 200,
            "message": "已解析，尚未写入数据库",
            "data": {"parsed": len(rows), "preview": rows[:5]},
        }
    )
