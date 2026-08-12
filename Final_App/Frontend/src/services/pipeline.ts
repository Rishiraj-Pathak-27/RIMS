import { API_BASE_URL } from "@/services/api";

// ─── Types ──────────────────────────────────────────────────────────

export interface LiveRiskTick {
  tick: string;
  timestamp: string;
  order_summary: {
    segment: string;
    market: string;
    sales: number;
    quantity: number;
    shipping_mode: string;
    lead_time: number;
    defect_rate: number;
  };
  delivery_risk: number;
  anomaly_prediction: string;
  anomaly_score: number;
  anomaly_risk: number;
  supply_chain_risk: number;
  risk_category: "Low" | "Medium" | "High";
}

export interface LiveDemandTick {
  tick: string;
  timestamp: string;
  lag_1: number;
  lag_2: number;
  lag_3: number;
  month: number;
  predicted_demand: number;
  rolling_mean_3: number;
}

export interface PipelineTickEvent {
  type: "pipeline_tick";
  tick: string;
  timestamp: string;
  risk: LiveRiskTick;
  demand: LiveDemandTick;
}

export interface PipelineInitEvent {
  type: "init";
  risk_history: LiveRiskTick[];
  demand_history: LiveDemandTick[];
}

export type PipelineEvent = PipelineTickEvent | PipelineInitEvent;

// ─── SSE Stream ─────────────────────────────────────────────────────

export type PipelineListener = (event: PipelineEvent) => void;

/**
 * Connect to the live data injection pipeline SSE stream.
 * Returns an unsubscribe function to close the connection.
 */
export function subscribeToPipeline(onEvent: PipelineListener): () => void {
  const url = `${API_BASE_URL}/api/pipeline/stream`;
  const source = new EventSource(url);

  source.onmessage = (msg) => {
    try {
      const parsed: PipelineEvent = JSON.parse(msg.data);
      onEvent(parsed);
    } catch {
      // Ignore parse errors (keepalive comments, etc.)
    }
  };

  source.onerror = () => {
    // EventSource auto-reconnects; we just let it retry
  };

  return () => {
    source.close();
  };
}
