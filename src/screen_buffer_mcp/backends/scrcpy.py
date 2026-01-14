#!/usr/bin/env python3
"""Scrcpy backend - fast screenshots via scrcpy video stream.

Uses MYScrcpy library for scrcpy 3.x support. Provides ~50ms latency
for screenshots by maintaining a circular frame buffer.

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
from collections import deque
from typing import Any

logger = logging.getLogger("screen-buffer-mcp.scrcpy")

# Frame buffer size
FRAME_BUFFER_SIZE = 10

# Try to import MYScrcpy
try:
    from adbutils import adb
    from myscrcpy.core import Session, VideoArgs
    from PIL import Image
    import numpy as np
    MYSCRCPY_AVAILABLE = True
except ImportError:
    MYSCRCPY_AVAILABLE = False
    adb = None
    Session = None
    VideoArgs = None
    Image = None
    np = None


class ScrcpyBackend:
    """Fast screenshots using MYScrcpy (scrcpy 3.x) frame buffer."""

    def __init__(self):
        self._session: "Session | None" = None
        self._device_id: str | None = None
        self._connected = False
        self._width = 0
        self._height = 0
        # Circular buffer of last N frames
        self._frame_buffer: deque = deque(maxlen=FRAME_BUFFER_SIZE)
        self._lock = threading.Lock()
        self._frame_thread: threading.Thread | None = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        """Check if video stream is connected."""
        return self._connected and self._session is not None and self._session.va is not None

    def _frame_polling_loop(self) -> None:
        """Continuously poll for new frames and add to buffer."""
        while self._running and self._session is not None:
            try:
                if self._session.va is not None:
                    frame = self._session.va.get_frame()
                    if frame is not None:
                        with self._lock:
                            self._frame_buffer.append({
                                'frame': frame,
                                'timestamp': time.time()
                            })
                            if self._height == 0:
                                self._height, self._width = frame.shape[:2]
                time.sleep(0.016)  # ~60 fps polling
            except Exception as e:
                logger.debug(f"Frame polling error: {e}")
                time.sleep(0.1)

    async def connect(self, device_id: str | None = None) -> bool:
        """Connect to device via scrcpy video stream. Returns True if successful."""
        if not MYSCRCPY_AVAILABLE:
            logger.warning("MYScrcpy not available - install with: pip install mysc adbutils")
            return False

        if self._connected and self._session:
            return True

        try:
            # Get device
            devices = adb.device_list()
            if not devices:
                logger.warning("No Android devices found")
                return False

            # Find requested device or use first
            device = None
            if device_id:
                for d in devices:
                    if d.serial == device_id:
                        device = d
                        break
                if not device:
                    logger.warning(f"Device {device_id} not found")
                    return False
            else:
                device = devices[0]

            self._device_id = device.serial
            logger.info(f"Connecting to {self._device_id}...")

            # Create session with video only (no control needed)
            loop = asyncio.get_event_loop()

            def _connect():
                self._session = Session(
                    device,
                    video_args=VideoArgs(fps=60),
                    control_args=None  # No control needed - just video stream
                )
                # Wait for connection
                time.sleep(1)
                return self._session.va is not None

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
        """Get latest screenshot from frame buffer. Returns PNG bytes."""
        if not self._connected or not self._session:
            raise RuntimeError("scrcpy not connected")

        with self._lock:
            if not self._frame_buffer:
                raise RuntimeError("No frames available in buffer")
            # Get most recent frame
            latest = self._frame_buffer[-1]
            frame = latest['frame']

        # Convert numpy array to PNG bytes
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    async def get_frame_at_offset(self, offset: int = 0) -> bytes:
        """Get frame at offset from latest (0 = latest, 1 = previous, etc.).

        Returns PNG bytes.
        """
        if not self._connected or not self._session:
            raise RuntimeError("scrcpy not connected")

        with self._lock:
            if not self._frame_buffer:
                raise RuntimeError("No frames available in buffer")

            # Clamp offset to buffer size
            offset = min(offset, len(self._frame_buffer) - 1)
            # Get frame at offset from end
            frame_data = self._frame_buffer[-(offset + 1)]
            frame = frame_data['frame']

        # Convert numpy array to PNG bytes
        img = Image.fromarray(frame)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def get_buffer_info(self) -> dict[str, Any]:
        """Get info about current frame buffer state."""
        with self._lock:
            count = len(self._frame_buffer)
            oldest_ts = self._frame_buffer[0]['timestamp'] if count > 0 else None
            newest_ts = self._frame_buffer[-1]['timestamp'] if count > 0 else None

        return {
            'frame_count': count,
            'buffer_size': FRAME_BUFFER_SIZE,
            'oldest_frame_age_ms': int((time.time() - oldest_ts) * 1000) if oldest_ts else None,
            'newest_frame_age_ms': int((time.time() - newest_ts) * 1000) if newest_ts else None,
        }

    async def get_screen_size(self) -> tuple[int, int]:
        """Get screen size from video stream."""
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
        self._frame_buffer.clear()
        logger.info("Disconnected from scrcpy")
