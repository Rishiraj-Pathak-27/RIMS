from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from ml_handler import get_ml_handler

ml_router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

class OrderRiskRequest(BaseModel):
    product_id: int = Field(default=365, description="Product ID")
    customer_id: int = Field(default=2, description="Customer ID")
    customer_segment: str = Field(default="Consumer", description="Consumer, Corporate, or Home Office")
    sales: float = Field(default=119.98, description="Order total sales amount")
    quantity: int = Field(default=2, description="Order quantity")
    shipping_mode: str = Field(default="Standard Class", description="Standard Class, Second Class, First Class, or Same Day")
    market: str = Field(default="LATAM", description="LATAM, Europe, USCA, Asia Pacific, or Africa")
    lead_time: int = Field(default=10, description="Lead time in days")
    avg_order_value_30d: float = Field(default=119.98, description="Customer's average order value over last 30 days")
    num_orders_30d: int = Field(default=1, description="Customer's number of orders over last 30 days")
    is_high_value: int = Field(default=0, description="1 if high value order, 0 otherwise")
    is_bulk_order: int = Field(default=0, description="1 if bulk order, 0 otherwise")
    day_of_week: int = Field(default=3, description="Day of week (0-6)")
    month: int = Field(default=1, description="Month (1-12)")
    quarter: int = Field(default=1, description="Quarter (1-4)")
    year: int = Field(default=2017, description="Year")
    department: str = Field(default="Technology", description="Product department")
    item_class: str = Field(default="Regular Air", alias="class", description="Logistics transport class")
    profit: float = Field(default=20.0, description="Order profit")
    order_processing_days: int = Field(default=2, description="Order processing days")
    avg_lead_time_by_mode: float = Field(default=10.0, description="Average lead time for selected shipping mode")
    avg_shipping_cost: float = Field(default=5.0, description="Average shipping cost")
    avg_defect_rate: float = Field(default=1.0, description="Average supplier defect rate (%)")
    max_defect_rate: float = Field(default=2.0, description="Maximum supplier defect rate (%)")
    profit_margin: float = Field(default=0.17, description="Profit margin ratio (0.0 to 1.0)")

    class Config:
        populate_by_name = True

class OrderRiskResponse(BaseModel):
    delivery_risk: float = Field(..., description="Estimated probability of delivery delay (%)")
    anomaly_prediction: str = Field(..., description="Normal or Anomaly")
    anomaly_score: float = Field(..., description="Decision function anomaly score")
    anomaly_risk: float = Field(..., description="Normalized anomaly risk (%)")
    supply_chain_risk: float = Field(..., description="Combined supply chain risk score (0-100)")
    risk_category: str = Field(..., description="Low, Medium, or High")

class DemandForecastRequest(BaseModel):
    lag_1: float = Field(default=4675.0, description="Demand 1 month ago")
    lag_2: float = Field(default=4146.0, description="Demand 2 months ago")
    lag_3: float = Field(default=4823.0, description="Demand 3 months ago")
    month: int = Field(default=10, description="Target forecast month (1-12)")

class DemandForecastResponse(BaseModel):
    predicted_demand: float = Field(..., description="Forecasted monthly demand quantity")
    rolling_mean_3: float = Field(..., description="3-month rolling mean demand")

@ml_router.get("/status")
async def ml_status():
    handler = get_ml_handler()
    return {
        "status": "online" if handler.is_loaded else "offline",
        "models_loaded": handler.is_loaded,
        "models": [
            "Delivery Delay Classifier (RandomForest)",
            "Anomaly Detector (IsolationForest)",
            "Demand Forecaster (RandomForestRegressor)"
        ]
    }

@ml_router.post("/predict-risk", response_model=OrderRiskResponse)
async def predict_risk_endpoint(request: OrderRiskRequest):
    handler = get_ml_handler()
    if not handler.is_loaded:
        raise HTTPException(status_code=503, detail="ML Models are not loaded on backend.")
    try:
        data = request.model_dump(by_alias=True)
        # Ensure 'class' key is present as expected by preprocessor
        if "item_class" in data and "class" not in data:
            data["class"] = data["item_class"]
        result = handler.predict_supply_chain_risk(data)
        return OrderRiskResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Prediction Error: {str(e)}")

@ml_router.post("/predict-demand", response_model=DemandForecastResponse)
async def predict_demand_endpoint(request: DemandForecastRequest):
    handler = get_ml_handler()
    if not handler.is_loaded:
        raise HTTPException(status_code=503, detail="ML Models are not loaded on backend.")
    try:
        predicted = handler.predict_demand(
            lag_1=request.lag_1,
            lag_2=request.lag_2,
            lag_3=request.lag_3,
            month=request.month
        )
        rolling_mean = round((request.lag_1 + request.lag_2 + request.lag_3) / 3.0, 2)
        return DemandForecastResponse(
            predicted_demand=predicted,
            rolling_mean_3=rolling_mean
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Demand Forecast Error: {str(e)}")
