"""链家 / 贝壳列表页采集适配器（骨架）。

实现位置：``fetch`` → ``_crawl_page`` → ``_parse_item``。
采集约束：单页间隔不少于 5 秒、轮换 User-Agent、只取列表页公开字段，
``detailUrl`` 作为唯一键用于去重。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from backend.adapters.base import DataSourceAdapter, Row
from backend.domain.profile import DomainProfile

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]


class LianjiaCrawlerAdapter(DataSourceAdapter):
    """链家二手房列表页采集器。"""

    key = "crawler"
    label = "链家二手房列表页"
    kind = "crawler"

    def fetch(self, limit: Optional[int] = None) -> List[Row]:
        """按区域分页采集。

        待实现步骤：
        1. ``GET https://sh.lianjia.com/ershoufang/pg{page}/``，带随机 UA；
        2. 解析 ``div.info.clear`` 节点，取标题、小区、户型、面积、总价、单价、楼层、朝向；
        3. 组装为 13 个槽位后调用 ``self.normalize``；
        4. 每页间隔 ``self.options.get('interval', 5)`` 秒。
        """
        raise NotImplementedError("链家采集器待实现，参考本方法文档字符串")

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def _sleep(interval: float = 5.0) -> None:
        time.sleep(interval)

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info["site"] = "https://sh.lianjia.com/ershoufang/"
        info["interval_seconds"] = self.options.get("interval", 5)
        return info
