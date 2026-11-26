"""Binary sensor platform of powerbrain integration (read-only status)."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import get_entity_deviceinfo
from .__init__ import PowerbrainUpdateCoordinator
from .const import DOMAIN
from .powerbrain import Evse
from .powerbrain import Powerbrain

# (attribute in get_dev_info, entity name, icon)
EVSE_BINARY_SENSORS = [
    ("charging_enabled", "Charging Allowed", "mdi:ev-plug-type2"),
    ("paused", "Paused", "mdi:pause-circle-outline"),
    ("needs_auth", "Authorization Required", "mdi:card-account-details-outline"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the binary sensor entities for powerbrain integration."""
    brain: Powerbrain = hass.data[DOMAIN][entry.entry_id]
    coordinator = hass.data[DOMAIN][entry.entry_id + "_coordinator"]

    entities = []
    for device in brain.devices.values():
        if not device.attributes["is_evse"]:
            continue
        for attr, name, icon in EVSE_BINARY_SENSORS:
            if attr in device.attributes:
                entities.append(
                    PowerbrainBinarySensor(coordinator, device, attr, name, icon)
                )
    async_add_entities(entities)


class PowerbrainBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Read-only boolean status of an EVSE."""

    def __init__(
        self,
        coordinator: PowerbrainUpdateCoordinator,
        device: Evse,
        attr: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.device = device
        self.attribute = attr
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{device.dev_id}_{name}"
        self._attr_name = name
        self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        """Return the status."""
        value = self.device.attributes.get(self.attribute)
        return None if value is None else bool(value)

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)
