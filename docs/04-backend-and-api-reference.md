# 04 — Backend & API Reference (`Final_App/Backend`)

## Overview
The FastAPI backend (`Final_App/Backend`) serves as the central orchestration engine. It manages local Machine Learning model execution, Databricks SQL Warehouse connectivity, the live streaming pipeline, AI RAG assistant queries, and the embedded Gradio model testing interface.

---

## Backend Submodules & Structure

| File / Component | Responsibility |
|------------------|----------------|
| `main.py` | Application entry point, CORS configuration, router mounting, Gradio interface mounting |
| `ml_handler.py` | Singleton lazy loader & executor for scikit-learn models |
| `ml_router.py` | REST endpoints for manual risk prediction and demand forecasting |
| `databricks_client.py` | Databricks SQL Warehouse connector, parameterized query executor, in-memory caching |
| `databricks_analytics.py` | Transforms raw Gold table rows into frontend dashboard data models |
| `live_data_injection_pipeline/` | Background 10s tick generator, rolling buffer manager, SSE streaming router |
| `ai_handler.py` | Multi-LLM provider integration (Google Gemini primary, OpenAI fallback) |
| `rag_handler.py` | ChromaDB vector store indexer & retriever for operational documentation |

---

## Databricks Gold-Layer Analytics Integration

The backend connects securely to a Databricks SQL Warehouse using `databricks-sql-connector`. It queries three Gold-layer tables:
1. `gold_sales_ml_clean`: Sales volume, revenue, product categories, and profit margins.
2. `gold_inventory_features`: Stock levels, warehouse capacity, product days of cover.
3. `gold_delivery_features`: Delivery statuses (delivered, in-transit, delayed, at-risk), lead times, and carrier performance.

### Performance Caching
To maintain high responsiveness and reduce Databricks warehouse compute costs, query results are cached in-memory with a configurable TTL (`DATABRICKS_CACHE_TTL_SECONDS=300`).

---

## AI & RAG Assistant Engine (`ai_handler.py` & `rag_handler.py`)

- **Vector Database**: `ChromaDB` with `all-MiniLM-L6-v2` embeddings.
- **Document Indexing**: `POST /upload-documents` parses `.txt` and `.md` files into vector embeddings for similarity search.
- **LLM Handler**: `POST /query` retrieves relevant context chunks from ChromaDB and passes them to Google Gemini (or OpenAI fallback) to generate natural language diagnostic responses.

---

## Interactive Gradio Testing Interface (`/model/test/`)

- **Mounted Endpoint**: `http://localhost:8000/model/test/`
- **Purpose**: Provides a full, standalone GUI embedded directly inside FastAPI. Allows developers and operations staff to enter custom order parameters, test edge-case inputs, and view ML risk scores interactively.

---

## Complete API Endpoints Table

### Health & Pipeline Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check & API version |
| `GET` | `/api/databricks-status` | Databricks SQL connection state |
| `GET` | `/api/ml/status` | ML models load status & registered model list |
| `GET` | `/api/pipeline/status` | Live streaming pipeline execution status |

### Machine Learning & Real-Time Stream
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ml/predict-risk` | Calculate delivery risk, anomaly prediction, and overall supply chain risk |
| `POST` | `/api/ml/predict-demand` | Predict monthly demand from lag inputs (`lag_1`, `lag_2`, `lag_3`, `month`) |
| `GET` | `/api/pipeline/stream` | Server-Sent Events (SSE) stream emitting ML predictions every 10s |
| `GET` | `/api/pipeline/history/risk` | Fetch recent risk prediction history (30-tick rolling buffer) |
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

### AI RAG Assistant & Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query` | Submit natural language query to AI assistant with RAG context |
| `POST` | `/upload-documents` | Upload and index `.txt`/`.md` files into ChromaDB vector store |
| `GET` | `/documents-status` | View current ChromaDB collection status & indexed document count |
| `DELETE` | `/clear-documents` | Clear all indexed document collections in ChromaDB |
