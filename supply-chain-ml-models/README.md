# Supply Chain ML Models

Machine Learning models for supply chain risk analysis.

## Models

This repository contains three trained ML components:

### 1. Delivery Delay Prediction

Random Forest Classifier used to estimate the probability that an order will be delivered late.

Output:

- `delivery_risk`

### 2. Anomaly Detection

Isolation Forest used to identify unusual supply-chain orders.

Outputs:

- `anomaly_prediction`
- `anomaly_score`
- `anomaly_risk`

### 3. Demand Forecasting

Random Forest Regressor used to forecast monthly demand using historical demand features.

Output:

- `predicted demand`

## Supply Chain Risk

Delivery Risk and Anomaly Risk are combined to generate an overall Supply Chain Risk Score.

The final risk score is calculated using:

```text
Supply Chain Risk = 60% Delivery Risk + 40% Anomaly Risk
```

Risk categories:

- Low: score < 25
- Medium: score 25–60
- High: score > 60

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

### Supply Chain Risk Prediction

Import the prediction function:

```python
from predict import predict_supply_chain_risk
```

The `predict_supply_chain_risk()` function requires the following input fields:

- `product_id`
- `customer_id`
- `customer_segment`
- `sales`
- `quantity`
- `shipping_mode`
- `market`
- `lead_time`
- `avg_order_value_30d`
- `num_orders_30d`
- `is_high_value`
- `is_bulk_order`
- `day_of_week`
- `month`
- `quarter`
- `year`
- `department`
- `class`
- `profit`
- `order_processing_days`
- `avg_lead_time_by_mode`
- `avg_shipping_cost`
- `avg_defect_rate`
- `max_defect_rate`
- `profit_margin`

Provide the required order data:

```python
order_data = {
    "product_id": 365,
    "customer_id": 2,
    "customer_segment": "Consumer",
    "sales": 119.98,
    "quantity": 2,
    "shipping_mode": "Standard Class",
    "market": "LATAM",
    "lead_time": 10,
    "avg_order_value_30d": 119.98,
    "num_orders_30d": 1,
    "is_high_value": 0,
    "is_bulk_order": 0,
    "day_of_week": 3,
    "month": 1,
    "quarter": 1,
    "year": 2017,
    "department": "Technology",
    "class": "Regular Air",

    "profit": 20.0,
    "order_processing_days": 2,
    "avg_lead_time_by_mode": 10.0,
    "avg_shipping_cost": 5.0,
    "avg_defect_rate": 1.0,
    "max_defect_rate": 2.0,
    "profit_margin": 0.17
}

result = predict_supply_chain_risk(order_data)

print(result)
```

Example output:

```python
{
    "delivery_risk": 22.0,
    "anomaly_prediction": "Normal",
    "anomaly_score": 0.059487,
    "anomaly_risk": 40.06,
    "supply_chain_risk": 29.23,
    "risk_category": "Medium"
}
```

### Demand Forecasting

Import the demand forecasting function:

```python
from predict import predict_demand
```

The `predict_demand()` function requires:

- `lag_1`
- `lag_2`
- `lag_3`
- `month`

Provide the previous three months of demand:

```python
prediction = predict_demand(
    lag_1=4675,
    lag_2=4146,
    lag_3=4823,
    month=10
)

print(prediction)
```

Example output:

```text
4701.02
```

## Project Structure

```text
supply-chain-ml-models/
│
├── models/
│   ├── delivery_delay_model.pkl
│   ├── delivery_preprocessor.pkl
│   ├── demand_forecasting_model.pkl
│   ├── demand_forecast_features.pkl
│   ├── anomaly_detection_model.pkl
│   ├── anomaly_scaler.pkl
│   └── anomaly_risk_scaler.pkl
│
├── predict.py
├── requirements.txt
└── README.md
```

## Backend Integration

The `predict.py` module is designed to be imported by a backend API.

The backend can call:

```python
from predict import predict_supply_chain_risk
from predict import predict_demand
```

For supply chain risk:

```python
result = predict_supply_chain_risk(order_data)
```

For demand forecasting:

```python
prediction = predict_demand(
    lag_1,
    lag_2,
    lag_3,
    month
)
```

The returned prediction results can be converted to JSON by the backend API and sent to the frontend.

## Model Testing

The trained models were independently tested after saving.

Tested components:

- Delivery delay prediction
- Anomaly detection
- Demand forecasting
- Supply chain risk calculation

The models were also tested after downloading them from the Hugging Face repository.

The downloaded models successfully loaded and generated predictions through the standalone inference pipeline.

## Hugging Face Repository

The trained models and inference code are hosted in this repository:

`saniamirza/supply-chain-ml-models`

The repository contains all required model files, preprocessors, scalers, inference code, dependencies, and documentation for backend integration.