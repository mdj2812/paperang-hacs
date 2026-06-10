"""Base entity mixin for Paperang P2 Printer entities.

Provides common patterns used across all entity platforms:
- entry_id (for multi-device service routing)
- available property (reads from coordinator)
- device info (per-entry for multi-device support)
- entity naming convention
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

DEVICE_ID = "paperang_p2_printer"


def make_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return per-entry DeviceInfo for a config entry.

    This is the canonical helper so multiple Paperang devices coexist
    without collisions.  Every platform's ``async_setup_entry`` calls
    this to eliminate duplicate-code (pylint R0801).
    """
    device_id = f"paperang_{entry.entry_id}"
    return DeviceInfo(
        identifiers={("paperang", device_id)},
    )


# Map English entity names to Chinese (zh-Hans).
_NAME_ZH: dict[str, str] = {
    # Sensors
    "Battery": "电池电量",
    "Status": "状态",
    "Voltage": "电压",
    "Temperature": "温度",
    "Heat Density": "加热浓度",
    "Connection": "连接状态",
    # Buttons
    "Print": "打印",
    "Feed Paper": "送纸",
    "Test Print": "测试打印",
    # Selects
    "Print Mode": "打印模式",
    "Image Profile": "图片配置",
    # Numbers
    "Font Size": "字体大小",
    "QR Size": "二维码大小",
    "Feed Lines": "送纸行数",
    # Text
    "Print Content": "打印内容",
    # Switches
    "Vertical": "竖版打印",
}


class PaperangEntity(CoordinatorEntity):
    """Base class for all Paperang entities."""

    _attr_has_entity_name = True

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        coordinator,
        entry_id: str,
        name: str,
        suffix: str,
        icon: str,
        *,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize common attributes.

        *entry_id* is HA's raw config entry id.  Together with *suffix*
        it forms the entity unique id (``paperang_{entry_id}_{suffix}``).
        """
        self._attr_name = name
        self._attr_unique_id = f"paperang_{entry_id}_{suffix}"
        self._attr_translation_key = suffix
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
    def name(self) -> str | None:
        """Return localized name based on HA language."""
        if self.hass and (lang := self.hass.config.language) and lang.startswith("zh"):
            return _NAME_ZH.get(self._attr_name, self._attr_name)
        return self._attr_name

    @name.setter
    def name(self, value: str | None) -> None:
        """Allow setting name via _attr_name."""
        self._attr_name = value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
