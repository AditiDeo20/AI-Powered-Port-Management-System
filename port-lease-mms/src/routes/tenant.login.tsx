import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import { Anchor, LockKeyhole, ShieldCheck, Loader2, AlertCircle, ShieldAlert, X } from "lucide-react";
import heroImg from "@/assets/port-hero.jpg";

export const Route = createFileRoute("/tenant/login")({
  head: () => ({
    meta: [
      { title: "Tenant Login | Port Management System" },
      { name: "description", content: "Secure tenant portal login for port land lease services." },
    ],
  }),
  component: TenantLogin,
});

const getApiBase = () => {
  const envUrl = (import.meta as any).env?.VITE_API_URL;
  if (envUrl) return envUrl;
  if (typeof window !== "undefined" && window.location?.hostname) {
    const host = window.location.hostname === "localhost" ? "127.0.0.1" : window.location.hostname;
    return `http://${host}:8000`;
  }
  return "http://127.0.0.1:8000";
};
const API_BASE = getApiBase();


// ─── Types ───────────────────────────────────────────
interface LoginResponse {
  status: string;
  user_name: string;
  name: string;
  tenant_id: string;
  token?: string;
  applicant_id?: number;
}

function TenantLogin() {
  const navigate = useNavigate();

  // ── Form state ──
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/tenant/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });


      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const errorMessage = body?.detail ?? "Invalid credentials. Please try again.";
        throw new Error(errorMessage);
      }

      const data: LoginResponse = await res.json();

      // Store session items securely in localStorage
      localStorage.setItem("tenantName", data.name);
      localStorage.setItem("tenantUserName", data.user_name);
      localStorage.setItem("tenantId", data.tenant_id);
      if (data.token) {
        localStorage.setItem("tenantToken", data.token);
      }
      if (data.applicant_id) {
        localStorage.setItem("tenantApplicantId", String(data.applicant_id));
      }

      // Redirect to Tenant Dashboard
      navigate({ to: "/tenant/dashboard" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background relative">
      <GovHeader />
      <main className="flex-1 bg-surface py-10">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 lg:grid-cols-2 lg:items-stretch">
          {/* Login Card */}
          <div className="card-gov p-8 sm:p-10">
            <div className="mb-6 flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-navy text-navy-foreground">
                <Anchor className="h-5 w-5" />
              </div>
              <div>
                <div className="font-display text-lg font-semibold text-navy">
                  Tenant Portal Login
                </div>
                <div className="text-xs text-muted-foreground">
                  Access your lease details, organization profile and payment status
                </div>
              </div>
            </div>

            {/* Inline Error Alert */}
            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-1.5">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  placeholder="Username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 text-foreground/80 cursor-pointer">
                  <Checkbox id="remember" /> Remember me
                </label>
                <a href="#" className="font-medium text-navy hover:underline">
                  Forgot password?
                </a>
              </div>

              <Button
                type="submit"
                className="w-full bg-navy text-navy-foreground hover:bg-navy/90"
                size="lg"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Signing in…
                  </>
                ) : (
                  <>
                    <LockKeyhole className="mr-2 h-4 w-4" /> Secure Login
                  </>
                )}
              </Button>
              <Button asChild type="button" variant="outline" className="w-full" size="lg">
                <Link to="/tenant/login">Register as New Tenant</Link>
              </Button>
            </form>

            <div className="mt-6 flex items-start gap-2 rounded-md border border-gov-green/20 bg-gov-green/5 p-3 text-xs text-foreground/80">
              <ShieldCheck className="mt-0.5 h-4 w-4 text-gov-green shrink-0" />
              <span>
                This is an official Major Port Authority portal. Unauthorised access is a punishable
                offence under applicable cybersecurity laws and regulations.
              </span>
            </div>
          </div>

          {/* Illustration */}
          <div className="relative hidden overflow-hidden rounded-lg border border-border lg:block">
            <img
              src={heroImg}
              alt="Port with shipping containers"
              className="h-full w-full object-cover"
              loading="lazy"
              width={1920}
              height={1080}
            />
            <div className="absolute inset-0 bg-gradient-to-tr from-navy/85 via-navy/40 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
              <div className="text-xs uppercase tracking-widest text-gold">Tenant Portal</div>
              <div className="mt-2 font-display text-2xl font-semibold">
                Manage your port land lease
              </div>
              <p className="mt-2 max-w-md text-sm text-white/80">
                Isolated, secure digital access to lease agreements, tax credentials, and lease duration details.
              </p>
            </div>
          </div>
        </div>
      </main>
      <GovFooter />

    </div>
  );
}
