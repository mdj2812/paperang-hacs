"""Load pip *paperang-p2-lib* despite the package name clash with this integration.

Home Assistant puts ``custom_components/`` first on ``sys.path``, which would
make ``import paperang`` resolve to this package.  We temporarily strip those
entries, import the real library, then restore ``sys.path``.
"""

from __future__ import annotations

import sys

# The pip-installed paperang-p2-lib shares the module name 'paperang'
# with this HA component.
_custom_paths = [p for p in sys.path if "custom_components" in p]
for _p in _custom_paths:
    sys.path.remove(_p)

# pylint: disable-next=import-outside-toplevel,import-error,wrong-import-position
import paperang as _lib  # noqa: E402 pylint: disable=no-member

for _p in _custom_paths:
    sys.path.insert(0, _p)

PaperangP2 = _lib.PaperangP2  # pylint: disable=no-member
load_profiles = _lib.load_profiles  # pylint: disable=no-member
crc32_paperang = _lib.crc32_paperang  # pylint: disable=no-member
pack_packet = _lib.pack_packet  # pylint: disable=no-member
UsbTransportBase = _lib.transport.UsbTransport  # pylint: disable=no-member

try:
    BtTransport = _lib.transport.BtTransport  # pylint: disable=no-member
    check_paperang_uuid = _lib.transport.check_paperang_uuid  # pylint: disable=no-member
    PAPERANG_BT_NAMES = _lib.transport.PAPERANG_BT_NAMES  # pylint: disable=no-member
except (ImportError, AttributeError):
    BtTransport = None  # pylint: disable=invalid-name
    check_paperang_uuid = None  # pylint: disable=invalid-name
    PAPERANG_BT_NAMES = None  # pylint: disable=invalid-name
