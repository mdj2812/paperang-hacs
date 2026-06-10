"""E2E tests for Paperang entities — real HA Core, mock transport.

Verifies coordinator data, transport configs, and entry lifecycle.
Entity existence is tested via platform-specific unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import (
    CONF_TRANSPORT,
    DOMAIN,
    TRANSPORT_BT,
    TRANSPORT_USB,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

PATCH_RUNTIME_GET = "custom_components.paperang.core.runtime._get_printer"


@pytest.fixture(autouse=True)
def _clear_all_caches() -> None:
    """Clear all module-level caches between tests."""
    from custom_components.paperang.core.runtime import _persistent_printers
    from custom_components.paperang.core.state import (
        _dynamic_caches,
        _static_caches,
    )

    _persistent_printers.clear()
    _static_caches.clear()
    _dynamic_caches.clear()
    yield
    _persistent_printers.clear()
    _static_caches.clear()
    _dynamic_caches.clear()


def _make_printer() -> MagicMock:
    """Return a fully mocked printer with all return values set."""
    p = MagicMock()
    # Dynamic reads
    p.get_battery.return_value = 80
    p.get_status.return_value = "online"
    # Static reads
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


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and set up a config entry, mocking forward_entry_setups."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TRANSPORT: TRANSPORT_USB},
        title="Paperang P2 (USB 1-3)",
    )
    entry.add_to_hass(hass)

    import custom_components.paperang as mod

    mock_p = _make_printer()
    with (
        patch(PATCH_RUNTIME_GET, return_value=mock_p),
        patch.object(mod, "async_setup", return_value=True),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", return_value=None
        ),
    ):
        await mod.async_setup_entry(hass, entry)

    return entry


class TestCoordinatorData:
    """Coordinator is populated with mock printer data."""

    async def test_coordinator_has_data(self, hass: HomeAssistant) -> None:
        """After setup, coordinator.data is populated."""
        entry = await _setup_entry(hass)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data is not None
        assert coordinator.data.get("available") is True
        assert coordinator.data.get("battery") == 80

    async def test_coordinator_static_fields(self, hass: HomeAssistant) -> None:
        """Coordinator has model, version, serial fields."""
        entry = await _setup_entry(hass)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data.get("model") == "P2"
        assert coordinator.data.get("version") == "V1.0.11"
        assert coordinator.data.get("serial") == "SN123"
        assert coordinator.data.get("board") == "V1.0"

    async def test_coordinator_dynamic_fields(self, hass: HomeAssistant) -> None:
        """Coordinator has battery and status."""
        entry = await _setup_entry(hass)
        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data.get("battery") == 80
        assert coordinator.data.get("status") == "online"
        assert coordinator.data.get("voltage") == 4200


class TestTransportConfigs:
    """Transport configs stored per entry."""

    async def test_transport_config_stored(self, hass: HomeAssistant) -> None:
        """Entry data stored in transport_configs."""
        entry = await _setup_entry(hass)

        import custom_components.paperang as mod

        assert entry.entry_id in mod._transport_configs
        assert mod._transport_configs[entry.entry_id][CONF_TRANSPORT] == TRANSPORT_USB


class TestEntryLifecycle:
    """Entry setup and unload."""

    async def test_setup_returns_true(self, hass: HomeAssistant) -> None:
        """async_setup returns True."""
        entry = await _setup_entry(hass)
        assert entry.entry_id in hass.data[DOMAIN]

    async def test_unload_cleans_up(self, hass: HomeAssistant) -> None:
        """Unload removes coordinator and caches."""
        entry = await _setup_entry(hass)

        import custom_components.paperang as mod

        mock_p = _make_printer()
        with patch(PATCH_RUNTIME_GET, return_value=mock_p):
            result = await mod.async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data.get(DOMAIN, {})


class TestBTEntryPollingInterval:
    """BT entry uses 30s poll interval."""

    async def test_bt_entry_30s_poll(self, hass: HomeAssistant) -> None:
        """BT transport → 30s interval."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_BT},
            title="Paperang P2 (BT)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        mock_p = _make_printer()
        with (
            patch(PATCH_RUNTIME_GET, return_value=mock_p),
            patch.object(mod, "async_setup", return_value=True),
            patch.object(
                hass.config_entries, "async_forward_entry_setups", return_value=None
            ),
        ):
            await mod.async_setup_entry(hass, entry)

        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.update_interval.seconds == 30


class TestEntityImports:
    """All entity modules are importable (class existence)."""

    def test_sensor_entity_imports(self) -> None:
        """Sensor entity class can be imported."""
        from custom_components.paperang.sensor import PaperangSensor

        assert PaperangSensor is not None

    def test_button_entity_imports(self) -> None:
        """Button entity classes can be imported."""
        from custom_components.paperang.button import PaperangPrintButton

        assert PaperangPrintButton is not None

    def test_select_entity_imports(self) -> None:
        """Select entity classes can be imported."""
        from custom_components.paperang.select import PaperangPrintModeSelect

        assert PaperangPrintModeSelect is not None

    def test_number_entity_imports(self) -> None:
        """Number entity class can be imported."""
        from custom_components.paperang.number import PaperangNumber

        assert PaperangNumber is not None

    def test_text_entity_imports(self) -> None:
        """Text entity class can be imported."""
        from custom_components.paperang.text import PaperangPrintContent

        assert PaperangPrintContent is not None

    def test_switch_entity_imports(self) -> None:
        """Switch entity class can be imported."""
        from custom_components.paperang.switch import PaperangVerticalSwitch

        assert PaperangVerticalSwitch is not None
