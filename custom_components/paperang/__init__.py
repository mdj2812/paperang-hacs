"""Paperang P2 Printer integration for Home Assistant."""

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    SERVICE_PRINT_TEXT,
    SERVICE_PRINT_IMAGE,
    SERVICE_PRINT_QR,
    SERVICE_PRINT_PICKUP_CODE,
    ATTR_TEXT,
    ATTR_FONT_SIZE,
    ATTR_HEAT_DENSITY,
    ATTR_IMAGE_URL,
    ATTR_PROFILE,
    ATTR_QR_CONTENT,
    ATTR_QR_SIZE,
    ATTR_PICKUP_CODE,
)
from .printer import PaperangPrinter

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Paperang P2 Printer component."""

    printer = PaperangPrinter()

    async def handle_print_text(call: ServiceCall) -> None:
        """Handle print text service call."""
        text = call.data.get(ATTR_TEXT, "")
        font_size = call.data.get(ATTR_FONT_SIZE, 24)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)

        try:
            printer.connect()
            printer.print_text(text, font_size=font_size, heat_density=heat_density)
        finally:
            printer.disconnect()

    async def handle_print_image(call: ServiceCall) -> None:
        """Handle print image service call."""
        image_url = call.data.get(ATTR_IMAGE_URL, "")
        profile = call.data.get(ATTR_PROFILE)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)

        try:
            printer.connect()
            printer.print_image(image_url, profile=profile, heat_density=heat_density)
        finally:
            printer.disconnect()

    async def handle_print_qr(call: ServiceCall) -> None:
        """Handle print QR code service call."""
        qr_content = call.data.get(ATTR_QR_CONTENT, "")
        qr_size = call.data.get(ATTR_QR_SIZE, 500)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)

        try:
            printer.connect()
            printer.print_qr(qr_content, size=qr_size, heat_density=heat_density)
        finally:
            printer.disconnect()

    async def handle_print_pickup_code(call: ServiceCall) -> None:
        """Handle print pickup code service call."""
        pickup_code = call.data.get(ATTR_PICKUP_CODE, "")

        try:
            printer.connect()
            printer.print_pickup_code(pickup_code)
        finally:
            printer.disconnect()

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_PRINT_TEXT, handle_print_text)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_IMAGE, handle_print_image)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_QR, handle_print_qr)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_PICKUP_CODE, handle_print_pickup_code)

    _LOGGER.info("Paperang P2 Printer integration loaded")
    return True
