from __future__ import annotations
from TISControlProtocol import *
_D=alpha__("ZGV2aWNlX2lk")
_C=alpha__("dmFjYXRpb24=")
_B=alpha__("ZGlzYXJt")
_A=None
from homeassistant.components.select import SelectEntity
from TISControlProtocol.api import TISApi
from homeassistant.const import MATCH_ALL,STATE_UNAVAILABLE
from homeassistant.core import callback,Event,HomeAssistant
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISPacket,TISProtocolHandler
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.import TISConfigEntry
import logging
SECURITY_OPTIONS={_C:1,alpha__("YXdheQ=="):2,alpha__("bmlnaHQ="):3,_B:6}
SECURITY_FEEDBACK_OPTIONS={1:_C,2:alpha__("YXdheQ=="),3:alpha__("bmlnaHQ="),6:_B}
handler=TISProtocolHandler()
async def async_setup_entry(hass,entry,async_add_devices):
    A=entry.runtime_data.api;B=await A.get_entities(platform=alpha__("c2VjdXJpdHk="))
    if B:C=[(C,next(iter(A[alpha__("Y2hhbm5lbHM=")][0].values())),A[_D],A[alpha__("Z2F0ZXdheQ==")])for B in B for(C,A)in B.items()];D=[TISSecurity(api=A,name=B,options=list(SECURITY_OPTIONS.keys()),initial_option=_B,channel_number=C,device_id=D,gateway=E)for(B,C,D,E)in C];async_add_devices(D)
protocol_handler=TISProtocolHandler()
class TISSecurity(SelectEntity):
    def __init__(A,api,name,options,initial_option,channel_number,device_id,gateway):A._name=name;A.api=api;A.unique_id=beta__("c2VsZWN0X3tfX3ZhcjB9", __var0=A.name);A._attr_options=options;A._attr_current_option=A._state=initial_option;A._attr_icon=alpha__("bWRpOnNoaWVsZA==");A._attr_is_protected=True;A._attr_read_only=True;A._listener=_A;A.channel_number=int(channel_number);A.device_id=device_id;A.gateway=gateway;A.update_packet=protocol_handler.generate_update_security_packet(A)
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            E=alpha__("ZmVlZGJhY2tfdHlwZQ==");B=event
            if B.event_type==alpha__("YWRtaW5fbG9jaw=="):
                logging.info(beta__("YWRtaW4gbG9jayBldmVudDoge19fdmFyMH0=", __var0=B.data))
                if B.data.get(alpha__("bG9ja2Vk")):A.protect()
                else:A.unprotect()
            if B.data.get(E)==alpha__("c2VjdXJpdHlfZmVlZGJhY2s=")or B.data.get(E)==alpha__("c2VjdXJpdHlfdXBkYXRl"):
                logging.info(beta__("c2VjdXJpdHkgZmVlZGJhY2sgZXZlbnQ6IHtfX3ZhcjB9", __var0=B.data))
                if A.channel_number==B.data[alpha__("Y2hhbm5lbF9udW1iZXI=")]and A.device_id==B.data[_D]:
                    C=B.data[alpha__("bW9kZQ==")]
                    if C in SECURITY_FEEDBACK_OPTIONS:D=SECURITY_FEEDBACK_OPTIONS[C];logging.info(beta__("bW9kZToge19fdmFyMH0sIG9wdGlvbjoge19fdmFyMX0=", __var0=C, __var1=D));A._state=A._attr_current_option=D
            A.async_write_ha_state()
        A._listener=A.hass.bus.async_listen(MATCH_ALL,B);await A.api.protocol.sender.send_packet(A.update_packet);logging.info(beta__("dXBkYXRlIHBhY2tldCBzZW50OiB7X192YXIwfQ==", __var0=A.update_packet));logging.info(beta__("bGlzdGVuZXIgYWRkZWQ6IHtfX3ZhcjB9", __var0=A._listener))
    @property
    def name(self):return self._name
    @property
    def options(self):return self._attr_options
    @property
    def current_option(self):return self._attr_current_option if self._attr_current_option in SECURITY_FEEDBACK_OPTIONS.values()else _A
    def protect(A):A._attr_read_only=True
    def unprotect(A):A._attr_read_only=False
    async def async_select_option(A,option):
        B=option
        if A._attr_is_protected:
            if A._attr_read_only:A._state=A._attr_current_option=STATE_UNAVAILABLE;logging.error(alpha__("cmVzZXR0aW5nIHN0YXRlIHRvIGxhc3Qga25vd24gc3RhdGU="));await A.api.protocol.sender.send_packet(A.update_packet);A.async_write_ha_state();raise ValueError(alpha__("VGhlIHNlY3VyaXR5IG1vZHVsZSBpcyBwcm90ZWN0ZWQgYW5kIHJlYWQgb25seQ=="))
            else:
                logging.info(beta__("c2V0dGluZyBzZWN1cml0eSBtb2RlIHRvIHtfX3ZhcjB9", __var0=B));C=SECURITY_OPTIONS.get(B,_A)
                if C:
                    logging.info(beta__("bW9kZToge19fdmFyMH0=", __var0=C));D=handler.generate_control_security_packet(A,C);E=await A.api.protocol.sender.send_packet_with_ack(D);logging.info(beta__("Y29udHJvbF9wYWNrZXQ6IHtfX3ZhcjB9", __var0=D));logging.info(beta__("YWNrOiB7X192YXIwfQ==", __var0=E))
                    if E:logging.info(beta__("c2V0dGluZyBzdGF0ZSB0byB7X192YXIwfQ==", __var0=B));A._state=A._attr_current_option=B;A.async_write_ha_state()
                    else:logging.warning(beta__("RmFpbGVkIHRvIHNldCBzZWN1cml0eSBtb2RlIHRvIHtfX3ZhcjB9", __var0=B));A._state=A._attr_current_option=_A;A.async_write_ha_state()
        if B not in A._attr_options:raise ValueError(beta__("SW52YWxpZCBvcHRpb246IHtfX3ZhcjB9IChwb3NzaWJsZSBvcHRpb25zOiB7X192YXIxfSk=", __var0=B, __var1=A._attr_options))