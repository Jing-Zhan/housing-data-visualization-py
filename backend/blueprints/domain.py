"""领域配置接口：前端可读取字段标签与图表标题。"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify

from backend.runtime import get_profile

bp = Blueprint("domain", __name__, url_prefix="/api/domain")


@bp.get("/profile")
def profile():
    """返回当前领域的字段语义与图表标题。"""
    data = get_profile(current_app).to_dict()
    return jsonify({"code": 200, "message": "success", "data": data})


@bp.get("/list")
def list_profiles():
    """列出可切换的领域配置文件。"""
    directory = Path(current_app.config["DOMAIN_DIR"])
    names = sorted(path.stem for path in directory.glob("*.yaml"))
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {"current": current_app.config["DOMAIN"], "available": names},
        }
    )
