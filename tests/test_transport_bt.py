"""Tests for Bluetooth transport layer — device scan and verification."""

from unittest.mock import MagicMock, patch

import pytest


# ── _scan_fallback_devices ──────────────────────────────────────────


class TestScanFallbackDevices:
    """Tests for _scan_fallback_devices (bluetoothctl fallback)."""

    def test_returns_paperang_devices(self):
        """Finds devices named 'Paperang-xxxx' in bluetoothctl output."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        fake_stdout = (
            "Device AA:BB:CC:DD:EE:FF Paperang-01\n"
            "Device 11:22:33:44:55:66 SomeOtherDevice\n"
            "Device 77:88:99:AA:BB:CC miaomiaoji-P2\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = fake_stdout
            mock_run.return_value.returncode = 0
            result = _scan_fallback_devices(set())

        assert len(result) == 2
        assert result[0] == {"name": "Paperang-01", "address": "AA:BB:CC:DD:EE:FF"}
        assert result[1] == {"name": "miaomiaoji-P2", "address": "77:88:99:AA:BB:CC"}

    def test_dedup_by_seen_set(self):
        """Skips addresses already in the seen set."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        fake_stdout = "Device AA:BB:CC:DD:EE:FF Paperang-01\n"
        seen = {"AA:BB:CC:DD:EE:FF"}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = fake_stdout
            mock_run.return_value.returncode = 0
            result = _scan_fallback_devices(seen)

        assert result == []
        assert "AA:BB:CC:DD:EE:FF" in seen

    def test_no_paperang_devices(self):
        """Returns empty when no matching device names found."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        fake_stdout = "Device AA:BB:CC:DD:EE:FF RandomPrinter\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = fake_stdout
            mock_run.return_value.returncode = 0
            result = _scan_fallback_devices(set())

        assert result == []

    def test_subprocess_exception_handled(self):
        """Returns empty list on subprocess error."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        with patch("subprocess.run", side_effect=OSError("bluetoothctl not found")):
            result = _scan_fallback_devices(set())

        assert result == []

    def test_empty_stdout(self):
        """Returns empty on empty bluetoothctl output."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            result = _scan_fallback_devices(set())

        assert result == []


# ── scan_bt_devices ──────────────────────────────────────────────────


class TestScanBtDevices:
    """Tests for scan_bt_devices()."""

    def test_active_scan_finds_devices(self):
        """BtTransport.scan() returns matching devices."""
        from custom_components.paperang.transport.bt import scan_bt_devices

        mock_bt = MagicMock()
        mock_bt.scan.return_value = [
            ("AA:BB:CC:DD:EE:FF", "Paperang-01"),
            ("11:22:33:44:55:66", "OtherDevice"),
        ]

        with patch("custom_components.paperang.transport.bt.BtTransport", mock_bt):
            result = scan_bt_devices()

        assert len(result) == 1
        assert result[0] == {"name": "Paperang-01", "address": "AA:BB:CC:DD:EE:FF"}

    def test_active_scan_empty_falls_back(self):
        """When active scan returns empty, falls back to bluetoothctl."""
        from custom_components.paperang.transport.bt import scan_bt_devices

        mock_bt = MagicMock()
        mock_bt.scan.return_value = []

        fake_stdout = "Device 77:88:99:AA:BB:CC miaomiaoji-P2\n"

        with patch("custom_components.paperang.transport.bt.BtTransport", mock_bt):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = fake_stdout
                mock_run.return_value.returncode = 0
                result = scan_bt_devices()

        assert len(result) == 1
        assert result[0] == {"name": "miaomiaoji-P2", "address": "77:88:99:AA:BB:CC"}

    def test_active_scan_exception_handled(self):
        """BtTransport.scan() raising exception → empty list, fallback used."""
        from custom_components.paperang.transport.bt import scan_bt_devices

        mock_bt = MagicMock()
        mock_bt.scan.side_effect = RuntimeError("scan failed")

        fake_stdout = "Device AA:BB:CC:DD:EE:FF Paperang-01\n"

        with patch("custom_components.paperang.transport.bt.BtTransport", mock_bt):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = fake_stdout
                mock_run.return_value.returncode = 0
                result = scan_bt_devices()

        assert len(result) == 1

    def test_scan_ignores_nameless_devices(self):
        """Devices with None/empty name are filtered out."""
        from custom_components.paperang.transport.bt import scan_bt_devices

        mock_bt = MagicMock()
        mock_bt.scan.return_value = [
            ("AA:BB:CC:DD:EE:FF", None),
            ("11:22:33:44:55:66", ""),
        ]

        with patch("custom_components.paperang.transport.bt.BtTransport", mock_bt):
            with patch(
                "custom_components.paperang.transport.bt._scan_fallback_devices",
                return_value=[],
            ):
                result = scan_bt_devices()

        assert result == []
