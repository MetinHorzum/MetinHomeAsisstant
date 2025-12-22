from __future__ import annotations
from TISControlProtocol import *
_L=alpha__("bWRpOmN1cnJlbnQtYWM=")
_K=alpha__("aGVhbHRoX2ZlZWRiYWNr")
_J=alpha__("bWRpOnRoZXJtb21ldGVy")
_I=alpha__("dGVtcF9zZW5zb3I=")
_H=alpha__("bW9uaXRvcg==")
_G=alpha__("YmlsbF9lbmVyZ3lfc2Vuc29y")
_F=alpha__("bW9udGhseV9lbmVyZ3lfc2Vuc29y")
_E=alpha__("YW5hbG9nX3NlbnNvcg==")
_D=alpha__("aGVhbHRoX3NlbnNvcg==")
_C=alpha__("ZW5lcmd5X3NlbnNvcg==")
_B=alpha__("ZmVlZGJhY2tfdHlwZQ==")
_A=None
from datetime import timedelta
import logging,json
from TISControlProtocol.api import TISApi
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISProtocolHandler
from homeassistant.components.sensor import SensorEntity,UnitOfTemperature
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from.import TISConfigEntry
from.coordinator import SensorUpdateCoordinator
from.entities import BaseSensorEntity
from.const import ENERGY_SENSOR_TYPES,HEALTH_SENSOR_TYPES,HEALTH_STATES
from datetime import datetime
class TISSensorEntity:
    def __init__(A,device_id,api,gateway,channel_number):A.device_id=device_id;A.api=api;A.gateway=gateway;A.channel_number=channel_number
async def async_setup_entry(hass,entry,async_add_devices):
    B=hass;A=entry.runtime_data.api;J=[]
    for(I,D)in RELEVANT_TYPES.items():
        K=await A.get_entities(platform=I)
        if K and len(K)>0:
            N=[(C,next(iter(A[alpha__("Y2hhbm5lbHM=")][0].values())),A[alpha__("ZGV2aWNlX2lk")],A[alpha__("aXNfcHJvdGVjdGVk")],A[alpha__("Z2F0ZXdheQ==")],A[alpha__("bWlu")],A[alpha__("bWF4")],A[alpha__("c2V0dGluZ3M=")])for B in K for(C,A)in B.items()];C=[]
            for(E,F,G,Q,H,min,max,O)in N:
                if I==_E:C.append(D(hass=B,tis_api=A,gateway=H,name=E,device_id=G,channel_number=F,min=min,max=max,settings=O))
                elif I==_C:
                    for(L,M)in ENERGY_SENSOR_TYPES.items():C.append(D(hass=B,tis_api=A,gateway=H,name=beta__("e19fdmFyMH0ge19fdmFyMX0=", __var0=M, __var1=E),device_id=G,channel_number=F,key=L,sensor_type=_C))
                    C.append(D(hass=B,tis_api=A,gateway=H,name=beta__("TW9udGhseSBFbmVyZ3kge19fdmFyMH0=", __var0=E),device_id=G,channel_number=F,sensor_type=_F));C.append(D(hass=B,tis_api=A,gateway=H,name=beta__("QmlsbCB7X192YXIwfQ==", __var0=E),device_id=G,channel_number=F,sensor_type=_G))
                elif I==_D:
                    for(L,M)in HEALTH_SENSOR_TYPES.items():C.append(D(hass=B,tis_api=A,gateway=H,name=beta__("e19fdmFyMH0ge19fdmFyMX0=", __var0=M, __var1=E),device_id=G,channel_number=F,key=L))
                    C.append(D(hass=B,tis_api=A,gateway=H,name=beta__("SGVhbHRoIE1vbml0b3Ige19fdmFyMH0=", __var0=E),device_id=G,channel_number=F,key=alpha__("Tm9uZQ=="),sensor_type=_H))
                else:C.append(D(hass=B,tis_api=A,gateway=H,name=E,device_id=G,channel_number=F))
            J.extend(C)
    async_add_devices(J)
def get_coordinator(hass,tis_api,device_id,gateway,coordinator_type,channel_number):
    G=channel_number;F=tis_api;D=device_id;A=coordinator_type;E=beta__("e19fdmFyMH1fe19fdmFyMX0=", __var0=tuple(D), __var1=A)if _C not in A else beta__("e19fdmFyMH1fe19fdmFyMX1fe19fdmFyMn0=", __var0=tuple(D), __var1=A, __var2=G)
    if E not in coordinators:
        B=TISSensorEntity(D,F,gateway,G)
        if A==_I:C=protocol_handler.generate_temp_sensor_update_packet(entity=B)
        elif A==_D:C=protocol_handler.generate_health_sensor_update_packet(entity=B)
        elif A==_E:C=protocol_handler.generate_update_analog_packet(entity=B)
        elif A==_C:C=protocol_handler.generate_update_energy_packet(entity=B)
        elif A==_F:C=protocol_handler.generate_update_monthly_energy_packet(entity=B)
        elif A==_G:C=protocol_handler.generate_update_monthly_energy_packet(entity=B)
        coordinators[E]=SensorUpdateCoordinator(hass,F,timedelta(seconds=30),D,C)
    return coordinators[E]
