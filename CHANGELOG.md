# Changelog

All notable changes to the TIS Home Automation integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-24

### Added
- 🎉 **Initial Release** - Complete TIS Home Automation integration for Home Assistant
- 🔌 **Multi-Platform Support**: Switch, Light, Climate, Sensor, Binary Sensor entities
- 🌐 **Dual Transport Layer**: UDP (Port 6000) and RS485 serial communication
- 🔍 **Advanced Device Discovery**: Multi-OpCode discovery with 43+ second extended timeout
- 🏠 **150+ Device Types**: Comprehensive TIS device type mapping and classification
- 🇹🇷 **Turkish Language Support**: Native Turkish language and character support
- ⚡ **Real-time Updates**: Live status updates and device state synchronization
- 🎛️ **Climate Control**: Full AC unit control (temperature, mode, fan speed)
- 📊 **Sensor Integration**: Temperature, humidity, light, and environmental sensors
- 🔧 **HACS Compatible**: Easy installation through HACS custom repository
- 🛠️ **Configuration Flow**: User-friendly setup wizard with auto-detection
- 🌍 **Network Discovery**: Automatic device discovery on local network
- 🔒 **CRC Validation**: Packet integrity validation with TIS SMARTCLOUD protocol
- 📝 **Custom Services**: Raw command sending and manual device discovery
- 🐛 **Debug Tools**: Comprehensive logging and troubleshooting utilities

### Device Support
- **Switches & Dimmers** (0x806C, 0x807A, 0x80BA)
- **Lights & LED Controllers** (0x8090, 0x80B0)
- **Climate Control Units** (Air conditioners, thermostats)
- **Environmental Sensors** (Temperature, humidity, light level)
- **Binary Sensors** (Motion, door/window, occupancy)
- **Smart Panels & Controllers**

### Technical Features
- **TIS SMARTCLOUD Protocol**: Full protocol implementation with reverse-engineered packet format
- **Multi-Stage Discovery**: Sequential OpCode transmission (0xF003, 0x000E, 0xDA44, 0x0002)
- **Extended Response Handling**: 30s main + 8s for device names + 5s final timeout
- **Async Architecture**: Non-blocking communication with asyncio coordination
- **Error Recovery**: Connection retry and offline device handling
- **Device Classification**: Automatic entity type assignment based on device capabilities
- **UTF-8 Support**: Turkish character handling in device names

### Real-World Testing
Successfully tested with live TIS Home Automation network containing:
- "Mekanik", "Mutfak", "Toplantı Odası" (Conference Room)
- "AR-GE", "Elektronik", "Pano" (Panel)
- "Y.KapıUST", "Danışma" (Consultation)
- And 12+ other active TIS devices

### Configuration
- **Network Setup**: Automatic IP detection with manual override
- **Discovery Options**: Configurable timeout and retry parameters
- **Transport Selection**: Choose between UDP, RS485, or dual mode
- **Debug Logging**: Detailed packet-level debugging support

## [Unreleased]

### Planned Features
- Entity state persistence across Home Assistant restarts
- Device group and scene support
- Energy monitoring integration
- Advanced climate scheduling
- Mobile app push notifications
- Custom dashboard cards
- Bulk device operations
- Historical data analysis

---

## Version History

### Pre-Release Development
- Reverse engineering of TIS protocol from `rs485_tis_gui_tester.py`
- Protocol packet format analysis and CRC validation
- Device type mapping and capability discovery
- Network communication testing and optimization
- Multi-transport layer development
- Home Assistant integration architecture design
- Entity platform implementations
- Configuration flow development
- Testing with real TIS hardware network

---

**For detailed technical documentation, see the [README.md](README.md)**

**For bug reports and feature requests, visit our [GitHub Issues](https://github.com/yourusername/tis-home-automation-ha/issues)**