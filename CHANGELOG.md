# Changelog

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
