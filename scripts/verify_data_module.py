# -*- coding: utf-8 -*-
"""数据入库模块自检脚本。

在临时数据库中跑一遍入库模块的核心场景，逐项输出 PASS / FAIL，
结束后默认删除临时库（加 ``--keep`` 保留现场）。

用法：

    # 方式一：仓库根目录有 .env，直接读里面的 DB_*
    python scripts/verify_data_module.py

    # 方式二：用环境变量传数据库连接信息
    set DB_USER=root
    set DB_PASSWORD=******
    python scripts/verify_data_module.py --keep

检查项对应需求 FR-04（去重）、FR-06（事务回滚）、FR-07（版本快照）、
FR-08（版本回滚）以及 7.4 节的数据质量规则。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.repo.case_repo import CaseRepository  # noqa: E402

SCHEMA = ROOT / "backend" / "models" / "schema.sql"

RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"：{detail}" if detail else ""))


def load_env() -> dict:
    """优先读环境变量，其次读仓库根目录的 .env。"""
    values = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip()
    for key in ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_CHARSET"):
        if os.getenv(key):
            values[key] = os.getenv(key)
    return {
        "host": values.get("DB_HOST", "127.0.0.1"),
        "port": int(values.get("DB_PORT", "3306")),
        "user": values.get("DB_USER", "root"),
        "password": values.get("DB_PASSWORD", ""),
        "charset": values.get("DB_CHARSET", "utf8mb4"),
    }


def create_database(base: dict, db_name: str) -> dict:
    conn = pymysql.connect(**base)
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            cursor.execute(f"CREATE DATABASE `{db_name}` DEFAULT CHARACTER SET utf8mb4")
    finally:
        conn.close()

    db_config = dict(base)
    db_config["database"] = db_name
    sql_text = SCHEMA.read_text(encoding="utf-8")
    statements = [
        stmt.strip()
        for stmt in sql_text.split(";")
        if stmt.strip()
        and not stmt.strip().upper().startswith("CREATE DATABASE")
        and not stmt.strip().upper().startswith("USE ")
    ]
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            for stmt in statements:
                cursor.execute(stmt)
        conn.commit()
    finally:
        conn.close()
    return db_config


def make_row(index: int, **overrides) -> dict:
    row = {
        "type": "2室1厅",
        "gender": "精装",
        "age": "5",
        "time": "03.15",
        "content": f"满五唯一 近地铁 测试房源 {index}",
        "docName": "王××",
        "docHospital": "阳光花园",
        "department": "朝阳区",
        "detailUrl": f"https://example.com/verify/{index}",
        "height": "89.5",
        "weight": "420",
        "illDuration": "中楼层/共18层",
        "allergy": "南北",
    }
    row.update(overrides)
    return row


def table_count(repo: CaseRepository) -> int:
    return repo.count()


def main() -> int:
    parser = argparse.ArgumentParser(description="数据入库模块自检")
    parser.add_argument("--keep", action="store_true", help="保留临时数据库")
    parser.add_argument("--db", default=None, help="指定临时库名，默认自动生成")
    args = parser.parse_args()

    base = load_env()
    db_name = args.db or f"housing_verify_{int(time.time())}"
    print(f"临时数据库：{db_name}\n")

    db_config = create_database(base, db_name)
    repo = CaseRepository(db_config)

    try:
        # 1. 空表
        check("初始表为空", table_count(repo) == 0, f"count={table_count(repo)}")

        # 2. 批量写入 3 条
        result = repo.insert_many([make_row(i) for i in range(3)])
        check(
            "批量写入 3 条",
            result.inserted == 3 and table_count(repo) == 3,
            f"inserted={result.inserted}, count={table_count(repo)}",
        )

        # 3. 重复写入，按详情链接去重
        result = repo.insert_many([make_row(i) for i in range(3)])
        check(
            "重复写入被跳过",
            result.inserted == 0 and result.skipped == 3 and table_count(repo) == 3,
            f"inserted={result.inserted}, skipped={result.skipped}, count={table_count(repo)}",
        )

        # 4. 数据质量：缺必填字段与数值越界
        bad_rows = [
            make_row(10),
            make_row(11),
            make_row(12, content=""),
            make_row(13, height="5000"),
        ]
        result = repo.insert_many(bad_rows)
        check(
            "异常数据被过滤",
            result.inserted == 2 and result.invalid == 2 and table_count(repo) == 5,
            f"inserted={result.inserted}, invalid={result.invalid}, count={table_count(repo)}",
        )

        # 5. 带版本写入：数据与快照同时落库
        result = repo.insert_with_version(
            [make_row(20), make_row(21)], action="verify", description="自检写入"
        )
        versions = repo.list_versions()
        snapshot_ok = False
        if versions:
            with pymysql.connect(**db_config) as conn, conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM cases_snapshot WHERE version_id=%s",
                    (versions[0]["id"],),
                )
                snapshot_ok = cursor.fetchone()[0] == table_count(repo)
        check(
            "带版本写入生成快照",
            result.inserted == 2 and len(versions) == 1 and snapshot_ok,
            f"inserted={result.inserted}, versions={len(versions)}, count={table_count(repo)}",
        )

        # 6. 事务回滚：中途失败，数据与版本都不应写入（注入异常触发）
        before_count = table_count(repo)
        before_versions = len(repo.list_versions())
        broken = [make_row(30), make_row(31)]
        rolled_back = False
        original = pymysql.cursors.DictCursor.executemany

        def _boom(self, *args, **kwargs):
            raise RuntimeError("模拟写入失败")

        pymysql.cursors.DictCursor.executemany = _boom
        try:
            repo.insert_with_version(broken, action="verify", description="构造失败")
        except Exception as exc:  # noqa: BLE001 - 预期异常
            rolled_back = True
            print(f"      捕获预期异常：{type(exc).__name__}")
        finally:
            pymysql.cursors.DictCursor.executemany = original
        check(
            "写入失败整批回滚",
            rolled_back
            and table_count(repo) == before_count
            and len(repo.list_versions()) == before_versions,
            f"count={table_count(repo)}, versions={len(repo.list_versions())}",
        )

        # 7. 回滚到历史版本
        first_version = repo.list_versions()[-1]["id"]
        target_count = table_count(repo)
        restored = repo.restore_version(first_version)
        check(
            "按版本恢复数据",
            restored == target_count and table_count(repo) == restored,
            f"restored={restored}, count={table_count(repo)}",
        )
        check(
            "回滚动作记入版本",
            len(repo.list_versions()) == before_versions + 1,
            f"versions={len(repo.list_versions())}",
        )

        # 8. 回滚到不存在的版本：应报错且数据不变
        before_count = table_count(repo)
        raised = False
        try:
            repo.restore_version(999999)
        except Exception as exc:  # noqa: BLE001 - 预期异常
            raised = True
            print(f"      捕获异常：{type(exc).__name__}")
        check(
            "不存在的版本被拒绝",
            raised and table_count(repo) == before_count,
            f"raised={raised}, count={table_count(repo)}（原 {before_count}）",
        )
    finally:
        if not args.keep:
            conn = pymysql.connect(**base)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            finally:
                conn.close()
        else:
            print(f"\n临时库已保留：{db_name}")

    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n结果：{passed}/{total} 项通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
