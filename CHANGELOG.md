# Changelog

All notable changes to this integration are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow the `version` field in `custom_components/souliss/manifest.json`, and each version is published as a GitHub release tagged `v<version>`.

## [Unreleased]

## [0.1.0-alpha.3.4] - 2026-09-16

### Fixed

- **Outgoing MaCaco frames are now paced through a send queue** (`TX_INTERVAL`, 0.25 s). The Souliss Gateway buffers a single UDP frame, so requests sent back-to-back in the same event-loop tick (ping + DB structure at startup, subscription + health after each Typicals answer, ping + rediscovery on the 300 s tick) were silently dropped except for the first one. Symptoms: a Gateway whose startup DB-structure request was lost stayed at 0 nodes with every entity unavailable, health requests (`0x25`) never got an answer, and periodic rediscovery never reached the Gateway. Identical pending requests are merged; FORCE commands are never merged.

### Added

- English translation (`translations/en.json`). Home Assistant loads translations for custom integrations only from the `translations` folder, so the setup dialog could show untranslated field names in English.

## [0.1.0-alpha.3.3] - 2026-09-14

### Fixed

- **Removed the periodic state poll introduced in 0.1.0-alpha.3.2.** After updating to 0.1.0-alpha.3.2, a Souliss Gateway stopped responding, including to other Souliss user interfaces. The cause is not confirmed, but the poll (`0x27`) was the only new request sent to the Gateway. The integration now sends only the same requests as before 0.1.0-alpha.3.2.
- Idle nodes still stay available: a non-zero node health response (`0x35`) keeps their entities available, without sending any additional request.

> [!IMPORTANT]
> If your Gateway stopped responding after installing 0.1.0-alpha.3.2, install this version, restart Home Assistant, and power-cycle the Gateway.

## [0.1.0-alpha.3.2] - 2026-09-14

> [!WARNING]
> Superseded by 0.1.0-alpha.3.3. The state poll added in this version may cause some Gateways to stop responding.

### Fixed

- **Idle nodes no longer become unavailable.** Entities on nodes whose state did not change for about three minutes were marked unavailable, while nodes that were switched on stayed available. The Souliss Gateway only answers a subscription when node state changes, so idle nodes sent no state data.
  - The integration now polls the full node state (MaCaco `0x27`) every 60 seconds and after Typical discovery. The Gateway answers a poll even when nothing has changed.
  - A non-zero node health response (`0x35`) now also counts as proof that the node is reachable. Nodes reporting health `0` still become unavailable.
  - Entity availability is refreshed after every health response.

> [!NOTE]
> Verified with an offline protocol simulation, not yet on physical hardware. If your log shows `Souliss Gateway returned unsupported function (0x83)` every minute, your Gateway firmware does not support polling. Please open an issue with your debug log and diagnostics.

### Changed

- `manifest.json` now includes `codeowners` and `issue_tracker`, as required by HACS, and `documentation` points to this repository.
- The README describes installation and updates via HACS.

### Removed

- Compiled Python cache files (`__pycache__`) and macOS `.DS_Store` files are no longer part of the repository or the downloaded integration.

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

[Unreleased]: https://github.com/lbokor78/Souliss---Home-Assistant-integration/compare/v0.1.0-alpha.3.3...HEAD
[0.1.0-alpha.3.3]: https://github.com/lbokor78/Souliss---Home-Assistant-integration/releases/tag/v0.1.0-alpha.3.3
[0.1.0-alpha.3.2]: https://github.com/lbokor78/Souliss---Home-Assistant-integration/releases/tag/v0.1.0-alpha.3.2
[0.1.0-alpha.3.1]: https://github.com/lbokor78/Souliss---Home-Assistant-integration/tree/0751538
