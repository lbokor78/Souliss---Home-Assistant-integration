"""Climate platform for Souliss T31."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_AUTO, FAN_HIGH, FAN_LOW, FAN_MEDIUM, FAN_OFF,
    HVACAction, HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    T31,
    T3N_COOLING, T3N_FAN_AUTO, T3N_FAN_HIGH, T3N_FAN_LOW,
    T3N_FAN_MANUAL, T3N_FAN_MED, T3N_FAN_OFF,
    T3N_HEATING, T3N_SET_TEMP, T3N_SHUTDOWN,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, half_to_float


class SoulissClimate(SoulissEntity, ClimateEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_fan_modes = [FAN_AUTO, FAN_OFF, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = -20
    _attr_max_temp = 50

    @property
    def _raw_state(self) -> int | None:
        return self.typical.payload[0] if self.typical.payload else None

    @property
    def current_temperature(self) -> float | None:
        return half_to_float(self.typical.payload[1:3]) if len(self.typical.payload) >= 3 else None

    @property
    def target_temperature(self) -> float | None:
        return half_to_float(self.typical.payload[3:5]) if len(self.typical.payload) >= 5 else None

    @property
    def hvac_mode(self) -> HVACMode | None:
        raw = self._raw_state
        if raw is None:
            return None
        if not (raw & 0x01):
            return HVACMode.OFF
        return HVACMode.COOL if (raw & 0x80) else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        raw = self._raw_state
        if raw is None:
            return None
        if not (raw & 0x01):
            return HVACAction.OFF
        if raw & 0x02:
            return HVACAction.HEATING
        if raw & 0x04:
            return HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        raw = self._raw_state
        if raw is None:
            return None
        # Souliss speed is encoded by bits 3,4,5; current openHAB decoder
        # uses the count of active speed bits.
        speed = int(bool(raw & 0x08)) + int(bool(raw & 0x10)) + int(bool(raw & 0x20))
        if speed == 0:
            return FAN_OFF
        if speed == 1:
            return FAN_LOW
        if speed == 2:
            return FAN_MEDIUM
        return FAN_HIGH

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        cmd = {
            HVACMode.OFF: T3N_SHUTDOWN,
            HVACMode.HEAT: T3N_HEATING,
            HVACMode.COOL: T3N_COOLING,
        }.get(hvac_mode)
        if cmd is not None:
            self.client.send_force(self.typical.node, self.typical.slot, cmd)

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get("temperature")
        if temperature is not None:
            self.client.send_t31_setpoint(
                self.typical.node, self.typical.slot, T3N_SET_TEMP, float(temperature)
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode == FAN_AUTO:
            self.client.send_force(self.typical.node, self.typical.slot, T3N_FAN_AUTO)
            return
        if fan_mode == FAN_OFF:
            self.client.send_force(self.typical.node, self.typical.slot, T3N_FAN_OFF)
            return

        command = {
            FAN_LOW: T3N_FAN_LOW,
            FAN_MEDIUM: T3N_FAN_MED,
            FAN_HIGH: T3N_FAN_HIGH,
        }.get(fan_mode)
        if command is not None:
            self.client.send_force(self.typical.node, self.typical.slot, T3N_FAN_MANUAL)
            self.client.send_force(self.typical.node, self.typical.slot, command)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical == T31,
        SoulissClimate,
    )
