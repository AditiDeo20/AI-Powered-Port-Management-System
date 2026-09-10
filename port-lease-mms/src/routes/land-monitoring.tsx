import { createFileRoute } from "@tanstack/react-router";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Layers, MapPin } from "lucide-react";

export const Route = createFileRoute("/land-monitoring")({
  head: () => ({
    meta: [
      { title: "Land Monitoring | Port Management System" },
      { name: "description", content: "Interactive GIS view of port land status." },
    ],
  }),
  component: LandMonitoring,
});

const legend = [
  { label: "Active Lease", color: "bg-gov-green", text: "text-gov-green" },
  { label: "Expired Lease", color: "bg-destructive", text: "text-destructive" },
  { label: "Renewal Due", color: "bg-gold", text: "text-navy" },
  { label: "Vacant Land", color: "bg-port", text: "text-port" },
];

const parcels = [
  { id: "A-101", status: "active", top: "18%", left: "14%" },
  { id: "A-102", status: "renewal", top: "22%", left: "28%" },
  { id: "A-103", status: "active", top: "30%", left: "42%" },
  { id: "A-104", status: "vacant", top: "38%", left: "22%" },
  { id: "A-105", status: "expired", top: "46%", left: "56%" },
  { id: "A-106", status: "active", top: "52%", left: "38%" },
  { id: "A-107", status: "renewal", top: "60%", left: "70%" },
  { id: "A-108", status: "vacant", top: "68%", left: "48%" },
  { id: "A-109", status: "active", top: "74%", left: "24%" },
  { id: "A-110", status: "expired", top: "34%", left: "78%" },
  { id: "A-111", status: "active", top: "58%", left: "18%" },
  { id: "A-112", status: "active", top: "80%", left: "66%" },
];

const statusColor: Record<string, string> = {
  active: "bg-gov-green",
  expired: "bg-destructive",
  renewal: "bg-gold",
  vacant: "bg-port",
};

function LandMonitoring() {
  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <GovHeader />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-gov-green">
              GIS Monitoring
            </div>
            <h1 className="mt-1 font-display text-2xl font-semibold text-navy sm:text-3xl">
              Port Land Monitoring
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Real-time status of leased and vacant parcels across major Indian ports.
            </p>
          </div>
          <Button variant="outline">
            <Layers className="mr-1.5 h-4 w-4" /> Layers
          </Button>
        </div>

        {/* Filters */}
        <div className="card-gov mb-4 grid gap-3 p-4 sm:grid-cols-4">
          <FilterSelect label="Port" placeholder="All ports" options={["JNPT", "Kandla", "Mumbai", "Chennai", "Kolkata"]} />
          <FilterSelect label="District" placeholder="All districts" options={["Raigad", "Kutch", "Chennai", "Kolkata"]} />
          <FilterSelect label="Lease Type" placeholder="All types" options={["Container", "Bulk Cargo", "Warehousing", "Logistics"]} />
          <FilterSelect label="Status" placeholder="All statuses" options={["Active", "Expired", "Renewal Due", "Vacant"]} />
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
          {/* Map */}
          <div className="card-gov relative overflow-hidden">
            <div className="relative h-[520px] bg-gradient-to-br from-navy/5 via-port/5 to-gov-green/10">
              <div
                className="absolute inset-0 opacity-50"
                style={{
                  backgroundImage:
                    "linear-gradient(hsl(215 30% 40% / 0.15) 1px, transparent 1px), linear-gradient(90deg, hsl(215 30% 40% / 0.15) 1px, transparent 1px)",
                  backgroundSize: "32px 32px",
                }}
              />
              {/* Water shape */}
              <div className="absolute right-0 top-0 h-full w-1/3 bg-port/20" />
              {parcels.map((p) => (
                <div
                  key={p.id}
                  className="group absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ top: p.top, left: p.left }}
                >
                  <div className={`h-4 w-4 rounded-full ${statusColor[p.status]} ring-2 ring-white shadow-md`} />
                  <div className="pointer-events-none absolute left-1/2 top-full mt-1 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-white px-2 py-1 text-[10px] font-medium text-foreground shadow group-hover:block">
                    Plot {p.id} · {p.status.toUpperCase()}
                  </div>
                </div>
              ))}
              <div className="absolute bottom-3 left-3 rounded-md border border-border bg-white/95 px-3 py-2 shadow">
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Legend
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {legend.map((l) => (
                    <div key={l.label} className="flex items-center gap-1.5 text-[11px]">
                      <span className={`h-2 w-2 rounded-full ${l.color}`} />
                      <span className={l.text}>{l.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="absolute right-3 top-3 rounded-md border border-border bg-white/95 px-2.5 py-1.5 text-[11px] font-medium text-foreground shadow">
                <MapPin className="mr-1 inline h-3 w-3 text-navy" />
                JNPT · Zone B
              </div>
            </div>
          </div>

          {/* Details panel */}
          <aside className="card-gov flex flex-col p-5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Selected Parcel
            </div>
            <div className="mt-1 font-display text-lg font-semibold text-navy">
              Plot A-105
            </div>
            <Badge className="mt-2 w-fit bg-destructive text-destructive-foreground hover:bg-destructive">
              Expired Lease
            </Badge>

            <div className="mt-4 space-y-2 text-sm">
              {[
                ["Port", "JNPT"],
                ["District", "Raigad"],
                ["Area", "6,120 sq.m."],
                ["Lease Type", "Container"],
                ["Tenant", "M/s Coastal Freight"],
                ["Expired On", "12 Jun 2026"],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center justify-between border-b border-border pb-1.5 text-sm">
                  <span className="text-muted-foreground">{k}</span>
                  <span className="font-medium text-foreground">{v}</span>
                </div>
              ))}
            </div>
            <div className="mt-auto space-y-2 pt-4">
              <Button className="w-full bg-navy text-navy-foreground hover:bg-navy/90">
                Initiate Renewal
              </Button>
              <Button variant="outline" className="w-full">
                View Full Record
              </Button>
            </div>
          </aside>
        </div>
      </main>
      <GovFooter />
    </div>
  );
}

function FilterSelect({
  label,
  placeholder,
  options,
}: {
  label: string;
  placeholder: string;
  options: string[];
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-muted-foreground">{label}</label>
      <Select>
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o} value={o.toLowerCase()}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
