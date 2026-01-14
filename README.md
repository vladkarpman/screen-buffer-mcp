# screen-buffer-mcp

MCP server for fast Android screenshots via scrcpy frame buffer (~50ms latency).

<!-- mcp-name: io.github.vladkarpman/screen-buffer-mcp -->

## Features

- **Fast screenshots** via scrcpy frame buffer (~50ms vs ~500ms with adb)
- **10-frame circular buffer** for instant access to recent frames
- **Historical frame access** via `device_get_frame` for debugging/recording
- **Automatic fallback** to adb when scrcpy unavailable
- **Works with Claude Code** and any MCP-compatible client

## Requirements

- macOS 12+ or Linux
- Python 3.11+
- adb (Android Debug Bridge)
- scrcpy 3.x installed
- Android device connected via USB

## Usage with Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "screen-buffer": {
      "command": "uvx",
      "args": ["screen-buffer-mcp"]
    }
  }
}
```

Or add globally:

```bash
claude mcp add screen-buffer -s user -- uvx screen-buffer-mcp
```

## Available Tools

| Tool | Description | Latency |
|------|-------------|---------|
| `device_screenshot` | Capture latest frame from buffer | ~50ms (scrcpy) / ~500ms (adb) |
| `device_get_frame` | Get historical frame at offset | ~10ms |
| `device_list` | List connected devices | ~100ms |
| `device_screen_size` | Get screen dimensions | ~10ms |
| `device_backend_status` | Check active backend | instant |

## How It Works

The server maintains a 10-frame circular buffer from the scrcpy video stream:

1. **scrcpy backend** (preferred): Connects to scrcpy server on device in video-only mode. Continuously captures frames at ~60fps into a circular buffer. Screenshots return the latest buffered frame instantly.

2. **adb backend** (fallback): Uses `adb exec-out screencap -p` for screenshots. Works everywhere but slower (~500ms per screenshot).

## Frame Buffer

The frame buffer stores the last 10 frames (~160ms at 60fps), enabling:

- **Instant screenshots**: Latest frame always ready, no capture delay
- **Historical access**: Get frames from before an action for debugging
- **Recording support**: Extract frames at specific offsets

```python
# Get latest screenshot
device_screenshot()

# Get frame from 100ms ago (offset 6 at 60fps)
device_get_frame(offset=6)
```

## Configuration

### Environment Variables

- `SCREEN_BUFFER_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

### Multiple Devices

Specify device ID for multi-device setups:

```python
device_screenshot(device="RFCW318P7NV")
```

## Use with mobile-mcp

For full device control (taps, swipes, typing), combine with [mobile-mcp](https://github.com/anthropics/mobile-mcp):

```json
{
  "mcpServers": {
    "screen-buffer": {
      "command": "uvx",
      "args": ["screen-buffer-mcp"]
    },
    "mobile-mcp": {
      "command": "npx",
      "args": ["-y", "@mobilenext/mobile-mcp@latest"]
    }
  }
}
```

- **screen-buffer-mcp**: Fast screenshots (~50ms)
- **mobile-mcp**: Device input (tap, swipe, type)

## Development

```bash
git clone https://github.com/vladkarpman/screen-buffer-mcp
cd screen-buffer-mcp
pip install -e ".[dev]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [mobile-mcp](https://github.com/anthropics/mobile-mcp) - Official Anthropic mobile MCP
- [MYScrcpy](https://github.com/nicholasrobinson/myscrcpy) - Python scrcpy client
- [Claude Code](https://claude.ai/code) - AI coding assistant
