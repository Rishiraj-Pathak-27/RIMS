# RIMS — Real-Time Inventory & Supply Chain Intelligence System

**RIMS** (Real-Time Inventory Monitoring System) is an enterprise-grade, Databricks-backed supply chain analytics and machine learning platform. It combines live Databricks Gold-layer analytics, real-time multi-model machine learning inference (delivery risk classification, isolation forest anomaly detection, and autoregressive demand forecasting), an automated 10-second live data injection streaming pipeline via Server-Sent Events (SSE), an interactive Gradio model testing interface, and an AI-powered RAG (Retrieval-Augmented Generation) assistant.

---

## 📚 Comprehensive Documentation Index (`docs/`)

For detailed technical explanations, mathematical formulations, API specifications, and troubleshooting guides, please refer to the dedicated documentation modules in the [`docs/`](docs/) directory:

- 📖 **[01 — Architecture & Vision](docs/01-architecture-and-vision.md)**: Executive summary, project aim, problem solved, detection matrix, and high-level system diagrams.
- 🤖 **[02 — Machine Learning Engine](docs/02-machine-learning-engine.md)**: Deep dive into the 3 scikit-learn models (`RandomForestClassifier`, `IsolationForest`, `RandomForestRegressor`), scalers, composite risk formulas, and Python inference code.
- ⚡ **[03 — Live Data Injection Pipeline](docs/03-live-data-injection-pipeline.md)**: Real-time 10s streaming tick loop, synthetic telemetry generation, 30-tick rolling buffer, Server-Sent Events (SSE), and dynamic UI rendering.
- ⚙️ **[04 — Backend & API Reference](docs/04-backend-and-api-reference.md)**: FastAPI architecture, Databricks SQL caching, ChromaDB vector RAG engine, Gradio testing GUI (`/model/test/`), and complete endpoint reference tables.
- 💻 **[05 — Frontend Dashboard](docs/05-frontend-dashboard.md)**: React 18 + Vite + TailwindCSS component tree, Recharts dynamic charts, Zustand state stores, and TanStack routing.
- ❓ **[06 — FAQ & Troubleshooting](docs/06-faq-and-troubleshooting.md)**: Answers to core architectural questions, operational detection scenarios, and step-by-step troubleshooting guides.

---

## Quick Architecture Overview

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
            RAG_Handler["rag_handler.py (Pinecone VDB)"]
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

## Project Structure Overview

```
.
├── docs/                               # Modular Documentation Hub
│   ├── 01-architecture-and-vision.md   # Project vision, aim, and detection matrix
│   ├── 02-machine-learning-engine.md   # Detailed scikit-learn models & formulas
│   ├── 03-live-data-injection-pipeline.md # 10s streaming pipeline & SSE lifecycle
│   ├── 04-backend-and-api-reference.md # FastAPI routes, Databricks & ChromaDB RAG
│   ├── 05-frontend-dashboard.md        # React components, Recharts & Zustand stores
│   └── 06-faq-and-troubleshooting.md   # FAQs and diagnostic guides
├── Final_App/
│   ├── start.sh                        # One-click startup script for Backend & Frontend
│   ├── stop.sh                         # Clean shutdown script for background processes
│   ├── Backend/                        # FastAPI Backend Application
│   │   ├── main.py                     # FastAPI entry point & Gradio mounting
│   │   ├── ml_handler.py               # Singleton lazy loader for scikit-learn models
│   │   ├── ml_router.py                # REST endpoints for risk & demand inference
│   │   ├── live_data_injection_pipeline/ # Real-time streaming pipeline
│   │   ├── databricks_client.py        # Databricks SQL connection & caching
│   │   ├── ai_handler.py               # Gemini & OpenAI LLM handler
│   │   └── rag_handler.py              # ChromaDB vector store retriever
│   └── Frontend/                       # Vite + React Dashboard Application
│       ├── src/                        # Components, hooks, services, stores, routes
│       └── vite.config.ts
├── supply-chain-ml-models/             # Serialized scikit-learn models & predict.py
│   ├── models/                         # Serialized model weights (.pkl files)
│   ├── app.py                          # Gradio testing interface
│   └── predict.py                      # Core python inference routines
├── DataSets/                           # Cleaned CSV datasets & Databricks notebooks
└── README.md                           # Master Overview & Documentation Hub
```

---

## Quick Start Guide

### Prerequisites
- **Python 3.10+** (Python 3.13 recommended)
- **Node.js 18+** & `npm`
- Databricks SQL Warehouse PAT (Personal Access Token)

### Environment Setup

Configure secrets in `Final_App/Backend/.env` (see `.env.example` template):

```env
DATABRICKS_SERVER_HOSTNAME=adb-xxxxxxxxxxxxxxxx.x.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your_warehouse_id
DATABRICKS_ACCESS_TOKEN=dapi_your_databricks_pat_here
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=default
DATABRICKS_CACHE_TTL_SECONDS=300

# Optional AI Assistant Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

### Running Backend & Frontend

Start both services with a single command:

```bash
cd Final_App
bash start.sh
```

- **React Dashboard**: `http://127.0.0.1:8082`
- **FastAPI Backend**: `http://127.0.0.1:8000`
- **Gradio Interactive Testing**: `http://127.0.0.1:8000/model/test/`

To shut down cleanly:

```bash
cd Final_App
bash stop.sh
```
