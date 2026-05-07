# Changelog

## v1.0.0 (2026-05-08)

Initial release of the Paperang P2 Printer Home Assistant integration.

### Features

- **Text Printing**: Print text with configurable font size and heat density
- **Image Printing**: Print images with print profiles (portrait, landscape, document, high_contrast, light)
- **QR Code Printing**: Print QR codes with configurable size
- **Pickup Code Printing**: Print large pickup codes (96px bold) for package lockers

### Services

- `paperang.print_text` - Print text content
- `paperang.print_image` - Print an image
- `paperang.print_qr` - Print a QR code
- `paperang.print_pickup_code` - Print a large pickup code

### Technical

- Wraps the verified working `paperang_p2.py` core script
- USB direct connection (no MQTT required)
- Font support with local font files at `/config/paperang/`
