"""Constants for Paperang P2 Printer integration."""

DOMAIN = "paperang"

# USB IDs
VENDOR_ID = 0x4348
PRODUCT_ID = 0x5584

# Services
SERVICE_PRINT_TEXT = "print_text"
SERVICE_PRINT_IMAGE = "print_image"
SERVICE_PRINT_QR = "print_qr"
SERVICE_PRINT_PICKUP_CODE = "print_pickup_code"

# Service attributes
ATTR_TEXT = "text"
ATTR_FONT_SIZE = "font_size"
ATTR_HEAT_DENSITY = "heat_density"
ATTR_IMAGE_URL = "image_url"
ATTR_PROFILE = "profile"
ATTR_QR_CONTENT = "qr_content"
ATTR_QR_SIZE = "qr_size"
ATTR_PICKUP_CODE = "pickup_code"
