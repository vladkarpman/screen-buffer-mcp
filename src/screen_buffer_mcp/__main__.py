#!/usr/bin/env python3
"""Entry point for screen-buffer-mcp server."""

import asyncio
import sys

from .server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
