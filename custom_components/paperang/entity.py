"""Base entity mixin for Paperang P2 Printer entities.

Provides common patterns used across all entity platforms:
- entry_id (for multi-device service routing)
- available property (reads from coordinator)
- device info (per-entry for multi-device support)
- entity naming convention
"""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

DEVICE_ID = "paperang_p2_printer"


class PaperangEntity(CoordinatorEntity):
    """Base class for all Paperang entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        name: str,
        unique_id: str,
        icon: str,
        *,
        entry_id: str,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize common attributes."""
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = icon
        self._entry_id = entry_id
        if device_info is not None:
            self._attr_device_info = device_info
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={("paperang", DEVICE_ID)},
                name="Paperang P2 Printer",
                manufacturer="Paperang",
                model="P2",
            )
        super().__init__(coordinator)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
