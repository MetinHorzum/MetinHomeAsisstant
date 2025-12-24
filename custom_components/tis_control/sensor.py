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
try:
    from gpiozero import CPUTemperature
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False
    CPUTemperature = None
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
    B=hass;A=entry.runtime_data.api;await A.get_bill_configs();J=[]
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
    P=CPUTemperatureSensor(B);J.append(P);async_add_devices(J)
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
class CoordinatedLUXSensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number):C=channel_number;B=device_id;D=get_coordinator(hass,tis_api,B,gateway,_D,C);super().__init__(D,name,B);A._attr_icon=alpha__("bWRpOmJyaWdodG5lc3MtNg==");A.name=name;A.device_id=B;A.channel_number=C;A._attr_unique_id=beta__("c2Vuc29yX3tfX3ZhcjB9", __var0=A.name)

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
        await super().async_added_to_hass()
        @callback
        def B(event):
            B=event
            try:
                if B.data[_B]==_K:A._state=int(B.data[alpha__("bHV4")])
                A.async_write_ha_state()
            except Exception as C:logging.error(beta__("ZXZlbnQgZGF0YSBlcnJvciBmb3IgbHV4OiB7X192YXIwfQ==", __var0=B.data))
        A.hass.bus.async_listen(str(A.device_id),B)
    def _update_state(A,data):0
class CoordinatedHealthSensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number,key=_A,sensor_type=alpha__("c2Vuc29y")):C=channel_number;B=device_id;D=get_coordinator(hass,tis_api,B,gateway,_D,C);super().__init__(D,name,B);A._attr_icon=alpha__("bWRpOmhlYXJ0LXB1bHNl");A.name=name;A.device_id=B;A.channel_number=C;A._attr_unique_id=beta__("c2Vuc29yX3tfX3ZhcjB9", __var0=A.name);A._key=key;A._sensor_type=sensor_type;A.states=HEALTH_STATES
    def calculate_health_percentage(O,health):
        B=health;A=B[alpha__("dGVtcA==")]
        if A is _A:C=0
        elif 20<=A<=26:C=100
        elif 16<=A<=19 or 27<=A<=29:C=75
        elif 11<=A<=15 or 30<=A<=34:C=50
        elif 6<=A<=10 or 35<=A<=39:C=25
        else:C=0
        F=B[alpha__("aHVtaWRpdHk=")]
        if F is _A:G=0
        elif 30<=F<=50:G=100
        elif 10<=F<=29 or 51<=F<=80:G=50
        else:G=0
        E=B[alpha__("bm9pc2U=")]
        if E is _A:D=0
        elif 0<=E<=20:D=100
        elif 21<=E<=100:D=75
        elif 101<=E<=300:D=50
        elif 301<=E<=500:D=25
        else:D=0
        def H(value):
            A=value
            if A==1:return 100
            elif A==2:return 75
            elif A==3:return 50
            elif A==4:return 25
            else:return 0
        I=B[alpha__("Y29fc3RhdGU=")];J=B[alpha__("ZWNvMl9zdGF0ZQ==")];K=B[alpha__("dHZvY19zdGF0ZQ==")];L=H(J);M=H(K);N=(C+G+D+L+M)/5
        if I in(1,2):return N
        else:return .0

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
        await super().async_added_to_hass()
        @callback
        def B(event):
            B=event
            try:
                if B.data[_B]==_K:
                    logging.info(beta__("SGVhbHRoIGZlZWRiYWNrIHJlY2VpdmVkOiB7X192YXIwfQ==", __var0=B.data))
                    if A._sensor_type==_H:A._state=A.calculate_health_percentage(B.data)
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
        else:raise ValueError(alpha__("bWluIGFuZCBtYXggY2FwYWNpdHkgdmFsdWVzIGFyZSByZXF1aXJlZCBmb3IgYW5hbG9nIHNlbnNvcnM="))

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
class CPUTemperatureSensor(SensorEntity):
    def __init__(A,hass):
        A._hass=hass;A._attr_name=alpha__("Q1BVIFRlbXBlcmF0dXJlIFNlbnNvcg==");A._attr_icon=_J;A._attr_update_interval=timedelta(seconds=10);A._attr_unique_id=beta__("c2Vuc29yX3tfX3ZhcjB9", __var0=A.name)
        if HAS_GPIOZERO:
            A._cpu=CPUTemperature();A._state=A._cpu.temperature
        else:
            try:
                import psutil
                A._cpu=None;A._state=psutil.sensors_temperatures().get('coretemp',[{'current':0}])[0]['current'] if hasattr(psutil,'sensors_temperatures') else 0
            except:
                A._cpu=None;A._state=0
        async_track_time_interval(A._hass,A.async_update,A._attr_update_interval)
    async def async_update(A,event_time):
        if HAS_GPIOZERO and A._cpu:
            A._state=A._cpu.temperature
        else:
            try:
                import psutil
                A._state=psutil.sensors_temperatures().get('coretemp',[{'current':0}])[0]['current'] if hasattr(psutil,'sensors_temperatures') else 0
            except:
                A._state=0
        A.hass.bus.async_fire(alpha__("Y3B1X3RlbXBlcmF0dXJl"),{alpha__("dGVtcGVyYXR1cmU="):int(A._state)});A.async_write_ha_state()
    @property
    def should_poll(self):return False
    @property
    def state(self):return self._state
    @property
    def unit_of_measurement(self):return UnitOfTemperature.CELSIUS
    @property
    def name(self):return self._attr_name
