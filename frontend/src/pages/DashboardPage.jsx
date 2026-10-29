import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/api";
import { CrumbSep, Layout } from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const FLOW_COLORS = { backlog: "#9ca3af", started: "#f59e0b", done: "#0f766e" };
const PRIORITY_COLORS = {
  urgent: "#e11d48",
  high: "#ea580c",
  medium: "#0d9488",
  low: "#9ca3af",
};
const ACCENT = "#0f766e";
const CYAN = "#0891b2";
const GRID = "#e4e3df";
const TICK = "#6b6b64";

function Kpi({ label, value, hint, warn }) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card px-4 py-3",
        warn && "border-amber-500/30 bg-amber-500/5",
      )}
    >
      <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
      {hint ? <p className="mt-1 text-[12px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function ChartCard({ title, subtitle, children }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>{title}</CardTitle>
        {subtitle ? <CardDescription>{subtitle}</CardDescription> : null}
      </CardHeader>
      <CardContent className="min-h-[220px]">{children}</CardContent>
    </Card>
  );
}

const tip = {
  background: "#ffffff",
  border: "1px solid #e4e3df",
  borderRadius: 6,
  fontSize: 12,
  color: "#1a1a19",
};

export function DashboardPage() {
  const { orgId = "" } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    setLoading(true);
    setForbidden(false);
    api
      .adminDashboard(orgId)
      .then(setData)
      .catch((e) => {
        const msg = String(e.message).toLowerCase();
        if (msg.includes("permission") || msg.includes("403") || msg.includes("forbidden")) {
          setForbidden(true);
        } else setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [orgId]);

  const flowData = useMemo(
    () => Object.entries(data?.by_category || {}).map(([name, value]) => ({ name, value })),
    [data],
  );
  const priorityData = useMemo(
    () =>
      ["urgent", "high", "medium", "low"].map((name) => ({
        name,
        value: data?.by_priority?.[name] || 0,
      })),
    [data],
  );
  const workloadData = useMemo(
    () =>
      (data?.workload || [])
        .filter((w) => w.open_tasks || w.done_tasks)
        .map((w) => ({
          name: w.name.length > 12 ? `${w.name.slice(0, 11)}…` : w.name,
          open: w.open_tasks,
          done: w.done_tasks,
        })),
    [data],
  );
  const activityData = useMemo(
    () => (data?.activity_series || []).map((d) => ({ ...d, label: d.date.slice(5) })),
    [data],
  );
  const projectData = useMemo(
    () =>
      (data?.project_breakdown || data?.projects || []).map((p) => ({
        name: p.key,
        open: p.open,
        done: p.done,
      })),
    [data],
  );

  if (forbidden) return <Navigate to={`/orgs/${orgId}`} replace />;

  const summary = data?.summary || {};
  const kpis = data?.kpis || {};

  return (
    <Layout
      orgId={orgId}
      title="Insights"
      subtitle="Delivery health"
      crumbs={
        <>
          <Link to="/" className="hover:text-foreground">
            Orgs
          </Link>
          <CrumbSep />
          <Link to={`/orgs/${orgId}`} className="hover:text-foreground">
            Projects
          </Link>
          <CrumbSep />
          <span className="text-foreground/80">Insights</span>
        </>
      }
      actions={
        <Button asChild variant="outline" size="sm">
          <Link to={`/orgs/${orgId}`}>Projects</Link>
        </Button>
      }
    >
      {loading && <p className="text-[13px] text-muted-foreground">Loading…</p>}
      {error && (
        <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Kpi
              label="Completion"
              value={`${kpis.completion_rate ?? 0}%`}
              hint={`${summary.done_tasks}/${summary.total_tasks} done`}
            />
            <Kpi
              label="Risk index"
              value={kpis.risk_index ?? 0}
              hint="Overdue + unassigned + priority pressure"
              warn={(kpis.risk_index || 0) >= 60}
            />
            <Kpi
              label="Overdue rate"
              value={`${kpis.overdue_rate ?? 0}%`}
              hint={`${summary.overdue} past due`}
              warn={(kpis.overdue_rate || 0) > 20}
            />
            <Kpi
              label="14d created"
              value={kpis.throughput_14d ?? 0}
              hint={`${kpis.active_contributors ?? 0} contributors`}
            />
          </div>

          <div className="grid gap-3 xl:grid-cols-2">
            <ChartCard title="Activity" subtitle="Last 14 days">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={activityData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={ACCENT} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={ACCENT} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: TICK }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: TICK }} />
                  <Tooltip contentStyle={tip} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="total" stroke={ACCENT} fill="url(#gTotal)" strokeWidth={2} />
                  <Area type="monotone" dataKey="created" stroke={CYAN} fill="transparent" strokeWidth={1.5} />
                  <Area
                    type="monotone"
                    dataKey="commented"
                    stroke="#64748b"
                    fill="transparent"
                    strokeWidth={1.5}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Flow mix" subtitle="Backlog / started / done">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={flowData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={80}
                    paddingAngle={3}
                  >
                    {flowData.map((e) => (
                      <Cell key={e.name} fill={FLOW_COLORS[e.name] || "#6b7280"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tip} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Priority pressure" subtitle="Open work by priority">
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={priorityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: TICK }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: TICK }} />
                  <Tooltip contentStyle={tip} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {priorityData.map((e) => (
                      <Cell key={e.name} fill={PRIORITY_COLORS[e.name]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Workload" subtitle="Open vs done by person">
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={workloadData} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: TICK }} />
                  <YAxis type="category" dataKey="name" width={84} tick={{ fontSize: 11, fill: TICK }} />
                  <Tooltip contentStyle={tip} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="open" stackId="a" fill="#f59e0b" />
                  <Bar dataKey="done" stackId="a" fill="#34d399" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Project delivery" subtitle="Open vs done by key">
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={projectData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: TICK }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: TICK }} />
                  <Tooltip contentStyle={tip} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="open" stackId="p" fill={ACCENT} />
                  <Bar dataKey="done" stackId="p" fill="#34d399" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Overdue" subtitle="Past-due open issues">
              {data.overdue.length === 0 ? (
                <p className="grid min-h-[160px] place-content-center text-[13px] text-muted-foreground">
                  Nothing overdue.
                </p>
              ) : (
                <div className="divide-y divide-border overflow-hidden rounded-md border border-border">
                  {data.overdue.map((item) => (
                    <Link
                      key={item.id}
                      to={`/projects/${item.project_id}`}
                      className="flex items-center justify-between gap-3 px-3 py-2.5 hover:bg-accent/40"
                    >
                      <div className="min-w-0">
                        <p className="font-mono text-[11px] text-muted-foreground">
                          {item.project_key}-{item.number}
                        </p>
                        <p className="truncate text-[13px]">{item.title}</p>
                      </div>
                      <Badge
                        variant={item.priority === "urgent" ? "danger" : "warning"}
                        className="capitalize"
                      >
                        {item.priority}
                      </Badge>
                    </Link>
                  ))}
                </div>
              )}
            </ChartCard>
          </div>
        </>
      )}
    </Layout>
  );
}
