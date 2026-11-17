"""指标与图表计算的纯函数测试。"""

from backend.config import Config
from backend.domain.profile import DomainProfile
from backend.services import chart_service, kpi_service

PROFILE = DomainProfile.load("house", Config.DOMAIN_DIR)

ROWS = [
    {"type": "2室1厅", "gender": "精装", "age": "3", "height": "80", "weight": "300",
     "department": "朝阳区", "content": "满五唯一 近地铁", "detailUrl": "u1"},
    {"type": "2室1厅", "gender": "简装", "age": "12", "height": "90", "weight": "420",
     "department": "海淀区", "content": "南北通透", "detailUrl": "u2"},
    {"type": "3室2厅", "gender": "精装", "age": "25", "height": "120", "weight": "760",
     "department": "朝阳区", "content": "学区房 满五唯一", "detailUrl": "u3"},
]


def test_summary_counts_and_averages():
    summary = kpi_service.summarize(ROWS, PROFILE)
    assert summary["total"] == 3
    assert summary["topType"] == "2室1厅"
    assert summary["topDepartment"] == "朝阳区"
    assert summary["avgWeight"] == 493.3


def test_age_pie_uses_profile_bins():
    data = chart_service.age_pie(ROWS, PROFILE)
    assert len(data) == len(PROFILE.bins)
    assert sum(item["value"] for item in data) == 3


def test_split_ratio_matches_configured_values():
    data = chart_service.split_ratio(ROWS, PROFILE)
    assert data["left"]["name"] == "精装"
    assert data["left"]["count"] == 2
    assert data["right"]["count"] == 1


def test_mean_by_type_returns_three_series():
    data = chart_service.mean_by_type(ROWS, PROFILE)
    assert len(data["xData"]) == 2
    assert len(data["y1Data"]) == len(data["xData"])


def test_word_cloud_hits_keywords():
    data = chart_service.word_cloud(ROWS, PROFILE)
    names = [item["name"] for item in data]
    assert "满五唯一" in names
