"""Switch platform for Souliss."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    T11, T12, T18,
    T1N_AUTO,
    T1N_OFF, T1N_OFF_COIL, T1N_OFF_COIL_AUTO, T1N_OFF_FEEDBACK,
    T1N_ON, T1N_ON_COIL, T1N_ON_COIL_AUTO, T1N_ON_FEEDBACK,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, SoulissTypical


ON_STATES = {T1N_ON_COIL, T1N_ON_COIL_AUTO, T1N_ON_FEEDBACK}
OFF_STATES = {T1N_OFF_COIL, T1N_OFF_COIL_AUTO, T1N_OFF_FEEDBACK}


class SoulissSwitch(SoulissEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        if not self.typical.payload:
            return None
        raw = self.typical.payload[0]
        if raw in ON_STATES:
            return True
        if raw in OFF_STATES:
            return False
        return None

    async def async_turn_on(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T1N_ON)

    async def async_turn_off(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T1N_OFF)


class SoulissT12AutoSwitch(SoulissEntity, SwitchEntity):
    """AUTO-mode control for T12.

    Souliss has an explicit AUTO command but no explicit AUTO-OFF command.
    To leave AUTO while preserving current output, send normal ON/OFF.
    """

    def __init__(self, client: SoulissClient, typical: SoulissTypical) -> None:
        super().__init__(client, typical, role="auto", name=f"{typical.code} AUTO N{typical.node} S{typical.slot}")

    @property
    def is_on(self) -> bool | None:
        if not self.typical.payload:
            return None
        return self.typical.payload[0] in {T1N_ON_COIL_AUTO, T1N_OFF_COIL_AUTO}

    async def async_turn_on(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T1N_AUTO)

    async def async_turn_off(self, **kwargs) -> None:
        raw = self.typical.payload[0] if self.typical.payload else T1N_OFF_COIL
        command = T1N_ON if raw in {T1N_ON_COIL, T1N_ON_COIL_AUTO, T1N_ON_FEEDBACK} else T1N_OFF
        self.client.send_force(self.typical.node, self.typical.slot, command)


def make_switches(client: SoulissClient, item: SoulissTypical):
    entities = [SoulissSwitch(client, item)]
    if item.typical == T12:
        entities.append(SoulissT12AutoSwitch(client, item))
    return entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in {T11, T12, T18},
        make_switches,
    )
