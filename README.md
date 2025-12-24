# TIS Control Integration for Home Assistant

Platform-independent TIS Control integration for Home Assistant.

## Features
- Supports all platforms (x86, x64, ARM, Docker, VM)
- 11 entity types: switch, light, sensor, binary_sensor, climate, cover, select, lock, fan, button, weather
- Optional Raspberry Pi GPIO support for CPU fan control
- Platform-independent CPU temperature monitoring

## Installation
1. Copy this folder to `custom_components/tis_control/`
2. Restart Home Assistant
3. Add integration via UI

## Requirements
- Home Assistant 2024.1.0 or newer
- TISControlProtocol 1.0.5
- All platforms supported (no hardware dependencies)

## Platform Support
✅ Home Assistant OS (x86/x64)
✅ Docker Container
✅ Virtual Machine
✅ Windows/Mac/Linux
✅ Raspberry Pi (with optional GPIO features)
