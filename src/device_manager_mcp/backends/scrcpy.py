#!/usr/bin/env python3
"""Scrcpy backend - fast device interaction via scrcpy protocol.

Uses MYScrcpy library for scrcpy 3.x support. Provides ~50ms latency
for screenshots and input operations.

Requirements:
- scrcpy 3.x installed and in PATH
- Python 3.11+ (for MYScrcpy)
- pip install mysc adbutils pillow numpy
"""

import asyncio
import io
import logging
import threading
import time
from typing import Any

logger = logging.getLogger("device-manager-mcp.scrcpy")

# Try to import MYScrcpy
try:
    from adbutils import adb
    from myscrcpy.core import Session, VideoArgs, ControlArgs
    from myscrcpy.utils import Action
    from PIL import Image
    import numpy as np
    MYSCRCPY_AVAILABLE = True
except ImportError:
    MYSCRCPY_AVAILABLE = False
    adb = None
    Session = None
    VideoArgs = None
    ControlArgs = None
    Action = None
    Image = None
    np = None


class ScrcpyBackend:
    """Fast device interaction using MYScrcpy (scrcpy 3.x)."""

    def __init__(self):
        self._session: "Session | None" = None
        self._device_id: str | None = None
        self._connected = False
        self._width = 0
        self._height = 0
        self._last_frame: "np.ndarray | None" = None
        self._last_frame_time: float = 0
        self._lock = threading.Lock()
        self._frame_thread: threading.Thread | None = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _frame_polling_loop(self) -> None:
        """Continuously poll for new frames."""
        while self._running and self._session is not None:
            try:
                if self._session.va is not None:
                    frame = self._session.va.get_frame()
                    if frame is not None:
                        with self._lock:
                            self._last_frame = frame
                            self._last_frame_time = time.time()
                            if self._height == 0:
                                self._height, self._width = frame.shape[:2]
                time.sleep(0.016)  # ~60 fps polling
            except Exception as e:
                logger.debug(f"Frame polling error: {e}")
                time.sleep(0.1)

    async def connect(self) -> bool:
        """Try to connect to device via scrcpy. Returns True if successful."""
        if not MYSCRCPY_AVAILABLE:
            logger.warning("MYScrcpy not available - install with: pip install mysc adbutils")
            return False

        if self._connected and self._session:
            return True

        try:
            # Get first available device
            devices = adb.device_list()
            if not devices:
                logger.warning("No Android devices found")
                return False

            device = devices[0]
            self._device_id = device.serial
            logger.info(f"Connecting to {self._device_id}...")

            # Create session with video and control
            loop = asyncio.get_event_loop()

            def _connect():
                self._session = Session(
                    device,  # Pass AdbDevice object, not string
                    video_args=VideoArgs(fps=60),
                    control_args=ControlArgs()
                )
                # Wait for connection
                time.sleep(1)
                return self._session.va is not None and self._session.ca is not None

            connected = await loop.run_in_executor(None, _connect)

            if connected:
                self._connected = True
                self._running = True
                self._frame_thread = threading.Thread(target=self._frame_polling_loop, daemon=True)
                self._frame_thread.start()
                # Wait for first frame
                await asyncio.sleep(0.5)
                logger.info(f"scrcpy connected to {self._device_id}")
                return True
            else:
                logger.warning("scrcpy connection failed")
                return False

        except Exception as e:
            logger.warning(f"scrcpy connection error: {e}")
            return False

    async def screenshot(self) -> bytes:
        """Take a screenshot. Returns PNG bytes."""
        if not self._connected or not self._session:
            raise RuntimeError("scrcpy not connected")

        with self._lock:
            frame = self._last_frame

        if frame is None:
            raise RuntimeError("No frame available from scrcpy")

        # Convert numpy array to PNG bytes
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        if not self._connected or not self._session or not self._session.ca:
            raise RuntimeError("scrcpy not connected")

        if self._width == 0:
            raise RuntimeError("Screen size not available")

        loop = asyncio.get_event_loop()

        def _tap():
            self._session.ca.f_touch(Action.DOWN, x, y, self._width, self._height, 0)
            time.sleep(0.05)
            self._session.ca.f_touch(Action.RELEASE, x, y, self._width, self._height, 0)

        await loop.run_in_executor(None, _tap)

    async def swipe(
        self,
        start_x: int, start_y: int,
        end_x: int, end_y: int,
        duration_ms: int = 300
    ) -> None:
        """Swipe from start to end coordinates."""
        if not self._connected or not self._session or not self._session.ca:
            raise RuntimeError("scrcpy not connected")

        if self._width == 0:
            raise RuntimeError("Screen size not available")

        loop = asyncio.get_event_loop()

        def _swipe():
            steps = max(10, duration_ms // 30)
            step_delay = duration_ms / 1000.0 / steps
            dx = (end_x - start_x) / steps
            dy = (end_y - start_y) / steps

            self._session.ca.f_touch(Action.DOWN, start_x, start_y, self._width, self._height, 0)

            for i in range(1, steps + 1):
                x = int(start_x + dx * i)
                y = int(start_y + dy * i)
                self._session.ca.f_touch(Action.MOVE, x, y, self._width, self._height, 0)
                time.sleep(step_delay)

            self._session.ca.f_touch(Action.RELEASE, end_x, end_y, self._width, self._height, 0)

        await loop.run_in_executor(None, _swipe)

    async def type_text(self, text: str) -> None:
        """Type text using clipboard paste."""
        if not self._connected or not self._session or not self._session.ca:
            raise RuntimeError("scrcpy not connected")

        loop = asyncio.get_event_loop()

        def _type():
            self._session.ca.f_text_paste(text, paste=True)

        await loop.run_in_executor(None, _type)

    async def press_key(self, key: str) -> None:
        """Press a key (BACK, HOME, ENTER, etc.)."""
        if not self._connected:
            raise RuntimeError("scrcpy not connected")

        # Map key names to Android keycodes
        key_map = {
            "BACK": 4,
            "HOME": 3,
            "ENTER": 66,
            "VOLUME_UP": 24,
            "VOLUME_DOWN": 25,
            "POWER": 26,
            "TAB": 61,
            "ESCAPE": 111,
            "DELETE": 67,
        }

        keycode = key_map.get(key.upper())
        if keycode is None:
            raise ValueError(f"Unknown key: {key}")

        # Use adb for key events (more reliable)
        loop = asyncio.get_event_loop()

        def _press():
            import subprocess
            subprocess.run(
                ['adb', '-s', self._device_id, 'shell', 'input', 'keyevent', str(keycode)],
                capture_output=True, timeout=5
            )

        await loop.run_in_executor(None, _press)

    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen size."""
        if self._width > 0 and self._height > 0:
            return self._width, self._height

        raise RuntimeError("Screen size not available")

    def disconnect(self) -> None:
        """Disconnect from device."""
        self._running = False
        if self._frame_thread:
            self._frame_thread.join(timeout=1)
        if self._session:
            try:
                self._session.stop()
            except Exception:
                pass
        self._session = None
        self._connected = False
        self._width = 0
        self._height = 0
        logger.info("Disconnected from scrcpy")
