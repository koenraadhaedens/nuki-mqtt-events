# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to semantic versioning.

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
