"""Stub homeassistant so tests run without a full HA installation."""
import sys
from unittest.mock import AsyncMock, MagicMock

# ── homeassistant stubs ───────────────────────────────────────────

_ha = MagicMock()
_ha.setup = MagicMock()
_ha.const.Platform = MagicMock()  # type: ignore
_ha.const.Platform.SENSOR = "sensor"
_ha.const.Platform.BUTTON = "button"
_ha.const.Platform.SELECT = "select"
_ha.const.Platform.NUMBER = "number"
_ha.const.Platform.TEXT = "text"
setattr(_ha.const, "__all__", [])

# config_entries
_ha.config_entries = MagicMock()
_ha.config_entries.ConfigFlow = object

class FakeConfigEntry:
    """Minimal config entry for testing migration."""
    def __init__(self, version=1, data=None):
        self.version = version
        self.data = data or {}

_ha.config_entries.ConfigEntry = FakeConfigEntry

# core
_ha.core = MagicMock()
_ha.core.HomeAssistant = MagicMock
_ha.core.callback = lambda f: f

# helpers
_ha.helpers.typing = MagicMock()
_ha.helpers.typing.ConfigType = dict
_ha.helpers.update_coordinator = MagicMock()

# util
_ha.util = MagicMock()

# request
_ha.auth.permissions.const = MagicMock()
_ha.auth.permissions.const.POLICY_READ = "read"

# ── voluptuous (real) ────────────────────────────────────────────
# Already installed — imported normally by config_flow


# ── paperang-p2-lib stubs ────────────────────────────────────────

_paperang = MagicMock()
_paperang.PaperangP2 = MagicMock
_paperang.PaperangPrinter = MagicMock
_paperang.load_profiles = MagicMock(return_value={})
_paperang.list_profiles = MagicMock()
_paperang.crc32_paperang = MagicMock()
_paperang.pack_packet = MagicMock()

_transport = MagicMock()
_transport.Transport = object
_transport.UsbTransport = MagicMock
_transport.BleTransport = MagicMock
_paperang.transport = _transport


# ── Inject into sys.modules ──────────────────────────────────────

sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.const"] = _ha.const
sys.modules["homeassistant.config_entries"] = _ha.config_entries
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.helpers"] = _ha.helpers
sys.modules["homeassistant.helpers.typing"] = _ha.helpers.typing
sys.modules["homeassistant.helpers.update_coordinator"] = _ha.helpers.update_coordinator
sys.modules["homeassistant.util"] = _ha.util
sys.modules["homeassistant.auth"] = _ha.auth
sys.modules["homeassistant.auth.permissions"] = _ha.auth.permissions
sys.modules["homeassistant.auth.permissions.const"] = _ha.auth.permissions.const

sys.modules["paperang"] = _paperang
sys.modules["paperang.transport"] = _transport
