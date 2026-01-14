#!/usr/bin/env python3
"""Device Router - provides fast screenshots via scrcpy frame buffer."""

import logging
import time
from typing import Any

from .backends.scrcpy import ScrcpyBackend
from .backends.adb import AdbBackend

logger = logging.getLogger("screen-buffer-mcp.router")


class DeviceRouter:
    """Routes screenshot operations to scrcpy frame buffer.

    Uses scrcpy for fast screenshots (~50ms) via frame buffer.
    Falls back to adb for device listing and when scrcpy unavailable.
    """

    def __init__(self):
        self._scrcpy: ScrcpyBackend | None = None
        self._adb: AdbBackend | None = None
        self._scrcpy_available: bool | None = None  # None = not checked yet

    @property
    def scrcpy(self) -> ScrcpyBackend:
        """Get or create scrcpy backend."""
        if self._scrcpy is None:
            self._scrcpy = ScrcpyBackend()
        return self._scrcpy

    @property
    def adb(self) -> AdbBackend:
        """Get or create adb backend."""
        if self._adb is None:
            self._adb = AdbBackend()
        return self._adb

    async def _check_scrcpy_available(self) -> bool:
        """Check if scrcpy backend is available and connected."""
        if self._scrcpy_available is None:
            try:
                self._scrcpy_available = await self.scrcpy.connect()
                if self._scrcpy_available:
                    logger.info("scrcpy frame buffer connected - fast screenshots enabled")
                else:
                    logger.info("scrcpy not available - using adb fallback for screenshots")
            except Exception as e:
                logger.warning(f"scrcpy backend check failed: {e}")
                self._scrcpy_available = False
        return self._scrcpy_available

    def get_backend_status(self) -> dict[str, Any]:
        """Get current backend status."""
        return {
            "scrcpy_available": self._scrcpy_available,
            "scrcpy_connected": self._scrcpy.is_connected if self._scrcpy else False,
            "frame_buffer": self._scrcpy.get_buffer_info() if self._scrcpy and self._scrcpy.is_connected else None,
            "primary_backend": "scrcpy" if self._scrcpy_available else "adb"
        }

    async def screenshot(self, device: str | None = None) -> tuple[bytes, str]:
        """Take a screenshot from frame buffer. Returns (image_data, backend_used)."""
        if await self._check_scrcpy_available():
            try:
                start = time.perf_counter()
                data = await self.scrcpy.screenshot()
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug(f"scrcpy screenshot from buffer: {elapsed:.1f}ms")
                return data, "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy screenshot failed, falling back to adb: {e}")

        # Fallback to adb
        data = await self.adb.screenshot(device)
        return data, "adb"

    async def get_frame_at_offset(self, offset: int = 0, device: str | None = None) -> tuple[bytes, str]:
        """Get frame at offset from buffer (0=latest, 1=previous, etc.)."""
        if await self._check_scrcpy_available():
            try:
                data = await self.scrcpy.get_frame_at_offset(offset)
                return data, "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy get_frame_at_offset failed: {e}")
                # For offset > 0, no fallback possible
                if offset > 0:
                    raise RuntimeError(f"Cannot get historical frame (offset={offset}) without scrcpy buffer")

        # Fallback to adb for latest frame only
        data = await self.adb.screenshot(device)
        return data, "adb"

    async def list_devices(self) -> list[dict[str, Any]]:
        """List connected devices."""
        return await self.adb.list_devices()

    async def get_screen_size(self, device: str | None = None) -> tuple[int, int]:
        """Get screen size. Returns (width, height)."""
        if await self._check_scrcpy_available():
            try:
                return await self.scrcpy.get_screen_size()
            except Exception as e:
                logger.warning(f"scrcpy get_screen_size failed, falling back to adb: {e}")

        return await self.adb.get_screen_size(device)
