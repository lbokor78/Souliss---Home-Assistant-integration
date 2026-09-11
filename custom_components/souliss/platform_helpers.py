"""Dynamic entity helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .protocol import SoulissClient, SoulissTypical


def setup_dynamic_typicals(
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    client: SoulissClient,
    accepts: Callable[[SoulissTypical], bool],
    factory: Callable[[SoulissClient, SoulissTypical], Any | Iterable[Any]],
) -> None:
    """Create one or more entities whenever a matching Typical is discovered."""
    added: set[str] = set()

    def add_item(item: SoulissTypical) -> None:
        if not accepts(item):
            return
        result = factory(client, item)
        entities = list(result) if isinstance(result, (list, tuple, set)) else [result]
        fresh = []
        for entity in entities:
            uid = getattr(entity, "unique_id", None) or getattr(entity, "_attr_unique_id", None)
            if uid is None or uid in added:
                continue
            added.add(uid)
            fresh.append(entity)
        if fresh:
            async_add_entities(fresh)

    for item in list(client.typicals.values()):
        if item.active:
            add_item(item)

    entry.async_on_unload(client.add_discovery_listener(add_item))
