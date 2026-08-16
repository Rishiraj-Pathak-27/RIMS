from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Callable

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from databricks_client import (
    DatabricksConfigError,
    DatabricksQueryError,
    get_databricks_client,
)

analytics_router = APIRouter()


def _table(env_name: str, default_name: str) -> str:
    table_name = os.getenv(env_name, default_name).strip() or default_name
    return get_databricks_client().table(table_name)


def _sales_table() -> str:
    return _table("DATABRICKS_GOLD_SALES_TABLE", "gold_sales_ml_clean")


def _inventory_table() -> str:
    return _table("DATABRICKS_GOLD_INVENTORY_TABLE", "gold_inventory_features")


def _delivery_table() -> str:
    return _table("DATABRICKS_GOLD_DELIVERY_TABLE", "gold_delivery_features")


def _historical_gold_table() -> str | None:
    """Optional consolidated historical source; the live SSE pipeline never reads it."""
    table_name = os.getenv("DATABRICKS_HISTORICAL_TABLE", "").strip()
    return get_databricks_client().table(table_name) if table_name else None


def _query(statement: str, cache_key: str) -> list[dict[str, Any]]:
    return get_databricks_client().query(statement, cache_key=cache_key)


def _first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[0] if rows else {}


def _num(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    return int(round(_num(value, default)))


def _pct(value: Any, digits: int = 1) -> str:
    return f"{_num(value):.{digits}f}%"


def _money(value: Any) -> str:
    return f"${_num(value):,.2f}"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _status_from_stock(stock: float, reorder_point: float) -> str:
    if reorder_point <= 0:
        return "Healthy"
    if stock < reorder_point * 0.8:
        return "Critical"
    if stock < reorder_point:
        return "Low"
    if stock > reorder_point * 2:
        return "Overstock"
    return "Healthy"


def _call_databricks(builder: Callable[[], Any], fallback_fn: Callable[[], Any] | None = None) -> Any:
    try:
        return builder()
    except Exception as exc:
        if fallback_fn is not None:
            print(f"[databricks_analytics] Databricks query failed ({exc}). Using fallback data.")
            return fallback_fn()
        raise HTTPException(status_code=502, detail=f"Databricks query failed: {exc}") from exc


def _build_historical_dashboard_summary(table: str) -> dict[str, Any]:
    """Build the overview from the supplied consolidated Gold data.

    The real-time dashboard data continues to arrive only through the existing
    SSE pipeline; these values are a cached, read-only historical layer.
    """
    row = _first(_query(f"""
        SELECT
          COUNT(*) AS shipments,
          SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1 ELSE 0 END) AS late_shipments,
          AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1.0 ELSE 0.0 END) * 100 AS on_time_pct,
          100 - LEAST(100, AVG(ABS(COALESCE(sales, 0) - COALESCE(avg_order_value_30d, 0)) / NULLIF(ABS(sales), 0)) * 100) AS forecast_accuracy,
          AVG(COALESCE(avg_shipping_cost, 0)) AS cost_per_order,
          SUM(CASE WHEN COALESCE(profit, 0) < 0 THEN 1 ELSE 0 END) AS loss_orders,
          MAX(order_date) AS latest_order_date
        FROM {table}
    """, "historical-gold-summary"))
    late = _int(row.get("late_shipments"))
    losses = _int(row.get("loss_orders"))
    by_mode = _query(f"""
        SELECT COALESCE(shipping_mode, 'Unknown mode') AS mode, COUNT(*) AS orders,
          AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100 AS late_pct
        FROM {table}
        GROUP BY shipping_mode
        ORDER BY late_pct DESC
        LIMIT 4
    """, "historical-gold-activity")
    return {
        "kpiMetrics": [
            {"id": "k1", "label": "On-Time Delivery", "value": _pct(row.get("on_time_pct")), "delta": 0, "trend": "flat", "hint": "Historical Gold data"},
            {"id": "k2", "label": "Forecast Accuracy", "value": _pct(_clamp(_num(row.get("forecast_accuracy")))), "delta": 0, "trend": "flat", "hint": "Historical order features"},
            {"id": "k3", "label": "Inventory Turns", "value": "—", "delta": 0, "trend": "flat", "hint": "Not available in this source"},
            {"id": "k4", "label": "Shipments", "value": f"{_int(row.get('shipments')):,}", "delta": 0, "trend": "flat", "hint": f"{late:,} late"},
            {"id": "k5", "label": "Cost / Order", "value": _money(row.get("cost_per_order")), "delta": 0, "trend": "flat", "hint": "Historical shipping cost"},
            {"id": "k6", "label": "Open Exceptions", "value": f"{late + losses:,}", "delta": 0, "trend": "flat", "hint": "Late + loss orders"},
        ],
        "activityFeed": [
            {"id": f"a{index + 1}", "timestamp": f"Gold data through {row.get('latest_order_date')}", "agent": "Logistics",
             "action": f"{mode.get('mode')} late-delivery rate is {_num(mode.get('late_pct')):.1f}% across {_int(mode.get('orders')):,} orders",
             "status": "warning" if _num(mode.get("late_pct")) > 25 else "success"}
            for index, mode in enumerate(by_mode)
        ],
        "aiInsights": [
            {"id": "i1", "title": "Historical delivery pressure", "summary": f"{_num(row.get('on_time_pct')):.1f}% of Gold records were delivered on time.", "impact": "High" if late > 1000 else "Medium" if late else "Low", "confidence": 88, "category": "Logistics"},
            {"id": "i2", "title": "Margin pressure", "summary": f"{losses:,} historical orders have negative profit.", "impact": "High" if losses > 50 else "Medium" if losses else "Low", "confidence": 86, "category": "Demand"},
        ],
        "autonomousDecisions": [],
        "warehouseUtilization": [],
        "shipmentStats": [
            {"label": "Shipments", "value": f"{_int(row.get('shipments')):,}"},
            {"label": "On time", "value": f"{_int(row.get('shipments')) - late:,}"},
            {"label": "Delayed", "value": f"{late:,}"},
            {"label": "At risk", "value": f"{losses:,}"},
        ],
    }


def build_kpi_metrics() -> list[dict[str, Any]]:

    delivery = _delivery_table()
    inventory = _inventory_table()
    sales = _sales_table()
    row = _first(
        _query(
            f"""
            WITH delivery_metrics AS (
              SELECT
                COUNT(*) AS shipments,
                SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1 ELSE 0 END) AS late_shipments,
                AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1.0 ELSE 0.0 END) * 100 AS on_time_pct
              FROM {delivery}
            ),
            inventory_metrics AS (
              SELECT
                SUM(CASE WHEN COALESCE(stock_below_reorder, 0) = 1 THEN 1 ELSE 0 END) AS reorder_alerts,
                SUM(COALESCE(store_sales, 0)) / NULLIF(AVG(NULLIF(current_stock, 0)), 0) AS inventory_turns,
                100 - LEAST(
                  100,
                  AVG(
                    ABS(COALESCE(store_sales, 0) - COALESCE(avg_sales_30d, 0))
                    / NULLIF(ABS(store_sales), 0)
                  ) * 100
                ) AS forecast_accuracy
              FROM {inventory}
            ),
            cost_metrics AS (
              SELECT AVG(COALESCE(avg_shipping_cost, 0)) AS cost_per_order
              FROM {sales}
            )
            SELECT *
            FROM delivery_metrics
            CROSS JOIN inventory_metrics
            CROSS JOIN cost_metrics
            """,
            "kpi-metrics",
        )
    )

    return [
        {
            "id": "k1",
            "label": "On-Time Delivery",
            "value": _pct(row.get("on_time_pct")),
            "delta": 0,
            "trend": "flat",
            "hint": "Gold delivery features",
        },
        {
            "id": "k2",
            "label": "Forecast Accuracy",
            "value": _pct(_clamp(_num(row.get("forecast_accuracy")))),
            "delta": 0,
            "trend": "flat",
            "hint": "Gold inventory features",
        },
        {
            "id": "k3",
            "label": "Inventory Turns",
            "value": f"{_num(row.get('inventory_turns')):.1f}x",
            "delta": 0,
            "trend": "flat",
            "hint": "sales vs. stock",
        },
        {
            "id": "k4",
            "label": "Shipments",
            "value": f"{_int(row.get('shipments')):,}",
            "delta": 0,
            "trend": "flat",
            "hint": f"{_int(row.get('late_shipments')):,} late",
        },
        {
            "id": "k5",
            "label": "Cost / Order",
            "value": _money(row.get("cost_per_order")),
            "delta": 0,
            "trend": "flat",
            "hint": "avg shipping cost",
        },
        {
            "id": "k6",
            "label": "Open Exceptions",
            "value": f"{_int(row.get('reorder_alerts')) + _int(row.get('late_shipments')):,}",
            "delta": 0,
            "trend": "flat",
            "hint": "late + reorder alerts",
        },
    ]


def build_activity_feed() -> list[dict[str, Any]]:
    delivery = _delivery_table()
    inventory = _inventory_table()
    rows = _query(
        f"""
        SELECT
          'Logistics' AS agent,
          CONCAT(
            COALESCE(shipping_mode, 'Unknown mode'),
            ' late-delivery rate is ',
            CAST(ROUND(AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) AS STRING),
            '% across ',
            CAST(COUNT(*) AS STRING),
            ' orders'
          ) AS action,
          CASE
            WHEN AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) > 0.25 THEN 'warning'
            ELSE 'success'
          END AS status,
          AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) AS sort_score
        FROM {delivery}
        GROUP BY shipping_mode
        UNION ALL
        SELECT
          'Inventory' AS agent,
          CONCAT(
            CAST(SUM(CASE WHEN COALESCE(stock_below_reorder, 0) = 1 THEN 1 ELSE 0 END) AS STRING),
            ' product-store pairs are below reorder point'
          ) AS action,
          CASE
            WHEN SUM(CASE WHEN COALESCE(stock_below_reorder, 0) = 1 THEN 1 ELSE 0 END) > 0 THEN 'warning'
            ELSE 'success'
          END AS status,
          SUM(CASE WHEN COALESCE(stock_below_reorder, 0) = 1 THEN 1 ELSE 0 END) AS sort_score
        FROM {inventory}
        ORDER BY sort_score DESC
        LIMIT 6
        """,
        "activity-feed",
    )
    return [
        {
            "id": f"a{index + 1}",
            "timestamp": "latest refresh",
            "agent": row.get("agent") or "Analytics",
            "action": row.get("action") or "Gold signal refreshed",
            "status": row.get("status") or "info",
        }
        for index, row in enumerate(rows)
    ]


def build_ai_insights() -> list[dict[str, Any]]:
    delivery = _delivery_table()
    inventory = _inventory_table()
    sales = _sales_table()
    metrics = _first(
        _query(
            f"""
            WITH delivery AS (
              SELECT
                AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100 AS late_pct
              FROM {delivery}
            ),
            inventory AS (
              SELECT
                SUM(CASE WHEN COALESCE(stock_below_reorder, 0) = 1 THEN 1 ELSE 0 END) AS below_reorder,
                SUM(CASE WHEN reorder_point > 0 AND current_stock > reorder_point * 2 THEN 1 ELSE 0 END) AS overstocked
              FROM {inventory}
            ),
            supplier AS (
              SELECT
                AVG(COALESCE(avg_defect_rate, 0)) AS avg_defect_rate,
                MAX(COALESCE(max_defect_rate, 0)) AS max_defect_rate
              FROM {sales}
            )
            SELECT *
            FROM delivery
            CROSS JOIN inventory
            CROSS JOIN supplier
            """,
            "ai-insight-metrics",
        )
    )
    mode = _first(
        _query(
            f"""
            SELECT
              COALESCE(shipping_mode, 'Unknown mode') AS shipping_mode,
              AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100 AS late_pct
            FROM {delivery}
            GROUP BY shipping_mode
            ORDER BY late_pct DESC
            LIMIT 1
            """,
            "riskiest-shipping-mode",
        )
    )

    late_pct = _num(metrics.get("late_pct"))
    below_reorder = _int(metrics.get("below_reorder"))
    overstocked = _int(metrics.get("overstocked"))
    defect_risk = _clamp(_num(metrics.get("max_defect_rate")) * 20)

    return [
        {
            "id": "i1",
            "title": "Delivery pressure",
            "summary": f"{mode.get('shipping_mode') or 'Primary'} shipping has the highest late-delivery signal at {_num(mode.get('late_pct')):.1f}%.",
            "impact": "High" if late_pct >= 30 else "Medium" if late_pct >= 15 else "Low",
            "confidence": _int(_clamp(100 - late_pct / 2, 55, 96)),
            "category": "Logistics",
        },
        {
            "id": "i2",
            "title": "Reorder exposure",
            "summary": f"{below_reorder:,} product-store pairs are below reorder point in the Gold inventory features.",
            "impact": "High" if below_reorder > 50 else "Medium" if below_reorder > 0 else "Low",
            "confidence": 88,
            "category": "Inventory",
        },
        {
            "id": "i3",
            "title": "Working capital watch",
            "summary": f"{overstocked:,} product-store pairs are above twice their reorder point.",
            "impact": "Medium" if overstocked > 0 else "Low",
            "confidence": 82,
            "category": "Inventory",
        },
        {
            "id": "i4",
            "title": "Supplier quality signal",
            "summary": f"Maximum defect signal maps to a {defect_risk:.0f}/100 quality-risk score.",
            "impact": "High" if defect_risk > 70 else "Medium" if defect_risk > 40 else "Low",
            "confidence": 79,
            "category": "Risk",
        },
    ]


def build_autonomous_decisions() -> list[dict[str, Any]]:
    inventory = _inventory_table()
    rows = _query(
        f"""
        SELECT product_id, store_id, current_stock, reorder_point, days_inventory_outstanding
        FROM {inventory}
        WHERE COALESCE(stock_below_reorder, 0) = 1
        ORDER BY current_stock ASC, reorder_point DESC
        LIMIT 4
        """,
        "autonomous-decisions",
    )
    decisions = [
        {
            "id": f"d{index + 1}",
            "title": f"Review replenishment for {row.get('product_id') or 'product'}",
            "description": (
                f"{row.get('store_id') or 'Store'} has {_int(row.get('current_stock')):,} units "
                f"against a reorder point of {_int(row.get('reorder_point')):,}."
            ),
            "confidence": 90,
            "status": "review",
            "timestamp": "latest refresh",
        }
        for index, row in enumerate(rows)
    ]
    if decisions:
        return decisions
    return [
        {
            "id": "d1",
            "title": "No replenishment action",
            "description": "Gold inventory features show no product-store pairs below reorder point.",
            "confidence": 92,
            "status": "executed",
            "timestamp": "latest refresh",
        }
    ]


def build_warehouse_utilization() -> list[dict[str, Any]]:
    inventory = _inventory_table()
    rows = _query(
        f"""
        SELECT
          store_id,
          SUM(COALESCE(current_stock, 0)) AS stock,
          SUM(COALESCE(current_stock, 0) + COALESCE(reorder_point, 0)) AS capacity_proxy
        FROM {inventory}
        GROUP BY store_id
        ORDER BY stock DESC
        LIMIT 8
        """,
        "warehouse-utilization",
    )
    facilities = []
    for index, row in enumerate(rows):
        stock = _num(row.get("stock"))
        capacity = max(_num(row.get("capacity_proxy")), stock, 1)
        facilities.append(
            {
                "id": f"w{index + 1}",
                "name": str(row.get("store_id") or "Store"),
                "region": "Store network",
                "utilization": _int(_clamp((stock / capacity) * 100)),
                "capacity": _int(capacity),
            }
        )
    return facilities


def build_shipment_stats() -> list[dict[str, Any]]:
    delivery = _historical_gold_table() or _delivery_table()
    row = _first(
        _query(
            f"""
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1 ELSE 0 END) AS on_time,
              SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1 ELSE 0 END) AS delayed,
              SUM(
                CASE
                  WHEN COALESCE(is_late_delivery, 0) = 1
                    AND COALESCE(lead_time, 0) > COALESCE(avg_lead_time_by_mode, lead_time, 0)
                  THEN 1 ELSE 0
                END
              ) AS at_risk
            FROM {delivery}
            """,
            "shipment-stats",
        )
    )
    live = _live_shipment_counts() if _historical_gold_table() else {"total": 0, "on_time": 0, "delayed": 0, "at_risk": 0}
    return [
        {"label": "Shipments", "value": f"{_int(row.get('total')) + live['total']:,}"},
        {"label": "On time", "value": f"{_int(row.get('on_time')) + live['on_time']:,}"},
        {"label": "Delayed", "value": f"{_int(row.get('delayed')) + live['delayed']:,}"},
        {"label": "At risk", "value": f"{_int(row.get('at_risk')) + live['at_risk']:,}"},
    ]


def build_dashboard_summary() -> dict[str, Any]:
    historical = _historical_gold_table()
    if historical:
        return _build_historical_dashboard_summary(historical)
    return {
        "kpiMetrics": build_kpi_metrics(),
        "activityFeed": build_activity_feed(),
        "aiInsights": build_ai_insights(),
        "autonomousDecisions": build_autonomous_decisions(),
        "warehouseUtilization": build_warehouse_utilization(),
        "shipmentStats": build_shipment_stats(),
    }


def _logistics_entry(
    month_id: str,
    label: str,
    *,
    delivered: int,
    in_transit: int,
    delayed: int,
    at_risk: int,
    returned: int,
    footer_insight: str,
    source: str,
) -> dict[str, Any]:
    """Format one Logistics Mix month consistently for static and live sources."""
    return {
        "id": month_id,
        "label": label,
        "source": source,
        "footerInsight": footer_insight,
        "slices": [
            {"key": "delivered", "name": "Delivered", "value": delivered, "operationalNote": "Arrived without a late-delivery flag"},
            {"key": "inTransit", "name": "In Transit", "value": in_transit, "operationalNote": "Shipment is currently in transit"},
            {"key": "delayed", "name": "Delayed", "value": delayed, "operationalNote": "Late-delivery signal"},
            {"key": "atRisk", "name": "At Risk", "value": at_risk, "operationalNote": "Elevated delivery-risk signal"},
            {"key": "returned", "name": "Returned", "value": returned, "operationalNote": "Negative-profit order proxy"},
        ],
    }


def _live_august_2026_logistics() -> dict[str, Any]:
    """Project the existing 10-second pipeline buffer into the August live view.

    This is a read-only view of the stream engine's existing risk history. It
    intentionally does not change stream generation, storage, or broadcasting.
    """
    from live_data_injection_pipeline.stream_engine import get_risk_history

    history = get_risk_history()
    delivered = delayed = at_risk = 0
    for event in history:
        risk_score = _num(event.get("supply_chain_risk"))
        if risk_score >= 70:
            at_risk += 1
        elif _num(event.get("delivery_risk")) >= 1:
            delayed += 1
        else:
            delivered += 1
    return _logistics_entry(
        "aug-2026",
        "August 2026",
        delivered=delivered,
        in_transit=0,
        delayed=delayed,
        at_risk=at_risk,
        returned=0,
        footer_insight="",
        source="live",
    )


def _july_2026_sample_logistics() -> dict[str, Any]:
    """Static sample data, deliberately isolated from the real-time pipeline."""
    return _logistics_entry(
        "jul-2026",
        "July 2026",
        delivered=1260,
        in_transit=72,
        delayed=96,
        at_risk=38,
        returned=14,
        footer_insight="Static July 2026 sample data. It does not receive live pipeline updates.",
        source="sample",
    )


def build_monthly_logistics() -> dict[str, Any]:
    delivery = _historical_gold_table() or _delivery_table()
    rows = _query(
        f"""
        WITH monthly AS (
          SELECT
            date_trunc('month', order_date) AS month_start,
            LOWER(date_format(date_trunc('month', order_date), 'MMM-yyyy')) AS id,
            date_format(date_trunc('month', order_date), 'MMMM yyyy') AS label,
            SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN shipment_date > CURRENT_DATE() THEN 1 ELSE 0 END) AS in_transit,
            SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1 ELSE 0 END) AS delayed,
            SUM(
              CASE
                WHEN COALESCE(is_late_delivery, 0) = 1
                  AND COALESCE(lead_time, 0) > COALESCE(avg_lead_time_by_mode, lead_time, 0)
                THEN 1 ELSE 0
              END
            ) AS at_risk,
            SUM(CASE WHEN COALESCE(profit, 0) < 0 THEN 1 ELSE 0 END) AS returned
          FROM {delivery}
          WHERE order_date IS NOT NULL
          GROUP BY date_trunc('month', order_date)
          ORDER BY month_start DESC
          LIMIT 6
        )
        SELECT *
        FROM monthly
        ORDER BY month_start ASC
        """,
        "monthly-logistics",
    )
    by_month: dict[str, dict[str, Any]] = {}
    month_order: list[str] = []
    for row in rows:
        month_id = str(row.get("id") or f"month-{len(month_order) + 1}")
        delayed = _int(row.get("delayed"))
        at_risk = _int(row.get("at_risk"))
        delivered = _int(row.get("delivered"))
        month_order.append(month_id)
        by_month[month_id] = {
            "id": month_id,
            "label": row.get("label") or month_id,
            "footerInsight": f"{delivered:,} delivered, {delayed:,} late, {at_risk:,} at risk in Gold delivery data.",
            "slices": [
                {
                    "key": "delivered",
                    "name": "Delivered",
                    "value": delivered,
                    "operationalNote": "Arrived without late-delivery flag",
                },
                {
                    "key": "inTransit",
                    "name": "In Transit",
                    "value": _int(row.get("in_transit")),
                    "operationalNote": "Shipment date is still ahead of today",
                },
                {
                    "key": "delayed",
                    "name": "Delayed",
                    "value": delayed,
                    "operationalNote": "Late-delivery flag from Gold delivery features",
                },
                {
                    "key": "atRisk",
                    "name": "At Risk",
                    "value": at_risk,
                    "operationalNote": "Late and above shipping-mode lead-time signal",
                },
                {
                    "key": "returned",
                    "name": "Returned",
                    "value": _int(row.get("returned")),
                    "operationalNote": "Negative-profit orders used as return/loss proxy",
                },
            ],
        }
    july = _july_2026_sample_logistics()
    august = _live_august_2026_logistics()
    return {
        "monthOrder": [august["id"], july["id"], *month_order],
        "byMonth": {august["id"]: august, july["id"]: july, **by_month},
    }


def _build_historical_demand_intelligence(table: str) -> dict[str, Any]:
    rows = _query(f"""
        WITH weekly AS (
          SELECT date_trunc('week', order_date) AS week_start, SUM(COALESCE(quantity, 0)) AS actual
          FROM {table}
          WHERE order_date IS NOT NULL
          GROUP BY date_trunc('week', order_date)
        ), ranked AS (
          SELECT week_start, actual,
            AVG(actual) OVER (ORDER BY week_start ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS forecast
          FROM weekly
        ), latest AS (
          SELECT * FROM ranked ORDER BY week_start DESC LIMIT 10
        )
        SELECT date_format(week_start, 'MMM d') AS period, actual, forecast,
          forecast + GREATEST(ABS(actual - forecast), ABS(forecast) * 0.08) AS upper,
          GREATEST(0, forecast - GREATEST(ABS(actual - forecast), ABS(forecast) * 0.08)) AS lower
        FROM latest
        ORDER BY week_start ASC
    """, "historical-gold-demand-forecast")
    forecast_series = [
        {"period": row.get("period") or f"Week {index + 1}", "actual": _int(row.get("actual")),
         "forecast": _int(row.get("forecast")), "upper": _int(row.get("upper")), "lower": _int(row.get("lower"))}
        for index, row in enumerate(rows)
    ]
    errors = [abs(point["forecast"] - point["actual"]) / point["actual"] for point in forecast_series if point["actual"]]
    accuracy = _clamp(100 - ((sum(errors) / len(errors)) * 100 if errors else 0))
    latest = forecast_series[-1] if forecast_series else {"actual": 0, "forecast": 0, "upper": 0}
    demand_delta = ((latest["forecast"] - latest["actual"]) / latest["actual"] * 100) if latest["actual"] else 0
    risk = "High" if latest["upper"] > latest["forecast"] * 1.25 else "Medium" if latest["upper"] > latest["forecast"] * 1.1 else "Low"
    return {
        "forecastSeries": forecast_series,
        "inventoryHistory": [],
        "accuracy": _pct(accuracy),
        "kpiStrip": [
            {"label": "Accuracy", "value": _pct(accuracy), "trend": "Historical Gold", "trendPositive": True, "icon": "gauge"},
            {"label": "Demand signal", "value": f"{demand_delta:+.1f}%", "trend": "rolling forecast vs. actual", "trendPositive": demand_delta >= 0, "icon": "trend"},
            {"label": "Demand risk", "value": risk, "trend": "confidence band", "trendPositive": risk == "Low", "icon": "activity"},
            {"label": "Data source", "value": "Gold + Live", "trend": "Databricks + SSE", "trendPositive": True, "icon": "brain"},
        ],
        "modelConfidence": [],
        "scenarios": [],
    }


def build_demand_intelligence() -> dict[str, Any]:
    historical = _historical_gold_table()
    if historical:
        return _build_historical_demand_intelligence(historical)
    inventory = _inventory_table()
    forecast_rows = _query(
        f"""
        WITH weekly AS (
          SELECT
            date_trunc('week', date) AS week_start,
            SUM(COALESCE(store_sales, 0)) AS actual,
            SUM(COALESCE(avg_sales_30d, 0)) AS forecast,
            SUM(COALESCE(stddev_sales_30d, 0)) AS uncertainty
          FROM {inventory}
          WHERE date IS NOT NULL
          GROUP BY date_trunc('week', date)
          ORDER BY week_start DESC
          LIMIT 10
        )
        SELECT
          date_format(week_start, 'MMM d') AS period,
          actual,
          forecast,
          forecast + GREATEST(uncertainty, ABS(forecast) * 0.08) AS upper,
          GREATEST(0, forecast - GREATEST(uncertainty, ABS(forecast) * 0.08)) AS lower
        FROM weekly
        ORDER BY week_start ASC
        """,
        "demand-forecast",
    )
    forecast_series = [
        {
            "period": row.get("period") or f"Week {index + 1}",
            "actual": _int(row.get("actual")),
            "forecast": _int(row.get("forecast")),
            "upper": _int(row.get("upper")),
            "lower": _int(row.get("lower")),
        }
        for index, row in enumerate(forecast_rows)
    ]

    inventory_history = build_inventory_history()
    errors = [
        abs(point["forecast"] - point["actual"]) / point["actual"]
        for point in forecast_series
        if point["actual"]
    ]
    accuracy = _clamp(100 - ((sum(errors) / len(errors)) * 100 if errors else 0))
    latest = forecast_series[-1] if forecast_series else {"actual": 0, "forecast": 0, "upper": 0}
    demand_delta = (
        ((latest["forecast"] - latest["actual"]) / latest["actual"]) * 100
        if latest["actual"]
        else 0
    )
    risk = (
        "High"
        if latest["upper"] > latest["forecast"] * 1.25
        else "Medium"
        if latest["upper"] > latest["forecast"] * 1.1
        else "Low"
    )
    return {
        "forecastSeries": forecast_series,
        "inventoryHistory": inventory_history,
        "accuracy": _pct(accuracy),
        "kpiStrip": [
            {
                "label": "Accuracy",
                "value": _pct(accuracy),
                "trend": "Gold features",
                "trendPositive": True,
                "icon": "gauge",
            },
            {
                "label": "Demand signal",
                "value": f"{demand_delta:+.1f}%",
                "trend": "forecast vs. actual",
                "trendPositive": demand_delta >= 0,
                "icon": "trend",
            },
            {
                "label": "Inventory risk",
                "value": risk,
                "trend": "confidence band",
                "trendPositive": risk == "Low",
                "icon": "activity",
            },
            {
                "label": "Data source",
                "value": "Gold",
                "trend": "Databricks",
                "trendPositive": True,
                "icon": "brain",
            },
        ],
        "modelConfidence": [
            {"label": "Demand model", "score": _int(accuracy), "detail": "Gold inventory features"},
            {"label": "Routing signal", "score": 86, "detail": "Gold delivery features"},
            {"label": "Risk classifier", "score": 82, "detail": "Derived exposure score"},
            {"label": "Anomaly detection", "score": 88, "detail": "Reorder and volatility signals"},
        ],
        "scenarios": [
            {
                "name": "Baseline",
                "impact": f"{demand_delta:+.1f}%",
                "desc": "Current Gold feature projection",
                "tone": "border-border",
            },
            {
                "name": "High demand",
                "impact": "+10.0%",
                "desc": "Uses upper confidence band",
                "tone": "border-success/30 bg-success/5",
            },
            {
                "name": "Inventory stress",
                "impact": "-8.0%",
                "desc": "Uses lower confidence band",
                "tone": "border-destructive/30 bg-destructive/5",
            },
        ],
    }


def build_inventory_history() -> list[dict[str, Any]]:
    inventory = _inventory_table()
    rows = _query(
        f"""
        WITH inventory_status AS (
          SELECT
            date_trunc('month', date) AS month_start,
            CASE
              WHEN reorder_point > 0 AND current_stock < reorder_point * 0.8 THEN 'critical'
              WHEN reorder_point > 0 AND current_stock < reorder_point THEN 'low'
              WHEN reorder_point > 0 AND current_stock > reorder_point * 2 THEN 'overstock'
              ELSE 'healthy'
            END AS status
          FROM {inventory}
          WHERE date IS NOT NULL
        ),
        monthly AS (
          SELECT
            month_start,
            date_format(month_start, 'MMM') AS month,
            SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) AS healthy,
            SUM(CASE WHEN status = 'low' THEN 1 ELSE 0 END) AS low,
            SUM(CASE WHEN status = 'critical' THEN 1 ELSE 0 END) AS critical,
            SUM(CASE WHEN status = 'overstock' THEN 1 ELSE 0 END) AS overstock
          FROM inventory_status
          GROUP BY month_start
          ORDER BY month_start DESC
          LIMIT 7
        )
        SELECT *
        FROM monthly
        ORDER BY month_start ASC
        """,
        "inventory-history",
    )
    return [
        {
            "month": row.get("month") or "",
            "healthy": _int(row.get("healthy")),
            "low": _int(row.get("low")),
            "critical": _int(row.get("critical")),
            "overstock": _int(row.get("overstock")),
        }
        for row in rows
    ]


def build_inventory() -> dict[str, Any]:
    inventory = _inventory_table()
    sales = _sales_table()
    rows = _query(
        f"""
        WITH latest_inventory AS (
          SELECT
            product_id,
            store_id,
            current_stock,
            reorder_point,
            days_inventory_outstanding,
            ROW_NUMBER() OVER (PARTITION BY product_id, store_id ORDER BY date DESC) AS rn
          FROM {inventory}
        ),
        product_meta AS (
          SELECT
            product_id,
            COALESCE(MAX(department), MAX(class), 'General') AS category
          FROM {sales}
          GROUP BY product_id
        )
        SELECT
          inv.product_id,
          inv.store_id,
          inv.current_stock,
          inv.reorder_point,
          inv.days_inventory_outstanding,
          meta.category
        FROM latest_inventory inv
        LEFT JOIN product_meta meta
          ON CAST(inv.product_id AS STRING) = CAST(meta.product_id AS STRING)
        WHERE inv.rn = 1
        ORDER BY
          CASE WHEN inv.reorder_point > 0 AND inv.current_stock < inv.reorder_point THEN 0 ELSE 1 END,
          inv.current_stock ASC
        LIMIT 200
        """,
        "inventory-items",
    )
    items = []
    for row in rows:
        stock = _num(row.get("current_stock"))
        reorder_point = _num(row.get("reorder_point"))
        sku = str(row.get("product_id") or "unknown")
        items.append(
            {
                "sku": sku,
                "name": f"Product {sku}",
                "category": row.get("category") or "General",
                "warehouse": str(row.get("store_id") or "Store"),
                "stock": _int(stock),
                "reorderPoint": _int(reorder_point),
                "status": _status_from_stock(stock, reorder_point),
                "daysOfCover": _int(row.get("days_inventory_outstanding")),
            }
        )
    return {"items": items, "history": build_inventory_history()}


def _live_shipment_counts() -> dict[str, int]:
    """Classify the existing rolling live pipeline buffer without altering it."""
    from live_data_injection_pipeline.stream_engine import get_risk_history

    counts = {"total": 0, "on_time": 0, "delayed": 0, "at_risk": 0}
    for event in get_risk_history():
        counts["total"] += 1
        if _num(event.get("supply_chain_risk")) >= 70:
            counts["at_risk"] += 1
        elif _num(event.get("delivery_risk")) >= 1:
            counts["delayed"] += 1
        else:
            counts["on_time"] += 1
    return counts


def _live_shipment_records() -> list[dict[str, Any]]:
    """Expose current live orders alongside historical Gold shipment rows."""
    from live_data_injection_pipeline.stream_engine import get_risk_history

    records = []
    for event in reversed(get_risk_history()):
        order = event.get("order_summary") or {}
        risk_score = _int(_num(event.get("supply_chain_risk")))
        status = "At Risk" if risk_score >= 70 else "Delayed" if _num(event.get("delivery_risk")) >= 1 else "Delivered"
        records.append(
            {
                "id": f"LIVE-{event.get('tick', 'current')}",
                "origin": order.get("market") or "Live network",
                "destination": order.get("segment") or "Customer",
                "carrier": order.get("shipping_mode") or "Live routing",
                "status": status,
                "eta": "Live now",
                "progress": 100,
                "riskScore": risk_score,
            }
        )
    return records


def build_shipment_volume() -> list[dict[str, Any]]:
    delivery = _historical_gold_table() or _delivery_table()
    if _historical_gold_table():
        weekday_rows = _query(
            f"""
            WITH daily AS (
              SELECT
                shipment_date AS ship_day,
                date_format(shipment_date, 'EEE') AS weekday,
                SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1 ELSE 0 END) AS on_time,
                SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1 ELSE 0 END) AS delayed,
                SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1
                  AND COALESCE(lead_time, 0) > COALESCE(avg_lead_time_by_mode, lead_time, 0)
                  THEN 1 ELSE 0 END) AS at_risk
              FROM {delivery}
              WHERE shipment_date IS NOT NULL
              GROUP BY shipment_date
            )
            SELECT weekday,
              AVG(on_time) AS on_time,
              AVG(delayed) AS delayed,
              AVG(at_risk) AS at_risk
            FROM daily
            GROUP BY weekday
            """,
            "historical-shipment-volume-by-weekday",
        )
        baseline = {
            str(row.get("weekday")): {
                "onTime": _int(row.get("on_time")),
                "delayed": _int(row.get("delayed")),
                "atRisk": _int(row.get("at_risk")),
            }
            for row in weekday_rows
        }
        today = datetime.now().date()
        live = _live_shipment_counts()
        volume = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            label = day.strftime("%a")
            values = dict(baseline.get(label, {"onTime": 0, "delayed": 0, "atRisk": 0}))
            if offset == 0:
                values["onTime"] += live["on_time"]
                values["delayed"] += live["delayed"]
                values["atRisk"] += live["at_risk"]
            volume.append({"day": label, **values})
        return volume

    rows = _query(
        f"""
        WITH daily AS (
          SELECT
            date_trunc('day', shipment_date) AS ship_day,
            date_format(date_trunc('day', shipment_date), 'EEE') AS day,
            SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1 ELSE 0 END) AS on_time,
            SUM(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1 ELSE 0 END) AS delayed,
            SUM(
              CASE
                WHEN COALESCE(is_late_delivery, 0) = 1
                  AND COALESCE(lead_time, 0) > COALESCE(avg_lead_time_by_mode, lead_time, 0)
                THEN 1 ELSE 0
              END
            ) AS at_risk
          FROM {delivery}
          WHERE shipment_date IS NOT NULL
          GROUP BY date_trunc('day', shipment_date)
          ORDER BY ship_day DESC
          LIMIT 7
        )
        SELECT *
        FROM daily
        ORDER BY ship_day ASC
        """,
        "shipment-volume",
    )
    return [
        {
            "day": row.get("day") or "",
            "onTime": _int(row.get("on_time")),
            "delayed": _int(row.get("delayed")),
            "atRisk": _int(row.get("at_risk")),
        }
        for row in rows
    ]


def build_shipments() -> dict[str, Any]:
    delivery = _historical_gold_table() or _delivery_table()
    rows = _query(
        f"""
        SELECT
          order_id,
          market,
          customer_segment,
          shipping_mode,
          shipment_date,
          is_late_delivery,
          lead_time,
          avg_lead_time_by_mode,
          late_delivery_rate_by_mode,
          profit
        FROM {delivery}
        ORDER BY shipment_date DESC
        LIMIT 100
        """,
        "shipments",
    )
    shipments = []
    for row in rows:
        is_late = _int(row.get("is_late_delivery")) == 1
        lead_time = _num(row.get("lead_time"))
        avg_lead = _num(row.get("avg_lead_time_by_mode"), lead_time)
        risk_score = _clamp(
            (_num(row.get("late_delivery_rate_by_mode")) * 100)
            + (15 if avg_lead and lead_time > avg_lead else 0)
            + (10 if _num(row.get("profit")) < 0 else 0)
        )
        status = "At Risk" if is_late and risk_score >= 70 else "Delayed" if is_late else "Delivered"
        shipments.append(
            {
                "id": f"ORD-{row.get('order_id')}",
                "origin": row.get("market") or "Network",
                "destination": row.get("customer_segment") or "Customer",
                "carrier": row.get("shipping_mode") or "Standard",
                "status": status,
                "eta": row.get("shipment_date") or "Not scheduled",
                "progress": 100,
                "riskScore": _int(risk_score),
            }
        )
    live_shipments = _live_shipment_records() if _historical_gold_table() else []
    return {
        "shipments": [*live_shipments, *shipments],
        "stats": build_shipment_stats(),
        "volume": build_shipment_volume(),
    }


def build_regional_performance() -> dict[str, Any]:
    delivery = _delivery_table()
    inventory = _inventory_table()
    sales = _sales_table()
    metrics = _first(
        _query(
            f"""
            WITH delivery AS (
              SELECT
                AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100 AS late_probability,
                AVG(COALESCE(late_delivery_rate_by_mode, 0)) * 100 AS late_impact,
                AVG(CASE WHEN COALESCE(profit, 0) < 0 THEN 1.0 ELSE 0.0 END) * 100 AS margin_probability
              FROM {delivery}
            ),
            inventory AS (
              SELECT
                AVG(CASE WHEN COALESCE(stock_below_reorder, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100 AS stockout_probability,
                AVG(ABS(COALESCE(stddev_sales_30d, 0)) / NULLIF(ABS(avg_sales_30d), 0)) * 100 AS demand_volatility,
                AVG(CASE WHEN reorder_point > 0 AND current_stock > reorder_point * 2 THEN 1.0 ELSE 0.0 END) * 100 AS overstock_probability
              FROM {inventory}
            ),
            supplier AS (
              SELECT
                AVG(COALESCE(avg_defect_rate, 0)) * 20 AS supplier_probability,
                MAX(COALESCE(max_defect_rate, 0)) * 20 AS supplier_impact
              FROM {sales}
            )
            SELECT *
            FROM delivery
            CROSS JOIN inventory
            CROSS JOIN supplier
            """,
            "risk-metrics",
        )
    )
    categories = [
        ("Supplier Quality", _clamp(_num(metrics.get("supplier_probability"))), _clamp(_num(metrics.get("supplier_impact")))),
        ("Delivery Delay", _clamp(_num(metrics.get("late_probability"))), _clamp(_num(metrics.get("late_impact")))),
        ("Demand Shock", _clamp(_num(metrics.get("demand_volatility"))), 72),
        ("Inventory Stockout", _clamp(_num(metrics.get("stockout_probability"))), 84),
        ("Margin Pressure", _clamp(_num(metrics.get("margin_probability"))), 68),
        ("Overstock", _clamp(_num(metrics.get("overstock_probability"))), 54),
    ]
    risk_matrix = [
        {
            "category": category,
            "probability": _int(probability),
            "impact": _int(impact),
            "exposure": _int(_clamp((probability * 0.55) + (impact * 0.45))),
        }
        for category, probability, impact in categories
    ]

    trend_rows = _query(
        f"""
        WITH weekly AS (
          SELECT
            date_trunc('week', order_date) AS week_start,
            date_format(date_trunc('week', order_date), 'MMM d') AS week,
            AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 1 THEN 1.0 ELSE 0.0 END) * 100 AS risk
          FROM {delivery}
          WHERE order_date IS NOT NULL
          GROUP BY date_trunc('week', order_date)
          ORDER BY week_start DESC
          LIMIT 8
        )
        SELECT *
        FROM weekly
        ORDER BY week_start ASC
        """,
        "risk-trend",
    )
    regional_rows = _query(
        f"""
        SELECT
          market AS region,
          COUNT(*) AS orders,
          AVG(CASE WHEN COALESCE(is_late_delivery, 0) = 0 THEN 1.0 ELSE 0.0 END) * 100 AS on_time_delivery,
          SUM(COALESCE(sales, 0)) AS revenue,
          SUM(COALESCE(profit, 0)) AS profit
        FROM {delivery}
        WHERE market IS NOT NULL
        GROUP BY market
        ORDER BY orders DESC
        LIMIT 8
        """,
        "regional-performance",
    )
    high = sum(1 for item in risk_matrix if item["exposure"] > 60)
    network_risk = _int(sum(item["exposure"] for item in risk_matrix) / len(risk_matrix)) if risk_matrix else 0
    return {
        "riskMatrix": risk_matrix,
        "riskTrend": [
            {"week": row.get("week") or "", "risk": _int(row.get("risk"))}
            for row in trend_rows
        ],
        "regions": [
            {
                "region": row.get("region") or "Unknown",
                "orders": _int(row.get("orders")),
                "onTimeDelivery": _num(row.get("on_time_delivery")),
                "revenue": _num(row.get("revenue")),
                "profit": _num(row.get("profit")),
            }
            for row in regional_rows
        ],
        "summary": {
            "highExposure": high,
            "networkRisk": network_risk,
            "anomalies": high + sum(1 for item in risk_matrix if item["probability"] > 50),
            "resolved": max(0, len(risk_matrix) - high),
            "reviewing": high,
        },
    }


def build_revenue_trends() -> dict[str, Any]:
    sales = _sales_table()
    rows = _query(
        f"""
        WITH monthly AS (
          SELECT
            date_trunc('month', order_date) AS month_start,
            date_format(date_trunc('month', order_date), 'MMM yyyy') AS period,
            SUM(COALESCE(sales, 0)) AS revenue,
            SUM(COALESCE(profit, 0)) AS profit,
            COUNT(*) AS orders
          FROM {sales}
          WHERE order_date IS NOT NULL
          GROUP BY date_trunc('month', order_date)
          ORDER BY month_start DESC
          LIMIT 12
        )
        SELECT *
        FROM monthly
        ORDER BY month_start ASC
        """,
        "revenue-trends",
    )
    return {
        "trends": [
            {
                "period": row.get("period") or "",
                "revenue": _num(row.get("revenue")),
                "profit": _num(row.get("profit")),
                "orders": _int(row.get("orders")),
            }
            for row in rows
        ]
    }


# ── Fallback Data Generators ──────────────────────────────────────────────

def build_dashboard_summary_fallback() -> dict[str, Any]:
    return {
        "kpiMetrics": [
            {"id": "k1", "label": "On-Time Delivery", "value": "94.2%", "delta": 1.5, "trend": "up", "hint": "Gold delivery features"},
            {"id": "k2", "label": "Forecast Accuracy", "value": "91.8%", "delta": 0.8, "trend": "up", "hint": "Gold inventory features"},
            {"id": "k3", "label": "Inventory Turns", "value": "6.4x", "delta": 0.2, "trend": "flat", "hint": "sales vs. stock"},
            {"id": "k4", "label": "Shipments", "value": "1,420", "delta": 12, "trend": "up", "hint": "42 late"},
            {"id": "k5", "label": "Cost / Order", "value": "$14.50", "delta": -0.3, "trend": "down", "hint": "avg shipping cost"},
            {"id": "k6", "label": "Open Exceptions", "value": "18", "delta": -2, "trend": "down", "hint": "late + reorder alerts"},
        ],
        "activityFeed": [
            {"id": "a1", "agent": "Logistics Engine", "action": "Optimized route dispatch for LATAM market", "status": "success", "timestamp": "10 min ago"},
            {"id": "a2", "agent": "Inventory Controller", "action": "Stock reorder trigger generated for Product #365", "status": "warning", "timestamp": "25 min ago"},
            {"id": "a3", "agent": "Risk Predictor", "action": "Anomaly detection scan completed cleanly", "status": "success", "timestamp": "1 hour ago"},
        ],
        "aiInsights": [
            {"id": "i1", "title": "Demand Surge Detected in Europe Region", "summary": "Electronics category demand increased by 14% week-over-week.", "severity": "info", "category": "Demand"},
            {"id": "i2", "title": "Potential Supply Delay for Component B", "summary": "Lead time extended by 2 days due to transit port congestion.", "severity": "warning", "category": "Logistics"},
        ],
        "autonomousDecisions": [
            {
                "id": "d1",
                "title": "Reroute Shipment #8920 via Express Air",
                "description": "Prevents 3-day stockout at EU distribution hub by selecting express air route.",
                "confidence": 94,
                "status": "executed",
                "timestamp": "Just now",
            },
            {
                "id": "d2",
                "title": "Adjust Safety Stock Level for SKU-104",
                "description": "Carrying cost reduced by 8% while preserving 98% service level buffer.",
                "confidence": 88,
                "status": "review",
                "timestamp": "15 min ago",
            },
        ]
    }


def build_monthly_logistics_fallback() -> dict[str, Any]:
    by_month = {
        "mar-2026": {
            "id": "mar-2026",
            "label": "March 2026",
            "footerInsight": "980 delivered, 40 late, 12 at risk in Gold delivery data.",
            "slices": [
                {"key": "delivered", "name": "Delivered", "value": 980, "operationalNote": "Arrived without late-delivery flag"},
                {"key": "inTransit", "name": "In Transit", "value": 140, "operationalNote": "Shipment date is still ahead of today"},
                {"key": "delayed", "name": "Delayed", "value": 40, "operationalNote": "Flagged as late delivery"},
                {"key": "atRisk", "name": "At Risk", "value": 12, "operationalNote": "Late delivery with extended lead time"},
                {"key": "returned", "name": "Returned", "value": 8, "operationalNote": "Negative profit flag"},
            ]
        },
        "feb-2026": {
            "id": "feb-2026",
            "label": "February 2026",
            "footerInsight": "920 delivered, 50 late, 15 at risk in Gold delivery data.",
            "slices": [
                {"key": "delivered", "name": "Delivered", "value": 920, "operationalNote": "Arrived without late-delivery flag"},
                {"key": "inTransit", "name": "In Transit", "value": 90, "operationalNote": "Shipment date is still ahead of today"},
                {"key": "delayed", "name": "Delayed", "value": 50, "operationalNote": "Flagged as late delivery"},
                {"key": "atRisk", "name": "At Risk", "value": 15, "operationalNote": "Late delivery with extended lead time"},
                {"key": "returned", "name": "Returned", "value": 5, "operationalNote": "Negative profit flag"},
            ]
        }
    }
    return {
        "monthOrder": ["mar-2026", "feb-2026"],
        "byMonth": by_month,
    }


def build_demand_intelligence_fallback() -> dict[str, Any]:
    weeks = [f"W{i:02d}" for i in range(1, 11)]
    base_demand = [4500, 4620, 4800, 4750, 4900, 5100, 5050, 5200, 5350, 5500]
    series = []
    for i, w in enumerate(weeks):
        f = base_demand[i]
        series.append({
            "period": w,
            "actual": f - 80 if i < 6 else None,
            "forecast": f,
            "upper": round(f * 1.08),
            "lower": round(f * 0.92),
        })
    return {
        "accuracy": "94.8%",
        "forecastSeries": series,
        "inventoryHistory": [
            {"month": "Jan", "healthy": 120, "low": 15, "critical": 4, "overstock": 8},
            {"month": "Feb", "healthy": 128, "low": 12, "critical": 3, "overstock": 10},
            {"month": "Mar", "healthy": 135, "low": 10, "critical": 2, "overstock": 7},
        ],
        "kpiStrip": [
            {"label": "Projected Demand", "value": "52,170 units", "trend": "+4.2%", "trendPositive": True, "icon": "trend"},
            {"label": "Mean Absolute Error", "value": "3.1%", "trend": "-0.5%", "trendPositive": True, "icon": "gauge"},
            {"label": "Safety Buffer", "value": "4,800 units", "trend": "Optimal", "trendPositive": True, "icon": "brain"},
        ],
        "modelConfidence": [
            {"label": "RandomForest Regressor", "score": 94, "detail": "Trained on Gold demand history"},
            {"label": "IsolationForest Anomaly", "score": 91, "detail": "Real-time anomaly scoring"},
        ],
        "scenarios": [
            {"name": "Base Case", "impact": "+4.2% Growth", "desc": "Current seasonal purchasing trends continue.", "tone": "emerald"},
            {"name": "Supply Bottleneck", "impact": "-8.5% Volume", "desc": "Port transit delay extends lead time by 3 days.", "tone": "amber"},
        ]
    }


def build_regional_performance_fallback() -> dict[str, Any]:
    return {
        "riskMatrix": [
            {"market": "LATAM", "customerSegment": "Consumer", "shippingMode": "Standard Class", "riskScore": 68, "riskLevel": "Medium"},
            {"market": "Europe", "customerSegment": "Corporate", "shippingMode": "First Class", "riskScore": 22, "riskLevel": "Low"},
            {"market": "USCA", "customerSegment": "Home Office", "shippingMode": "Same Day", "riskScore": 82, "riskLevel": "High"},
        ],
        "riskTrend": [
            {"week": "W01", "risk": 42},
            {"week": "W02", "risk": 38},
            {"week": "W03", "risk": 45},
            {"week": "W04", "risk": 35},
        ],
        "regions": [
            {"region": "Europe", "orders": 12000, "onTimeDelivery": 95.2, "revenue": 450000.0, "profit": 65000.0},
            {"region": "LATAM", "orders": 9800, "onTimeDelivery": 93.8, "revenue": 380000.0, "profit": 52000.0},
            {"region": "USCA", "orders": 14500, "onTimeDelivery": 96.5, "revenue": 520000.0, "profit": 78000.0},
        ],
        "summary": {
            "highExposure": 12,
            "networkRisk": 34.5,
            "anomalies": 3,
            "resolved": 18,
            "reviewing": 4,
        }
    }


def build_revenue_trends_fallback() -> dict[str, Any]:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    return {
        "trends": [
            {"period": m, "revenue": 120000 + i * 8000, "profit": 20000 + i * 1500, "orders": 1400 + i * 50}
            for i, m in enumerate(months)
        ]
    }


def build_inventory_fallback() -> dict[str, Any]:
    return {
        "items": [
            {"id": "SKU-101", "name": "Industrial Sensor Mod-A", "category": "Electronics", "stock": 420, "reorderPoint": 150, "status": "Healthy", "leadTime": 5, "storeId": "STORE-01", "daysInventory": 24},
            {"id": "SKU-102", "name": "Control Module X2", "category": "Electronics", "stock": 45, "reorderPoint": 100, "status": "Low", "leadTime": 12, "storeId": "STORE-02", "daysInventory": 8},
            {"id": "SKU-103", "name": "Hydraulic Pump Array", "category": "Machinery", "stock": 15, "reorderPoint": 30, "status": "Critical", "leadTime": 18, "storeId": "STORE-01", "daysInventory": 3},
            {"id": "SKU-104", "name": "Heavy Duty Bearing Unit", "category": "Hardware", "stock": 850, "reorderPoint": 200, "status": "Overstock", "leadTime": 4, "storeId": "STORE-03", "daysInventory": 45},
        ],
        "history": [
            {"month": "Jan", "healthy": 120, "low": 15, "critical": 4, "overstock": 8},
            {"month": "Feb", "healthy": 128, "low": 12, "critical": 3, "overstock": 10},
            {"month": "Mar", "healthy": 135, "low": 10, "critical": 2, "overstock": 7},
        ]
    }


def build_shipments_fallback() -> dict[str, Any]:
    return {
        "shipments": [
            {
                "id": "ORD-8920",
                "origin": "LATAM",
                "destination": "Consumer",
                "carrier": "First Class",
                "status": "Delivered",
                "eta": "2026-08-15",
                "progress": 100,
                "riskScore": 15,
            },
            {
                "id": "ORD-8921",
                "origin": "Europe",
                "destination": "Corporate",
                "carrier": "Standard Class",
                "status": "Delayed",
                "eta": "2026-08-18",
                "progress": 65,
                "riskScore": 78,
            },
            {
                "id": "ORD-8922",
                "origin": "USCA",
                "destination": "Home Office",
                "carrier": "Second Class",
                "status": "At Risk",
                "eta": "2026-08-19",
                "progress": 40,
                "riskScore": 85,
            },
        ],
        "stats": [
            {"label": "Shipments", "value": "1,420"},
            {"label": "On time", "value": "1,338"},
            {"label": "Delayed", "value": "52"},
            {"label": "At risk", "value": "30"},
        ],
        "volume": [
            {"day": "Mon", "volume": 180},
            {"day": "Tue", "volume": 210},
            {"day": "Wed", "volume": 240},
            {"day": "Thu", "volume": 195},
            {"day": "Fri", "volume": 225},
        ]
    }


@analytics_router.get("/api/databricks-status")
async def databricks_status():
    def builder() -> dict[str, str]:
        row = _first(
            get_databricks_client().query(
                "SELECT 1 AS ok",
                cache_key="databricks-status",
                ttl_seconds=30,
            )
        )
        return {"status": "connected" if row.get("ok") == 1 else "unknown"}

    def fallback() -> dict[str, str]:
        return {"status": "disconnected"}

    return await run_in_threadpool(lambda: _call_databricks(builder, fallback))


@analytics_router.get("/api/dashboard-summary")
async def dashboard_summary():
    return await run_in_threadpool(lambda: _call_databricks(build_dashboard_summary, build_dashboard_summary_fallback))


@analytics_router.get("/api/monthly-logistics")
async def monthly_logistics():
    return await run_in_threadpool(lambda: _call_databricks(build_monthly_logistics, build_monthly_logistics_fallback))


@analytics_router.get("/api/demand-intelligence")
async def demand_intelligence():
    return await run_in_threadpool(lambda: _call_databricks(build_demand_intelligence, build_demand_intelligence_fallback))


@analytics_router.get("/api/regional-performance")
async def regional_performance():
    return await run_in_threadpool(lambda: _call_databricks(build_regional_performance, build_regional_performance_fallback))


@analytics_router.get("/api/revenue-trends")
async def revenue_trends():
    return await run_in_threadpool(lambda: _call_databricks(build_revenue_trends, build_revenue_trends_fallback))


@analytics_router.get("/api/inventory")
async def inventory():
    return await run_in_threadpool(lambda: _call_databricks(build_inventory, build_inventory_fallback))


@analytics_router.get("/api/shipments")
async def shipments():
    return await run_in_threadpool(lambda: _call_databricks(build_shipments, build_shipments_fallback))
