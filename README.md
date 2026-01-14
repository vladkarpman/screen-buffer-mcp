# device-manager-mcp

MCP server for fast Android device interaction with scrcpy acceleration.

## Features

- **Fast operations** via scrcpy (~50ms latency)
- **Automatic fallback** to adb (~500ms) when scrcpy unavailable
- **Screenshots, taps, swipes, typing** - all device interactions
- **Works with Claude Code** and any MCP-compatible client

## Requirements

- macOS 12+, Python 3.11+, adb, scrcpy 3.x
- Android device connected via USB

See [docs/requirements.md](docs/requirements.md) for detailed setup instructions.

## Usage with Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "device-manager": {
      "command": "uvx",
      "args": ["device-manager-mcp"]
    }
  }
}
```

Or add globally:

```bash
claude mcp add device-manager -s user -- uvx device-manager-mcp
```

## Available Tools

| Tool | Description | Latency |
|------|-------------|---------|
| `device_screenshot` | Capture screen as PNG | ~40ms (scrcpy) / ~500ms (adb) |
| `device_tap` | Tap at coordinates | ~50ms (scrcpy) / ~200ms (adb) |
| `device_swipe` | Swipe gesture | ~300ms |
| `device_type` | Type text | ~100ms |
| `device_press_key` | Press BACK, HOME, ENTER, etc. | ~50ms |
| `device_list` | List connected devices | ~100ms |
| `device_screen_size` | Get screen dimensions | ~10ms |
| `device_backend_status` | Check active backend | instant |

## How It Works

The server automatically selects the best backend:

1. **scrcpy backend** (if available): Uses MYScrcpy library to communicate directly with scrcpy server on device. Provides ~50ms latency for screenshots and input.

2. **adb backend** (fallback): Uses standard `adb` commands. Works everywhere but slower (~500ms for screenshots).

## Example

```python
# Claude Code will automatically use these tools:

# Take a screenshot
device_screenshot()

# Tap at coordinates
device_tap(x=540, y=1200)

# Swipe down
device_swipe(start_x=540, start_y=800, end_x=540, end_y=1600)

# Type text
device_type(text="Hello World")

# Press back button
device_press_key(key="BACK")
```

## Configuration

### Environment Variables

- `DEVICE_MANAGER_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

### Multiple Devices

Specify device ID for multi-device setups:

```python
device_tap(x=100, y=200, device="RFCW318P7NV")
```

## Development

```bash
git clone https://github.com/vladkarpman/device-manager-mcp
cd device-manager-mcp
pip install -e ".[dev]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [mobile-mcp](https://github.com/anthropics/mobile-mcp) - Official Anthropic mobile MCP
- [MYScrcpy](https://github.com/nicholasrobinson/myscrcpy) - Python scrcpy client
- [Claude Code](https://claude.ai/code) - AI coding assistant
