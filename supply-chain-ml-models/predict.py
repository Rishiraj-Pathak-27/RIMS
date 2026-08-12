import os
import joblib
import pandas as pd


# ============================================================
# LOAD MODELS
# ============================================================

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_BASE_DIR, "models")

delivery_model = joblib.load(
    os.path.join(_MODELS_DIR, "delivery_delay_model.pkl")
)

delivery_preprocessor = joblib.load(
    os.path.join(_MODELS_DIR, "delivery_preprocessor.pkl")
)

anomaly_model = joblib.load(
    os.path.join(_MODELS_DIR, "anomaly_detection_model.pkl")
)

anomaly_scaler = joblib.load(
    os.path.join(_MODELS_DIR, "anomaly_scaler.pkl")
)

anomaly_risk_scaler = joblib.load(
    os.path.join(_MODELS_DIR, "anomaly_risk_scaler.pkl")
)

demand_model = joblib.load(
    os.path.join(_MODELS_DIR, "demand_forecasting_model.pkl")
)



# ============================================================
# FEATURE DEFINITIONS
# ============================================================

delivery_features = [
    "product_id",
    "customer_id",
    "customer_segment",
    "sales",
    "quantity",
    "shipping_mode",
    "market",
    "lead_time",
    "avg_order_value_30d",
    "num_orders_30d",
    "is_high_value",
    "is_bulk_order",
    "day_of_week",
    "month",
    "quarter",
    "year",
    "department",
    "class"
]


anomaly_features = [
    "sales",
    "quantity",
    "profit",
    "lead_time",
    "order_processing_days",
    "avg_order_value_30d",
    "num_orders_30d",
    "avg_lead_time_by_mode",
    "avg_shipping_cost",
    "avg_defect_rate",
    "max_defect_rate",
    "profit_margin"
]


# ============================================================
# RISK CATEGORY
# ============================================================

def classify_risk(score):

    if score < 25:
        return "Low"

    elif score <= 60:
        return "Medium"

    else:
        return "High"


# ============================================================
# SUPPLY CHAIN RISK PREDICTION
# ============================================================

def predict_supply_chain_risk(order_data):

    input_df = pd.DataFrame([order_data])

    # --------------------------------------------------------
    # Delivery Risk
    # --------------------------------------------------------

    delivery_input = input_df[delivery_features]

    delivery_processed = delivery_preprocessor.transform(
        delivery_input
    )

    delivery_probability = delivery_model.predict_proba(
        delivery_processed
    )[0, 1]

    delivery_risk = delivery_probability * 100

    # --------------------------------------------------------
    # Anomaly Risk
    # --------------------------------------------------------

    anomaly_input = input_df[anomaly_features]

    anomaly_scaled = anomaly_scaler.transform(
        anomaly_input
    )

    anomaly_prediction = anomaly_model.predict(
        anomaly_scaled
    )[0]

    anomaly_score = anomaly_model.decision_function(
        anomaly_scaled
    )[0]

    # Use the same scaler used during model development
    anomaly_score_df = pd.DataFrame(
        [[-anomaly_score]],
        columns=anomaly_risk_scaler.feature_names_in_
    )

    anomaly_risk = (
        anomaly_risk_scaler
        .transform([[-anomaly_score]])[0, 0]
        * 100
    )

    # Keep anomaly risk within a valid 0-100 range
    anomaly_risk = max(0.0, min(100.0, float(anomaly_risk)))

    # --------------------------------------------------------
    # Combined Risk
    # --------------------------------------------------------

    supply_chain_risk = (
        0.60 * delivery_risk
        + 0.40 * anomaly_risk
    )

    risk_category = classify_risk(
        supply_chain_risk
    )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "delivery_risk": round(
            delivery_risk,
            2
        ),

        "anomaly_prediction": (
            "Anomaly"
            if anomaly_prediction == -1
            else "Normal"
        ),

        "anomaly_score": round(
            anomaly_score,
            6
        ),

        "anomaly_risk": round(
            anomaly_risk,
            2
        ),

        "supply_chain_risk": round(
            supply_chain_risk,
            2
        ),

        "risk_category": risk_category
    }


# ============================================================
# DEMAND FORECASTING
# ============================================================

def predict_demand(
    lag_1,
    lag_2,
    lag_3,
    month
):

    rolling_mean_3 = (
        lag_1 + lag_2 + lag_3
    ) / 3

    demand_input = pd.DataFrame({
        "lag_1": [lag_1],
        "lag_2": [lag_2],
        "lag_3": [lag_3],
        "rolling_mean_3": [rolling_mean_3],
        "month": [month]
    })

    prediction = demand_model.predict(
        demand_input
    )[0]

    return round(
        prediction,
        2
    )