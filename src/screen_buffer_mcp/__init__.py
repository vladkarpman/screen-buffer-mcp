"""Screen Buffer MCP Server - Fast screenshots and frame buffer via scrcpy."""

import asyncio

__version__ = "1.0.0"

from .server import main as _async_main


def main():
    """Entry point for the MCP server."""
    asyncio.run(_async_main())


__all__ = ["main", "__version__"]
