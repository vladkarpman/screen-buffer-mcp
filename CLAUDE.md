# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP server for fast Android device interaction. Provides ~50ms latency via scrcpy when available, with automatic fallback to adb (~500ms).

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest

# Run the server locally
python -m device_manager_mcp
```

## Architecture

```
server.py          # MCP server - defines tools, handles JSON-RPC protocol
    ↓
router.py          # DeviceRouter - backend selection + automatic fallback
    ↓
backends/
├── scrcpy.py     # Fast backend (~50ms) - uses MYScrcpy for scrcpy 3.x
└── adb.py        # Fallback backend (~500ms) - shell commands via adb
```

**DeviceRouter pattern**: Every operation first tries scrcpy, falls back to adb on failure. Connection state is cached after first check.

**ScrcpyBackend threading**: Uses a background thread for continuous frame polling (~60fps). Screenshot reads the latest cached frame for instant response.

## Key Implementation Details

- `ScrcpyBackend.connect()` runs blocking MYScrcpy initialization in executor
- Frame polling thread writes to `_last_frame` with lock protection
- `AdbBackend` uses temp files for screenshots (screencap → pull → read → cleanup)
- Key presses map string names ("BACK", "HOME") to Android keycodes

## Environment Variables

- `DEVICE_MANAGER_LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
