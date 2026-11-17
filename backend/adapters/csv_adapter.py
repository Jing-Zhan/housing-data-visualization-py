"""离线文件适配器：读取 CSV / Excel 并映射到 13 个槽位。

用法::

    adapter = CsvAdapter(profile, path="data/sample_house.csv")
    rows = adapter.fetch(limit=100)
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.adapters.base import DataSourceAdapter, Row
from backend.domain.profile import DomainProfile


class CsvAdapter(DataSourceAdapter):
    """CSV / Excel 文件适配器，列名即槽位名。"""

    key = "csv"
    label = "离线文件（CSV / Excel）"
    kind = "file"

    REQUIRED = ("type", "content")

    def fetch(self, limit: Optional[int] = None) -> List[Row]:
        path = self.options.get("path")
        if not path:
            raise ValueError("CsvAdapter 需要 path 参数")

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在：{file_path}")

        if file_path.suffix.lower() in (".xlsx", ".xls"):
            records = self._read_excel(file_path)
        else:
            records = self._read_csv(file_path)

        missing = [key for key in self.REQUIRED if key not in records[0]] if records else []
        if missing:
            raise ValueError(f"文件缺少必需列：{', '.join(missing)}")

        rows = [self.normalize(record) for record in records]
        return rows[:limit] if limit else rows

    @staticmethod
    def _read_csv(file_path: Path) -> List[Dict[str, Any]]:
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with file_path.open("r", encoding=encoding, newline="") as handle:
                    return list(csv.DictReader(handle))
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("csv", b"", 0, 1, "无法识别文件编码，请另存为 UTF-8")

    @staticmethod
    def _read_excel(file_path: Path) -> List[Dict[str, Any]]:
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("读取 Excel 需要 pandas，请执行 pip install -r requirements.txt") from exc
        frame = pd.read_excel(file_path)
        return frame.where(frame.notnull(), None).to_dict(orient="records")
