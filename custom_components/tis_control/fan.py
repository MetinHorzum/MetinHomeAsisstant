from __future__ import annotations
from TISControlProtocol import *
_B=False
_A=None
from typing import Any
import logging
from homeassistant.components.fan import FanEntity,FanEntityFeature
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from TISControlProtocol.api import TISApi
from.import TISConfigEntry

# Try to import RPi.GPIO for Raspberry Pi support (optional)
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

SUPPORT=FanEntityFeature.SET_SPEED|FanEntityFeature.TURN_OFF|FanEntityFeature.TURN_ON

async def async_setup_entry(hass,entry,async_add_entities):
    """Setup CPU fan only on Raspberry Pi platforms"""
    if not HAS_GPIO:
        logging.info("RPi.GPIO not available - CPU fan control disabled (platform not supported)")
        return
    
    A=entry.runtime_data.api
    async_add_entities([TISCPUFan(hass,alpha__("Q1BVX0Zhbg=="),alpha__("Q1BVIEZhbiBTcGVlZCBDb250cm9sbGVy"),SUPPORT,A)])
class TISCPUFan(FanEntity):
    _attr_should_poll=_B;_attr_translation_key=alpha__("Y3B1")
    def __init__(A,hass,unique_id,name,supported_features,api,pin=13,lower_threshold=40,higher_threshold=50):
        B=supported_features;A._pin=pin;A._state=True;A._higher_temperature_threshold=higher_threshold;A._lower_temperature_threshold=lower_threshold;A._listener=_A;A._api=api;A.hass=hass;A._unique_id=unique_id;A._attr_supported_features=B;A._percentage=_A;A._attr_name=name;A._pwm=_A;A._attr_available=True
        if B&FanEntityFeature.OSCILLATE:A._oscillating=_B
        if B&FanEntityFeature.DIRECTION:A._direction=alpha__("Zm9yd2FyZA==")
        A.setup_light()
    def setup_light(A):
        """Setup GPIO PWM for fan control (Raspberry Pi only)"""
        if not HAS_GPIO:
            logging.warning("GPIO not available - fan control disabled")
            A._attr_available=_B
            return
        try:
            GPIO.setmode(GPIO.BCM);GPIO.setup(A._pin,GPIO.OUT);A._pwm=GPIO.PWM(A._pin,100);A._pwm.start(50)
        except RuntimeError:
            logging.error(alpha__("R1BJTyBQV00gYWxyZWFkeSBpbiB1c2U="))
            A._pwm=_A;A._attr_available=_B
        except Exception as e:
            logging.error(f"Error setting up GPIO: {e}")
            A._pwm=_A;A._attr_available=_B

    @property
    def device_info(self):
        from homeassistant.helpers.entity import DeviceInfo
        return DeviceInfo(
            identifiers={("tis_control", str(self.device_id))},
            name=getattr(self, '_device_name', f"TIS Device {self.device_id}"),
            manufacturer="TIS Control",
            model=getattr(self, '_device_type', "Unknown"),
            sw_version="1.0"
        )
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            try:
                B=event.data.get(alpha__("dGVtcGVyYXR1cmU="))
                if B is _A:return
                if B>A._higher_temperature_threshold:await A.async_turn_on(percentage=100)
                elif B>A._lower_temperature_threshold:await A.async_turn_on(percentage=50)
                else:await A.async_turn_on(percentage=25)
            except Exception as C:logging.error(beta__("RXJyb3IgYWRqdXN0aW5nIGZhbiBzcGVlZDoge19fdmFyMH0=", __var0=C))
        A._listener=A.hass.bus.async_listen(alpha__("Y3B1X3RlbXBlcmF0dXJl"),B)
    @property
    def name(self):return self._attr_name
    @property
    def icon(self):return alpha__("bWRpOmZhbg==")
    @property
    def is_on(self):return self._state
    @property
    def unique_id(self):return self._unique_id
    @property
    def percentage(self):return self._percentage
    def log_fan_state(A):logging.info(beta__("RmFuIFN0YXRlIC0gUGVyY2VudGFnZToge19fdmFyMH0sIFRlbXBlcmF0dXJlIFJhbmdlOiB7X192YXIxfS17X192YXIyfQ==", __var0=A._percentage, __var1=A._lower_temperature_threshold, __var2=A._higher_temperature_threshold))
    @property
    def supported_features(self):return self._attr_supported_features
    async def async_will_remove_from_hass(A):
        if A._listener:A._listener()
        if A._pwm and HAS_GPIO:
            try:A._pwm.stop();GPIO.cleanup(A._pin)
            except Exception as B:logging.error(beta__("RXJyb3IgY2xlYW5pbmcgdXAgR1BJTzoge19fdmFyMH0=", __var0=B))
    async def async_set_percentage(A,percentage):
        if not A._pwm:
            logging.warning("PWM not available - cannot set fan speed")
            return
        A._percentage=percentage;A._pwm.ChangeDutyCycle(A._percentage);A._state=True;A.async_write_ha_state()
    async def async_turn_on(B,percentage=_A,**C):
        A=percentage
        if A is _A:A=50
        await B.async_set_percentage(A)
    async def async_turn_off(A,**B):
        if not A._pwm:
            return
        A._pwm.ChangeDutyCycle(0);A._state=_B;A.async_write_ha_state()