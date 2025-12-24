from __future__ import annotations
from TISControlProtocol import *
_G=alpha__("bG9ja2Vk")
_F=alpha__("YWRtaW5fbG9jaw==")
_E=alpha__("SW52YWxpZCBwYXNzd29yZA==")
_D=alpha__("dXNlcg==")
_C=True
_B=alpha__("Y29kZQ==")
_A=False
from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from.const import DOMAIN
from TISControlProtocol.api import TISApi
import asyncio,logging
async def async_setup_entry(hass,entry,async_add_devices):
    B=entry.runtime_data.api;A=await B.get_entities(platform=alpha__("bG9ja19tb2R1bGU="))
    if A is None:logging.error(alpha__("Tm8gbG9jayBtb2R1bGUgZm91bmQgaW4gdGhlIGNvbmZpZ3VyYXRpb24="));return
    else:async_add_devices([TISControlLock(alpha__("QWRtaW4gTG9jaw=="),A[alpha__("cGFzc3dvcmQ=")])])

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
class TISControlLock(LockEntity):
    def __init__(A,name,password):A._attr_name=name;A.unique_id=beta__("bG9ja197X192YXIwfQ==", __var0=A.name);A._attr_is_locked=_C;A._attr_password=password;A._attr_changed_by=None;A._attr_code_format=alpha__("Lio=");A._attr_is_locking=_A;A._attr_is_unlocking=_A;A._attr_is_opening=_A;A._attr_is_open=_A;A._attr_timeout=60
    @property
    def name(self):return self._attr_name
    @property
    def is_locked(self):return self._attr_is_locked
    async def async_lock(A,**B):
        if _B in B and B[_B]==A._attr_password:A._attr_is_locked=_C;A._attr_changed_by=_D;A.hass.bus.async_fire(str(_F),{_G:_C})
        else:raise ValueError(_E)
    async def async_unlock(A,**B):
        if _B in B and B[_B]==A._attr_password:
            A._attr_is_locked=_A;A._attr_changed_by=_D;A.hass.bus.async_fire(str(_F),{_G:_A})
            if hasattr(A,alpha__("X2F1dG9fbG9ja190YXNr"))and A._auto_lock_task:A._auto_lock_task.cancel()
            A._auto_lock_task=asyncio.create_task(A.auto_lock())
        else:raise ValueError(_E)
    async def auto_lock(A):await asyncio.sleep(A._attr_timeout);await A.async_lock(code=A._attr_password)
    async def async_open(A,**B):
        if _B in B and B[_B]==A._attr_password:A._attr_is_open=_C;A._attr_changed_by=_D
        else:raise ValueError(_E)