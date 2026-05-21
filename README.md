# Paperang P2 Printer - Home Assistant Integration

[![CI](https://github.com/mdj2812/paperang-hacs/actions/workflows/ci.yml/badge.svg)](https://github.com/mdj2812/paperang-hacs/actions/workflows/ci.yml)
[![coverage](https://raw.githubusercontent.com/mdj2812/paperang-hacs/badges/coverage.svg)](https://github.com/mdj2812/paperang-hacs/actions/workflows/ci.yml)

Control and monitor your Paperang P2 thermal printer through Home Assistant. Print text, images, QR codes, pickup codes — all from the device page with interactive controls, plus real-time printer telemetry via USB or Bluetooth BLE.

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mdj2812&repository=paperang-hacs&category=integration)

## Features

- 🔌 **USB auto-discovery** — printer detected automatically when plugged in
- 📡 **Bluetooth BLE** — auto-discovered or specify MAC address
- 🎛️ **Device page controls** — interactive print panel with mode selector, text input, parameter sliders, and print button
- 📊 **6 telemetry sensors** — battery, status, voltage, temperature, heat density, and Connection (diagnostic); static info (model, firmware, board, serial) shown on device card
- 🖨️ **7 services** — print text, images, QR codes, pickup codes, test page, get status, feed paper
- 📦 **Single device** — all entities grouped under one "Paperang P2 Printer" device
- ✅ **High coverage** — 109 tests, 85% coverage, pylint 10.00/10

## Installation

### Method 1: HACS (Recommended)

1. Add a custom repository in HACS:
   - HACS → Integrations → ⋮ → Custom repositories
   - Repository URL: `https://github.com/mdj2812/paperang-hacs`
   - Category: `Integration`
   - Install `Paperang P2 Printer`

### Method 2: Manual Installation

```bash
git clone https://github.com/mdj2812/paperang-hacs.git
cp -r paperang-hacs/custom_components/paperang /config/custom_components/paperang
```

Restart Home Assistant after installation.

## Setup

### USB Auto-Discovery

Plug in your Paperang P2 via USB. Home Assistant will detect it automatically and show a notification — click to confirm and the integration is ready.

### Bluetooth BLE Setup

**Settings → Devices & Services** — if your Paperang P2 is powered on and within BLE range, HA will auto-discover it and show a notification.

Or add manually: **Settings → Devices & Services → Add Integration → Search "Paperang P2 Printer"** — choose **Bluetooth BLE** and enter the MAC address (e.g. `00:15:83:EB:05:17`).

### Manual Setup

**Settings → Devices & Services → Add Integration → Search "Paperang P2 Printer"** — choose **USB** or **Bluetooth BLE**.

### YAML Import

If you prefer configuration via `configuration.yaml`, add:

```yaml
paperang:
```

On restart, HA will automatically import this as a config entry.

## Prerequisites

**USB:** Paperang P2 printer connected via USB to the HA host. USB device must be passed through to the HA VM (if running in a VM).

**BLE:** Bluetooth adapter on the HA host. Printer must be powered on and within range. Works with both `Paperang` and `MiaoMiaoJi` (喵喵机) branded devices.

> 📦 Requires `paperang-p2-lib>=0.4.0rc1` (installed automatically by HA).

## Device Controls

The device page provides an interactive print panel:

| Entity | Type | Description |
|--------|------|-------------|
| Print Mode | select | text / image / qr / pickup_code |
| Print Content | text | Enter text, URL, QR data, or pickup code |
| Font Size | number (12–96) | Text print font size |
| Heat Density | number (0–100%) | Print darkness |
| QR Size | number (100–576px) | QR code dimensions |
| Image Profile | select | portrait / landscape / document / high_contrast / light |
| Feed Lines | number (10–500) | Lines to feed |

| Button | Action |
|--------|--------|
| Print | Reads all current settings and prints accordingly |
| Feed Paper | Advances paper by Feed Lines |
| Test Print | Prints a test page |

## Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| Battery | Battery level | % |
| Status | Printer status code | — |
| Voltage | Battery voltage | mV |
| Temperature | Printer head temperature | °C |
| Heat Density | Current heat density setting | % |
| Connection | Connection status (diagnostic) | — |

> ℹ️ Static info (model, firmware version, board version, serial number) is shown on the device card, not as separate sensors.

## Services

### paperang.print_text

Print text content.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | string | — | Text to print |
| font_size | number | 24 | Font size in pixels (12–96) |
| heat_density | number | 75 | Print heat density (0–100) |

### paperang.print_image

Print an image from a local file path or remote URL.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| image_url | string | — | Image URL or local file path |
| profile | select | document | portrait / landscape / document / high_contrast / light |
| heat_density | number | 75 | Print heat density (0–100) |

### paperang.print_qr

Print a QR code.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| qr_content | string | — | Content to encode in the QR code |
| qr_size | number | 500 | QR code size in pixels (100–576) |
| heat_density | number | 75 | Print heat density (0–100) |

### paperang.print_pickup_code

Print large pickup codes (e.g., for package lockers).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| pickup_code | string | — | Pickup code, e.g. "19-4308" |

### paperang.print_test_page

Print a built-in test page (no parameters).

### paperang.get_status

Query current battery and status. Results logged at INFO level.

### paperang.feed_paper

Feed paper by the given number of lines.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| lines | number | 100 | Number of lines to feed |

## Automation Examples

### Auto-print Pickup Code on Package Arrival

```yaml
automation:
  - alias: "Print Pickup Code"
    trigger:
      platform: state
      entity_id: sensor.package_arrived
    action:
      - service: paperang.print_pickup_code
        data:
          pickup_code: "{{ states('input_text.pickup_code') }}"
```

### Daily Weather Print

```yaml
automation:
  - alias: "Daily Weather Print"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: paperang.print_text
        data:
          text: >
            Today: {{ states('weather.home') }}
            Temp: {{ states('sensor.home_temperature') }}°C
          font_size: 18
          heat_density: 60
```

### Low Battery Alert

```yaml
automation:
  - alias: "Low Battery Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.paperang_p2_battery
        below: 20
    action:
      - service: paperang.print_text
        data:
          text: >
            ⚠️ Printer battery low!
            {{ states('sensor.paperang_p2_battery') }}%
          font_size: 24
```

### Print on Printer Available

```yaml
automation:
  - alias: "Print Test on Reconnect"
    trigger:
      - platform: state
        entity_id: sensor.paperang_p2_status
        from: "unavailable"
    action:
      - service: paperang.print_text
        data:
          text: "🟢 Paperang P2 online"
          font_size: 24
          heat_density: 50
```

## License

MIT License — Copyright (c) 2026 Martin Ma
