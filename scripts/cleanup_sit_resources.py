#!/usr/bin/env python3
"""Clean up SIT test resources from Zabbix."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.zabbix_mcp.client import ZabbixClient

def cleanup_test_hosts():
    """Delete all sit-test-* hosts from Zabbix."""
    
    client = ZabbixClient(
        os.getenv("ZABBIX_URL", "http://192.168.1.101"),
        os.getenv("ZABBIX_USERNAME", "Admin"),
        os.getenv("ZABBIX_PASSWORD", "zabbix"),
    )
    
    token = os.getenv("ZABBIX_API_TOKEN")
    if token:
        client.token = token
    else:
        client.authenticate()
    
    # Get all hosts
    all_hosts = client.call("host.get", {
        "output": ["hostid", "host", "name"],
        "limit": 500,
    })
    
    print(f"Total hosts in Zabbix: {len(all_hosts)}")
    
    # Find test hosts (sit-test-* or sit-*-* patterns)
    test_hosts = [h for h in all_hosts if 'sit-' in h['host'].lower() or 'sit-' in h['name'].lower()]
    
    print(f"\nFound {len(test_hosts)} test hosts to clean up:")
    for h in test_hosts:
        print(f"  - {h['name']} ({h['host']}) - ID: {h['hostid']}")
    
    if not test_hosts:
        print("\nNo test hosts found to clean up.")
        return 0
    
    # Confirm before deleting
    response = input(f"\nDelete {len(test_hosts)} test hosts? (yes/no): ")
    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        return 0
    
    # Delete hosts
    host_ids = [h['hostid'] for h in test_hosts]
    try:
        result = client.call("host.delete", host_ids)
        deleted = result.get('hostids', []) if isinstance(result, dict) else result
        print(f"\n✅ Deleted {len(deleted)} test hosts")
        return 0
    except Exception as e:
        print(f"\n❌ Error deleting hosts: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(cleanup_test_hosts())
