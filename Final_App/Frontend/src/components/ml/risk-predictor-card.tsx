import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { predictOrderRisk, type OrderRiskRequest, type OrderRiskResponse } from "@/services/ml";
import { ShieldAlert, AlertTriangle, CheckCircle2, Cpu, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const DEFAULT_ORDER: OrderRiskRequest = {
  product_id: 365,
  customer_id: 2,
  customer_segment: "Consumer",
  sales: 119.98,
  quantity: 2,
  shipping_mode: "Standard Class",
  market: "LATAM",
  lead_time: 10,
  avg_order_value_30d: 119.98,
  num_orders_30d: 1,
  is_high_value: 0,
  is_bulk_order: 0,
  day_of_week: 3,
  month: 1,
  quarter: 1,
  year: 2017,
  department: "Technology",
  class: "Regular Air",
  profit: 20.0,
  order_processing_days: 2,
  avg_lead_time_by_mode: 10.0,
  avg_shipping_cost: 5.0,
  avg_defect_rate: 1.0,
  max_defect_rate: 2.0,
  profit_margin: 0.17,
};

const PRESETS: { name: string; desc: string; data: Partial<OrderRiskRequest> }[] = [
  {
    name: "Standard Consumer Order",
    desc: "Typical regular order with low lead time & normal defect rates.",
    data: { ...DEFAULT_ORDER },
  },
  {
    name: "High-Value Corporate Rush",
    desc: "Large corporate order with long lead times & tight processing window.",
    data: {
      ...DEFAULT_ORDER,
      customer_segment: "Corporate",
      sales: 2450.0,
      quantity: 15,
      shipping_mode: "First Class",
      is_high_value: 1,
      is_bulk_order: 1,
      lead_time: 25,
      profit: 420.0,
      avg_defect_rate: 4.5,
      max_defect_rate: 8.0,
      order_processing_days: 5,
    },
  },
  {
    name: "High-Risk Anomaly Order",
    desc: "Anomalous order with zero profit, high defect rate & unusual metrics.",
    data: {
      ...DEFAULT_ORDER,
      sales: 4999.0,
      quantity: 50,
      lead_time: 45,
      profit: -150.0,
      avg_defect_rate: 12.0,
      max_defect_rate: 25.0,
      profit_margin: -0.05,
      order_processing_days: 10,
    },
  },
];

export function RiskPredictorCard() {
  const [formData, setFormData] = useState<OrderRiskRequest>(DEFAULT_ORDER);

  const mutation = useMutation<OrderRiskResponse, Error, OrderRiskRequest>({
    mutationFn: predictOrderRisk,
  });

  const handleChange = (key: keyof OrderRiskRequest, value: string | number) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handlePresetSelect = (presetData: Partial<OrderRiskRequest>) => {
    const updated = { ...DEFAULT_ORDER, ...presetData };
    setFormData(updated);
    mutation.mutate(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  const result = mutation.data;

  return (
    <div className="rounded-lg border border-border bg-surface shadow-sm transition-all overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border px-5 py-4 bg-muted/20 gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              Live ML Order Risk Predictor
              <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary border border-primary/20">
                HF Model Connected
              </span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Random Forest Classifier + Isolation Forest model combined inference
            </p>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {PRESETS.map((preset) => (
            <button
              key={preset.name}
              type="button"
              onClick={() => handlePresetSelect(preset.data)}
              className="rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              title={preset.desc}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5 grid gap-6 xl:grid-cols-12">
        {/* Input Form */}
        <form onSubmit={handleSubmit} className="xl:col-span-7 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3 text-xs">
            <div>
              <label className="block font-medium text-muted-foreground mb-1">Customer Segment</label>
              <select
                value={formData.customer_segment}
                onChange={(e) => handleChange("customer_segment", e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="Consumer">Consumer</option>
                <option value="Corporate">Corporate</option>
                <option value="Home Office">Home Office</option>
              </select>
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Shipping Mode</label>
              <select
                value={formData.shipping_mode}
                onChange={(e) => handleChange("shipping_mode", e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="Standard Class">Standard Class</option>
                <option value="Second Class">Second Class</option>
                <option value="First Class">First Class</option>
                <option value="Same Day">Same Day</option>
              </select>
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Market Region</label>
              <select
                value={formData.market}
                onChange={(e) => handleChange("market", e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="LATAM">LATAM</option>
                <option value="Europe">Europe</option>
                <option value="USCA">USCA</option>
                <option value="Asia Pacific">Asia Pacific</option>
                <option value="Africa">Africa</option>
              </select>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-4 text-xs">
            <div>
              <label className="block font-medium text-muted-foreground mb-1">Sales ($)</label>
              <input
                type="number"
                step="0.01"
                value={formData.sales}
                onChange={(e) => handleChange("sales", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Quantity</label>
              <input
                type="number"
                value={formData.quantity}
                onChange={(e) => handleChange("quantity", parseInt(e.target.value) || 1)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Lead Time (days)</label>
              <input
                type="number"
                value={formData.lead_time}
                onChange={(e) => handleChange("lead_time", parseInt(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Profit ($)</label>
              <input
                type="number"
                step="0.01"
                value={formData.profit}
                onChange={(e) => handleChange("profit", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 text-xs">
            <div>
              <label className="block font-medium text-muted-foreground mb-1">Avg Defect Rate (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.avg_defect_rate}
                onChange={(e) => handleChange("avg_defect_rate", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Max Defect Rate (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.max_defect_rate}
                onChange={(e) => handleChange("max_defect_rate", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">Processing Days</label>
              <input
                type="number"
                value={formData.order_processing_days}
                onChange={(e) => handleChange("order_processing_days", parseInt(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={mutation.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {mutation.isPending ? (
                <>Calculating ML Risk...</>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" /> Predict Supply Chain Risk
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => {
                setFormData(DEFAULT_ORDER);
                mutation.reset();
              }}
              className="inline-flex items-center gap-1 rounded-md border border-input bg-background px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-accent"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Reset Form
            </button>
          </div>
        </form>

        {/* Prediction Results Display */}
        <div className="xl:col-span-5 border-t xl:border-t-0 xl:border-l border-border pt-5 xl:pt-0 xl:pl-6 flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              ML Inference Output
            </h4>

            {mutation.isError && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-xs text-destructive">
                <AlertTriangle className="h-4 w-4 inline mr-1.5" />
                {mutation.error.message}
              </div>
            )}

            {!result && !mutation.isPending && !mutation.isError && (
              <div className="rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
                Click <strong>"Predict Supply Chain Risk"</strong> or choose a preset to evaluate order risk metrics in real-time.
              </div>
            )}

            {mutation.isPending && (
              <div className="space-y-3 p-4 rounded-md border border-primary/20 bg-primary/5 animate-pulse text-xs">
                <div className="h-4 bg-primary/20 rounded w-3/4"></div>
                <div className="h-8 bg-primary/20 rounded w-1/2"></div>
                <div className="h-4 bg-primary/20 rounded w-full"></div>
              </div>
            )}

            {result && (
              <div className="space-y-4">
                {/* Overall Score Banner */}
                <div
                  className={cn(
                    "rounded-lg p-4 border flex items-center justify-between",
                    result.risk_category === "High"
                      ? "border-destructive/40 bg-destructive/10 text-destructive-foreground"
                      : result.risk_category === "Medium"
                      ? "border-warning/40 bg-warning/10 text-warning-foreground"
                      : "border-success/40 bg-success/10 text-success-foreground"
                  )}
                >
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider block">
                      Supply Chain Risk
                    </span>
                    <span className="text-3xl font-bold tracking-tight">
                      {result.supply_chain_risk}
                      <span className="text-xs font-normal"> / 100</span>
                    </span>
                  </div>

                  <div className="text-right">
                    <span
                      className={cn(
                        "inline-block rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider",
                        result.risk_category === "High"
                          ? "bg-destructive text-white"
                          : result.risk_category === "Medium"
                          ? "bg-amber-500 text-white"
                          : "bg-emerald-500 text-white"
                      )}
                    >
                      {result.risk_category} Risk
                    </span>
                    <p className="text-[10px] mt-1 text-muted-foreground">
                      60% Delivery + 40% Anomaly
                    </p>
                  </div>
                </div>

                {/* Sub-Metrics Grid */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-md border border-border bg-background p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-muted-foreground">Delivery Delay Risk</span>
                      <ShieldAlert className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <p className="mt-1 text-lg font-semibold text-foreground">
                      {result.delivery_risk}%
                    </p>
                    <div className="mt-1.5 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-500"
                        style={{ width: `${Math.min(100, result.delivery_risk)}%` }}
                      />
                    </div>
                  </div>

                  <div className="rounded-md border border-border bg-background p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-muted-foreground">Anomaly Risk</span>
                      {result.anomaly_prediction === "Anomaly" ? (
                        <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                      ) : (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                      )}
                    </div>
                    <p className="mt-1 text-lg font-semibold text-foreground">
                      {result.anomaly_risk}%
                    </p>
                    <div className="mt-1.5 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className={cn(
                          "h-full transition-all duration-500",
                          result.anomaly_prediction === "Anomaly" ? "bg-destructive" : "bg-emerald-500"
                        )}
                        style={{ width: `${Math.min(100, result.anomaly_risk)}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Detailed Anomaly Detection Info */}
                <div className="rounded-md border border-border bg-background p-3 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Anomaly Status:</span>
                    <span
                      className={cn(
                        "font-semibold",
                        result.anomaly_prediction === "Anomaly" ? "text-destructive" : "text-emerald-500"
                      )}
                    >
                      {result.anomaly_prediction}
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-muted-foreground">Decision Score:</span>
                    <span className="font-mono text-foreground">{result.anomaly_score}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <p className="text-[10px] text-muted-foreground text-center pt-4 border-t border-border mt-4">
            Model weights loaded directly from HuggingFace (`saniamirza/supply-chain-ml-models`)
          </p>
        </div>
      </div>
    </div>
  );
}
