import { fetchJson } from "@/services/api";

export interface OrderRiskRequest {
  product_id: number;
  customer_id: number;
  customer_segment: string;
  sales: number;
  quantity: number;
  shipping_mode: string;
  market: string;
  lead_time: number;
  avg_order_value_30d: number;
  num_orders_30d: number;
  is_high_value: number;
  is_bulk_order: number;
  day_of_week: number;
  month: number;
  quarter: number;
  year: number;
  department: string;
  class: string;
  profit: number;
  order_processing_days: number;
  avg_lead_time_by_mode: number;
  avg_shipping_cost: number;
  avg_defect_rate: number;
  max_defect_rate: number;
  profit_margin: number;
}

export interface OrderRiskResponse {
  delivery_risk: number;
  anomaly_prediction: string;
  anomaly_score: number;
  anomaly_risk: number;
  supply_chain_risk: number;
  risk_category: "Low" | "Medium" | "High";
}

export interface DemandForecastRequest {
  lag_1: number;
  lag_2: number;
  lag_3: number;
  month: number;
}

export interface DemandForecastResponse {
  predicted_demand: number;
  rolling_mean_3: number;
}

export interface MLStatusResponse {
  status: string;
  models_loaded: boolean;
  models: string[];
}

export function getMLStatus(): Promise<MLStatusResponse> {
  return fetchJson<MLStatusResponse>("/api/ml/status");
}

export function predictOrderRisk(data: OrderRiskRequest): Promise<OrderRiskResponse> {
  return fetchJson<OrderRiskResponse>("/api/ml/predict-risk", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function predictDemandML(data: DemandForecastRequest): Promise<DemandForecastResponse> {
  return fetchJson<DemandForecastResponse>("/api/ml/predict-demand", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
