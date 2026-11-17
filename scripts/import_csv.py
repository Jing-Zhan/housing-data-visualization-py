"""把 CSV / Excel 导入 cases 表。

用法::

    python scripts/import_csv.py --file data/sample_house.csv --domain house
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.adapters.csv_adapter import CsvAdapter  # noqa: E402
from backend.config import Config  # noqa: E402
from backend.domain.profile import DomainProfile  # noqa: E402
from backend.repo.case_repo import CaseRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="导入离线房源数据")
    parser.add_argument("--file", required=True, help="CSV 或 Excel 文件路径")
    parser.add_argument("--domain", default="house", help="领域配置名")
    parser.add_argument("--limit", type=int, default=None, help="最多导入条数")
    args = parser.parse_args()

    profile = DomainProfile.load(args.domain, Config.DOMAIN_DIR)
    adapter = CsvAdapter(profile, path=args.file)
    rows = adapter.fetch(limit=args.limit)
    print(f"解析完成：{len(rows)} 条")

    repo = CaseRepository(Config.DB_CONFIG)
    if not repo.ping():
        print("数据库连接失败，请检查 .env 中的 DB_* 配置")
        return 1

    inserted = repo.insert_many(rows)
    print(f"写入完成：新增 {inserted} 条，当前总数 {repo.count()} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
