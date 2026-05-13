"""Stub homeassistant so tests run without a full HA installation."""
# pylint: disable=unused-import
import sys
from unittest.mock import MagicMock  # noqa: F401

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

# config_entries — use real module object so subclassing works
class _ConfigFlowBase:
    """Fake ConfigFlow that accepts domain= kwarg."""
    VERSION = 1

    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)

    @staticmethod
    def async_get_options_flow(config_entry):
        return None

    async def async_set_unique_id(self, unique_id):
        pass

    def _abort_if_unique_id_configured(self):
        pass

    def async_create_entry(self, title, data):
        return MagicMock()

    def async_show_form(self, step_id, data_schema=None):
        return {}

_ce_mod = type(sys)("homeassistant.config_entries")
_ce_mod.ConfigFlow = _ConfigFlowBase
_ce_mod.OptionsFlow = object
sys.modules["homeassistant.config_entries"] = _ce_mod

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

# auth
_ha.auth.permissions.const = MagicMock()
_ha.auth.permissions.const.POLICY_READ = "read"

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
