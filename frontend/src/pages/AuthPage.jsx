import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function AuthPage() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, name, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(15,118,110,0.08),transparent_55%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#e4e3df_1px,transparent_1px),linear-gradient(to_bottom,#e4e3df_1px,transparent_1px)] bg-[size:48px_48px] opacity-40" />

      <div className="relative w-full max-w-[380px]">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 grid size-9 place-items-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            K
          </div>
          <h1 className="text-xl font-semibold tracking-tight">
            {mode === "login" ? "Sign in to KubeFlow" : "Create your workspace"}
          </h1>
          <p className="mt-1.5 text-[13px] text-muted-foreground">
            Issues, projects, and delivery — built for speed.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <form className="grid gap-3" onSubmit={onSubmit}>
            {mode === "register" && (
              <div className="grid gap-1.5">
                <Label htmlFor="name" className="text-[12px]">
                  Name
                </Label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
            )}
            <div className="grid gap-1.5">
              <Label htmlFor="email" className="text-[12px]">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="password" className="text-[12px]">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-[13px] text-destructive">
                {error}
              </div>
            )}
            <Button type="submit" disabled={busy} className="mt-1 w-full">
              {busy ? "Working…" : mode === "login" ? "Continue" : "Create account"}
            </Button>
          </form>
        </div>

        <p className="mt-4 text-center text-[13px] text-muted-foreground">
          {mode === "login" ? "No account?" : "Already have an account?"}{" "}
          <button
            type="button"
            className="font-medium text-primary hover:underline"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
