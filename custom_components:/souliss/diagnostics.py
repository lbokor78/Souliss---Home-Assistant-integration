"""Diagnostics support for Souliss."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import TYPICAL_NAMES
from .protocol import SoulissClient


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    client: SoulissClient = entry.runtime_data

    nodes = []
    for node in range(client.nodes):
        active = sorted(
            (i for i in client.typicals.values() if i.active and i.node == node),
            key=lambda x: x.slot,
        )
        nodes.append({
            "node": node,
            "health_raw": client.node_health.get(node),
            "last_state_packet": (
                client.node_last_seen[node].isoformat()
                if node in client.node_last_seen else None
            ),
            "typical_map": [
                f"{v:02X}" for v in client.node_typical_maps.get(node, [])
            ],
            "active_typicals": len(active),
        })

    return {
        "gateway": {
            "host": client.gateway_ip,
            "gateway_port": client.gateway_port,
            "local_port": client.local_port,
            "user_index": client.user_index,
            "node_index": client.node_index,
            "online": client.is_online,
            "nodes": client.nodes,
            "max_typicals_per_node": client.max_typicals_per_node,
            "last_packet": client.last_packet.isoformat() if client.last_packet else None,
        },
        "nodes": nodes,
        "typicals": [
            {
                "node": item.node,
                "slot": item.slot,
                "typical": item.code,
                "typical_name": TYPICAL_NAMES.get(item.typical, "Unknown/Custom"),
                "span": item.span,
                "active": item.active,
                "raw": item.raw_hex,
                "health_raw": item.health,
                "last_seen": item.last_seen.isoformat() if item.last_seen else None,
            }
            for item in sorted(client.typicals.values(), key=lambda x: (x.node, x.slot, x.typical))
        ],
        "action_messages": [
            {
                "topic": f"0x{topic.topic_hex}",
                "variant": f"0x{topic.variant_hex}",
                "value": topic.value,
                "raw": topic.payload.hex(" ").upper(),
                "last_seen": topic.last_seen.isoformat() if topic.last_seen else None,
            }
            for topic in sorted(client.topics.values(), key=lambda x: (x.topic, x.variant))
        ],
        "protocol_errors": dict(client.protocol_errors),
        "unknown_functions": dict(client.unknown_functions),
        "packet_history_last_100": list(client.packet_history),
    }
