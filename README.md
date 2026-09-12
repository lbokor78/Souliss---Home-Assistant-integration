# Souliss for Home Assistant

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-41BDF5?logo=homeassistant&logoColor=white)
![Souliss](https://img.shields.io/badge/Souliss-MaCaco%20%2F%20VNet-informational)
![Status](https://img.shields.io/badge/status-alpha-orange)
![Communication](https://img.shields.io/badge/communication-local%20UDP-success)

A native, local Home Assistant integration for **Souliss** smart-home networks.

It communicates directly with a Souliss Gateway over UDP, discovers Souliss nodes and Typicals, and exposes them as Home Assistant entities without requiring openHAB, MQTT, or another bridge in between.

> [!IMPORTANT]
> This is an **independent, unofficial community project**.  
> It is **not affiliated with, endorsed by, or maintained by the Souliss project or Home Assistant**.

---

## Why this project exists

This integration was created out of practical necessity.

My home has been running on **Souliss for many years**, and the system has proven to be extremely stable. It is a distributed installation built around Arduino-compatible nodes, with local logic that continues to work independently of any central home-automation server.

When moving the higher-level home automation and user interface to Home Assistant, there was no current native Souliss integration available.

Replacing a stable, working Souliss installation simply because the new frontend did not support it made little sense.

So this project was created to let an existing Souliss network become a first-class citizen in Home Assistant while keeping the underlying Souliss architecture intact.

The goal is not to replace Souliss.

The goal is to **connect Souliss and Home Assistant cleanly and directly**.

---

## Project status

This project is currently **alpha software**.

The core communication path has been tested on a real installation using:

- Home Assistant OS
- Home Assistant 2026.9.x
- a physical Souliss Gateway
- a multi-node Souliss database
- real T11 outputs

The following have been confirmed on real hardware:

- direct UDP communication with the Souliss Gateway
- Gateway ping
- DB structure discovery
- Typical discovery
- subscription/state updates
- T11 state feedback
- T11 commands from Home Assistant
- automatic Home Assistant device/entity creation
- diagnostics
- network rediscovery

Support for the wider set of Souliss Typicals is implemented from the public Souliss protocol behaviour and the current openHAB Souliss binding, but not every Typical has yet been validated on physical hardware.

**Feedback and real-world testing are very welcome.**

---

## Architecture

```text
                         Home Assistant
                               │
                               │  UDP / Souliss protocol
                               │
                               ▼
                     ┌───────────────────┐
                     │  Souliss Gateway  │
                     └───────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
             Node 0         Node 1         Node 2 ...
             Arduino        Arduino        Arduino
                │              │              │
          lights / I/O     sensors       HVAC / covers
```

The physical Souliss network can use technologies such as Ethernet, Wi-Fi, wireless links, or RS-485 behind the Gateway.

Home Assistant interacts with the **logical Souliss network exposed by the Gateway**.

---

## Main features

- Direct local communication with a Souliss Gateway
- No cloud dependency
- No MQTT bridge required
- No openHAB installation required
- Home Assistant Config Flow
- Automatic DBSTRUCT discovery
- Automatic Souliss Typical discovery
- Home Assistant devices grouped by Souliss node
- Automatic state subscriptions
- Periodic health requests
- Automatic network rediscovery
- Manual **Rediscover network** button
- Support for Action Messages / Topics
- Raw fallback for unknown or legacy Typicals
- Detailed integration diagnostics
- Last 100 TX/RX protocol packets retained for troubleshooting
- Raw protocol tools for advanced debugging
- Existing entities remain stable during network rebuilds where possible

---

## Supported Souliss Typicals

The integration currently maps the following standard Souliss Typicals.

| Souliss Typical | Function | Home Assistant representation |
|---|---|---|
| `T11` | ON/OFF digital output + timer | `switch` |
| `T12` | ON/OFF digital output + AUTO | `switch` + AUTO switch |
| `T13` | Digital input | `binary_sensor` |
| `T14` | Pulse digital output | `button` |
| `T16` | RGB LED | `light` |
| `T18` | ON/OFF digital output | `switch` |
| `T19` | Single-color dimmable LED | `light` |
| `T1A` | 8-bit digital input pass-through | 8 × `binary_sensor` |
| `T21` | Motorized device | `cover` |
| `T22` | Motorized device with intermediate state | `cover` |
| `T31` | Temperature controller | `climate` |
| `T41` | Anti-theft main controller | `alarm_control_panel` |
| `T42` | Anti-theft peer | `binary_sensor` |
| `T51` | Generic analog input | `sensor` |
| `T52` | Temperature | `sensor` |
| `T53` | Humidity | `sensor` |
| `T54` | Illuminance | `sensor` |
| `T55` | Voltage | `sensor` |
| `T56` | Current | `sensor` |
| `T57` | Power | `sensor` |
| `T58` | Pressure | `sensor` |
| `T61`–`T68` | Analog/setpoint variants | `number` |
| Action Message / Topic | Souliss network message | dynamic `sensor` + HA event |

### Unknown and legacy Typicals

Unknown or currently unsupported Typicals are **not discarded**.

The integration keeps:

- node
- slot
- Typical code
- inferred slot span
- raw state bytes
- health value
- last-seen time

and exposes a diagnostic entity where possible.

This is intentional: old Souliss installations may contain legacy Typicals or custom firmware, and retaining the raw information makes later support and troubleshooting possible.

---

## Requirements

You need an already functioning Souliss network with at least:

1. one Souliss node configured as a **Gateway**
2. Ethernet or Wi-Fi connectivity between Home Assistant and that Gateway
3. a known Gateway IP address
4. UDP communication allowed between Home Assistant and the Gateway

A good first check is to confirm that the Gateway works with **SoulissApp** or another known Souliss user interface.

The standard Souliss Gateway UDP port is:

```text
230
```

---

## Installation

### Manual installation

1. Download or clone this repository.

2. Copy:

```text
custom_components/souliss
```

to your Home Assistant configuration directory:

```text
/config/custom_components/souliss
```

The final structure should look similar to:

```text
/config/
└── custom_components/
    └── souliss/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        ├── protocol.py
        ├── entity.py
        ├── switch.py
        ├── sensor.py
        ├── binary_sensor.py
        ├── light.py
        ├── cover.py
        ├── climate.py
        ├── alarm_control_panel.py
        ├── number.py
        ├── button.py
        ├── diagnostics.py
        ├── services.yaml
        └── translations/
```

3. Restart Home Assistant.

4. Open:

```text
Settings → Devices & services → Add integration
```

5. Search for:

```text
Souliss
```

6. Enter the Gateway configuration.

---

## Configuration

The setup dialog asks for:

| Setting | Description | Typical value |
|---|---|---:|
| Gateway IP | IP address of the Souliss Gateway | `192.168.1.10` |
| Gateway UDP port | Souliss Gateway port | `230` |
| Local UDP port | UDP port used by this HA integration | `23000` |
| `USER_INDEX` | Souliss user-interface identifier | `71` |
| `NODE_INDEX` | Souliss user-interface node identifier | `121` |

### USER_INDEX and NODE_INDEX

Every Souliss user interface must use its own identification values.

For example, if you use:

- SoulissApp
- openHAB
- Home Assistant

at the same time, they should **not use the same `USER_INDEX` / `NODE_INDEX` pair**.

This is normal Souliss behaviour and is not specific to this integration.

---

## Discovery

After connection, the integration requests the Souliss database structure and discovers Typicals automatically.

A discovered entity initially uses a technical name such as:

```text
T11 N0 S4
```

which means:

```text
Typical: T11
Node:    0
Slot:    4
```

You can freely rename the entity in Home Assistant to something meaningful such as:

```text
Kitchen ceiling light
```

The underlying Souliss node/slot addressing remains unchanged.

---

## Devices in Home Assistant

The Gateway is represented as a Home Assistant device:

```text
Souliss Gateway <IP>
```

Souliss nodes are represented separately:

```text
Souliss Node 0
Souliss Node 1
Souliss Node 2
...
```

This separation is useful for diagnostics even when one physical Souliss node serves devices located in several rooms.

For normal Home Assistant use, it is usually better to assign the individual entities to Home Assistant **Areas** rather than assigning the complete Souliss node to a room.

---

## Network rediscovery

The integration periodically rechecks the Souliss network.

A manual button is also available on the Gateway device:

```text
Rediscover network
```

There is also a Home Assistant action:

```yaml
action: souliss.rediscover
```

This is useful when:

- adding a new node
- moving a node from RS-485 to Ethernet
- changing Typical assignments
- rebuilding an older Souliss installation
- bringing an offline node back online

If a previously known Typical disappears, the integration prefers to keep its Home Assistant entity unavailable instead of immediately destroying its registry identity.

---

## Health diagnostics

Every Souliss node reported by DBSTRUCT gets a diagnostic health entity.

The value is currently deliberately exposed as the **raw Souliss health byte**.

Example:

```text
255
```

It is **not converted to a percentage**, because doing so without a fully verified definition of the Souliss health algorithm would be misleading.

Additional attributes include:

- node number
- active Typical count
- last state packet
- raw Typical map

---

## Diagnostics

Home Assistant diagnostics can be downloaded from:

```text
Settings
→ Devices & services
→ Souliss
→ ⋮
→ Download diagnostics
```

Diagnostics include:

- Gateway parameters
- connection state
- number of nodes
- slots per node
- node health
- node Typical maps
- all discovered Typicals
- active/inactive state
- raw payloads
- Action Messages
- protocol error counters
- unknown function codes
- last 100 TX/RX packets

This information is especially useful when reporting a problem.

---

## Debug logging

Add the following to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.souliss: debug
```

Useful log entries include:

```text
Souliss TX
Souliss RX
Souliss DB structure
Souliss Typical discovered
Souliss Action Message
```

When reporting protocol problems, please provide both:

1. the relevant debug log
2. the downloaded Souliss diagnostics file

---

## Home Assistant actions

### Rediscover the network

```yaml
action: souliss.rediscover
```

### T1n timed command

```yaml
action: souliss.timed
data:
  node: 0
  slot: 4
  cycles: 5
```

### Advanced RAW FORCE

```yaml
action: souliss.raw_force
data:
  node: 0
  slot: 4
  command: 34
  data: "FF 00 80"
```

### RAW MaCaco payload

```yaml
action: souliss.raw_macaco
data:
  payload: "08 00 00 00 00"
```

> [!CAUTION]
> `raw_force` and `raw_macaco` are expert/debug tools.  
> Incorrect commands may operate real outputs or produce unexpected behaviour. Use them only when you understand the target Souliss command.

---

## Action Messages / Topics

Souliss Action Messages are exposed in two ways:

1. as dynamically discovered Topic sensors
2. as a Home Assistant event:

```text
souliss_action_message
```

The event contains information such as:

```yaml
gateway: 192.168.1.10
topic: 4660
topic_hex: "0x1234"
variant: 2
variant_hex: "0x02"
value: 24.5
raw: "20 4E"
```

This allows Souliss network events to be used directly in Home Assistant automations.

---

## Updating

For manual installations:

1. replace the contents of:

```text
/config/custom_components/souliss/
```

with the newer version

2. restart Home Assistant

The integration is designed to preserve entity unique IDs whenever possible so dashboard and automation references remain stable across updates.

Always review release notes before installing a newer alpha version.

---

## Troubleshooting

### The integration cannot connect

Check:

- Gateway IP address
- UDP port `230`
- Home Assistant and Gateway are on reachable networks
- firewall/VLAN rules allow UDP traffic
- the Gateway responds to SoulissApp
- `USER_INDEX` / `NODE_INDEX` do not conflict with another Souliss UI

### The Gateway connects but no entities appear

Try:

```text
Souliss Gateway → Rediscover network
```

Then download diagnostics and check:

- reported number of nodes
- Typical map
- RX/TX packet history

### A node exists but has no functional entities

This may be valid.

A Souliss database can contain a node entry even when:

- the physical node is offline
- the bus connection is damaged
- no Typicals are assigned
- an old project configuration still reserves that node

The diagnostic health entity remains useful in this situation.

### Old entities remain unavailable after a rebuild

This is partly intentional.

Deleting entities automatically during a network migration could break dashboards and automations. Once you are sure an old entity will never return, you can remove it manually from the Home Assistant entity registry.

### Health shows `255`

The value is currently raw protocol data, not a percentage.

Do not interpret `255` as either an error or 100% solely from the number.

---

## Safety

Souliss can control real electrical equipment.

When testing a new Typical for the first time, start with a harmless load such as a lamp or test relay.

Be especially careful with:

- gates and doors
- shutters
- pumps
- heaters
- HVAC equipment
- alarm functions
- high-power loads

This integration is provided without warranty. You are responsible for validating commands and ensuring that your installation is electrically and functionally safe.

---

## Contributing

Contributions are welcome, especially from users who still operate real Souliss networks.

The most useful contributions are:

- confirmation of a Typical on physical hardware
- debug logs for unsupported Typicals
- diagnostics files
- protocol captures
- fixes for different Souliss firmware versions
- translations
- Home Assistant entity improvements
- documentation

When opening an issue, please include:

- Home Assistant version
- Souliss Gateway hardware
- Souliss node hardware
- connection type (Ethernet / Wi-Fi / RS-485 / other)
- Typical involved
- node and slot
- expected behaviour
- actual behaviour
- debug log
- diagnostics export

Please remove any information from diagnostics that you do not want to publish.

---

## Design philosophy

This integration follows a few deliberate principles:

**Preserve local control.**  
Home Assistant should enhance a Souliss installation, not make it dependent on Home Assistant.

**Do not invent protocol semantics.**  
If a legacy or custom Typical is unknown, raw data is preserved rather than pretending to understand it.

**Keep entity identities stable.**  
Souliss installations can evolve over many years. Rebuilding the physical network should not unnecessarily destroy Home Assistant dashboards and automations.

**Make troubleshooting possible.**  
Raw health data, Typical maps, protocol errors, and packet history are retained because old distributed automation networks are much easier to maintain when the protocol is visible.

---

## Background and references

Souliss is an open-source smart-home networking framework for Arduino and compatible platforms. It supports distributed control and several physical network technologies.

Useful upstream references:

- Souliss project: https://souliss.github.io/
- Souliss GitHub: https://github.com/souliss
- openHAB Souliss binding: https://www.openhab.org/addons/bindings/souliss/
- Home Assistant: https://www.home-assistant.io/

The openHAB Souliss binding and public Souliss protocol behaviour were valuable references while implementing broader Typical support.

This repository contains an independent Home Assistant implementation and is not an official port of the openHAB binding.

---

## Disclaimer

This project is maintained independently and primarily developed against real-world needs from an existing long-running Souliss installation.

It may contain bugs and protocol assumptions that do not apply to every Souliss firmware version or custom network.

Use it at your own risk, test new functions carefully, and keep working backups of both your Home Assistant configuration and Souliss firmware/projects.

---

## Acknowledgements

Thanks to the original **Souliss developers and community** for creating an open, distributed home-automation framework that has remained useful for many years.

Thanks also to the **openHAB Souliss binding contributors**, whose public implementation and documentation provide valuable reference material for understanding and maintaining Souliss interoperability.

And thanks to anyone who tests this Home Assistant integration on another real Souliss installation and helps improve compatibility for the remaining community.
