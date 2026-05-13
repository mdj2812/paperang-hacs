"""Test fixtures for paperang custom component tests.

Uses pytest-homeassistant-custom-component for the ``hass`` fixture,
with fallback stubs when the plugin is not available.
"""
import sys
from unittest.mock import MagicMock

# ── Try loading the plugin; fall back to stubs if unavailable ────

try:
    # pylint: disable-next=unused-import
    import pytest_homeassistant_custom_component  # noqa: F401 — used as pytest plugin
    HAS_HASS = True
except ImportError:
    HAS_HASS = False

    # Stubs — only used when plugin is not installed
    _ha = MagicMock()
    _ha.setup = MagicMock()
    _ha.const.Platform = MagicMock()
    _ha.const.Platform.SENSOR = "sensor"
    _ha.const.Platform.BUTTON = "button"
    _ha.const.Platform.SELECT = "select"
    _ha.const.Platform.NUMBER = "number"
    _ha.const.Platform.TEXT = "text"
    setattr(_ha.const, "__all__", [])

    _ce_mod = type(sys)("homeassistant.config_entries")
    class _ConfigFlowBase:
        VERSION = 1
        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
    _ce_mod.ConfigFlow = _ConfigFlowBase
    _ce_mod.OptionsFlow = object
    sys.modules["homeassistant.config_entries"] = _ce_mod

    _ha.core = MagicMock()
    _ha.core.HomeAssistant = MagicMock
    _ha.core.callback = lambda f: f

    _ha.helpers.typing = MagicMock()
    _ha.helpers.typing.ConfigType = dict
    _ha.helpers.update_coordinator = MagicMock()
    _ha.util = MagicMock()
    _ha.auth.permissions.const = MagicMock()
    _ha.auth.permissions.const.POLICY_READ = "read"

    for mod, stub in [
        ("homeassistant", _ha),
        ("homeassistant.const", _ha.const),
        ("homeassistant.core", _ha.core),
        ("homeassistant.helpers", _ha.helpers),
        ("homeassistant.helpers.typing", _ha.helpers.typing),
        ("homeassistant.helpers.update_coordinator", _ha.helpers.update_coordinator),
        ("homeassistant.util", _ha.util),
        ("homeassistant.auth", _ha.auth),
        ("homeassistant.auth.permissions", _ha.auth.permissions),
        ("homeassistant.auth.permissions.const", _ha.auth.permissions.const),
    ]:
        sys.modules[mod] = stub


# ── paperang-p2-lib stubs (always needed in CI) ──────────────────

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

for mod in ("paperang", "paperang.transport"):
    sys.modules[mod] = _paperang if mod == "paperang" else _paperang.transport
