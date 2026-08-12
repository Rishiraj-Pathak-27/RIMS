"""
stream_engine.py
Core engine that runs the 10-second tick loop.
Each tick: generate order → ML inference → broadcast to all SSE subscribers.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Set
from asyncio import Queue

from live_data_injection_pipeline.data_generator import generate_order, generate_demand_input

# ─── Global state ──────────────────────────────────────────────────────────

# Connected SSE client queues
_subscribers: Set[Queue] = set()

# Recent history for charts (rolling window)
_risk_history: list[dict] = []
_demand_history: list[dict] = []

MAX_HISTORY = 30          # Keep last 30 ticks (~5 minutes at 10s)
TICK_INTERVAL = 10        # Seconds between each data injection

_engine_task: asyncio.Task | None = None


def get_risk_history() -> list[dict]:
    return list(_risk_history)


def get_demand_history() -> list[dict]:
    return list(_demand_history)


def subscribe() -> Queue:
    """Register a new SSE client. Returns a queue the client reads from."""
    q: Queue = Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: Queue) -> None:
    """Remove an SSE client queue."""
    _subscribers.discard(q)


async def _broadcast(event: dict) -> None:
    """Push an event dict to every connected client."""
    dead: list[Queue] = []
    for q in _subscribers:
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        _subscribers.discard(q)


async def _tick(ml_handler) -> None:
    """Single pipeline tick: generate → infer → broadcast."""
    tick_time = datetime.now(timezone.utc).isoformat()
    tick_label = datetime.now().strftime("%H:%M:%S")

    # ── 1. Risk prediction on a freshly generated order ─────────────
    order = generate_order()
    try:
        risk_result = ml_handler.predict_supply_chain_risk(order)
    except Exception as e:
        risk_result = {
            "delivery_risk": 0,
            "anomaly_prediction": "Error",
            "anomaly_score": 0,
            "anomaly_risk": 0,
            "supply_chain_risk": 0,
            "risk_category": "Unknown",
        }

    risk_event = {
        "tick": tick_label,
        "timestamp": tick_time,
        "order_summary": {
            "segment": order["customer_segment"],
            "market": order["market"],
            "sales": order["sales"],
            "quantity": order["quantity"],
            "shipping_mode": order["shipping_mode"],
            "lead_time": order["lead_time"],
            "defect_rate": order["avg_defect_rate"],
        },
        **risk_result,
    }

    _risk_history.append(risk_event)
    if len(_risk_history) > MAX_HISTORY:
        _risk_history.pop(0)

    # ── 2. Demand forecast on generated lag inputs ──────────────────
    demand_input = generate_demand_input()
    try:
        predicted_demand = ml_handler.predict_demand(
            lag_1=demand_input["lag_1"],
            lag_2=demand_input["lag_2"],
            lag_3=demand_input["lag_3"],
            month=demand_input["month"],
        )
    except Exception:
        predicted_demand = 0

    rolling_mean = round((demand_input["lag_1"] + demand_input["lag_2"] + demand_input["lag_3"]) / 3, 2)

    demand_event = {
        "tick": tick_label,
        "timestamp": tick_time,
        "lag_1": demand_input["lag_1"],
        "lag_2": demand_input["lag_2"],
        "lag_3": demand_input["lag_3"],
        "month": demand_input["month"],
        "predicted_demand": predicted_demand,
        "rolling_mean_3": rolling_mean,
    }

    _demand_history.append(demand_event)
    if len(_demand_history) > MAX_HISTORY:
        _demand_history.pop(0)

    # ── 3. Broadcast combined event ─────────────────────────────────
    combined = {
        "type": "pipeline_tick",
        "tick": tick_label,
        "timestamp": tick_time,
        "risk": risk_event,
        "demand": demand_event,
    }

    await _broadcast(combined)


async def _run_loop(ml_handler) -> None:
    """Infinite loop that fires _tick every TICK_INTERVAL seconds."""
    while True:
        try:
            await _tick(ml_handler)
        except Exception as e:
            print(f"[StreamEngine] tick error: {e}")
        await asyncio.sleep(TICK_INTERVAL)


def start_engine(ml_handler) -> None:
    """Start the background pipeline engine (call once at app startup)."""
    global _engine_task
    if _engine_task is not None:
        return  # Already running

    loop = asyncio.get_event_loop()
    _engine_task = loop.create_task(_run_loop(ml_handler))
    print(f"[StreamEngine] Live data injection pipeline started (interval={TICK_INTERVAL}s)")


def stop_engine() -> None:
    """Stop the background pipeline engine."""
    global _engine_task
    if _engine_task is not None:
        _engine_task.cancel()
        _engine_task = None
        print("[StreamEngine] Pipeline stopped.")
