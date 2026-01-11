"""Mikrotik sensor platform."""

from __future__ import annotations

from logging import getLogger
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MikrotikCoordinator
from .entity import MikrotikEntity, async_add_entities
from .helper import format_attribute
from .sensor_types import (
    SENSOR_TYPES,
    SENSOR_SERVICES,
    DEVICE_ATTRIBUTES_IFACE_ETHER,
    DEVICE_ATTRIBUTES_IFACE_SFP,
    DEVICE_ATTRIBUTES_IFACE_WIRELESS,
)
from .const import CONF_POE_GROUPS, CONF_POE_INTERFACES

_LOGGER = getLogger(__name__)


# ---------------------------
#   async_setup_entry
# ---------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    _async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry for component"""
    dispatcher = {
        "MikrotikSensor": MikrotikSensor,
        "MikrotikInterfaceTrafficSensor": MikrotikInterfaceTrafficSensor,
        "MikrotikClientTrafficSensor": MikrotikClientTrafficSensor,
    }
    await async_add_entities(hass, config_entry, dispatcher)

    # Add POE sensors if POE interfaces are selected or POE-only mode is enabled
    poe_interfaces = config_entry.options.get(CONF_POE_INTERFACES, [])
    poe_only_mode = config_entry.options.get("poe_only_mode", False)
    
    if poe_interfaces or poe_only_mode:
        coordinator = hass.data["mikrotik_router"][config_entry.entry_id].data_coordinator
        entities = []
        
        # Get available POE interfaces from coordinator data
        available_poe_interfaces = list(coordinator.ds.get("poe", {}).keys())
        
        if poe_only_mode and not poe_interfaces:
            # In POE-only mode with no specific selection, use all available
            selected_interfaces = available_poe_interfaces
        else:
            # Use selected interfaces, filtered by what's available
            selected_interfaces = [iface for iface in poe_interfaces if iface in available_poe_interfaces]
        
        entities.extend([MikrotikPOESensor(coordinator, iface) for iface in selected_interfaces])
        
        # Add POE group sensors
        poe_groups_str = config_entry.options.get(CONF_POE_GROUPS, "")
        if poe_groups_str:
            for group_def in poe_groups_str.split(";"):
                if ":" in group_def:
                    group_name, ifaces_str = group_def.split(":", 1)
                    group_name = group_name.strip()
                    interfaces = [iface.strip() for iface in ifaces_str.split(",")]
                    entities.append(MikrotikPOEGroupSensor(coordinator, group_name, interfaces))
        
        _async_add_entities(entities)


# ---------------------------
#   MikrotikPOESensor
# ---------------------------
class MikrotikPOESensor(CoordinatorEntity, SensorEntity):
    """Sensor for POE wattage of an interface."""
    def __init__(self, coordinator, interface):
        super().__init__(coordinator)
        self._attr_name = f"POE Power {interface}"
        self._attr_unique_id = f"{coordinator.host}_poe_power_{interface}"
        self._attr_native_unit_of_measurement = "W"
        self.interface = interface

    @property
    def native_value(self):
        poe_data = self.coordinator.ds.get("poe", {})
        return poe_data.get(self.interface, None)


# ---------------------------
#   MikrotikPOEGroupSensor
# ---------------------------
class MikrotikPOEGroupSensor(CoordinatorEntity, SensorEntity):
    """Sensor for summed POE wattage of multiple interfaces."""
    def __init__(self, coordinator, group_name, interfaces):
        super().__init__(coordinator)
        self._attr_name = f"POE Power {group_name}"
        self._attr_unique_id = f"{coordinator.host}_poe_power_{group_name.lower().replace(' ', '_')}"
        self._attr_native_unit_of_measurement = "W"
        self.group_name = group_name
        self.interfaces = interfaces

    @property
    def native_value(self):
        poe_data = self.coordinator.ds.get("poe", {})
        total = 0
        for iface in self.interfaces:
            power = poe_data.get(iface, 0)
            if power:
                total += power
        return total if total > 0 else None


# ---------------------------
#   MikrotikSensor
# ---------------------------
class MikrotikSensor(MikrotikEntity, SensorEntity):
    """Define an Mikrotik sensor."""

    def __init__(
        self,
        coordinator: MikrotikCoordinator,
        entity_description,
        uid: str | None = None,
    ):
        super().__init__(coordinator, entity_description, uid)
        self._attr_suggested_unit_of_measurement = (
            self.entity_description.suggested_unit_of_measurement
        )

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self._data[self.entity_description.data_attribute]

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit the value is expressed in."""
        if self.entity_description.native_unit_of_measurement:
            if self.entity_description.native_unit_of_measurement.startswith("data__"):
                uom = self.entity_description.native_unit_of_measurement[6:]
                if uom in self._data:
                    return self._data[uom]

            return self.entity_description.native_unit_of_measurement

        return None


# ---------------------------
#   MikrotikInterfaceTrafficSensor
# ---------------------------
class MikrotikInterfaceTrafficSensor(MikrotikSensor):
    """Define an Mikrotik MikrotikInterfaceTrafficSensor sensor."""

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes

        if self._data["type"] == "ether":
            for variable in DEVICE_ATTRIBUTES_IFACE_ETHER:
                if variable in self._data:
                    attributes[format_attribute(variable)] = self._data[variable]

            if "sfp-shutdown-temperature" in self._data:
                for variable in DEVICE_ATTRIBUTES_IFACE_SFP:
                    if variable in self._data:
                        attributes[format_attribute(variable)] = self._data[variable]

        elif self._data["type"] == "wlan":
            for variable in DEVICE_ATTRIBUTES_IFACE_WIRELESS:
                if variable in self._data:
                    attributes[format_attribute(variable)] = self._data[variable]

        return attributes


# ---------------------------
#   MikrotikClientTrafficSensor
# ---------------------------
class MikrotikClientTrafficSensor(MikrotikSensor):
    """Define an Mikrotik MikrotikClientTrafficSensor sensor."""

    @property
    def custom_name(self) -> str:
        """Return the name for this entity"""
        return f"{self.entity_description.name}"

    # @property
    # def available(self) -> bool:
    #     """Return if controller and accounting feature in Mikrotik is available.
    #     Additional check for lan-tx/rx sensors
    #     """
    #     if self.entity_description.data_attribute in ["lan-tx", "lan-rx"]:
    #         return (
    #             self.coordinator.connected()
    #             and self._data["available"]
    #             and self._data["local_accounting"]
    #         )
    #     else:
    #         return self.coordinator.connected() and self._data["available"]
