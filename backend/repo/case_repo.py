"""仓储层：所有 SQL 集中在此，业务层不直接拼 SQL。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, NamedTuple, Optional

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


class InsertResult(NamedTuple):
    """批量写入结果：inserted 新增条数，skipped 重复跳过条数，
    invalid 数据质量不合格跳过条数，completeness 字段完整率（0~1）。"""

    inserted: int
    skipped: int
    invalid: int = 0
    completeness: Optional[float] = None


class CaseRepository:
    """``cases`` 事实表的读写。"""

    def __init__(self, db_config: Dict[str, Any]) -> None:
        self.db_config = db_config

    @staticmethod
    def _completeness(rows: List[Dict[str, Any]]) -> Optional[float]:
        """字段完整率：非空槽位数 / 总槽位数，返回 0~1。"""
        total = len(rows) * len(SLOTS)
        if not total:
            return None
        filled = sum(
            1 for row in rows for slot in SLOTS if row.get(slot) not in (None, "")
        )
        return round(filled / total, 4)

    # 数据质量规则（需求 7.4）：必填字段与数值范围兜底
    REQUIRED_SLOTS = ("type", "content", "detailUrl")
    RANGE_SLOTS = {
        "height": (1.0, 1000.0),     # 建筑面积（㎡）
        "weight": (1.0, 100000.0),   # 挂牌总价（万）
    }

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "").replace("㎡", "").replace("万", ""))
        except (TypeError, ValueError):
            return None

    def _filter_valid(self, rows: List[Dict[str, Any]]) -> tuple:
        """过滤数据质量不合格的行，返回 (有效行, 无效条数)。"""
        valid: List[Dict[str, Any]] = []
        invalid = 0
        for row in rows:
            missing = [s for s in self.REQUIRED_SLOTS if row.get(s) in (None, "")]
            if missing:
                invalid += 1
                continue
            out_of_range = [
                slot
                for slot, (lo, hi) in self.RANGE_SLOTS.items()
                if (value := self._to_float(row.get(slot))) is not None
                and not (lo <= value <= hi)
            ]
            if out_of_range:
                invalid += 1
                continue
            valid.append(row)
        return valid, invalid

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

    # ------------------------------------------------------------------ 写入
    def insert_many(self, rows: Iterable[Dict[str, Any]]) -> InsertResult:
        """批量插入房源：数据质量校验 → ``detailUrl`` 去重 → 单事务写入，出错整批回滚。

        返回 :class:`InsertResult`：``inserted`` 新增条数，``skipped`` 重复跳过条数，
        ``invalid`` 数据质量不合格跳过条数，``completeness`` 字段完整率。
        """
        all_rows = list(rows)
        if not all_rows:
            return InsertResult(0, 0)
        valid_rows, invalid = self._filter_valid(all_rows)
        if not valid_rows:
            return InsertResult(
                inserted=0,
                skipped=0,
                invalid=invalid,
                completeness=self._completeness(all_rows),
            )
        payload = [tuple(row.get(slot) for slot in SLOTS) for row in valid_rows]
        sql = (
            f"INSERT IGNORE INTO cases ({', '.join(SLOTS)}) "
            f"VALUES ({', '.join(['%s'] * len(SLOTS))})"
        )
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(sql, payload)
                inserted = cursor.rowcount
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return InsertResult(
            inserted=inserted,
            skipped=len(payload) - inserted,
            invalid=invalid,
            completeness=self._completeness(all_rows),
        )

    # ------------------------------------------------------------------ 版本
    def _count_on(self, cursor) -> int:
        cursor.execute("SELECT COUNT(*) AS total FROM cases")
        return int(cursor.fetchone()["total"])

    def _insert_version(
        self,
        cursor,
        action: str,
        description: str,
        operator: str,
        delta: int,
    ) -> int:
        code = datetime.now().strftime("v%Y%m%d%H%M%S%f")
        name = f"{action}-{code}"
        cursor.execute(
            "INSERT INTO data_versions "
            "(name, version_code, operator, action, description, total_records, delta_records) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (name, code, operator, action, description, self._count_on(cursor), delta),
        )
        return cursor.lastrowid

    def _snapshot(self, cursor, version_id: int) -> None:
        cols = ", ".join(SLOTS)
        cursor.execute(
            f"INSERT INTO cases_snapshot (version_id, case_id, {cols}) "
            f"SELECT %s, id, {cols} FROM cases",
            (version_id,),
        )

    def save_version(self, action: str, description: str, operator: str = "system", delta: int = 0) -> int:
        """写入版本记录并生成整表快照（独立事务），返回 version_id。"""
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                version_id = self._insert_version(cursor, action, description, operator, delta)
                self._snapshot(cursor, version_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return version_id

    def insert_with_version(
        self,
        rows: Iterable[Dict[str, Any]],
        action: str = "import",
        description: str = "",
        operator: str = "system",
    ) -> InsertResult:
        """一个事务内完成：数据质量校验 → 批量插入 + 写版本记录 + 整表快照。

        数据写入与版本快照要么一起成功、要么一起回滚。全部重复（无新增）时不生成版本。
        """
        all_rows = list(rows)
        if not all_rows:
            return InsertResult(0, 0)
        valid_rows, invalid = self._filter_valid(all_rows)
        if not valid_rows:
            return InsertResult(
                inserted=0,
                skipped=0,
                invalid=invalid,
                completeness=self._completeness(all_rows),
            )
        payload = [tuple(row.get(slot) for slot in SLOTS) for row in valid_rows]
        sql = (
            f"INSERT IGNORE INTO cases ({', '.join(SLOTS)}) "
            f"VALUES ({', '.join(['%s'] * len(SLOTS))})"
        )
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(sql, payload)
                inserted = cursor.rowcount
                if inserted:
                    version_id = self._insert_version(cursor, action, description, operator, inserted)
                    self._snapshot(cursor, version_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return InsertResult(
            inserted=inserted,
            skipped=len(payload) - inserted,
            invalid=invalid,
            completeness=self._completeness(all_rows),
        )

    def list_versions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """按时间倒序返回版本记录。"""
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, version_code, operator, action, description, "
                "created_at, total_records, delta_records "
                "FROM data_versions ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            return list(cursor.fetchall())

    def restore_version(self, version_id: int, operator: str = "system") -> int:
        """用指定版本的整表快照覆盖 cases 表，并记录一次回滚动作。返回恢复条数。

        回滚本身也是一次数据变更：恢复数据后，在同一事务内写入一条
        ``action=restore`` 的版本记录并生成回滚后的新快照，保证可追溯。
        """
        cols = ", ".join(SLOTS)
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM cases")
                cursor.execute(
                    f"INSERT INTO cases (id, {cols}) "
                    f"SELECT case_id, {cols} FROM cases_snapshot WHERE version_id = %s",
                    (version_id,),
                )
                restored = cursor.rowcount
                new_version_id = self._insert_version(
                    cursor, "restore", f"从版本 {version_id} 回滚", operator, delta=0
                )
                self._snapshot(cursor, new_version_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return restored
