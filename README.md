# RIMS — Real-Time Inventory & Supply Chain Intelligence System

**RIMS** (Real-Time Inventory Monitoring System) is an enterprise-grade, Databricks-backed supply chain analytics and machine learning platform. It combines live Databricks Gold-layer analytics, real-time machine learning inference (risk classification, anomaly detection, and demand forecasting), an automated 10-second live data injection streaming pipeline via Server-Sent Events (SSE), an interactive Gradio model testing interface, and an AI-powered RAG (Retrieval-Augmented Generation) assistant.

---

## Architecture Overview

```mermaid
flowchart TB
    subgraph Frontend["Frontend (Vite + React 18 + TailwindCSS)"]
        UI["Dashboard UI / Recharts"]
        SSE_Client["SSE Client (pipeline.ts)"]
        API_Client["API Service (ml.ts / api.ts)"]
    end

    subgraph Backend["Backend (FastAPI - Port 8000)"]
        Router["FastAPI App (main.py)"]
        
        subgraph ML_Engine["Local Machine Learning Engine"]
            ML_Handler["ml_handler.py"]
            ML_Router["ml_router.py"]
            Gradio_App["Gradio Interface (/model/test)"]
        end

        subgraph Stream_Engine["Live Data Injection Pipeline"]
            DataGen["data_generator.py"]
            Engine["stream_engine.py (10s Loop)"]
            StreamRouter["stream_router.py (SSE)"]
        end

        subgraph Analytics_Engine["Databricks Analytics"]
            DB_Client["databricks_client.py"]
            DB_Analytics["databricks_analytics.py"]
        end

        subgraph AI_RAG["AI & RAG Engine"]
            AI_Handler["ai_handler.py (Gemini + OpenAI)"]
            RAG_Handler["rag_handler.py (ChromaDB)"]
        end
    end

    subgraph External["External Services & Storage"]
        Databricks["Databricks Gold Tables (SQL Warehouse)"]
        ML_Models["Scikit-Learn Models (.pkl files)"]
    end

    UI --> API_Client
    UI --> SSE_Client
    SSE_Client <-->|SSE EventStream| StreamRouter
    API_Client <-->|HTTP REST| Router
    Router --> ML_Router
    Router --> StreamRouter
    Router --> Gradio_App
    Router --> DB_Analytics
    Router --> AI_RAG

    ML_Handler <-->|joblib load| ML_Models
    Engine -->|Runs Inference| ML_Handler
    Engine --> DataGen
    DB_Analytics <-->|SQL Queries| DB_Client
    DB_Client <-->|SQL Connector| Databricks
```

---

## Detailed Directory & Component Structure

```
.
├── Final_App/
│   ├── start.sh                        # One-click startup script for Backend & Frontend
│   ├── stop.sh                         # Clean shutdown script for background processes
│   ├── Backend/                        # FastAPI Backend Application
│   │   ├── main.py                     # Entry point, router registration, Gradio mounting
│   │   ├── ml_handler.py               # Singleton lazy loader & runner for scikit-learn models
│   │   ├── ml_router.py                # REST endpoints for risk prediction & demand forecasting
│   │   ├── live_data_injection_pipeline/ # Real-time streaming pipeline
│   │   │   ├── __init__.py
│   │   │   ├── data_generator.py       # Realistic order & lag feature generator
│   │   │   ├── stream_engine.py        # 10s tick loop & SSE subscriber queue manager
│   │   │   └── stream_router.py        # SSE endpoint (/api/pipeline/stream) & history API
│   │   ├── databricks_client.py        # Databricks SQL connection, queries & memory caching
│   │   ├── databricks_analytics.py     # Aggregates Gold tables into dashboard data models
│   │   ├── sendData.py                 # Databricks live SSE streaming router
│   │   ├── ai_handler.py               # Multi-model LLM handler (Google Gemini + OpenAI)
│   │   ├── rag_handler.py              # Vector store document indexer & retriever (ChromaDB)
│   │   ├── requirements.txt            # Backend Python dependencies
│   │   └── .env.example                # Template for Databricks credentials & configuration
│   └── Frontend/                       # Vite + React Dashboard Application
│       ├── src/
│       │   ├── components/
│       │   │   ├── charts/
│       │   │   │   ├── forecast-chart.tsx # Demand Forecast graph with live SSE stream overlay
│       │   │   │   ├── risk-chart.tsx     # Risk Matrix bar chart & live ML risk stream timeline
│       │   │   │   └── ...
│       │   │   └── ...
│       │   ├── services/
│       │   │   ├── api.ts              # Core API fetch wrapper
│       │   │   ├── ml.ts               # REST client for ML prediction endpoints
│       │   │   ├── pipeline.ts         # SSE EventSource listener for live pipeline
│       │   │   └── ...
│       ├── package.json
│       └── vite.config.ts
├── supply-chain-ml-models/             # Machine Learning Repository
│   ├── models/                         # Serialized scikit-learn model artifacts (.pkl)
│   │   ├── delivery_delay_model.pkl    # RandomForestClassifier for delivery delays
│   │   ├── delivery_preprocessor.pkl # ColumnTransformer preprocessor
│   │   ├── anomaly_detection_model.pkl# IsolationForest for supply chain anomalies
│   │   ├── anomaly_scaler.pkl         # StandardScaler for numerical features
│   │   ├── anomaly_risk_scaler.pkl    # MinMaxScaler for anomaly risk normalization
│   │   └── demand_forecasting_model.pkl # RandomForestRegressor for monthly demand
│   ├── app.py                          # Gradio UI mounted at /model/test/ on FastAPI
│   ├── predict.py                      # Core inference routines
│   └── requirements.txt
└── DataSets/                           # Cleaned CSV datasets & notebook resources
```

