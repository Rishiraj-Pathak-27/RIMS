import os
import joblib
import pandas as pd
from typing import Dict, Any

class MLModelHandler:
    """
    Handles loading and inference for the Supply Chain ML Models:
    1. Delivery Delay Prediction (RandomForestClassifier + ColumnTransformer)
    2. Anomaly Detection (IsolationForest + StandardScaler + MinMaxScaler)
    3. Demand Forecasting (RandomForestRegressor)
    """

    def __init__(self, models_dir: str = None):
        if models_dir is None:
            # Look relative to current file or root workspace
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            possible_path = os.path.join(base_dir, "supply-chain-ml-models", "models")
            if os.path.exists(possible_path):
                models_dir = possible_path
            else:
                models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

        self.models_dir = models_dir
        self.is_loaded = False
        
        self.delivery_model = None
        self.delivery_preprocessor = None
        self.anomaly_model = None
        self.anomaly_scaler = None
        self.anomaly_risk_scaler = None
        self.demand_model = None

        self._load_models()

    def _load_models(self):
        try:
            self.delivery_model = joblib.load(
                os.path.join(self.models_dir, "delivery_delay_model.pkl")
            )
            self.delivery_preprocessor = joblib.load(
                os.path.join(self.models_dir, "delivery_preprocessor.pkl")
            )
            self.anomaly_model = joblib.load(
                os.path.join(self.models_dir, "anomaly_detection_model.pkl")
            )
            self.anomaly_scaler = joblib.load(
                os.path.join(self.models_dir, "anomaly_scaler.pkl")
            )
            self.anomaly_risk_scaler = joblib.load(
                os.path.join(self.models_dir, "anomaly_risk_scaler.pkl")
            )
            self.demand_model = joblib.load(
                os.path.join(self.models_dir, "demand_forecasting_model.pkl")
            )
            self.is_loaded = True
            print(f"[MLModelHandler] Successfully loaded all models from {self.models_dir}")
        except Exception as e:
            print(f"[MLModelHandler] Error loading ML models: {e}")
            self.is_loaded = False

    def classify_risk(self, score: float) -> str:
        if score < 25:
            return "Low"
        elif score <= 60:
            return "Medium"
        else:
            return "High"

    def predict_supply_chain_risk(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_loaded:
            raise RuntimeError("ML Models are not loaded.")

        input_df = pd.DataFrame([order_data])

        # 1. Delivery Risk
        delivery_features = [
            "product_id", "customer_id", "customer_segment", "sales", "quantity",
            "shipping_mode", "market", "lead_time", "avg_order_value_30d",
            "num_orders_30d", "is_high_value", "is_bulk_order", "day_of_week",
            "month", "quarter", "year", "department", "class"
        ]
        delivery_input = input_df[delivery_features]
        delivery_processed = self.delivery_preprocessor.transform(delivery_input)
        delivery_probability = self.delivery_model.predict_proba(delivery_processed)[0, 1]
        delivery_risk = delivery_probability * 100.0

        # 2. Anomaly Risk
        anomaly_features = [
            "sales", "quantity", "profit", "lead_time", "order_processing_days",
            "avg_order_value_30d", "num_orders_30d", "avg_lead_time_by_mode",
            "avg_shipping_cost", "avg_defect_rate", "max_defect_rate", "profit_margin"
        ]
        anomaly_input = input_df[anomaly_features]
        anomaly_scaled = self.anomaly_scaler.transform(anomaly_input)
        anomaly_prediction = self.anomaly_model.predict(anomaly_scaled)[0]
        anomaly_score = float(self.anomaly_model.decision_function(anomaly_scaled)[0])

        anomaly_score_df = pd.DataFrame(
            [[-anomaly_score]],
            columns=getattr(self.anomaly_risk_scaler, "feature_names_in_", None)
        )
        if hasattr(self.anomaly_risk_scaler, "feature_names_in_"):
            raw_anomaly_risk = self.anomaly_risk_scaler.transform(anomaly_score_df)[0, 0] * 100.0
        else:
            raw_anomaly_risk = self.anomaly_risk_scaler.transform([[-anomaly_score]])[0, 0] * 100.0
        anomaly_risk = max(0.0, min(100.0, float(raw_anomaly_risk)))

        # 3. Combined Risk (60% Delivery Risk + 40% Anomaly Risk)
        supply_chain_risk = 0.60 * delivery_risk + 0.40 * anomaly_risk
        risk_category = self.classify_risk(supply_chain_risk)

        return {
            "delivery_risk": round(float(delivery_risk), 2),
            "anomaly_prediction": "Anomaly" if anomaly_prediction == -1 else "Normal",
            "anomaly_score": round(anomaly_score, 6),
            "anomaly_risk": round(float(anomaly_risk), 2),
            "supply_chain_risk": round(float(supply_chain_risk), 2),
            "risk_category": risk_category,
        }

    def predict_demand(self, lag_1: float, lag_2: float, lag_3: float, month: int) -> float:
        if not self.is_loaded:
            raise RuntimeError("ML Models are not loaded.")

        rolling_mean_3 = (lag_1 + lag_2 + lag_3) / 3.0
        demand_input = pd.DataFrame({
            "lag_1": [lag_1],
            "lag_2": [lag_2],
            "lag_3": [lag_3],
            "rolling_mean_3": [rolling_mean_3],
            "month": [month]
        })

        prediction = float(self.demand_model.predict(demand_input)[0])
        return round(prediction, 2)

# Global singleton instance
_ml_handler_instance = None

def get_ml_handler() -> MLModelHandler:
    global _ml_handler_instance
    if _ml_handler_instance is None:
        _ml_handler_instance = MLModelHandler()
    return _ml_handler_instance
