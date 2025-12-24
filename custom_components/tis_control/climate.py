from __future__ import annotations
from TISControlProtocol import *
_I=alpha__("b3BlcmF0aW9uX3ZhbHVl")
_H=alpha__("c3ViX29wZXJhdGlvbg==")
_G=alpha__("bnVtYmVy")
_F=alpha__("ZmVlZGJhY2tfdHlwZQ==")
_E=False
_D=True
_C=alpha__("bWF4")
_B=alpha__("bWlu")
_A=None
from homeassistant.helpers.event import async_track_time_interval
from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any
from TISControlProtocol.api import TISApi
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISPacket,TISProtocolHandler
from homeassistant.components.climate import ATTR_TEMPERATURE,FAN_AUTO,FAN_HIGH,FAN_LOW,FAN_MEDIUM,ClimateEntity,ClimateEntityFeature,HVACMode,UnitOfTemperature
from homeassistant.const import STATE_OFF,STATE_ON,STATE_UNKNOWN
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.import TISConfigEntry
from.const import FAN_MODES,TEMPERATURE_RANGES
handler=TISProtocolHandler()
POLLING_INTERVAL=timedelta(seconds=60)
async def async_setup_entry(hass,entry,async_add_devices):
    H=alpha__("Z2F0ZXdheQ==");G=alpha__("aXNfcHJvdGVjdGVk");F=alpha__("ZGV2aWNlX2lk");E=alpha__("Y2hhbm5lbHM=");B=async_add_devices;A=entry.runtime_data.api;C=await A.get_entities(platform=alpha__("YWM="))
    if C:I=[(C,next(iter(A[E][0].values())),A[F],A[G],A[H])for B in C for(C,A)in B.items()];J=[TISClimate(tis_api=A,ac_name=B,ac_number=C,device_id=D,gateway=E)for(B,C,D,F,E)in I];B(J)
    D=await A.get_entities(platform=alpha__("Zmxvb3JfaGVhdGluZw=="))
    if D:K=[(C,next(iter(A[E][0].values())),A[F],A[G],A[H])for B in D for(C,A)in B.items()];L=[TISFloorHeating(tis_api=A,heater_name=B,heater_number=C,device_id=D,gateway=E)for(B,C,D,F,E)in K];B(L)
