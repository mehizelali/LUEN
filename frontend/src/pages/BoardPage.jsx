import {
  CheckCircle2,
  Circle,
  CircleDot,
  MessageSquare,
  Plus,
  Search,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api";
import { CrumbSep, Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

function StatusIcon({ category, className }) {
  if (category === "done") return <CheckCircle2 className={cn("size-3.5 text-teal-600", className)} />;
  if (category === "started") return <CircleDot className={cn("size-3.5 text-amber-500", className)} />;
  return <Circle className={cn("size-3.5 text-muted-foreground", className)} />;
}

function PriorityBars({ priority }) {
  const level = { low: 1, medium: 2, high: 3, urgent: 4 }[priority] || 1;
  const color =
    priority === "urgent"
      ? "bg-rose-500"
      : priority === "high"
        ? "bg-orange-400"
        : priority === "medium"
          ? "bg-yellow-400/80"
          : "bg-muted-foreground/40";
  return (
    <div className="flex items-end gap-px" title={priority}>
      {[1, 2, 3, 4].map((n) => (
        <span
          key={n}
          className={cn(
            "w-[3px] rounded-sm",
            n === 1 ? "h-1.5" : n === 2 ? "h-2" : n === 3 ? "h-2.5" : "h-3",
            n <= level ? color : "bg-border",
          )}
        />
      ))}
    </div>
  );
}

export function BoardPage() {
  const { projectId = "" } = useParams();
  const [project, setProject] = useState(null);
  const [statuses, setStatuses] = useState([]);
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");
  const [statusId, setStatusId] = useState("");
  const [selected, setSelected] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentBody, setCommentBody] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);

  async function loadBoard(search) {
    const [p, s, w] = await Promise.all([
      api.getProject(projectId),
      api.listStatuses(projectId),
      api.listWorkItems(projectId, search || undefined),
    ]);
    setProject(p);
    setStatuses(s);
    setItems(w);
    setStatusId((prev) => prev || s[0]?.id || "");
  }

  useEffect(() => {
    setLoading(true);
    setError(null);
    loadBoard()
      .catch((e) => setError(e.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [projectId]);

  async function openItem(item) {
    setSelected(item);
    setError(null);
    try {
      setComments(await api.listComments(item.id));
    } catch (err) {
      setComments([]);
      setError(err instanceof Error ? err.message : "Failed to load comments");
    }
  }

  async function onCreate(e) {
    e.preventDefault();
    const trimmed = title.trim();
    if (!trimmed || creating) return;
    setCreating(true);
    setError(null);
    try {
      const payload = { title: trimmed, priority };
      if (statusId) payload.status_id = statusId;
      const created = await api.createWorkItem(projectId, payload);
      setTitle("");
      setPriority("medium");
      setComposerOpen(false);
      await loadBoard(q);
      await openItem(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create task");
    } finally {
      setCreating(false);
    }
  }

  async function moveItem(item, nextStatusId) {
    const updated = await api.updateWorkItem(item.id, { status_id: nextStatusId });
    setItems((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    if (selected?.id === updated.id) setSelected(updated);
  }

  async function saveSelected(patch) {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateWorkItem(selected.id, {
        title: patch.title,
        description: patch.description ?? undefined,
        priority: patch.priority,
        status_id: patch.status_id ?? undefined,
      });
      setSelected(updated);
      setItems((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function addComment(e) {
    e.preventDefault();
    if (!selected || !commentBody.trim()) return;
    try {
      const c = await api.createComment(selected.id, commentBody.trim());
      setComments((prev) => [...prev, c]);
      setCommentBody("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comment failed");
    }
  }

  const byStatus = useMemo(() => {
    const map = new Map();
    for (const s of statuses) map.set(s.id, []);
    for (const item of items) {
      const key = item.status_id ?? statuses[0]?.id;
      if (!key) continue;
      map.get(key)?.push(item);
    }
    return map;
  }, [items, statuses]);

  const statusById = useMemo(() => new Map(statuses.map((s) => [s.id, s])), [statuses]);

  return (
    <Layout
      wide
      orgId={project?.org_id}
      title={project ? project.name : "Issues"}
      subtitle={project ? project.key : undefined}
      crumbs={
        project ? (
          <>
            <Link to="/" className="hover:text-foreground">
              Orgs
            </Link>
            <CrumbSep />
            <Link to={`/orgs/${project.org_id}`} className="hover:text-foreground">
              Projects
            </Link>
            <CrumbSep />
            <span className="text-foreground/80">{project.key}</span>
          </>
        ) : null
      }
      actions={
        <Button
          size="sm"
          onClick={() => setComposerOpen(true)}
        >
          <Plus className="size-3.5" />
          New issue
        </Button>
      }
    >
      <div className="flex min-h-[calc(100vh-3rem)]">
        {/* Issue stream */}
        <div
          className={cn(
            "flex min-w-0 flex-1 flex-col border-r border-border",
            selected ? "max-xl:hidden" : "",
          )}
        >
          <div className="flex h-11 items-center gap-2 border-b border-border px-3">
            <form
              className="flex flex-1 items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                loadBoard(q).catch((err) => setError(err.message));
              }}
            >
              <Search className="size-3.5 shrink-0 text-muted-foreground" />
              <input
                className="h-8 w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
                placeholder="Filter issues…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </form>
            <span className="tabular-nums text-[11px] text-muted-foreground">{items.length}</span>
          </div>

          {composerOpen && (
            <form
              onSubmit={onCreate}
              className="space-y-2 border-b border-border bg-card/60 px-3 py-3"
            >
              <Input
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Issue title"
                required
                disabled={creating}
                className="border-0 bg-transparent px-0 text-[14px] font-medium shadow-none focus-visible:ring-0"
              />
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className="select-field w-auto min-w-[120px]"
                  value={statusId}
                  onChange={(e) => setStatusId(e.target.value)}
                  disabled={creating || !statuses.length}
                >
                  {statuses.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                <select
                  className="select-field w-auto min-w-[110px]"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  disabled={creating}
                >
                  {["low", "medium", "high", "urgent"].map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <div className="ml-auto flex gap-1.5">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setComposerOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" size="sm" disabled={creating || !title.trim()}>
                    {creating ? "Creating…" : "Create"}
                  </Button>
                </div>
              </div>
            </form>
          )}

          {error && (
            <div className="border-b border-destructive/20 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
              {error}
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <p className="px-4 py-8 text-[13px] text-muted-foreground">Loading…</p>
            ) : items.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <p className="text-sm font-medium">No issues</p>
                <p className="mt-1 text-[13px] text-muted-foreground">
                  Create the first issue to start the stream.
                </p>
                <Button className="mt-4" size="sm" onClick={() => setComposerOpen(true)}>
                  <Plus className="size-3.5" /> New issue
                </Button>
              </div>
            ) : (
              statuses.map((s) => {
                const list = byStatus.get(s.id) ?? [];
                if (list.length === 0 && items.length > 0) return null;
                return (
                  <div key={s.id}>
                    <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-muted/40 px-3 py-1.5 backdrop-blur">
                      <StatusIcon category={s.category} />
                      <span className="text-[12px] font-medium">{s.name}</span>
                      <span className="tabular-nums text-[11px] text-muted-foreground">
                        {list.length}
                      </span>
                    </div>
                    {list.map((item) => (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => openItem(item)}
                        className={cn(
                          "group flex w-full items-center gap-3 border-b border-border/70 px-3 py-2 text-left transition-colors hover:bg-accent/40",
                          selected?.id === item.id && "bg-accent",
                        )}
                      >
                        <StatusIcon category={statusById.get(item.status_id)?.category} />
                        <span className="w-16 shrink-0 font-mono text-[11px] text-muted-foreground">
                          {project?.key}-{item.number}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-[13px]">{item.title}</span>
                        <PriorityBars priority={item.priority} />
                      </button>
                    ))}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Detail pane */}
        <aside
          className={cn(
            "flex w-full shrink-0 flex-col bg-background xl:w-[420px]",
            !selected && "max-xl:hidden",
          )}
        >
          {!selected ? (
            <div className="grid flex-1 place-content-center px-8 text-center">
              <p className="text-sm font-medium text-muted-foreground">Select an issue</p>
              <p className="mt-1 text-[12px] text-muted-foreground/70">
                Details and properties appear here.
              </p>
            </div>
          ) : (
            <>
              <div className="flex h-11 items-center justify-between border-b border-border px-3">
                <span className="font-mono text-[12px] text-muted-foreground">
                  {project?.key}-{selected.number}
                  {saving ? " · saving" : ""}
                </span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setSelected(null)}
                  className="xl:hidden"
                >
                  <X className="size-3.5" />
                </Button>
              </div>

              <div className="flex-1 space-y-5 overflow-y-auto p-4">
                <Input
                  className="h-auto border-0 bg-transparent px-0 text-lg font-semibold tracking-tight shadow-none focus-visible:ring-0"
                  value={selected.title}
                  onChange={(e) => setSelected({ ...selected, title: e.target.value })}
                  onBlur={() => saveSelected({ title: selected.title })}
                />

                <div className="space-y-0 divide-y divide-border rounded-md border border-border">
                  <PropertyRow label="Status">
                    <select
                      className="select-field h-7 border-0 bg-transparent px-0 focus-visible:ring-0"
                      value={selected.status_id ?? ""}
                      onChange={(e) => moveItem(selected, e.target.value)}
                    >
                      {statuses.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </PropertyRow>
                  <PropertyRow label="Priority">
                    <select
                      className="select-field h-7 border-0 bg-transparent px-0 focus-visible:ring-0"
                      value={selected.priority}
                      onChange={(e) => {
                        const next = e.target.value;
                        setSelected({ ...selected, priority: next });
                        saveSelected({ priority: next });
                      }}
                    >
                      {["low", "medium", "high", "urgent"].map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </PropertyRow>
                </div>

                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Description
                  </p>
                  <Textarea
                    rows={6}
                    value={selected.description ?? ""}
                    placeholder="Add description…"
                    className="border-border/80 bg-muted/20"
                    onChange={(e) => setSelected({ ...selected, description: e.target.value })}
                    onBlur={() => saveSelected({ description: selected.description })}
                  />
                </div>

                <div>
                  <p className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    <MessageSquare className="size-3" /> Activity
                  </p>
                  <div className="space-y-3">
                    {comments.length === 0 && (
                      <p className="text-[13px] text-muted-foreground">No comments yet.</p>
                    )}
                    {comments.map((c) => (
                      <div key={c.id} className="flex gap-2.5">
                        <div className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-secondary text-[9px] font-medium text-muted-foreground">
                          {(c.author.name || "?")
                            .split(" ")
                            .map((p) => p[0])
                            .join("")
                            .slice(0, 2)
                            .toUpperCase()}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-[12px]">
                            <span className="font-medium">{c.author.name}</span>
                            <span className="text-muted-foreground">
                              {" · "}
                              {new Date(c.created_at).toLocaleString()}
                            </span>
                          </p>
                          <p className="mt-0.5 text-[13px] text-foreground/90">{c.body}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <form className="mt-3 grid gap-2" onSubmit={addComment}>
                    <Textarea
                      rows={2}
                      placeholder="Leave a comment…"
                      value={commentBody}
                      onChange={(e) => setCommentBody(e.target.value)}
                    />
                    <Button type="submit" size="sm" className="w-fit" disabled={!commentBody.trim()}>
                      Comment
                    </Button>
                  </form>
                </div>
              </div>
            </>
          )}
        </aside>
      </div>
    </Layout>
  );
}

function PropertyRow({ label, children }) {
  return (
    <div className="grid grid-cols-[100px_1fr] items-center gap-2 px-3 py-2">
      <span className="text-[12px] text-muted-foreground">{label}</span>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
