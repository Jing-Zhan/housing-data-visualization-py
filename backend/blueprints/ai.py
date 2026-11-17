"""AI 对话与 Agent 接口（模块负责人：占竞）。

对应需求第 6 章：会话、工具编排、结果组织。
具体实现放在 ``backend/agent/``，本文件只负责协议适配。
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.runtime import get_profile

bp = Blueprint("ai", __name__, url_prefix="/api/ai")

PLANNED_TOOLS = [
    {"name": "query_cases", "desc": "按区域、户型、价格区间查询房源"},
    {"name": "aggregate_stats", "desc": "按区域、户型、月份分组统计数量与均价"},
    {"name": "price_distribution", "desc": "按价格区间统计房源数量"},
    {"name": "find_similar", "desc": "按描述查找相似房源"},
    {"name": "predict_category", "desc": "预测户型或价格档位"},
    {"name": "render_chart", "desc": "把统计结果转成图表配置"},
    {"name": "draft_report", "desc": "生成报告草稿"},
    {"name": "export_report", "desc": "导出报告文件"},
]


@bp.get("/health")
def health():
    profile = get_profile(current_app)
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {"status": "planned", "domain": profile.name, "module": "ai-agent"},
        }
    )


@bp.get("/tools")
def tools():
    """返回 Agent 可调用的工具清单，前端可用于展示能力说明。"""
    return jsonify({"code": 200, "message": "success", "data": PLANNED_TOOLS})


@bp.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"code": 400, "message": "question 不能为空", "data": None}), 400

    return (
        jsonify(
            {
                "code": 501,
                "message": "对话服务待接入，WebSocket 版参考 backend/legacy/websocket_chat.py",
                "data": {"question": question, "session": payload.get("session")},
            }
        ),
        501,
    )
