"""开放数据接口适配器（骨架）。

面向各地公共数据开放平台（如深圳开放数据平台的"二手房成交按日统计"），
调用方需在 ``.env`` 中配置 ``OPEN_DATA_APP_KEY``。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.adapters.base import DataSourceAdapter, Row
from backend.domain.profile import DomainProfile


class OpenDataApiAdapter(DataSourceAdapter):
    """公共数据开放平台接口适配器。"""

    key = "api"
    label = "开放数据接口"
    kind = "api"

    def fetch(self, limit: Optional[int] = None) -> List[Row]:
        """调用开放平台接口并转换字段。

        待实现步骤：
        1. 读取 ``app_key`` 与接口地址 ``self.options['url']``；
        2. 按日 / 按区分页拉取成交记录；
        3. 把"成交日期、区域、小区、面积、总价"映射到 13 个槽位；
        4. 调用 ``self.normalize`` 后返回。
        """
        raise NotImplementedError("开放数据接口适配器待实现，参考本方法文档字符串")

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info["platform"] = "https://opendata.sz.gov.cn/"
        return info
