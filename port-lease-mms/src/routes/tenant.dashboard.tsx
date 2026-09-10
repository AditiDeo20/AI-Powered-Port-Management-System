import { useState, useEffect } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { DashboardShell, type NavItem } from "@/components/site/DashboardShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LayoutDashboard,
  FileText,
  Building2,
  UserCheck,
  CreditCard,
  CalendarClock,
  ShieldCheck,
  Bot,
  Loader2,
  AlertTriangle,
  Activity,
  CheckCircle2,
  Clock,
  Home,
} from "lucide-react";

export const Route = createFileRoute("/tenant/dashboard")({
  head: () => ({
    meta: [{ title: "Tenant Dashboard | Port Management System" }],
  }),
  component: TenantDashboard,
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


const nav: NavItem[] = [
  { to: "/tenant/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/tenant/dashboard", label: "My Profile", icon: UserCheck },
  { to: "/tenant/dashboard", label: "Lease Agreements", icon: FileText },
  { to: "/tenant/ai-support", label: "AI Support", icon: Bot },
];

// ─── Types ───────────────────────────────────────────
interface TenantSummary {
  applicant_id: number;
  ind_org_name: string;
  contact_person_name: string;
  username: string;
  pan_number: string;
  gst_number: string;
  tenant_id: string;
  tenancy_id: string;
  tenancy_type: string;
  tenant_type: string;
  mapping_status: string;
  purpose: string;
  duration_from: string;
}

function TenantDashboard() {
  const [summary, setSummary] = useState<TenantSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSummary() {
      setLoading(true);
      setError(null);
      
      const token = localStorage.getItem("tenantToken");
      const applicantId = localStorage.getItem("tenantApplicantId");

      try {
        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        if (applicantId) {
          headers["X-Applicant-ID"] = applicantId;
        }

        const res = await fetch(`${API_BASE}/tenant/api/dashboard/summary`, {
          headers,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.detail ?? `Failed to load dashboard profile summary (${res.status})`);
        }

        const data: TenantSummary = await res.json();
        if (!cancelled) {
          setSummary(data);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Error connecting to backend API.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchSummary();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Loading state ──
  if (loading) {
    return (
      <DashboardShell
        title="Loading Tenant Portal…"
        subtitle="Retrieving profile & property mapping information"
        role="Tenant"
        user="Tenant User"
        nav={nav}
      >
        <div className="flex flex-col items-center justify-center gap-4 py-32 text-muted-foreground">
          <Loader2 className="h-10 w-10 animate-spin text-navy" />
          <p className="text-sm font-medium">Authenticating & loading tenant property mapping…</p>
        </div>
      </DashboardShell>
    );
  }

  // ── Error state ──
  if (error || !summary) {
    return (
      <DashboardShell
        title="Tenant Dashboard"
        subtitle="Error loading property mapping"
        role="Tenant"
        user="Tenant"
        nav={nav}
      >
        <div className="flex flex-col items-center justify-center gap-4 py-28 text-muted-foreground">
          <AlertTriangle className="h-10 w-10 text-destructive" />
          <p className="text-sm text-destructive">{error ?? "Unable to fetch summary profile."}</p>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
            Retry Connection
          </Button>
        </div>
      </DashboardShell>
    );
  }

  const contactName = summary.contact_person_name || summary.username || "Tenant Contact";
  const orgName = summary.ind_org_name || "Port Tenant Corp";
  const displayTenantId = summary.tenant_id.startsWith("TNT-") ? summary.tenant_id : `TNT-${summary.tenant_id}`;

  return (
    <DashboardShell
      title={`Welcome, ${contactName}`}
      subtitle={`${orgName} | Tenant ID: ${displayTenantId} | Tenancy ID: ${summary.tenancy_id}`}
      role="Tenant"
      user={contactName}
      nav={nav}
    >
      {/* Overview Banner */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-navy/10 bg-gradient-to-r from-navy/5 via-surface to-gov-green/5 p-6 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-display text-xl font-bold text-navy">{orgName}</h2>
            <Badge className="bg-gov-green/10 text-gov-green border-gov-green/20 hover:bg-gov-green/20">
              <CheckCircle2 className="mr-1 h-3 w-3 inline" /> {summary.mapping_status ?? "APPROVED"}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Tenant ID: <span className="font-semibold text-foreground">{displayTenantId}</span> · Tenancy ID: <span className="font-semibold text-foreground">{summary.tenancy_id}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button asChild size="sm" variant="outline" className="border-navy/30 text-navy font-semibold hover:bg-navy/5">
            <Link to="/tenant/ai-support">
              <Bot className="mr-2 h-4 w-4" /> AI Support
            </Link>
          </Button>
        </div>
      </div>

      {/* Full Tenant Profile UI (Grid Layout) */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Section 1: Lease Overview */}
        <div className="card-gov p-6">
          <div className="mb-4 flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-navy/10 text-navy">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold text-navy">Section 1: Lease Overview</h3>
              <p className="text-xs text-muted-foreground">Mapping status & tenancy types</p>
            </div>
          </div>
          <div className="space-y-3.5 text-sm">
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground font-medium">Mapping Status</span>
              <Badge className="bg-gov-green/10 text-gov-green font-semibold border border-gov-green/20">
                {summary.mapping_status ?? "APPROVED"}
              </Badge>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground font-medium">Tenancy Type</span>
              <span className="font-semibold text-navy">{summary.tenancy_type ?? "Long Lease"}</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-muted-foreground font-medium">Tenant Type</span>
              <span className="font-semibold text-navy">{summary.tenant_type ?? "Sole-Tenancy"}</span>
            </div>
          </div>
        </div>

        {/* Section 2: Organization & Identity */}
        <div className="card-gov p-6">
          <div className="mb-4 flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-navy/10 text-navy">
              <Building2 className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold text-navy">Section 2: Organization & Identity</h3>
              <p className="text-xs text-muted-foreground">Entity registration details</p>
            </div>
          </div>
          <div className="space-y-3.5 text-sm">
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground font-medium">Organization Name</span>
              <span className="font-semibold text-navy text-right max-w-[220px] truncate" title={summary.ind_org_name}>
                {summary.ind_org_name ?? "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground font-medium">Username</span>
              <span className="font-mono font-semibold text-foreground">{summary.username ?? "N/A"}</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-muted-foreground font-medium">Primary Contact</span>
              <span className="font-semibold text-navy">{summary.contact_person_name ?? "N/A"}</span>
            </div>
          </div>
        </div>

        {/* Section 3: Tax & Legal Information */}
        <div className="card-gov p-6">
          <div className="mb-4 flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-navy/10 text-navy">
              <CreditCard className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold text-navy">Section 3: Tax & Legal Information</h3>
              <p className="text-xs text-muted-foreground">Government regulatory IDs</p>
            </div>
          </div>
          <div className="space-y-3.5 text-sm">
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground font-medium">PAN Number</span>
              <span className="font-mono font-bold tracking-wider text-navy uppercase bg-surface px-2.5 py-1 rounded border border-border">
                {summary.pan_number ?? "N/A"}
              </span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-muted-foreground font-medium">GST Number</span>
              <span className="font-mono font-bold tracking-wider text-navy uppercase bg-surface px-2.5 py-1 rounded border border-border">
                {summary.gst_number ?? "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* Section 4: Property Details */}
        <div className="card-gov p-6">
          <div className="mb-4 flex items-center gap-2.5 border-b border-border pb-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-navy/10 text-navy">
              <Home className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold text-navy">Section 4: Property Details</h3>
              <p className="text-xs text-muted-foreground">Allotment purpose & commencement</p>
            </div>
          </div>
          <div className="space-y-3.5 text-sm">
            <div className="flex justify-between items-center py-1.5 border-b border-border/50">
              <span className="text-muted-foreground font-medium">Purpose</span>
              <span className="font-semibold text-navy">{summary.purpose ?? "Commercial Land Lease"}</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-muted-foreground font-medium flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-gov-green" /> Valid From
              </span>
              <span className="font-semibold text-navy">{summary.duration_from ?? "1992-05-01"}</span>
            </div>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
