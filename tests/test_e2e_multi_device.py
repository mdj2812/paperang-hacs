"""E2E tests for multi-device Paperang setup — two config entries, no collisions."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import CONF_TRANSPORT, DOMAIN, TRANSPORT_USB

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

PATCH_RUNTIME_GET = "custom_components.paperang.core.runtime._get_printer"


@pytest.fixture(autouse=True)
def _clear_persistent_printers() -> None:
    """Clear persistent printer cache between tests."""
    from custom_components.paperang.core.runtime import _persistent_printers

    _persistent_printers.clear()
    yield
    _persistent_printers.clear()


@pytest.fixture
def mock_printer() -> MagicMock:
    """Return a fully mocked printer."""
    mock_p = MagicMock()
    mock_p.get_battery.return_value = 80
    mock_p.get_status.return_value = "online"
    mock_p.get_voltage.return_value = 4200
    mock_p.get_temperature.return_value = 35
    mock_p.get_heat_density.return_value = 75
    mock_p.get_paper_type.return_value = "normal"
    return mock_p


class TestMultiDevice:
    """Two config entries coexist without entity ID collisions."""

    async def test_two_entries_different_entity_ids(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Entity unique_ids are scoped per entry_id."""
        entry1 = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry2 = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 2-1)",
        )
        entry1.add_to_hass(hass)
        entry2.add_to_hass(hass)

        import custom_components.paperang as mod

        with (
            patch(PATCH_RUNTIME_GET, return_value=mock_printer),
            patch.object(mod, "async_setup", return_value=True),
            patch.object(
                hass.config_entries, "async_forward_entry_setups", return_value=None
            ),
        ):
            await mod.async_setup_entry(hass, entry1)
            await mod.async_setup_entry(hass, entry2)

        registry = er.async_get(hass)
        eid1 = entry1.entry_id
        eid2 = entry2.entry_id

        # Both entries get their own battery sensor
        uid1 = f"paperang_{eid1}_battery"
        uid2 = f"paperang_{eid2}_battery"
        entity1 = registry.async_get_entity_id("sensor", DOMAIN, uid1)
        entity2 = registry.async_get_entity_id("sensor", DOMAIN, uid2)
        assert entity1 is not None
        assert entity2 is not None
        assert entity1 != entity2, "Entity IDs must differ between devices"

        # Both get their own vertical switch
        uid1v = f"paperang_{eid1}_vertical"
        uid2v = f"paperang_{eid2}_vertical"
        sw1 = registry.async_get_entity_id("switch", DOMAIN, uid1v)
        sw2 = registry.async_get_entity_id("switch", DOMAIN, uid2v)
        assert sw1 is not None
        assert sw2 is not None
        assert sw1 != sw2

    async def test_unload_one_entry_leaves_other(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Unloading one entry does not affect the other."""
        entry1 = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 1-3)",
        )
        entry2 = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Paperang P2 (USB 2-1)",
        )
        entry1.add_to_hass(hass)
        entry2.add_to_hass(hass)

        import custom_components.paperang as mod

        with (
            patch(PATCH_RUNTIME_GET, return_value=mock_printer),
            patch.object(mod, "async_setup", return_value=True),
            patch.object(
                hass.config_entries, "async_forward_entry_setups", return_value=None
            ),
        ):
            await mod.async_setup_entry(hass, entry1)
            await mod.async_setup_entry(hass, entry2)

        # Unload entry1
        with patch(PATCH_RUNTIME_GET, return_value=mock_printer):
            await mod.async_unload_entry(hass, entry1)

        # entry1 gone, entry2 still present
        assert entry1.entry_id not in hass.data.get(DOMAIN, {})
        assert entry2.entry_id in hass.data.get(DOMAIN, {})


class TestMultiDeviceCoordinators:
    """Each device has its own coordinator with its own data."""

    async def test_coordinators_independent(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Two entries → two coordinators, different data instances."""
        mock2 = MagicMock()
        mock2.get_battery.return_value = 50
        mock2.get_status.return_value = "offline"

        entry1 = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Printer A",
        )
        entry2 = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_USB},
            title="Printer B",
        )
        entry1.add_to_hass(hass)
        entry2.add_to_hass(hass)

        import custom_components.paperang as mod

        def _get_printer_side_effect(entry_id):
            return mock_printer if entry_id == entry1.entry_id else mock2

        with (
            patch(
                PATCH_RUNTIME_GET,
                side_effect=_get_printer_side_effect,
            ),
            patch.object(mod, "async_setup", return_value=True),
            patch.object(
                hass.config_entries, "async_forward_entry_setups", return_value=None
            ),
        ):
            await mod.async_setup_entry(hass, entry1)
            await mod.async_setup_entry(hass, entry2)

        c1 = hass.data[DOMAIN][entry1.entry_id]
        c2 = hass.data[DOMAIN][entry2.entry_id]
        assert c1 is not c2
