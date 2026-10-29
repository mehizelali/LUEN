import { ArrowRight, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function HomePage() {
  const [orgs, setOrgs] = useState([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  async function load() {
    setOrgs(await api.listOrgs());
  }

  useEffect(() => {
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function onCreate(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.createOrg(name, slug);
      setName("");
      setSlug("");
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <Layout
      title="Organizations"
      subtitle="Your workspaces"
      actions={
        <Button size="sm" onClick={() => setShowCreate((v) => !v)}>
          <Plus className="size-3.5" />
          New org
        </Button>
      }
    >
      {showCreate && (
        <div className="mb-4 rounded-lg border border-border bg-card p-4">
          <form className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end" onSubmit={onCreate}>
            <div className="grid gap-1.5">
              <Label htmlFor="org-name" className="text-[12px]">
                Name
              </Label>
              <Input
                id="org-name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (!slug || slug === name.toLowerCase().replace(/[^a-z0-9]+/g, "-")) {
                    setSlug(
                      e.target.value
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, "-")
                        .replace(/^-|-$/g, ""),
                    );
                  }
                }}
                placeholder="Acme Delivery"
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="org-slug" className="text-[12px]">
                Slug
              </Label>
              <Input
                id="org-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value.toLowerCase())}
                pattern="^[a-z0-9-]+$"
                placeholder="acme-delivery"
                required
              />
            </div>
            <Button type="submit">Create</Button>
          </form>
          {error && (
            <p className="mt-2 text-[13px] text-destructive">{error}</p>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-[13px] text-muted-foreground">Loading…</p>
      ) : orgs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border px-6 py-16 text-center">
          <p className="text-sm font-medium">No organizations yet</p>
          <p className="mt-1 text-[13px] text-muted-foreground">Create a workspace to start shipping.</p>
          <Button className="mt-4" size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="size-3.5" /> New organization
          </Button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          {orgs.map((o, i) => (
            <Link
              key={o.id}
              to={`/orgs/${o.id}`}
              className={`group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent/50 ${
                i > 0 ? "border-t border-border" : ""
              }`}
            >
              <div className="grid size-8 place-items-center rounded-md bg-primary/15 text-[11px] font-semibold text-primary">
                {o.name.slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium">{o.name}</p>
                <p className="truncate text-[12px] text-muted-foreground">/{o.slug}</p>
              </div>
              <ArrowRight className="size-3.5 text-muted-foreground opacity-0 transition group-hover:opacity-100" />
            </Link>
          ))}
        </div>
      )}
    </Layout>
  );
}
