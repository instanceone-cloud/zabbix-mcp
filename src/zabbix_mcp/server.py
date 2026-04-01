"""Zabbix MCP Server - Main MCP implementation."""

import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import load_config
from .client import ZabbixClient, ZabbixAPIError
from .tools import TOOLS, get_tool_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("zabbix-mcp")
client: ZabbixClient | None = None


def get_client() -> ZabbixClient:
    global client
    if client is None:
        raise RuntimeError("Zabbix client not initialized")
    return client


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    zc = get_client()
    try:
        handler = get_tool_handler(name)
        result = handler(zc, arguments)
        return [TextContent(type="text", text=str(result))]
    except ZabbixAPIError as e:
        return [TextContent(type="text", text=f"Zabbix API error: {e}")]
    except Exception as e:
        logger.exception("Unexpected error while executing tool '%s': %s", name, e)
        return [TextContent(type="text", text="Error executing tool")]


async def main_async():
    global client
    config = load_config()
    logger.info(f"Loaded config: {config.host}:{config.port}")

    client = ZabbixClient(
        base_url=config.base_url,
        username=config.username,
        password=config.password,
        verify_ssl=config.verify_ssl,
    )

    api_token = os.getenv("ZABBIX_API_TOKEN")
    if api_token:
        client.token = api_token
        logger.info("Using ZABBIX_API_TOKEN directly")
    else:
        client.authenticate()
        logger.info("Authenticated with Zabbix")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
