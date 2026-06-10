"""E2E tests for Paperang entities — real HA Core entity creation + state transitions.

These tests verify that all entity platforms create their entities correctly
and that state transitions work as expected. Only the transport layer is mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
def _clear_caches() -> None:
    """Clear persistent caches between tests."""
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
    mock_p.get_version.return_value = "720897"
    mock_p.get_model.return_value = "P2"
    mock_p.get_sn.return_value = "SN123"
    mock_p.get_board_version.return_value = "V1.0"
    mock_p.get_hw_info.return_value = "ABC"
    return mock_p


async def _setup_entry(hass: HomeAssistant, mock_printer: MagicMock) -> MockConfigEntry:
    """Create config entry and set it up — entities created for real."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TRANSPORT: TRANSPORT_USB},
        title="Paperang P2 (USB 1-3)",
    )
    entry.add_to_hass(hass)

    import custom_components.paperang as mod

    with (
        patch(PATCH_RUNTIME_GET, return_value=mock_printer),
        patch.object(mod, "async_setup", return_value=True),
    ):
        # Let async_forward_entry_setups run — entities get created
        await mod.async_setup_entry(hass, entry)

    return entry


class TestSensorEntities:
    """Verify sensor entities are created."""

    async def test_sensors_created(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """All 6 sensor entities appear after setup."""
        entry = await _setup_entry(hass, mock_printer)
        registry = er.async_get(hass)
        eid = entry.entry_id
        expected = [
            "battery",
            "status",
            "voltage",
            "temperature",
            "heat_density",
            "connection",
        ]
        for suffix in expected:
            uid = f"paperang_{eid}_{suffix}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, uid)
            assert entity_id is not None, f"sensor.{suffix} ({uid}) not found"


class TestSelectEntities:
    """Verify select entities exist."""

    async def test_select_entities_created(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Print mode and image profile selects appear."""
        entry = await _setup_entry(hass, mock_printer)
        registry = er.async_get(hass)
        eid = entry.entry_id
        for suffix in ("print_mode", "image_profile"):
            uid = f"paperang_{eid}_{suffix}"
            entity_id = registry.async_get_entity_id("select", DOMAIN, uid)
            assert entity_id is not None, f"select.{suffix} not found"


class TestNumberEntities:
    """Verify number entities exist."""

    async def test_number_entities_created(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """All 4 number entities appear."""
        entry = await _setup_entry(hass, mock_printer)
        registry = er.async_get(hass)
        eid = entry.entry_id
        for suffix in ("font_size", "heat_density", "qr_size", "feed_lines"):
            uid = f"paperang_{eid}_{suffix}"
            entity_id = registry.async_get_entity_id("number", DOMAIN, uid)
            assert entity_id is not None, f"number.{suffix} not found"


class TestButtonEntities:
    """Verify button entities exist."""

    async def test_buttons_created(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """All 3 button entities appear."""
        entry = await _setup_entry(hass, mock_printer)
        registry = er.async_get(hass)
        eid = entry.entry_id
        for suffix in ("btn_print", "btn_feed_paper", "btn_test_print"):
            uid = f"paperang_{eid}_{suffix}"
            entity_id = registry.async_get_entity_id("button", DOMAIN, uid)
            assert entity_id is not None, f"button.{suffix} not found"


class TestTextEntity:
    """Verify text entity exists."""

    async def test_text_entity_created(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Print content text entity appears."""
        entry = await _setup_entry(hass, mock_printer)
        registry = er.async_get(hass)
        eid = entry.entry_id
        uid = f"paperang_{eid}_print_content"
        entity_id = registry.async_get_entity_id("text", DOMAIN, uid)
        assert entity_id is not None


class TestSwitchEntity:
    """Verify vertical switch entity exists."""

    async def test_vertical_switch_created(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Vertical switch entity appears after setup."""
        entry = await _setup_entry(hass, mock_printer)
        registry = er.async_get(hass)
        eid = entry.entry_id
        uid = f"paperang_{eid}_vertical"
        entity_id = registry.async_get_entity_id("switch", DOMAIN, uid)
        assert entity_id is not None


class TestEntityCleanup:
    """Verify entities are removed on unload."""

    async def test_unload_removes_entry(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Entry removed from hass.data after unload."""
        entry = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_RUNTIME_GET, return_value=mock_printer):
            result = await mod.async_unload_entry(hass, entry)

        assert result is True
        assert entry.entry_id not in hass.data.get(DOMAIN, {})


class TestBTEntryPollingInterval:
    """BT entry uses 30s poll interval."""

    async def test_bt_entry_30s_poll(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """BT transport → 30s interval."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_TRANSPORT: TRANSPORT_BT},
            title="Paperang P2 (BT)",
        )
        entry.add_to_hass(hass)

        import custom_components.paperang as mod

        with (
            patch(PATCH_RUNTIME_GET, return_value=mock_printer),
            patch.object(mod, "async_setup", return_value=True),
        ):
            await mod.async_setup_entry(hass, entry)

        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.update_interval.seconds == 30
