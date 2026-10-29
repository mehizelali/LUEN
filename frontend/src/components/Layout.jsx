import {
  BarChart3,
  Building2,
  ChevronRight,
  FolderKanban,
  LogOut,
  Search,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function NavItem({ to, active, icon: Icon, children }) {
  return (
    <Link
      to={to}
      className={cn(
        "group flex h-8 items-center gap-2 rounded-md px-2 text-[13px] transition-colors",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
      )}
    >
      <Icon
        className={cn(
          "size-3.5 shrink-0",
          active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
        )}
      />
      <span className="truncate">{children}</span>
    </Link>
  );
}

export function Layout({ title, subtitle, orgId, crumbs, children, wide, actions }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const path = location.pathname;
  const initials = (user?.name || "?")
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const onHome = path === "/";
  const onOrg = orgId && path === `/orgs/${orgId}`;
  const onDash = orgId && path === `/orgs/${orgId}/dashboard`;
  const onBoard = path.startsWith("/projects/");

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="sticky top-0 z-30 flex h-screen w-[220px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar max-lg:h-auto max-lg:w-full max-lg:border-b max-lg:border-r-0">
        <div className="flex h-12 items-center gap-2 border-b border-sidebar-border px-3">
          <div className="grid size-5 place-items-center rounded bg-primary text-[10px] font-bold text-primary-foreground">
            K
          </div>
          <span className="truncate text-[13px] font-semibold tracking-tight">KubeFlow</span>
        </div>

        <nav className="flex-1 space-y-4 overflow-y-auto px-2 py-3">
          <div className="space-y-0.5">
            <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
              Workspace
            </p>
            <NavItem to="/" active={onHome} icon={Building2}>
              Organizations
            </NavItem>
          </div>

          {orgId ? (
            <div className="space-y-0.5">
              <p className="mb-1 px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
                Organization
              </p>
              <NavItem to={`/orgs/${orgId}`} active={onOrg || onBoard} icon={FolderKanban}>
                Projects
              </NavItem>
              <NavItem to={`/orgs/${orgId}/dashboard`} active={onDash} icon={BarChart3}>
                Insights
              </NavItem>
            </div>
          ) : null}
        </nav>

        <div className="border-t border-sidebar-border p-2">
          <div className="flex items-center gap-2 rounded-md px-1.5 py-1.5">
            <Avatar className="size-6">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-medium text-foreground">{user?.name}</p>
              <p className="truncate text-[10px] text-muted-foreground">{user?.email}</p>
            </div>
            <Button variant="ghost" size="icon-sm" onClick={logout} title="Log out">
              <LogOut className="size-3.5" />
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-12 items-center justify-between gap-3 border-b border-border bg-background/90 px-4 backdrop-blur-md">
          <div className="min-w-0">
            {crumbs ? (
              <div className="mb-0.5 flex flex-wrap items-center gap-1 text-[11px] text-muted-foreground">
                {crumbs}
              </div>
            ) : null}
            <div className="flex items-baseline gap-2">
              <h1 className="truncate text-[15px] font-semibold tracking-tight">{title || "KubeFlow"}</h1>
              {subtitle ? (
                <p className="hidden truncate text-[12px] text-muted-foreground sm:block">{subtitle}</p>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="hidden h-7 items-center gap-2 rounded-md border border-border bg-muted/40 px-2.5 text-[12px] text-muted-foreground transition-colors hover:bg-accent md:inline-flex"
            >
              <Search className="size-3" />
              <span>Search</span>
              <kbd className="ml-2 rounded border border-border bg-background px-1 font-mono text-[10px] text-muted-foreground">
                ⌘K
              </kbd>
            </button>
            {actions}
          </div>
        </header>

        <main className={cn("mx-auto w-full flex-1", wide ? "max-w-none" : "max-w-6xl p-4 md:p-5")}>
          {children}
        </main>
      </div>
    </div>
  );
}

export function CrumbSep() {
  return <ChevronRight className="size-3 opacity-50" />;
}
