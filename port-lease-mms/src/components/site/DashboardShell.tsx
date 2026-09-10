import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { Bell, LogOut, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import type { ReactNode } from "react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  id?: string;
  active?: boolean;
  onClick?: () => void;
}

interface Props {
  title: string;
  subtitle?: string;
  role: string;
  user: string;
  nav: NavItem[];
  children: ReactNode;
}

export function DashboardShell({ title, subtitle, role, user, nav, children }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const initials = user
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("");

  return (
    <div className="flex min-h-screen bg-surface">
      {/* Sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-border bg-white lg:flex lg:flex-col">
        <div className="gov-strip" aria-hidden />
        <div className="flex items-center gap-2 border-b border-border px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy text-navy-foreground">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="font-display text-sm font-semibold text-navy">
              Port Estate & Land Management (AI-PMS)
            </div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {role}
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {nav.map((item) => {
            const isSelected = item.active !== undefined ? item.active : location.pathname === item.to;
            const Icon = item.icon;
            
            return (
              <button
                key={item.label}
                onClick={() => {
                  if (item.onClick) {
                    item.onClick();
                  } else {
                    navigate({ to: item.to as any });
                  }
                }}
                className={
                  "w-full flex items-center justify-between rounded-md px-3 py-2.5 text-sm font-medium transition-all text-left " +
                  (isSelected
                    ? "bg-navy text-navy-foreground font-semibold shadow-sm"
                    : "text-foreground/80 hover:bg-secondary hover:text-navy")
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </div>
                {item.label.toLowerCase().includes("active thread") && (
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-gov-green opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-gov-green"></span>
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="border-t border-border p-3">
          <button
            onClick={() => {
              if (role.toLowerCase().includes("tenant")) {
                localStorage.removeItem("tenantToken");
                localStorage.removeItem("tenantName");
                localStorage.removeItem("tenantId");
                navigate({ to: "/tenant/login" as any });
              } else {
                localStorage.removeItem("authorityId");
                localStorage.removeItem("authorityUserName");
                localStorage.removeItem("authorityUsername");
                localStorage.removeItem("authorityRoleId");
                navigate({ to: "/authority/login" as any });
              }
            }}
            className="w-full flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-foreground/80 hover:bg-secondary transition-colors text-left"
          >
            <LogOut className="h-4 w-4" /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-border bg-white">
          <div className="flex items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <div>
              <h1 className="font-display text-lg font-semibold text-navy sm:text-xl">
                {title}
              </h1>
              {subtitle && (
                <p className="text-xs text-muted-foreground">{subtitle}</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              <Badge
                variant="outline"
                className="hidden gap-1.5 border-gov-green/30 bg-gov-green/10 text-gov-green sm:inline-flex"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-gov-green" />
                Secure Session
              </Badge>
              <Button variant="ghost" size="icon" aria-label="Notifications">
                <Bell className="h-5 w-5" />
              </Button>
              <div className="flex items-center gap-2">
                <Avatar className="h-9 w-9 border border-border">
                  <AvatarFallback className="bg-navy text-navy-foreground text-xs">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <div className="hidden text-right sm:block">
                  <div className="text-sm font-medium text-foreground">{user}</div>
                  <div className="text-[11px] text-muted-foreground">{role}</div>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
