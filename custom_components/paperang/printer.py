"""Paperang P2 Printer driver for Home Assistant."""

import logging
import os
import struct
import zlib

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

# Font search paths - NotoSans (HA compatible)
_FONT_CANDIDATES = [
    "/config/paperang/DejaVuSans.ttf",
    "/config/paperang/NotoSans-Regular.ttf",
    "/usr/share/fonts/TTF/NotoSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]
_BOLD_FONT_CANDIDATES = [
    "/config/paperang/DejaVuSans-Bold.ttf",
    "/config/paperang/NotoSans-Bold.ttf",
    "/usr/share/fonts/TTF/NotoSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]


def _find_font(size, bold=False):
    """Find a usable font."""
    candidates = _BOLD_FONT_CANDIDATES if bold else _FONT_CANDIDATES
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return None


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

    def _send_command(self, cmd, data=b'', packet_remain=0):
        """Send a command packet to the printer."""
        if not self._connected:
            raise ConnectionError("Printer not connected")
        packet = pack_packet(cmd, data, packet_remain)
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

    def _render_text_bitmap(self, text, font_size=24):
        """Render text to a 1-bit bitmap image."""
        font = _find_font(font_size)

        if font is None:
            _LOGGER.warning("No TrueType font available, printing test pattern")
            height = max(font_size, 32)
            img = Image.new('1', (PRINT_WIDTH, height + 8), 1)
            draw = ImageDraw.Draw(img)
            for i in range(0, PRINT_WIDTH, 16):
                draw.line([(i, 4), (i, height)], fill=0)
            for y in range(0, height, 16):
                draw.line([(0, y), (PRINT_WIDTH, y)], fill=0)
            return img

        temp = Image.new('1', (1, 1))
        bbox = ImageDraw.Draw(temp).textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        if th < 4:
            th = font_size
        if tw < 4:
            tw = len(text) * font_size // 2

        img = Image.new('1', (PRINT_WIDTH, th + 8), 1)
        draw = ImageDraw.Draw(img)
        x = max(0, (PRINT_WIDTH - tw) // 2)
        draw.text((x, 4), text, fill=0, font=font)
        return img

    def print_text(self, text, font_size=24, heat_density=75):
        """Print text content."""
        _LOGGER.info("Printing text: %s (font_size=%d, heat_density=%d)", text[:50], font_size, heat_density)

        try:
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            img = self._render_text_bitmap(text, font_size)

            black_pixels = sum(1 for y in range(img.height) for x in range(img.width) if img.getpixel((x, y)) == 0)
            _LOGGER.info("Bitmap: %dx%d, %d black pixels", img.width, img.height, black_pixels)

            self._send_bitmap(img)

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

            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            if image_path.startswith("http"):
                tmp_path = "/tmp/paperang_image.jpg"
                import urllib.request
                urllib.request.urlretrieve(image_path, tmp_path)
                image_path = tmp_path

            img = Image.open(image_path).convert('L')
            img = img.resize((PRINT_WIDTH, int(img.height * PRINT_WIDTH / img.width)), Image.Resampling.LANCZOS)

            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)

            img = img.point(lambda p: 0 if p < threshold else 1).convert('1')
            self._send_bitmap(img)

            self._send_command(0x20, bytes([100]))
            self._read_response()

        except Exception as e:
            _LOGGER.error("Failed to print image: %s", e)
            raise

    def print_qr(self, content, size=500, heat_density=75):
        """Print a QR code."""
        _LOGGER.info("Printing QR code: %s", content[:50])

        try:
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
            qr.add_data(content)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert('1')
            img = img.resize((min(size, PRINT_WIDTH), min(size, PRINT_WIDTH)), Image.Resampling.NEAREST)

            final_img = Image.new('1', (PRINT_WIDTH, img.height + 20), 1)
            x_offset = (PRINT_WIDTH - img.width) // 2
            final_img.paste(img, (x_offset, 10))

            self._send_bitmap(final_img)

            self._send_command(0x20, bytes([100]))
            self._read_response()

        except Exception as e:
            _LOGGER.error("Failed to print QR code: %s", e)
            raise

    def print_pickup_code(self, code, heat_density=85):
        """Print a large pickup code (e.g., '19-4308')."""
        _LOGGER.info("Printing pickup code: %s", code)

        try:
            self._send_command(0x1A, bytes([heat_density]))
            self._read_response()

            font_size = 96
            font = _find_font(font_size, bold=True)

            if font is None:
                _LOGGER.warning("No bold font for pickup code, printing test pattern")
                img = Image.new('1', (PRINT_WIDTH, 100), 1)
                draw = ImageDraw.Draw(img)
                for x in range(10, PRINT_WIDTH - 10, 20):
                    draw.rectangle([(x, 10), (x + 12, 90)], fill=0)
            else:
                temp = Image.new('1', (1, 1))
                bbox = ImageDraw.Draw(temp).textbbox((0, 0), code, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                if th < 4:
                    th = font_size

                img = Image.new('1', (PRINT_WIDTH, th + 20), 1)
                draw = ImageDraw.Draw(img)
                x = max(0, (PRINT_WIDTH - tw) // 2)
                draw.text((x, 10), code, fill=0, font=font)

            self._send_bitmap(img)

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
        remaining = height - 1

        pixels = img.load()
        for y in range(height):
            row_data = bytearray()
            for byte_idx in range(LINE_BYTES):
                byte_val = 0
                for bit in range(8):
                    x = byte_idx * 8 + bit
                    if x < width and pixels[x, y] == 0:
                        byte_val |= (1 << (7 - bit))
                row_data.append(byte_val)
            self._send_command(0x28, bytes(row_data), remaining)
            remaining -= 1

        _LOGGER.info("Bitmap sent: %d rows", height)

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
