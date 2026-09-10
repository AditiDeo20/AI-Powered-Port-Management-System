import { Link } from "@tanstack/react-router";
import { Anchor, Globe, Menu } from "lucide-react";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

const navLinks = [
  { to: "/", label: "Home" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
  { to: "/help", label: "Help" },
];

export function GovHeader() {
  const [open, setOpen] = useState(false);

  // Check if current view is inside Tenant portal
  const isTenantPortal = typeof window !== "undefined" && (
    window.location.pathname.startsWith("/tenant") ||
    (Boolean(localStorage.getItem("tenantToken")) && !localStorage.getItem("authorityId"))
  );

  // Hide general public links if inside Tenant portal
  const activeNavLinks = isTenantPortal ? [] : navLinks;
  const logoHref = isTenantPortal ? "/tenant/dashboard" : "/";

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white">
      <div className="gov-strip" aria-hidden />
      {/* Top identification bar */}
      <div className="bg-navy text-navy-foreground">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-2 text-xs">
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline">Major Port Authority | Estate & Land Management Portal</span>
            <span className="hidden md:inline opacity-80">
              Port Estate & Land Management System (AI-PMS)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Globe className="h-3.5 w-3.5 opacity-80" />
            <Select defaultValue="en">
              <SelectTrigger className="h-7 w-[130px] border-white/20 bg-white/5 text-xs text-white focus:ring-white/30">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="hi">हिन्दी</SelectItem>
                <SelectItem value="mr">मराठी</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Emblem + title bar */}
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <Link to={logoHref} className="flex items-center gap-3 transition-opacity hover:opacity-90">
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-navy/20 bg-white shadow-2xs">
            <Anchor className="h-6 w-6 text-navy" />
          </div>
          <div className="hidden sm:block">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Major Port Authority
            </div>
            <div className="font-display text-sm font-semibold text-navy sm:text-base">
              Port Estate & Land Management System (AI-PMS)
            </div>
          </div>
          <div className="sm:hidden">
            <Anchor className="h-5 w-5 text-navy" />
          </div>
        </Link>

        {activeNavLinks.length > 0 && (
          <nav className="hidden items-center gap-1 lg:flex">
            {activeNavLinks.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                activeOptions={{ exact: l.to === "/" }}
                activeProps={{ className: "text-navy bg-secondary" }}
                className="rounded-md px-3 py-2 text-sm font-medium text-foreground/80 transition-colors hover:bg-secondary hover:text-navy"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        )}

        {activeNavLinks.length > 0 && (
          <div className="flex items-center gap-2 lg:hidden">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon" aria-label="Open menu">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-72">
                <div className="mt-8 flex flex-col gap-1">
                  {activeNavLinks.map((l) => (
                    <Link
                      key={l.to}
                      to={l.to}
                      onClick={() => setOpen(false)}
                      className="rounded-md px-3 py-2 text-sm font-medium text-foreground hover:bg-secondary"
                    >
                      {l.label}
                    </Link>
                  ))}
                </div>
              </SheetContent>
            </Sheet>
          </div>
        )}
      </div>
    </header>
  );
}
