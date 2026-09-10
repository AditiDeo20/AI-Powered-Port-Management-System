import { createFileRoute } from "@tanstack/react-router";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Mail, Phone, MapPin } from "lucide-react";

export const Route = createFileRoute("/contact")({
  head: () => ({ meta: [{ title: "Contact | Port Management System" }] }),
  component: Contact,
});

function Contact() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <GovHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12">
        <h1 className="font-display text-3xl font-semibold text-navy">Contact Us</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Reach out to the Indian Port Authority for support or grievances.
        </p>
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_320px]">
          <form className="card-gov space-y-4 p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="name">Full Name</Label>
                <Input id="name" placeholder="Your name" />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" placeholder="you@example.com" />
              </div>
            </div>
            <div>
              <Label htmlFor="sub">Subject</Label>
              <Input id="sub" placeholder="How can we help?" />
            </div>
            <div>
              <Label htmlFor="msg">Message</Label>
              <Textarea id="msg" rows={5} placeholder="Describe your query..." />
            </div>
            <Button className="bg-navy text-navy-foreground hover:bg-navy/90">
              Send Message
            </Button>
          </form>
          <aside className="space-y-3">
            {[
              { icon: MapPin, t: "Address", d: "Transport Bhawan, New Delhi — 110001" },
              { icon: Mail, t: "Email", d: "support-portlease@gov.in" },
              { icon: Phone, t: "Helpline", d: "1800-11-0000 (Toll Free)" },
            ].map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.t} className="card-gov flex items-start gap-3 p-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary text-navy">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-navy">{c.t}</div>
                    <div className="text-xs text-muted-foreground">{c.d}</div>
                  </div>
                </div>
              );
            })}
          </aside>
        </div>
      </main>
      <GovFooter />
    </div>
  );
}
