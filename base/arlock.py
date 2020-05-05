#!/usr/bin/env python3

import asyncio
import contextvars

class ARLock:
    """
    An async reentrant lock -- locking while inside the lock doesn't cause
    deadlock.

    This lock is also an async context manager.
    """
    def __init__(self):
        self._ctxcount = contextvars.ContextVar("ARLock._ctxcount", default=0)
        self._lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquires the lock. This shouldn't usually be used -- use the lock as a
        context manager instead.
        """
        count = self._ctxcount.get()
        if count == 0:
            # we gotta lock
            await self._lock.acquire()
        self._ctxcount.set(count+1)

    def release(self):
        """
        Releases the lock. This shouldn't usually be used -- use the lock as a
        context manager instead.
        """
        count = self._ctxcount.get()
        if count <= 0:
            raise RuntimeError("cannot release un-acquired lock")
        if count == 1:
            self._lock.release()
        self._ctxcount.set(count - 1)

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, _exc_type, _exc, _tb):
        self.release()
