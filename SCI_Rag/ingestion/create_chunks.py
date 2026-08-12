from __future__ import annotations

from typing import Any

import pandas as pd

from ingestion.load_data import load_data


SUMMARY_FIELDS = [
    "order_id",
    "product_id",
    "customer_id",
    "customer_segment",
    "sales",
    "quantity",
    "profit",
    "profit_margin",
    "shipping_mode",
    "lead_time",
    "order_processing_days",
    "market",
    "department",
    "class",
    "is_late_delivery",
    "is_high_value",
    "is_bulk_order",
    "is_profitable",
    "day_of_week",
    "month",
    "quarter",
    "year",
    "order_date",
    "shipment_date",
    "avg_order_value_30d",
    "num_orders_30d",
    "avg_lead_time_by_mode",
    "late_delivery_rate_by_mode",
    "avg_shipping_cost",
    "avg_defect_rate",
    "max_defect_rate",
    "feature_extraction_date",
]


def _format_value(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def row_to_text(row: pd.Series) -> str:
    lines = ["Order record:"]
    for field in SUMMARY_FIELDS:
        if field not in row:
            continue
        label = field.replace("_", " ").title()
        lines.append(f"{label}: {_format_value(row[field])}")
    return "\n".join(lines)


def row_to_metadata(row: pd.Series) -> dict[str, str]:
    return {column: _format_value(value) for column, value in row.items()}


def create_chunks(df: pd.DataFrame) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        order_id = _format_value(row.get("order_id", "unknown"))
        product_id = _format_value(row.get("product_id", "unknown"))

        chunks.append(
            {
                "id": f"order_{order_id}_product_{product_id}",
                "text": row_to_text(row),
                "metadata": row_to_metadata(row),
            }
        )

    return chunks


if __name__ == "__main__":
    dataframe = load_data()
    chunks = create_chunks(dataframe)

    print("Number of chunks:", len(chunks))
    print("\nFirst chunk:")
    print(chunks[0]["text"])