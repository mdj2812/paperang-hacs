"""Home Assistant service registration and handlers for Paperang."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from ..const import (
    ATTR_FONT_SIZE,
    ATTR_HEAT_DENSITY,
    ATTR_IMAGE_URL,
    ATTR_LINES,
    ATTR_PICKUP_CODE,
    ATTR_PROFILE,
    ATTR_QR_CONTENT,
    ATTR_QR_SIZE,
    ATTR_TEXT,
    DOMAIN,
    SERVICE_FEED_PAPER,
    SERVICE_GET_STATUS,
    SERVICE_PRINT_IMAGE,
    SERVICE_PRINT_PICKUP_CODE,
    SERVICE_PRINT_QR,
    SERVICE_PRINT_TEST_PAGE,
    SERVICE_PRINT_TEXT,
)
from ..core.blocking import (
    _do_feed_paper,
    _do_get_status,
    _do_print_image,
    _do_print_pickup_code,
    _do_print_qr,
    _do_print_test_page,
    _do_print_text,
)
from ..core.paperang_lib import load_profiles
from ..core.runtime import transport_configs

_LOGGER = logging.getLogger(__name__)


def _get_entry_id_from_call(call: ServiceCall) -> str:
    """Resolve entry_id from a service call."""
    explicit = call.data.get("entry_id")
    if explicit and explicit in transport_configs:
        return explicit
    if transport_configs:
        return next(iter(transport_configs))
    return ""


def async_setup_services(hass: HomeAssistant, config: ConfigType) -> None:
    # pylint: disable=too-many-statements
    """Register Paperang domain services."""

    async def handle_print_text(call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(call)
        if not entry_id:
            return
        text = call.data.get(ATTR_TEXT, "")
        font_size = call.data.get(ATTR_FONT_SIZE, 24)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)
        await hass.async_add_executor_job(
            _do_print_text, entry_id, text, font_size, heat_density
        )

    async def handle_print_image(call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(call)
        if not entry_id:
            return
        image_url = call.data.get(ATTR_IMAGE_URL, "")
        profile = call.data.get(ATTR_PROFILE)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)

        profiles = await hass.async_add_executor_job(load_profiles)
        profile_settings = profiles.get(profile, {}) if profile else {}

        threshold = profile_settings.get("threshold", 128)
        brightness = profile_settings.get("brightness", 1.0)
        contrast = profile_settings.get("contrast", 1.0)
        if "heat_density" in profile_settings:
            heat_density = profile_settings["heat_density"]

        await hass.async_add_executor_job(
            _do_print_image,
            entry_id,
            image_url=image_url,
            heat_density=heat_density,
            threshold=threshold,
            brightness=brightness,
            contrast=contrast,
        )

    async def handle_print_qr(call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(call)
        if not entry_id:
            return
        qr_content = call.data.get(ATTR_QR_CONTENT, "")
        qr_size = call.data.get(ATTR_QR_SIZE, 500)
        heat_density = call.data.get(ATTR_HEAT_DENSITY, 75)
        await hass.async_add_executor_job(
            _do_print_qr, entry_id, qr_content, qr_size, heat_density
        )

    async def handle_print_pickup_code(call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(call)
        if not entry_id:
            return
        pickup_code = call.data.get(ATTR_PICKUP_CODE, "")
        await hass.async_add_executor_job(_do_print_pickup_code, entry_id, pickup_code)

    async def handle_get_status(_call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(_call)
        if not entry_id:
            return
        result = await hass.async_add_executor_job(_do_get_status, entry_id)
        _LOGGER.info("Paperang P2 status: %s", result)

    async def handle_feed_paper(call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(call)
        if not entry_id:
            return
        lines = call.data.get(ATTR_LINES, 100)
        await hass.async_add_executor_job(_do_feed_paper, entry_id, lines)

    async def handle_print_test_page(_call: ServiceCall) -> None:
        entry_id = _get_entry_id_from_call(_call)
        if not entry_id:
            return
        await hass.async_add_executor_job(_do_print_test_page, entry_id)

    hass.services.async_register(DOMAIN, SERVICE_PRINT_TEXT, handle_print_text)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_IMAGE, handle_print_image)
    hass.services.async_register(DOMAIN, SERVICE_PRINT_QR, handle_print_qr)
    hass.services.async_register(
        DOMAIN, SERVICE_PRINT_PICKUP_CODE, handle_print_pickup_code
    )
    hass.services.async_register(DOMAIN, SERVICE_GET_STATUS, handle_get_status)
    hass.services.async_register(DOMAIN, SERVICE_FEED_PAPER, handle_feed_paper)
    hass.services.async_register(
        DOMAIN, SERVICE_PRINT_TEST_PAGE, handle_print_test_page
    )

    _LOGGER.info("Paperang P2 Printer integration loaded")

    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=config[DOMAIN],
            )
        )
