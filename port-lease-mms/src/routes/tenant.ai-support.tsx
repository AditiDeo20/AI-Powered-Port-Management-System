import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DashboardShell, type NavItem } from "@/components/site/DashboardShell";
import { TenantChatbot } from "@/components/tenant-chatbot/TenantChatbot";
import {
  LayoutDashboard,
  FileText,
  UserCheck,
  Bot,
  Activity,
} from "lucide-react";

export const Route = createFileRoute("/tenant/ai-support")({
  head: () => ({
    meta: [{ title: "Tenant AI Support | Port Management System" }],
  }),
  component: TenantAiSupportPage,
});

const nav: NavItem[] = [
  { to: "/tenant/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/tenant/dashboard", label: "My Profile", icon: UserCheck },
  { to: "/tenant/dashboard", label: "Lease Agreements", icon: FileText },
  { to: "/tenant/ai-support", label: "AI Support", icon: Bot },
];

function TenantAiSupportPage() {
  const navigate = useNavigate();
  const [tenantName, setTenantName] = useState("Tenant User");
  const [tenantId, setTenantId] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("tenantToken");
    const name = localStorage.getItem("tenantName");
    const tid = localStorage.getItem("tenantId");

    if (!token && !name) {
      navigate({ to: "/tenant/login" });
      return;
    }

    if (name) setTenantName(name);
    if (tid) setTenantId(tid.startsWith("TNT-") ? tid : `TNT-${tid}`);
  }, [navigate]);

  return (
    <DashboardShell
      title="AI Land Lease Assistant"
      subtitle={`Tenant ID: ${tenantId || "TNT-Active"} | Source-grounded AI support for port land lease records & policies`}
      role="Tenant"
      user={tenantName}
      nav={nav}
    >
      <TenantChatbot />
    </DashboardShell>
  );
}
