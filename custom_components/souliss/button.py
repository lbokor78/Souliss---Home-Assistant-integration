"""Button platform for Souliss auxiliary commands."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    T11, T12, T14, T16, T19, T31, T41, T42,
    T1N_BRIGHT_DOWN, T1N_BRIGHT_UP, T1N_ON, T1N_SET,
    T3N_AS_MEASURED, T4N_REARM,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, SoulissTypical


class SoulissGatewayRediscoverButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Rediscover network"

    def __init__(self, client: SoulissClient) -> None:
        self.client = client
        self._attr_unique_id = f"{client.gateway_ip}_rediscover"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.client.gateway_ip}-gateway")},
            manufacturer="Souliss",
            model="Souliss Gateway",
            name=f"Souliss Gateway {self.client.gateway_ip}",
        )

    async def async_press(self) -> None:
        self.client.rediscover()


class SoulissCommandButton(SoulissEntity, ButtonEntity):
    def __init__(
        self,
        client: SoulissClient,
        typical: SoulissTypical,
        *,
        role: str,
        name: str,
        command: Callable[[], None],
    ) -> None:
        super().__init__(client, typical, role=role, name=name)
        self._command = command

    async def async_press(self) -> None:
        self._command()


def make_buttons(client: SoulissClient, item: SoulissTypical):
    n, s = item.node, item.slot
    out = []

    def add(role: str, label: str, fn: Callable[[], None]) -> None:
        out.append(SoulissCommandButton(
            client, item, role=role,
            name=f"{label} N{n} S{s}", command=fn,
        ))

    if item.typical == T14:
        add("pulse", "T14 Pulse", lambda: client.send_force(n, s, T1N_ON))

    if item.typical == T16:
        add("white", "T16 White", lambda: client.send_force(n, s, T1N_SET, bytes([255, 255, 255])))
        add("brightness_up", "T16 Brightness up", lambda: client.send_force(n, s, T1N_BRIGHT_UP))
        add("brightness_down", "T16 Brightness down", lambda: client.send_force(n, s, T1N_BRIGHT_DOWN))

    if item.typical == T19:
        add("brightness_up", "T19 Brightness up", lambda: client.send_force(n, s, T1N_BRIGHT_UP))
        add("brightness_down", "T19 Brightness down", lambda: client.send_force(n, s, T1N_BRIGHT_DOWN))

    if item.typical == T31:
        add("as_measured", "T31 Use measured as setpoint", lambda: client.send_force(n, s, T3N_AS_MEASURED))

    if item.typical in {T41, T42}:
        add("rearm", f"{item.code} Rearm alarm", lambda: client.send_force(n, s, T4N_REARM))

    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    async_add_entities([SoulissGatewayRediscoverButton(client)])
    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in {T11, T12, T14, T16, T19, T31, T41, T42},
        make_buttons,
    )