---

## Key Modules & Responsibilities

### 1. Machine Learning Engine (`supply-chain-ml-models` & `Backend/ml_handler.py`)
- **Delivery Risk Classifier**: Predicts probability of delivery delay based on 18 order parameters (sales, shipping mode, market, lead time, customer segment, etc.) using `RandomForestClassifier`.
- **Anomaly Detection System**: Evaluates order data for operational anomalies (spikes in defect rate, shipping costs, profit margin deviations) using `IsolationForest` combined with `StandardScaler` and `MinMaxScaler`.
- **Demand Forecaster**: Uses `RandomForestRegressor` trained on historical monthly demand lag features (`lag_1`, `lag_2`, `lag_3`, `month`) to project future product demand.
- **Data Frame Wrapping**: `ml_handler.py` wraps incoming dictionary inputs into `pandas.DataFrame` structures with exact feature column names to eliminate scikit-learn feature name warnings.

### 2. Live Data Injection Pipeline (`Backend/live_data_injection_pipeline/`)
- **`data_generator.py`**: Simulates realistic supply chain order transactions with controlled randomness across segments (Consumer, Corporate, Home Office), shipping modes, markets, lead times, and defect rates (~10% controlled anomaly injection).
- **`stream_engine.py`**: Background asynchronous task running every 10 seconds. On each tick:
  1. Generates a fresh simulated order.
  2. Executes risk classification and anomaly detection.
  3. Generates demand lag features and runs demand forecasting.
  4. Stores results in a rolling history window (last 30 ticks).
  5. Broadcasts combined JSON payloads to all connected SSE clients.
- **`stream_router.py`**: Exposes `GET /api/pipeline/stream` via `StreamingResponse` (Server-Sent Events) and provides initial history bursts so frontend charts display historical trends immediately upon connection.

### 3. Gradio Model Testing Interface (`/model/test`)
- **Mounted Route**: `http://localhost:8000/model/test/`
- **Purpose**: Provides a full, standalone interactive GUI embedded directly inside the FastAPI backend.
- Allows operations teams and developers to manually input custom order data, test edge-case inputs, and view risk scores and demand predictions in real time.

### 4. Databricks Analytics Integration (`Backend/databricks_client.py` & `databricks_analytics.py`)
- Connects securely to a Databricks SQL Warehouse via `databricks-sql-connector`.
- Queries Gold-layer analytical tables:
  - `gold_sales_ml_clean`
  - `gold_inventory_features`
  - `gold_delivery_features`
- Features automatic in-memory caching with configurable TTL (`DATABRICKS_CACHE_TTL_SECONDS`).
- Transforms raw SQL rows into camelCase JSON contracts expected by the React frontend components.

