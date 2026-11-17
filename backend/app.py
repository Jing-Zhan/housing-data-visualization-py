"""应用入口：创建 Flask 应用并注册蓝图。

本地运行::

    python -m backend.app

默认使用 mock 数据源，无需数据库即可访问 /api/dashboard/overview。
"""

from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS

from backend import __version__
from backend.blueprints.ai import bp as ai_bp
from backend.blueprints.dashboard import bp as dashboard_bp
from backend.blueprints.data import bp as data_bp
from backend.blueprints.domain import bp as domain_bp
from backend.config import Config
from backend.runtime import get_profile, init_runtime

BLUEPRINTS = (dashboard_bp, data_bp, domain_bp, ai_bp)


def create_app(config_object=None) -> Flask:
    """应用工厂，测试时可注入自定义配置。"""
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    app.json.ensure_ascii = False
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    init_runtime(app)

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.get("/api/health")
    def health():
        profile = get_profile(app)
        return jsonify(
            {
                "code": 200,
                "message": "success",
                "data": {
                    "version": __version__,
                    "domain": profile.name,
                    "title": profile.title,
                    "dataSource": app.config.get("DATA_SOURCE"),
                },
            }
        )

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"code": 404, "message": "接口不存在", "data": None}), 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("服务异常：%s", error)
        return jsonify({"code": 500, "message": "服务内部错误", "data": None}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_RUN_PORT", "5000")),
        debug=True,
    )
