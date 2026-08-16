import os
import joblib
import pandas as pd

def _load_model(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            header = f.read(100)
            if b"git-lfs" in header or b"https://git-lfs" in header:
                return None
        return joblib.load(path)
    except Exception:
        return None



_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_BASE_DIR, "models")

delivery_model = _load_model(os.path.join(_MODELS_DIR, "delivery_delay_model.pkl"))
delivery_preprocessor = _load_model(os.path.join(_MODELS_DIR, "delivery_preprocessor.pkl"))
anomaly_model = _load_model(os.path.join(_MODELS_DIR, "anomaly_detection_model.pkl"))
anomaly_scaler = _load_model(os.path.join(_MODELS_DIR, "anomaly_scaler.pkl"))
anomaly_risk_scaler = _load_model(os.path.join(_MODELS_DIR, "anomaly_risk_scaler.pkl"))
demand_model = _load_model(os.path.join(_MODELS_DIR, "demand_forecasting_model.pkl"))

models_loaded = all(
    m is not None
    for m in [
        delivery_model, delivery_preprocessor, anomaly_model,
        anomaly_scaler, anomaly_risk_scaler, demand_model
    ]
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
    if models_loaded:
        try:
            input_df = pd.DataFrame([order_data])

            delivery_input = input_df[delivery_features]
            delivery_processed = delivery_preprocessor.transform(delivery_input)
            delivery_probability = delivery_model.predict_proba(delivery_processed)[0, 1]
            delivery_risk = delivery_probability * 100

            anomaly_input = input_df[anomaly_features]
            anomaly_scaled = anomaly_scaler.transform(anomaly_input)
            anomaly_prediction = anomaly_model.predict(anomaly_scaled)[0]
            anomaly_score = anomaly_model.decision_function(anomaly_scaled)[0]

            anomaly_score_df = pd.DataFrame(
                [[-anomaly_score]],
                columns=getattr(anomaly_risk_scaler, "feature_names_in_", None)
            )
            if hasattr(anomaly_risk_scaler, "feature_names_in_"):
                raw_risk = anomaly_risk_scaler.transform(anomaly_score_df)[0, 0] * 100
            else:
                raw_risk = anomaly_risk_scaler.transform([[-anomaly_score]])[0, 0] * 100

            anomaly_risk = max(0.0, min(100.0, float(raw_risk)))
            supply_chain_risk = 0.60 * delivery_risk + 0.40 * anomaly_risk
            risk_category = classify_risk(supply_chain_risk)

            return {
                "delivery_risk": round(float(delivery_risk), 2),
                "anomaly_prediction": "Anomaly" if anomaly_prediction == -1 else "Normal",
                "anomaly_score": round(float(anomaly_score), 6),
                "anomaly_risk": round(float(anomaly_risk), 2),
                "supply_chain_risk": round(float(supply_chain_risk), 2),
                "risk_category": risk_category
            }
        except Exception:
            pass

    # Analytical fallback calculation
    lead_time = float(order_data.get("lead_time", 5))
    avg_lead_time = float(order_data.get("avg_lead_time_by_mode", 5))
    defect_rate = float(order_data.get("avg_defect_rate", 1.0))
    sales = float(order_data.get("sales", 100.0))

    lead_delay = max(0.0, lead_time - avg_lead_time)
    delivery_risk = min(95.0, max(5.0, 15.0 + lead_delay * 12.0 + (sales / 1000.0) * 5.0))
    is_anomaly = defect_rate > 4.5 or lead_delay > 6.0
    anomaly_prediction = "Anomaly" if is_anomaly else "Normal"
    anomaly_score = -0.15 if is_anomaly else 0.25
    anomaly_risk = min(98.0, max(2.0, defect_rate * 12.0 + lead_delay * 8.0))

    supply_chain_risk = 0.60 * delivery_risk + 0.40 * anomaly_risk
    risk_category = classify_risk(supply_chain_risk)

    return {
        "delivery_risk": round(delivery_risk, 2),
        "anomaly_prediction": anomaly_prediction,
        "anomaly_score": round(anomaly_score, 6),
        "anomaly_risk": round(anomaly_risk, 2),
        "supply_chain_risk": round(supply_chain_risk, 2),
        "risk_category": risk_category
    }


# ============================================================
# DEMAND FORECASTING
# ============================================================

def predict_demand(lag_1, lag_2, lag_3, month):
    rolling_mean_3 = (lag_1 + lag_2 + lag_3) / 3
    if models_loaded:
        try:
            demand_input = pd.DataFrame({
                "lag_1": [lag_1],
                "lag_2": [lag_2],
                "lag_3": [lag_3],
                "rolling_mean_3": [rolling_mean_3],
                "month": [month]
            })
            prediction = demand_model.predict(demand_input)[0]
            return round(float(prediction), 2)
        except Exception:
            pass

    trend = (lag_1 - lag_3) * 0.15
    forecast = rolling_mean_3 + trend
    return round(max(10.0, float(forecast)), 2)