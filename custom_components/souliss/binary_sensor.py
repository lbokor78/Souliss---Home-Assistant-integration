"""Binary sensor platform for Souliss."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    T13, T1A, T42,
    T1N_OFF_COIL, T1N_OFF_FEEDBACK, T1N_ON_COIL, T1N_ON_FEEDBACK,
    T4N_ANTITHEFT, T4N_IN_ALARM,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, SoulissTypical


class SoulissBinarySensor(SoulissEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        if not self.typical.payload:
            return None
        raw = self.typical.payload[0]
        if raw in (T1N_ON_COIL, T1N_ON_FEEDBACK):
            return True
        if raw in (T1N_OFF_COIL, T1N_OFF_FEEDBACK):
            return False
        return bool(raw)


class SoulissT1ABitSensor(SoulissEntity, BinarySensorEntity):
    def __init__(self, client: SoulissClient, typical: SoulissTypical, bit: int) -> None:
        self.bit = bit
        super().__init__(
            client, typical, role=f"bit_{bit + 1}",
            name=f"T1A Input {bit + 1} N{typical.node} S{typical.slot}",
        )

    @property
    def is_on(self) -> bool | None:
        if not self.typical.payload:
            return None
        return bool(self.typical.payload[0] & (1 << self.bit))


class SoulissT42AlarmSensor(SoulissEntity, BinarySensorEntity):
    def __init__(self, client: SoulissClient, typical: SoulissTypical) -> None:
        super().__init__(client, typical, role="alarm", name=f"T42 Alarm N{typical.node} S{typical.slot}")

    @property
    def is_on(self) -> bool | None:
        if not self.typical.payload:
            return None
        raw = self.typical.payload[0]
        return raw in {T4N_ANTITHEFT, T4N_IN_ALARM}


def factory(client: SoulissClient, item: SoulissTypical):
    if item.typical == T1A:
        return [SoulissT1ABitSensor(client, item, bit) for bit in range(8)]
    if item.typical == T42:
        return SoulissT42AlarmSensor(client, item)
    return SoulissBinarySensor(client, item)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in {T13, T1A, T42},
        factory,
    )
