"""数据源状态仓储：读写 ``data_sources`` 表。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.cursors import DictCursor


class SourceRepository:
    """数据源注册、运行状态与健康指标的读写。"""

    def __init__(self, db_config: Dict[str, Any]) -> None:
        self.db_config = db_config

    def _connect(self) -> pymysql.connections.Connection:
        return pymysql.connect(cursorclass=DictCursor, **self.db_config)

    # ------------------------------------------------------------------ 查询
    def list_sources(self) -> List[Dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, code, name, type, description, enabled, status, "
                "last_run_at, last_success_at, last_delta, total_records, last_message "
                "FROM data_sources ORDER BY id"
            )
            return list(cursor.fetchall())

    def get_source(self, code: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, code, name, type, description, enabled, status, "
                "last_run_at, last_success_at, last_delta, total_records, last_message "
                "FROM data_sources WHERE code = %s",
                (code,),
            )
            return cursor.fetchone()

    # ------------------------------------------------------------------ 写入
    def upsert_source(
        self,
        code: str,
        name: str,
        source_type: str = "crawler",
        description: Optional[str] = None,
        enabled: int = 1,
        disease: str = "",
    ) -> None:
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO data_sources (code, name, disease, type, description, enabled) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE name=VALUES(name), type=VALUES(type), "
                "description=VALUES(description), enabled=VALUES(enabled)",
                (code, name, disease, source_type, description, enabled),
            )
            conn.commit()

    def record_run(self, code: str, message: Optional[str] = None) -> None:
        """标记一次采集开始运行。"""
        now = datetime.now()
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE data_sources SET status='running', last_run_at=%s, last_message=%s "
                "WHERE code=%s",
                (now, message, code),
            )
            conn.commit()

    def record_success(self, code: str, delta: int = 0, message: Optional[str] = None) -> None:
        """记录一次采集成功，累加采集条数。"""
        now = datetime.now()
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE data_sources SET status='idle', last_success_at=%s, last_delta=%s, "
                "total_records=total_records+%s, last_message=%s WHERE code=%s",
                (now, delta, delta, message, code),
            )
            conn.commit()

    def record_failure(self, code: str, message: str) -> None:
        """记录一次采集失败。"""
        now = datetime.now()
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE data_sources SET status='error', last_run_at=%s, last_message=%s "
                "WHERE code=%s",
                (now, message, code),
            )
            conn.commit()

    def set_enabled(self, code: str, enabled: int) -> Optional[Dict[str, Any]]:
        """启用（1）或停用（0）数据源，返回更新后的记录；不存在时返回 None。"""
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE data_sources SET enabled=%s WHERE code=%s", (enabled, code)
            )
            conn.commit()
        return self.get_source(code)
