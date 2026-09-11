"""Base entities for Souliss."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, TYPICAL_NAMES
from .protocol import SoulissClient, SoulissTypical


class SoulissEntity(Entity):
    _attr_has_entity_name = True

    def __init__(
        self,
        client: SoulissClient,
        typical: SoulissTypical,
        *,
        role: str = "main",
        name: str | None = None,
    ) -> None:
        self.client = client
        self.typical = typical
        self.role = role
        # Preserve the alpha.2 unique_id for the primary entity so upgrades
        # never create duplicate Home Assistant registry entries.
        if role == "main":
            self._attr_unique_id = (
                f"{client.gateway_ip}_node_{typical.node}_slot_{typical.slot}_"
                f"{typical.code.lower()}"
            )
        else:
            self._attr_unique_id = (
                f"{client.gateway_ip}_node_{typical.node}_slot_{typical.slot}_"
                f"{typical.code.lower()}_{role}"
            )
        self._attr_name = name or f"{typical.code} N{typical.node} S{typical.slot}"

    @property
    def available(self) -> bool:
        return self.client.typical_available(self.typical)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.client.gateway_ip}-node-{self.typical.node}")},
            manufacturer="Souliss",
            model="Souliss Node",
            name=f"Souliss Node {self.typical.node}",
            via_device=(DOMAIN, f"{self.client.gateway_ip}-gateway"),
        )

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attrs: dict[str, object] = {
            "souliss_typical": self.typical.code,
            "typical_name": TYPICAL_NAMES.get(self.typical.typical, "Unknown/Custom"),
            "node": self.typical.node,
            "slot": self.typical.slot,
            "slot_span": self.typical.span,
            "raw": self.typical.raw_hex,
            "active_in_discovery": self.typical.active,
        }
        if self.typical.health is not None:
            attrs["health_raw"] = self.typical.health
        if self.typical.last_seen is not None:
            attrs["last_seen"] = self.typical.last_seen.isoformat()
        return attrs

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_state_listener(self._handle_souliss_update))
        self.async_on_remove(self.client.add_gateway_listener(self._handle_souliss_update))
        self.async_on_remove(self.client.add_structure_listener(self._handle_souliss_update))

    def _handle_souliss_update(self) -> None:
        self.async_write_ha_state()
