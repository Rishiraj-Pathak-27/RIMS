# 01 — Project Vision, Core Aim & System Architecture

## Executive Summary
**RIMS** (Real-Time Inventory Monitoring System) is an enterprise-grade supply chain analytics and machine learning platform. It combines Databricks Gold-layer analytics, real-time multi-model machine learning inference, an automated 10-second live data injection streaming pipeline via Server-Sent Events (SSE), an interactive Gradio model testing interface, and an AI-powered RAG (Retrieval-Augmented Generation) assistant.

---

## 1. Project Vision & Core Aim

### The Core Problem Solved
Legacy Supply Chain Management (SCM) systems rely on batch reporting (daily or weekly ETL runs), leaving logistics managers blind to intra-day disruptions. When a shipment is delayed, a supplier defect rate spikes, or inventory runs out, operations teams usually react **after** customer dissatisfaction or financial loss occurs.

### The Aim of RIMS
**The Aim of RIMS** is to transform supply chain operations from **reactive troubleshooting** to **proactive predictive intelligence**. By pairing enterprise-scale Databricks Gold-layer analytical tables with a 10-second live machine learning inference pipeline, RIMS detects disruptions, quantifies risk, and predicts demand changes **in real time**.

---

## 2. What RIMS Detects (Detection Matrix)

RIMS continuously monitors supply chain transactions and automatically detects:

| Detection Category | Component | Key Metrics & Indicators | Operational Impact |
|-------------------|-----------|-------------------------|-------------------|
| 🚚 **Delivery Delay Risks** | `RandomForestClassifier` | Shipping mode, carrier lead time, market, segment | Identifies high-risk orders *before* dispatch |
| ⚠️ **Operational & Financial Anomalies** | `IsolationForest` | Margin drops, shipping cost spikes, defect rates | Flags supplier defect spikes & profit leaks |
| 📈 **Demand Shifts & Stockouts** | `RandomForestRegressor` | 3-month autoregressive demand lags ($t-1, t-2, t-3$) | Prevents stockouts & warehouse overstocking |
| 🏭 **Regional & Carrier Bottlenecks** | Databricks Gold Tables | Delivery status ratios, regional performance, days of cover | Highlights underperforming carrier routes |

---

## 3. High-Level System Architecture

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

## 4. Documentation Index

- [01 Architecture and Vision](01-architecture-and-vision.md)
- [02 Machine Learning Engine](02-machine-learning-engine.md)
- [03 Live Data Injection Pipeline](03-live-data-injection-pipeline.md)
- [04 Backend and API Reference](04-backend-and-api-reference.md)
- [05 Frontend Dashboard](05-frontend-dashboard.md)
- [06 FAQ and Troubleshooting](06-faq-and-troubleshooting.md)
