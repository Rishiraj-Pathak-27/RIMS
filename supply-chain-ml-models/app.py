import gradio as gr

from predict import predict_supply_chain_risk, predict_demand


# ============================================================
# SUPPLY CHAIN RISK PREDICTION
# ============================================================

def risk_prediction(
    product_id,
    customer_id,
    customer_segment,
    sales,
    quantity,
    shipping_mode,
    market,
    lead_time,
    avg_order_value_30d,
    num_orders_30d,
    is_high_value,
    is_bulk_order,
    day_of_week,
    month,
    quarter,
    year,
    department,
    item_class,
    profit,
    order_processing_days,
    avg_lead_time_by_mode,
    avg_shipping_cost,
    avg_defect_rate,
    max_defect_rate,
    profit_margin
):

    order_data = {
        "product_id": product_id,
        "customer_id": customer_id,
        "customer_segment": customer_segment,
        "sales": sales,
        "quantity": quantity,
        "shipping_mode": shipping_mode,
        "market": market,
        "lead_time": lead_time,
        "avg_order_value_30d": avg_order_value_30d,
        "num_orders_30d": num_orders_30d,
        "is_high_value": is_high_value,
        "is_bulk_order": is_bulk_order,
        "day_of_week": day_of_week,
        "month": month,
        "quarter": quarter,
        "year": year,
        "department": department,
        "class": item_class,
        "profit": profit,
        "order_processing_days": order_processing_days,
        "avg_lead_time_by_mode": avg_lead_time_by_mode,
        "avg_shipping_cost": avg_shipping_cost,
        "avg_defect_rate": avg_defect_rate,
        "max_defect_rate": max_defect_rate,
        "profit_margin": profit_margin
    }

    result = predict_supply_chain_risk(order_data)

    return (
        result["delivery_risk"],
        result["anomaly_prediction"],
        result["anomaly_score"],
        result["anomaly_risk"],
        result["supply_chain_risk"],
        result["risk_category"]
    )


# ============================================================
# DEMAND FORECASTING
# ============================================================

def demand_prediction(lag_1, lag_2, lag_3, month):

    return predict_demand(
        lag_1,
        lag_2,
        lag_3,
        month
    )


# ============================================================
# CUSTOM CSS
# ============================================================

custom_css = """
body {
    background: #f5f7fa;
}

.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
    padding: 30px !important;
}

/* Main header */
.main-header {
    text-align: center;
    padding: 25px 20px;
    margin-bottom: 25px;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}

.main-title {
    font-size: 32px;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 8px;
}

.main-subtitle {
    font-size: 15px;
    color: #64748b;
}

/* Section headers */
.section-header {
    font-size: 21px;
    font-weight: 650;
    color: #1e293b;
    padding-bottom: 10px;
    border-bottom: 2px solid #e2e8f0;
    margin-bottom: 18px;
}

/* Input sections */
.input-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px;
}

/* Buttons */
.primary-button {
    margin-top: 20px;
}

/* Results */
.results-header {
    font-size: 19px;
    font-weight: 650;
    color: #1e293b;
    margin-top: 25px;
    margin-bottom: 12px;
}

.result-box {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

/* Footer */
.footer-text {
    text-align: center;
    color: #94a3b8;
    font-size: 13px;
    margin-top: 30px;
}
"""


# ============================================================
# GRADIO INTERFACE
# ============================================================

