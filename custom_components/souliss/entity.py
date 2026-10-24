"""Base entities for Souliss."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, TYPICAL_NAMES
from .protocol import SoulissClient, SoulissTypical


def gateway_via(hass: HomeAssistant | None, gateway_ip: str) -> dict:
    """Return the Gateway device's registry id as `via_device_id`.

    Since Home Assistant 2026 the `via_device=(DOMAIN, ...)` identifier pair is
    deprecated: after editing an entity in the registry, re-adding it raised an
    error and the entity did not load. If the Gateway device is not in the
    registry yet (first start), the parent link is skipped and added on the next
    start.
    """
    if hass is None:
        return {}
    dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, f"{gateway_ip}-gateway")})
    return {"via_device_id": dev.id} if dev else {}


def write_if_changed(entity: Entity) -> None:
    """Write the state only when something really changed.

    The client calls every listener on every packet (~14 s). Here the entity compares
    availability, state and attributes with what it wrote last; if nothing changed, the
    previous value stays and nothing is written (no state_changed / state_reported, no
    recorder row). A failure while building the snapshot falls back to a plain write.
    """
    try:
        available = entity.available
        snapshot = (
            available,
            entity.state,
            (entity.capability_attributes, entity.state_attributes, entity.extra_state_attributes)
            if available else None,
        )
    except Exception:  # noqa: BLE001 – never lose an update because of the comparison
        entity.async_write_ha_state()
        return
    if snapshot == getattr(entity, "_souliss_written", None):
        return
    entity._souliss_written = snapshot
    entity.async_write_ha_state()


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
            **gateway_via(self.hass, self.client.gateway_ip),
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
        # No last_seen / health_raw here: last_seen changed on every packet (~14 s), so every entity wrote a
        # recorder row without any real change. Health is on the node's Health sensor; both stay in the
        # diagnostics download, and availability still uses last_seen.
        return attrs

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_state_listener(self._handle_souliss_update))
        self.async_on_remove(self.client.add_gateway_listener(self._handle_souliss_update))
        self.async_on_remove(self.client.add_structure_listener(self._handle_souliss_update))

    def _handle_souliss_update(self) -> None:
        write_if_changed(self)
