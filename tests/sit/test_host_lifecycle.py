"""System Integration Tests for Host Lifecycle Operations (Phase 1A)."""

import pytest
from zabbix_mcp.tools import (
    handle_create_host,
    handle_update_host,
    handle_enable_host,
    handle_disable_host,
    handle_delete_host,
    handle_add_host_interface,
    handle_update_host_interface,
    handle_delete_host_interface,
)


class TestHostLifecycle:
    """Test host creation, modification, and deletion."""

    @pytest.mark.smoke
    @pytest.mark.full
    def test_create_host_success(self, zabbix_client, test_environment):
        """Test creating a new host with valid parameters."""
        result = handle_create_host(zabbix_client, {
            "hostname": f"sit-create-host-{id(self)}",
            "display_name": "SIT Test Create Host",
            "ip_address": "192.168.1.99",
            "port": "10050",
            "group_id": test_environment["group_id"],
        })

        assert "✅" in result, f"Expected success, got: {result}"
        assert "Host ID:" in result
        assert "Host Created!" in result

    @pytest.mark.smoke
    def test_create_host_minimal(self, zabbix_client, test_environment):
        """Test creating host with minimal parameters."""
        result = handle_create_host(zabbix_client, {
            "hostname": f"sit-minimal-{id(self)}",
            "display_name": "Minimal Host",
            "ip_address": "192.168.1.100",
            "group_id": test_environment["group_id"],
        })

        assert "✅" in result

    @pytest.mark.full
    def test_create_host_invalid_ip(self, zabbix_client, test_environment):
        """Test host creation with invalid IP address."""
        result = handle_create_host(zabbix_client, {
            "hostname": f"sit-invalid-{id(self)}",
            "display_name": "Invalid Host",
            "ip_address": "999.999.999.999",  # Invalid
            "group_id": test_environment["group_id"],
        })

        # Should either succeed (Zabbix accepts it) or fail gracefully
        # We're mainly checking it doesn't crash
        assert isinstance(result, str)

    @pytest.mark.full
    def test_update_host_name(self, zabbix_client, test_host):
        """Test updating host display name."""
        result = handle_update_host(zabbix_client, {
            "hostid": test_host["id"],
            "name": "Updated Host Name",
        })

        assert "✅" in result
        assert "name →" in result
        assert "Updated" in result

    @pytest.mark.full
    def test_update_host_description(self, zabbix_client, test_host):
        """Test updating host description."""
        result = handle_update_host(zabbix_client, {
            "hostid": test_host["id"],
            "description": "This is a test host for SIT testing",
        })

        assert "✅" in result
        assert "description" in result.lower()

    @pytest.mark.full
    def test_update_host_multiple_properties(self, zabbix_client, test_host):
        """Test updating multiple host properties at once."""
        result = handle_update_host(zabbix_client, {
            "hostid": test_host["id"],
            "name": "Multi-Update Host",
            "description": "Updated multiple properties",
        })

        assert "✅" in result
        assert "name →" in result
        assert "description" in result.lower()

    @pytest.mark.smoke
    @pytest.mark.full
    def test_disable_host(self, zabbix_client, test_host):
        """Test disabling host monitoring."""
        result = handle_disable_host(zabbix_client, {
            "hostid": test_host["id"],
        })

        assert "✅" in result
        assert "paused" in result.lower() or "disabled" in result.lower()

    @pytest.mark.smoke
    @pytest.mark.full
    def test_enable_host(self, zabbix_client, test_host):
        """Test enabling host monitoring."""
        # First disable to ensure state is known
        handle_disable_host(zabbix_client, {"hostid": test_host["id"]})

        # Then enable
        result = handle_enable_host(zabbix_client, {
            "hostid": test_host["id"],
        })

        assert "✅" in result
        assert "active" in result.lower()

    @pytest.mark.full
    def test_enable_disable_cycle(self, zabbix_client, test_host):
        """Test enable/disable cycle."""
        # Disable
        disable_result = handle_disable_host(zabbix_client, {
            "hostid": test_host["id"],
        })
        assert "✅" in disable_result

        # Enable
        enable_result = handle_enable_host(zabbix_client, {
            "hostid": test_host["id"],
        })
        assert "✅" in enable_result

        # Disable again
        disable_result2 = handle_disable_host(zabbix_client, {
            "hostid": test_host["id"],
        })
        assert "✅" in disable_result2

    @pytest.mark.full
    def test_delete_host(self, zabbix_client, test_environment):
        """Test deleting a host."""
        # Create a host to delete
        create_result = handle_create_host(zabbix_client, {
            "hostname": f"sit-delete-test-{id(self)}",
            "display_name": "Host to Delete",
            "ip_address": "192.168.1.101",
            "group_id": test_environment["group_id"],
        })

        assert "✅" in create_result
        hostid = extract_hostid_from_result(create_result)

        # Delete it
        delete_result = handle_delete_host(zabbix_client, {
            "hostid": hostid,
        })

        assert "✅" in delete_result
        assert "Deleted" in delete_result or "Removed" in delete_result


class TestHostInterfaces:
    """Test host interface operations."""

    @pytest.mark.full
    def test_add_host_interface(self, zabbix_client, test_host):
        """Test adding interface to host."""
        result = handle_add_host_interface(zabbix_client, {
            "hostid": test_host["id"],
            "ip_address": "192.168.1.100",
            "port": "10050",
        })

        assert "✅" in result
        assert "Interface ID:" in result

    @pytest.mark.full
    def test_add_multiple_interfaces(self, zabbix_client, test_host):
        """Test adding multiple interfaces to same host."""
        # Add first interface
        result1 = handle_add_host_interface(zabbix_client, {
            "hostid": test_host["id"],
            "ip_address": "192.168.1.100",
        })
        assert "✅" in result1

        # Add second interface
        result2 = handle_add_host_interface(zabbix_client, {
            "hostid": test_host["id"],
            "ip_address": "192.168.1.101",
        })
        assert "✅" in result2

    @pytest.mark.full
    def test_update_interface_ip(self, zabbix_client, test_host):
        """Test updating interface IP address."""
        # Add interface first
        add_result = handle_add_host_interface(zabbix_client, {
            "hostid": test_host["id"],
            "ip_address": "192.168.1.100",
        })
        assert "✅" in add_result

        interfaceid = extract_interfaceid_from_result(add_result)

        # Update IP
        update_result = handle_update_host_interface(zabbix_client, {
            "interfaceid": interfaceid,
            "ip_address": "192.168.1.102",
        })

        assert "✅" in update_result
        assert "IP →" in update_result or "ip" in update_result.lower()

    @pytest.mark.full
    def test_update_interface_port(self, zabbix_client, test_host):
        """Test updating interface port."""
        # Add interface
        add_result = handle_add_host_interface(zabbix_client, {
            "hostid": test_host["id"],
            "ip_address": "192.168.1.100",
            "port": "10050",
        })
        interfaceid = extract_interfaceid_from_result(add_result)

        # Update port
        update_result = handle_update_host_interface(zabbix_client, {
            "interfaceid": interfaceid,
            "port": "10051",
        })

        assert "✅" in update_result

    @pytest.mark.full
    def test_delete_interface(self, zabbix_client, test_host):
        """Test deleting host interface."""
        # Add interface
        add_result = handle_add_host_interface(zabbix_client, {
            "hostid": test_host["id"],
            "ip_address": "192.168.1.100",
        })
        interfaceid = extract_interfaceid_from_result(add_result)

        # Delete interface
        delete_result = handle_delete_host_interface(zabbix_client, {
            "interfaceid": interfaceid,
        })

        assert "✅" in delete_result
        assert "Deleted" in delete_result or "Removed" in delete_result


class TestHostInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.security
    def test_create_host_missing_hostname(self, zabbix_client, test_environment):
        """Test creating host without hostname."""
        result = handle_create_host(zabbix_client, {
            "display_name": "No Hostname Host",
            "ip_address": "192.168.1.100",
            "group_id": test_environment["group_id"],
        })

        # Should fail gracefully
        assert "Error" in result or "❌" in result

    @pytest.mark.security
    def test_update_host_invalid_hostid(self, zabbix_client):
        """Test updating with invalid host ID."""
        result = handle_update_host(zabbix_client, {
            "hostid": "999999999",  # Non-existent
            "name": "Updated Name",
        })

        # Should fail gracefully
        assert "Error" in result or "Failed" in result or "❌" in result

    @pytest.mark.security
    def test_disable_invalid_hostid(self, zabbix_client):
        """Test disabling with invalid host ID."""
        result = handle_disable_host(zabbix_client, {
            "hostid": "999999999",
        })

        # Should handle gracefully
        assert isinstance(result, str)


# Helper functions
def extract_hostid_from_result(result: str) -> str:
    """Extract host ID from handler result string."""
    lines = result.split('\n')
    for line in lines:
        if "Host ID:" in line:
            return line.split("Host ID:")[-1].strip()
    raise ValueError("Could not extract host ID from result")


def extract_interfaceid_from_result(result: str) -> str:
    """Extract interface ID from handler result string."""
    lines = result.split('\n')
    for line in lines:
        if "Interface ID:" in line:
            return line.split("Interface ID:")[-1].strip()
    raise ValueError("Could not extract interface ID from result")
