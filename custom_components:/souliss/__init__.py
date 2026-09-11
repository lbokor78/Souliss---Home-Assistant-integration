"""Souliss integration for Home Assistant."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_GATEWAY_PORT, CONF_LOCAL_PORT, CONF_NODE_INDEX, CONF_USER_INDEX,
    DOMAIN, PLATFORMS,
    SERVICE_RAW_FORCE, SERVICE_RAW_MACACO, SERVICE_REDISCOVER, SERVICE_TIMED,
    T1N_TIMED,
)
from .protocol import SoulissClient, SoulissTopic

_LOGGER = logging.getLogger(__name__)


def _client_for_call(hass: HomeAssistant, call: ServiceCall) -> SoulissClient:
    clients: dict[str, SoulissClient] = hass.data[DOMAIN]["clients"]
    entry_id = call.data.get("entry_id")
    if entry_id:
        if entry_id not in clients:
            raise HomeAssistantError(f"Unknown Souliss entry_id: {entry_id}")
        return clients[entry_id]
    if len(clients) != 1:
        raise HomeAssistantError(
            "More than one Souliss Gateway is configured; specify entry_id."
        )
    return next(iter(clients.values()))


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_REDISCOVER):
        return

    async def rediscover(call: ServiceCall) -> None:
        _client_for_call(hass, call).rediscover()

    async def raw_force(call: ServiceCall) -> None:
        client = _client_for_call(hass, call)
        data = bytes.fromhex(str(call.data.get("data", "")).replace("0x", "").replace(",", " "))
        client.send_force(
            int(call.data["node"]),
            int(call.data["slot"]),
            int(call.data["command"]),
            data,
        )

    async def timed(call: ServiceCall) -> None:
        client = _client_for_call(hass, call)
        cycles = int(call.data["cycles"])
        client.send_force(
            int(call.data["node"]),
            int(call.data["slot"]),
            T1N_TIMED + cycles,
        )

    async def raw_macaco(call: ServiceCall) -> None:
        client = _client_for_call(hass, call)
        raw = str(call.data["payload"]).replace("0x", "").replace(",", " ")
        client.send_raw_macaco(bytes.fromhex(raw))

    optional_entry = {vol.Optional("entry_id"): str}

    hass.services.async_register(
        DOMAIN, SERVICE_REDISCOVER, rediscover,
        schema=vol.Schema(optional_entry),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RAW_FORCE, raw_force,
        schema=vol.Schema({
            **optional_entry,
            vol.Required("node"): vol.All(vol.Coerce(int), vol.Range(min=0, max=254)),
            vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=0, max=254)),
            vol.Required("command"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.Optional("data", default=""): str,
        }),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TIMED, timed,
        schema=vol.Schema({
            **optional_entry,
            vol.Required("node"): vol.All(vol.Coerce(int), vol.Range(min=0, max=254)),
            vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=0, max=254)),
            vol.Required("cycles"): vol.All(vol.Coerce(int), vol.Range(min=0, max=15)),
        }),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RAW_MACACO, raw_macaco,
        schema=vol.Schema({
            **optional_entry,
            vol.Required("payload"): str,
        }),
    )


def _cleanup_alpha3_registry_artifacts(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entity-registry artifacts created only by alpha.3.

    Alpha.3 accidentally changed the primary entity unique_id by appending
    `_main`, which duplicated every already existing alpha.2 entity. It also
    created one default timed button for each T11/T12/T16/T19 entity. Alpha.3.1
    restores the stable primary IDs and removes those obsolete registry rows.
    """
    registry = er.async_get(hass)
    remove_ids: list[str] = []

    for reg_entry in registry.entities.values():
        if reg_entry.config_entry_id != entry.entry_id:
            continue
        if reg_entry.platform != DOMAIN:
            continue

        uid = reg_entry.unique_id
        if uid.endswith("_main") or uid.endswith("_sleep_default"):
            remove_ids.append(reg_entry.entity_id)

    for entity_id in remove_ids:
        registry.async_remove(entity_id)

    if remove_ids:
        _LOGGER.info(
            "Removed %s obsolete Souliss alpha.3 registry entities",
            len(remove_ids),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _cleanup_alpha3_registry_artifacts(hass, entry)

    client = SoulissClient(
        host=entry.data[CONF_HOST],
        gateway_port=entry.data[CONF_GATEWAY_PORT],
        local_port=entry.data[CONF_LOCAL_PORT],
        user_index=entry.data[CONF_USER_INDEX],
        node_index=entry.data[CONF_NODE_INDEX],
    )

    try:
        await client.async_start()
    except (OSError, TimeoutError) as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = client
    domain_data = hass.data.setdefault(DOMAIN, {"clients": {}})
    domain_data["clients"][entry.entry_id] = client

    def topic_event(topic: SoulissTopic) -> None:
        hass.bus.async_fire(
            "souliss_action_message",
            {
                "entry_id": entry.entry_id,
                "gateway": client.gateway_ip,
                "topic": topic.topic,
                "topic_hex": f"0x{topic.topic_hex}",
                "variant": topic.variant,
                "variant_hex": f"0x{topic.variant_hex}",
                "value": topic.value,
                "raw": topic.payload.hex(" ").upper(),
            },
        )

    entry.async_on_unload(client.add_topic_listener(topic_event))
    await _async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        client: SoulissClient = entry.runtime_data
        await client.async_close()
        clients = hass.data.get(DOMAIN, {}).get("clients", {})
        clients.pop(entry.entry_id, None)
        if not clients:
            for service in (
                SERVICE_REDISCOVER, SERVICE_RAW_FORCE, SERVICE_TIMED, SERVICE_RAW_MACACO
            ):
                hass.services.async_remove(DOMAIN, service)
            hass.data.pop(DOMAIN, None)
    return unload_ok
