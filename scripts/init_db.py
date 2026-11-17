"""初始化数据库：创建库表结构。"""

from __future__ import annotations

import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import BASE_DIR, Config  # noqa: E402

load_dotenv(BASE_DIR.parent / ".env")
SCHEMA = BASE_DIR / "models" / "schema.sql"


def main() -> int:
    sql_text = SCHEMA.read_text(encoding="utf-8")
    statements = [item.strip() for item in sql_text.split(";") if item.strip()]
    config = dict(Config.DB_CONFIG)
    config.pop("database", None)

    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()

    print(f"已执行 {len(statements)} 条语句，库表初始化完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
