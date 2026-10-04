"""Test fixtures for paperang custom component — HA Core style."""

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


class _StubModel:
    """Minimal stand-in for paperang.models.PrinterModel."""

    def __init__(self, name: str, print_width: int) -> None:
        self.name = name
        self.print_width = print_width
        self.line_bytes = print_width // 8


STUB_MODELS = {
    "p2": _StubModel("P2", 576),
    "d1": _StubModel("D1", 384),
}


def _stub_get_model(model=None):
    if model is None:
        return STUB_MODELS["p2"]
    return STUB_MODELS[str(model).strip().lower()]


def _stub_resolve_model(vid=None, pid=None, reported_name=None):
    """Resolve like the library does: reported name first, then USB ID."""
    if reported_name and "d1" in str(reported_name).lower():
        return STUB_MODELS["d1"]
    if pid == 0x5585:
        return STUB_MODELS["d1"]
    return STUB_MODELS["p2"]


_paperang.Paperang = _paperang.PaperangP2
_paperang.DEFAULT_MODEL = "p2"
_paperang.usb_pids = MagicMock(return_value=(0x5584, 0x5585))
_paperang.get_model = MagicMock(side_effect=_stub_get_model)
_paperang.list_models = MagicMock(return_value=dict(STUB_MODELS))
_paperang.resolve_model = MagicMock(side_effect=_stub_resolve_model)

sys.modules["paperang"] = _paperang
sys.modules["paperang.transport"] = _paperang.transport


@pytest.fixture(autouse=True)
def _mock_paperang() -> Generator[None]:
    """Re-apply paperang stubs per test (already set at module level)."""
    yield


# ── Shared fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_persistent_printers() -> Generator[None]:
    """Clear persistent printer connection cache between tests.

    Only clears the transport-level connection cache — NOT the data
    caches (_static_caches / _dynamic_caches).  Those are per-entry
    and the production code clears them via ``clear_caches_for_entry``
    on ``async_unload_entry``.
    """
    from custom_components.paperang.core.runtime import _persistent_printers

    _persistent_printers.clear()
    yield
    _persistent_printers.clear()


@pytest.fixture
def mock_printer() -> MagicMock:
    """Return a fully mocked printer with all sensor return values set."""
    p = MagicMock()
    p.get_battery.return_value = 80
    p.get_status.return_value = "online"
    p.get_voltage.return_value = 4200
    p.get_temperature.return_value = 35
    p.get_heat_density.return_value = 75
    p.get_paper_type.return_value = "normal"
    p.get_version.return_value = "720897"
    p.get_model.return_value = "P2"
    p.get_sn.return_value = "SN123"
    p.get_board_version.return_value = "V1.0"
    p.get_hw_info.return_value = "ABC"
    return p


# ── Legacy fixtures (kept for backward compat) ───────────────────────


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