protocol_handler=TISProtocolHandler()
_LOGGER=logging.getLogger(__name__)
coordinators={}
class CoordinatedTemperatureSensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number):C=channel_number;B=device_id;D=get_coordinator(hass,tis_api,B,gateway,_I,C);super().__init__(D,name,B);A._attr_icon=_J;A.name=name;A.device_id=B;A.channel_number=C;A._attr_unique_id=beta__("c2Vuc29yX3tfX3ZhcjB9", __var0=A.name)
    async def async_added_to_hass(A):
        await super().async_added_to_hass()
        @callback
        def B(event):
            B=event
            try:
                if B.data[_B]==alpha__("dGVtcF9mZWVkYmFjaw=="):A._state=B.data[alpha__("dGVtcA==")]
                A.async_write_ha_state()
            except Exception as C:logging.error(beta__("ZXZlbnQgZGF0YSBlcnJvciBmb3IgdGVtcGVyYXR1cmU6IHtfX3ZhcjB9", __var0=B.data))
        A.hass.bus.async_listen(str(A.device_id),B)
    def _update_state(A,data):0
    @property
    def unit_of_measurement(self):return UnitOfTemperature.CELSIUS
class CoordinatedHealthSensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number,key=_A,sensor_type=alpha__("c2Vuc29y")):C=channel_number;B=device_id;D=get_coordinator(hass,tis_api,B,gateway,_D,C);super().__init__(D,name,B);A._attr_icon=alpha__("bWRpOmhlYXJ0LXB1bHNl");A.name=name;A.device_id=B;A.channel_number=C;A._attr_unique_id=beta__("c2Vuc29yX3tfX3ZhcjB9", __var0=A.name);A._key=key;A._sensor_type=sensor_type;A.states=HEALTH_STATES
    async def async_added_to_hass(A):
        await super().async_added_to_hass()
        @callback
        def B(event):
            B=event
            try:
                if B.data[_B]==_K:
                    logging.info(beta__("SGVhbHRoIGZlZWRiYWNrIHJlY2VpdmVkOiB7X192YXIwfQ==", __var0=B.data))
                    if A._sensor_type==_H:A._state=50  # Simplified health calculation
                    else:
                        A._state=int(B.data.get(A._key,_A))
                        if A._key.find(alpha__("c3RhdGU="))!=-1:A._state=A.states.get(str(A._state),_A)
                A.async_write_ha_state()
            except Exception as C:logging.error(beta__("ZXZlbnQgZGF0YSBlcnJvciBmb3IgaGVhbHRoOiB7X192YXIwfQ==", __var0=B.data))
        A.hass.bus.async_listen(str(A.device_id),B)
    def _update_state(A,data):0
class CoordinatedAnalogSensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number,min=0,max=100,settings=_A):
        D=channel_number;C=device_id;B=settings;E=get_coordinator(hass,tis_api,C,gateway,_E,D);super().__init__(E,name,C);A._attr_icon=_L;A.name=name;A.device_id=C;A.channel_number=D;A.min=min;A.max=max;A._attr_unique_id=beta__("c2Vuc29yX3tfX3ZhcjB9", __var0=A.name)
        if B:B=json.loads(B);A.min_capacity=int(B.get(alpha__("bWluX2NhcGFjaXR5"),0));A.max_capacity=int(B.get(alpha__("bWF4X2NhcGFjaXR5"),100))
        else:A.min_capacity=0;A.max_capacity=100
    async def async_added_to_hass(A):
        await super().async_added_to_hass()
        @callback
        def B(event):
            B=event
            try:
                if B.data[_B]==alpha__("YW5hbG9nX2ZlZWRiYWNr"):D=float(B.data[alpha__("YW5hbG9n")][A.channel_number-1]);C=(D-A.min)/(A.max-A.min);C=max(0,min(1,C));A._state=A.min_capacity+(A.max_capacity-A.min_capacity)*C
                A.async_write_ha_state()
            except Exception as E:logging.error(beta__("ZXZlbnQgZGF0YSBlcnJvciBmb3IgYW5hbG9nIHNlbnNvcjoge19fdmFyMH0gXG4gZXJyb3I6IHtfX3ZhcjF9", __var0=B.data, __var1=E))
        A.hass.bus.async_listen(str(A.device_id),B)
    def _update_state(A,data):0
class CoordinatedEnergySensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number,key=_A,sensor_type=_A):E=sensor_type;D=channel_number;C=tis_api;B=device_id;F=get_coordinator(hass,C,B,gateway,E,D);super().__init__(F,name,B);A._attr_icon=_L;A.api=C;A.name=name;A.device_id=B;A.channel_number=D;A._attr_unique_id=beta__("ZW5lcmd5X3tfX3ZhcjB9", __var0=A.name);A._key=key;A.sensor_type=E;A._attr_state_class=alpha__("bWVhc3VyZW1lbnQ=")
    async def async_added_to_hass(A):
        await super().async_added_to_hass()
        @callback
        def B(event):
            B=event
            try:
                if B.data[_B]==alpha__("ZW5lcmd5X2ZlZWRiYWNr")and A.sensor_type==_C:A._state=float(B.data[alpha__("ZW5lcmd5")].get(A._key,_A))
                elif B.data[_B]==alpha__("bW9udGhseV9lbmVyZ3lfZmVlZGJhY2s=")and A.sensor_type in(_F,_G):A._state=B.data[alpha__("ZW5lcmd5")]
                A.async_write_ha_state()
            except Exception as C:logging.error(beta__("ZXJyb3IgaW4gZW5lcmd5IHNlbnNvcjoge19fdmFyMH0=", __var0=C))
        A.hass.bus.async_listen(str(A.device_id),B)
    def _update_state(A,data):0
    @property
    def native_value(self):return self.state
RELEVANT_TYPES={alpha__("dGVtcGVyYXR1cmVfc2Vuc29y"):CoordinatedTemperatureSensor,_E:CoordinatedAnalogSensor,_C:CoordinatedEnergySensor,_D:CoordinatedHealthSensor}