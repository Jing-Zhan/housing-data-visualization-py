"""仓储层：所有 SQL 集中在此，业务层不直接拼 SQL。"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pymysql
from pymysql.cursors import DictCursor

SLOTS = (
    "type",
    "gender",
    "age",
    "time",
    "content",
    "docName",
    "docHospital",
    "department",
    "detailUrl",
    "height",
    "weight",
    "illDuration",
    "allergy",
)


class CaseRepository:
    """``cases`` 事实表的读写。"""

    def __init__(self, db_config: Dict[str, Any]) -> None:
        self.db_config = db_config

    # ------------------------------------------------------------------ 连接
    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(cursorclass=DictCursor, **self.db_config)

    def ping(self) -> bool:
        try:
            with self._connect() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ 查询
    def count(self) -> int:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM cases")
            return int(cursor.fetchone()["total"])

    def list_cases(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        sql = f"SELECT id, {', '.join(SLOTS)} FROM cases ORDER BY id DESC LIMIT %s OFFSET %s"
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(sql, (limit, offset))
            return list(cursor.fetchall())

    def existing_urls(self, urls: Iterable[str]) -> set:
        urls = [u for u in urls if u]
        if not urls:
            return set()
        placeholders = ",".join(["%s"] * len(urls))
        sql = f"SELECT detailUrl FROM cases WHERE detailUrl IN ({placeholders})"
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(sql, urls)
            return {row["detailUrl"] for row in cursor.fetchall()}

    # ------------------------------------------------------------------ 写入
    def insert_many(self, rows: Iterable[Dict[str, Any]]) -> int:
        """按 detailUrl 去重后批量插入，返回新增条数。"""
        rows = list(rows)
        if not rows:
            return 0
        skip = self.existing_urls(row.get("detailUrl") for row in rows)
        payload = [
            tuple(row.get(slot) for slot in SLOTS)
            for row in rows
            if not (row.get("detailUrl") and row.get("detailUrl") in skip)
        ]
        if not payload:
            return 0
        sql = f"INSERT INTO cases ({', '.join(SLOTS)}) VALUES ({', '.join(['%s'] * len(SLOTS))})"
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.executemany(sql, payload)
            conn.commit()
        return len(payload)

    # ------------------------------------------------------------------ 版本
    def save_version(self, action: str, description: str, operator: str = "system", delta: int = 0) -> int:
        """写入版本记录并生成整表快照（对应"实时更新"任务的审计需求）。

        待实现：与 ``insert_many`` 放在同一事务中，避免快照与数据不一致。
        """
        raise NotImplementedError("版本快照待实现，见 docs/01-需求规格说明书.md")
