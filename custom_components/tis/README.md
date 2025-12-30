# TIS Home Assistant Custom Integration (SmartCloud UDP)

- Discovers all TIS SmartCloud devices via UDP 6000 broadcast (0x000E/0x000F)
- Always exposes `sensor.tis_discovery_devices` with the full discovered list
- For RCU devices (device_type 0x802B): creates
  - 24 output switches (CH1..CH24) with control via opcode 0x0031 (value 0/100)
  - 20 digital inputs (DI1..DI20) via opcodes 0xD218/0xD219

Notes:
- If Home Assistant runs in Docker, use host networking so UDP broadcast works.