class TISClimate(ClimateEntity):
    def __init__(A,tis_api,ac_name,ac_number,device_id,gateway):A.api=tis_api;A._name=ac_name;A.device_id=device_id;A.ac_number=int(ac_number)-1;A._attr_unique_id=beta__("YWNfe19fdmFyMH1fe19fdmFyMX0=", __var0=A.device_id, __var1=A.ac_number);A.gateway=gateway;A._attr_temperature_unit=UnitOfTemperature.CELSIUS;A._unit_index=0 if A._attr_temperature_unit==UnitOfTemperature.CELSIUS else 1;A.update_packet=handler.generate_ac_update_packet(A);A.listener=_A;A._attr_state=STATE_UNKNOWN;A._attr_target_temperature=_A;A._attr_max_temp=_A;A._attr_min_temp=_A;A._attr_target_temperature_step=_A;A.setup_ac()
    def setup_ac(A):A._attr_state=STATE_UNKNOWN;A._attr_target_temperature=_A;A._attr_hvac_mode=_A;A._attr_fan_mode=FAN_MEDIUM;A._attr_max_temp=15;A._attr_min_temp=26;A._attr_target_temperature_step=1 if A._unit_index==0 else 2;A._attr_hvac_modes=[HVACMode.OFF,HVACMode.HEAT,HVACMode.COOL,HVACMode.AUTO,HVACMode.FAN_ONLY];A._attr_supported_features=ClimateEntityFeature.FAN_MODE|ClimateEntityFeature.TARGET_TEMPERATURE|ClimateEntityFeature.TURN_OFF|ClimateEntityFeature.TURN_ON;A._attr_fan_modes=[FAN_AUTO,FAN_LOW,FAN_MEDIUM,FAN_HIGH];A.mode_target_temperatures={HVACMode.COOL:20,HVACMode.HEAT:30,HVACMode.FAN_ONLY:_A,HVACMode.AUTO:20,HVACMode.OFF:_A};A._update_task_unsub=_A
    def _start_polling(A):
        if not A._update_task_unsub:logging.info(beta__("U3RhcnRpbmcgc3RhdGUgcG9sbGluZyBmb3Ige19fdmFyMH0=", __var0=A.name));A._update_task_unsub=async_track_time_interval(A.hass,A._async_poll_for_state,POLLING_INTERVAL)
    def _stop_polling(A):
        if A._update_task_unsub:logging.info(beta__("U3RvcHBpbmcgc3RhdGUgcG9sbGluZyBmb3Ige19fdmFyMH0=", __var0=A.name));A._update_task_unsub();A._update_task_unsub=_A
    async def _async_poll_for_state(A,now=_A):logging.info(beta__("UG9sbGluZyBmb3Igc3RhdGUgb2Yge19fdmFyMH0=", __var0=A.name));await A.api.protocol.sender.send_packet(A.update_packet)

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
        A._start_polling()
        @callback
        async def B(event):
            F=alpha__("cGFja2V0X21vZGVfaW5kZXg=");B=event
            if B.event_type==str(A.device_id):
                E=B.data.get(_F,_A)
                if E==alpha__("YWNfZmVlZGJhY2s="):
                    G=B.data[_G];D=B.data[_H];C=B.data[_I]
                    if A.ac_number==int(G):
                        logging.info(beta__("QUMgZmVlZGJhY2sgZXZlbnQ6IHtfX3ZhcjB9", __var0=B.data))
                        if D==3:
                            if C==0:A._attr_state=STATE_OFF;A._attr_hvac_mode=HVACMode.OFF;logging.info(alpha__("QUMgdHVybmVkIG9mZg=="))
                        else:
                            A._attr_state=STATE_ON
                            if D==4:A._attr_hvac_mode=HVACMode.COOL;A._attr_target_temperature=C;logging.info(beta__("Q29vbCBtb2RlIHRlbXBlcmF0dXJlIHVwZGF0ZWQgdG8ge19fdmFyMH0=", __var0=C))
                            elif D==5:A._attr_fan_mode=next(A for(A,B)in FAN_MODES.items()if B==C);logging.info(beta__("RmFuIHNwZWVkIHVwZGF0ZWQgdG8ge19fdmFyMH0=", __var0=C))
                            elif D==6:A._attr_hvac_mode=next((A for(A,B)in TEMPERATURE_RANGES.items()if B[F]==C),_A);logging.info(beta__("SFZBQyBtb2RlIGNoYW5nZWQgdG8ge19fdmFyMH0=", __var0=C))
                            elif D==7:A._attr_hvac_mode=HVACMode.HEAT;A._attr_target_temperature=C;logging.info(beta__("SGVhdGluZyBtb2RlIHRlbXBlcmF0dXJlIHVwZGF0ZWQgdG8ge19fdmFyMH0=", __var0=C))
                            elif D==8:A._attr_hvac_mode=HVACMode.AUTO;A._attr_target_temperature=C;logging.info(beta__("QXV0byBtb2RlIHRlbXBlcmF0dXJlIHVwZGF0ZWQgdG8ge19fdmFyMH0=", __var0=C))
                            else:logging.error(beta__("VW5rbm93biBzdWIgb3BlcmF0aW9uIGZvciBBQyBmZWVkYmFjazoge19fdmFyMH0=", __var0=D))
                elif E==alpha__("dXBkYXRlX2ZlZWRiYWNr"):
                    if B.data[alpha__("YWNfbnVtYmVy")]==A.ac_number:
                        if B.data[alpha__("c3RhdGU=")]==0:A._attr_state=STATE_OFF;A._attr_hvac_mode=HVACMode.OFF
                        else:
                            A._attr_state=STATE_ON;A._attr_hvac_mode=next((A for(A,C)in TEMPERATURE_RANGES.items()if C[F]==B.data[alpha__("aHZhY19tb2Rl")]),_A);A._attr_fan_mode=next(A for(A,C)in FAN_MODES.items()if C==B.data[alpha__("ZmFuX3NwZWVk")]);A._attr_min_temp=TEMPERATURE_RANGES[A.hvac_mode][_B][A._unit_index];A._attr_max_temp=TEMPERATURE_RANGES[A.hvac_mode][_C][A._unit_index]
                            if A._attr_hvac_mode==HVACMode.COOL:A._attr_target_temperature=B.data[alpha__("Y29vbF90ZW1w")]
                            elif A._attr_hvac_mode==HVACMode.HEAT:A._attr_target_temperature=B.data[alpha__("aGVhdF90ZW1w")]
                            elif A._attr_hvac_mode==HVACMode.AUTO:A._attr_target_temperature=B.data[alpha__("YXV0b190ZW1w")]
                            else:A._attr_target_temperature=_A
                    A._stop_polling()
            A.async_write_ha_state();await A.async_update_ha_state(_D)
        A.listener=A.hass.bus.async_listen(str(A.device_id),B);await A.api.protocol.sender.send_packet(A.update_packet)
    @property
    def name(self):return self._name
    @property
    def is_on(self):
        if self._attr_state==STATE_ON:return _D
        elif self._attr_state==STATE_OFF:return _E
        else:return
    @property
    def temperature_unit(self):return self._attr_temperature_unit
    @property
    def target_temperature(self):return self._attr_target_temperature
    @property
    def hvac_mode(self):return self._attr_hvac_mode
    @property
    def hvac_modes(self):return self._attr_hvac_modes
    @property
    def fan_modes(self):return self._attr_fan_modes
    @property
    def should_poll(self):return _E
    async def async_set_hvac_mode(A,hvac_mode):
        B=hvac_mode
        if B==HVACMode.OFF:C=STATE_OFF;D=_A;E=_A;F=_A
        else:C=STATE_ON;E=TEMPERATURE_RANGES[B][_B][A._unit_index];F=TEMPERATURE_RANGES[B][_C][A._unit_index];D=A.mode_target_temperatures[B]
        G=handler.generate_ac_control_packet(A,TEMPERATURE_RANGES,FAN_MODES,target_state=C,target_temperature=D,target_mode=B);H=await A.api.protocol.sender.send_packet_with_ack(G)
        if H:A._attr_hvac_mode=B;A._attr_state=C;A._attr_min_temp=E;A._attr_max_temp=F;A._attr_target_temperature=D;A._stop_polling()
        else:logging.error(alpha__("RmFpbGVkIHRvIHNldCBodmFjIG1vZGU="));A._attr_state=STATE_UNKNOWN;A._start_polling();A._attr_hvac_mode=_A
        A.async_write_ha_state()
    async def async_set_fan_mode(A,fan_mode):
        B=fan_mode;C=handler.generate_ac_control_packet(A,TEMPERATURE_RANGES,FAN_MODES,target_fan_mode=B);D=await A.api.protocol.sender.send_packet_with_ack(C)
        if D:A._attr_fan_mode=B;A._stop_polling()
        else:logging.error(alpha__("RmFpbGVkIHRvIHNldCBmYW4gbW9kZQ=="));A._attr_state=STATE_UNKNOWN;A._start_polling();A._attr_fan_mode=_A
        A.async_write_ha_state()
    async def async_set_temperature(A,**C):
        B=C.get(ATTR_TEMPERATURE);D=handler.generate_ac_control_packet(A,TEMPERATURE_RANGES,FAN_MODES,target_temperature=B);E=await A.api.protocol.sender.send_packet_with_ack(D)
        if E:A._attr_target_temperature=B;A._stop_polling();A.mode_target_temperatures[A.hvac_mode]=B if B else A.target_temperature
        else:A._attr_state=STATE_UNKNOWN;logging.error(alpha__("RmFpbGVkIHRvIHNldCB0ZW1wZXJhdHVyZQ=="));A._attr_target_temperature=_A;A._attr_hvac_mode=_A;A._start_polling()
        A.async_write_ha_state()
