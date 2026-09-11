"""Cover platform for Souliss."""

from __future__ import annotations

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    T21, T22,
    T2N_CLOSE, T2N_COIL_CLOSE, T2N_COIL_OPEN, T2N_COIL_STOP,
    T2N_LIM_CLOSE, T2N_LIM_OPEN, T2N_NO_LIMIT,
    T2N_OPEN, T2N_STATE_CLOSE, T2N_STATE_OPEN, T2N_STOP, T2N_TIMER_OFF,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient


class SoulissCover(SoulissEntity, CoverEntity):
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP

    @property
    def current_cover_position(self) -> int | None:
        if not self.typical.payload:
            return None
        raw = self.typical.payload[0]
        # Home Assistant: 100=open, 0=closed.
        if raw in (T2N_COIL_OPEN, T2N_LIM_OPEN, T2N_STATE_OPEN):
            return 100
        if raw in (T2N_COIL_CLOSE, T2N_LIM_CLOSE, T2N_STATE_CLOSE):
            return 0
        if raw in (T2N_COIL_STOP, T2N_NO_LIMIT, T2N_TIMER_OFF):
            return 50
        return None

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        return None if pos is None else pos == 0

    @property
    def is_opening(self) -> bool | None:
        return bool(self.typical.payload and self.typical.payload[0] == T2N_OPEN)

    @property
    def is_closing(self) -> bool | None:
        return bool(self.typical.payload and self.typical.payload[0] == T2N_CLOSE)

    async def async_open_cover(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T2N_OPEN)

    async def async_close_cover(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T2N_CLOSE)

    async def async_stop_cover(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T2N_STOP)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in {T21, T22},
        SoulissCover,
    )
