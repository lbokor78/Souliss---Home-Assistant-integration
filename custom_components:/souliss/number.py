"""Number platform for Souliss T61-T68 setpoints."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfPower,
    UnitOfPressure, UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SUPPORTED_NUMBER_TYPICALS, T61, T62, T63, T64, T65, T66, T67, T68
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, half_to_float

RANGES = {
    T61: (-65504.0, 65504.0, 0.1),
    T62: (-20.0, 50.0, 0.1),
    T63: (0.0, 100.0, 0.1),
    T64: (0.0, 40.0, 0.1),
    T65: (0.0, 400.0, 0.1),
    T66: (0.0, 25.0, 0.1),
    T67: (0.0, 6500.0, 1.0),
    T68: (0.0, 1500.0, 0.1),
}
UNITS = {
    T62: UnitOfTemperature.CELSIUS,
    T63: PERCENTAGE,
    T64: "kLux",
    T65: UnitOfElectricPotential.VOLT,
    T66: UnitOfElectricCurrent.AMPERE,
    T67: UnitOfPower.WATT,
    T68: UnitOfPressure.HPA,
}

class SoulissSetpoint(SoulissEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, client, typical) -> None:
        super().__init__(client, typical)
        minimum, maximum, step = RANGES[typical.typical]
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = UNITS.get(typical.typical)

    @property
    def native_value(self) -> float | None:
        return half_to_float(self.typical.payload)

    async def async_set_native_value(self, value: float) -> None:
        self.client.send_half_setpoint(self.typical.node, self.typical.slot, float(value))

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in SUPPORTED_NUMBER_TYPICALS,
        SoulissSetpoint,
    )
