"""E2E tests for multi-device Paperang — two entries, isolated coordinators."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import CONF_TRANSPORT, DOMAIN, TRANSPORT_USB

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

PATCH_RUNTIME_GET = "custom_components.paperang.core.runtime._get_printer"



def _make_printer(battery: int = 80) -> MagicMock:
    """Return a mocked printer with all return values set."""
    p = MagicMock()
    p.get_battery.return_value = battery
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


class TestMultiDevice:
    """Two config entries coexist with isolated coordinators."""

    async def test_two_entries_independent_coordinators(
        self, hass: HomeAssistant
    ) -> None:
        """Each entry gets its own coordinator."""
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

        p1 = _make_printer(80)
        p2 = _make_printer(50)

        def _getter(entry_id):
            return p1 if entry_id == entry1.entry_id else p2

        with (
            patch(PATCH_RUNTIME_GET, side_effect=_getter),
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
        assert c1.data is not None
        assert c2.data is not None

    async def test_unload_one_leaves_other(self, hass: HomeAssistant) -> None:
        """Unloading entry1 does not affect entry2."""
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

        p = _make_printer()
        with (
            patch(PATCH_RUNTIME_GET, return_value=p),
            patch.object(mod, "async_setup", return_value=True),
            patch.object(
                hass.config_entries, "async_forward_entry_setups", return_value=None
            ),
        ):
            await mod.async_setup_entry(hass, entry1)
            await mod.async_setup_entry(hass, entry2)

        with patch(PATCH_RUNTIME_GET, return_value=_make_printer()):
            await mod.async_unload_entry(hass, entry1)

        assert entry1.entry_id not in hass.data.get(DOMAIN, {})
        assert entry2.entry_id in hass.data.get(DOMAIN, {})


class TestMultiDeviceTransportConfigs:
    """Each entry has its own transport config."""

    async def test_transport_configs_per_entry(self, hass: HomeAssistant) -> None:
        """transport_configs keyed per entry_id."""
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

        p = _make_printer()
        with (
            patch(PATCH_RUNTIME_GET, return_value=p),
            patch.object(mod, "async_setup", return_value=True),
            patch.object(
                hass.config_entries, "async_forward_entry_setups", return_value=None
            ),
        ):
            await mod.async_setup_entry(hass, entry1)
            await mod.async_setup_entry(hass, entry2)

        assert entry1.entry_id in mod._transport_configs
        assert entry2.entry_id in mod._transport_configs
        assert (
            mod._transport_configs[entry1.entry_id]
            is not mod._transport_configs[entry2.entry_id]
        )
