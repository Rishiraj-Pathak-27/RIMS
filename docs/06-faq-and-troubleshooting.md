# 06 — Frequently Asked Questions (FAQ) & Troubleshooting

## Frequently Asked Questions

### Q1: What is the primary aim of the RIMS project?
**Answer**: The primary aim of RIMS is to provide an end-to-end, real-time supply chain intelligence platform. It eliminates operational blind spots by bridging enterprise analytical warehousing (Databricks Gold tables) with live 10-second machine learning telemetry, enabling proactive risk mitigation before disruptions affect customers.

### Q2: What specific supply chain disruptions does RIMS detect?
**Answer**: RIMS detects three core categories of disruptions:
1. **Shipping Delays**: High probability of late delivery based on carrier, route, lead time, and order traits.
2. **Operational & Financial Anomalies**: Unusually high defect rates, unexpected shipping cost surges, and profit margin collapses.
3. **Demand Volatility**: Impending inventory stockouts or overstocking through 3-month autoregressive lag forecasting.

### Q3: Why are multiple ML models used instead of a single overall model?
**Answer**: Supply chain dynamics require different types of mathematical modeling:
- **Delivery Delay** is a *supervised classification problem* trained on historical fulfillment labels (`RandomForestClassifier`).
- **Anomaly Detection** is an *unsupervised pattern recognition problem* designed to flag novel, unseen operational failures (`IsolationForest`).
- **Demand Forecasting** is a *continuous regression problem* modeling seasonal and temporal demand trends (`RandomForestRegressor`).

### Q4: How are Delivery Risk and Anomaly Risk combined into a single score?
**Answer**: They are combined using a weighted composite formula:
$$\text{Supply Chain Risk} = 0.60 \times \text{Delivery Risk} + 0.40 \times \text{Anomaly Risk}$$
Delivery risk carries a 60% weight because fulfillment delays directly impact customer satisfaction, while operational anomalies carry a 40% weight to catch cost leaks and defect spikes.

### Q5: How does the live 10-second data injection pipeline work without overloading Databricks?
**Answer**: The live pipeline operates asynchronously in-memory inside the FastAPI backend. It generates synthetic live order telemetry and runs lightweight scikit-learn models locally every 10 seconds. Heavy analytical queries hit Databricks SQL Warehouse separately with an automated 300-second in-memory cache, keeping Databricks query costs low while maintaining instant UI reactivity.

### Q6: What is the purpose of the AI RAG Assistant?
**Answer**: The AI RAG (Retrieval-Augmented Generation) assistant enables operations teams to interact with supply chain data using natural language. It indexes operational documentation into ChromaDB and uses Google Gemini (or OpenAI) to answer complex diagnostic questions about inventory levels, risk scores, and carrier performance.

### Q7: How can developers or logistics staff test custom inputs manually?
**Answer**: By visiting the interactive Gradio GUI embedded directly at `http://localhost:8000/model/test/`.

---

## Troubleshooting Guide

### 1. Backend Fails to Connect to Databricks
- **Symptom**: `GET /api/databricks-status` returns `connected: false`.
- **Solution**:
  1. Verify `Final_App/Backend/.env` contains valid `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, and `DATABRICKS_ACCESS_TOKEN`.
  2. Test if your Personal Access Token (PAT) has expired in Databricks settings.
  3. Ensure your Databricks SQL Warehouse is running (not stopped or suspended).

### 2. ML Models Missing or Load Failure
- **Symptom**: `/api/ml/status` shows models missing or `is_loaded: false`.
- **Solution**:
  1. Check that `supply-chain-ml-models/models/` contains all required `.pkl` files (`delivery_delay_model.pkl`, `anomaly_detection_model.pkl`, `demand_forecasting_model.pkl`, etc.).
  2. Verify python packages (`scikit-learn`, `joblib`, `pandas`) are installed inside `Final_App/Backend/.venv`.

### 3. Frontend Displays Stale Stream Data
- **Symptom**: Live risk charts do not update every 10 seconds.
- **Solution**:
  1. Open Browser DevTools -> Network -> filter by `stream`. Verify `GET /api/pipeline/stream` is active with status `200 OK` (EventStream).
  2. Ensure background pipeline loop is active by checking `GET /api/pipeline/status`.
