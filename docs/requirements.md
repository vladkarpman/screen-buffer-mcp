# Requirements

Prerequisites for using device-manager-mcp on macOS.

## System Requirements

| Requirement | Version | Verify |
|-------------|---------|--------|
| macOS | 12+ (Monterey) | `sw_vers` |
| Python | 3.11+ | `python3 --version` |
| uv | latest | `uv --version` |
| adb | any | `adb --version` |
| scrcpy | 3.x | `scrcpy --version` |

## Installation

Install dependencies via Homebrew:

```bash
brew install python@3.11 android-platform-tools scrcpy
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Device Setup

- Android device connected via USB
- Device must be authorized (`adb devices` shows "device" status, not "unauthorized")

## MCP Configuration

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

Or add globally via CLI:

```bash
claude mcp add device-manager -s user -- uvx device-manager-mcp
```

## Verification

After installation, verify everything works:

```bash
# 1. Verify device is connected and authorized
adb devices
# Expected: Shows device ID with "device" status

# 2. Verify scrcpy can connect
scrcpy --version
scrcpy  # Should mirror device screen, Ctrl+C to close

# 3. Test the MCP server directly
uvx device-manager-mcp
# Should start without errors, Ctrl+C to stop
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `adb devices` shows empty | Device not connected or USB debugging off | Check cable, enable USB debugging on device |
| `adb devices` shows "unauthorized" | Device hasn't authorized this computer | Accept the prompt on device screen |
| scrcpy fails to connect | adb server version mismatch | Run `adb kill-server && adb start-server` |
| Slow screenshots (~500ms) | Fell back to adb backend | Check scrcpy connection, restart MCP server |
