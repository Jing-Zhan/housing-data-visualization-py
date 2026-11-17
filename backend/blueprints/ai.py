"""预测与对话接口（骨架）。

对应作业要求 5（大模型对话）与要求 6（神经网络预测），
实现时把推理逻辑放到 ``backend/ml`` 与 ``backend/chat`` 服务中，
本文件只负责协议适配。
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from backend.runtime import get_profile

bp = Blueprint("ai", __name__, url_prefix="/api/ai")

PLANNED = {
    "predict": "文本分类：房源标题与描述 → 户型 / 价格档",
    "similar": "相似样本检索：句向量余弦相似度",
    "chat": "对话：Socket.IO 推送大模型回复，注入当前领域统计",
}


@bp.get("/health")
def health():
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {"status": "planned", "domain": get_profile(current_app).name, "capabilities": PLANNED},
        }
    )


@bp.post("/predict")
def predict():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("content") or "").strip()
    if not text:
        return jsonify({"code": 400, "message": "content 不能为空", "data": None}), 400

    return (
        jsonify(
            {
                "code": 501,
                "message": "模型服务待接入",
                "data": {"input": text, "plan": PLANNED["predict"]},
            }
        ),
        501,
    )


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
                "message": "对话服务待接入，WebSocket 版本见 backend/legacy/websocket_chat.py",
                "data": {"question": question, "plan": PLANNED["chat"]},
            }
        ),
        501,
    )
