import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import { LockKeyhole, ShieldCheck, Building2, Loader2, AlertCircle, ShieldAlert, X } from "lucide-react";

export const Route = createFileRoute("/authority/login")({
  head: () => ({
    meta: [
      { title: "Authority Login | Port Management System" },
      { name: "description", content: "Restricted login for port authority officers." },
    ],
  }),
  component: AuthorityLogin,
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


interface AuthorityLoginResponse {
  status: string;
  user_name: string;
  name: string;
  admin_id: string;
  role_id: string;
  role_title: string;
}

function AuthorityLogin() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/authority/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });


      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const errorMessage = body?.detail ?? "Authentication failed.";
        throw new Error(errorMessage);
      }

      const data: AuthorityLoginResponse = await res.json();

      // Validate allowed roles: HO (Head of Department), NO (Nodal Officer), DO (Data Entry Operator)
      const allowedRoles = ["HO", "NO", "DO"];
      if (!allowedRoles.includes(data.role_id?.toUpperCase())) {
        setError("Invalid credentials.");
        return;
      }

      // Store authority session details in localStorage
      localStorage.setItem("authorityName", data.name);
      localStorage.setItem("authorityUserName", data.user_name);
      localStorage.setItem("authorityUsername", data.user_name);
      localStorage.setItem("authorityId", data.admin_id);
      localStorage.setItem("authorityRoleId", data.role_id);
      localStorage.setItem("authorityRoleTitle", data.role_title);
      localStorage.setItem("authorityRole", data.role_title);

      // Redirect to Admin/Authority Dashboard
      navigate({ to: "/authority/dashboard" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background relative">
      <GovHeader />
      <main className="flex-1 bg-surface flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="card-gov p-8 sm:p-10 shadow-xl border border-navy/15 rounded-2xl bg-white">
            <div className="mb-6 flex items-center gap-3 border-b border-navy/10 pb-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-navy text-gold shadow-sm">
                <Building2 className="h-6 w-6" />
              </div>
              <div>
                <div className="font-display text-xl font-bold text-navy">
                  Authority Portal
                </div>
                <div className="text-xs font-medium text-muted-foreground flex items-center gap-1 mt-0.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-gov-green" /> Restricted access — Officers only
                </div>
              </div>
            </div>

            {error && (
              <div className="mb-5 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs font-semibold text-red-700 shadow-2xs">
                <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                <span>{error}</span>
              </div>
            )}

            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-1.5">
                <Label htmlFor="auth-id" className="text-xs font-bold text-navy uppercase tracking-wider">Username</Label>
                <div className="relative">
                  <Input 
                    id="auth-id" 
                    placeholder="Enter Officer Username (e.g. do_ND_satya)" 
                    required 
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={loading}
                    className="h-10 text-xs font-medium border-navy/20 focus:border-navy"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-xs font-bold text-navy uppercase tracking-wider">Password</Label>
                <div className="relative">
                  <Input 
                    id="password" 
                    type="password" 
                    placeholder="••••••••" 
                    required 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                    className="h-10 text-xs font-medium border-navy/20 focus:border-navy"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-11 bg-navy text-white hover:bg-navy/90 font-bold text-sm shadow-md mt-2"
                size="lg"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Authenticating Officer…
                  </>
                ) : (
                  <>
                    <LockKeyhole className="mr-2 h-4 w-4 text-gold" /> Sign in Securely
                  </>
                )}
              </Button>
            </form>

            <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-gold/40 bg-amber-50/60 p-3.5 text-xs font-medium text-amber-900 shadow-2xs">
              <ShieldAlert className="mt-0.5 h-4 w-4 text-amber-600 shrink-0" />
              <span>
                All officer activities are logged and audited under statutory port authority IT security guidelines.
              </span>
            </div>

            <div className="mt-6 text-center text-xs font-medium text-muted-foreground border-t border-navy/10 pt-4">
              Not a Port Officer?{" "}
              <Link to="/tenant/login" className="font-bold text-navy hover:underline">
                Go to Tenant Login Portal
              </Link>
            </div>
          </div>
        </div>
      </main>
      <GovFooter />
    </div>
  );
}
