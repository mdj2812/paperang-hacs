# Paperang P2 Printer - Home Assistant Integration

Control your Paperang P2 thermal printer through Home Assistant. Supports printing text, images, QR codes, and pickup codes.

## Installation

### Method 1: HACS (Recommended)

1. Add a custom repository in HACS:
   - HACS → Integrations → ⋮ → Custom repositories
   - Repository URL: `https://github.com/mdj2812/paperang-hacs.git`
   - Category: `Integration`
   - Install `Paperang P2 Printer`

### Method 2: Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mdj2812/paperang-hacs.git
   ```
2. Copy `custom_components/paperang` to HA's `/config/custom_components/paperang/`
3. Install the pip dependency:
   ```bash
   pip install paperang-p2-lib[qr,cjk]>=0.2.0
   ```
4. Restart Home Assistant

## Prerequisites

- Paperang P2 printer connected via USB to the HA host
- USB device passed through to the HA VM (if running in a VM)

## Services

### paperang.print_text

Print text content.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| text | string | - | Text to print |
| font_size | number | 24 | Font size in pixels (12-96) |
| heat_density | number | 75 | Print heat density (0-100) |

### paperang.print_pickup_code

Print large pickup codes (e.g., for package lockers).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| pickup_code | string | - | Pickup code, e.g. "19-4308" |

### paperang.print_qr

Print a QR code.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| qr_content | string | - | Content to encode in the QR code |
| qr_size | number | 500 | QR code size in pixels (100-576) |
| heat_density | number | 75 | Print heat density (0-100) |

### paperang.print_image

Print an image.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| image_url | string | - | Image URL or local file path |
| profile | select | document | Print profile: portrait/landscape/document/high_contrast/light |
| heat_density | number | 75 | Print heat density (0-100) |

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

### Doorbell Notification Print

```yaml
automation:
  - alias: "Doorbell Notification Print"
    trigger:
      platform: state
      entity_id: binary_sensor.doorbell
      to: "on"
    action:
      - service: paperang.print_text
        data:
          text: "Someone at the door!"
          font_size: 32
          heat_density: 80
```

## License

MIT License - Copyright (c) 2026 Martin Ma
