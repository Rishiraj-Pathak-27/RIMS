# 05 — Frontend Dashboard (`Final_App/Frontend`)

## Overview
The frontend is a single-page React 18 application built with Vite, TypeScript, and TailwindCSS. It provides interactive charts (via Recharts), live streaming risk feeds (via SSE), Databricks analytics views, and an AI assistant drawer.

---

## Directory Structure

```
Final_App/Frontend/
├── src/
│   ├── components/
│   │   ├── charts/
│   │   │   ├── forecast-chart.tsx    # Demand Forecast chart with live stream overlay
│   │   │   ├── risk-chart.tsx        # Risk breakdown chart & live risk timeline
│   │   │   ├── inventory-chart.tsx   # Product inventory stock levels & days of cover
│   │   │   └── shipment-chart.tsx    # Daily shipment volume & carrier breakdown
│   │   ├── ml/
│   │   │   ├── demand-forecaster-card.tsx # Interactive demand prediction card
│   │   │   └── risk-predictor-card.tsx    # Interactive risk calculation & anomaly alert card
│   │   ├── ui/                       # Shadcn UI primitives (Button, Card, Badge, Dialog, etc.)
│   │   └── chatbot/                  # AI RAG assistant chat drawer component
│   ├── services/
│   │   ├── api.ts                    # Base fetch API wrapper
│   │   ├── ml.ts                     # REST client for ML prediction endpoints
│   │   ├── pipeline.ts               # SSE EventSource listener for live pipeline stream
│   │   ├── dashboard.ts              # REST client for Databricks summary endpoints
│   │   ├── inventory.ts              # REST client for inventory endpoints
│   │   └── shipments.ts              # REST client for logistics endpoints
│   ├── store/                        # Zustand global state stores
│   │   ├── dashboard-store.ts        # Dashboard metrics state & refresh logic
│   │   └── chatbot-store.ts          # Chat drawer state & conversation history
│   ├── routes/                       # React TanStack router views
│   │   ├── index.tsx                 # Main Executive Overview Dashboard
│   │   ├── forecasting.tsx           # Demand Intelligence & ML Forecasting View
│   │   ├── risk-analysis.tsx         # Risk Analysis & Anomaly Matrix View
│   │   ├── inventory.tsx             # Inventory & Stock Monitoring View
│   │   ├── shipments.tsx             # Logistics & Shipment Tracker View
│   │   └── ai-assistant.tsx          # Standalone AI RAG Assistant View
│   ├── styles.css                    # TailwindCSS & global styles
│   └── main.tsx                      # App entry point
├── package.json
└── vite.config.ts
```

---

## Key Frontend Features & Bindings

### 1. Live SSE Stream Connection (`pipeline.ts`)
The `pipeline.ts` service creates a persistent browser `EventSource` connection to `GET /api/pipeline/stream`.
- Listens for incoming 10-second JSON ticks.
- Updates global state stores, appending new data points to Recharts graphs in real time without triggering full-page re-renders.

### 2. Interactive ML Predictor Cards (`components/ml/`)
- Allows users to enter custom parameter values or trigger sample payloads directly from the dashboard UI.
- Displays immediate visual feedback (e.g. `Low`, `Medium`, or `High` risk badges, anomaly status badges, and predicted demand counts).

### 3. Responsive UI & Navigation
- Built using Lucide icons, TailwindCSS styling, dark mode support, and TanStack Router for route switching.
