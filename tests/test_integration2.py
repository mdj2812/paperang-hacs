"""Tests for paperang integration — HA service calls and entry setup."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import DOMAIN, TRANSPORT_USB, CONF_TRANSPORT

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_PATCH_STATE_GET = "custom_components.paperang.core.state._get_printer"
_PATCH_BLOCK_GET = "custom_components.paperang.core.blocking._get_printer"


@pytest.fixture
def mock_p():
    """Return a fully mocked printer."""
    mp = MagicMock()
    mp.get_battery.return_value = 80
    mp.get_status.return_value = "online"
    mp.get_voltage.return_value = 4200
    mp.get_temperature.return_value = 35
    mp.get_heat_density.return_value = 75
    mp.get_paper_type.return_value = "normal"
    mp.get_version.return_value = "720897"
    mp.get_model.return_value = "P2"
    mp.get_sn.return_value = "SN123"
    mp.get_board_version.return_value = "V1.0"
    mp.get_hw_info.return_value = "ABC"
    return mp


async def _setup_entry(hass, mock_p, extra_data=None):
    """Set up a config entry with mocked printer, skip platform loading."""
    data = {CONF_TRANSPORT: TRANSPORT_USB}
    if extra_data:
        data.update(extra_data)
    entry = MockConfigEntry(domain=DOMAIN, data=data, title="Paperang P2 (USB 1-3)")
    entry.add_to_hass(hass)

    import custom_components.paperang as mod
    # Register services (async_setup is called once per HA instance)
    await mod.async_setup(hass, {})
    with patch(_PATCH_STATE_GET, return_value=mock_p):
        with patch.object(hass.config_entries, "async_forward_entry_setups", return_value=None):
            await mod.async_setup_entry(hass, entry)
    return entry


class TestServiceRegistration:
    async def test_async_setup_registers_services(self, hass: HomeAssistant) -> None:
        """async_setup registers all 7 services."""
        import custom_components.paperang as mod

        await mod.async_setup(hass, {})

        for svc in ("print_text", "print_image", "print_qr", "print_pickup_code",
                     "get_status", "feed_paper", "print_test_page"):
            assert hass.services.has_service(DOMAIN, svc), f"Missing service: {svc}"

    async def test_print_text_calls_printer(self, hass: HomeAssistant, mock_p) -> None:
        """print_text service dispatches to printer."""
        entry = await _setup_entry(hass, mock_p)

        with patch(_PATCH_BLOCK_GET, return_value=mock_p):
            await hass.services.async_call(
                DOMAIN, "print_text",
                {"text": "Hello", "font_size": 24, "heat_density": 75,
                 "entry_id": entry.entry_id},
                blocking=True,
            )
        mock_p.print_text.assert_called_once()

    async def test_feed_paper_calls_printer(self, hass: HomeAssistant, mock_p) -> None:
        """feed_paper service dispatches to printer."""
        entry = await _setup_entry(hass, mock_p)

        with patch(_PATCH_BLOCK_GET, return_value=mock_p):
            await hass.services.async_call(
                DOMAIN, "feed_paper",
                {"lines": 50, "entry_id": entry.entry_id},
                blocking=True,
            )
        mock_p.feed.assert_called_once()

    async def test_print_test_page_calls_printer(self, hass: HomeAssistant, mock_p) -> None:
        """print_test_page service dispatches to printer."""
        entry = await _setup_entry(hass, mock_p)

        with patch(_PATCH_BLOCK_GET, return_value=mock_p):
            await hass.services.async_call(
                DOMAIN, "print_test_page",
                {"entry_id": entry.entry_id},
                blocking=True,
            )
        mock_p.print_test_page.assert_called_once()

    async def test_service_without_entry_id(self, hass: HomeAssistant, mock_p) -> None:
        """Service without entry_id falls back to first entry."""
        await _setup_entry(hass, mock_p)

        with patch(_PATCH_BLOCK_GET, return_value=mock_p):
            await hass.services.async_call(
                DOMAIN, "feed_paper", {"lines": 100}, blocking=True,
            )
        mock_p.feed.assert_called_once()

    async def test_get_status(self, hass: HomeAssistant, mock_p) -> None:
        """get_status service logs printer status."""
        entry = await _setup_entry(hass, mock_p)

        with patch(_PATCH_BLOCK_GET, return_value=mock_p):
            await hass.services.async_call(
                DOMAIN, "get_status", {"entry_id": entry.entry_id}, blocking=True,
            )


class TestCoordinator:
    async def test_coordinator_reads_all_keys(self, hass: HomeAssistant, mock_p) -> None:
        """Coordinator data contains all expected keys after refresh."""
        entry = await _setup_entry(hass, mock_p)

        coordinator = hass.data[DOMAIN][entry.entry_id]

        assert coordinator.data["available"] is True
        assert coordinator.data["battery"] == 80
        assert coordinator.data["status"] == "online"
        assert coordinator.data["version"] == "V1.0.11"

    async def test_unload_clears_config(self, hass: HomeAssistant, mock_p) -> None:
        """Unloading removes transport config and caches."""
        entry = await _setup_entry(hass, mock_p)

        import custom_components.paperang as mod

        with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
            result = await mod.async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in mod._transport_configs
        assert entry.entry_id not in mod._static_caches
        assert entry.entry_id not in mod._dynamic_caches

    async def test_diagnostics_returns_static_info(self, hass: HomeAssistant, mock_p) -> None:
        """async_get_config_entry_diagnostics returns static printer info."""
        entry = await _setup_entry(hass, mock_p)

        import custom_components.paperang as mod
        diag = await mod.async_get_config_entry_diagnostics(hass, entry)

        assert diag["board_version"] == "V1.0"
        assert diag["firmware_version"] == "V1.0.11"
        assert diag["model"] == "P2"
        assert diag["serial_number"] == "SN123"

    async def test_diagnostics_empty_without_coordinator(self, hass: HomeAssistant) -> None:
        """Diagnostics returns empty dict when no coordinator."""
        import custom_components.paperang as mod

        entry = MockConfigEntry(domain=DOMAIN, data={CONF_TRANSPORT: TRANSPORT_USB})
        entry.add_to_hass(hass)
        await mod.async_setup(hass, {})
        diag = await mod.async_get_config_entry_diagnostics(hass, entry)
        assert diag == {}


class TestVersionDecode:
    async def test_version_already_string_passed_through(self, hass: HomeAssistant, mock_p) -> None:
        """If version is already 'V1.0.11', it's passed through."""
        mock_p.get_version.return_value = "720897"
        entry = await _setup_entry(hass, mock_p)

        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data["version"] == "V1.0.11"

    async def test_version_readable_string_preserved(self, hass: HomeAssistant, mock_p) -> None:
        """If version is already '1.2.3', decode is skipped."""
        mock_p.get_version.return_value = "1.2.3"
        entry = await _setup_entry(hass, mock_p)

        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data["version"] == "1.2.3"
