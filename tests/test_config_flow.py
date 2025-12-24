"""Test TIS Home Automation config flow."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from custom_components.tis_home_automation import config_flow
from custom_components.tis_home_automation.const import (
    DOMAIN,
    CONF_LOCAL_IP,
    CONF_COMMUNICATION_TYPE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_DISCOVERY_TIMEOUT,
    COMMUNICATION_TYPE_UDP,
    COMMUNICATION_TYPE_RS485,
)

pytestmark = pytest.mark.asyncio

class TestTISConfigFlow:
    """Test TIS config flow."""

    async def test_form_user_step(self, hass: HomeAssistant, mock_tis_protocol):
        """Test user step shows form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_form_user_step_missing_protocol(self, hass: HomeAssistant):
        """Test user step aborts when TIS protocol is missing."""
        with patch(
            'custom_components.tis_home_automation.config_flow.HAS_TIS_PROTOCOL',
            False
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
            assert result["reason"] == "missing_tis_protocol"

    async def test_form_communication_step(self, hass: HomeAssistant, mock_tis_protocol):
        """Test communication type selection step."""
        # Start flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        # Submit user step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_name": "Test TIS Integration"}
        )
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "communication"
        assert result["errors"] == {}

    async def test_udp_config_step(self, hass: HomeAssistant, mock_tis_protocol):
        """Test UDP configuration step."""
        # Start flow and go to communication step
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_name": "Test TIS Integration"}
        )
        
        # Select UDP communication
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP}
        )
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "udp_config"
        assert result["errors"] == {}

    async def test_serial_config_step(self, hass: HomeAssistant, mock_tis_protocol):
        """Test RS485 serial configuration step."""
        # Mock serial ports available
        with patch(
            'custom_components.tis_home_automation.config_flow.get_available_serial_ports',
            return_value=["/dev/ttyUSB0", "/dev/ttyUSB1"]
        ):
            # Start flow and go to communication step
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Integration"}
            )
            
            # Select RS485 communication
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_RS485}
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["step_id"] == "serial_config"
            assert result["errors"] == {}

    async def test_udp_config_connection_test_success(self, hass: HomeAssistant, mock_tis_protocol):
        """Test successful UDP connection test."""
        with patch.object(config_flow.TISConfigFlow, '_test_udp_connection') as mock_test:
            mock_test.return_value = {"success": True}
            
            # Start flow through UDP config
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Integration"}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP}
            )
            
            # Configure UDP settings
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_LOCAL_IP: "192.168.1.100",
                    CONF_PORT: 6000
                }
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["step_id"] == "discovery"
            assert result["errors"] == {}

    async def test_udp_config_connection_test_failure(self, hass: HomeAssistant, mock_tis_protocol):
        """Test failed UDP connection test."""
        with patch.object(config_flow.TISConfigFlow, '_test_udp_connection') as mock_test:
            mock_test.return_value = {"success": False, "error": "udp_connection_failed"}
            
            # Start flow through UDP config
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Integration"}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP}
            )
            
            # Configure UDP settings with invalid data
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_LOCAL_IP: "192.168.1.100",
                    CONF_PORT: 6000
                }
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["step_id"] == "udp_config"
            assert result["errors"]["base"] == "udp_connection_failed"

    async def test_discovery_step_success(self, hass: HomeAssistant, mock_tis_protocol):
        """Test successful device discovery."""
        with patch.object(config_flow.TISConfigFlow, '_test_udp_connection') as mock_test_udp, \
             patch.object(config_flow.TISConfigFlow, '_perform_device_discovery') as mock_discovery:
            
            mock_test_udp.return_value = {"success": True}
            mock_discovery.return_value = {
                "success": True,
                "devices": {"01FE": MagicMock()},
                "count": 1
            }
            
            # Complete flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Integration"}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_LOCAL_IP: "192.168.1.100",
                    CONF_PORT: 6000
                }
            )
            
            # Complete discovery
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_DISCOVERY_TIMEOUT: 30.0}
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["title"] == "TIS Home Automation (1 cihaz)"
            assert result["data"][CONF_LOCAL_IP] == "192.168.1.100"
            assert result["data"][CONF_PORT] == 6000
            assert result["data"][CONF_COMMUNICATION_TYPE] == COMMUNICATION_TYPE_UDP

    async def test_discovery_step_failure(self, hass: HomeAssistant, mock_tis_protocol):
        """Test failed device discovery."""
        with patch.object(config_flow.TISConfigFlow, '_test_udp_connection') as mock_test_udp, \
             patch.object(config_flow.TISConfigFlow, '_perform_device_discovery') as mock_discovery:
            
            mock_test_udp.return_value = {"success": True}
            mock_discovery.return_value = {
                "success": False,
                "error": "discovery_failed"
            }
            
            # Start flow through discovery
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Integration"}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_LOCAL_IP: "192.168.1.100",
                    CONF_PORT: 6000
                }
            )
            
            # Fail discovery
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_DISCOVERY_TIMEOUT: 30.0}
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["step_id"] == "discovery"
            assert result["errors"]["base"] == "discovery_failed"

    async def test_serial_flow_complete(self, hass: HomeAssistant, mock_tis_protocol):
        """Test complete serial configuration flow."""
        with patch(
            'custom_components.tis_home_automation.config_flow.get_available_serial_ports',
            return_value=["/dev/ttyUSB0"]
        ), \
        patch.object(config_flow.TISConfigFlow, '_test_serial_connection') as mock_test_serial, \
        patch.object(config_flow.TISConfigFlow, '_perform_device_discovery') as mock_discovery:
            
            mock_test_serial.return_value = {"success": True}
            mock_discovery.return_value = {
                "success": True,
                "devices": {"01FE": MagicMock()},
                "count": 1
            }
            
            # Complete serial flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Serial"}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_RS485}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_SERIAL_PORT: "/dev/ttyUSB0",
                    CONF_BAUDRATE: 9600
                }
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_DISCOVERY_TIMEOUT: 30.0}
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["data"][CONF_SERIAL_PORT] == "/dev/ttyUSB0"
            assert result["data"][CONF_BAUDRATE] == 9600
            assert result["data"][CONF_COMMUNICATION_TYPE] == COMMUNICATION_TYPE_RS485

    async def test_no_serial_ports_available(self, hass: HomeAssistant, mock_tis_protocol):
        """Test abort when no serial ports available."""
        with patch(
            'custom_components.tis_home_automation.config_flow.get_available_serial_ports',
            return_value=[]
        ):
            # Start flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"setup_name": "Test TIS Serial"}
            )
            
            # Try to select RS485 - should show only UDP option
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNICATION_TYPE: COMMUNICATION_TYPE_UDP}
            )
            
            # Should proceed to UDP config since RS485 wasn't available
            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["step_id"] == "udp_config"

