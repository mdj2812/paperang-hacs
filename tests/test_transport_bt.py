"""Tests for Bluetooth transport layer — device scan and verification."""

from unittest.mock import MagicMock, patch

import pytest

# All tests mock lib imports — avoids dependency on paperang-p2-lib being
# installed / PyPI-cached in the CI container.

_MOCK_BT_NAMES = {"paperang", "miaomiaoji"}


def _mock_check_uuid_true(_addr: str) -> bool:
    return True


def _mock_check_uuid_false(_addr: str) -> bool:
    return False


# ── _scan_fallback_devices ──────────────────────────────────────────


class TestScanFallbackDevices:
    """Tests for _scan_fallback_devices (bluetoothctl fallback)."""

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           return_value=False)
    def test_returns_paperang_devices(self, mock_uuid, mock_names):
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

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           return_value=False)
    def test_dedup_by_seen_set(self, mock_uuid, mock_names):
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

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           return_value=False)
    def test_no_paperang_devices(self, mock_uuid, mock_names):
        """Returns empty when no matching device names or UUIDs found."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        devices_proc = MagicMock()
        devices_proc.stdout = "Device AA:BB:CC:DD:EE:FF RandomPrinter\n"
        devices_proc.returncode = 0

        with patch("subprocess.run", return_value=devices_proc):
            result = _scan_fallback_devices(set())

        assert result == []

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    def test_subprocess_exception_handled(self, mock_names):
        """Returns empty list on subprocess error."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        with patch("subprocess.run", side_effect=OSError("bluetoothctl not found")):
            result = _scan_fallback_devices(set())

        assert result == []

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    def test_empty_stdout(self, mock_names):
        """Returns empty on empty bluetoothctl output."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            result = _scan_fallback_devices(set())

        assert result == []

    # ── UUID fallback tests ──

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           return_value=True)
    def test_uuid_fallback_finds_renamed_device(self, mock_uuid, mock_names):
        """A renamed/paired device with matching UUID is discovered."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        devices_proc = MagicMock()
        devices_proc.stdout = "Device AA:BB:CC:DD:EE:FF MyRenamedPrinty\n"
        devices_proc.returncode = 0

        with patch("subprocess.run", return_value=devices_proc):
            result = _scan_fallback_devices(set())

        assert len(result) == 1
        assert result[0] == {"name": "MyRenamedPrinty",
                             "address": "AA:BB:CC:DD:EE:FF"}

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           return_value=False)
    def test_uuid_fallback_skips_non_paperang_uuid(self, mock_uuid, mock_names):
        """Device with non-matching name and UUID is excluded."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        devices_proc = MagicMock()
        devices_proc.stdout = "Device 11:22:33:44:55:66 SomeGadget\n"
        devices_proc.returncode = 0

        with patch("subprocess.run", return_value=devices_proc):
            result = _scan_fallback_devices(set())

        assert result == []

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           side_effect=[True, False])
    def test_uuid_fallback_and_name_match_coexist(self, mock_uuid, mock_names):
        """Both fast path (name) and UUID fallback find paired devices."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        devices_proc = MagicMock()
        devices_proc.stdout = (
            "Device 00:15:83:EB:05:17 Paperang-01\n"
            "Device AA:BB:CC:DD:EE:FF RenamedPrinty\n"
            "Device 11:22:33:44:55:66 RandomSpeaker\n"
        )
        devices_proc.returncode = 0

        with patch("subprocess.run", return_value=devices_proc):
            result = _scan_fallback_devices(set())

        assert len(result) == 2
        assert result[0] == {"name": "Paperang-01",
                             "address": "00:15:83:EB:05:17"}
        assert result[1] == {"name": "RenamedPrinty",
                             "address": "AA:BB:CC:DD:EE:FF"}

    @patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
           _MOCK_BT_NAMES)
    @patch("custom_components.paperang.transport.bt.check_paperang_uuid",
           return_value=False)
    def test_uuid_fallback_error_skips_device(self, mock_uuid, mock_names):
        """check_paperang_uuid returns False (error) → device skipped."""
        from custom_components.paperang.transport.bt import _scan_fallback_devices

        devices_proc = MagicMock()
        devices_proc.stdout = "Device DE:AD:BE:EF:00:01 BadDevice\n"
        devices_proc.returncode = 0

        with patch("subprocess.run", return_value=devices_proc):
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

        with (
            patch("custom_components.paperang.transport.bt.BtTransport",
                  mock_bt),
            patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
                  _MOCK_BT_NAMES),
            patch("custom_components.paperang.transport.bt._scan_fallback_devices",
                  return_value=[]),
        ):
            result = scan_bt_devices()

        assert len(result) == 1
        assert result[0] == {"name": "Paperang-01",
                             "address": "AA:BB:CC:DD:EE:FF"}

    def test_active_scan_empty_falls_back(self):
        """When active scan returns empty, falls back to bluetoothctl."""
        from custom_components.paperang.transport.bt import scan_bt_devices

        mock_bt = MagicMock()
        mock_bt.scan.return_value = []

        with (
            patch("custom_components.paperang.transport.bt.BtTransport",
                  mock_bt),
            patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
                  _MOCK_BT_NAMES),
            patch("custom_components.paperang.transport.bt._scan_fallback_devices",
                  return_value=[{"name": "miaomiaoji-P2",
                                 "address": "77:88:99:AA:BB:CC"}]),
        ):
            result = scan_bt_devices()

        assert len(result) == 1
        assert result[0] == {"name": "miaomiaoji-P2",
                             "address": "77:88:99:AA:BB:CC"}

    def test_active_scan_exception_handled(self):
        """BtTransport.scan() raising exception → empty list, fallback used."""
        from custom_components.paperang.transport.bt import scan_bt_devices

        mock_bt = MagicMock()
        mock_bt.scan.side_effect = RuntimeError("scan failed")

        with (
            patch("custom_components.paperang.transport.bt.BtTransport",
                  mock_bt),
            patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
                  _MOCK_BT_NAMES),
            patch("custom_components.paperang.transport.bt._scan_fallback_devices",
                  return_value=[{"name": "Paperang-01",
                                 "address": "AA:BB:CC:DD:EE:FF"}]),
        ):
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

        with (
            patch("custom_components.paperang.transport.bt.BtTransport",
                  mock_bt),
            patch("custom_components.paperang.transport.bt.PAPERANG_BT_NAMES",
                  _MOCK_BT_NAMES),
            patch("custom_components.paperang.transport.bt._scan_fallback_devices",
                  return_value=[]),
        ):
            result = scan_bt_devices()

        assert result == []
