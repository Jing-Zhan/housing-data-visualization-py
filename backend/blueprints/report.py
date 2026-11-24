"""报告生成接口（模块负责人：付悰安）。

对应需求 FR-22、FR-23，模板与导出逻辑放在 ``backend/report/``。
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

bp = Blueprint("report", __name__, url_prefix="/api/reports")


@bp.get("/health")
def health():
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {"status": "planned", "formats": ["pdf"], "optional": ["word"]},
        }
    )


@bp.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    template_id = payload.get("templateId") or "tpl-month"
    return (
        jsonify(
            {
                "code": 501,
                "message": "报告生成待接入",
                "data": {
                    "templateId": template_id,
                    "filters": payload.get("filters") or {},
                    "plan": "模板渲染 → 数据块填充 → 导出 PDF",
                },
            }
        ),
        501,
    )
