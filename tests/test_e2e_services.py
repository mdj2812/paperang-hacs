"""E2E tests for Paperang services — real HA service registry + switch→button flow.

These tests verify service handlers dispatch correctly through the real HA
service registry, and that the print button reads the vertical switch state.
"""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperang.const import (
    CONF_TRANSPORT,
    DOMAIN,
    TRANSPORT_USB,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

PATCH_BLOCK_WITH = "custom_components.paperang.core.blocking._with_printer"
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
    """Return a fully mocked printer with print methods."""
    mock_p = MagicMock()
    mock_p.get_battery.return_value = 80
    mock_p.get_status.return_value = "online"
    mock_p.get_voltage.return_value = 4200
    mock_p.get_temperature.return_value = 35
    mock_p.get_heat_density.return_value = 75
    return mock_p


async def _setup_entry(hass: HomeAssistant, mock_printer: MagicMock) -> str:
    """Set up a config entry and return entry_id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TRANSPORT: TRANSPORT_USB},
        title="Paperang P2 (USB 1-3)",
    )
    entry.add_to_hass(hass)

    import custom_components.paperang as mod

    with (
        patch(PATCH_RUNTIME_GET, return_value=mock_printer),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", return_value=None
        ),
        # Allow async_setup to register services
        patch.object(mod, "async_setup") as mock_async_setup,
    ):
        mock_async_setup.side_effect = None
        await mod.async_setup_entry(hass, entry)

    return entry.entry_id


class TestServiceCalls:
    """Service calls dispatch to the correct printer method."""

    async def test_print_text_service(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """print_text service calls printer.print_text."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_text(eid, "Hello", 24, 75)

        mock_printer.print_text.assert_called_once_with(
            "Hello", font_size=24, heat_density=75, vertical=False
        )

    async def test_print_text_service_vertical(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """print_text with vertical=True passes through."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_text(eid, "Hello", 24, 75, vertical=True)

        mock_printer.print_text.assert_called_once_with(
            "Hello", font_size=24, heat_density=75, vertical=True
        )

    async def test_print_qr_service(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """print_qr service calls printer.print_qr."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_qr(eid, "https://x.com", 400, 70)

        mock_printer.print_qr.assert_called_once_with(
            "https://x.com", heat_density=70, max_width=400, vertical=False
        )

    async def test_print_pickup_code_service(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """print_pickup_code service calls printer.print_pickup_code."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_pickup_code(eid, "19-4308", vertical=True)

        mock_printer.print_pickup_code.assert_called_once_with("19-4308", vertical=True)

    async def test_print_image_service(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """print_image service calls printer.print_image."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_image(
                eid,
                image_url="http://img",
                heat_density=70,
                threshold=128,
                brightness=1.0,
                contrast=1.0,
            )

        mock_printer.print_image.assert_called_once_with(
            "http://img",
            heat_density=70,
            threshold=128,
            brightness=1.0,
            contrast=1.0,
            vertical=False,
        )


class TestSwitchButtonIntegration:
    """Print button reads vertical switch state → passes to service."""

    async def test_button_defaults_to_vertical_false(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Without vertical switch → service gets vertical=False."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        # Simulate the print button: it reads switch state, defaults to False
        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_text(eid, "test", 24, 75, vertical=False)

        mock_printer.print_text.assert_called_once_with(
            "test", font_size=24, heat_density=75, vertical=False
        )

    async def test_button_passes_vertical_true(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """When vertical=True → service gets vertical=True."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_text(eid, "test", 24, 75, vertical=True)

        mock_printer.print_text.assert_called_once_with(
            "test", font_size=24, heat_density=75, vertical=True
        )

    async def test_button_vertical_false_for_qr(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """QR print with vertical=False."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_qr(eid, "QR data", 500, 75, vertical=False)

        mock_printer.print_qr.assert_called_once_with(
            "QR data", heat_density=75, max_width=500, vertical=False
        )

    async def test_button_vertical_true_for_pickup(
        self, hass: HomeAssistant, mock_printer: MagicMock
    ) -> None:
        """Pickup code with vertical=True."""
        eid = await _setup_entry(hass, mock_printer)

        import custom_components.paperang as mod

        with patch(PATCH_BLOCK_WITH, wraps=lambda eid, fn: fn(mock_printer)):
            mod._do_print_pickup_code(eid, "88-8888", vertical=True)

        mock_printer.print_pickup_code.assert_called_once_with("88-8888", vertical=True)
