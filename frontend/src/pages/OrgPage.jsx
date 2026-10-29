import { ArrowRight, LayoutDashboard, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api";
import { CrumbSep, Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function OrgPage() {
  const { orgId = "" } = useParams();
  const [projects, setProjects] = useState([]);
  const [dash, setDash] = useState(null);
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  async function load() {
    const [p, d] = await Promise.all([api.listProjects(orgId), api.dashboard(orgId)]);
    setProjects(p);
    setDash(d);
  }

  useEffect(() => {
    setLoading(true);
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [orgId]);

  async function onCreate(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createProject(orgId, name, key.toUpperCase());
      setName("");
      setKey("");
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <Layout
      orgId={orgId}
      title="Projects"
      subtitle={
        dash ? `${dash.my_open_tasks} open work item${dash.my_open_tasks === 1 ? "" : "s"} assigned to you` : undefined
      }
      crumbs={
        <>
          <Link to="/" className="hover:text-foreground">
            Organizations
          </Link>
          <CrumbSep />
          <span className="text-foreground/80">Projects</span>
        </>
      }
      actions={
        <div className="flex items-center gap-2">
          {dash?.is_admin && (
            <Button asChild size="sm" variant="outline">
              <Link to={`/orgs/${orgId}/dashboard`}>
                <LayoutDashboard className="size-3.5" />
                Dashboard
              </Link>
            </Button>
          )}
          <Button size="sm" onClick={() => setShowCreate((v) => !v)}>
            <Plus className="size-3.5" />
            New project
          </Button>
        </div>
      }
    >
      {showCreate && (
        <div className="mb-4 rounded-lg border border-border bg-card p-4">
          <form className="grid gap-3 sm:grid-cols-[1fr_140px_auto] sm:items-end" onSubmit={onCreate}>
            <div className="grid gap-1.5">
              <Label htmlFor="proj-name" className="text-[12px]">
                Name
              </Label>
              <Input
                id="proj-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Platform Delivery"
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="proj-key" className="text-[12px]">
                Key
              </Label>
              <Input
                id="proj-key"
                value={key}
                onChange={(e) => setKey(e.target.value.toUpperCase())}
                pattern="^[A-Z][A-Z0-9]*$"
                placeholder="KUBE"
                required
              />
            </div>
            <Button type="submit">Create</Button>
          </form>
          {error && <p className="mt-2 text-[13px] text-destructive">{error}</p>}
        </div>
      )}

      {loading ? (
        <p className="text-[13px] text-muted-foreground">Loading…</p>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border px-6 py-16 text-center">
          <p className="text-sm font-medium">No projects yet</p>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Create a project to manage work items and statuses.
          </p>
          <Button className="mt-4" size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="size-3.5" /> New project
          </Button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <div className="grid grid-cols-[72px_1fr_120px_28px] gap-3 border-b border-border bg-muted/30 px-4 py-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            <span>Key</span>
            <span>Name</span>
            <span className="text-right">Progress</span>
            <span />
          </div>
          {projects.map((p, i) => {
            const stats = dash?.projects.find((x) => x.id === p.id);
            const pct = stats?.total ? Math.round((stats.done / stats.total) * 100) : 0;
            return (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className={`group grid grid-cols-[72px_1fr_120px_28px] items-center gap-3 px-4 py-2.5 transition-colors hover:bg-accent/40 ${
                  i > 0 ? "border-t border-border" : ""
                }`}
              >
                <span className="font-mono text-[12px] text-muted-foreground">{p.key}</span>
                <div className="min-w-0">
                  <p className="truncate text-[13px] font-medium">{p.name}</p>
                  <p className="truncate text-[12px] text-muted-foreground">
                    {p.description || "View work items"}
                  </p>
                </div>
                <div className="text-right">
                  {stats ? (
                    <>
                      <p className="text-[12px] tabular-nums text-muted-foreground">
                        {stats.done}/{stats.total}
                      </p>
                      <div className="ml-auto mt-1 h-1 w-16 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                    </>
                  ) : (
                    <span className="text-[12px] text-muted-foreground">—</span>
                  )}
                </div>
                <ArrowRight className="size-3.5 justify-self-end text-muted-foreground opacity-0 transition group-hover:opacity-100" />
              </Link>
            );
          })}
        </div>
      )}
    </Layout>
  );
}