class TestTISOptionsFlow:
    """Test TIS options flow."""

    async def test_options_form(self, hass: HomeAssistant, mock_config_entry, mock_tis_protocol):
        """Test options form."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "init"

    async def test_options_update_udp(self, hass: HomeAssistant, mock_config_entry, mock_tis_protocol):
        """Test updating UDP options."""
        # Add config entry to hass
        mock_config_entry.add_to_hass(hass)
        
        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_LOCAL_IP: "192.168.1.101",
                CONF_PORT: 6001,
                CONF_DISCOVERY_TIMEOUT: 45.0
            }
        )
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"][CONF_LOCAL_IP] == "192.168.1.101"
        assert result["data"][CONF_PORT] == 6001
        assert result["data"][CONF_DISCOVERY_TIMEOUT] == 45.0

    async def test_options_update_serial(self, hass: HomeAssistant, mock_serial_config_entry, mock_tis_protocol):
        """Test updating serial options."""
        with patch(
            'custom_components.tis_home_automation.config_flow.get_available_serial_ports',
            return_value=["/dev/ttyUSB0", "/dev/ttyUSB1"]
        ):
            # Add config entry to hass
            mock_serial_config_entry.add_to_hass(hass)
            
            result = await hass.config_entries.options.async_init(mock_serial_config_entry.entry_id)
            
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_SERIAL_PORT: "/dev/ttyUSB1",
                    CONF_BAUDRATE: 19200,
                    CONF_DISCOVERY_TIMEOUT: 60.0
                }
            )
            
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["data"][CONF_SERIAL_PORT] == "/dev/ttyUSB1"
            assert result["data"][CONF_BAUDRATE] == 19200
            assert result["data"][CONF_DISCOVERY_TIMEOUT] == 60.0