"""
SSE progress manager — one asyncio.Queue per session.
Background threads push events; the SSE endpoint streams them to the browser.
"""
import asyncio
import uuid
from typing import AsyncGenerator

_queues: dict[str, asyncio.Queue] = {}


def create_session() -> str:
    sid = str(uuid.uuid4())
    _queues[sid] = asyncio.Queue()
    return sid


async def push(session_id: str, message: dict) -> None:
    q = _queues.get(session_id)
    if q:
        await q.put(message)


def push_sync(session_id: str, loop: asyncio.AbstractEventLoop, message: dict) -> None:
    """Call from a synchronous worker thread to push an event."""
    q = _queues.get(session_id)
    if q and loop and not loop.is_closed():
        future = asyncio.run_coroutine_threadsafe(q.put(message), loop)
        try:
            future.result(timeout=5)
        except Exception:
            pass


async def stream(session_id: str) -> AsyncGenerator[dict, None]:
    """Async generator — yields event dicts until a done=True event."""
    q = _queues.get(session_id)
    if not q:
        yield {"done": True, "msg": "Session not found"}
        return
    while True:
        try:
            msg = await asyncio.wait_for(q.get(), timeout=120)
        except asyncio.TimeoutError:
            yield {"done": True, "msg": "Timeout"}
            break
        yield msg
        if msg.get("done"):
            _queues.pop(session_id, None)
            break
