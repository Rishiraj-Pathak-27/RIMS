import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { predictDemandML, type DemandForecastRequest, type DemandForecastResponse } from "@/services/ml";
import { TrendingUp, Sparkles, BarChart3, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const PRESETS: { name: string; desc: string; data: DemandForecastRequest }[] = [
  {
    name: "Q4 Peak Season",
    desc: "Historical Q4 uptrend (4675, 4146, 4823)",
    data: { lag_1: 4675, lag_2: 4146, lag_3: 4823, month: 10 },
  },
  {
    name: "Q1 Post-Holiday",
    desc: "Post-holiday drop (3200, 4800, 5100)",
    data: { lag_1: 3200, lag_2: 4800, lag_3: 5100, month: 1 },
  },
  {
    name: "Mid-Year Steady",
    desc: "Consistent summer volume (3800, 3750, 3900)",
    data: { lag_1: 3800, lag_2: 3750, lag_3: 3900, month: 6 },
  },
];

export function DemandForecasterCard() {
  const [formData, setFormData] = useState<DemandForecastRequest>({
    lag_1: 4675,
    lag_2: 4146,
    lag_3: 4823,
    month: 10,
  });

  const mutation = useMutation<DemandForecastResponse, Error, DemandForecastRequest>({
    mutationFn: predictDemandML,
  });

  const handleInputChange = (key: keyof DemandForecastRequest, value: number) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handlePresetSelect = (presetData: DemandForecastRequest) => {
    setFormData(presetData);
    mutation.mutate(presetData);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(formData);
  };

  const result = mutation.data;
  const rollingMean = (formData.lag_1 + formData.lag_2 + formData.lag_3) / 3;

  return (
    <div className="rounded-lg border border-border bg-surface shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border px-5 py-4 bg-muted/20 gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
              Live ML Demand Forecaster
              <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary border border-primary/20">
                Random Forest Regressor
              </span>
            </h3>
            <p className="text-xs text-muted-foreground">
              Predict next month's product demand based on 3-month historical lag features
            </p>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => handlePresetSelect(p.data)}
              className="rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              title={p.desc}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      <div className="p-5 grid gap-6 xl:grid-cols-12">
        {/* Form Inputs */}
        <form onSubmit={handleSubmit} className="xl:col-span-7 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3 text-xs">
            <div>
              <label className="block font-medium text-muted-foreground mb-1">
                Lag 1 (Previous Month)
              </label>
              <input
                type="number"
                value={formData.lag_1}
                onChange={(e) => handleInputChange("lag_1", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">
                Lag 2 (2 Months Ago)
              </label>
              <input
                type="number"
                value={formData.lag_2}
                onChange={(e) => handleInputChange("lag_2", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block font-medium text-muted-foreground mb-1">
                Lag 3 (3 Months Ago)
              </label>
              <input
                type="number"
                value={formData.lag_3}
                onChange={(e) => handleInputChange("lag_3", parseFloat(e.target.value) || 0)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 text-xs">
            <div>
              <label className="block font-medium text-muted-foreground mb-1">Forecast Target Month</label>
              <select
                value={formData.month}
                onChange={(e) => handleInputChange("month", parseInt(e.target.value))}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {MONTH_NAMES.map((m, idx) => (
                  <option key={m} value={idx + 1}>
                    {m} (Month {idx + 1})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col justify-end">
              <div className="rounded-md border border-border bg-muted/20 px-3 py-1.5 text-xs text-muted-foreground flex items-center justify-between">
                <span>3-Month Rolling Average:</span>
                <span className="font-semibold text-foreground">{Math.round(rollingMean)}</span>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? (
              <>Running Random Forest Regressor...</>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" /> Forecast Demand
              </>
            )}
          </button>
        </form>

        {/* Prediction Results */}
        <div className="xl:col-span-5 border-t xl:border-t-0 xl:border-l border-border pt-5 xl:pt-0 xl:pl-6 flex flex-col justify-between">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Demand Forecast Result
            </h4>

            {mutation.isError && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-xs text-destructive">
                <AlertTriangle className="h-4 w-4 inline mr-1.5" />
                {mutation.error.message}
              </div>
            )}

            {!result && !mutation.isPending && !mutation.isError && (
              <div className="rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
                Enter historical demand values or select a preset and click <strong>"Forecast Demand"</strong> to get the ML prediction.
              </div>
            )}

            {mutation.isPending && (
              <div className="space-y-3 p-4 rounded-md border border-primary/20 bg-primary/5 animate-pulse text-xs">
                <div className="h-4 bg-primary/20 rounded w-1/2"></div>
                <div className="h-8 bg-primary/20 rounded w-3/4"></div>
              </div>
            )}

            {result && (
              <div className="space-y-4">
                <div className="rounded-lg border border-primary/30 bg-primary/10 p-4">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-primary block">
                    Predicted Demand ({MONTH_NAMES[formData.month - 1]})
                  </span>
                  <span className="text-3xl font-bold tracking-tight text-foreground">
                    {result.predicted_demand.toLocaleString()}
                    <span className="text-xs font-normal text-muted-foreground"> units</span>
                  </span>
                </div>

                <div className="rounded-md border border-border bg-background p-3 text-xs space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>3-Month Rolling Average:</span>
                    <span className="font-medium text-foreground">{result.rolling_mean_3.toLocaleString()}</span>
                  </div>

                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>Trend vs Rolling Mean:</span>
                    <span
                      className={cn(
                        "font-semibold flex items-center gap-1",
                        result.predicted_demand >= result.rolling_mean_3
                          ? "text-emerald-500"
                          : "text-amber-500"
                      )}
                    >
                      <BarChart3 className="h-3.5 w-3.5" />
                      {((result.predicted_demand - result.rolling_mean_3) / result.rolling_mean_3 * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <p className="text-[10px] text-muted-foreground text-center pt-4 border-t border-border mt-4">
            Model: Random Forest Regressor (`demand_forecasting_model.pkl`)
          </p>
        </div>
      </div>
    </div>
  );
}
