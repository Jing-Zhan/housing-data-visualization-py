"""大屏聚合接口。"""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from backend.runtime import get_profile, get_rows
from backend.services import chart_service, kpi_service

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/overview")
def overview():
    """一次返回大屏所需全部数据，前端只渲染不计算。"""
    app = current_app
    profile = get_profile(app)
    rows = get_rows(app)

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "domain": profile.name,
                "title": profile.title,
                "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "kpi": kpi_service.summarize(rows, profile),
                "charts": chart_service.build_all(rows, profile),
            },
        }
    )


@bp.get("/cases")
def cases():
    """分页返回明细，供大屏列表使用。"""
    app = current_app
    profile = get_profile(app)
    limit = min(int(request.args.get("limit", 50)), 500)
    rows = get_rows(app)
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(rows),
                "slots": profile.slots,
                "labels": [profile.label(slot) for slot in profile.slots],
                "items": rows[:limit],
            },
        }
    )
