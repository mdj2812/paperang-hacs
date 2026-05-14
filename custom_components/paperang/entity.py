# pylint: disable=import-error
"""Base entity mixin for Paperang P2 Printer entities.

Provides common patterns used across all entity platforms:
- available property (reads from coordinator)
- device info
- entity naming convention
"""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

DEVICE_ID = "paperang_p2_printer"
DEVICE_INFO = DeviceInfo(  # pylint: disable=invalid-name
    identifiers={("paperang", DEVICE_ID)},
    name="Paperang P2 Printer",
    manufacturer="Paperang",
    model="P2",
)


class PaperangEntity(CoordinatorEntity):  # pylint: disable=too-few-public-methods
    """Base class for all Paperang entities."""

    _attr_has_entity_name = True
    _attr_device_info = DEVICE_INFO

    def __init__(self, coordinator, name: str, unique_id: str, icon: str) -> None:
        """Initialize common attributes."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        super().__init__(coordinator)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
