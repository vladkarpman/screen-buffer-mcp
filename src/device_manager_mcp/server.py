#!/usr/bin/env python3
"""Device Manager MCP Server - provides fast device interaction tools."""

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
logger = logging.getLogger("device-manager-mcp")

# Create MCP server
server = Server("device-manager")

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
            description="Take a screenshot of the device screen. Returns base64-encoded PNG image. Uses scrcpy for ~40ms latency when available, falls back to adb (~500ms).",
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
            name="device_tap",
            description="Tap on the screen at the specified coordinates. Uses scrcpy for ~50ms latency when available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate in pixels"},
                    "y": {"type": "integer", "description": "Y coordinate in pixels"},
                    "device": {"type": "string", "description": "Device ID (optional)"}
                },
                "required": ["x", "y"]
            }
        ),
        Tool(
            name="device_swipe",
            description="Swipe on the screen from start to end coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "Start X coordinate"},
                    "start_y": {"type": "integer", "description": "Start Y coordinate"},
                    "end_x": {"type": "integer", "description": "End X coordinate"},
                    "end_y": {"type": "integer", "description": "End Y coordinate"},
                    "duration_ms": {"type": "integer", "description": "Swipe duration in milliseconds", "default": 300},
                    "device": {"type": "string", "description": "Device ID (optional)"}
                },
                "required": ["start_x", "start_y", "end_x", "end_y"]
            }
        ),
        Tool(
            name="device_type",
            description="Type text on the device.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "device": {"type": "string", "description": "Device ID (optional)"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="device_press_key",
            description="Press a key on the device (e.g., BACK, HOME, ENTER).",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press: BACK, HOME, ENTER, VOLUME_UP, VOLUME_DOWN, POWER, TAB, ESCAPE, DELETE"},
                    "device": {"type": "string", "description": "Device ID (optional)"}
                },
                "required": ["key"]
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
            description="Get the current backend status showing whether scrcpy (fast) or adb (fallback) is being used.",
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

        elif name == "device_tap":
            x = arguments["x"]
            y = arguments["y"]
            device = arguments.get("device")

            latency_ms, backend_used = await r.tap(x, y, device)
            return [TextContent(
                type="text",
                text=f"Tapped at ({x}, {y}) via {backend_used} ({latency_ms:.1f}ms)"
            )]

        elif name == "device_swipe":
            start_x = arguments["start_x"]
            start_y = arguments["start_y"]
            end_x = arguments["end_x"]
            end_y = arguments["end_y"]
            duration_ms = arguments.get("duration_ms", 300)
            device = arguments.get("device")

            latency_ms, backend_used = await r.swipe(
                start_x, start_y, end_x, end_y, duration_ms, device
            )
            return [TextContent(
                type="text",
                text=f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y}) via {backend_used} ({latency_ms:.1f}ms)"
            )]

        elif name == "device_type":
            text = arguments["text"]
            device = arguments.get("device")

            backend_used = await r.type_text(text, device)
            return [TextContent(
                type="text",
                text=f"Typed '{text}' via {backend_used}"
            )]

        elif name == "device_press_key":
            key = arguments["key"]
            device = arguments.get("device")

            backend_used = await r.press_key(key, device)
            return [TextContent(
                type="text",
                text=f"Pressed {key} via {backend_used}"
            )]

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