class CoordinatedEnergySensor(BaseSensorEntity,SensorEntity):
    def __init__(A,hass,tis_api,gateway,name,device_id,channel_number,key=_A,sensor_type=_A):E=sensor_type;D=channel_number;C=tis_api;B=device_id;F=get_coordinator(hass,C,B,gateway,E,D);super().__init__(F,name,B);A._attr_icon=_L;A.api=C;A.name=name;A.device_id=B;A.channel_number=D;A._attr_unique_id=beta__("ZW5lcmd5X3tfX3ZhcjB9", __var0=A.name);A._key=key;A.sensor_type=E;A._attr_state_class=alpha__("bWVhc3VyZW1lbnQ=")

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
        await super().async_added_to_hass()
        @callback
        def B(event):
            I=alpha__("cHJpY2VfcGVyX2t3");H=alpha__("bW9udGhseV9lbmVyZ3lfZmVlZGJhY2s=");F=alpha__("ZW5lcmd5");E=alpha__("Y2hhbm5lbF9udW0=");B=event
            try:
                if B.data[_B]==alpha__("ZW5lcmd5X2ZlZWRiYWNr")and A.sensor_type==_C:
                    if B.data[E]==A.channel_number:A._state=float(B.data[F].get(A._key,_A))
                elif B.data[_B]==H and A.sensor_type==_F:
                    if B.data[E]==A.channel_number:A._state=B.data[F]
                elif B.data[_B]==H and A.sensor_type==_G:
                    if B.data[E]==A.channel_number:
                        J=datetime.now().month;K=J in[6,7,8,9];C=A.api.bill_configs.get(alpha__("c3VtbWVyX3JhdGVz"),{})if K else A.api.bill_configs.get(alpha__("d2ludGVyX3JhdGVz"),{});G=B.data[F];D=_A
                        for(L,M)in enumerate(C):
                            if G<M[alpha__("bWluX2t3")]:D=C[L-1][I];break
                        if D is _A and len(C)>0:D=C[-1][I]
                        A._state=int(D*G)
                A.async_write_ha_state()
            except Exception as N:logging.error(beta__("ZXJyb3IgaW4gc2VsZi5uYW1lOiB7X192YXIwfSwgc2VsZi5fa2V5OiB7X192YXIxfSwgc2VsZi5zZW5zb3JfdHlwZToge19fdmFyMn0=", __var0=A.name, __var1=A._key, __var2=A.sensor_type));logging.error(beta__("ZXZlbnQgZGF0YSBlcnJvciBmb3IgZW5lcmd5IHNlbnNvcjoge19fdmFyMH0gXG4gZXJyb3I6IHtfX3ZhcjF9", __var0=B.data, __var1=N))
        A.hass.bus.async_listen(str(A.device_id),B)
    def _update_state(A,data):0
    @property
    def native_value(self):return self.state
RELEVANT_TYPES={alpha__("bHV4X3NlbnNvcg=="):CoordinatedLUXSensor,alpha__("dGVtcGVyYXR1cmVfc2Vuc29y"):CoordinatedTemperatureSensor,_E:CoordinatedAnalogSensor,_C:CoordinatedEnergySensor,_D:CoordinatedHealthSensor}