class TISFloorHeating(ClimateEntity):
    def __init__(A,tis_api,heater_name,heater_number,device_id,gateway):A.api=tis_api;A._name=heater_name;A.device_id=device_id;A.heater_number=int(heater_number)-1;A._attr_unique_id=beta__("Zmxvb3JfaGVhdGVyX3tfX3ZhcjB9X3tfX3ZhcjF9", __var0=A.device_id, __var1=A.heater_number);A.gateway=gateway;A._attr_temperature_unit=UnitOfTemperature.CELSIUS;A._unit_index=0 if A._attr_temperature_unit==UnitOfTemperature.CELSIUS else 1;A.update_packet=handler.generate_floor_update_packet(A);A.listener=_A;A._attr_state=STATE_OFF;A._attr_target_temperature=_A;A._attr_max_temp=_A;A._attr_min_temp=_A;A._attr_target_temperature_step=_A;A.setup_heater()
    def setup_heater(A):A._attr_hvac_mode=_A;A._attr_max_temp=TEMPERATURE_RANGES[HVACMode.HEAT][_C][A._unit_index];A._attr_min_temp=TEMPERATURE_RANGES[HVACMode.HEAT][_B][A._unit_index];A._attr_target_temperature=_A;A._attr_target_temperature_step=1 if A._unit_index==0 else 2;A._attr_hvac_modes=[HVACMode.OFF,HVACMode.HEAT];A._attr_supported_features=ClimateEntityFeature.TARGET_TEMPERATURE|ClimateEntityFeature.TURN_OFF|ClimateEntityFeature.TURN_ON;A.mode_target_temperatures={HVACMode.HEAT:30,HVACMode.OFF:_A};A._update_task_unsub=_A
    def _start_polling(A):
        if not A._update_task_unsub:logging.info(beta__("U3RhcnRpbmcgc3RhdGUgcG9sbGluZyBmb3Ige19fdmFyMH0=", __var0=A.name));A._update_task_unsub=async_track_time_interval(A.hass,A._async_poll_for_state,POLLING_INTERVAL)
    def _stop_polling(A):
        if A._update_task_unsub:logging.info(beta__("U3RvcHBpbmcgc3RhdGUgcG9sbGluZyBmb3Ige19fdmFyMH0=", __var0=A.name));A._update_task_unsub();A._update_task_unsub=_A
    async def _async_poll_for_state(A,now=_A):logging.info(beta__("UG9sbGluZyBmb3Igc3RhdGUgb2Yge19fdmFyMH0=", __var0=A.name));await A.api.protocol.sender.send_packet(A.update_packet)

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
        A._start_polling()
        @callback
        async def B(event):
            B=event
            if B.event_type==str(A.device_id):
                E=B.data.get(_F,_A)
                if E==alpha__("Zmxvb3JfZmVlZGJhY2s="):
                    logging.info(beta__("Zmxvb3IgaGVhdGluZyBmZWVkYmFjayBldmVudDoge19fdmFyMH0=", __var0=B.data));F=B.data[_G];D=B.data[_H];C=B.data[_I]
                    if A.heater_number==int(F):
                        A._stop_polling()
                        if D==20:
                            if C==0:A._attr_state=STATE_OFF;A._attr_hvac_mode=HVACMode.OFF;logging.info(alpha__("SGVhdGVyIHR1cm5lZCBvZmY="))
                            else:A._attr_state=STATE_ON;A._attr_hvac_mode=HVACMode.HEAT;A._attr_target_temperature=C;logging.info(beta__("SGVhdGluZyBtb2RlIHRlbXBlcmF0dXJlIHVwZGF0ZWQgdG8ge19fdmFyMH0=", __var0=C))
                        elif D==24:A._attr_target_temperature=C
                        else:logging.error(beta__("VW5rbm93biBzdWIgb3BlcmF0aW9uIGZvciBBQyBmZWVkYmFjazoge19fdmFyMH0=", __var0=D))
                elif E==alpha__("Zmxvb3JfdXBkYXRl"):
                    logging.info(beta__("Zmxvb3IgaGVhdGluZyB1cGRhdGUgZXZlbnQ6IHtfX3ZhcjB9", __var0=B.data))
                    if B.data[alpha__("aGVhdGVyX251bWJlcg==")]==A.heater_number:
                        A._stop_polling()
                        if B.data[alpha__("c3RhdGU=")]==0:A._attr_state=STATE_OFF;A._attr_hvac_mode=HVACMode.OFF
                        else:
                            A._attr_state=STATE_ON;A._attr_hvac_mode=HVACMode.HEAT;A._attr_min_temp=TEMPERATURE_RANGES[A.hvac_mode][_B][A._unit_index];A._attr_max_temp=TEMPERATURE_RANGES[A.hvac_mode][_C][A._unit_index]
                            if A._attr_hvac_mode==HVACMode.HEAT:A._attr_target_temperature=B.data[alpha__("dGVtcA==")]
                            else:A._attr_target_temperature=_A
            A.async_write_ha_state();await A.async_update_ha_state(_D)
        A.listener=A.hass.bus.async_listen(str(A.device_id),B);await A.api.protocol.sender.send_packet(A.update_packet)
    @property
    def name(self):return self._name
    @property
    def is_on(self):
        if self._attr_state==STATE_ON:return _D
        elif self._attr_state==STATE_OFF:return _E
        else:return
    @property
    def temperature_unit(self):return self._attr_temperature_unit
    @property
    def target_temperature(self):return self._attr_target_temperature
    @property
    def hvac_mode(self):return self._attr_hvac_mode
    @property
    def hvac_modes(self):return self._attr_hvac_modes
    @property
    def should_poll(self):return _E
    async def async_set_hvac_mode(A,hvac_mode):B=handler.generate_floor_on_off_packet(A,0 if hvac_mode==HVACMode.OFF else 1);await A.api.protocol.sender.send_packet(B)
    async def async_set_temperature(A,**B):C=B.get(ATTR_TEMPERATURE);D=handler.generate_floor_set_temp_packet(A,int(C));await A.api.protocol.sender.send_packet(D)