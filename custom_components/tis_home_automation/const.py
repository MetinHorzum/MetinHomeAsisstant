"""
Constants for TIS Home Automation integration.
"""

# Integration domain
DOMAIN = "tis_home_automation"

# Integration info
INTEGRATION_NAME = "TIS Home Automation"
INTEGRATION_VERSION = "1.0.0"

# Startup message
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{INTEGRATION_NAME} v{INTEGRATION_VERSION}
TIS protokol tabanlı akıllı ev cihazları entegrasyonu
Reverse engineering: TIS SMARTCLOUD protokol desteği
-------------------------------------------------------------------
"""

# Configuration keys
CONF_LOCAL_IP = "local_ip"
CONF_COMMUNICATION_TYPE = "communication_type"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_DISCOVERY_TIMEOUT = "discovery_timeout"

# Communication types
COMMUNICATION_TYPE_UDP = "udp"
COMMUNICATION_TYPE_RS485 = "rs485"

# Default values
DEFAULT_LOCAL_IP = "192.168.1.100"
DEFAULT_UDP_PORT = 6000
DEFAULT_SERIAL_BAUDRATE = 9600
DEFAULT_DISCOVERY_TIMEOUT = 30.0
DEFAULT_UPDATE_INTERVAL = 30  # seconds

# Device discovery
MAX_DISCOVERY_RETRIES = 3
DISCOVERY_BROADCAST_IP = "255.255.255.255"

# TIS Protocol OpCodes (from reverse engineering)
TIS_OPCODES = {
    # Discovery
    "DEVICE_DISCOVERY": [0x00, 0x0E],
    "DEVICE_DISCOVERY_RESPONSE": 0x000F,
    
    # Device Info
    "DEVICE_INFO_REQUEST": [0xF0, 0x03],
    "DEVICE_INFO_RESPONSE": 0xF004,
    "FIRMWARE_VERSION_REQUEST": [0xEF, 0xFF],
    "FIRMWARE_VERSION_RESPONSE": 0xEFFE,
    
    # Device Control
    "DEVICE_ON": [0x02, 0x80],
    "DEVICE_OFF": [0x02, 0x81],
    "DEVICE_STATUS_REQUEST": [0x02, 0x80],
    "DEVICE_STATUS_RESPONSE": 0x0281,
    
    # Lighting Control
    "LIGHT_ON": [0x11, 0x01],
    "LIGHT_OFF": [0x11, 0x02],
    "LIGHT_DIMMER": [0x11, 0x03],
    "LIGHT_STATUS": [0x11, 0x04],
    
    # AC Control  
    "AC_POWER_ON": [0xE0, 0xED],
    "AC_POWER_OFF": [0xE0, 0xEE],
    "AC_SET_TEMPERATURE": [0xE0, 0xEF],
    "AC_SET_MODE": [0xE0, 0xF0],
    "AC_SET_FAN_SPEED": [0xE0, 0xF1],
    "AC_STATUS_REQUEST": [0xE0, 0xF2],
    
    # Sensor Data
    "SENSOR_DATA_REQUEST": [0x20, 0x24],
    "SENSOR_DATA_RESPONSE": 0x2025,
    "HEALTH_SENSOR_DATA": 0x2025,
}

# Device Types (from TIS protocol analysis)
TIS_DEVICE_TYPES = {
    # Lighting
    0x0100: "switch_1gang",
    0x0101: "switch_2gang", 
    0x0102: "switch_3gang",
    0x0103: "switch_4gang",
    0x0110: "dimmer_1gang",
    0x0111: "dimmer_2gang",
    0x0120: "curtain_switch",
    0x0130: "scene_switch",
    
    # Climate Control
    0x0200: "ac_controller",
    0x0201: "thermostat",
    0x0202: "floor_heating", 
    0x0210: "fan_controller",
    
    # Sensors
    0x0300: "motion_sensor",
    0x0301: "door_window_sensor",
    0x0302: "temperature_sensor",
    0x0303: "humidity_sensor",
    0x0304: "light_sensor",
    0x0305: "smoke_detector",
    0x0306: "gas_detector",
    0x0310: "health_sensor",
    0x0320: "noise_sensor",
    0x0330: "air_quality_sensor",
    
    # Security
    0x0400: "door_lock",
    0x0401: "alarm_panel",
    0x0402: "siren",
    0x0410: "camera_controller",
    
    # Audio/Visual
    0x0500: "audio_controller",
    0x0501: "tv_controller", 
    0x0510: "projector_controller",
    
    # Infrastructure
    0x0600: "gateway",
    0x0601: "repeater",
    0x0602: "bridge",
    
    # Special/Unknown
    0xFFFE: "unknown_device",
    0xFFFF: "broadcast_all"
}

# Device capabilities mapping
DEVICE_CAPABILITIES = {
    # Switches
    "switch_1gang": ["switch"],
    "switch_2gang": ["switch", "switch"], 
    "switch_3gang": ["switch", "switch", "switch"],
    "switch_4gang": ["switch", "switch", "switch", "switch"],
    
    # Dimmers
    "dimmer_1gang": ["light"],
    "dimmer_2gang": ["light", "light"],
    
    # Climate
    "ac_controller": ["climate"],
    "thermostat": ["climate"],
    "floor_heating": ["climate"],
    "fan_controller": ["fan"],
    
    # Sensors
    "motion_sensor": ["binary_sensor"],
    "door_window_sensor": ["binary_sensor"],
    "temperature_sensor": ["sensor"],
    "humidity_sensor": ["sensor"],
    "light_sensor": ["sensor"],
    "smoke_detector": ["binary_sensor"],
    "gas_detector": ["binary_sensor"], 
    "health_sensor": ["sensor", "sensor", "sensor", "sensor", "sensor", "sensor"],  # Multi-sensor
    "noise_sensor": ["sensor"],
    "air_quality_sensor": ["sensor"],
    
    # Security
    "door_lock": ["lock"],
    "alarm_panel": ["alarm_control_panel"],
    "siren": ["switch", "binary_sensor"],
    
    # Default
    "unknown_device": ["sensor"]
}

# Entity names and icons
ENTITY_DEFINITIONS = {
    "switch": {
        "icon": "mdi:light-switch",
        "device_class": None
    },
    "light": {
        "icon": "mdi:lightbulb", 
        "device_class": None
    },
    "climate": {
        "icon": "mdi:thermostat",
        "device_class": None
    },
    "fan": {
        "icon": "mdi:fan",
        "device_class": "fan"
    },
    "motion_sensor": {
        "icon": "mdi:motion-sensor",
        "device_class": "motion"
    },
    "door_window_sensor": {
        "icon": "mdi:door",
        "device_class": "door"
    },
    "temperature_sensor": {
        "icon": "mdi:thermometer",
        "device_class": "temperature",
        "unit": "°C"
    },
    "humidity_sensor": {
        "icon": "mdi:water-percent",
        "device_class": "humidity", 
        "unit": "%"
    },
    "light_sensor": {
        "icon": "mdi:brightness-6",
        "device_class": "illuminance",
        "unit": "lux"
    },
    "smoke_detector": {
        "icon": "mdi:smoke-detector",
        "device_class": "smoke"
    },
    "gas_detector": {
        "icon": "mdi:gas-cylinder",
        "device_class": "gas"
    },
    "noise_sensor": {
        "icon": "mdi:volume-high",
        "device_class": "sound_pressure",
        "unit": "dB"
    },
    "air_quality_sensor": {
        "icon": "mdi:air-filter",
        "device_class": "aqi"
    },
    "door_lock": {
        "icon": "mdi:door-closed-lock",
        "device_class": None
    },
    "alarm_panel": {
        "icon": "mdi:shield-home",
        "device_class": None
    }
}

# Health sensor sub-sensors
HEALTH_SENSOR_MAPPING = {
    "lux": {
        "name": "Light Level",
        "icon": "mdi:brightness-6", 
        "device_class": "illuminance",
        "unit": "lux",
        "state_class": "measurement"
    },
    "noise": {
        "name": "Noise Level",
        "icon": "mdi:volume-high",
        "device_class": "sound_pressure", 
        "unit": "dB",
        "state_class": "measurement"
    },
    "eco2": {
        "name": "eCO2",
        "icon": "mdi:molecule-co2",
        "device_class": "carbon_dioxide",
        "unit": "ppm", 
        "state_class": "measurement"
    },
    "tvoc": {
        "name": "TVOC",
        "icon": "mdi:air-filter",
        "device_class": "volatile_organic_compounds",
        "unit": "ppb",
        "state_class": "measurement"
    },
    "temperature": {
        "name": "Temperature",
        "icon": "mdi:thermometer",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "humidity": {
        "name": "Humidity", 
        "icon": "mdi:water-percent",
        "device_class": "humidity",
        "unit": "%",
        "state_class": "measurement"
    }
}

# AC modes mapping
AC_MODES = {
    0: "cool",
    1: "heat", 
    2: "fan_only",
    3: "auto"
}

AC_FAN_SPEEDS = {
    0: "auto",
    1: "low",
    2: "medium", 
    3: "high"
}

# Update intervals
UPDATE_INTERVALS = {
    "switch": 60,      # 1 minute
    "light": 60,       # 1 minute  
    "climate": 30,     # 30 seconds
    "sensor": 30,      # 30 seconds
    "binary_sensor": 15,  # 15 seconds
}

# Error messages
ERROR_MESSAGES = {
    "NO_TIS_PROTOCOL": "TIS Protocol library not found. Please install the tis_protocol module.",
    "CONNECTION_FAILED": "Failed to connect to TIS devices.",
    "DISCOVERY_FAILED": "Device discovery failed.",
    "DEVICE_UNREACHABLE": "Device is unreachable.",
    "INVALID_RESPONSE": "Invalid response from device.",
    "TIMEOUT": "Communication timeout.",
    "UNKNOWN_DEVICE_TYPE": "Unknown device type.",
}

# Service definitions
SERVICE_DISCOVER_DEVICES = "discover_devices"
SERVICE_SEND_RAW_COMMAND = "send_raw_command"
SERVICE_REFRESH_DEVICE = "refresh_device"
SERVICE_RESET_DEVICE = "reset_device"

# Attributes
ATTR_DEVICE_ID = "device_id" 
ATTR_DEVICE_TYPE = "device_type"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_SIGNAL_STRENGTH = "signal_strength"
ATTR_LAST_SEEN = "last_seen"
ATTR_COMMUNICATION_TYPE = "communication_type"
ATTR_SOURCE_ADDRESS = "source_address"

# Event types
EVENT_TIS_DEVICE_DISCOVERED = f"{DOMAIN}_device_discovered"
EVENT_TIS_DEVICE_LOST = f"{DOMAIN}_device_lost"
EVENT_TIS_COMMUNICATION_ERROR = f"{DOMAIN}_communication_error"

# Configuration flow steps
STEP_USER = "user"
STEP_COMMUNICATION = "communication"
STEP_UDP_CONFIG = "udp_config"
STEP_SERIAL_CONFIG = "serial_config"
STEP_DISCOVERY = "discovery"