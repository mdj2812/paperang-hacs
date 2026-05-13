"""Constants for Paperang P2 Printer integration."""

DOMAIN = "paperang"

# Transport types
TRANSPORT_USB = "usb"
TRANSPORT_BLE = "ble"

# Config entry keys
CONF_TRANSPORT = "transport"
CONF_BLE_ADDRESS = "ble_address"

# Services
SERVICE_PRINT_TEXT = "print_text"
SERVICE_PRINT_IMAGE = "print_image"
SERVICE_PRINT_QR = "print_qr"
SERVICE_PRINT_PICKUP_CODE = "print_pickup_code"
SERVICE_GET_STATUS = "get_status"
SERVICE_FEED_PAPER = "feed_paper"
SERVICE_PRINT_TEST_PAGE = "print_test_page"

# Service attributes
ATTR_TEXT = "text"
ATTR_FONT_SIZE = "font_size"
ATTR_HEAT_DENSITY = "heat_density"
ATTR_IMAGE_URL = "image_url"
ATTR_PROFILE = "profile"
ATTR_QR_CONTENT = "qr_content"
ATTR_QR_SIZE = "qr_size"
ATTR_PICKUP_CODE = "pickup_code"
ATTR_LINES = "lines"

# Sensors
SENSOR_BATTERY = "battery"
SENSOR_STATUS = "status"
