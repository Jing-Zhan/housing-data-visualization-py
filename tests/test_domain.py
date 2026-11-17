"""领域配置的加载与字段语义。"""

from backend.config import Config
from backend.domain.profile import DomainProfile


def test_house_profile_has_13_slots():
    profile = DomainProfile.load("house", Config.DOMAIN_DIR)
    assert len(profile.slots) == 13
    assert profile.label("type") == "户型"
    assert profile.label("weight") == "挂牌总价"
    assert profile.chart_title("age") == "各房龄段占比"


def test_medical_profile_keeps_legacy_labels():
    profile = DomainProfile.load("medical", Config.DOMAIN_DIR)
    assert profile.label("type") == "疾病类型"
    assert profile.split_values == ["男", "女"]


def test_profile_to_dict_contains_fields():
    profile = DomainProfile.load("house", Config.DOMAIN_DIR)
    payload = profile.to_dict()
    assert payload["name"] == "house"
    assert len(payload["fields"]) == 13
    assert payload["fields"][0]["key"] == "type"
