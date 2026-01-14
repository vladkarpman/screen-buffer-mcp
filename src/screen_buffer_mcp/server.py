#!/usr/bin/env python3
"""Device Manager MCP Server - provides fast screenshots via scrcpy frame buffer."""

import asyncio
import base64
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .router import DeviceRouter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("screen-buffer-mcp")

# Create MCP server
server = Server("screen-buffer")

# Global router instance
router: DeviceRouter | None = None


def get_router() -> DeviceRouter:
    """Get or create the device router."""
    global router
    if router is None:
        router = DeviceRouter()
    return router


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available device tools."""
    return [
        Tool(
            name="device_screenshot",
            description="Take a screenshot of the device screen. Returns base64-encoded PNG image. Uses scrcpy frame buffer for ~50ms latency when available, falls back to adb (~500ms).",
            inputSchema={
                "type": "object",
                "properties": {
                    "device": {
                        "type": "string",
                        "description": "Device ID (optional, uses first available if not specified)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="device_get_frame",
            description="Get a frame from the scrcpy buffer at specified offset. Offset 0 = latest frame, 1 = previous frame, etc. Buffer holds last 10 frames.",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Frame offset from latest (0=latest, 1=previous, etc.)",
                        "default": 0
                    },
                    "device": {
                        "type": "string",
                        "description": "Device ID (optional)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="device_list",
            description="List all connected Android devices.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="device_screen_size",
            description="Get the screen size of the device in pixels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "device": {"type": "string", "description": "Device ID (optional)"}
                },
                "required": []
            }
        ),
        Tool(
            name="device_backend_status",
            description="Get the current backend status showing scrcpy connection and frame buffer info.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Handle tool calls."""
    r = get_router()

    try:
        if name == "device_screenshot":
            device = arguments.get("device")
            image_data, backend_used = await r.screenshot(device)

            return [
                ImageContent(
                    type="image",
                    data=base64.b64encode(image_data).decode("utf-8"),
                    mimeType="image/png"
                ),
                TextContent(
                    type="text",
                    text=f"Screenshot captured via {backend_used}"
                )
            ]

        elif name == "device_get_frame":
            offset = arguments.get("offset", 0)
            device = arguments.get("device")
            image_data, backend_used = await r.get_frame_at_offset(offset, device)

            return [
                ImageContent(
                    type="image",
                    data=base64.b64encode(image_data).decode("utf-8"),
                    mimeType="image/png"
                ),
                TextContent(
                    type="text",
                    text=f"Frame at offset {offset} captured via {backend_used}"
                )
            ]

        elif name == "device_list":
            devices = await r.list_devices()
            return [TextContent(
                type="text",
                text=json.dumps(devices, indent=2)
            )]

        elif name == "device_screen_size":
            device = arguments.get("device")
            width, height = await r.get_screen_size(device)
            return [TextContent(
                type="text",
                text=f"Screen size: {width}x{height}"
            )]

        elif name == "device_backend_status":
            status = r.get_backend_status()
            return [TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.exception(f"Error in {name}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    logger.info("Starting device-manager MCP server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
