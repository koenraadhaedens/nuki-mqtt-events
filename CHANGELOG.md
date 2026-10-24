# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to semantic versioning.

## [0.5.0] - 2026-10-24

### Added
- Add a native MQTT lock entity per device with non-retained lock/unlock commands, reported state, and device/broker availability.

### Fixed
- Align state sensor labels with Nuki's MQTT state codes, including unlocking, unlocked, unlatched, unlatching, and motor blocked.

## [0.4.4] - 2026-10-24

### Fixed
- Prevent duplicate integration entries, including when an existing entry has no unique ID.

## [0.4.3] - 2026-10-14

### Changed
- Update the integration icon for improved branding.

## [0.4.2] - 2026-10-14

### Fixed
- Order Home Assistant manifest keys for hassfest validation.
- Add the repository description and topics required for HACS default inclusion.

## [0.4.1] - 2026-10-14

### Added
- Add a local Home Assistant brand icon for the integration.

## [0.4.0] - 2026-10-13

### Added
- Decode `lockActionEvent` into a readable `Last action` sensor with event details as attributes.
- Support YAML mappings from Nuki authorization and keypad code IDs to user names.

## [0.3.0] - 2026-10-13

### Added
- Create independent sensor and binary-sensor entities for every Nuki device under the configured MQTT topic.
- Name each device's entities from the MQTT payload `name`, with the topic device segment as a fallback.

## [0.2.1] - 2026-10-13

### Fixed
- Parse individual MQTT field topics as well as multiline key/value payloads.
- Keep entity values when MQTT messages update unrelated fields instead of replacing them with unknown/unavailable values.

## [0.2.0] - 2026-10-13

### Added
- Separate entities for every field in the Nuki MQTT payload, including firmware, timestamp, device name/type, mode, and lock action event.
- Binary sensors for connection, battery critical/charging, keypad battery critical, and door-sensor battery critical.
- Normalization of the `doorsensorBatteryCritical` MQTT field spelling.

## [0.1.0] - 2026-10-13

### Added
- Initial Home Assistant custom integration scaffold for HACS distribution.
- HACS repository metadata in `hacs.json`.
- Home Assistant manifest with MQTT dependency metadata and version `0.1.0`.
- MQTT event parser for Nuki key/value payloads.
- State sensor, battery sensor, and connection binary sensor entities.
- HACS installation documentation for custom repositories in Home Assistant.
- GitHub validation and release workflows for automated checks and GitHub Releases.
