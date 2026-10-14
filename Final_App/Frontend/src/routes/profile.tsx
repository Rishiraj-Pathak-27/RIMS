import { createFileRoute } from "@tanstack/react-router";
import {
  BarChart3,
  BellRing,
  Boxes,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileText,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Truck,
  UserRound,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [{ title: "Profile · RIMS" }],
  }),
  component: Profile,
});

const metrics = [
  {
    label: "Reports viewed",
    value: "124",
    change: "+12%",
    icon: FileText,
    tone: "text-chart-2 bg-chart-2/10",
  },
  {
    label: "Shipments tracked",
    value: "56",
    change: "+18%",
    icon: Truck,
    tone: "text-success bg-success/10",
  },
  {
    label: "Forecasts reviewed",
    value: "23",
    change: "+9%",
    icon: TrendingUp,
    tone: "text-warning bg-warning/10",
  },
  {
    label: "Active alerts",
    value: "4",
    change: "Needs review",
    icon: BellRing,
    tone: "text-destructive bg-destructive/10",
  },
] as const;

const accessModules = [
  { label: "Overview", icon: BarChart3 },
  { label: "Inventory", icon: Boxes },
  { label: "Forecasting", icon: TrendingUp },
  { label: "Shipments", icon: Truck },
  { label: "Risk analysis", icon: ShieldCheck },
  { label: "AI assistant", icon: Sparkles },
] as const;

function Profile() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 pb-8">
      <PageHeader
        title="User Profile"
        description="Your operations identity, access, and workspace activity."
      />

      <section
        className="rounded-md border border-border/70 bg-surface p-5 sm:p-6"
        aria-label="Profile summary"
      >
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
          <div className="flex min-w-0 flex-1 items-center gap-4">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border border-border bg-primary-soft text-xl font-semibold text-foreground">
              AK
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-semibold tracking-tight text-foreground">Alex Kim</h2>
                <Badge className="border-success/30 bg-success/10 text-success" variant="outline">
                  Active
                </Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Operations Manager · Supply Chain Control
              </p>
              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" /> alex.kim@rims.local
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Phone className="h-3.5 w-3.5" /> +1 415 555 0148
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" /> San Francisco, CA
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-6 border-t border-border/60 pt-5 text-xs lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
            <div className="flex gap-2.5">
              <CalendarDays className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Member since</p>
                <p className="mt-1 font-medium text-foreground">October 2024</p>
              </div>
            </div>
            <div className="flex gap-2.5">
              <Clock3 className="mt-0.5 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Last sign-in</p>
                <p className="mt-1 font-medium text-foreground">Today, 18:57</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Profile metrics"
      >
        {metrics.map(({ label, value, change, icon: Icon, tone }) => (
          <div key={label} className="rounded-md border border-border/70 bg-surface p-4">
            <div className="flex items-start justify-between gap-3">
              <span className={`flex h-9 w-9 items-center justify-center rounded-md ${tone}`}>
                <Icon className="h-4.5 w-4.5" />
              </span>
              <span className="text-[11px] font-medium text-success">{change}</span>
            </div>
            <p className="mt-4 text-2xl font-semibold tabular-nums text-foreground">{value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{label}</p>
          </div>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-md border border-border/70 bg-surface">
          <div className="flex items-center gap-2 border-b border-border/60 px-5 py-4">
            <UserRound className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">Personal information</h2>
          </div>
          <dl className="grid grid-cols-[8rem_1fr] gap-x-4 gap-y-4 p-5 text-sm">
            <dt className="text-muted-foreground">Full name</dt>
            <dd className="font-medium text-foreground">Alex Kim</dd>
            <dt className="text-muted-foreground">Role</dt>
            <dd className="text-foreground">Operations Manager</dd>
            <dt className="text-muted-foreground">Email</dt>
            <dd className="text-foreground">alex.kim@rims.local</dd>
            <dt className="text-muted-foreground">Phone</dt>
            <dd className="text-foreground">+1 415 555 0148</dd>
            <dt className="text-muted-foreground">Location</dt>
            <dd className="text-foreground">San Francisco, California</dd>
            <dt className="text-muted-foreground">Team</dt>
            <dd className="text-foreground">Global Operations</dd>
          </dl>
        </div>

        <div className="rounded-md border border-border/70 bg-surface">
          <div className="flex items-center gap-2 border-b border-border/60 px-5 py-4">
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold text-foreground">System access</h2>
          </div>
          <div className="p-5">
            <div className="flex items-center gap-2 rounded-md border border-success/20 bg-success/10 px-3 py-2 text-xs text-success">
              <CheckCircle2 className="h-4 w-4" /> Your account has access to the following modules.
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {accessModules.map(({ label, icon: Icon }) => (
                <div
                  key={label}
                  className="flex items-center gap-2 rounded-md border border-border/60 bg-surface-muted px-3 py-2 text-xs text-foreground"
                >
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" /> {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
