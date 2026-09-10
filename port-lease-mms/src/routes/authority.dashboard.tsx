import { useState, useEffect } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { DashboardShell, type NavItem } from "@/components/site/DashboardShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
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
import {
  BarChart3,
  Bot,
  Building2,
  ClipboardList,
  FileUp,
  LandPlot,
  LayoutDashboard,
  Map as MapIcon,
  Users,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Eye,
  FileSpreadsheet,
  Layers,
  Search,
  UploadCloud,
  Download,
} from "lucide-react";

export const Route = createFileRoute("/authority/dashboard")({
  head: () => ({
    meta: [{ title: "Authority Dashboard | Port Management System" }],
  }),
  component: AuthorityDashboard,
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


const defaultExpiryData = [
  { m: "Jan", leases: 12 },
  { m: "Feb", leases: 18 },
  { m: "Mar", leases: 28 },
  { m: "Apr", leases: 22 },
  { m: "May", leases: 34 },
  { m: "Jun", leases: 40 },
  { m: "Jul", leases: 30 },
  { m: "Aug", leases: 26 },
  { m: "Sep", leases: 24 },
  { m: "Oct", leases: 32 },
  { m: "Nov", leases: 38 },
  { m: "Dec", leases: 45 },
];

const defaultOccupancyData = [
  { name: "Occupied (Status: A)", value: 405.71, color: "hsl(215 55% 30%)" },
  { name: "Vacant (Status: V)", value: 6.58, color: "hsl(210 40% 65%)" },
  { name: "Pending (Status: RG)", value: 13.51, color: "hsl(45 90% 55%)" },
];

function KPI({
  label,
  value,
  subtext,
  icon: Icon,
  tint,
}: {
  label: string;
  value: string;
  subtext?: string;
  icon: React.ComponentType<{ className?: string }>;
  tint: string;
}) {
  return (
    <div className="card-gov p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{label}</span>
        <div className={`flex h-8 w-8 items-center justify-center rounded-md ${tint}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-2 font-display text-xl sm:text-2xl font-bold text-navy tracking-tight">{value}</div>
      {subtext && (
        <div className="mt-1 text-xs font-medium text-muted-foreground">{subtext}</div>
      )}
    </div>
  );
}

interface ApplicationRow {
  tenancy_id?: string;
  tenant_id: string;
  tenant_name: string;
  person_name?: string;
  tenancy_type: string;
  status: string;
  purpose: string;
  duration_from: string;
  pan_number?: string;
  gst_number?: string;
  username?: string;
}

function AuthorityDashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState("Authority Officer");
  const [adminId, setAdminId] = useState("");
  const [roleTitle, setRoleTitle] = useState("Head of Department");

  // Active View State: 'overview' displays master metrics
  const [activeTab, setActiveTab] = useState<"overview" | "tenants" | "lease_management" | "documents">("overview");
  const [searchFilter, setSearchFilter] = useState("");
  const [searchResults, setSearchResults] = useState<ApplicationRow[] | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<ApplicationRow | null>(null);

  const [userRoleId, setUserRoleId] = useState("");
  const [userUsername, setUserUsername] = useState("");

  // Live Database Metrics state
  const [totalPlots, setTotalPlots] = useState("2,770 plots");
  const [totalLandSqm, setTotalLandSqm] = useState("4,383,038.68 sq.m");
  const [totalLandHa, setTotalLandHa] = useState("438.30 ha");
  const [occupiedSqm, setOccupiedSqm] = useState("4,057,052.65 sq.m");
  const [occupiedHa, setOccupiedHa] = useState("405.71 ha");
  const [vacantSqm, setVacantSqm] = useState("65,847.28 sq.m");
  const [vacantHa, setVacantHa] = useState("6.58 ha");
  const [pendingSqm, setPendingSqm] = useState("135,138.75 sq.m");
  const [pendingHa, setPendingHa] = useState("13.51 ha");

  const [expiryTimeline, setExpiryTimeline] = useState(defaultExpiryData);
  const [occupancySplit, setOccupancySplit] = useState(defaultOccupancyData);
  const [recentApps, setRecentApps] = useState<ApplicationRow[]>([]);

  useEffect(() => {
    // If logged in as tenant without authority credentials, redirect to tenant dashboard
    const tenantToken = localStorage.getItem("tenantToken");
    const id = localStorage.getItem("authorityId");
    if (tenantToken && !id) {
      navigate({ to: "/tenant/dashboard" });
      return;
    }

    const name = localStorage.getItem("authorityName");
    const uname = localStorage.getItem("authorityUsername") || localStorage.getItem("authorityUser");
    const storedRoleTitle = localStorage.getItem("authorityRoleTitle");
    const storedRoleId = localStorage.getItem("authorityRoleId") || localStorage.getItem("authorityRole");

    if (!id && !uname) {
      navigate({ to: "/authority/login" });
      return;
    }

    if (name) setUserName(name);
    if (id) setAdminId(id);
    if (uname) setUserUsername(uname);
    if (storedRoleId) setUserRoleId(storedRoleId);

    if (storedRoleTitle) {
      setRoleTitle(storedRoleTitle);
    } else if (storedRoleId) {
      const uRole = storedRoleId.toUpperCase();
      if (uRole === "HO" || uRole === "HOD") {
        setRoleTitle("Head of Department");
      } else if (uRole === "NO" || uRole === "NODAL") {
        setRoleTitle("Nodal Officer");
      } else if (uRole === "DO" || uRole === "DEO") {
        setRoleTitle("Data Entry Operator");
      }
    }

    // Fetch metrics from backend API
    async function fetchMetrics() {
      try {
        const res = await fetch(`${API_BASE}/api/authority/dashboard/metrics`);
        if (res.ok) {
          const data = await res.json();
          if (data.total_registered_plots) setTotalPlots(data.total_registered_plots);
          if (data.total_land_sqm) setTotalLandSqm(data.total_land_sqm);
          if (data.total_land_ha) setTotalLandHa(data.total_land_ha);
          if (data.occupied_land_sqm) setOccupiedSqm(data.occupied_land_sqm);
          if (data.occupied_land_ha) setOccupiedHa(data.occupied_land_ha);
          if (data.vacant_land_sqm) setVacantSqm(data.vacant_land_sqm);
          if (data.vacant_land_ha) setVacantHa(data.vacant_land_ha);
          if (data.pending_land_sqm) setPendingSqm(data.pending_land_sqm);
          if (data.pending_land_ha) setPendingHa(data.pending_land_ha);

          if (data.expiry_timeline) setExpiryTimeline(data.expiry_timeline);
          if (data.occupancy_split) setOccupancySplit(data.occupancy_split);
          if (data.recent_applications) setRecentApps(data.recent_applications);
        }
      } catch (err) {
        console.warn("Using default database metrics fallback:", err);
      }
    }

    fetchMetrics();
  }, []);

  // Live tenant search — triggers on any search input change
  useEffect(() => {
    if (!searchFilter.trim() || activeTab !== "tenants") {
      setSearchResults(null);
      setSelectedTenant(null);
      return;
    }
    const timer = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/authority/tenants/search?q=${encodeURIComponent(searchFilter.trim())}`);
        if (res.ok) {
          const data: ApplicationRow[] = await res.json();
          setSearchResults(data);
          // Auto-select if exactly 1 result for an ID search
          const q = searchFilter.trim().toUpperCase();
          if (data.length === 1 && (q.startsWith("TNT-") || q.startsWith("TN-") || /^\d+$/.test(q))) {
            setSelectedTenant(data[0]);
          } else {
            setSelectedTenant(null);
          }
        }
      } catch {
        // On error, fall back to client-side filter
        setSearchResults(null);
      } finally {
        setSearchLoading(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [searchFilter, activeTab]);

  // Left Sidebar Navigation Configuration
  const sidebarNav: NavItem[] = [
    {
      to: "/authority/dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      active: activeTab === "overview",
      onClick: () => setActiveTab("overview"),
    },
    {
      to: "/authority/dashboard",
      label: "Tenants",
      icon: Users,
      active: activeTab === "tenants",
      onClick: () => setActiveTab("tenants"),
    },
    {
      to: "/ai-chat",
      label: "AI Assistant",
      icon: Bot,
      onClick: () => navigate({ to: "/ai-chat" }),
    },
  ];

  // Use live search results if available, else client-side filter of loaded rows
  const displayRows = searchResults !== null
    ? searchResults
    : recentApps.filter(
        (app) =>
          !searchFilter ||
          app.tenant_name.toLowerCase().includes(searchFilter.toLowerCase()) ||
          app.tenant_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
          (app.tenancy_id && app.tenancy_id.toLowerCase().includes(searchFilter.toLowerCase())) ||
          (app.person_name && app.person_name.toLowerCase().includes(searchFilter.toLowerCase())) ||
          app.purpose.toLowerCase().includes(searchFilter.toLowerCase()) ||
          app.tenancy_type.toLowerCase().includes(searchFilter.toLowerCase())
      );

  return (
    <DashboardShell
      title={`Welcome, ${userName}`}
      subtitle={`${roleTitle} | Admin ID: ${adminId}`}
      role={roleTitle}
      user={userName}
      nav={sidebarNav}
    >
      {/* Officer Designation Banner */}
      <div className="mb-6 flex items-center justify-between rounded-lg border border-navy/10 bg-gradient-to-r from-navy/5 via-surface to-gold/10 p-4 shadow-sm">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Officer Designation</div>
          <div className="font-display text-lg font-bold text-navy">{roleTitle}</div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Logged in as <span className="font-semibold text-foreground">{userName}</span> · Admin ID: <span className="font-semibold text-foreground">{adminId}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-navy text-navy-foreground text-xs font-semibold px-3 py-1.5 shadow-sm">
            <ShieldCheck className="mr-1.5 h-3.5 w-3.5 inline text-gold" /> {roleTitle}
          </Badge>
        </div>
      </div>

      {/* ── OVERVIEW & LAND STATISTICS VIEW ── */}
      {activeTab === "overview" && (
        <>
          {/* 5 Live Database KPI Stat Cards */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <KPI 
              label="Total Registered Plots" 
              value={totalPlots} 
              subtext="From public.plot table" 
              icon={Layers} 
              tint="bg-navy/10 text-navy" 
            />
            <KPI 
              label="Total Land Area" 
              value={totalLandSqm} 
              subtext={`Equivalent to ${totalLandHa}`} 
              icon={LandPlot} 
              tint="bg-navy/10 text-navy" 
            />
            <KPI 
              label="Occupied Land (Status: A)" 
              value={occupiedSqm} 
              subtext={`${occupiedHa} (Approved)`} 
              icon={Building2} 
              tint="bg-gov-green/10 text-gov-green" 
            />
            <KPI 
              label="Vacant Land (Status: V)" 
              value={vacantSqm} 
              subtext={`${vacantHa} (Available)`} 
              icon={LandPlot} 
              tint="bg-port/10 text-port" 
            />
            <KPI 
              label="Registered / Pending (Status: RG)" 
              value={pendingSqm} 
              subtext={`${pendingHa} (In Process)`} 
              icon={Clock} 
              tint="bg-gold/20 text-navy" 
            />
          </section>

          {/* Charts Section */}
          <section className="mt-6 max-w-xl">
            {/* Land Occupancy Split (Donut Chart) */}
            <div className="card-gov p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="font-display text-base font-semibold text-navy">
                    Land Occupancy Split
                  </div>
                  <div className="text-xs text-muted-foreground">By hectare distribution</div>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={occupancySplit}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={3}
                    >
                      {occupancySplit.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: "11px" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>

        </>
      )}

      {/* ── TAB: TENANTS MANAGEMENT ── */}
      {activeTab === "tenants" && (
        <section className="space-y-6">
          <div className="card-gov p-6">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
              <div>
                <h2 className="font-display text-lg font-bold text-navy flex items-center gap-2">
                  <Users className="h-5 w-5" /> Registered Port Tenants Directory
                </h2>
                {searchResults !== null && (
                  <p className="text-xs text-navy font-semibold mt-0.5">
                    {displayRows.length} result{displayRows.length !== 1 ? "s" : ""} found
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="relative w-72">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by Tenant ID, Tenancy ID, or name…"
                    className="pl-8 text-xs"
                    value={searchFilter}
                    onChange={(e) => {
                      setSearchFilter(e.target.value);
                      setSelectedTenant(null);
                    }}
                  />
                  {searchLoading && (
                    <span className="absolute right-2.5 top-2.5 h-4 w-4 animate-spin rounded-full border-2 border-navy border-t-transparent" />
                  )}
                </div>
                {searchFilter && (
                  <Button variant="ghost" size="sm" className="h-8 text-xs text-muted-foreground" onClick={() => { setSearchFilter(""); setSearchResults(null); setSelectedTenant(null); }}>
                    Clear
                  </Button>
                )}
              </div>
            </div>

            {/* ── FULL DETAIL CARD when exact tenant is selected ── */}
            {selectedTenant && (
              <div className="mb-6 rounded-xl border border-navy/20 bg-gradient-to-br from-navy/5 to-surface p-5 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-navy/10">
                      <Users className="h-4 w-4 text-navy" />
                    </div>
                    <div>
                      <div className="font-display text-base font-bold text-navy">{selectedTenant.tenant_name}</div>
                      <div className="text-xs text-muted-foreground">Full Tenant Profile</div>
                    </div>
                  </div>
                  <button onClick={() => setSelectedTenant(null)} className="text-xs text-muted-foreground hover:text-navy transition-colors">✕ Close</button>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                  {[
                    { label: "Tenant ID", value: selectedTenant.tenant_id },
                    { label: "Tenancy ID", value: selectedTenant.tenancy_id || "N/A" },
                    { label: "Contact Person", value: selectedTenant.person_name || "N/A" },
                    { label: "Organization", value: selectedTenant.tenant_name },
                    { label: "Tenancy Type", value: selectedTenant.tenancy_type },
                    { label: "Purpose", value: selectedTenant.purpose },
                    { label: "Commencement", value: selectedTenant.duration_from },
                    { label: "Status", value: selectedTenant.status },
                    ...(selectedTenant.pan_number ? [{ label: "PAN Number", value: selectedTenant.pan_number }] : []),
                    ...(selectedTenant.gst_number ? [{ label: "GST Number", value: selectedTenant.gst_number }] : []),
                    ...(selectedTenant.username ? [{ label: "Username", value: selectedTenant.username }] : []),
                  ].map(({ label, value }) => (
                    <div key={label} className="rounded-lg bg-white/60 border border-border p-3">
                      <div className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wide mb-0.5">{label}</div>
                      <div className="text-xs font-semibold text-navy break-all">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-surface/60 text-muted-foreground uppercase font-semibold">
                    <th className="py-3 px-4">Tenancy ID</th>
                    <th className="py-3 px-4">Organization / Tenant</th>
                    <th className="py-3 px-4">Contact Person</th>
                    <th className="py-3 px-4">Tenancy Type</th>
                    <th className="py-3 px-4">Purpose</th>
                    <th className="py-3 px-4">Commencement</th>
                    <th className="py-3 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {displayRows.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground text-xs">
                        {searchFilter ? "No tenants found matching your search." : "Loading tenant directory…"}
                      </td>
                    </tr>
                  )}
                  {displayRows.map((row, idx) => (
                    <tr
                      key={idx}
                      className={`hover:bg-surface/40 transition-colors cursor-pointer ${selectedTenant?.tenant_id === row.tenant_id ? "bg-navy/5" : ""}`}
                      onClick={() => setSelectedTenant(row)}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-navy">{row.tenancy_id || row.tenant_id}</td>
                      <td className="py-3 px-4 font-semibold text-foreground">{row.tenant_name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{row.person_name || "—"}</td>
                      <td className="py-3 px-4 text-muted-foreground">{row.tenancy_type}</td>
                      <td className="py-3 px-4 text-muted-foreground max-w-[200px] truncate" title={row.purpose}>{row.purpose}</td>
                      <td className="py-3 px-4 font-mono text-muted-foreground">{row.duration_from}</td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-gov-green/10 text-gov-green font-semibold border border-gov-green/20">
                          {row.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!searchFilter && recentApps.length > 0 && (
              <p className="mt-3 text-[10px] text-muted-foreground text-right">
                Showing {recentApps.length} records. Search by Tenant ID or Tenancy ID to find a specific tenant.
              </p>
            )}
          </div>
        </section>
      )}

      {/* ── TAB: LEASE MANAGEMENT ── */}
      {activeTab === "lease_management" && (
        <section className="space-y-6">
          <div className="card-gov p-6">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
              <div>
                <h2 className="font-display text-lg font-bold text-navy flex items-center gap-2">
                  <ClipboardList className="h-5 w-5" /> Lease Agreement Management
                </h2>
                <p className="text-xs text-muted-foreground">
                  Active lease terms, duration from <code className="font-mono text-navy">applicant_property_mapping</code>
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-surface/60 text-muted-foreground uppercase font-semibold">
                    <th className="py-3 px-4">Tenancy ID</th>
                    <th className="py-3 px-4">Tenant Name</th>
                    <th className="py-3 px-4">Lease Term</th>
                    <th className="py-3 px-4">Start Date</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {recentApps.map((row, idx) => (
                    <tr key={idx} className="hover:bg-surface/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-navy">{row.tenant_id}</td>
                      <td className="py-3 px-4 font-semibold text-foreground">{row.tenant_name}</td>
                      <td className="py-3 px-4 text-muted-foreground">{row.tenancy_type}</td>
                      <td className="py-3 px-4 font-mono text-muted-foreground">{row.duration_from}</td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-gov-green/10 text-gov-green font-semibold border border-gov-green/20">
                          {row.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button variant="outline" size="sm" className="h-7 text-xs">
                          <Download className="mr-1 h-3 w-3" /> Agreement
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </DashboardShell>
  );
}
