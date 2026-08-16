import type {
  ActivityEvent,
  AIInsight,
  AutonomousDecision,
  KpiMetric,
  WarehouseUtil,
} from "@/types/dashboard";
import type { InventoryItem } from "@/types/inventory";
import type { ForecastPoint, RiskPoint, ShipmentRecord } from "@/types/prediction";

export interface ShipmentStat {
  label: string;
  value: string;
}

export interface DashboardSummary {
  kpiMetrics: KpiMetric[];
  activityFeed: ActivityEvent[];
  aiInsights: AIInsight[];
  autonomousDecisions: AutonomousDecision[];
  warehouseUtilization: WarehouseUtil[];
  shipmentStats: ShipmentStat[];
}

export type LogisticsStatusKey = "delivered" | "inTransit" | "delayed" | "atRisk" | "returned";

export interface LogisticsSlice {
  key: LogisticsStatusKey;
  name: string;
  value: number;
  operationalNote: string;
}

export interface MonthLogisticsEntry {
  id: string;
  label: string;
  slices: LogisticsSlice[];
  footerInsight: string;
  source?: "historical" | "sample" | "live";
}

export interface MonthlyLogisticsResponse {
  monthOrder: string[];
  byMonth: Record<string, MonthLogisticsEntry>;
}

export interface InventoryHistoryPoint {
  month: string;
  healthy: number;
  low: number;
  critical: number;
  overstock: number;
}

export interface DemandKpi {
  label: string;
  value: string;
  trend: string;
  trendPositive?: boolean;
  icon?: "activity" | "brain" | "gauge" | "trend";
}

export interface ModelConfidence {
  label: string;
  score: number;
  detail?: string;
}

export interface ForecastScenario {
  name: string;
  impact: string;
  desc: string;
  tone: string;
}

export interface DemandIntelligence {
  forecastSeries: ForecastPoint[];
  inventoryHistory: InventoryHistoryPoint[];
  accuracy: string;
  kpiStrip: DemandKpi[];
  modelConfidence: ModelConfidence[];
  scenarios: ForecastScenario[];
}

export interface InventoryResponse {
  items: InventoryItem[];
  history: InventoryHistoryPoint[];
}

export interface ShipmentVolumePoint {
  day: string;
  onTime: number;
  delayed: number;
  atRisk: number;
}

export interface ShipmentsResponse {
  shipments: ShipmentRecord[];
  stats: ShipmentStat[];
  volume: ShipmentVolumePoint[];
}

export interface RiskTrendPoint {
  week: string;
  risk: number;
}

export interface RegionalPerformance {
  riskMatrix: RiskPoint[];
  riskTrend: RiskTrendPoint[];
  regions: Array<{
    region: string;
    orders: number;
    onTimeDelivery: number;
    revenue: number;
    profit: number;
  }>;
  summary: {
    highExposure: number;
    networkRisk: number;
    anomalies: number;
    resolved: number;
    reviewing: number;
  };
}

export interface RevenueTrendsResponse {
  trends: Array<{
    period: string;
    revenue: number;
    profit: number;
    orders: number;
  }>;
}
