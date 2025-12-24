# TIS Home (SmartCloud UDP) - Home Assistant Custom Integration

## Install
Copy `custom_components/tis` into your HA config folder: `/config/custom_components/tis`

Restart Home Assistant.

## Setup
Settings -> Devices & Services -> Add Integration -> "TIS Home (SmartCloud UDP)"

- Host: gateway IP (e.g. 192.168.1.200)
- Port: 6000
- Broadcast: usually 192.168.1.255 (if your LAN is /24)

## Notes
This version discovers devices via OpCode 0x000E/0x000F and shows two debug sensors:
- Discovered devices
- Seconds since last packet
