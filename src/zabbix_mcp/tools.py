"""MCP Tool definitions and handlers."""

import json
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

from mcp.types import Tool

from .client import ZabbixClient

# Tool definitions
TOOLS: List[Tool] = [
    Tool(
        name="get_hosts",
        description="List all monitored hosts in Zabbix",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_problems",
        description="Get active problems/alerts",
        inputSchema={"type": "object", "properties": {"limit": {"type": "integer"}}},
    ),
    Tool(
        name="get_triggers",
        description="List triggers with their current status",
        inputSchema={"type": "object", "properties": {"limit": {"type": "integer"}}},
    ),
    Tool(
        name="get_events",
        description="Get recent events from Zabbix",
        inputSchema={"type": "object", "properties": {"limit": {"type": "integer"}}},
    ),
    Tool(
        name="get_host_details",
        description="Get detailed information about a specific host",
        inputSchema={
            "type": "object",
            "properties": {"hostname": {"type": "string"}},
            "required": ["hostname"],
        },
    ),
    Tool(
        name="get_items",
        description="Get monitored items (metrics)",
        inputSchema={"type": "object", "properties": {"hostname": {"type": "string"}}},
    ),
    Tool(
        name="get_host_groups",
        description="List all host groups",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_system_status",
        description="Get overall system status and statistics",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_templates",
        description="List all available templates",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="link_template",
        description="Link a template to a host by names (hostname and template name)",
        inputSchema={
            "type": "object",
            "properties": {
                "hostname": {"type": "string", "description": "Host name"},
                "template_name": {"type": "string", "description": "Template name"},
            },
            "required": ["hostname", "template_name"],
        },
    ),
    Tool(
        name="create_user",
        description="Create a new Zabbix user with specified role",
        inputSchema={
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Unique username"},
                "password": {"type": "string", "description": "User password"},
                "role": {"type": "string", "description": "Role name (default: Super admin role)"},
                "email": {"type": "string", "description": "Optional email address"},
                "name": {"type": "string", "description": "Optional first name"},
                "surname": {"type": "string", "description": "Optional last name"},
            },
            "required": ["username", "password"],
        },
    ),
    Tool(
        name="update_user",
        description="Update user properties (password, role, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "userid": {"type": "string", "description": "User ID"},
                "password": {"type": "string", "description": "New password"},
                "current_password": {"type": "string", "description": "Current password (required if changing password)"},
                "roleid": {"type": "string", "description": "New role ID"},
            },
            "required": ["userid"],
        },
    ),
    Tool(
        name="get_roles",
        description="List all available Zabbix roles",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="check_host_interface_availability",
        description="Check if host interface (agent) is available",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID"},
            },
            "required": ["hostid"],
        },
    ),
    Tool(
        name="create_host",
        description="Create a new Zabbix host (monitor). Use this to add new containers/servers to monitoring.",
        inputSchema={
            "type": "object",
            "properties": {
                "hostname": {"type": "string", "description": "Internal hostname identifier (e.g., 'my-server')"},
                "display_name": {"type": "string", "description": "Display name shown in Zabbix frontend"},
                "ip_address": {"type": "string", "description": "IP address for agent polling (e.g., 10.0.0.5)"},
                "port": {"type": "string", "description": "Agent port (default: 10050)"},
                "group_id": {"type": "string", "description": "Host group ID (default: 2 for 'Linux servers')"},
                "template_id": {"type": "string", "description": "Template ID to auto-link items (default: 10001 for 'Linux by Zabbix agent')"},
            },
            "required": ["hostname", "display_name", "ip_address"],
        },
    ),
    Tool(
        name="add_host_interface",
        description="Add a network interface to an existing host for polling by Zabbix server",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID"},
                "ip_address": {"type": "string", "description": "IP address for polling"},
                "port": {"type": "string", "description": "Agent port (default: 10050)"},
                "interface_type": {"type": "string", "description": "Interface type: 1=Agent (default), 2=SNMP, 3=IPMI, 4=JMX"},
            },
            "required": ["hostid", "ip_address"],
        },
    ),
    Tool(
        name="sync_zabbix_sequences",
        description="Fix sequence table desynchronization (call this once after manual DB operations)",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="create_maintenance_window",
        description="Create a maintenance window for hosts to pause data collection and suppress alerts",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Maintenance window name (e.g., 'Nightly Maintenance')"},
                "description": {"type": "string", "description": "Optional description"},
                "hostids": {"type": "array", "items": {"type": "string"}, "description": "List of host IDs (e.g., ['10699', '10700'])"},
                "start_time": {"type": "integer", "description": "Start time in seconds since midnight (e.g., 79200 for 22:00)"},
                "duration_seconds": {"type": "integer", "description": "Duration in seconds (e.g., 28800 for 8 hours)"},
                "recurring_daily": {"type": "boolean", "description": "If true, repeat daily. If false, one-time (default: true)"},
            },
            "required": ["name", "hostids", "start_time", "duration_seconds"],
        },
    ),
    # Phase 1A: Host Lifecycle Management
    Tool(
        name="update_host",
        description="Update host properties (name, status, groups, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID"},
                "name": {"type": "string", "description": "New display name (optional)"},
                "status": {"type": "string", "description": "Status: 0=enabled (monitored), 1=disabled (not monitored)"},
                "group_ids": {"type": "array", "items": {"type": "string"}, "description": "List of host group IDs (optional)"},
                "description": {"type": "string", "description": "Host description (optional)"},
            },
            "required": ["hostid"],
        },
    ),
    Tool(
        name="enable_host",
        description="Enable monitoring for a host (set status=0)",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID to enable"},
            },
            "required": ["hostid"],
        },
    ),
    Tool(
        name="disable_host",
        description="Disable monitoring for a host (set status=1). Host will stop collecting data.",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID to disable"},
            },
            "required": ["hostid"],
        },
    ),
    Tool(
        name="delete_host",
        description="Delete a host from Zabbix monitoring. Removes all associated items, triggers, and history.",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID to delete"},
                "cascade": {"type": "boolean", "description": "Cascade delete (removes all related data). Default: true"},
            },
            "required": ["hostid"],
        },
    ),
    Tool(
        name="update_host_interface",
        description="Update a host interface (IP address, port, authentication, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "interfaceid": {"type": "string", "description": "Interface ID"},
                "ip_address": {"type": "string", "description": "New IP address (optional)"},
                "port": {"type": "string", "description": "New port (optional)"},
                "useip": {"type": "string", "description": "Use IP (0=DNS, 1=IP). Default: 1"},
                "dns": {"type": "string", "description": "DNS name (if useip=0)"},
                "bulk": {"type": "string", "description": "Bulk value (0=not bulk, 1=bulk). Default: 0"},
            },
            "required": ["interfaceid"],
        },
    ),
    Tool(
        name="delete_host_interface",
        description="Delete a host interface. Host must have at least one interface remaining.",
        inputSchema={
            "type": "object",
            "properties": {
                "interfaceid": {"type": "string", "description": "Interface ID to delete"},
            },
            "required": ["interfaceid"],
        },
    ),
    # Phase 1B: Problem & Trigger Management
    Tool(
        name="acknowledge_problem",
        description="Acknowledge a problem alert. Mark as reviewed by operator.",
        inputSchema={
            "type": "object",
            "properties": {
                "problemid": {"type": "string", "description": "Problem ID"},
                "message": {"type": "string", "description": "Optional acknowledgement message/note"},
            },
            "required": ["problemid"],
        },
    ),
    Tool(
        name="update_problem_status",
        description="Update problem state (mark as resolved or re-open)",
        inputSchema={
            "type": "object",
            "properties": {
                "problemid": {"type": "string", "description": "Problem ID"},
                "status": {"type": "string", "description": "Status: 0=problem (open), 1=resolved (closed)"},
            },
            "required": ["problemid", "status"],
        },
    ),
    Tool(
        name="update_trigger",
        description="Update trigger configuration (expression, description, enabled status, etc.)",
        inputSchema={
            "type": "object",
            "properties": {
                "triggerid": {"type": "string", "description": "Trigger ID"},
                "expression": {"type": "string", "description": "Trigger expression (e.g., 'last(/host/key)>100')"},
                "description": {"type": "string", "description": "Trigger description/title"},
                "enabled": {"type": "string", "description": "Enable: 0=disabled, 1=enabled"},
                "priority": {"type": "string", "description": "Severity: 0=Not classified, 1=Info, 2=Warning, 3=Average, 4=High, 5=Disaster"},
                "manual_close": {"type": "string", "description": "Allow manual close: 0=no, 1=yes"},
            },
            "required": ["triggerid"],
        },
    ),
    Tool(
        name="enable_trigger",
        description="Enable a trigger (start evaluating conditions and generating problems)",
        inputSchema={
            "type": "object",
            "properties": {
                "triggerid": {"type": "string", "description": "Trigger ID"},
            },
            "required": ["triggerid"],
        },
    ),
    Tool(
        name="disable_trigger",
        description="Disable a trigger (stop evaluating conditions, no new problems)",
        inputSchema={
            "type": "object",
            "properties": {
                "triggerid": {"type": "string", "description": "Trigger ID"},
            },
            "required": ["triggerid"],
        },
    ),
    Tool(
        name="delete_trigger",
        description="Delete a trigger. Removes associated problems and history.",
        inputSchema={
            "type": "object",
            "properties": {
                "triggerid": {"type": "string", "description": "Trigger ID"},
            },
            "required": ["triggerid"],
        },
    ),
    Tool(
        name="acknowledge_event",
        description="Acknowledge an event. Mark as seen/reviewed by operator.",
        inputSchema={
            "type": "object",
            "properties": {
                "eventid": {"type": "string", "description": "Event ID"},
                "message": {"type": "string", "description": "Optional acknowledgement message"},
                "acknowledge": {"type": "string", "description": "Action: 0=unacknowledge, 1=acknowledge (default: 1)"},
            },
            "required": ["eventid"],
        },
    ),
    # Phase 2A: Item & Metric Management
    Tool(
        name="create_item",
        description="Create a new monitored item (metric) on a host",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID"},
                "name": {"type": "string", "description": "Item display name (e.g., 'CPU Load')"},
                "key_": {"type": "string", "description": "Item key (e.g., 'system.cpu.load')"},
                "type": {"type": "string", "description": "Item type: 0=Zabbix agent, 2=SNMP, 3=IPMI, 7=SSH, 10=External, 11=Database, 12=JMX, 13=SNMP trap, 15=Dependent"},
                "value_type": {"type": "string", "description": "Data type: 0=float, 1=string, 2=log, 3=unsigned int, 4=text"},
                "interval": {"type": "string", "description": "Polling interval (e.g., '1m', '5m', '1h')"},
                "units": {"type": "string", "description": "Units (e.g., 'Bps', 'B', '%')"},
                "description": {"type": "string", "description": "Item description"},
            },
            "required": ["hostid", "name", "key_", "type", "value_type"],
        },
    ),
    Tool(
        name="update_item",
        description="Update an existing monitored item configuration",
        inputSchema={
            "type": "object",
            "properties": {
                "itemid": {"type": "string", "description": "Item ID"},
                "name": {"type": "string", "description": "New display name (optional)"},
                "key_": {"type": "string", "description": "New item key (optional)"},
                "type": {"type": "string", "description": "New item type (optional)"},
                "value_type": {"type": "string", "description": "New data type (optional)"},
                "interval": {"type": "string", "description": "New polling interval (optional)"},
                "units": {"type": "string", "description": "New units (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
                "enabled": {"type": "string", "description": "Enable (0=disabled, 1=enabled)"},
            },
            "required": ["itemid"],
        },
    ),
    Tool(
        name="delete_item",
        description="Delete a monitored item and its history",
        inputSchema={
            "type": "object",
            "properties": {
                "itemid": {"type": "string", "description": "Item ID to delete"},
            },
            "required": ["itemid"],
        },
    ),
    # Phase 2B: Template Management
    Tool(
        name="create_template",
        description="Create a new reusable monitoring template",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Template name (e.g., 'Linux Nginx Monitoring')"},
                "description": {"type": "string", "description": "Template description"},
                "group_ids": {"type": "array", "items": {"type": "string"}, "description": "Template group IDs (e.g., ['1'])"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="update_template",
        description="Update template properties (name, description, groups)",
        inputSchema={
            "type": "object",
            "properties": {
                "templateid": {"type": "string", "description": "Template ID"},
                "name": {"type": "string", "description": "New name (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
                "group_ids": {"type": "array", "items": {"type": "string"}, "description": "New group IDs (optional)"},
            },
            "required": ["templateid"],
        },
    ),
    Tool(
        name="delete_template",
        description="Delete a template. Unlinks from all hosts first.",
        inputSchema={
            "type": "object",
            "properties": {
                "templateid": {"type": "string", "description": "Template ID to delete"},
            },
            "required": ["templateid"],
        },
    ),
    # Phase 2C: Template Link Management
    Tool(
        name="unlink_template",
        description="Remove a template from a host",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID"},
                "templateid": {"type": "string", "description": "Template ID"},
                "clean": {"type": "string", "description": "Clean up items: 0=no, 1=yes (default: 0)"},
            },
            "required": ["hostid", "templateid"],
        },
    ),
    Tool(
        name="link_multiple_templates",
        description="Attach multiple templates to a host in one operation",
        inputSchema={
            "type": "object",
            "properties": {
                "hostid": {"type": "string", "description": "Host ID"},
                "template_ids": {"type": "array", "items": {"type": "string"}, "description": "List of template IDs to link"},
            },
            "required": ["hostid", "template_ids"],
        },
    ),
    # Phase 2D: Host Group Management
    Tool(
        name="create_host_group",
        description="Create a new host group for organizing hosts",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Group name (e.g., 'Production Servers')"},
                "description": {"type": "string", "description": "Optional group description"},
            },
            "required": ["name"],
        },
    ),
    # Phase 3A: Role Management
    Tool(
        name="create_role",
        description="Create a new Zabbix role with specific permissions",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Role name (e.g., 'Monitoring Read-Only')"},
                "type": {"type": "string", "description": "Role type: 1=User role, 2=Admin role, 3=Super admin role"},
                "description": {"type": "string", "description": "Role description"},
            },
            "required": ["name", "type"],
        },
    ),
    Tool(
        name="update_role",
        description="Update role properties (name, description, permissions)",
        inputSchema={
            "type": "object",
            "properties": {
                "roleid": {"type": "string", "description": "Role ID"},
                "name": {"type": "string", "description": "New role name (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
            },
            "required": ["roleid"],
        },
    ),
    Tool(
        name="delete_role",
        description="Delete a custom role. Cannot delete built-in roles.",
        inputSchema={
            "type": "object",
            "properties": {
                "roleid": {"type": "string", "description": "Role ID to delete"},
            },
            "required": ["roleid"],
        },
    ),
    # Phase 3B: User Management
    Tool(
        name="delete_user",
        description="Delete a Zabbix user account",
        inputSchema={
            "type": "object",
            "properties": {
                "userid": {"type": "string", "description": "User ID to delete"},
            },
            "required": ["userid"],
        },
    ),
    # Phase 3C: Host Group Management
    Tool(
        name="update_host_group",
        description="Update host group properties (name, description)",
        inputSchema={
            "type": "object",
            "properties": {
                "groupid": {"type": "string", "description": "Host group ID"},
                "name": {"type": "string", "description": "New group name (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
            },
            "required": ["groupid"],
        },
    ),
    Tool(
        name="delete_host_group",
        description="Delete a host group. Cannot delete if hosts assigned.",
        inputSchema={
            "type": "object",
            "properties": {
                "groupid": {"type": "string", "description": "Host group ID to delete"},
            },
            "required": ["groupid"],
        },
    ),
    # Phase 3D: Maintenance Window Management
    Tool(
        name="get_maintenance_windows",
        description="List all maintenance windows with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default: 50)"},
            },
        },
    ),
    Tool(
        name="update_maintenance_window",
        description="Update maintenance window schedule or hosts",
        inputSchema={
            "type": "object",
            "properties": {
                "maintenanceid": {"type": "string", "description": "Maintenance window ID"},
                "name": {"type": "string", "description": "New name (optional)"},
                "description": {"type": "string", "description": "New description (optional)"},
                "active_since": {"type": "string", "description": "New start timestamp (optional)"},
                "active_till": {"type": "string", "description": "New end timestamp (optional)"},
            },
            "required": ["maintenanceid"],
        },
    ),
    Tool(
        name="delete_maintenance_window",
        description="Delete a maintenance window",
        inputSchema={
            "type": "object",
            "properties": {
                "maintenanceid": {"type": "string", "description": "Maintenance window ID to delete"},
            },
            "required": ["maintenanceid"],
        },
    ),
]


