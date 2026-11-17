"""适配器工厂与演示数据适配器。"""

import pytest

from backend.adapters.mock_adapter import MockAdapter
from backend.adapters.registry import ADAPTERS, create_adapter
from backend.config import Config
from backend.domain.profile import DomainProfile

PROFILE = DomainProfile.load("house", Config.DOMAIN_DIR)


def test_registry_contains_four_kinds():
    assert set(ADAPTERS) == {"mock", "csv", "crawler", "api"}


def test_mock_adapter_returns_full_slots():
    adapter = create_adapter(PROFILE, "mock", rows=10, seed=7)
    rows = adapter.fetch()
    assert len(rows) == 10
    assert set(rows[0]) == set(PROFILE.slots)
    assert rows[0]["detailUrl"].startswith("https://")


def test_mock_adapter_is_deterministic_with_seed():
    first = MockAdapter(PROFILE, rows=5, seed=9).fetch()
    second = MockAdapter(PROFILE, rows=5, seed=9).fetch()
    assert first == second


def test_unknown_adapter_raises():
    with pytest.raises(ValueError):
        create_adapter(PROFILE, "unknown")
