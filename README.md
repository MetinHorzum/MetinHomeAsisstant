# TIS Home Automation Integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/yourusername/tis-home-automation-ha.svg?style=for-the-badge)](https://github.com/yourusername/tis-home-automation-ha/releases)
[![License](https://img.shields.io/github/license/yourusername/tis-home-automation-ha.svg?style=for-the-badge)](LICENSE)

Home Assistant custom component for **TIS Home Automation** systems. This integration provides comprehensive support for TIS devices including switches, lights, climate control (AC units), sensors, and binary sensors.

## ✨ Features

- 🔌 **Multiple Platform Support**: Switch, Light, Climate, Sensor, Binary Sensor
- 🌐 **Dual Transport**: UDP (Port 6000) and RS485 serial communication
- 🔍 **Auto Discovery**: Automatic device discovery on your network
- 🏠 **150+ Device Types**: Comprehensive TIS device type mapping
- 🇹🇷 **Turkish Language Support**: Native Turkish language support
- ⚡ **Real-time Updates**: Live status updates from TIS devices  
- 🎛️ **Climate Control**: Full AC unit control (temperature, mode, fan speed)
- 📊 **Sensor Data**: Temperature, humidity, light, and other sensor readings
- 🔧 **HACS Compatible**: Easy installation through HACS

## 🚀 Supported TIS Devices

This integration supports **150+ TIS device types** including:

- **Switches & Dimmers** (0x806C, 0x807A, 0x80BA)
- **Lights & LED Controllers** (0x8090, 0x80B0)  
- **Climate Control** (AC units, thermostats)
- **Sensors** (Temperature, humidity, light, motion)
- **Binary Sensors** (Door/window, motion, occupancy)
- **Smart Panels & Controllers**

Real device examples discovered during testing:
- "Mekanik", "Mutfak", "Toplantı Odası", "AR-GE", "Elektronik", "Pano", "Y.KapıUST"

## 📋 Requirements

- Home Assistant 2023.12.0 or later
- TIS Home Automation devices on your network
- Network access to TIS devices (UDP Port 6000)
- Optional: RS485 serial interface for direct communication

## 📥 Installation

### Method 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations**  
3. Click the **+** button and search for "**TIS Home Automation**"
4. Click **Install**
5. Restart Home Assistant

### Method 2: Manual Installation

1. Download the latest release from [Releases](https://github.com/yourusername/tis-home-automation-ha/releases)
2. Extract to `custom_components/tis_home_automation/` in your HA config directory
3. Restart Home Assistant

## ⚙️ Configuration

### Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "**TIS Home Automation**"
4. Follow the setup wizard

### Configuration Options

#### Network Configuration (UDP)
- **Local IP Address**: Your Home Assistant IP (auto-detected)
- **Port**: TIS communication port (default: 6000)
- **Discovery Timeout**: Device discovery timeout (default: 30s)

#### Serial Configuration (RS485) - Optional
- **Serial Port**: RS485 interface port (e.g., `/dev/ttyUSB0`)
- **Baud Rate**: Communication speed (default: 9600)

### Manual Configuration (YAML) - Advanced

```yaml
# configuration.yaml
tis_home_automation:
  - platform: udp
    local_ip: "192.168.1.100"  # Your Home Assistant IP
    port: 6000
    discovery_timeout: 30
    
  - platform: serial  # Optional RS485
    port: "/dev/ttyUSB0"
    baudrate: 9600
```

## 🏠 Device Auto-Discovery

The integration automatically discovers TIS devices on your network:

1. **Multi-Stage Discovery**: Uses multiple OpCodes for comprehensive device detection
2. **Extended Timeout**: 43+ seconds total discovery time for reliable detection  
3. **Device Naming**: Automatically extracts device names (supports Turkish characters)
4. **Device Classification**: Maps devices to appropriate Home Assistant platforms

### Discovery Process
- Sends discovery packets: `0xF003`, `0x000E`, `0xDA44`, `0x0002`
- Listens for responses: `0xF004`, `0x000F`, `0xDA45`, `0xDA44`, `0x0002`
- Processes device information and creates entities

## 🎛️ Supported Entities

### Switch Platform
- Light switches and dimmers
- Power outlets and relays
- Scene controllers

### Light Platform  
- Dimmable lights
- LED strip controllers
- Smart bulbs

### Climate Platform
- Air conditioning units
- Temperature control
- Fan speed control
- Mode selection (Cool/Heat/Fan/Auto)

### Sensor Platform
- Temperature sensors
- Humidity sensors  
- Light level sensors
- Power consumption
- Energy monitoring

### Binary Sensor Platform
- Motion detectors
- Door/window sensors
- Occupancy sensors
- Device status indicators

## 🔧 Services

### Custom Services

#### `tis_home_automation.send_command`
Send raw commands to TIS devices.

```yaml
service: tis_home_automation.send_command
data:
  device_id: [0x01, 0x12]
  operation_code: [0x02, 0x81] 
  additional_data: [0x01]
```

#### `tis_home_automation.discover_devices`
Manually trigger device discovery.

```yaml
service: tis_home_automation.discover_devices
data:
  timeout: 30
```

## 🛠️ Troubleshooting

### Common Issues

#### No Devices Found
1. Verify TIS devices are powered and on the network
2. Check your Home Assistant IP is in the same network segment
3. Ensure UDP port 6000 is not blocked by firewall
4. Try increasing discovery timeout

#### Connection Issues
1. Verify network connectivity to TIS devices
2. Check if other applications are using port 6000
3. Ensure Home Assistant has network access

#### Device Control Not Working
1. Verify device is responding (check logs)
2. Confirm device type mapping is correct
3. Check if device requires specific command format

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.tis_home_automation: debug
    custom_components.tis_home_automation.tis_protocol: debug
```

### Useful Debug Commands

```bash
# Check UDP traffic on port 6000
sudo tcpdump -i any -X port 6000

# Test UDP connectivity
nc -u [device_ip] 6000
```

## 📊 Network Protocol

This integration uses the **TIS SMARTCLOUD Protocol**:

- **Transport**: UDP Port 6000 (primary) + RS485 serial (optional)
- **Packet Format**: IP(4) + "SMARTCLOUD"(10) + Separator(2) + Length(1) + Data + CRC(2)
- **Discovery**: Multi-OpCode discovery with extended timeouts
- **CRC Validation**: 16-bit CRC for packet integrity
- **Device Types**: 150+ mapped device types with Turkish support

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

### Development Setup

1. Clone this repository
2. Create a virtual environment
3. Install development dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `pytest`

### Adding New Device Types

1. Identify device OpCodes and responses
2. Add device type mapping in `device_types.py`
3. Implement entity class if needed
4. Add tests and documentation

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- **TIS Home Automation** for their comprehensive smart home ecosystem
- **Home Assistant Community** for the excellent platform
- **HACS** for making custom integrations easily accessible

## 🔗 Links

- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)
- [TIS Home Automation](https://www.tis.com.tr/)

## 📞 Support

- Create an [Issue](https://github.com/yourusername/tis-home-automation-ha/issues) for bugs or feature requests
- Join discussions in [Discussions](https://github.com/yourusername/tis-home-automation-ha/discussions)
- Check the [Wiki](https://github.com/yourusername/tis-home-automation-ha/wiki) for detailed documentation

---

**⭐ If this integration helps you, please give it a star!**

Made with ❤️ for the Home Assistant community