with gr.Blocks(
    title="Supply Chain ML Predictor",
    css=custom_css,
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate"
    )
) as demo:

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    gr.HTML(
        """
        <div class="main-header">
            <div class="main-title">
                Supply Chain Intelligence
            </div>
            <div class="main-subtitle">
                Machine Learning based risk analysis and demand forecasting
            </div>
        </div>
        """
    )

    # ========================================================
    # SUPPLY CHAIN RISK
    # ========================================================

    gr.HTML(
        '<div class="section-header">Supply Chain Risk Prediction</div>'
    )

    gr.Markdown(
        "Enter order and operational information to calculate the overall supply chain risk."
    )

    with gr.Row():

        # ----------------------------------------------------
        # LEFT COLUMN
        # ----------------------------------------------------

        with gr.Column(elem_classes="input-card"):

            gr.Markdown("### Order Information")

            product_id = gr.Number(
                label="Product ID",
                value=365
            )

            customer_id = gr.Number(
                label="Customer ID",
                value=2
            )

            customer_segment = gr.Dropdown(
                ["Consumer", "Corporate", "Home Office"],
                label="Customer Segment",
                value="Consumer"
            )

            sales = gr.Number(
                label="Sales",
                value=119.98
            )

            quantity = gr.Number(
                label="Quantity",
                value=2
            )

            shipping_mode = gr.Dropdown(
                [
                    "Standard Class",
                    "Second Class",
                    "First Class",
                    "Same Day"
                ],
                label="Shipping Mode",
                value="Standard Class"
            )

            market = gr.Dropdown(
                [
                    "LATAM",
                    "Europe",
                    "USCA",
                    "Asia Pacific",
                    "Africa"
                ],
                label="Market",
                value="LATAM"
            )

            lead_time = gr.Number(
                label="Lead Time",
                value=10
            )

            avg_order_value_30d = gr.Number(
                label="Average Order Value (30 Days)",
                value=119.98
            )

            num_orders_30d = gr.Number(
                label="Number of Orders (30 Days)",
                value=1
            )

            is_high_value = gr.Number(
                label="High Value Order (0/1)",
                value=0
            )

            is_bulk_order = gr.Number(
                label="Bulk Order (0/1)",
                value=0
            )

        # ----------------------------------------------------
        # RIGHT COLUMN
        # ----------------------------------------------------

        with gr.Column(elem_classes="input-card"):

            gr.Markdown("### Operational Information")

            day_of_week = gr.Number(
                label="Day of Week",
                value=3
            )

            month = gr.Number(
                label="Month",
                value=1
            )

            quarter = gr.Number(
                label="Quarter",
                value=1
            )

            year = gr.Number(
                label="Year",
                value=2017
            )

            department = gr.Textbox(
                label="Department",
                value="Technology"
            )

            item_class = gr.Textbox(
                label="Class",
                value="Regular Air"
            )

            profit = gr.Number(
                label="Profit",
                value=20.0
            )

            order_processing_days = gr.Number(
                label="Order Processing Days",
                value=2
            )

            avg_lead_time_by_mode = gr.Number(
                label="Average Lead Time by Mode",
                value=10.0
            )

            avg_shipping_cost = gr.Number(
                label="Average Shipping Cost",
                value=5.0
            )

            avg_defect_rate = gr.Number(
                label="Average Defect Rate",
                value=1.0
            )

            max_defect_rate = gr.Number(
                label="Maximum Defect Rate",
                value=2.0
            )

            profit_margin = gr.Number(
                label="Profit Margin",
                value=0.17
            )

    # --------------------------------------------------------
    # PREDICTION BUTTON
    # --------------------------------------------------------

    predict_button = gr.Button(
        "Predict Supply Chain Risk",
        variant="primary",
        size="lg",
        elem_classes="primary-button"
    )

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    gr.HTML(
        '<div class="results-header">Prediction Results</div>'
    )

    with gr.Row(elem_classes="result-box"):

        delivery_output = gr.Number(
            label="Delivery Risk (%)"
        )

        anomaly_prediction_output = gr.Textbox(
            label="Anomaly Prediction"
        )

        anomaly_score_output = gr.Number(
            label="Anomaly Score"
        )

    with gr.Row(elem_classes="result-box"):

        anomaly_risk_output = gr.Number(
            label="Anomaly Risk (%)"
        )

        supply_chain_risk_output = gr.Number(
            label="Supply Chain Risk"
        )

        risk_category_output = gr.Textbox(
            label="Risk Category"
        )

    predict_button.click(
        fn=risk_prediction,
        inputs=[
            product_id,
            customer_id,
            customer_segment,
            sales,
            quantity,
            shipping_mode,
            market,
            lead_time,
            avg_order_value_30d,
            num_orders_30d,
            is_high_value,
            is_bulk_order,
            day_of_week,
            month,
            quarter,
            year,
            department,
            item_class,
            profit,
            order_processing_days,
            avg_lead_time_by_mode,
            avg_shipping_cost,
            avg_defect_rate,
            max_defect_rate,
            profit_margin
        ],
        outputs=[
            delivery_output,
            anomaly_prediction_output,
            anomaly_score_output,
            anomaly_risk_output,
            supply_chain_risk_output,
            risk_category_output
        ]
    )

    # ========================================================
    # DEMAND FORECASTING
    # ========================================================

    gr.HTML(
        '<div class="section-header" style="margin-top: 40px;">Demand Forecasting</div>'
    )

    gr.Markdown(
        "Enter historical demand values to forecast the next month's demand."
    )

    with gr.Row(elem_classes="input-card"):

        lag_1 = gr.Number(
            label="Previous Month Demand (Lag 1)",
            value=4675
        )

        lag_2 = gr.Number(
            label="Two Months Ago (Lag 2)",
            value=4146
        )

        lag_3 = gr.Number(
            label="Three Months Ago (Lag 3)",
            value=4823
        )

        forecast_month = gr.Number(
            label="Forecast Month",
            value=10
        )

    forecast_button = gr.Button(
        "Forecast Demand",
        variant="primary",
        size="lg"
    )

    demand_output = gr.Number(
        label="Predicted Demand"
    )

    forecast_button.click(
        fn=demand_prediction,
        inputs=[
            lag_1,
            lag_2,
            lag_3,
            forecast_month
        ],
        outputs=demand_output
    )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    gr.HTML(
        """
        <div class="footer-text">
            Supply Chain Machine Learning System
        </div>
        """
    )


# ============================================================
# LAUNCH
# ============================================================

if __name__ == "__main__":
    import os
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    demo.launch(server_name=server_name, server_port=server_port, show_error=True)