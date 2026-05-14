"""Tests for paperang custom component constants."""


class TestConstants:
    def test_domain(self):
        from custom_components.paperang.const import DOMAIN

        assert DOMAIN == "paperang"

    def test_transport_types(self):
        from custom_components.paperang.const import (
            TRANSPORT_USB,
            TRANSPORT_BLE,
        )

        assert TRANSPORT_USB == "usb"
        assert TRANSPORT_BLE == "ble"

    def test_config_keys(self):
        from custom_components.paperang.const import (
            CONF_TRANSPORT,
            CONF_BLE_ADDRESS,
        )

        assert CONF_TRANSPORT == "transport"
        assert CONF_BLE_ADDRESS == "ble_address"

    def test_service_names(self):
        from custom_components.paperang.const import (
            SERVICE_PRINT_TEXT,
            SERVICE_PRINT_IMAGE,
            SERVICE_PRINT_QR,
            SERVICE_PRINT_PICKUP_CODE,
            SERVICE_PRINT_TEST_PAGE,
            SERVICE_GET_STATUS,
            SERVICE_FEED_PAPER,
        )

        assert SERVICE_PRINT_TEXT == "print_text"
        assert SERVICE_PRINT_IMAGE == "print_image"
        assert SERVICE_PRINT_QR == "print_qr"
        assert SERVICE_PRINT_PICKUP_CODE == "print_pickup_code"
        assert SERVICE_PRINT_TEST_PAGE == "print_test_page"
        assert SERVICE_GET_STATUS == "get_status"
        assert SERVICE_FEED_PAPER == "feed_paper"

    def test_attribute_names(self):
        from custom_components.paperang.const import (
            ATTR_TEXT,
            ATTR_FONT_SIZE,
            ATTR_HEAT_DENSITY,
            ATTR_IMAGE_URL,
            ATTR_PROFILE,
            ATTR_QR_CONTENT,
            ATTR_QR_SIZE,
            ATTR_PICKUP_CODE,
            ATTR_LINES,
        )

        assert ATTR_TEXT == "text"
        assert ATTR_FONT_SIZE == "font_size"
        assert ATTR_HEAT_DENSITY == "heat_density"
        assert ATTR_IMAGE_URL == "image_url"
        assert ATTR_PROFILE == "profile"
        assert ATTR_QR_CONTENT == "qr_content"
        assert ATTR_QR_SIZE == "qr_size"
        assert ATTR_PICKUP_CODE == "pickup_code"
        assert ATTR_LINES == "lines"

    def test_sensor_names(self):
        from custom_components.paperang.const import (
            SENSOR_BATTERY,
            SENSOR_STATUS,
        )

        assert SENSOR_BATTERY == "battery"
        assert SENSOR_STATUS == "status"
