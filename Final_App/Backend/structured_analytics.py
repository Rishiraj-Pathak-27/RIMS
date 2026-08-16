"""Exact full-dataset calculations for questions that vector search cannot answer."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


class StructuredAnalytics:
    """Answer supported aggregate questions from the complete source dataset."""

    def __init__(self) -> None:
        default_path = Path(__file__).resolve().parents[2] / "SCI_Rag" / "data" / "03_gold_load_sql.csv"
        self.data_path = Path(default_path)
        self._dataframe: Optional[pd.DataFrame] = None

    def answer(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Return a calculated context document when an exact aggregation is supported."""
        question = query.lower()
        dataframe = self._load_data()
        if dataframe is None:
            return None

        scoped = self._apply_time_scope(dataframe, question)
        scope = self._scope_label(scoped, dataframe, question)

        if "product" in question and "sales" in question and self._contains_any(question, "highest", "top", "most"):
            grouped = (
                scoped.groupby("product_id", as_index=False)
                .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"), orders=("order_id", "nunique"))
                .nlargest(5, "total_sales")
            )
            lines = [f"Exact product-sales ranking calculated from {scope}:"]
            for rank, row in enumerate(grouped.itertuples(index=False), 1):
                lines.append(
                    f"{rank}. Product ID {row.product_id}: total sales ${row.total_sales:,.2f}; "
                    f"total profit ${row.total_profit:,.2f}; {int(row.orders):,} orders."
                )
            return [self._document("Full-dataset product-sales calculation", lines)]

        if "department" in question and "shipping cost" in question and self._contains_any(question, "highest", "top", "average", "avg"):
            grouped = (
                scoped.groupby("department", as_index=False)
                .agg(average_shipping_cost=("avg_shipping_cost", "mean"), orders=("order_id", "nunique"))
                .nlargest(5, "average_shipping_cost")
            )
            lines = [f"Exact department shipping-cost ranking calculated from {scope}:"]
            for rank, row in enumerate(grouped.itertuples(index=False), 1):
                lines.append(
                    f"{rank}. {row.department}: average shipping cost ${row.average_shipping_cost:,.2f} "
                    f"across {int(row.orders):,} orders."
                )
            return [self._document("Full-dataset department shipping-cost calculation", lines)]

        if "sales" in question and "profit" in question and self._contains_any(question, "compare", "comparison"):
            grouped = (
                scoped.groupby(["year", "quarter"], as_index=False)
                .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"), orders=("order_id", "nunique"))
                .sort_values(["year", "quarter"])
            )
            lines = [f"Exact sales and profit comparison calculated from {scope}:"]
            for row in grouped.itertuples(index=False):
                lines.append(
                    f"Year {int(row.year)}, Q{int(row.quarter)}: total sales ${row.total_sales:,.2f}; "
                    f"total profit ${row.total_profit:,.2f}; {int(row.orders):,} orders."
                )
            return [self._document("Full-dataset sales and profit comparison", lines)]

        if "bulk" in question and self._contains_any(question, "not profitable", "unprofitable", "loss"):
            bulk_orders = scoped[
                (pd.to_numeric(scoped["is_bulk_order"], errors="coerce") == 1)
                & (pd.to_numeric(scoped["is_profitable"], errors="coerce") == 0)
            ].sort_values(["profit", "sales"])
            lines = [
                f"Exact bulk-order profitability result from {scope}: "
                f"{len(bulk_orders):,} bulk orders are not profitable.",
                "The following are the 10 lowest-profit orders:",
            ]
            for row in bulk_orders.head(10).itertuples(index=False):
                lines.append(
                    f"Order {row.order_id}: product ID {row.product_id}; quantity {row.quantity:g}; "
                    f"sales ${row.sales:,.2f}; profit ${row.profit:,.2f}; profit margin {row.profit_margin:.2%}."
                )
            return [self._document("Full-dataset unprofitable bulk-order calculation", lines)]

        if "late" in question and self._contains_any(question, "order", "delivery"):
            late_orders = scoped[pd.to_numeric(scoped["is_late_delivery"], errors="coerce") == 1]
            grouped = (
                late_orders.groupby(["market", "department"], as_index=False)
                .agg(late_orders=("order_id", "nunique"), average_lead_time=("lead_time", "mean"))
                .nlargest(10, "late_orders")
            )
            lines = [f"Exact late-order overview calculated from {scope}: {len(late_orders):,} late orders."]
            for row in grouped.itertuples(index=False):
                lines.append(
                    f"{row.market} / {row.department}: {int(row.late_orders):,} late orders; "
                    f"average lead time {row.average_lead_time:.2f} days."
                )
            return [self._document("Full-dataset late-order calculation", lines)]

        if "lead time" in question and "shipping mode" in question and self._contains_any(question, "average", "avg", "compare"):
            grouped = (
                scoped.groupby("shipping_mode", as_index=False)
                .agg(average_lead_time=("lead_time", "mean"), orders=("order_id", "nunique"))
                .nlargest(10, "average_lead_time")
            )
            lines = [f"Exact shipping-mode lead-time comparison calculated from {scope}:"]
            for row in grouped.itertuples(index=False):
                lines.append(
                    f"{row.shipping_mode}: average lead time {row.average_lead_time:.2f} days across "
                    f"{int(row.orders):,} orders."
                )
            return [self._document("Full-dataset shipping-mode lead-time calculation", lines)]

        if "lead time" in question and self._contains_any(question, "highest", "longest", "largest"):
            rows = scoped.nlargest(5, "lead_time")
            lines = [f"Exact longest-lead-time orders from {scope}:"]
            for row in rows.itertuples(index=False):
                lines.append(
                    f"Order {row.order_id}: lead time {row.lead_time:g} days; product ID {row.product_id}; "
                    f"shipping mode {row.shipping_mode}."
                )
            return [self._document("Full-dataset lead-time calculation", lines)]

        if "quantity" in question and self._contains_any(question, "largest", "highest", "most"):
            rows = scoped.nlargest(5, "quantity")
            lines = [f"Exact largest-quantity orders from {scope}:"]
            for row in rows.itertuples(index=False):
                lines.append(
                    f"Order {row.order_id}: quantity {row.quantity:g}; sales ${row.sales:,.2f}; "
                    f"product ID {row.product_id}."
                )
            return [self._document("Full-dataset quantity calculation", lines)]

        return None

    def _load_data(self) -> Optional[pd.DataFrame]:
        if self._dataframe is not None:
            return self._dataframe
        try:
            self._dataframe = pd.read_csv(self.data_path)
            return self._dataframe
        except Exception as error:
            print(f"[analytics] Could not load {self.data_path}: {error}")
            return None

    @staticmethod
    def _contains_any(text: str, *terms: str) -> bool:
        return any(term in text for term in terms)

    @staticmethod
    def _apply_time_scope(dataframe: pd.DataFrame, question: str) -> pd.DataFrame:
        scoped = dataframe
        year_match = re.search(r"\b(20\d{2})\b", question)
        if year_match:
            scoped = scoped[scoped["year"] == int(year_match.group(1))]

        quarter_match = re.search(r"\bq([1-4])\b|\b([1-4])(st|nd|rd|th) quarter\b", question)
        if quarter_match:
            quarter = int(quarter_match.group(1) or quarter_match.group(2))
            scoped = scoped[scoped["quarter"] == quarter]
        return scoped if not scoped.empty else dataframe

    @staticmethod
    def _scope_label(scoped: pd.DataFrame, full: pd.DataFrame, question: str) -> str:
        if len(scoped) == len(full):
            return f"all {len(full):,} available order rows"
        return f"the requested time period ({len(scoped):,} order rows)"

    @staticmethod
    def _document(source: str, lines: List[str]) -> Dict[str, Any]:
        return {"content": "\n".join(lines), "source": source, "similarity": 1.0}
