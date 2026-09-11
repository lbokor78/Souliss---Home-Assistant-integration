"""Asynchronous Souliss/MaCaco protocol client."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import socket
import struct
from typing import Any

from .const import (
    FUNC_ACTION_MESSAGE,
    FUNC_DBSTRUCT_REQ,
    FUNC_DBSTRUCT_RESP,
    FUNC_FORCE,
    FUNC_HEALTH_REQ,
    FUNC_HEALTH_RESP,
    FUNC_PING_REQ,
    FUNC_PING_RESP,
    FUNC_POLL_RESP,
    FUNC_SUBSCRIBE_REQ,
    FUNC_SUBSCRIBE_RESP,
    FUNC_TYP_REQ,
    FUNC_TYP_RESP,
    HEALTH_INTERVAL,
    OFFLINE_TIMEOUT,
    PING_INTERVAL,
    REDISCOVERY_INTERVAL,
    SUBSCRIPTION_INTERVAL,
    T16,
    T19,
    T31,
    T51,
    T52,
    T53,
    T54,
    T55,
    T56,
    T57,
    T58,
    T61,
    T62,
    T63,
    T64,
    T65,
    T66,
    T67,
    T68,
    T_EMPTY,
    T_RELATED,
)

_LOGGER = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def half_to_float(data: bytes) -> float | None:
    """Decode Souliss IEEE-754 half precision little-endian value."""
    if len(data) < 2:
        return None
    try:
        return float(struct.unpack("<e", data[:2])[0])
    except (struct.error, OverflowError):
        return None


def float_to_half(value: float) -> bytes:
    """Encode a value as IEEE-754 half precision little-endian."""
    return struct.pack("<e", float(value))


def typical_length(typical: int) -> int:
    """Known state slot length for standard Typicals."""
    if typical == T16:
        return 4
    if typical == T19:
        return 2
    if typical == T31:
        return 5
    if typical in {
        T51, T52, T53, T54, T55, T56, T57, T58,
        T61, T62, T63, T64, T65, T66, T67, T68,
    }:
        return 2
    return 1


@dataclass(slots=True)
class SoulissTypical:
    node: int
    slot: int
    typical: int
    span: int = 1
    payload: bytes = b""
    health: int | None = None
    last_seen: datetime | None = None
    active: bool = True

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.node, self.slot, self.typical)

    @property
    def slot_key(self) -> tuple[int, int]:
        return (self.node, self.slot)

    @property
    def code(self) -> str:
        return f"T{self.typical:02X}"

    @property
    def raw_hex(self) -> str:
        return self.payload.hex(" ").upper() if self.payload else ""

    @property
    def payload_length(self) -> int:
        return max(self.span, typical_length(self.typical))


@dataclass(slots=True)
class SoulissTopic:
    topic: int
    variant: int
    value: float | int | None = None
    payload: bytes = b""
    last_seen: datetime | None = None

    @property
    def key(self) -> tuple[int, int]:
        return (self.topic, self.variant)

    @property
    def topic_hex(self) -> str:
        return f"{self.topic:04X}"

    @property
    def variant_hex(self) -> str:
        return f"{self.variant:02X}"


class _SoulissDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, client: "SoulissClient") -> None:
        self.client = client

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.client._transport = transport  # noqa: SLF001

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.client._datagram_received(data, addr)  # noqa: SLF001

    def error_received(self, exc: Exception) -> None:
        _LOGGER.warning("Souliss UDP error: %s", exc)


class SoulissClient:
    """Souliss Gateway client with live discovery and diagnostics."""

    def __init__(
        self,
        host: str,
        gateway_port: int,
        local_port: int,
        user_index: int,
        node_index: int,
    ) -> None:
        self.host = host
        self.gateway_port = gateway_port
        self.local_port = local_port
        self.user_index = user_index
        self.node_index = node_index

        self.gateway_ip = socket.gethostbyname(host)
        self._transport: asyncio.DatagramTransport | None = None
        self._periodic_task: asyncio.Task[None] | None = None
        self._online_event = asyncio.Event()
        self._closed = False

        self.online = False
        self.nodes = 0
        self.max_typicals_per_node = 24
        self.last_packet: datetime | None = None

        # Keep old/removed Typical objects so their HA entities become unavailable
        # instead of silently disappearing when a network is rebuilt.
        self.typicals: dict[tuple[int, int, int], SoulissTypical] = {}
        self.current_slots: dict[tuple[int, int], tuple[int, int, int]] = {}

        self.node_health: dict[int, int] = {}
        self.node_last_seen: dict[int, datetime] = {}
        self.node_typical_maps: dict[int, list[int]] = {}
        self.topics: dict[tuple[int, int], SoulissTopic] = {}

        self.packet_history: deque[dict[str, Any]] = deque(maxlen=100)
        self.protocol_errors: dict[str, int] = {
            "unsupported_function_0x83": 0,
            "data_out_of_range_0x84": 0,
            "subscription_refused_0x85": 0,
        }
        self.unknown_functions: dict[str, int] = {}

        self._discovery_listeners: list[Callable[[SoulissTypical], None]] = []
        self._state_listeners: list[Callable[[], None]] = []
        self._gateway_listeners: list[Callable[[], None]] = []
        self._structure_listeners: list[Callable[[], None]] = []
        self._topic_listeners: list[Callable[[SoulissTopic], None]] = []

    @property
    def is_online(self) -> bool:
        if not self.online or self.last_packet is None:
            return False
        return utcnow() - self.last_packet < timedelta(seconds=OFFLINE_TIMEOUT)

    def typical_available(self, item: SoulissTypical) -> bool:
        if not self.is_online or not item.active:
            return False
        if item.last_seen is None:
            return True
        return utcnow() - item.last_seen < timedelta(seconds=OFFLINE_TIMEOUT * 2)

    async def async_start(self, timeout: float = 4.0) -> None:
        loop = asyncio.get_running_loop()
        try:
            await loop.create_datagram_endpoint(
                lambda: _SoulissDatagramProtocol(self),
                local_addr=("0.0.0.0", self.local_port),
                allow_broadcast=True,
            )
        except OSError:
            _LOGGER.exception("Unable to bind Souliss UDP local port %s", self.local_port)
            raise

        self.send_ping()
        self.send_dbstruct()

        try:
            await asyncio.wait_for(self._online_event.wait(), timeout=timeout)
        except TimeoutError as err:
            await self.async_close()
            raise TimeoutError(
                f"Souliss Gateway {self.gateway_ip}:{self.gateway_port} did not answer"
            ) from err

        self._periodic_task = asyncio.create_task(self._periodic_loop())

    async def async_close(self) -> None:
        self._closed = True
        if self._periodic_task:
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
            self._periodic_task = None
        if self._transport:
            self._transport.close()
            self._transport = None

    async def _periodic_loop(self) -> None:
        elapsed = 0
        while not self._closed:
            await asyncio.sleep(5)
            elapsed += 5

            was_online = self.online
            if self.last_packet and utcnow() - self.last_packet >= timedelta(seconds=OFFLINE_TIMEOUT):
                self.online = False
            if self.online != was_online:
                self._notify_gateway()
                self._notify_state()

            if elapsed % PING_INTERVAL == 0:
                self.send_ping()
            if self.nodes and elapsed % SUBSCRIPTION_INTERVAL == 0:
                self.send_subscription()
            if self.nodes and elapsed % HEALTH_INTERVAL == 0:
                self.send_health()
            if elapsed % REDISCOVERY_INTERVAL == 0:
                self.rediscover()

    def add_discovery_listener(self, callback: Callable[[SoulissTypical], None]) -> Callable[[], None]:
        self._discovery_listeners.append(callback)
        return lambda: self._remove(self._discovery_listeners, callback)

    def add_state_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._state_listeners.append(callback)
        return lambda: self._remove(self._state_listeners, callback)

    def add_gateway_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._gateway_listeners.append(callback)
        return lambda: self._remove(self._gateway_listeners, callback)

    def add_structure_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._structure_listeners.append(callback)
        return lambda: self._remove(self._structure_listeners, callback)

    def add_topic_listener(self, callback: Callable[[SoulissTopic], None]) -> Callable[[], None]:
        self._topic_listeners.append(callback)
        return lambda: self._remove(self._topic_listeners, callback)

    @staticmethod
    def _remove(items: list, callback: Callable) -> None:
        if callback in items:
            items.remove(callback)

    def _notify_state(self) -> None:
        for callback in list(self._state_listeners):
            callback()

    def _notify_gateway(self) -> None:
        for callback in list(self._gateway_listeners):
            callback()

    def _notify_structure(self) -> None:
        for callback in list(self._structure_listeners):
            callback()

    def _record_packet(
        self, direction: str, data: bytes, addr: tuple[str, int] | None = None
    ) -> None:
        func = None
        if direction == "rx" and len(data) > 7:
            func = data[7]
        elif direction == "tx" and len(data) > 7:
            func = data[7]
        self.packet_history.append(
            {
                "time": utcnow().isoformat(),
                "direction": direction,
                "function": f"0x{func:02X}" if func is not None else None,
                "peer": f"{addr[0]}:{addr[1]}" if addr else f"{self.gateway_ip}:{self.gateway_port}",
                "raw": data.hex(" ").upper(),
            }
        )

    def _build_vnet_frame(self, macaco: bytes) -> bytes:
        ip = socket.inet_aton(self.gateway_ip)
        header = bytearray(
            [0, 0, 23, ip[3], 0, self.node_index & 0xFF, self.user_index & 0xFF]
        )
        total_len = len(header) + len(macaco)
        header[0] = total_len & 0xFF
        header[1] = (total_len - 1) & 0xFF
        return bytes(header) + macaco

    def _send_macaco(self, macaco: bytes) -> None:
        if not self._transport:
            return
        frame = self._build_vnet_frame(macaco)
        self._record_packet("tx", frame)
        _LOGGER.debug(
            "Souliss TX %s:%s %s",
            self.gateway_ip,
            self.gateway_port,
            frame.hex(" ").upper(),
        )
        self._transport.sendto(frame, (self.gateway_ip, self.gateway_port))

    def send_raw_macaco(self, payload: bytes) -> None:
        """Advanced/debug: send a complete MaCaco payload inside our VNet frame."""
        self._send_macaco(payload)

    def send_ping(self) -> None:
        self._send_macaco(bytes([FUNC_PING_REQ, 0, 0, 0, 0]))

    def send_dbstruct(self) -> None:
        self._send_macaco(bytes([FUNC_DBSTRUCT_REQ, 0, 0, 0, 0]))

    def rediscover(self) -> None:
        _LOGGER.info("Souliss network rediscovery requested")
        self.send_dbstruct()
        if self.nodes:
            self.send_typical_request()

    def send_typical_request(self, start_node: int = 0, nodes: int | None = None) -> None:
        count = self.nodes if nodes is None else nodes
        if count:
            self._send_macaco(bytes([FUNC_TYP_REQ, 0, 0, start_node & 0xFF, count & 0xFF]))

    def send_subscription(self) -> None:
        if self.nodes:
            self._send_macaco(bytes([FUNC_SUBSCRIBE_REQ, 0, 0, 0, self.nodes & 0xFF]))

    def send_health(self) -> None:
        if self.nodes:
            self._send_macaco(bytes([FUNC_HEALTH_REQ, 0, 0, 0, self.nodes & 0xFF]))

    def send_force(self, node: int, slot: int, command: int, extra: bytes = b"") -> None:
        payload = (b"\x00" * slot) + bytes([command & 0xFF]) + extra
        macaco = bytes([FUNC_FORCE, 0, 0, node & 0xFF, len(payload) & 0xFF]) + payload
        self._send_macaco(macaco)

    def send_half_setpoint(self, node: int, slot: int, value: float) -> None:
        payload = (b"\x00" * slot) + float_to_half(value)
        macaco = bytes([FUNC_FORCE, 0, 0, node & 0xFF, len(payload) & 0xFF]) + payload
        self._send_macaco(macaco)

    def send_t31_setpoint(self, node: int, slot: int, command: int, value: float) -> None:
        payload = (b"\x00" * slot) + bytes([command & 0xFF, 0x00, 0x00]) + float_to_half(value)
        macaco = bytes([FUNC_FORCE, 0, 0, node & 0xFF, len(payload) & 0xFF]) + payload
        self._send_macaco(macaco)

    def _datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if len(data) < 8:
            return

        self._record_packet("rx", data, addr)
        _LOGGER.debug("Souliss RX %s:%s %s", addr[0], addr[1], data.hex(" ").upper())
        self.last_packet = utcnow()

        macaco = data[7:]
        if not macaco:
            return

        func = macaco[0]

        if not self.online:
            self.online = True
            self._online_event.set()
            self._notify_gateway()

        if func == FUNC_PING_RESP:
            return

        if func == FUNC_DBSTRUCT_RESP:
            if len(macaco) >= 8:
                old = (self.nodes, self.max_typicals_per_node)
                self.nodes = macaco[5]
                self.max_typicals_per_node = macaco[7] or 24
                for node in range(self.nodes):
                    self.node_health.setdefault(node, -1)
                _LOGGER.info(
                    "Souliss DB structure: nodes=%s, slots_per_node=%s",
                    self.nodes,
                    self.max_typicals_per_node,
                )
                if old != (self.nodes, self.max_typicals_per_node):
                    self._notify_structure()
                if self.nodes:
                    self.send_typical_request()
            return

        if func == FUNC_TYP_RESP:
            self._decode_typicals(macaco)
            self.send_subscription()
            self.send_health()
            return

        if func in (FUNC_SUBSCRIBE_RESP, FUNC_POLL_RESP):
            self._decode_state(macaco)
            return

        if func == FUNC_HEALTH_RESP:
            self._decode_health(macaco)
            return

        if func == FUNC_ACTION_MESSAGE:
            self._decode_action_message(macaco)
            return

        if func == 0x83:
            self.protocol_errors["unsupported_function_0x83"] += 1
            _LOGGER.warning("Souliss Gateway returned unsupported function (0x83)")
            return
        if func == 0x84:
            self.protocol_errors["data_out_of_range_0x84"] += 1
            _LOGGER.warning("Souliss Gateway returned data out of range (0x84)")
            return
        if func == 0x85:
            self.protocol_errors["subscription_refused_0x85"] += 1
            _LOGGER.warning("Souliss Gateway refused subscription (0x85)")
            return

        key = f"0x{func:02X}"
        self.unknown_functions[key] = self.unknown_functions.get(key, 0) + 1
        _LOGGER.debug("Souliss function %s is not natively decoded", key)

    def _decode_typicals(self, macaco: bytes) -> None:
        if len(macaco) < 5:
            return

        target_node = macaco[3]
        number_of = macaco[4]
        raw = list(macaco[5 : 5 + min(number_of, max(0, len(macaco) - 5))])
        if not raw:
            return

        covered_nodes: set[int] = set()
        new_slot_keys: set[tuple[int, int, int]] = set()

        # Store the full returned Typical map per covered node.
        for offset in range(0, len(raw), self.max_typicals_per_node):
            node = target_node + (offset // self.max_typicals_per_node)
            segment = raw[offset : offset + self.max_typicals_per_node]
            covered_nodes.add(node)
            self.node_typical_maps[node] = segment + [0] * (
                self.max_typicals_per_node - len(segment)
            )

        for j, typical in enumerate(raw):
            slot = j % self.max_typicals_per_node
            node = j // self.max_typicals_per_node + target_node
            if typical in (T_EMPTY, T_RELATED):
                continue

            # Infer the occupied slot span from following T_RELATED markers.
            span = 1
            k = j + 1
            while (
                k < len(raw)
                and (k // self.max_typicals_per_node) == (j // self.max_typicals_per_node)
                and raw[k] == T_RELATED
            ):
                span += 1
                k += 1

            key = (node, slot, typical)
            new_slot_keys.add(key)

            current_key = self.current_slots.get((node, slot))
            if current_key and current_key != key:
                old = self.typicals.get(current_key)
                if old:
                    old.active = False

            item = self.typicals.get(key)
            if item is None:
                item = SoulissTypical(node=node, slot=slot, typical=typical, span=span)
                self.typicals[key] = item
                _LOGGER.info(
                    "Souliss Typical discovered: %s node=%s slot=%s span=%s",
                    item.code, node, slot, span,
                )
                for callback in list(self._discovery_listeners):
                    callback(item)
            else:
                item.span = span
                item.active = True

            self.current_slots[(node, slot)] = key

        # Typicals that disappeared inside nodes included in this response are
        # retained for HA registry stability, but become unavailable.
        for key, item in self.typicals.items():
            if item.node in covered_nodes and item.active and key not in new_slot_keys:
                if self.current_slots.get(item.slot_key) == key:
                    item.active = False
                    self.current_slots.pop(item.slot_key, None)

        self._notify_structure()
        self._notify_state()

    def _decode_state(self, macaco: bytes) -> None:
        if len(macaco) < 5:
            return

        node = macaco[3]
        number_of = macaco[4]
        node_payload = macaco[5 : 5 + number_of]
        now = utcnow()
        self.node_last_seen[node] = now
        changed = False

        for item in self.typicals.values():
            if item.node != node or not item.active:
                continue
            if item.slot >= len(node_payload):
                continue
            payload = bytes(node_payload[item.slot : item.slot + item.payload_length])
            if not payload:
                continue
            if item.payload != payload:
                item.payload = payload
                changed = True
            item.last_seen = now
            if node in self.node_health:
                item.health = self.node_health[node]

        if changed:
            self._notify_state()
        else:
            # last_seen/availability is also meaningful state.
            self._notify_state()

    def _decode_health(self, macaco: bytes) -> None:
        if len(macaco) < 5:
            return
        target_node = macaco[3]
        number_of = macaco[4]
        payload = macaco[5 : 5 + number_of]
        changed = False
        for offset, health in enumerate(payload):
            node = target_node + offset
            if self.node_health.get(node) != health:
                self.node_health[node] = health
                changed = True
            for item in self.typicals.values():
                if item.node == node and item.health != health:
                    item.health = health
                    changed = True
        if changed:
            self._notify_structure()
            self._notify_state()

    def _decode_action_message(self, macaco: bytes) -> None:
        # Current Souliss/openHAB format:
        # [0]=0x72, [1..2]=16-bit topic number little endian,
        # [3]=variant, [4]=payload length, [5..]=payload.
        if len(macaco) < 5:
            return
        topic_number = ((macaco[2] & 0xFF) << 8) | (macaco[1] & 0xFF)
        variant = macaco[3] & 0xFF
        length = macaco[4] & 0xFF
        payload = bytes(macaco[5 : 5 + length])

        value: float | int | None = None
        if length == 1 and payload:
            value = payload[0]
        elif length == 2:
            value = half_to_float(payload)

        key = (topic_number, variant)
        topic = self.topics.get(key)
        is_new = topic is None
        if topic is None:
            topic = SoulissTopic(topic=topic_number, variant=variant)
            self.topics[key] = topic
        topic.value = value
        topic.payload = payload
        topic.last_seen = utcnow()

        _LOGGER.info(
            "Souliss Action Message: topic=0x%04X variant=0x%02X value=%s",
            topic_number, variant, value,
        )
        for callback in list(self._topic_listeners):
            callback(topic)
        if is_new:
            self._notify_structure()


async def async_probe(
    host: str,
    gateway_port: int,
    user_index: int,
    node_index: int,
    timeout: float = 3.0,
) -> bool:
    gateway_ip = socket.gethostbyname(host)
    loop = asyncio.get_running_loop()
    response = asyncio.Event()

    class ProbeProtocol(asyncio.DatagramProtocol):
        def connection_made(self, transport: asyncio.BaseTransport) -> None:
            ip = socket.inet_aton(gateway_ip)
            macaco = bytes([FUNC_PING_REQ, 0, 0, 0, 0])
            header = bytearray([0, 0, 23, ip[3], 0, node_index & 0xFF, user_index & 0xFF])
            total_len = len(header) + len(macaco)
            header[0] = total_len
            header[1] = total_len - 1
            transport.sendto(bytes(header) + macaco, (gateway_ip, gateway_port))  # type: ignore[attr-defined]

        def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
            if len(data) >= 8 and data[7] == FUNC_PING_RESP:
                response.set()

    transport: asyncio.DatagramTransport | None = None
    try:
        transport, _ = await loop.create_datagram_endpoint(
            ProbeProtocol,
            local_addr=("0.0.0.0", 0),
        )
        await asyncio.wait_for(response.wait(), timeout=timeout)
        return True
    except (TimeoutError, OSError, socket.gaierror):
        return False
    finally:
        if transport:
            transport.close()
