"""Test fixtures for paperang custom component — HA core style."""

import sys
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

# ── paperang-p2-lib stubs (needed since lib isn't installed with extras) ──
# Must be set up at module level BEFORE any test files import custom_components.

_paperang = MagicMock()
_paperang.PaperangP2 = MagicMock
_paperang.PaperangPrinter = MagicMock
_paperang.load_profiles = MagicMock(return_value={})
_paperang.list_profiles = MagicMock()
_paperang.crc32_paperang = MagicMock()
_paperang.pack_packet = MagicMock()
_paperang.transport = MagicMock()
_paperang.transport.Transport = object
_paperang.transport.UsbTransport = MagicMock

sys.modules["paperang"] = _paperang
sys.modules["paperang.transport"] = _paperang.transport


@pytest.fixture(autouse=True)
def _mock_paperang() -> Generator[None]:
    """Re-apply paperang stubs per test (already set at module level)."""
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.paperang.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


class MockConfigEntry(ConfigEntry):
    """Minimal mock config entry for testing."""

    def __init__(self, *, domain, data=None, unique_id=None, **kwargs):
        super().__init__(data=data or {})  # type: ignore[call-arg]

    def add_to_hass(self, hass):
        """Add this entry to the hass instance."""
        hass.config_entries._entries.append(self)
