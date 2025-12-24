"""TIS Device Simulator for comprehensive testing."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

from .tis_protocol_mock import MockTISDevice

_LOGGER = logging.getLogger(__name__)

class TISDeviceSimulator:
    """Comprehensive TIS device simulator for testing scenarios."""
    
    def __init__(self):
        self.devices: Dict[str, MockTISDevice] = {}
        self.device_scenarios: Dict[str, DeviceScenario] = {}
        self.running = False
        self._simulation_task: Optional[asyncio.Task] = None
        
    def add_device(self, device_key: str, device: MockTISDevice):
        """Add device to simulator."""
        self.devices[device_key] = device
        self.device_scenarios[device_key] = DeviceScenario(device)
        
    def remove_device(self, device_key: str):
        """Remove device from simulator."""
        if device_key in self.devices:
            del self.devices[device_key]
        if device_key in self.device_scenarios:
            del self.device_scenarios[device_key]
    
    async def start_simulation(self):
        """Start device simulation."""
        if self.running:
            return
        
        self.running = True
        self._simulation_task = asyncio.create_task(self._simulation_loop())
        _LOGGER.info("TIS device simulation started")
    
    async def stop_simulation(self):
        """Stop device simulation."""
        self.running = False
        
        if self._simulation_task:
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass
            self._simulation_task = None
        
        _LOGGER.info("TIS device simulation stopped")
    
    async def _simulation_loop(self):
        """Main simulation loop."""
        try:
            while self.running:
                # Update all device scenarios
                for device_key, scenario in self.device_scenarios.items():
                    try:
                        await scenario.update()
                    except Exception as e:
                        _LOGGER.error(f"Error updating device {device_key}: {e}")
                
                # Sleep for simulation interval
                await asyncio.sleep(1.0)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _LOGGER.error(f"Simulation loop error: {e}")
    
    def get_device(self, device_key: str) -> Optional[MockTISDevice]:
        """Get device by key."""
        return self.devices.get(device_key)
    
    def get_scenario(self, device_key: str) -> Optional['DeviceScenario']:
        """Get device scenario."""
        return self.device_scenarios.get(device_key)
    
    def set_device_offline(self, device_key: str):
        """Set device offline."""
        scenario = self.device_scenarios.get(device_key)
        if scenario:
            scenario.set_offline()
    
    def set_device_online(self, device_key: str):
        """Set device online."""
        scenario = self.device_scenarios.get(device_key)
        if scenario:
            scenario.set_online()
    
    def simulate_motion_detection(self, device_key: str, duration: float = 10.0):
        """Simulate motion detection."""
        scenario = self.device_scenarios.get(device_key)
        if scenario:
            scenario.simulate_motion(duration)
    
    def simulate_door_activity(self, device_key: str, open_duration: float = 5.0):
        """Simulate door opening and closing."""
        scenario = self.device_scenarios.get(device_key)
        if scenario:
            scenario.simulate_door_activity(open_duration)
    
    def simulate_temperature_change(self, device_key: str, target_temp: float, rate: float = 0.1):
        """Simulate gradual temperature change."""
        scenario = self.device_scenarios.get(device_key)
        if scenario:
            scenario.simulate_temperature_change(target_temp, rate)

class DeviceScenario:
    """Individual device simulation scenario."""
    
    def __init__(self, device: MockTISDevice):
        self.device = device
        self.last_update = time.time()
        self.scenarios: List[ScenarioAction] = []
        self.active_scenarios: List[ScenarioAction] = []
        
        # Initialize device-specific simulation
        self._init_device_simulation()
    
    def _init_device_simulation(self):
        """Initialize simulation based on device type."""
        device_type = self.device.device_type
        
        # Motion sensor simulation
        if device_type == 0x0300:  # motion_sensor
            self.device.set_state("motion", False)
            self.device.set_state("last_motion", None)
            
        # Door/window sensor simulation
        elif device_type == 0x0301:  # door_window_sensor
            self.device.set_state("contact", False)  # False = closed
            self.device.set_state("last_changed", None)
            
        # Temperature sensor simulation
        elif device_type == 0x0302:  # temperature_sensor
            self.device.set_state("temperature", 22.5 + random.uniform(-2, 2))
            
        # Health sensor simulation
        elif device_type == 0x0310:  # health_sensor
            self.device.set_state("sensors", {
                "lux": random.randint(50, 500),
                "noise": random.randint(30, 60),
                "eco2": random.randint(400, 800),
                "tvoc": random.randint(0, 50),
                "temperature": 23.0 + random.uniform(-3, 3),
                "humidity": 45 + random.randint(-10, 20)
            })
            
        # Switch simulation
        elif device_type in [0x0100, 0x0101, 0x0102, 0x0103]:  # switches
            gang_count = (device_type & 0x000F) + 1
            switches = [{"state": "off"} for _ in range(gang_count)]
            self.device.set_state("switches", switches)
            
        # Dimmer simulation  
        elif device_type in [0x0110, 0x0111]:  # dimmers
            gang_count = (device_type & 0x000F) + 1
            dimmers = [{"state": "off", "brightness": 0} for _ in range(gang_count)]
            self.device.set_state("dimmers", dimmers)
            
        # AC controller simulation
        elif device_type == 0x0200:  # ac_controller
            self.device.set_state("ac", {
                "power": "off",
                "mode": "auto",
                "temperature": 24,
                "fan_speed": 0
            })
            self.device.set_state("current_temperature", 26.0)
            
    async def update(self):
        """Update device simulation."""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # Process active scenarios
        finished_scenarios = []
        for scenario in self.active_scenarios:
            if await scenario.update(dt):
                finished_scenarios.append(scenario)
        
        # Remove finished scenarios
        for scenario in finished_scenarios:
            self.active_scenarios.remove(scenario)
        
        # Update device-specific simulation
        await self._update_device_simulation(dt)
    
    async def _update_device_simulation(self, dt: float):
        """Update device-specific simulation."""
        device_type = self.device.device_type
        
        # Health sensor - gradually change values
        if device_type == 0x0310:
            sensors = self.device.get_state().get("sensors", {})
            
            # Add small random variations
            sensors["lux"] = max(0, sensors.get("lux", 100) + random.randint(-10, 10))
            sensors["noise"] = max(20, min(80, sensors.get("noise", 40) + random.randint(-2, 2)))
            sensors["eco2"] = max(300, min(2000, sensors.get("eco2", 450) + random.randint(-20, 20)))
            sensors["tvoc"] = max(0, min(200, sensors.get("tvoc", 10) + random.randint(-5, 5)))
            
            # Temperature drift
            temp = sensors.get("temperature", 23.0)
            temp += random.uniform(-0.1, 0.1) * dt
            sensors["temperature"] = round(max(10, min(40, temp)), 1)
            
            # Humidity drift
            hum = sensors.get("humidity", 50)
            hum += random.uniform(-0.5, 0.5) * dt
            sensors["humidity"] = max(0, min(100, int(hum)))
            
            self.device.set_state("sensors", sensors)
            
        # AC controller - simulate heating/cooling
        elif device_type == 0x0200:
            ac_state = self.device.get_state().get("ac", {})
            current_temp = self.device.get_state().get("current_temperature", 26.0)
            
            if ac_state.get("power") == "on":
                target_temp = ac_state.get("temperature", 24)
                mode = ac_state.get("mode", "auto")
                
                # Simulate temperature change based on AC operation
                if mode == "cool" and current_temp > target_temp:
                    current_temp -= 0.5 * dt  # Cool down
                elif mode == "heat" and current_temp < target_temp:
                    current_temp += 0.5 * dt  # Heat up
                elif mode == "auto":
                    if current_temp > target_temp + 1:
                        current_temp -= 0.3 * dt
                    elif current_temp < target_temp - 1:
                        current_temp += 0.3 * dt
            else:
                # Natural temperature drift toward ambient
                ambient = 25.0
                if current_temp > ambient:
                    current_temp -= 0.1 * dt
                elif current_temp < ambient:
                    current_temp += 0.1 * dt
            
            self.device.set_state("current_temperature", round(current_temp, 1))
    
    def add_scenario(self, scenario: 'ScenarioAction'):
        """Add a scenario to this device."""
        self.scenarios.append(scenario)
        
    def start_scenario(self, scenario: 'ScenarioAction'):
        """Start a specific scenario."""
        if scenario not in self.active_scenarios:
            self.active_scenarios.append(scenario)
            scenario.start(self.device)
    
    def set_offline(self):
        """Set device offline."""
        self.device.set_state("online", False)
        
    def set_online(self):
        """Set device online."""
        self.device.set_state("online", True)
        
    def simulate_motion(self, duration: float = 10.0):
        """Start motion detection simulation."""
        motion_scenario = MotionScenario(duration)
        self.start_scenario(motion_scenario)
        
    def simulate_door_activity(self, open_duration: float = 5.0):
        """Start door activity simulation."""
        door_scenario = DoorActivityScenario(open_duration)
        self.start_scenario(door_scenario)
        
    def simulate_temperature_change(self, target_temp: float, rate: float = 0.1):
        """Start temperature change simulation."""
        temp_scenario = TemperatureChangeScenario(target_temp, rate)
        self.start_scenario(temp_scenario)

class ScenarioAction:
    """Base class for device scenario actions."""
    
    def __init__(self, duration: Optional[float] = None):
        self.duration = duration
        self.elapsed = 0.0
        self.device: Optional[MockTISDevice] = None
        
    def start(self, device: MockTISDevice):
        """Start the scenario."""
        self.device = device
        self.elapsed = 0.0
        
    async def update(self, dt: float) -> bool:
        """Update scenario. Return True if finished."""
        self.elapsed += dt
        
        # Check if duration-based scenario is finished
        if self.duration and self.elapsed >= self.duration:
            await self.finish()
            return True
            
        # Update scenario logic
        await self.update_logic(dt)
        return False
        
    async def update_logic(self, dt: float):
        """Override in subclasses."""
        pass
        
    async def finish(self):
        """Override in subclasses for cleanup."""
        pass

class MotionScenario(ScenarioAction):
    """Motion detection scenario."""
    
    def __init__(self, duration: float = 10.0):
        super().__init__(duration)
        self.motion_started = False
        
    async def update_logic(self, dt: float):
        """Update motion detection."""
        if not self.motion_started:
            self.device.set_state("motion", True)
            self.device.set_state("last_motion", datetime.now().isoformat())
            self.motion_started = True
            _LOGGER.info(f"Motion detected on device {self.device.name}")
            
    async def finish(self):
        """Clear motion detection."""
        self.device.set_state("motion", False)
        _LOGGER.info(f"Motion cleared on device {self.device.name}")

class DoorActivityScenario(ScenarioAction):
    """Door opening/closing scenario."""
    
    def __init__(self, open_duration: float = 5.0):
        super().__init__(open_duration * 2)  # Open + close duration
        self.open_duration = open_duration
        self.door_opened = False
        self.door_closed = False
        
    async def update_logic(self, dt: float):
        """Update door state."""
        if not self.door_opened and self.elapsed < self.open_duration:
            # Open door
            self.device.set_state("contact", True)  # True = open
            self.device.set_state("last_changed", datetime.now().isoformat())
            self.door_opened = True
            _LOGGER.info(f"Door opened on device {self.device.name}")
            
        elif self.door_opened and not self.door_closed and self.elapsed >= self.open_duration:
            # Close door
            self.device.set_state("contact", False)  # False = closed
            self.device.set_state("last_changed", datetime.now().isoformat())
            self.door_closed = True
            _LOGGER.info(f"Door closed on device {self.device.name}")

class TemperatureChangeScenario(ScenarioAction):
    """Gradual temperature change scenario."""
    
    def __init__(self, target_temp: float, rate: float = 0.1):
        super().__init__()  # No fixed duration
        self.target_temp = target_temp
        self.rate = rate  # degrees per second
        self.initial_temp = None
        
    def start(self, device: MockTISDevice):
        """Start temperature change."""
        super().start(device)
        
        # Get initial temperature
        if device.device_type == 0x0310:  # health_sensor
            sensors = device.get_state().get("sensors", {})
            self.initial_temp = sensors.get("temperature", 23.0)
        else:
            self.initial_temp = device.get_state().get("temperature", 23.0)
            
    async def update_logic(self, dt: float):
        """Update temperature gradually."""
        if self.initial_temp is None:
            return
            
        # Calculate current temperature
        temp_change = self.rate * dt
        
        if self.device.device_type == 0x0310:  # health_sensor
            sensors = self.device.get_state().get("sensors", {})
            current_temp = sensors.get("temperature", self.initial_temp)
            
            # Move toward target
            if current_temp < self.target_temp:
                new_temp = min(self.target_temp, current_temp + temp_change)
            else:
                new_temp = max(self.target_temp, current_temp - temp_change)
                
            sensors["temperature"] = round(new_temp, 1)
            self.device.set_state("sensors", sensors)
            
            # Check if target reached
            if abs(new_temp - self.target_temp) < 0.1:
                return True  # Finished
        else:
            current_temp = self.device.get_state().get("temperature", self.initial_temp)
            
            # Move toward target
            if current_temp < self.target_temp:
                new_temp = min(self.target_temp, current_temp + temp_change)
            else:
                new_temp = max(self.target_temp, current_temp - temp_change)
                
            self.device.set_state("temperature", round(new_temp, 1))
            
            # Check if target reached
            if abs(new_temp - self.target_temp) < 0.1:
                return True  # Finished
                
        return False

# Pre-built scenarios
class TestScenarios:
    """Pre-built test scenarios."""
    
    @staticmethod
    def create_home_day_cycle(simulator: TISDeviceSimulator):
        """Create a full day cycle simulation."""
        scenarios = []
        
        # Morning routine (6:00 AM)
        scenarios.append({
            "time": 6 * 3600,  # 6 AM in seconds
            "actions": [
                ("motion", "04FE", 30.0),  # Motion in bedroom
                ("door_activity", "door_sensor", 2.0),  # Bathroom door
                ("temperature_change", "05FE", 24.0),  # Morning temp
            ]
        })
        
        # Evening routine (6:00 PM)
        scenarios.append({
            "time": 18 * 3600,  # 6 PM
            "actions": [
                ("motion", "04FE", 120.0),  # Motion in living room
                ("temperature_change", "05FE", 22.0),  # Evening temp
            ]
        })
        
        return scenarios
    
    @staticmethod
    def create_security_test(simulator: TISDeviceSimulator):
        """Create security system test scenarios."""
        return [
            ("motion", "04FE", 15.0),  # Intruder motion
            ("door_activity", "door_sensor", 1.0),  # Quick door open
        ]

# Export classes
__all__ = [
    "TISDeviceSimulator",
    "DeviceScenario", 
    "ScenarioAction",
    "MotionScenario",
    "DoorActivityScenario", 
    "TemperatureChangeScenario",
    "TestScenarios"
]