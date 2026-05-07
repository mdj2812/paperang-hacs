"""Paperang P2 Printer driver for Home Assistant."""

import logging
import os
import struct
import zlib
import urllib.request

import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont
import qrcode

from .const import VENDOR_ID, PRODUCT_ID

_LOGGER = logging.getLogger(__name__)

# Print parameters
PRINT_WIDTH = 576  # pixels
LINE_BYTES = 72    # bytes per line
MAX_PACKET_DATA = 1023
CRC_SEED = 0x35769521 & 0xFFFFFFFF

# Print profiles
PRINT_PROFILES = {
    "portrait": {"threshold": 180, "brightness": 1.5, "contrast": 0.6, "heat_density": 55},
    "landscape": {"threshold": 150, "brightness": 1.1, "contrast": 0.8, "heat_density": 70},
    "document": {"threshold": 128, "brightness": 1.0, "contrast": 1.0, "heat_density": 75},
    "high_contrast": {"threshold": 100, "brightness": 1.0, "contrast": 1.2, "heat_density": 85},
    "light": {"threshold": 200, "brightness": 1.3, "contrast": 0.5, "heat_density": 45},
}


def crc32_paperang(data, seed=CRC_SEED):
    """Paperang-specific CRC32 calculation."""
    crc = zlib.crc32(data, seed) & 0xFFFFFFFF
    if crc > 2147483647:
        crc = crc - 4294967296
    return crc


def pack_packet(cmd, data=b'', packet_remain=0):
    """Pack Paperang protocol packet."""
    crc = crc32_paperang(data)
    packet = bytearray()
    packet.append(0x02)
    packet.append(cmd & 0xFF)
    packet.append(packet_remain & 0xFF)
    packet.extend(struct.pack('<H', len(data)))
    packet.extend(data)
    packet.extend(struct.pack('<i', crc))
    packet.append(0x03)
    return bytes(packet)


