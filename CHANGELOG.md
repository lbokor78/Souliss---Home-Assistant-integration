# Changelog

All notable changes to this integration are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow the `version` field in `custom_components/souliss/manifest.json`.

## [Unreleased]

### Fixed

- **Idle nodes no longer become unavailable.** Entities on nodes whose state did not change for about three minutes were marked unavailable, while nodes that were switched on stayed available. The Souliss Gateway only answers a subscription when node state changes, so idle nodes sent no state data.
  - The integration now polls the full node state (MaCaco `0x27`) every 60 seconds and after Typical discovery. The Gateway answers a poll even when nothing has changed.
  - A non-zero node health response (`0x35`) now also counts as proof that the node is reachable. Nodes reporting health `0` still become unavailable.
  - Entity availability is refreshed after every health response.

> [!NOTE]
> Verified with an offline protocol simulation, not yet on physical hardware. If your log shows `Souliss Gateway returned unsupported function (0x83)` every minute, your Gateway firmware does not support polling. Please open an issue with your debug log and diagnostics.

## [0.1.0-alpha.3.1] - 2026-09-11

First version published in this repository.

### Added

- Direct local UDP communication with a Souliss Gateway (VNet / MaCaco), set up through the Home Assistant config flow.
- Automatic DB structure and Typical discovery, periodic rediscovery, and a **Rediscover network** button and action.
- Entities for Typicals T11–T1A, T21–T22, T31, T41–T42, T51–T58 and T61–T68, plus raw diagnostic sensors for unknown or legacy Typicals.
- Action Message / Topic sensors and the `souliss_action_message` event.
- Node health sensors, diagnostics download with the last 100 TX/RX packets, and the `timed`, `raw_force` and `raw_macaco` actions.
- HACS compatibility.

### Fixed

- Restored the stable primary entity unique IDs used by alpha.2. Alpha.3 had appended `_main` to them, which duplicated every existing entity.
- On startup, obsolete registry entries created only by alpha.3 are removed: the duplicated `_main` entities and the default `_sleep_default` timed buttons.

[Unreleased]: https://github.com/lbokor78/Souliss---Home-Assistant-integration/commits/main
[0.1.0-alpha.3.1]: https://github.com/lbokor78/Souliss---Home-Assistant-integration/tree/0751538
