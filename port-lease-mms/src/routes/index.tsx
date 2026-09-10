import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Bot,
  MapPin,
  LayoutDashboard,
  Lock,
  ShieldCheck,
  Database,
  BrainCircuit,
  ScrollText,
  Users,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import heroImg from "@/assets/port-hero.jpg";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Home | Major Port Authority — AI-PMS" },
      {
        name: "description",
        content:
          "AI powered platform for major port land lease records, tenant services and authority monitoring.",
      },
    ],
  }),
  component: HomePage,
});

const features = [
  {
    icon: Bot,
    title: "AI Chat Assistant",
    desc: "Ask questions about leases, land records and Government policies with cited sources.",
    tint: "text-navy",
  },
  {
    icon: Users,
    title: "Tenant Services",
    desc: "View lease information, track renewals and download agreements.",
    tint: "text-port",
  },
  {
    icon: LayoutDashboard,
    title: "Authority Dashboard",
    desc: "Manage tenants, leases, and authority monitoring from a single enterprise console.",
    tint: "text-gov-green",
  },
  {
    icon: MapPin,
    title: "Land Monitoring",
    desc: "Track port plot allocations, lease tenures, and spatial GIS boundaries.",
    tint: "text-navy",
  },
];

const badges = [
  { label: "JWT Auth", icon: Lock },
  { label: "RBAC", icon: ShieldCheck },
  { label: "Row Level Security", icon: ShieldCheck },
  { label: "Hybrid RAG", icon: BrainCircuit },
  { label: "GraphRAG", icon: BrainCircuit },
  { label: "Qwen 2.5", icon: BrainCircuit },
  { label: "PostgreSQL", icon: Database },
  { label: "pgvector", icon: Database },
  { label: "Audit Logging", icon: ScrollText },
];

function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <GovHeader />

      {/* Hero */}
      <section className="relative isolate overflow-hidden bg-navy text-white">
        <img
          src={heroImg}
          alt="Aerial view of an Indian port with cargo cranes and container ships"
          width={1920}
          height={1080}
          className="absolute inset-0 -z-10 h-full w-full object-cover opacity-30"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-navy via-navy/85 to-navy/60" />
        <div className="mx-auto max-w-7xl px-4 py-16 sm:py-20 lg:py-28">
          <Badge className="mb-4 border-white/20 bg-white/10 text-white hover:bg-white/10">
            <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-gold" />
            Major Port Authority · AI Powered
          </Badge>
          <h1 className="max-w-4xl font-display text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl">
            AI Powered Port Land Lease Management Assistant
          </h1>
          <p className="mt-4 max-w-3xl text-base text-white/85 sm:text-lg">
            Secure intelligent assistant for managing land lease records, policy documents,
            tenant services, and authority operations using Hybrid RAG, GraphRAG, and AI.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button
              asChild
              size="lg"
              className="bg-gold text-gold-foreground hover:bg-gold/90"
            >
              <Link to="/tenant/login">
                Tenant Portal <ArrowRight className="ml-1.5 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-white/30 bg-white/5 text-white hover:bg-white/10 hover:text-white"
            >
              <Link to="/authority/login">
                Authority Portal
              </Link>
            </Button>
          </div>

          <div className="mt-10 grid max-w-3xl grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ["13", "Major Ports"],
              ["4,820", "Active Leases"],
            ].map(([n, l]) => (
              <div key={l} className="rounded-lg border border-white/10 bg-white/5 p-3">
                <div className="font-display text-2xl font-semibold text-gold">{n}</div>
                <div className="text-xs text-white/70">{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-7xl px-4 py-16">
        <div className="mb-10 max-w-2xl">
          <div className="text-xs font-semibold uppercase tracking-widest text-gov-green">
            Platform Modules
          </div>
          <h2 className="mt-2 font-display text-2xl font-semibold text-navy sm:text-3xl">
            One secure system for port land governance
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Purpose-built for port authorities, tenants and policy officers.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="card-gov group p-6 transition-shadow hover:shadow-elevated"
              >
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-md bg-secondary">
                  <Icon className={`h-5 w-5 ${f.tint}`} />
                </div>
                <div className="font-display text-base font-semibold text-navy">
                  {f.title}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{f.desc}</p>
                <div className="mt-4 h-0.5 w-8 bg-gold" />
              </div>
            );
          })}
        </div>
      </section>

      {/* Security */}
      <section className="bg-surface py-16">
        <div className="mx-auto max-w-7xl px-4">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <div className="text-xs font-semibold uppercase tracking-widest text-gov-green">
                Security & Architecture
              </div>
              <h2 className="mt-2 font-display text-2xl font-semibold text-navy sm:text-3xl">
                Enterprise-grade, audited, compliant
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                Built to enterprise IT security standards with end-to-end
                encryption, role-based access, and full audit trails.
              </p>
            </div>
            <Button asChild variant="outline" className="border-navy text-navy hover:bg-navy hover:text-navy-foreground">
              <Link to="/about">Architecture overview</Link>
            </Button>
          </div>
          <div className="mt-8 flex flex-wrap gap-2">
            {badges.map((b) => {
              const Icon = b.icon;
              return (
                <div
                  key={b.label}
                  className="inline-flex items-center gap-2 rounded-md border border-border bg-white px-3 py-2 text-xs font-medium text-foreground/80"
                >
                  <Icon className="h-3.5 w-3.5 text-navy" />
                  {b.label}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <GovFooter />
    </div>
  );
}
