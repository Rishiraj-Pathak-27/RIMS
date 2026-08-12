"""
stream_router.py
FastAPI router that exposes the SSE endpoint and pipeline controls.
"""

import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from live_data_injection_pipeline.stream_engine import (
    subscribe,
    unsubscribe,
    get_risk_history,
    get_demand_history,
    start_engine,
    stop_engine,
    TICK_INTERVAL,
)

pipeline_router = APIRouter(
    prefix="/api/pipeline",
    tags=["Live Data Injection Pipeline"],
)


@pipeline_router.get("/status")
async def pipeline_status():
    """Return pipeline status and history lengths."""
    return {
        "status": "running",
        "tick_interval_seconds": TICK_INTERVAL,
        "risk_history_length": len(get_risk_history()),
        "demand_history_length": len(get_demand_history()),
    }


@pipeline_router.get("/history/risk")
async def risk_history():
    """Return the recent risk prediction history (last ~5 min)."""
    return get_risk_history()


@pipeline_router.get("/history/demand")
async def demand_history():
    """Return the recent demand prediction history (last ~5 min)."""
    return get_demand_history()


@pipeline_router.get("/stream")
async def sse_stream(request: Request):
    """
    Server-Sent Events endpoint.
    Clients connect here and receive a JSON event every ~10 seconds
    with fresh ML predictions.
    """
    queue = subscribe()

    async def event_generator():
        try:
            # Send initial history burst so the client has data immediately
            risk_hist = get_risk_history()
            demand_hist = get_demand_history()

            init_event = json.dumps({
                "type": "init",
                "risk_history": risk_hist,
                "demand_history": demand_hist,
            })
            yield f"data: {init_event}\n\n"

            # Then stream live ticks
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent proxy/browser timeout
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
