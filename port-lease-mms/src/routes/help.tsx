import { createFileRoute } from "@tanstack/react-router";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const Route = createFileRoute("/help")({
  head: () => ({ meta: [{ title: "Help & FAQ | Port Management System" }] }),
  component: Help,
});

const faqs = [
  ["How do I register as a new tenant?", "Visit the Tenant Portal and click Register. You'll be guided through document upload and verification by the Nodal Officer."],
  ["How is my data protected?", "The system uses JWT authentication, RBAC and PostgreSQL Row Level Security. All actions are audit-logged."],
  ["Which languages are supported?", "The portal currently supports English, हिन्दी and मराठी."],
  ["How does the AI Assistant work?", "It uses Hybrid RAG and GraphRAG over official Government policy documents and lease records, providing source citations and confidence scores."],
  ["Whom to contact for grievances?", "Please use the Contact page or dial the toll-free helpline listed there."],
];

function Help() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <GovHeader />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
        <h1 className="font-display text-3xl font-semibold text-navy">Help & FAQ</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Common questions from tenants and authority users.
        </p>
        <div className="card-gov mt-8 p-2">
          <Accordion type="single" collapsible>
            {faqs.map(([q, a], i) => (
              <AccordionItem key={i} value={`q${i}`}>
                <AccordionTrigger className="px-4 text-left text-sm font-medium text-navy">
                  {q}
                </AccordionTrigger>
                <AccordionContent className="px-4 text-sm text-foreground/80">
                  {a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </main>
      <GovFooter />
    </div>
  );
}
