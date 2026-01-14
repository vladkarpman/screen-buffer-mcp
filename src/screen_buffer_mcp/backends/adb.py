#!/usr/bin/env python3
"""ADB backend - fallback device interaction via adb commands.

Provides ~500ms latency for operations. Used when scrcpy is not available.

Requirements:
- adb installed and in PATH
- Android device connected via USB or WiFi
"""

import asyncio
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("screen-buffer-mcp.adb")


class AdbBackend:
    """Device interaction using adb commands (fallback)."""

    def __init__(self):
        self._default_device: str | None = None

    async def _run_adb(self, *args: str, device: str | None = None) -> tuple[str, str, int]:
        """Run adb command and return (stdout, stderr, returncode)."""
        cmd = ["adb"]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(args)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode(), stderr.decode(), proc.returncode

    async def _get_device(self, device: str | None) -> str | None:
        """Get device ID, using default if not specified."""
        if device:
            return device
        if self._default_device:
            return self._default_device

        # Get first available device
        devices = await self.list_devices()
        if devices:
            self._default_device = devices[0]["id"]
            return self._default_device
        return None

    async def list_devices(self) -> list[dict[str, Any]]:
        """List connected devices."""
        stdout, _, _ = await self._run_adb("devices", "-l")

        devices = []
        for line in stdout.strip().split("\n")[1:]:  # Skip header
            if not line.strip() or "offline" in line:
                continue

            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                device_id = parts[0]

                # Extract model if available
                model = None
                for part in parts:
                    if part.startswith("model:"):
                        model = part.split(":")[1]

                devices.append({
                    "id": device_id,
                    "name": model or device_id,
                    "platform": "android",
                    "state": "online"
                })

        return devices

    async def screenshot(self, device: str | None = None) -> bytes:
        """Take a screenshot. Returns PNG bytes."""
        dev = await self._get_device(device)

        # Use screencap and pull
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name

        try:
            # Capture to device
            await self._run_adb("shell", "screencap", "-p", "/sdcard/screenshot.png", device=dev)

            # Pull to local
            await self._run_adb("pull", "/sdcard/screenshot.png", tmp_path, device=dev)

            # Read file
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)
            await self._run_adb("shell", "rm", "/sdcard/screenshot.png", device=dev)

    async def tap(self, x: int, y: int, device: str | None = None) -> None:
        """Tap at coordinates."""
        dev = await self._get_device(device)
        await self._run_adb("shell", "input", "tap", str(x), str(y), device=dev)

    async def swipe(
        self,
        start_x: int, start_y: int,
        end_x: int, end_y: int,
        duration_ms: int = 300,
        device: str | None = None
    ) -> None:
        """Swipe from start to end coordinates."""
        dev = await self._get_device(device)
        await self._run_adb(
            "shell", "input", "swipe",
            str(start_x), str(start_y),
            str(end_x), str(end_y),
            str(duration_ms),
            device=dev
        )

    async def type_text(self, text: str, device: str | None = None) -> None:
        """Type text."""
        dev = await self._get_device(device)
        # Escape special characters for shell
        escaped = text.replace("\\", "\\\\").replace(" ", "%s").replace("'", "\\'")
        await self._run_adb("shell", "input", "text", escaped, device=dev)

    async def press_key(self, key: str, device: str | None = None) -> None:
        """Press a key."""
        dev = await self._get_device(device)

        # Map key names to Android keycodes
        key_map = {
            "BACK": "4",
            "HOME": "3",
            "ENTER": "66",
            "VOLUME_UP": "24",
            "VOLUME_DOWN": "25",
            "POWER": "26",
            "TAB": "61",
            "ESCAPE": "111",
            "DELETE": "67",
        }

        keycode = key_map.get(key.upper(), key)
        await self._run_adb("shell", "input", "keyevent", keycode, device=dev)

    async def get_screen_size(self, device: str | None = None) -> tuple[int, int]:
        """Get screen size."""
        dev = await self._get_device(device)
        stdout, _, _ = await self._run_adb("shell", "wm", "size", device=dev)

        # Parse "Physical size: 1080x2340"
        match = re.search(r"(\d+)x(\d+)", stdout)
        if match:
            return int(match.group(1)), int(match.group(2))

        # Default fallback
        return 1080, 2340
