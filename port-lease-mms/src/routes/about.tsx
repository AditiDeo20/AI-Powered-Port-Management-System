import { createFileRoute } from "@tanstack/react-router";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import { ShieldCheck, Cpu, Database, ScrollText } from "lucide-react";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [{ title: "About | Port Management System" }],
  }),
  component: About,
});

function About() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <GovHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12">
        <div className="text-xs font-semibold uppercase tracking-widest text-gov-green">
          About the Platform
        </div>
        <h1 className="mt-2 font-display text-3xl font-semibold text-navy sm:text-4xl">
          Modernising port land governance with AI
        </h1>
        <p className="mt-4 max-w-3xl text-base leading-relaxed text-foreground/80">
          The Port Estate & Land Management System (AI-PMS) is an enterprise
          platform for Major Port Authorities. It brings
          together tenant services, authority operations, and a knowledge-grounded AI
          assistant into a single secure platform serving major port estates.
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {[
            {
              icon: ShieldCheck,
              t: "Secure by Design",
              d: "JWT authentication, role-based access control and row-level security.",
            },
            {
              icon: Cpu,
              t: "AI Assistance",
              d: "Hybrid RAG and GraphRAG grounded in official Government policies.",
            },
            {
              icon: Database,
              t: "Trusted Data",
              d: "PostgreSQL with pgvector for reliable retrieval and analytics.",
            },
            {
              icon: ScrollText,
              t: "Audit Ready",
              d: "Full audit trails across every user and system action.",
            },
          ].map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.t} className="card-gov p-6">
                <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-md bg-secondary text-navy">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="font-display text-base font-semibold text-navy">{f.t}</div>
                <p className="mt-1 text-sm text-muted-foreground">{f.d}</p>
              </div>
            );
          })}
        </div>
      </main>
      <GovFooter />
    </div>
  );
}
