#!/usr/bin/env python3
"""Device Router - selects between scrcpy (fast) and adb (fallback) backends."""

import asyncio
import logging
import time
from typing import Any

from .backends.scrcpy import ScrcpyBackend
from .backends.adb import AdbBackend

logger = logging.getLogger("device-manager-mcp.router")


class DeviceRouter:
    """Routes device operations to the best available backend.

    Automatically uses scrcpy for fast operations (~50ms) when available,
    falling back to adb (~500ms) otherwise.
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
                    logger.info("scrcpy backend connected - using fast path")
                else:
                    logger.info("scrcpy backend not available - using adb fallback")
            except Exception as e:
                logger.warning(f"scrcpy backend check failed: {e}")
                self._scrcpy_available = False
        return self._scrcpy_available

    def get_backend_status(self) -> dict[str, Any]:
        """Get current backend status."""
        return {
            "scrcpy_available": self._scrcpy_available,
            "scrcpy_connected": self._scrcpy.is_connected if self._scrcpy else False,
            "primary_backend": "scrcpy" if self._scrcpy_available else "adb"
        }

    async def screenshot(self, device: str | None = None) -> tuple[bytes, str]:
        """Take a screenshot. Returns (image_data, backend_used)."""
        if await self._check_scrcpy_available():
            try:
                start = time.perf_counter()
                data = await self.scrcpy.screenshot()
                elapsed = (time.perf_counter() - start) * 1000
                logger.debug(f"scrcpy screenshot: {elapsed:.1f}ms")
                return data, "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy screenshot failed, falling back to adb: {e}")

        # Fallback to adb
        data = await self.adb.screenshot(device)
        return data, "adb"

    async def tap(self, x: int, y: int, device: str | None = None) -> tuple[float, str]:
        """Tap at coordinates. Returns (latency_ms, backend_used)."""
        if await self._check_scrcpy_available():
            try:
                start = time.perf_counter()
                await self.scrcpy.tap(x, y)
                latency = (time.perf_counter() - start) * 1000
                return latency, "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy tap failed, falling back to adb: {e}")

        # Fallback to adb
        start = time.perf_counter()
        await self.adb.tap(x, y, device)
        latency = (time.perf_counter() - start) * 1000
        return latency, "adb"

    async def swipe(
        self,
        start_x: int, start_y: int,
        end_x: int, end_y: int,
        duration_ms: int = 300,
        device: str | None = None
    ) -> tuple[float, str]:
        """Swipe on screen. Returns (latency_ms, backend_used)."""
        if await self._check_scrcpy_available():
            try:
                start = time.perf_counter()
                await self.scrcpy.swipe(start_x, start_y, end_x, end_y, duration_ms)
                latency = (time.perf_counter() - start) * 1000
                return latency, "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy swipe failed, falling back to adb: {e}")

        # Fallback to adb
        start = time.perf_counter()
        await self.adb.swipe(start_x, start_y, end_x, end_y, duration_ms, device)
        latency = (time.perf_counter() - start) * 1000
        return latency, "adb"

    async def type_text(self, text: str, device: str | None = None) -> str:
        """Type text. Returns backend_used."""
        if await self._check_scrcpy_available():
            try:
                await self.scrcpy.type_text(text)
                return "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy type failed, falling back to adb: {e}")

        await self.adb.type_text(text, device)
        return "adb"

    async def press_key(self, key: str, device: str | None = None) -> str:
        """Press a key. Returns backend_used."""
        if await self._check_scrcpy_available():
            try:
                await self.scrcpy.press_key(key)
                return "scrcpy"
            except Exception as e:
                logger.warning(f"scrcpy press_key failed, falling back to adb: {e}")

        await self.adb.press_key(key, device)
        return "adb"

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
