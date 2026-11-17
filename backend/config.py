"""应用配置：全部从环境变量读取，默认值只用于本地开发。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")


class Config:
    """Flask 配置对象。"""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-secret")

    # 领域与数据源
    DOMAIN = os.getenv("DOMAIN", "house")
    DATA_SOURCE = os.getenv("DATA_SOURCE", "mock")
    MOCK_ROWS = int(os.getenv("MOCK_ROWS", "300"))

    # 目录
    DOMAIN_DIR = BASE_DIR / "domain" / "profiles"
    LEGACY_DIR = BASE_DIR / "legacy"

    # 数据库
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "housinginfo"),
        "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    }

    JSON_AS_ASCII = False


class TestConfig(Config):
    """单元测试配置：不连数据库，固定使用 mock 数据。"""

    TESTING = True
    DATA_SOURCE = "mock"
    MOCK_ROWS = 50
