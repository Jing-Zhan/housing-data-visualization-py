"""演示数据适配器。

在无外网、无数据库的环境中生成与真实数据分布接近的样例行，
用于前端联调与"实时更新"演示（由调度器周期性调用）。
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from backend.adapters.base import DataSourceAdapter, Row
from backend.domain.profile import DomainProfile

DISTRICTS = ["朝阳区", "海淀区", "丰台区", "西城区", "东城区", "通州区"]
COMMUNITIES = ["阳光花园", "锦绣家园", "翠湖天地", "金域华府", "城市经典", "悦景湾"]
LAYOUTS = ["1室1厅", "2室1厅", "2室2厅", "3室2厅", "4室2厅"]
DECORATIONS = ["精装", "简装", "毛坯"]
ORIENTATIONS = ["南北", "南", "东南", "西南", "北"]
FLOORS = ["低楼层/共6层", "中楼层/共18层", "高楼层/共26层", "中楼层/共11层"]
TITLES = [
    "满五唯一 近地铁 精装两居",
    "南北通透 采光好 业主诚心出售",
    "学区房 楼层适中 看房方便",
    "低总价 首付低 拎包入住",
    "电梯房 精装修 近商圈",
]


class MockAdapter(DataSourceAdapter):
    """按领域配置生成演示数据。"""

    key = "mock"
    label = "演示数据（Mock）"
    kind = "mock"

    def fetch(self, limit: Optional[int] = None) -> List[Row]:
        count = int(limit or self.options.get("rows", 200))
        rng = random.Random(self.options.get("seed", 20260101))
        rows: List[Row] = []
        today = date.today()
        for index in range(count):
            layout = rng.choice(LAYOUTS)
            rooms = int(layout[0]) if layout[0].isdigit() else 2
            area = round(rng.uniform(38, 160) + rooms * 6, 1)
            unit_price = rng.uniform(4.2, 12.5)
            total = round(area * unit_price, 1)
            listed = today - timedelta(days=rng.randint(0, 90))
            rows.append(
                self.normalize(
                    {
                        "type": layout,
                        "gender": rng.choice(DECORATIONS),
                        "age": rng.randint(1, 32),
                        "time": listed.strftime("%m.%d"),
                        "content": rng.choice(TITLES),
                        "docName": f"{rng.choice('王李张刘陈杨')}××",
                        "docHospital": rng.choice(COMMUNITIES),
                        "department": rng.choice(DISTRICTS),
                        "detailUrl": f"https://example.com/house/{today:%Y%m%d}{index:04d}",
                        "height": area,
                        "weight": total,
                        "illDuration": rng.choice(FLOORS),
                        "allergy": f"{rng.choice(ORIENTATIONS)} · 满五唯一",
                    }
                )
            )
        return rows

    def describe(self) -> Dict[str, Any]:
        info = super().describe()
        info["note"] = "无外网环境下的演示数据，分布参数可在本文件调整"
        return info
