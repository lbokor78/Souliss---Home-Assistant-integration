"""Light platform for Souliss."""

from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    T16, T19,
    T1N_OFF, T1N_OFF_COIL, T1N_OFF_FEEDBACK,
    T1N_ON, T1N_ON_COIL, T1N_ON_FEEDBACK,
    T1N_SET,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, SoulissTypical


def raw_is_on(raw: int) -> bool | None:
    if raw in (T1N_ON_COIL, T1N_ON_FEEDBACK):
        return True
    if raw in (T1N_OFF_COIL, T1N_OFF_FEEDBACK):
        return False
    return None


class SoulissT19Light(SoulissEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool | None:
        return raw_is_on(self.typical.payload[0]) if self.typical.payload else None

    @property
    def brightness(self) -> int | None:
        return self.typical.payload[1] if len(self.typical.payload) >= 2 else None

    async def async_turn_on(self, **kwargs) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is None:
            self.client.send_force(self.typical.node, self.typical.slot, T1N_ON)
        else:
            self.client.send_force(
                self.typical.node, self.typical.slot, T1N_SET,
                bytes([int(brightness) & 0xFF]),
            )

    async def async_turn_off(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T1N_OFF)


class SoulissT16RGBLight(SoulissEntity, LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    @property
    def is_on(self) -> bool | None:
        return raw_is_on(self.typical.payload[0]) if self.typical.payload else None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        if len(self.typical.payload) < 4:
            return None
        return (
            self.typical.payload[1],
            self.typical.payload[2],
            self.typical.payload[3],
        )

    @property
    def brightness(self) -> int | None:
        rgb = self.rgb_color
        return max(rgb) if rgb else None

    async def async_turn_on(self, **kwargs) -> None:
        rgb = kwargs.get(ATTR_RGB_COLOR)
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if rgb is None and brightness is None:
            self.client.send_force(self.typical.node, self.typical.slot, T1N_ON)
            return

        if rgb is None:
            current = self.rgb_color or (255, 255, 255)
            current_max = max(current) or 1
            factor = int(brightness) / current_max
            rgb = tuple(max(0, min(255, round(c * factor))) for c in current)
        elif brightness is not None:
            current_max = max(rgb) or 1
            factor = int(brightness) / current_max
            rgb = tuple(max(0, min(255, round(c * factor))) for c in rgb)

        self.client.send_force(
            self.typical.node, self.typical.slot, T1N_SET,
            bytes([int(rgb[0]), int(rgb[1]), int(rgb[2])]),
        )

    async def async_turn_off(self, **kwargs) -> None:
        self.client.send_force(self.typical.node, self.typical.slot, T1N_OFF)


def factory(client: SoulissClient, item: SoulissTypical):
    if item.typical == T16:
        return SoulissT16RGBLight(client, item)
    return SoulissT19Light(client, item)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in {T16, T19},
        factory,
    )
