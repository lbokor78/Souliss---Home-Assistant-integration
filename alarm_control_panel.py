"""Alarm control panel platform for Souliss T41."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import T41, T4N_ANTITHEFT, T4N_ARMED_CMD, T4N_IN_ALARM, T4N_NOT_ARMED, T4N_NO_ANTITHEFT
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient


class SoulissT41Alarm(SoulissEntity, AlarmControlPanelEntity):
    _attr_supported_features = AlarmControlPanelEntityFeature.ARM_AWAY
    _attr_code_arm_required = False

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        if not self.typical.payload:
            return None
        raw = self.typical.payload[0]
        if raw == T4N_NO_ANTITHEFT:
            return AlarmControlPanelState.DISARMED
        if raw == T4N_IN_ALARM:
            return AlarmControlPanelState.TRIGGERED
        if raw in (T4N_ANTITHEFT, T4N_ARMED_CMD):
            return AlarmControlPanelState.ARMED_AWAY
        return None

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T4N_NOT_ARMED)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T4N_ARMED_CMD)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical == T41,
        SoulissT41Alarm,
    )
