"""Test fixtures for paperang custom component — HA core style."""
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

# ── paperang-p2-lib stubs (needed since lib isn't installed with extras) ──

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
_paperang.transport.BleTransport = MagicMock


@pytest.fixture(autouse=True)
def _mock_paperang() -> Generator[None]:
    """Stub paperang-p2-lib so tests run without USB/BLE hardware."""
    import sys
    with (
        patch.dict(sys.modules, {"paperang": _paperang}),
        patch.dict(sys.modules, {"paperang.transport": _paperang.transport}),
    ):
        yield


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.paperang.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup
