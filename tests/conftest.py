"""Pytest configuration and shared fixtures for SIT tests."""

import pytest
import os
import time
from datetime import datetime, timedelta
from zabbix_mcp.client import ZabbixClient
from zabbix_mcp.config import load_config


@pytest.fixture(scope="session")
def zabbix_client():
    """Create persistent Zabbix client for test session."""
    config = load_config()
    client = ZabbixClient(
        base_url=os.getenv("ZABBIX_URL", config.base_url),
        username=os.getenv("ZABBIX_USERNAME", config.username),
        password=os.getenv("ZABBIX_PASSWORD", config.password),
    )
    
    # Try token first, fall back to username/password
    token = os.getenv("ZABBIX_API_TOKEN")
    if token:
        client.token = token
    else:
        client.authenticate()
    
    # Verify connection
    try:
        hosts = client.call("host.get", {"limit": 1})
        assert hosts is not None
    except Exception as e:
        pytest.skip(f"Cannot connect to Zabbix: {e}")
    
    return client


@pytest.fixture(scope="session")
def test_environment(zabbix_client):
    """Create test environment (hosts, items, templates).
    
    Creates once per session and cleans up at end.
    """
    test_id = datetime.now().strftime("%s")
    
    # Create test host group
    try:
        group = zabbix_client.call("hostgroup.create", {
            "name": f"SIT_Test_Group_{test_id}"
        })
        group_id = group[0] if isinstance(group, list) else group.get("groupids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test group: {e}")
    
    # Create test host
    try:
        host = zabbix_client.call("host.create", {
            "host": f"sit-test-host-{test_id}",
            "name": "SIT Test Host",
            "groups": [{"groupid": group_id}],
        })
        host_id = host[0] if isinstance(host, list) else host.get("hostids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test host: {e}")
    
    # Create test template
    try:
        template = zabbix_client.call("template.create", {
            "host": f"sit-test-template-{test_id}",
            "name": "SIT Test Template",
            "groups": [{"groupid": "1"}],  # Templates group
        })
        template_id = template[0] if isinstance(template, list) else template.get("templateids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test template: {e}")
    
    yield {
        "test_id": test_id,
        "group_id": group_id,
        "host_id": host_id,
        "template_id": template_id,
    }
    
    # Cleanup
    try:
        zabbix_client.call("host.delete", [host_id])
        zabbix_client.call("template.delete", [template_id])
        zabbix_client.call("hostgroup.delete", [group_id])
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def test_host(test_environment, zabbix_client):
    """Create a test host for each test."""
    test_id = str(int(time.time() * 1000))  # Millisecond precision
    
    try:
        host = zabbix_client.call("host.create", {
            "host": f"sit-test-{test_id}",
            "name": f"Test Host {test_id}",
            "groups": [{"groupid": test_environment["group_id"]}],
        })
        host_id = host[0] if isinstance(host, list) else host.get("hostids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test host: {e}")
    
    yield {"id": host_id}
    
    # Cleanup
    try:
        zabbix_client.call("host.delete", [host_id])
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def test_item(test_host, zabbix_client):
    """Create a test item for each test."""
    test_id = str(int(time.time() * 1000))
    
    try:
        item = zabbix_client.call("item.create", {
            "hostid": test_host["id"],
            "name": f"Test Item {test_id}",
            "key_": f"test.item.{test_id}",
            "type": 0,  # Agent
            "value_type": 0,  # Float
            "delay": 60,
        })
        item_id = item[0] if isinstance(item, list) else item.get("itemids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test item: {e}")
    
    yield {"id": item_id}
    
    # Cleanup
    try:
        zabbix_client.call("item.delete", [item_id])
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def test_role(zabbix_client):
    """Create a test role for each test."""
    test_id = str(int(time.time() * 1000))
    
    try:
        role = zabbix_client.call("role.create", {
            "name": f"SIT_Test_Role_{test_id}",
            "type": 1,  # User role
        })
        role_id = role[0] if isinstance(role, list) else role.get("roleids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test role: {e}")
    
    yield {"id": role_id}
    
    # Cleanup
    try:
        zabbix_client.call("role.delete", [role_id])
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def test_user(test_role, zabbix_client):
    """Create a test user for each test."""
    test_id = str(int(time.time() * 1000))
    
    try:
        user = zabbix_client.call("user.create", {
            "username": f"sit_test_{test_id}",
            "passwd": f"Test#Pass123_{test_id}",
            "roleid": test_role["id"],
        })
        user_id = user[0] if isinstance(user, list) else user.get("userids", [None])[0]
    except Exception as e:
        pytest.skip(f"Cannot create test user: {e}")
    
    yield {"id": user_id}
    
    # Cleanup
    try:
        zabbix_client.call("user.delete", [user_id])
    except Exception:
        pass  # Best effort cleanup


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "smoke: quick smoke tests (5 min)"
    )
    config.addinivalue_line(
        "markers", "full: full SIT tests (30 min)"
    )
    config.addinivalue_line(
        "markers", "security: security validation tests"
    )
    config.addinivalue_line(
        "markers", "slow: slow tests (performance, load)"
    )