### 5. Multi-Model AI & Document RAG Assistant (`Backend/ai_handler.py` & `rag_handler.py`)
- **LLM Handler**: Supports multi-model inference (Google Gemini primary, OpenAI fallback).
- **Vector Search RAG**: Uses `ChromaDB` with `all-MiniLM-L6-v2` embeddings to index operational documentation (`.txt`, `.md`) and retrieve relevant context for AI assistant user queries (`POST /query`).

---

## API Endpoints Reference

### Health & Pipeline Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check & API version |
| `GET` | `/api/databricks-status` | Databricks connection state |
| `GET` | `/api/ml/status` | ML models load status & registered model list |
| `GET` | `/api/pipeline/status` | Live streaming pipeline execution status |

### Machine Learning & Real-Time Stream
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ml/predict-risk` | Calculate delivery risk, anomaly prediction, and overall supply chain risk |
| `POST` | `/api/ml/predict-demand` | Predict monthly demand from lag inputs (`lag_1`, `lag_2`, `lag_3`, `month`) |
| `GET` | `/api/pipeline/stream` | Server-Sent Events (SSE) stream emitting ML predictions every 10s |
| `GET` | `/api/pipeline/history/risk` | Fetch recent risk prediction history |
| `GET` | `/api/pipeline/history/demand` | Fetch recent demand forecasting history |
| `GET` | `/model/test/` | Interactive Gradio UI for manual ML model testing |

### Databricks Analytics Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard-summary` | KPI metrics, activity feeds, AI insights, and warehouse utilization |
| `GET` | `/api/demand-intelligence` | Demand forecast series, inventory history, and accuracy metrics |
| `GET` | `/api/regional-performance` | Regional risk matrix, risk trends, and performance totals |
| `GET` | `/api/monthly-logistics` | Monthly delivery statuses (delivered, in-transit, delayed, at-risk) |
| `GET` | `/api/inventory` | Inventory product list, stock levels, and days of cover |
| `GET` | `/api/shipments` | Latest shipment records and daily shipment volume |

---

## Getting Started

### Prerequisites
- **Python 3.10+** (Python 3.13 recommended)
- **Node.js 18+** & `npm`
- Databricks SQL Warehouse PAT (Personal Access Token)

### Environment Configuration

Create `Final_App/Backend/.env` based on `.env.example`:

```env
DATABRICKS_SERVER_HOSTNAME=adb-xxxxxxxxxxxxxxxx.x.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your_warehouse_id
DATABRICKS_ACCESS_TOKEN=dapi_your_databricks_pat_here
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=default
DATABRICKS_CACHE_TTL_SECONDS=300

# AI Assistant Keys (Optional)
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

### Running the Application

To start both Backend and Frontend with a single command:

```bash
cd Final_App
bash start.sh
```

The startup script automatically:
1. Creates the Python virtual environment (`Backend/.venv`) if not present.
2. Installs required Python and Node.js dependencies.
3. Launches the FastAPI backend on `http://127.0.0.1:8000`.
4. Starts the live data injection pipeline (10s interval).
5. Verifies Databricks SQL connectivity.
6. Launches the Vite React frontend on `http://127.0.0.1:8082`.

To stop both services cleanly:

```bash
cd Final_App
bash stop.sh
```

---

## Follow-Up Questions & Next Steps

To help tailor future enhancements, consider the following technical options:

1. **ML Model Retraining Pipeline**: Would you like to implement an automated Databricks job or trigger endpoint to retrain the scikit-learn models directly on updated Gold table data periodically?
2. **Persistent Stream Storage**: Currently, the live pipeline maintains a rolling memory buffer of 30 ticks (~5 minutes). Would you like to persist these live order ticks and predictions back into a Databricks streaming table or Delta table?
3. **Alerting & Notifications**: Should we add automated Webhook/Email alerts whenever the live pipeline detects a "High" risk order or an "Anomaly" score exceeding a configured threshold?
4. **Custom Order Input Form on Dashboard**: Would you like to embed a custom interactive order submission modal directly inside the main React frontend (in addition to the Gradio interface at `/model/test`)?
5. **Deployment & Containerization**: Would you like a `docker-compose.yml` setup for containerized production deployment across backend, frontend, and pipeline components?