def handle_get_hosts(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_hosts tool."""
    try:
        hosts = client.get_hosts()
        if not hosts:
            return "No hosts found"
        
        result = f"📋 Found {len(hosts)} hosts:\n\n"
        for host in hosts[:20]:
            result += f"🖥️ {host.get('name', 'Unknown')} ({host.get('host', 'N/A')})\n"
            result += f"   Status: {'Enabled' if host.get('status') == '0' else 'Disabled'}\n"
        
        if len(hosts) > 20:
            result += f"\n... and {len(hosts) - 20} more hosts"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_problems(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_problems tool."""
    try:
        limit = args.get("limit", 50)
        problems = client.get_problems(limit=limit)
        
        if not problems:
            return "✅ No active problems"
        
        result = f"⚠️ Active Problems: {len(problems)}\n\n"
        for problem in problems[:10]:
            hosts = problem.get("hosts", [])
            host_names = ", ".join([h.get("name", "Unknown") for h in hosts])
            result += f"• {problem.get('name', 'Unknown')} - {host_names}\n"
        
        if len(problems) > 10:
            result += f"\n... and {len(problems) - 10} more"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_triggers(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_triggers tool."""
    try:
        limit = args.get("limit", 50)
        triggers = client.get_triggers(limit=limit)
        
        if not triggers:
            return "No triggers found"
        
        result = f"🔔 Found {len(triggers)} triggers:\n\n"
        for trigger in triggers[:10]:
            status = "🔴 PROBLEM" if trigger.get("value") == "1" else "🟢 OK"
            result += f"{status} - {trigger.get('description', 'Unknown')}\n"
        
        if len(triggers) > 10:
            result += f"... and {len(triggers) - 10} more"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_events(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_events tool."""
    try:
        limit = args.get("limit", 20)
        events = client.get_events(limit=limit)
        
        if not events:
            return "No events found"
        
        result = f"📅 Recent Events ({len(events)}):\n\n"
        for event in events[:10]:
            timestamp = datetime.fromtimestamp(int(event.get("clock", 0))).strftime("%Y-%m-%d %H:%M:%S")
            hosts = event.get("hosts", [])
            host_names = ", ".join([h.get("name", "Unknown") for h in hosts])
            result += f"⏰ {timestamp} - {host_names}\n"
        
        if len(events) > 10:
            result += f"... and {len(events) - 10} more"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_host_details(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_host_details tool."""
    try:
        hostname = args.get("hostname")
        if not hostname:
            return "Error: hostname required"
        
        host = client.get_host_by_name(hostname)
        if not host:
            return f"Host '{hostname}' not found"
        
        result = f"🖥️ Host Details: {host.get('name')}\n\n"
        result += f"Host ID: {host.get('hostid')}\n"
        result += f"Status: {'Enabled' if host.get('status') == '0' else 'Disabled'}\n"
        
        interfaces = host.get("interfaces", [])
        if interfaces:
            result += f"\nInterfaces ({len(interfaces)}):\n"
            for iface in interfaces:
                result += f"  - {iface.get('ip', 'N/A')} ({iface.get('type', 'Unknown')})\n"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_items(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_items tool."""
    try:
        hostname = args.get("hostname")
        hostid = None
        
        if hostname:
            host = client.get_host_by_name(hostname)
            if not host:
                return f"Host '{hostname}' not found"
            hostid = host.get("hostid")
        
        items = client.get_items(hostid=hostid) if hostid else client.get_items()
        
        if not items:
            return "No items found"
        
        result = f"📊 Monitored Items: {len(items)}\n\n"
        for item in items[:15]:
            result += f"• {item.get('name', 'Unknown')} ({item.get('key_', 'N/A')})\n"
        
        if len(items) > 15:
            result += f"... and {len(items) - 15} more"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_host_groups(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_host_groups tool."""
    try:
        groups = client.get_groups()
        
        if not groups:
            return "No host groups found"
        
        result = f"👥 Host Groups: {len(groups)}\n\n"
        for group in groups:
            result += f"• {group.get('name')} (ID: {group.get('groupid')})\n"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_system_status(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_system_status tool."""
    try:
        hosts = client.get_hosts()
        problems = client.get_problems()
        triggers = client.get_triggers()
        
        result = "📊 Zabbix System Status\n\n"
        result += f"Total Hosts: {len(hosts)}\n"
        result += f"Active Problems: {len(problems)}\n"
        result += f"Total Triggers: {len(triggers)}\n"
        
        problem_triggers = [t for t in triggers if t.get("value") == "1"]
        result += f"Problem Triggers: {len(problem_triggers)}\n"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_get_templates(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_templates tool."""
    try:
        templates = client.get_templates()
        
        if not templates:
            return "No templates found"
        
        result = f"📋 Available Templates: {len(templates)}\n\n"
        for template in templates[:20]:
            result += f"• {template.get('name')} ({template.get('host')})\n"
        
        if len(templates) > 20:
            result += f"\n... and {len(templates) - 20} more templates"
        
        return result
    except Exception as e:
        return f"Error: {e}"


def handle_link_template(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle link_template tool."""
    try:
        hostname = args.get("hostname")
        template_name = args.get("template_name")
        
        if not hostname or not template_name:
            return "Error: hostname and template_name are required"
        
        success = client.link_template_by_names(hostname, template_name)
        
        if success:
            return f"✅ Successfully linked template '{template_name}' to host '{hostname}'"
        else:
            return f"❌ Failed to link template '{template_name}' to host '{hostname}'"
    except Exception as e:
        return f"❌ Error: {e}"


def handle_create_user(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_user tool."""
    try:
        from .user_management import UserManagement
        
        um = UserManagement(client)
        result = um.create_user(
            username=args.get("username"),
            password=args.get("password"),
            role=args.get("role", "Super admin role"),
            email=args.get("email"),
            name=args.get("name"),
            surname=args.get("surname")
        )
        
        if result["success"]:
            return f"✅ User created successfully\nUser ID: {result['userid']}\nUsername: {args.get('username')}"
        else:
            errors = "\n".join(result.get("validation_errors", []))
            return f"❌ Failed to create user\n{result['message']}\n{errors}"
    except Exception as e:
        return f"Error: {e}"


def handle_update_user(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_user tool."""
    try:
        from .user_management import UserManagement
        
        um = UserManagement(client)
        result = um.update_user(
            userid=args.get("userid"),
            password=args.get("password"),
            roleid=args.get("roleid"),
            current_password=args.get("current_password"),
            email=args.get("email"),
            name=args.get("name"),
            surname=args.get("surname")
        )
        
        if result["success"]:
            changes = ", ".join(result.get("changes_made", []))
            return f"✅ User updated successfully\nChanges: {changes}"
        else:
            return f"❌ {result['message']}"
    except Exception as e:
        return f"Error: {e}"


def handle_get_roles(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_roles tool."""
    try:
        from .user_management import UserManagement
        
        um = UserManagement(client)
        result = um.get_roles()
        
        if result["roles"]:
            output = f"📋 Available Roles ({result['total']}):\n\n"
            for role in result["roles"]:
                role_type = role.get("type", "unknown")
                output += f"• {role['name']} (ID: {role['roleid']}) - Type: {role_type}\n"
            return output
        else:
            return "No roles found"
    except Exception as e:
        return f"Error: {e}"


def handle_check_host_interface_availability(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle check_host_interface_availability tool."""
    try:
        from .user_management import UserManagement
        
        um = UserManagement(client)
        result = um.check_host_interface_availability(args.get("hostid"))
        
        status_emoji = {
            "available": "✅",
            "checking": "🔄",
            "unavailable": "❌",
            "unknown": "❓"
        }
        
        emoji = status_emoji.get(result["status"], "❓")
        output = f"{emoji} Host Interface Status\n"
        output += f"Host: {result.get('host', 'Unknown')}\n"
        output += f"Status: {result['status'].upper()}\n"
        
        if result["interfaces"]:
            output += f"Interfaces:\n"
            for iface in result["interfaces"]:
                output += f"  • {iface.get('ip')}:{iface.get('port')}\n"
        
        if result.get("error"):
            output += f"Error: {result['error']}"
        
        return output
    except Exception as e:
        return f"Error: {e}"


def handle_create_host(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_host tool - Create new Zabbix host for monitoring."""
    try:
        hostname = args.get("hostname")
        display_name = args.get("display_name")
        ip_address = args.get("ip_address")
        port = args.get("port", "10050")
        group_id = args.get("group_id", "2")  # Default: Linux servers
        template_id = args.get("template_id", "10001")  # Default: Linux by Zabbix agent
        
        if not all([hostname, display_name, ip_address]):
            return "❌ Error: hostname, display_name, and ip_address are required"
        
        # Step 1: Create host
        host_params = {
            "host": hostname,
            "name": display_name,
            "groups": [{"groupid": group_id}],
        }
        
        host_result = client.call("host.create", host_params)
        if not host_result:
            return f"❌ Failed to create host '{hostname}'"
        
        hostid = host_result[0] if isinstance(host_result, list) else host_result.get("hostids", [None])[0]
        if not hostid:
            return f"❌ Failed to get hostid from creation response"
        
        # Step 2: Add interface
        interface_params = {
            "hostid": hostid,
            "type": 1,  # Agent type
            "main": 1,  # Primary interface
            "useip": 1,  # Use IP
            "ip": ip_address,
            "dns": "",
            "port": port,
        }
        
        interface_result = client.call("hostinterface.create", interface_params)
        if not interface_result:
            return f"⚠️ Host created (ID: {hostid}) but interface creation failed"
        
        interfaceid = interface_result[0] if isinstance(interface_result, list) else interface_result.get("interfaceids", [None])[0]
        
        # Step 3: Link template
        if template_id:
            update_params = {
                "hostid": hostid,
                "templates": [{"templateid": template_id}],
            }
            
            template_result = client.call("host.update", update_params)
            if not template_result:
                return f"⚠️ Host created (ID: {hostid}) but template linking failed"
        
        return f"""✅ Host Created Successfully!
        
🖥️ Hostname: {hostname}
📝 Display: {display_name}
🌐 IP: {ip_address}:{port}
🔗 Host ID: {hostid}
📋 Interface ID: {interfaceid}
📊 Template: {'Linked (10001)' if template_id == '10001' else f'Linked ({template_id})'}

Next: Wait 30-60 seconds for agent to start reporting metrics."""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_add_host_interface(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle add_host_interface tool - Add interface to existing host."""
    try:
        hostid = args.get("hostid")
        ip_address = args.get("ip_address")
        port = args.get("port", "10050")
        interface_type = args.get("interface_type", "1")  # Default: Agent
        
        if not all([hostid, ip_address]):
            return "❌ Error: hostid and ip_address are required"
        
        interface_params = {
            "hostid": hostid,
            "type": interface_type,
            "main": 1,
            "useip": 1,
            "ip": ip_address,
            "dns": "",
            "port": port,
        }
        
        result = client.call("hostinterface.create", interface_params)
        if not result:
            return f"❌ Failed to add interface to host {hostid}"
        
        interfaceid = result[0] if isinstance(result, list) else result.get("interfaceids", [None])[0]
        
        return f"""✅ Interface Added!

🔗 Interface ID: {interfaceid}
🌐 IP: {ip_address}:{port}
🖥️ Host ID: {hostid}

Next: Wait for Zabbix server to poll the interface (30-60 seconds)."""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_sync_zabbix_sequences(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle sync_zabbix_sequences tool - Fix sequence table desynchronization."""
    try:
        # This requires direct database access, not API
        # Return instructions for manual execution
        return """⚠️ Sequence Sync - Manual Steps Required

After manual database operations, sequence tables can get out of sync.
Run these SQL commands on the Zabbix database:

```sql
-- Fix host sequence
UPDATE ids SET nextid = (SELECT MAX(hostid) + 1 FROM hosts) WHERE table_name = 'hosts';

-- Fix interface sequence  
UPDATE ids SET nextid = (SELECT MAX(interfaceid) + 1 FROM interface) WHERE table_name = 'interface';

-- Fix item sequence
UPDATE ids SET nextid = (SELECT MAX(itemid) + 1 FROM items) WHERE table_name = 'items';

-- Verify
SELECT table_name, nextid FROM ids WHERE table_name IN ('hosts', 'interface', 'items');
```

⚠️ Only run this once after manual DB edits. API-based operations handle sequences automatically."""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_create_maintenance_window(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_maintenance_window tool - Create maintenance window for hosts."""
    try:
        name = args.get("name")
        description = args.get("description", "")
        hostids = args.get("hostids", [])
        start_time = args.get("start_time")
        duration_seconds = args.get("duration_seconds")
        recurring_daily = args.get("recurring_daily", True)
        
        if not all([name, hostids, start_time is not None, duration_seconds is not None]):
            return "❌ Error: name, hostids, start_time, and duration_seconds are required"
        
        # Convert hostids to proper format
        if isinstance(hostids, str):
            hostids = [hostids]
        hostids = [str(h) for h in hostids]
        
        maintenance_params = {
            "name": name,
            "description": description,
            "active_since": int(datetime.now().timestamp()),
            "active_till": int(datetime.now().timestamp()) + (365 * 24 * 60 * 60),  # 1 year
            "maintenance_type": 0,  # 0 = normal maintenance
            "hostids": hostids,
        }
        
        # Add timeperiod for recurring windows
        if recurring_daily:
            maintenance_params["timeperiods"] = [{
                "timeperiod_type": 3,  # 3 = daily
                "start_time": start_time,
                "period": duration_seconds,
                "dayofweek": 127,  # All days (binary: 1111111)
                "every": 1,
            }]
        else:
            # One-time maintenance (starts immediately, lasts duration_seconds)
            maintenance_params["timeperiods"] = [{
                "timeperiod_type": 0,  # 0 = one-time
                "start_date": int(datetime.now().timestamp()),
                "period": duration_seconds,
            }]
        
        result = client.call("maintenance.create", maintenance_params)
        
        if not result:
            return f"❌ Failed to create maintenance window '{name}'"
        
        maintenanceid = result[0] if isinstance(result, list) else result.get("maintenanceids", [None])[0]
        
        # Format time for display
        hours = start_time // 3600
        minutes = (start_time % 3600) // 60
        duration_hours = duration_seconds // 3600
        
        schedule = f"{hours:02d}:{minutes:02d} for {duration_hours}h"
        if recurring_daily:
            schedule += " daily"
        
        return f"""✅ Maintenance Window Created!

📋 Name: {name}
🔗 ID: {maintenanceid}
⏰ Schedule: {schedule}
🖥️ Hosts: {len(hostids)} host(s)
📝 Description: {description or '(none)'}
🔄 Recurring: {'Yes (daily)' if recurring_daily else 'No (one-time)'}

Effect: Data collection paused, alerts suppressed during window."""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 1A: Host Lifecycle Management Handlers

def handle_update_host(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_host tool - Modify host properties."""
    try:
        hostid = args.get("hostid")
        if not hostid:
            return "❌ Error: hostid is required"
        
        update_params = {"hostid": hostid}
        changes = []
        
        if "name" in args:
            update_params["name"] = args["name"]
            changes.append(f"name → {args['name']}")
        
        if "status" in args:
            update_params["status"] = str(args["status"])
            status_text = "enabled" if args["status"] == 0 else "disabled"
            changes.append(f"status → {status_text}")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append("description updated")
        
        if "group_ids" in args:
            group_ids = args["group_ids"]
            if isinstance(group_ids, str):
                group_ids = [group_ids]
            update_params["groups"] = [{"groupid": gid} for gid in group_ids]
            changes.append(f"groups → {len(group_ids)} group(s)")
        
        if not changes:
            return "❌ Error: at least one property (name, status, description, or group_ids) must be specified"
        
        result = client.call("host.update", update_params)
        if not result:
            return f"❌ Failed to update host {hostid}"
        
        return f"""✅ Host Updated Successfully!

🖥️ Host ID: {hostid}
📝 Changes: {', '.join(changes)}"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_enable_host(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle enable_host tool - Re-enable monitoring for a host."""
    try:
        hostid = args.get("hostid")
        if not hostid:
            return "❌ Error: hostid is required"
        
        result = client.call("host.update", {
            "hostid": hostid,
            "status": 0,  # 0 = enabled
        })
        
        if not result:
            return f"❌ Failed to enable host {hostid}"
        
        return f"""✅ Host Enabled!

🖥️ Host ID: {hostid}
📊 Status: Monitoring active
🔄 Data collection: Resumed"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_disable_host(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle disable_host tool - Pause monitoring for a host."""
    try:
        hostid = args.get("hostid")
        if not hostid:
            return "❌ Error: hostid is required"
        
        result = client.call("host.update", {
            "hostid": hostid,
            "status": 1,  # 1 = disabled
        })
        
        if not result:
            return f"❌ Failed to disable host {hostid}"
        
        return f"""✅ Host Disabled!

🖥️ Host ID: {hostid}
📊 Status: Monitoring paused
⚠️ Data collection: Stopped
🔔 Alerts: Suppressed"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_host(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_host tool - Remove host from monitoring."""
    try:
        hostid = args.get("hostid")
        if not hostid:
            return "❌ Error: hostid is required"
        
        cascade = args.get("cascade", True)
        
        result = client.call("host.delete", [hostid])
        
        if not result:
            return f"❌ Failed to delete host {hostid}"
        
        return f"""✅ Host Deleted!

🖥️ Host ID: {hostid}
⚠️ Status: Removed from monitoring
📊 Data: {'Cascaded delete (all related data removed)' if cascade else 'Host record removed'}
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_host_interface(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_host_interface tool - Modify host interface config."""
    try:
        interfaceid = args.get("interfaceid")
        if not interfaceid:
            return "❌ Error: interfaceid is required"
        
        update_params = {"interfaceid": interfaceid}
        changes = []
        
        if "ip_address" in args:
            update_params["ip"] = args["ip_address"]
            changes.append(f"IP → {args['ip_address']}")
        
        if "port" in args:
            update_params["port"] = str(args["port"])
            changes.append(f"port → {args['port']}")
        
        if "useip" in args:
            update_params["useip"] = str(args["useip"])
            useip_text = "IP" if args["useip"] == 1 else "DNS"
            changes.append(f"mode → {useip_text}")
        
        if "dns" in args:
            update_params["dns"] = args["dns"]
            changes.append(f"DNS → {args['dns']}")
        
        if "bulk" in args:
            update_params["bulk"] = str(args["bulk"])
            bulk_text = "bulk" if args["bulk"] == 1 else "normal"
            changes.append(f"bulk → {bulk_text}")
        
        if not changes:
            return "❌ Error: at least one property (ip_address, port, useip, dns, or bulk) must be specified"
        
        result = client.call("hostinterface.update", update_params)
        
        if not result:
            return f"❌ Failed to update interface {interfaceid}"
        
        return f"""✅ Interface Updated!

🔗 Interface ID: {interfaceid}
📝 Changes: {', '.join(changes)}
⏱️ Effect: Next poll will use new config"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_host_interface(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_host_interface tool - Remove interface from host."""
    try:
        interfaceid = args.get("interfaceid")
        if not interfaceid:
            return "❌ Error: interfaceid is required"
        
        result = client.call("hostinterface.delete", [interfaceid])
        
        if not result:
            return f"❌ Failed to delete interface {interfaceid}"
        
        return f"""✅ Interface Deleted!

🔗 Interface ID: {interfaceid}
⚠️ Status: Removed from host
📊 Effect: Host may lose polling capability if this was the only interface
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 1B: Problem & Trigger Management Handlers

def handle_acknowledge_problem(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle acknowledge_problem tool - Mark problem as acknowledged."""
    try:
        problemid = args.get("problemid")
        message = args.get("message", "")
        
        if not problemid:
            return "❌ Error: problemid is required"
        
        ack_params = {
            "action": 0,  # Acknowledge
            "objectids": [problemid],
        }
        
        if message:
            ack_params["message"] = message
        
        result = client.call("acknowledges.create", ack_params)
        
        if not result:
            return f"❌ Failed to acknowledge problem {problemid}"
        
        return f"""✅ Problem Acknowledged!

⚠️ Problem ID: {problemid}
📝 Message: {message or '(no message)'}
👤 Status: Marked as reviewed
⏰ Timestamp: Now"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_problem_status(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_problem_status tool - Change problem state."""
    try:
        problemid = args.get("problemid")
        status = args.get("status")
        
        if not problemid or status is None:
            return "❌ Error: problemid and status are required"
        
        # Status: 0 = problem (open), 1 = resolved (closed)
        status_int = int(status)
        status_text = "Resolved" if status_int == 1 else "Open"
        
        result = client.call("problem.update", {
            "problemid": problemid,
            "status": str(status_int),
        })
        
        if not result:
            return f"❌ Failed to update problem {problemid}"
        
        return f"""✅ Problem Status Updated!

⚠️ Problem ID: {problemid}
📊 New Status: {status_text}
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_trigger(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_trigger tool - Modify trigger configuration."""
    try:
        triggerid = args.get("triggerid")
        if not triggerid:
            return "❌ Error: triggerid is required"
        
        update_params = {"triggerid": triggerid}
        changes = []
        
        if "expression" in args:
            update_params["expression"] = args["expression"]
            changes.append("expression updated")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append(f"description → {args['description'][:50]}")
        
        if "enabled" in args:
            update_params["status"] = str(args["enabled"])
            enabled_text = "enabled" if args["enabled"] == 1 else "disabled"
            changes.append(f"status → {enabled_text}")
        
        if "priority" in args:
            severity_map = {
                "0": "Not classified", "1": "Info", "2": "Warning",
                "3": "Average", "4": "High", "5": "Disaster"
            }
            update_params["priority"] = str(args["priority"])
            changes.append(f"priority → {severity_map.get(str(args['priority']), 'Unknown')}")
        
        if "manual_close" in args:
            update_params["manual_close"] = str(args["manual_close"])
            manual_text = "allowed" if args["manual_close"] == 1 else "disabled"
            changes.append(f"manual_close → {manual_text}")
        
        if not changes:
            return "❌ Error: at least one property must be specified"
        
        result = client.call("trigger.update", update_params)
        
        if not result:
            return f"❌ Failed to update trigger {triggerid}"
        
        return f"""✅ Trigger Updated!

🔔 Trigger ID: {triggerid}
📝 Changes: {', '.join(changes)}
⏰ Effect: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_enable_trigger(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle enable_trigger tool - Turn on trigger evaluation."""
    try:
        triggerid = args.get("triggerid")
        if not triggerid:
            return "❌ Error: triggerid is required"
        
        result = client.call("trigger.update", {
            "triggerid": triggerid,
            "status": 0,  # 0 = enabled
        })
        
        if not result:
            return f"❌ Failed to enable trigger {triggerid}"
        
        return f"""✅ Trigger Enabled!

🔔 Trigger ID: {triggerid}
📊 Status: Active
⚡ Evaluation: Started
🚨 Problems: Will be generated on match"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_disable_trigger(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle disable_trigger tool - Turn off trigger evaluation."""
    try:
        triggerid = args.get("triggerid")
        if not triggerid:
            return "❌ Error: triggerid is required"
        
        result = client.call("trigger.update", {
            "triggerid": triggerid,
            "status": 1,  # 1 = disabled
        })
        
        if not result:
            return f"❌ Failed to disable trigger {triggerid}"
        
        return f"""✅ Trigger Disabled!

🔔 Trigger ID: {triggerid}
📊 Status: Inactive
⚡ Evaluation: Stopped
🔇 Problems: Will NOT be generated"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_trigger(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_trigger tool - Remove trigger."""
    try:
        triggerid = args.get("triggerid")
        if not triggerid:
            return "❌ Error: triggerid is required"
        
        result = client.call("trigger.delete", [triggerid])
        
        if not result:
            return f"❌ Failed to delete trigger {triggerid}"
        
        return f"""✅ Trigger Deleted!

🔔 Trigger ID: {triggerid}
⚠️ Status: Removed
📊 Data: All associated problems and history removed
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_acknowledge_event(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle acknowledge_event tool - Acknowledge event."""
    try:
        eventid = args.get("eventid")
        message = args.get("message", "")
        acknowledge = args.get("acknowledge", 1)
        
        if not eventid:
            return "❌ Error: eventid is required"
        
        ack_params = {
            "objectids": [eventid],
            "action": int(acknowledge),  # 0 = unacknowledge, 1 = acknowledge
        }
        
        if message:
            ack_params["message"] = message
        
        result = client.call("acknowledges.create", ack_params)
        
        if not result:
            return f"❌ Failed to acknowledge event {eventid}"
        
        action_text = "Acknowledged" if acknowledge == 1 else "Unacknowledged"
        
        return f"""✅ Event {action_text}!

📅 Event ID: {eventid}
📝 Message: {message or '(no message)'}
👤 Status: Updated
⏰ Timestamp: Now"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 2A: Item & Metric Management Handlers

def handle_create_item(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_item tool - Create new monitored metric."""
    try:
        hostid = args.get("hostid")
        name = args.get("name")
        key_ = args.get("key_")
        type_ = args.get("type")
        value_type = args.get("value_type")
        interval = args.get("interval", "60")
        units = args.get("units", "")
        description = args.get("description", "")
        
        if not all([hostid, name, key_, type_, value_type]):
            return "❌ Error: hostid, name, key_, type, and value_type are required"
        
        item_params = {
            "hostid": hostid,
            "name": name,
            "key_": key_,
            "type": str(type_),
            "value_type": str(value_type),
            "delay": interval,  # Delay = polling interval
        }
        
        if units:
            item_params["units"] = units
        if description:
            item_params["description"] = description
        
        result = client.call("item.create", item_params)
        
        if not result:
            return f"❌ Failed to create item on host {hostid}"
        
        itemid = result[0] if isinstance(result, list) else result.get("itemids", [None])[0]
        
        type_map = {
            "0": "Zabbix agent", "2": "SNMP", "3": "IPMI",
            "7": "SSH", "10": "External", "11": "Database", "12": "JMX"
        }
        value_map = {"0": "float", "1": "string", "2": "log", "3": "unsigned int", "4": "text"}
        
        return f"""✅ Item Created!

📊 Item ID: {itemid}
🖥️ Host ID: {hostid}
📝 Name: {name}
🔑 Key: {key_}
📈 Type: {type_map.get(str(type_), 'Unknown')}
💾 Value Type: {value_map.get(str(value_type), 'Unknown')}
⏱️ Polling: {interval}
📋 Units: {units or '(none)'}

Next: Wait 1-2 minutes for data collection to start"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_item(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_item tool - Modify item configuration."""
    try:
        itemid = args.get("itemid")
        if not itemid:
            return "❌ Error: itemid is required"
        
        update_params = {"itemid": itemid}
        changes = []
        
        if "name" in args:
            update_params["name"] = args["name"]
            changes.append(f"name → {args['name']}")
        
        if "key_" in args:
            update_params["key_"] = args["key_"]
            changes.append(f"key → {args['key_']}")
        
        if "type" in args:
            update_params["type"] = str(args["type"])
            type_map = {"0": "Agent", "2": "SNMP", "3": "IPMI", "7": "SSH", "12": "JMX"}
            changes.append(f"type → {type_map.get(str(args['type']), 'Unknown')}")
        
        if "value_type" in args:
            update_params["value_type"] = str(args["value_type"])
            value_map = {"0": "float", "1": "string", "2": "log", "3": "uint", "4": "text"}
            changes.append(f"value_type → {value_map.get(str(args['value_type']), 'Unknown')}")
        
        if "interval" in args:
            update_params["delay"] = str(args["interval"])
            changes.append(f"interval → {args['interval']}")
        
        if "units" in args:
            update_params["units"] = args["units"]
            changes.append(f"units → {args['units']}")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append("description updated")
        
        if "enabled" in args:
            update_params["status"] = str(args["enabled"])
            status_text = "enabled" if args["enabled"] == 0 else "disabled"
            changes.append(f"status → {status_text}")
        
        if not changes:
            return "❌ Error: at least one property must be specified"
        
        result = client.call("item.update", update_params)
        
        if not result:
            return f"❌ Failed to update item {itemid}"
        
        return f"""✅ Item Updated!

📊 Item ID: {itemid}
📝 Changes: {', '.join(changes)}
⏰ Effect: Next poll will use new config"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_item(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_item tool - Remove monitored item."""
    try:
        itemid = args.get("itemid")
        if not itemid:
            return "❌ Error: itemid is required"
        
        result = client.call("item.delete", [itemid])
        
        if not result:
            return f"❌ Failed to delete item {itemid}"
        
        return f"""✅ Item Deleted!

📊 Item ID: {itemid}
⚠️ Status: Removed from monitoring
📊 Data: Historical data retained (can be purged separately)
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 2B: Template Management Handlers

def handle_create_template(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_template tool - Create new reusable template."""
    try:
        name = args.get("name")
        description = args.get("description", "")
        group_ids = args.get("group_ids", ["1"])  # Default: Templates group
        
        if not name:
            return "❌ Error: name is required"
        
        if isinstance(group_ids, str):
            group_ids = [group_ids]
        
        template_params = {
            "host": name,  # Zabbix API uses 'host' field for template hostname
            "groups": [{"groupid": gid} for gid in group_ids],
        }
        
        if description:
            template_params["description"] = description
        
        result = client.call("template.create", template_params)
        
        if not result:
            return f"❌ Failed to create template '{name}'"
        
        templateid = result[0] if isinstance(result, list) else result.get("templateids", [None])[0]
        
        return f"""✅ Template Created!

📋 Template ID: {templateid}
📝 Name: {name}
📖 Description: {description or '(none)'}
👥 Groups: {len(group_ids)} group(s)

Next: Link to hosts with link_template or link_multiple_templates"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_template(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_template tool - Modify template properties."""
    try:
        templateid = args.get("templateid")
        if not templateid:
            return "❌ Error: templateid is required"
        
        update_params = {"templateid": templateid}
        changes = []
        
        if "name" in args:
            update_params["host"] = args["name"]
            changes.append(f"name → {args['name']}")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append("description updated")
        
        if "group_ids" in args:
            group_ids = args["group_ids"]
            if isinstance(group_ids, str):
                group_ids = [group_ids]
            update_params["groups"] = [{"groupid": gid} for gid in group_ids]
            changes.append(f"groups → {len(group_ids)} group(s)")
        
        if not changes:
            return "❌ Error: at least one property (name, description, or group_ids) must be specified"
        
        result = client.call("template.update", update_params)
        
        if not result:
            return f"❌ Failed to update template {templateid}"
        
        return f"""✅ Template Updated!

📋 Template ID: {templateid}
📝 Changes: {', '.join(changes)}"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_template(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_template tool - Remove template."""
    try:
        templateid = args.get("templateid")
        if not templateid:
            return "❌ Error: templateid is required"
        
        result = client.call("template.delete", [templateid])
        
        if not result:
            return f"❌ Failed to delete template {templateid}"
        
        return f"""✅ Template Deleted!

📋 Template ID: {templateid}
⚠️ Status: Removed from system
🔗 Linked hosts: Automatically unlinked
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 2C: Template Link Management Handlers

def handle_unlink_template(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle unlink_template tool - Remove template from host."""
    try:
        hostid = args.get("hostid")
        templateid = args.get("templateid")
        clean = args.get("clean", 0)
        
        if not hostid or not templateid:
            return "❌ Error: hostid and templateid are required"
        
        update_params = {
            "hostid": hostid,
            "templates_clear": [templateid],
        }
        
        if clean == 1 or clean == "1":
            update_params["templates_clear_templates"] = "yes"
        
        result = client.call("host.update", update_params)
        
        if not result:
            return f"❌ Failed to unlink template {templateid} from host {hostid}"
        
        clean_text = "Items cleaned up" if clean else "Items retained"
        
        return f"""✅ Template Unlinked!

🖥️ Host ID: {hostid}
📋 Template ID: {templateid}
🧹 Cleanup: {clean_text}
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_link_multiple_templates(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle link_multiple_templates tool - Attach multiple templates."""
    try:
        hostid = args.get("hostid")
        template_ids = args.get("template_ids", [])
        
        if not hostid or not template_ids:
            return "❌ Error: hostid and template_ids are required"
        
        if isinstance(template_ids, str):
            template_ids = [template_ids]
        
        update_params = {
            "hostid": hostid,
            "templates": [{"templateid": tid} for tid in template_ids],
        }
        
        result = client.call("host.update", update_params)
        
        if not result:
            return f"❌ Failed to link templates to host {hostid}"
        
        return f"""✅ Templates Linked!

🖥️ Host ID: {hostid}
📋 Templates: {len(template_ids)} template(s) linked
⏰ Action: Immediate
🕐 Data Collection: Starts in ~1-2 minutes"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 2D: Host Group Management Handlers

def handle_create_host_group(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_host_group tool - Create new host group."""
    try:
        name = args.get("name")
        description = args.get("description", "")
        
        if not name:
            return "❌ Error: name is required"
        
        group_params = {"name": name}
        if description:
            group_params["description"] = description
        
        result = client.call("hostgroup.create", group_params)
        
        if not result:
            return f"❌ Failed to create host group '{name}'"
        
        groupid = result[0] if isinstance(result, list) else result.get("groupids", [None])[0]
        
        return f"""✅ Host Group Created!

👥 Group ID: {groupid}
📝 Name: {name}
📖 Description: {description or '(none)'}

Next: Assign hosts to this group with update_host"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 3A: Role Management Handlers

def handle_create_role(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle create_role tool - Create new Zabbix role."""
    try:
        name = args.get("name")
        type_ = args.get("type")
        description = args.get("description", "")
        
        if not name or type_ is None:
            return "❌ Error: name and type are required"
        
        role_params = {
            "name": name,
            "type": str(type_),
        }
        if description:
            role_params["description"] = description
        
        result = client.call("role.create", role_params)
        
        if not result:
            return f"❌ Failed to create role '{name}'"
        
        roleid = result[0] if isinstance(result, list) else result.get("roleids", [None])[0]
        
        type_map = {"1": "User", "2": "Admin", "3": "Super Admin"}
        type_text = type_map.get(str(type_), "Unknown")
        
        return f"""✅ Role Created!

👤 Role ID: {roleid}
📝 Name: {name}
📋 Type: {type_text}
📖 Description: {description or '(none)'}

Next: Assign permissions via Zabbix UI or assign to users"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_role(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_role tool - Modify role properties."""
    try:
        roleid = args.get("roleid")
        if not roleid:
            return "❌ Error: roleid is required"
        
        update_params = {"roleid": roleid}
        changes = []
        
        if "name" in args:
            update_params["name"] = args["name"]
            changes.append(f"name → {args['name']}")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append("description updated")
        
        if not changes:
            return "❌ Error: at least one property (name or description) must be specified"
        
        result = client.call("role.update", update_params)
        
        if not result:
            return f"❌ Failed to update role {roleid}"
        
        return f"""✅ Role Updated!

👤 Role ID: {roleid}
📝 Changes: {', '.join(changes)}"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_role(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_role tool - Remove custom role."""
    try:
        roleid = args.get("roleid")
        if not roleid:
            return "❌ Error: roleid is required"
        
        result = client.call("role.delete", [roleid])
        
        if not result:
            return f"❌ Failed to delete role {roleid} (may be built-in or in use)"
        
        return f"""✅ Role Deleted!

👤 Role ID: {roleid}
⚠️ Status: Removed from system
🔗 Users: Automatically reassigned to default role
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 3B: User Management Handlers

def handle_delete_user(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_user tool - Remove user account."""
    try:
        userid = args.get("userid")
        if not userid:
            return "❌ Error: userid is required"
        
        result = client.call("user.delete", [userid])
        
        if not result:
            return f"❌ Failed to delete user {userid}"
        
        return f"""✅ User Deleted!

👤 User ID: {userid}
⚠️ Status: Account removed
📝 Data: User history retained
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 3C: Host Group Management Handlers

def handle_update_host_group(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_host_group tool - Modify host group properties."""
    try:
        groupid = args.get("groupid")
        if not groupid:
            return "❌ Error: groupid is required"
        
        update_params = {"groupid": groupid}
        changes = []
        
        if "name" in args:
            update_params["name"] = args["name"]
            changes.append(f"name → {args['name']}")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append("description updated")
        
        if not changes:
            return "❌ Error: at least one property (name or description) must be specified"
        
        result = client.call("hostgroup.update", update_params)
        
        if not result:
            return f"❌ Failed to update host group {groupid}"
        
        return f"""✅ Host Group Updated!

👥 Group ID: {groupid}
📝 Changes: {', '.join(changes)}"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_host_group(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_host_group tool - Remove host group."""
    try:
        groupid = args.get("groupid")
        if not groupid:
            return "❌ Error: groupid is required"
        
        result = client.call("hostgroup.delete", [groupid])
        
        if not result:
            return f"❌ Failed to delete host group {groupid} (may have hosts assigned)"
        
        return f"""✅ Host Group Deleted!

👥 Group ID: {groupid}
⚠️ Status: Removed from system
🖥️ Hosts: Must be reassigned before deletion
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Phase 3D: Maintenance Window Management Handlers

def handle_get_maintenance_windows(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle get_maintenance_windows tool - List maintenance windows."""
    try:
        limit = args.get("limit", 50)
        
        windows = client.call("maintenance.get", {
            "output": ["maintenanceid", "name", "description", "active_since", "active_till"],
            "limit": limit,
        })
        
        if not windows:
            return "✅ No maintenance windows found"
        
        result = f"📋 Maintenance Windows ({len(windows)}):\n\n"
        for window in windows[:20]:
            from datetime import datetime
            start = datetime.fromtimestamp(int(window.get("active_since", 0))).strftime("%Y-%m-%d %H:%M")
            end = datetime.fromtimestamp(int(window.get("active_till", 0))).strftime("%Y-%m-%d %H:%M")
            result += f"📅 {window.get('name', 'Unknown')} (ID: {window.get('maintenanceid')})\n"
            result += f"   Period: {start} → {end}\n"
        
        if len(windows) > 20:
            result += f"\n... and {len(windows) - 20} more"
        
        return result
    except Exception as e:
        return f"❌ Error: {e}"


def handle_update_maintenance_window(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle update_maintenance_window tool - Modify maintenance window."""
    try:
        maintenanceid = args.get("maintenanceid")
        if not maintenanceid:
            return "❌ Error: maintenanceid is required"
        
        update_params = {"maintenanceid": maintenanceid}
        changes = []
        
        if "name" in args:
            update_params["name"] = args["name"]
            changes.append(f"name → {args['name']}")
        
        if "description" in args:
            update_params["description"] = args["description"]
            changes.append("description updated")
        
        if "active_since" in args:
            update_params["active_since"] = str(args["active_since"])
            changes.append("start time updated")
        
        if "active_till" in args:
            update_params["active_till"] = str(args["active_till"])
            changes.append("end time updated")
        
        if not changes:
            return "❌ Error: at least one property must be specified"
        
        result = client.call("maintenance.update", update_params)
        
        if not result:
            return f"❌ Failed to update maintenance window {maintenanceid}"
        
        return f"""✅ Maintenance Window Updated!

📅 Window ID: {maintenanceid}
📝 Changes: {', '.join(changes)}"""
    except Exception as e:
        return f"❌ Error: {e}"


def handle_delete_maintenance_window(client: ZabbixClient, args: Dict[str, Any]) -> str:
    """Handle delete_maintenance_window tool - Remove maintenance window."""
    try:
        maintenanceid = args.get("maintenanceid")
        if not maintenanceid:
            return "❌ Error: maintenanceid is required"
        
        result = client.call("maintenance.delete", [maintenanceid])
        
        if not result:
            return f"❌ Failed to delete maintenance window {maintenanceid}"
        
        return f"""✅ Maintenance Window Deleted!

📅 Window ID: {maintenanceid}
⚠️ Status: Removed
🔔 Alerts: Will resume for affected hosts
⏰ Action: Immediate"""
    except Exception as e:
        return f"❌ Error: {e}"


# Tool handler registry
TOOL_HANDLERS: Dict[str, Callable[[ZabbixClient, Dict[str, Any]], str]] = {
    "get_hosts": handle_get_hosts,
    "get_problems": handle_get_problems,
    "get_triggers": handle_get_triggers,
    "get_events": handle_get_events,
    "get_host_details": handle_get_host_details,
    "get_items": handle_get_items,
    "get_host_groups": handle_get_host_groups,
    "get_system_status": handle_get_system_status,
    "get_templates": handle_get_templates,
    "link_template": handle_link_template,
    "create_user": handle_create_user,
    "update_user": handle_update_user,
    "get_roles": handle_get_roles,
    "check_host_interface_availability": handle_check_host_interface_availability,
    "create_host": handle_create_host,
    "add_host_interface": handle_add_host_interface,
    "sync_zabbix_sequences": handle_sync_zabbix_sequences,
    "create_maintenance_window": handle_create_maintenance_window,
    # Phase 1A: Host Lifecycle
    "update_host": handle_update_host,
    "enable_host": handle_enable_host,
    "disable_host": handle_disable_host,
    "delete_host": handle_delete_host,
    "update_host_interface": handle_update_host_interface,
    "delete_host_interface": handle_delete_host_interface,
    # Phase 1B: Problem & Trigger Management
    "acknowledge_problem": handle_acknowledge_problem,
    "update_problem_status": handle_update_problem_status,
    "update_trigger": handle_update_trigger,
    "enable_trigger": handle_enable_trigger,
    "disable_trigger": handle_disable_trigger,
    "delete_trigger": handle_delete_trigger,
    "acknowledge_event": handle_acknowledge_event,
    # Phase 2A: Items & Metrics
    "create_item": handle_create_item,
    "update_item": handle_update_item,
    "delete_item": handle_delete_item,
    # Phase 2B: Template Management
    "create_template": handle_create_template,
    "update_template": handle_update_template,
    "delete_template": handle_delete_template,
    # Phase 2C: Template Links
    "unlink_template": handle_unlink_template,
    "link_multiple_templates": handle_link_multiple_templates,
    # Phase 2D: Host Groups
    "create_host_group": handle_create_host_group,
    # Phase 3A: Roles
    "create_role": handle_create_role,
    "update_role": handle_update_role,
    "delete_role": handle_delete_role,
    # Phase 3B: Users
    "delete_user": handle_delete_user,
    # Phase 3C: Host Groups (update/delete)
    "update_host_group": handle_update_host_group,
    "delete_host_group": handle_delete_host_group,
    # Phase 3D: Maintenance Windows
    "get_maintenance_windows": handle_get_maintenance_windows,
    "update_maintenance_window": handle_update_maintenance_window,
    "delete_maintenance_window": handle_delete_maintenance_window,
}


def get_tool_handler(name: str) -> Optional[Callable[[ZabbixClient, Dict[str, Any]], str]]:
    """Get handler for a tool by name."""
    return TOOL_HANDLERS.get(name)
