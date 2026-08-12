import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  Line,
  ComposedChart,
  Area,
} from "recharts";
import { getRegionalPerformance } from "@/services/risk";
import type { RiskPoint } from "@/types/prediction";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/common/data-state";
import { cn } from "@/lib/utils";
import { Radio, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";
import {
  subscribeToPipeline,
  type LiveRiskTick,
  type PipelineEvent,
} from "@/services/pipeline";

function colorFor(v: number) {
  if (v > 60) return "var(--color-destructive)";
  if (v > 45) return "var(--color-warning)";
  return "var(--color-primary)";
}

interface LiveRiskPoint {
  tick: string;
  supply_chain_risk: number;
  delivery_risk: number;
  anomaly_risk: number;
  anomaly_prediction: string;
  risk_category: string;
  segment: string;
  market: string;
}

const MAX_LIVE_RISK = 20;

export function RiskChart({
  data: overrideData,
  height = 340,
}: {
  data?: RiskPoint[];
  height?: number;
}) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["regional-performance"],
    queryFn: getRegionalPerformance,
    enabled: !overrideData,
    staleTime: 60_000,
  });

  const [liveRiskPoints, setLiveRiskPoints] = useState<LiveRiskPoint[]>([]);
  const [tickCount, setTickCount] = useState(0);

  // Subscribe to live pipeline SSE
  useEffect(() => {
    const unsub = subscribeToPipeline((event: PipelineEvent) => {
      if (event.type === "init" && event.risk_history) {
        const points = event.risk_history.map((r: LiveRiskTick) => ({
          tick: r.tick,
          supply_chain_risk: r.supply_chain_risk,
          delivery_risk: r.delivery_risk,
          anomaly_risk: r.anomaly_risk,
          anomaly_prediction: r.anomaly_prediction,
          risk_category: r.risk_category,
          segment: r.order_summary.segment,
          market: r.order_summary.market,
        }));
        setLiveRiskPoints(points.slice(-MAX_LIVE_RISK));
        setTickCount((c) => c + 1);
      }

      if (event.type === "pipeline_tick") {
        const r = event.risk;
        setLiveRiskPoints((prev) => {
          const next = [
            ...prev,
            {
              tick: r.tick,
              supply_chain_risk: r.supply_chain_risk,
              delivery_risk: r.delivery_risk,
              anomaly_risk: r.anomaly_risk,
              anomaly_prediction: r.anomaly_prediction,
              risk_category: r.risk_category,
              segment: r.order_summary.segment,
              market: r.order_summary.market,
            },
          ];
          return next.slice(-MAX_LIVE_RISK);
        });
        setTickCount((c) => c + 1);
      }
    });

    return unsub;
  }, []);

  const riskMatrix = overrideData ?? data?.riskMatrix ?? [];
  const latestLive = liveRiskPoints.length > 0 ? liveRiskPoints[liveRiskPoints.length - 1] : null;

  if (!overrideData && isLoading) return <LoadingBlock />;
  if (!overrideData && error) return <ErrorBlock error={error} onRetry={() => refetch()} />;
  if (!riskMatrix.length && !liveRiskPoints.length) return <EmptyBlock />;

  return (
    <div className="rounded-md border border-border bg-surface overflow-hidden space-y-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border px-5 py-3.5 gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            Risk by Category
            {liveRiskPoints.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <Radio className="h-3 w-3 animate-pulse" /> Live
              </span>
            )}
          </h3>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Probability × impact, 0–100
          </p>
        </div>
        <div className="flex items-center gap-2">
          {latestLive && (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[11px] font-semibold text-white",
                latestLive.risk_category === "High"
                  ? "bg-red-500"
                  : latestLive.risk_category === "Medium"
                  ? "bg-amber-500"
                  : "bg-emerald-500"
              )}
            >
              Latest: {latestLive.supply_chain_risk} ({latestLive.risk_category})
            </span>
          )}
          <span className="text-[11px] text-muted-foreground">{riskMatrix.length} categories</span>
        </div>
      </div>

      {/* Static Risk Bar Chart */}
      <div className="p-3" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={riskMatrix}
            layout="vertical"
            margin={{ top: 10, right: 16, left: 16, bottom: 0 }}
          >
            <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              domain={[0, 100]}
            />
            <YAxis
              dataKey="category"
              type="category"
              tick={{ fontSize: 11, fill: "var(--color-foreground)" }}
              axisLine={false}
              tickLine={false}
              width={130}
            />
            <Tooltip
              contentStyle={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
                boxShadow: "none",
              }}
            />
            <Bar dataKey="exposure" radius={[0, 6, 6, 0]} barSize={18}>
              {riskMatrix.map((r) => (
                <Cell key={r.category} fill={colorFor(r.exposure)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Live ML Risk Timeline */}
      {liveRiskPoints.length > 0 && (
        <div className="border-t border-border">
          <div className="px-5 py-3 flex items-center justify-between">
            <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-emerald-500" />
              Live ML Risk Stream
              <span className="text-muted-foreground font-normal">(updated every 10s)</span>
            </h4>
            <span className="text-[11px] text-muted-foreground">{liveRiskPoints.length} ticks</span>
          </div>
          <div className="px-3 pb-3" style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={liveRiskPoints}
                margin={{ top: 8, right: 12, left: 4, bottom: 4 }}
              >
                <defs>
                  <linearGradient id="liveRiskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke="var(--color-border)"
                  strokeDasharray="3 3"
                  vertical={false}
                  strokeOpacity={0.5}
                />
                <XAxis
                  dataKey="tick"
                  tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                  width={32}
                  domain={[0, 100]}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const row = payload[0].payload as LiveRiskPoint;
                    return (
                      <div className="rounded-md border border-border bg-surface px-3 py-2.5 text-xs shadow-lg space-y-1.5">
                        <p className="font-semibold text-foreground flex items-center justify-between gap-4">
                          <span>{row.tick}</span>
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-[10px] font-semibold text-white",
                              row.risk_category === "High"
                                ? "bg-red-500"
                                : row.risk_category === "Medium"
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                            )}
                          >
                            {row.risk_category}
                          </span>
                        </p>
                        <div className="text-[11px] space-y-0.5">
                          <p className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Supply Chain Risk:</span>
                            <span className="font-semibold">{row.supply_chain_risk}</span>
                          </p>
                          <p className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Delivery Risk:</span>
                            <span>{row.delivery_risk}%</span>
                          </p>
                          <p className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Anomaly Risk:</span>
                            <span>{row.anomaly_risk}%</span>
                          </p>
                          <p className="flex justify-between gap-4">
                            <span className="text-muted-foreground">Anomaly:</span>
                            <span className={cn(
                              "font-semibold flex items-center gap-1",
                              row.anomaly_prediction === "Anomaly"
                                ? "text-red-500"
                                : "text-emerald-500"
                            )}>
                              {row.anomaly_prediction === "Anomaly" ? (
                                <AlertTriangle className="h-3 w-3" />
                              ) : (
                                <CheckCircle2 className="h-3 w-3" />
                              )}
                              {row.anomaly_prediction}
                            </span>
                          </p>
                          <p className="flex justify-between gap-4 pt-1 border-t border-border/50 text-muted-foreground">
                            <span>{row.segment}</span>
                            <span>{row.market}</span>
                          </p>
                        </div>
                      </div>
                    );
                  }}
                />

                {/* Threshold line at 60 (High risk boundary) */}
                <Area
                  type="monotone"
                  dataKey="supply_chain_risk"
                  stroke="none"
                  fill="url(#liveRiskGrad)"
                  fillOpacity={1}
                  isAnimationActive
                  animationDuration={400}
                />
                <Line
                  type="monotone"
                  dataKey="supply_chain_risk"
                  name="Supply Chain Risk"
                  stroke="#ef4444"
                  strokeWidth={2.5}
                  dot={{
                    r: 4,
                    fill: "#ef4444",
                    stroke: "#fff",
                    strokeWidth: 2,
                  }}
                  activeDot={{
                    r: 6,
                    fill: "#ef4444",
                    stroke: "#fff",
                    strokeWidth: 3,
                  }}
                  isAnimationActive
                  animationDuration={500}
                />
                <Line
                  type="monotone"
                  dataKey="delivery_risk"
                  name="Delivery Risk"
                  stroke="var(--color-primary)"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  dot={false}
                  isAnimationActive
                  animationDuration={500}
                />
                <Line
                  type="monotone"
                  dataKey="anomaly_risk"
                  name="Anomaly Risk"
                  stroke="#a855f7"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  dot={false}
                  isAnimationActive
                  animationDuration={500}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
