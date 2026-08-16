import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getShipmentAnalytics } from "@/services/shipments";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "@/components/common/data-state";

const tooltipStyle = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: 8,
  fontSize: 12,
  boxShadow: "none",
};

export function ShipmentChart({ height = 280 }: { height?: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["shipment-analytics"],
    queryFn: getShipmentAnalytics,
    staleTime: 60_000,
  });
  const shipmentVolume = data?.volume ?? [];

  if (isLoading) return <LoadingBlock />;
  if (error) return <ErrorBlock error={error} onRetry={() => refetch()} />;
  if (!shipmentVolume.length) return <EmptyBlock />;

  return (
    <div className="rounded-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Shipment Volume — 7 days</h3>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Historical Gold baseline plus the current live stream through today
          </p>
        </div>
      </div>
      <div className="p-3" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={shipmentVolume} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="onTimeG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.4} />
                <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Area
              type="monotone"
              dataKey="onTime"
              stroke="var(--color-primary)"
              strokeWidth={2}
              fill="url(#onTimeG)"
              name="On Time"
            />
            <Area
              type="monotone"
              dataKey="delayed"
              stroke="var(--color-warning)"
              strokeWidth={2}
              fill="var(--color-warning)"
              fillOpacity={0.15}
              name="Delayed"
            />
            <Area
              type="monotone"
              dataKey="atRisk"
              stroke="var(--color-destructive)"
              strokeWidth={2}
              fill="var(--color-destructive)"
              fillOpacity={0.12}
              name="At Risk"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
