"""Switch platform of powerbrain integration."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import get_entity_deviceinfo
from .__init__ import PowerbrainUpdateCoordinator
from .const import DOMAIN
from .powerbrain import Evse
from .powerbrain import Powerbrain

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the switch entities for powerbrain integration."""
    brain: Powerbrain = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []
    for device in brain.devices.values():
        if device.attributes["is_evse"]:
            entities.append(
                EnableChargingSwitchEntity(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"],
                    device,
                    "Charging Enabled",
                )
            )
            entities.append(
                EnableRulesSwitchEntity(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"],
                    device,
                    "Charging Rules Enabled",
                )
            )
            entities.append(
                EnableUserRulesSwitchEntity(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"],
                    device,
                    "User Rules Enabled",
                )
            )
    async_add_entities(entities)


class EnableChargingSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for evse."""

    def __init__(
        self, coordinator: PowerbrainUpdateCoordinator, device: Evse, name: str
    ) -> None:
        """Initialize entity for charging current override."""
        super().__init__(coordinator)
        self.device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{self.device.dev_id}_{name}"
        self._attr_name = name
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_icon = "mdi:ev-station"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        _LOGGER.debug("Turning on %s on %s", self.name, self.device.name)
        await self.hass.async_add_executor_job(self.device.disable_charging, False)
        await _async_refresh_and_verify(self, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        _LOGGER.debug("Turning off %s on %s", self.name, self.device.name)
        await self.hass.async_add_executor_job(self.device.disable_charging, True)
        await _async_refresh_and_verify(self, False)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)

    @property
    def is_on(self) -> bool:
        """Switch status."""
        overridebit1 = self.device.attributes.get("overrides", 0) & 0b0001
        return not overridebit1


class EnableRulesSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for evse."""

    def __init__(
        self, coordinator: PowerbrainUpdateCoordinator, device: Evse, name: str
    ) -> None:
        """Initialize entity for evse rules switch."""
        super().__init__(coordinator)
        self.device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{self.device.dev_id}_{name}"
        self._attr_name = name
        self._attr_device_class = SwitchDeviceClass.SWITCH

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        _LOGGER.debug("Turning on %s on %s", self.name, self.device.name)
        await self.hass.async_add_executor_job(
            self.device.disable_charging_rules, False
        )
        await _async_refresh_and_verify(self, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        _LOGGER.debug("Turning off %s on %s", self.name, self.device.name)
        await self.hass.async_add_executor_job(self.device.disable_charging_rules, True)
        await _async_refresh_and_verify(self, False)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)

    @property
    def is_on(self) -> bool:
        """Switch status."""
        overridebit2 = self.device.attributes.get("overrides", 0) & 0b0010
        return not overridebit2


class EnableUserRulesSwitchEntity(EnableRulesSwitchEntity):
    """Switch entity for evse user rules."""

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on."""
        _LOGGER.debug("Turning on %s on %s", self.name, self.device.name)
        await self.hass.async_add_executor_job(self.device.disable_user_rules, False)
        await _async_refresh_and_verify(self, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off."""
        _LOGGER.debug("Turning off %s on %s", self.name, self.device.name)
        await self.hass.async_add_executor_job(self.device.disable_user_rules, True)
        await _async_refresh_and_verify(self, False)

    @property
    def is_on(self) -> bool:
        """Switch status."""
        overridebit3 = self.device.attributes.get("overrides", 0) & 0b0100
        return not overridebit3


async def _async_refresh_and_verify(entity: SwitchEntity, expected: bool) -> None:
    """Refresh data and report an error if the Powerbrain ignored the command."""
    await entity.coordinator.async_refresh()
    if entity.is_on != expected:
        msg = (
            f"{entity.device.name} / {entity.name}: the Powerbrain accepted the "
            "command but the state did not change "
            f"(overrides={entity.device.attributes.get('overrides')}). The wallbox "
            "may require an RFID/PIN (see integration options) or admin rights."
        )
        _LOGGER.warning(msg)
        raise HomeAssistantError(msg)