class PaperangPrinter:
    """Paperang P2 Printer driver."""

    def __init__(self):
        self.dev = None
        self.out_ep = None
        self.in_ep = None
        self._connected = False

    def connect(self):
        """Connect to Paperang P2 printer."""
        try:
            self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
            if self.dev is None:
                raise ConnectionError("Paperang P2 printer not found (USB IDs: 4348:5584)")

            # Detach kernel driver if active
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
                _LOGGER.info("Detached kernel driver from Paperang printer")

            self.dev.set_configuration()
            cfg = self.dev.get_active_configuration()
            intf = cfg[(0, 0)]

            self.out_ep = usb.util.find_descriptor(
                intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            self.in_ep = usb.util.find_descriptor(
                intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )

            if self.out_ep is None:
                raise ConnectionError("Could not find OUT endpoint")
            if self.in_ep is None:
                raise ConnectionError("Could not find IN endpoint")

            self._connected = True
            _LOGGER.info("Paperang P2 printer connected")
        except Exception as e:
            _LOGGER.error("Failed to connect to Paperang printer: %s", e)
            raise

    def disconnect(self):
        """Disconnect from printer."""
        if self.dev:
            try:
                usb.util.dispose_resources(self.dev)
            except Exception:
                pass
            self._connected = False
            _LOGGER.info("Paperang P2 printer disconnected")

    def _send_command(self, cmd, data=b''):
        """Send a command packet to the printer."""
        if not self._connected:
            raise ConnectionError("Printer not connected")
        packet = pack_packet(cmd, data)
        self.out_ep.write(packet, timeout=5000)

    def _read_response(self, length=64):
        """Read a response from the printer."""
        if not self._connected:
            raise ConnectionError("Printer not connected")
        try:
            return bytes(self.in_ep.read(length, timeout=5000))
        except Exception as e:
            _LOGGER.warning("Failed to read from printer: %s", e)
            return b''

    def print_text(self, text, font_size=24, heat_density=75):
        """Print text content."""
        _LOGGER.info("Printing text: %s (font_size=%d, heat_density=%d)", text[:50], font_size, heat_density)

        try:
            # Set print density
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            # Calculate bitmap dimensions
            img = Image.new('1', (PRINT_WIDTH, 1), 1)
            draw = ImageDraw.Draw(img)

            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()

            # Calculate text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Create image with text
            img = Image.new('1', (PRINT_WIDTH, text_height + 4), 1)
            draw = ImageDraw.Draw(img)
            draw.text((max(0, (PRINT_WIDTH - text_width) // 2), 2), text, fill=0, font=font)

            # Convert to bitmap rows and print
            self._send_bitmap(img)

            # Feed paper
            self._send_command(0x20, bytes([100]))
            self._read_response()

        except Exception as e:
            _LOGGER.error("Failed to print text: %s", e)
            raise

    def print_image(self, image_path, profile=None, heat_density=75, threshold=128, brightness=1.0, contrast=1.0):
        """Print an image."""
        _LOGGER.info("Printing image: %s", image_path)

        try:
            if profile and profile in PRINT_PROFILES:
                p = PRINT_PROFILES[profile]
                threshold = p["threshold"]
                brightness = p["brightness"]
                contrast = p["contrast"]
                heat_density = p["heat_density"]

            # Set print density
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            # Load and process image
            if image_path.startswith("http"):
                tmp_path = "/tmp/paperang_image.jpg"
                urllib.request.urlretrieve(image_path, tmp_path)
                image_path = tmp_path

            img = Image.open(image_path).convert('L')
            img = img.resize((PRINT_WIDTH, int(img.height * PRINT_WIDTH / img.width)), Image.Resampling.LANCZOS)

            # Apply adjustments
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)

            # Convert to 1-bit bitmap
            img = img.point(lambda p: 0 if p < threshold else 1).convert('1')

            # Print bitmap
            self._send_bitmap(img)

            # Feed paper
            self._send_command(0x20, bytes([100]))
            self._read_response()

        except Exception as e:
            _LOGGER.error("Failed to print image: %s", e)
            raise

    def print_qr(self, content, size=500, heat_density=75):
        """Print a QR code."""
        _LOGGER.info("Printing QR code: %s", content[:50])

        try:
            # Set print density
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            # Generate QR code
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
            qr.add_data(content)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert('1')
            img = img.resize((min(size, PRINT_WIDTH), min(size, PRINT_WIDTH)), Image.Resampling.NEAREST)

            # Center on paper
            final_img = Image.new('1', (PRINT_WIDTH, img.height + 20), 1)
            x_offset = (PRINT_WIDTH - img.width) // 2
            final_img.paste(img, (x_offset, 10))

            # Print bitmap
            self._send_bitmap(final_img)

            # Feed paper
            self._send_command(0x20, bytes([100]))
            self._read_response()

        except Exception as e:
            _LOGGER.error("Failed to print QR code: %s", e)
            raise

    def print_pickup_code(self, code, heat_density=85):
        """Print a large pickup code (e.g., '19-4308')."""
        _LOGGER.info("Printing pickup code: %s", code)

        try:
            # Set max print density for clarity
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            # Create large text image
            font_size = 96
            try:
                font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except Exception:
                    font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans.ttf", font_size)

            # Calculate size
            img = Image.new('1', (PRINT_WIDTH, 1), 1)
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), code, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Create centered image
            final_img = Image.new('1', (PRINT_WIDTH, text_height + 20), 1)
            draw = ImageDraw.Draw(final_img)
            x = max(0, (PRINT_WIDTH - text_width) // 2)
            draw.text((x, 10), code, fill=0, font=font)

            # Print bitmap
            self._send_bitmap(final_img)

            # Feed paper
            self._send_command(0x20, bytes([100]))
            self._read_response()

        except Exception as e:
            _LOGGER.error("Failed to print pickup code: %s", e)
            raise

    def _send_bitmap(self, img):
        """Send a 1-bit bitmap to the printer."""
        if img.mode != '1':
            img = img.convert('1')

        width, height = img.size
        rows = height
        total_packets = rows  # Each row is one packet
        remaining = total_packets - 1

        pixels = img.load()
        for y in range(rows):
            row_data = bytearray()
            for byte_idx in range(LINE_BYTES):
                byte_val = 0
                for bit in range(8):
                    x = byte_idx * 8 + bit
                    if x < width and pixels[x, y] == 0:  # 0 = black (print)
                        byte_val |= (1 << (7 - bit))
                row_data.append(byte_val)

            self._send_command(0x28, bytes(row_data), remaining)
            remaining -= 1

        _LOGGER.info("Bitmap sent: %d rows", rows)

    def get_status(self):
        """Get printer status."""
        try:
            self._send_command(0x10)
            response = self._read_response(8)
            return {"status": list(response)}
        except Exception as e:
            _LOGGER.error("Failed to get status: %s", e)
            return {"error": str(e)}

    def get_battery(self):
        """Get battery level."""
        try:
            self._send_command(0x30)
            response = self._read_response(8)
            if len(response) >= 3:
                return {"battery": response[2]}
            return {"error": "Invalid response"}
        except Exception as e:
            _LOGGER.error("Failed to get battery level: %s", e)
            return {"error": str(e)}
