# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP server for fast Android screenshots via scrcpy frame buffer (~50ms latency). Falls back to adb (~500ms) when scrcpy unavailable.

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest

# Run single test
pytest tests/test_name.py::test_function -v

# Run the server locally
python -m screen_buffer_mcp
```

## Architecture

```
src/screen_buffer_mcp/
├── server.py     # MCP server - defines tools, handles JSON-RPC protocol
├── router.py     # DeviceRouter - backend selection + automatic fallback
└── backends/
    ├── scrcpy.py # Fast backend (~50ms) - MYScrcpy for scrcpy 3.x
    └── adb.py    # Fallback backend (~500ms) - shell commands via adb
```

**DeviceRouter pattern**: Every operation first tries scrcpy, falls back to adb on failure. Connection state is cached after first check.

**Frame buffer**: ScrcpyBackend maintains a 10-frame circular buffer (~160ms at 60fps). A background thread polls frames at ~60fps with lock protection. Screenshots return the latest cached frame instantly.

## Key Implementation Details

- `ScrcpyBackend.connect()` runs blocking MYScrcpy initialization in executor
- Frame polling thread writes to `_frame_buffer` deque with `_lock` protection
- `AdbBackend` uses temp files for screenshots (screencap → pull → read → cleanup)
- Key presses map string names ("BACK", "HOME") to Android keycodes in `adb.py:key_map`

## Recording

Video recording uses a separate `scrcpy --record` process (not frame storage):

- `start_recording(path)` spawns `scrcpy -s {device} --record {path} --no-playback`
- `stop_recording()` terminates the process gracefully, allowing scrcpy to finalize the MP4
- Recording runs independently from the frame buffer - both work simultaneously
- Zero memory overhead since encoding happens on device

**MCP Tools:**
- `device_start_recording` - Start recording to file
- `device_stop_recording` - Stop recording, returns duration/size
- `device_recording_status` - Check if recording is active

## Environment Variables

- `SCREEN_BUFFER_LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
