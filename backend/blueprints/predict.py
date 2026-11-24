"""文本分类与相似检索接口（模块负责人：李艺淼）。

对应需求 FR-14 至 FR-16，模型与训练逻辑放在 ``backend/ml/``。
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

bp = Blueprint("predict", __name__, url_prefix="/api/ai")


@bp.get("/model")
def model_info():
    """返回模型状态，接入训练结果后补充版本与指标。"""
    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {"status": "not_trained", "labels": [], "metrics": {}},
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
                "data": {"input": text, "plan": "BERT 文本分类：房源描述 → 户型或价格档"},
            }
        ),
        501,
    )


@bp.post("/similar")
def similar():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("content") or "").strip()
    if not text:
        return jsonify({"code": 400, "message": "content 不能为空", "data": None}), 400

    top_k = min(int(payload.get("topK") or 5), 10)
    return (
        jsonify(
            {
                "code": 501,
                "message": "相似检索待接入",
                "data": {"input": text, "topK": top_k, "plan": "句向量余弦相似度"},
            }
        ),
        501,
    )
