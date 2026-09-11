"""Sensor and diagnostic platform for Souliss."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, EntityCategory,
    UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfPower,
    UnitOfPressure, UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, NATIVE_PLATFORM_TYPICALS, SUPPORTED_SENSOR_TYPICALS,
    T51, T52, T53, T54, T55, T56, T57, T58, TYPICAL_NAMES,
)
from .entity import SoulissEntity
from .platform_helpers import setup_dynamic_typicals
from .protocol import SoulissClient, SoulissTopic, half_to_float

SENSOR_META = {
    T51: (None, None, 1.0),
    T52: (SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, 1.0),
    T53: (SensorDeviceClass.HUMIDITY, PERCENTAGE, 1.0),
    T54: (SensorDeviceClass.ILLUMINANCE, "lx", 1000.0),
    T55: (SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, 1.0),
    T56: (SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, 1.0),
    T57: (SensorDeviceClass.POWER, UnitOfPower.WATT, 1.0),
    T58: (SensorDeviceClass.PRESSURE, UnitOfPressure.HPA, 1.0),
}


class SoulissGatewaySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Connection"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: SoulissClient) -> None:
        self.client = client
        self._attr_unique_id = f"{client.gateway_ip}_gateway_connection"

    @property
    def native_value(self) -> str:
        return "connected" if self.client.is_online else "disconnected"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.client.gateway_ip}-gateway")},
            manufacturer="Souliss",
            model="Souliss Gateway",
            name=f"Souliss Gateway {self.client.gateway_ip}",
        )

    @property
    def extra_state_attributes(self):
        return {
            "host": self.client.gateway_ip,
            "gateway_port": self.client.gateway_port,
            "local_port": self.client.local_port,
            "user_index": self.client.user_index,
            "node_index": self.client.node_index,
            "nodes": self.client.nodes,
            "slots_per_node": self.client.max_typicals_per_node,
            "active_typicals": sum(1 for i in self.client.typicals.values() if i.active),
            "topics": len(self.client.topics),
            "last_packet": self.client.last_packet.isoformat() if self.client.last_packet else None,
            "protocol_errors": dict(self.client.protocol_errors),
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_gateway_listener(self._handle))
        self.async_on_remove(self.client.add_state_listener(self._handle))
        self.async_on_remove(self.client.add_structure_listener(self._handle))

    def _handle(self) -> None:
        self.async_write_ha_state()


class SoulissNodeHealthSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Health"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: SoulissClient, node: int) -> None:
        self.client = client
        self.node = node
        self._attr_unique_id = f"{client.gateway_ip}_node_{node}_health"

    @property
    def native_value(self) -> int | None:
        value = self.client.node_health.get(self.node)
        return None if value is None or value < 0 else value

    @property
    def available(self) -> bool:
        return self.client.is_online

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.client.gateway_ip}-node-{self.node}")},
            manufacturer="Souliss",
            model="Souliss Node",
            name=f"Souliss Node {self.node}",
            via_device=(DOMAIN, f"{self.client.gateway_ip}-gateway"),
        )

    @property
    def extra_state_attributes(self):
        active = [i for i in self.client.typicals.values() if i.active and i.node == self.node]
        return {
            "node": self.node,
            "active_typicals": len(active),
            "last_state_packet": (
                self.client.node_last_seen[self.node].isoformat()
                if self.node in self.client.node_last_seen else None
            ),
            "typical_map": " ".join(
                f"{v:02X}" for v in self.client.node_typical_maps.get(self.node, [])
            ),
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_state_listener(self._handle))
        self.async_on_remove(self.client.add_structure_listener(self._handle))
        self.async_on_remove(self.client.add_gateway_listener(self._handle))

    def _handle(self) -> None:
        self.async_write_ha_state()


class SoulissAnalogSensor(SoulissEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client, typical) -> None:
        super().__init__(client, typical)
        device_class, unit, _scale = SENSOR_META[typical.typical]
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float | None:
        value = half_to_float(self.typical.payload)
        if value is None:
            return None
        _device_class, _unit, scale = SENSOR_META[self.typical.typical]
        return round(value * scale, 4)


class SoulissRawTypicalSensor(SoulissEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        return self.typical.raw_hex or None

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        attrs["decoder_status"] = "raw_fallback"
        attrs["known_name"] = TYPICAL_NAMES.get(self.typical.typical, "Unknown/Custom")
        return attrs


class SoulissTopicSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, client: SoulissClient, topic: SoulissTopic) -> None:
        self.client = client
        self.topic = topic
        self._attr_name = f"Topic {topic.topic_hex} Variant {topic.variant_hex}"
        self._attr_unique_id = f"{client.gateway_ip}_topic_{topic.topic_hex}_{topic.variant_hex}"

    @property
    def native_value(self):
        return self.topic.value

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.client.gateway_ip}-topics")},
            manufacturer="Souliss",
            model="Action Messages",
            name="Souliss Topics",
            via_device=(DOMAIN, f"{self.client.gateway_ip}-gateway"),
        )

    @property
    def extra_state_attributes(self):
        return {
            "topic": self.topic.topic,
            "topic_hex": f"0x{self.topic.topic_hex}",
            "variant": self.topic.variant,
            "variant_hex": f"0x{self.topic.variant_hex}",
            "raw": self.topic.payload.hex(" ").upper(),
            "last_seen": self.topic.last_seen.isoformat() if self.topic.last_seen else None,
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_topic_listener(self._handle_topic))

    def _handle_topic(self, topic: SoulissTopic) -> None:
        if topic.key == self.topic.key:
            self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    client: SoulissClient = entry.runtime_data
    async_add_entities([SoulissGatewaySensor(client)])

    # Node health entities are useful even for empty/broken nodes during a rebuild.
    node_added: set[int] = set()
    def add_nodes() -> None:
        fresh = []
        for node in range(client.nodes):
            if node not in node_added:
                node_added.add(node)
                fresh.append(SoulissNodeHealthSensor(client, node))
        if fresh:
            async_add_entities(fresh)
    add_nodes()
    entry.async_on_unload(client.add_structure_listener(add_nodes))

    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical in SUPPORTED_SENSOR_TYPICALS,
        SoulissAnalogSensor,
    )

    setup_dynamic_typicals(
        entry, async_add_entities, client,
        lambda item: item.typical not in NATIVE_PLATFORM_TYPICALS,
        SoulissRawTypicalSensor,
    )

    topic_added: set[tuple[int, int]] = set()
    def add_topic(topic: SoulissTopic) -> None:
        if topic.key in topic_added:
            return
        topic_added.add(topic.key)
        async_add_entities([SoulissTopicSensor(client, topic)])
    for topic in client.topics.values():
        add_topic(topic)
    entry.async_on_unload(client.add_topic_listener(add_topic))
