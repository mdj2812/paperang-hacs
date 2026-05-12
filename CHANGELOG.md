# Changelog

## v1.3.1 (2026-05-12)

### Added
- Device controls: Print button, Print Mode selector (text/image/qr/pickup_code),
  Image Profile selector, Print Content text input
- Configurable parameters: Font Size (12–96), Heat Density (0–100%),
  QR Size (100–576px), Feed Lines (10–500)
- Feed Paper and Test Print buttons on device page
- Brand logo with @2x assets for device page

### Fixed
- `print_image()` now supports remote URLs (http/https)
- `load_profiles()` wrapped in executor to avoid blocking event loop
- Polling: static values read every poll until non-None; dynamic values
  keep last known value on None (no more "unavailable" gaps)
- Method name fix: `print_test()` → `print_test_page()`
- Pylint 9.91/10

### Changed
- 3-retry loop on USB read failure with warning on final attempt

### Dependencies
- `paperang-p2-lib >= 0.3.6`

## v1.3.0 (2026-05-12)

### Added
- USB discovery: auto-detect Paperang P2 when plugged in (VID 0x4348, PID 0x5584)
- Config flow: UI-based setup with import from YAML, unique_id to prevent duplicates
- All 11 sensors now grouped under single "Paperang P2 Printer" device

### Changed
- `integration_type` set to `device`
- Coordinator logic moved to `__init__.py` for proper config entry lifecycle
- Sensor platform now uses `async_setup_entry` instead of YAML-based `async_setup_platform`
- Each sensor read now has 200ms delay to avoid USB communication conflicts

### Performance
- Static sensor values (voltage, temperature, firmware version, model, serial, etc.)
  are cached after first read, only re-read on device disconnect/reconnect
- Each poll cycle now reads only battery + status (0.4s vs 2.4s for full scan)

### Fixed
- Firmware version binary-to-int decoding (`\x00\x01` → `"1"`)
- Proper device association via `_attr_device_info` (was silently ignored by HA's `cached_property`)
- Coordinator `update_method` now uses `functools.partial` for reliable `hass` binding
- Pylint score improved to 9.83/10
- Removed non-existent `binary_sensor` and `button` platforms from `PLATFORMS`

### Dependencies
- `paperang-p2-lib >= 0.3.5`

## v1.2.3 (2026-05-12)

### Added
- Expanded sensor platform: voltage, temperature, heat_density, paper_type, firmware version, model, serial number, board version, hardware info
- All sensors grouped under single "Paperang P2 Printer" device via `DeviceInfo`

### Fixed
- Resolved pylint `too-many-positional-arguments` warning by making optional `__init__` params keyword-only
- Fixed coordinator `update_method` to use `functools.partial` instead of lambda for reliable `hass` binding
- Removed `__pycache__` from git tracking

## v1.2.2 (2026-05-12)

### Changed
- `_read_printer_state()` refactored to async with executor wrapper
- Dependency bump: `paperang-p2-lib >= 0.3.3`
- Removed monkey-patch, now calls lib API directly

## v1.2.1 (2026-05-12)

### Changed
- Dependency bump: `paperang-p2-lib >= 0.3.2` (fixes GET command response parsing)

## v1.2.0 (2026-05-12)

### Added
- Sensor platform: battery level and printer status monitoring
  - `sensor.paperang_p2_battery` — battery percentage (%)
  - `sensor.paperang_p2_status` — printer status (raw hex)
  - Polling every 60 seconds via DataUpdateCoordinator
- New services: `paperang.get_status`, `paperang.feed_paper`
- `async_setup_entry` / `async_unload_entry` for future config flow support
- Dependency bump: `paperang-p2-lib >= 0.2.2`

### Fixed
- `get_status()` and `get_battery()` now send required data byte (via lib update)
- Resolved all pylint warnings in sensor.py

## v1.1.1 (2026-05-11)

### Added
- HACS one-click install button in README

### Fixed
- Install instructions URLs point to GitHub repository

## v1.1.1 (2026-05-11)

### Added
- HACS one-click install button in README

### Fixed
- Install instructions URLs point to GitHub repository


## v1.1.0 (2026-05-08)

### Changed
- **Use paperang-p2-lib**: Core printer logic now comes from paperang-p2-lib pip package
  - Removed embedded `paperang_core.py` (replaced by `paperang.PaperangP2`)
  - Removed bundled fonts (provided by paperang-p2-lib + paperang-p2-fonts-cjk)
  - Removed `profiles.json` (bundled in paperang-p2-lib)
  - Updated manifest requirements to `paperang-p2-lib[qr,cjk]>=0.2.0`
- Simplified `const.py` (font constants no longer needed)
- Slimmer component zip (no embedded fonts, ~7MB smaller)

## v1.0.2 (2026-05-08)

### Added
- Add release workflow for automated GitHub Releases

## v1.0.1 (2026-05-08)

### Fixed
- Fix pylint issues: trailing whitespace, line length, import order, unused args
- Break long lines in paperang_core.py main block
- Shorten pattern-test help line

### Added
- Add Pylint workflow for Python code analysis
- Add GitHub Actions workflow for validation
- Add brand assets and printer icon

### Changed
- Update codeowners to @mdj2812
- Update repo URLs to GitHub mirror

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
