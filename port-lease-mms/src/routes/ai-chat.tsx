import { useState, useEffect, useRef } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { jsPDF } from "jspdf";
import { GovHeader } from "@/components/site/GovHeader";
import { GovFooter } from "@/components/site/GovFooter";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Bot,
  RefreshCw,
  Sparkles,
  ArrowLeft,
  MessageSquare,
  Lock,
  Edit3,
  Send,
  UserCheck,
  Building,
  FileText,
  History,
  CheckCircle2,
  XCircle,
  RotateCcw,
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  Users,
  User,
  Clock,
  Copy,
  Check,
  FileCheck,
  Square,
  Download,
  UploadCloud,
  Paperclip,
  Plus,
  Trash2,
} from "lucide-react";

const generateAndDownloadPdf = (filename: string, title: string, contentText: string) => {
  const cleanFilename = filename.toLowerCase().endsWith(".pdf") ? filename : `${filename}.pdf`;
  const cleanBody = contentText.replace(/\[Source:.*?\]/g, "").trim();

  // Extract sources for PDF document footer
  const dbMatches = contentText.match(/\[Source:\s*DB Table\s*-\s*([^\]]+)\]/gi) || [];
  const docMatches = contentText.match(/\[Source:\s*Doc\s*-\s*([^\]]+)\]/gi) || [];
  const dbSources = Array.from(new Set(dbMatches.map(m => {
    const r = /\[Source:\s*DB Table\s*-\s*([^\]]+)\]/i.exec(m);
    return r ? r[1].trim() : "DB Table";
  })));
  const docSources = Array.from(new Set(docMatches.map(m => {
    const r = /\[Source:\s*Doc\s*-\s*([^\]]+)\]/i.exec(m);
    return r ? r[1].trim() : "Doc";
  })));

  const pdf = new jsPDF({ unit: "pt", format: "a4" });

  // Header Title
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(16);
  pdf.setTextColor(15, 23, 42);
  pdf.text("Mumbai Port Authority — AI Assistant Report", 40, 50);

  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(100, 116, 139);
  pdf.text(`Title: ${title} | Date: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}`, 40, 68);

  pdf.setDrawColor(2, 132, 199);
  pdf.setLineWidth(1.5);
  pdf.line(40, 78, 555, 78);

  // Content Body
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(30, 41, 59);

  const splitText = pdf.splitTextToSize(cleanBody, 515);
  let cursorY = 100;

  for (let i = 0; i < splitText.length; i++) {
    if (cursorY > 780) {
      pdf.addPage();
      cursorY = 50;
    }
    pdf.text(splitText[i], 40, cursorY);
    cursorY += 14;
  }

  // Grounding & Citations Section
  if (dbSources.length > 0 || docSources.length > 0) {
    if (cursorY > 730) {
      pdf.addPage();
      cursorY = 50;
    }
    cursorY += 20;
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(10);
    pdf.setTextColor(2, 132, 199);
    pdf.text("FACTUAL GROUNDING & SOURCE CITATIONS:", 40, cursorY);
    cursorY += 16;

    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(9);
    pdf.setTextColor(71, 85, 105);
    const citeItems = [
      ...dbSources.map(s => `[DB Table: ${s}]`),
      ...docSources.map(s => `[Doc: ${s}]`)
    ];
    pdf.text(citeItems.join("  |  "), 40, cursorY);
  }

  // Directly save file into browser Downloads folder with 0 print window popups!
  pdf.save(cleanFilename);
};

export const Route = createFileRoute("/ai-chat")({
  head: () => ({
    meta: [{ title: "AI Assistant — Role-Based Agenda Workflow | Port Management System" }],
  }),
  component: RoleBasedAiAssistant,
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


interface OfficerUser {
  admin_id: string;
  name: string;
  user_name: string;
  email: string;
  role: string;
  department: string;
}

interface AgendaItem {
  agenda_id: string;
  title: string;
  tenancy_id: string | null;
  created_by: string;
  assigned_do: string | null;
  assigned_do_name?: string;
  assigned_no: string | null;
  assigned_no_name?: string;
  assigned_hod: string | null;
  assigned_hod_name?: string;
  current_owner: string;
  current_state: string;
  editing_version: number;
  is_read_only: boolean;
  created_at: string;
  latest_draft: string;
  final_approved_document?: string | null;
}

interface ContextCapsule {
  capsule_id: string;
  version: number;
  executive_summary: string;
  transferred_from: string;
  transferred_to: string;
  created_at: string;
}

interface ThreadMessage {
  message_id: string;
  sender_id: string;
  sender_name: string;
  sender_role: string;
  recipient_name: string;
  recipient_role: string;
  content: string;
  is_ai_response: boolean;
  ai_triggered_by: string;
  created_at: string;
}

const AestheticCitationsFooter = ({ text }: { text: string }) => {
  // If text is a guardrail refusal or SQL block, NEVER render citation badges!
  if (
    text.startsWith("Guardrail rejection:") ||
    text.startsWith("SQL Guardrail block:") ||
    text.toLowerCase().includes("guardrail rejection") ||
    text.toLowerCase().includes("scope is restricted")
  ) {
    return null;
  }

  const dbMatches = text.match(/\[Source:\s*DB Table\s*-\s*([^\]]+)\]/gi) || [];
  const docMatches = text.match(/\[Source:\s*Doc\s*-\s*([^\]]+)\]/gi) || [];

  if (dbMatches.length === 0 && docMatches.length === 0) return null;

  const dbSources = Array.from(new Set(dbMatches.map(m => {
    const r = /\[Source:\s*DB Table\s*-\s*([^\]]+)\]/i.exec(m);
    return r ? r[1].trim() : "PostgreSQL DB";
  })));

  const docSources = Array.from(new Set(docMatches.map(m => {
    const r = /\[Source:\s*Doc\s*-\s*([^\]]+)\]/i.exec(m);
    return r ? r[1].trim() : "Policy Document";
  })));

  return (
    <div className="mt-3 pt-2.5 border-t border-navy/15 flex flex-wrap items-center gap-2">
      <span className="text-[10px] font-bold text-navy/70 uppercase tracking-wider flex items-center gap-1">
        <Sparkles className="w-3 h-3 text-gold" /> Source Citations:
      </span>
      {dbSources.map((table, i) => (
        <Badge key={`db-${i}`} className="bg-blue-50 text-blue-800 border border-blue-200 text-[10px] px-2 py-0.5 font-bold flex items-center gap-1 shadow-2xs">
          <Building className="w-3 h-3 text-blue-600" /> 📊 DB Table: {table}
        </Badge>
      ))}
      {docSources.map((doc, i) => (
        <Badge key={`doc-${i}`} className="bg-amber-50 text-amber-900 border border-amber-200 text-[10px] px-2 py-0.5 font-bold flex items-center gap-1 shadow-2xs">
          <FileText className="w-3 h-3 text-amber-600" /> 📄 {doc}
        </Badge>
      ))}
    </div>
  );
};

const ResponseActionBar = ({
  text,
  msgId,
  onOpenPdfModal,
}: {
  text: string;
  msgId: string;
  onOpenPdfModal: (text: string) => void;
}) => {
  const [copied, setCopied] = useState(false);
  const isRefusal = (
    text.startsWith("Guardrail rejection:") ||
    text.startsWith("SQL Guardrail block:") ||
    text.toLowerCase().includes("guardrail rejection") ||
    text.toLowerCase().includes("scope is restricted")
  );
  const cleanBody = text.replace(/\[Source:.*?\]/g, "").replace(/\[OK\]\s*Citation\s*Verified/gi, "").trim();
  const wordCount = cleanBody.split(/\s+/).filter(Boolean).length;
  const showPdfDownload = !isRefusal && wordCount >= 50;

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanBody);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 flex items-center justify-between gap-2 pt-2 border-t border-border/50">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 text-[11px] font-semibold text-navy/80 hover:text-navy hover:bg-navy/10 gap-1 px-2"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-gov-green" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied!" : "Copy Response"}
        </Button>

        {showPdfDownload && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenPdfModal(text)}
            className="h-7 text-[11px] font-bold text-navy border-navy/30 hover:bg-navy hover:text-white gap-1 px-2.5 shadow-2xs transition-all"
          >
            <Download className="w-3.5 h-3.5 text-gold" /> Download PDF ({wordCount} words)
          </Button>
        )}
      </div>
      <span className="text-[10px] font-mono text-muted-foreground">{wordCount} words</span>
    </div>
  );
};

function RoleBasedAiAssistant() {
  const navigate = useNavigate();
  // ── Strict Session Lock ───────────────────
  const [isAuthChecking, setIsAuthChecking] = useState(true);
  const [activeRole, setActiveRole] = useState<"DO" | "NODAL" | "HOD">("DO");
  const [officerName, setOfficerName] = useState("Dealing Officer");
  const [userAdminId, setUserAdminId] = useState("565");
  const [userName, setUserName] = useState("sudhakark_do");

  // ── UI Tabs State ──────────────────────────
  const [mainTab, setMainTab] = useState<"sandbox" | "official">("sandbox");
  const [agendaDetailTab, setAgendaDetailTab] = useState<"thread" | "final_doc" | "capsules">("thread");

  // ── Officers Dropdown Data ────────────────
  const [dosList, setDosList] = useState<OfficerUser[]>([]);
  const [nodalList, setNodalList] = useState<OfficerUser[]>([]);
  const [hodsList, setHodsList] = useState<OfficerUser[]>([]);

  // ── Sandbox Messages State ────────────────
  const [sandboxMessages, setSandboxMessages] = useState<Array<{ sender: "user" | "ai"; text: string }>>([
    {
      sender: "ai",
      text: "Welcome to your AI Assistant. Ask private policy queries before forwarding draft to an agenda.",
    },
  ]);
  const [sandboxInput, setSandboxInput] = useState("");
  const [isSandboxAiLoading, setIsSandboxAiLoading] = useState(false);

  // ── Promote Sandbox Dialog ────────────────
  const [promoteDialogOpen, setPromoteDialogOpen] = useState(false);
  const [promoteTitle, setPromoteTitle] = useState("");
  const [promoteTenancyId, setPromoteTenancyId] = useState("");
  const [promoteDraftText, setPromoteDraftText] = useState("");

  // ── Agendas Data State ────────────────────
  const [agendas, setAgendas] = useState<AgendaItem[]>([]);
  const [selectedAgendaId, setSelectedAgendaId] = useState<string | null>(null);
  const [selectedAgenda, setSelectedAgenda] = useState<AgendaItem | null>(null);
  const [agendaMessages, setAgendaMessages] = useState<ThreadMessage[]>([]);
  const [agendaCapsules, setAgendaCapsules] = useState<ContextCapsule[]>([]);
  const [agendaInput, setAgendaInput] = useState("");
  const [isAiProcessingInThread, setIsAiProcessingInThread] = useState(false);
  const [copiedDoc, setCopiedDoc] = useState(false);

  // ── Working Draft & Handoff Panel State ──
  const [workingDraftText, setWorkingDraftText] = useState("");
  const [handoffTargetOfficer, setHandoffTargetOfficer] = useState("");
  const [handoffTargetOfficerName, setHandoffTargetOfficerName] = useState("");
  const [handoffRemarks, setHandoffRemarks] = useState("");
  const [isHandoffSubmitting, setIsHandoffSubmitting] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  // ── PDF Download Modal & Stop Controller States ──
  const [pdfModalOpen, setPdfModalOpen] = useState(false);
  const [pdfTargetText, setPdfTargetText] = useState("");
  const [pdfCustomFilename, setPdfCustomFilename] = useState("");

  // ── Dynamic Loading Indicator States ──────
  const [sandboxLoadingText, setSandboxLoadingText] = useState("Analyzing Port Land Policy database...");
  const [agendaLoadingText, setAgendaLoadingText] = useState("🤖 AI Assistant analyzing query & updating shared draft...");

  const sandboxAbortControllerRef = useRef<AbortController | null>(null);
  const agendaAbortControllerRef = useRef<AbortController | null>(null);

  const sandboxScrollRef = useRef<HTMLDivElement>(null);
  const agendaScrollRef = useRef<HTMLDivElement>(null);

  const unreadCount = agendas.filter((a) => !a.is_read_only && a.current_owner === userAdminId).length;

  const getDynamicLoadingSteps = (queryText: string) => {
    const q = queryText.toLowerCase();
    const isDb = q.includes("plot") || q.includes("rent") || q.includes("memo") || q.includes("table") || q.includes("bill") || q.includes("tenant") || q.includes("rate") || q.includes("area") || q.includes("sor") || q.includes("sql") || q.includes("database");
    const isDoc = q.includes("policy") || q.includes("manual") || q.includes("breach") || q.includes("clause") || q.includes("act") || q.includes("section") || q.includes("contract") || q.includes("sublet") || q.includes("law") || q.includes("legal");

    if (isDb && !isDoc) {
      return [
        "🔍 Classifying query route (SQL Database Engine)...",
        "📊 Fetching structured table records from PostgreSQL (pms_app schema)...",
        "⚡ Inspecting table columns & computing SQL distance metrics...",
        "✨ Structuring grounded answer & verifying DB citations..."
      ];
    } else if (isDoc && !isDb) {
      return [
        "🔍 Classifying query route (Vector Document Search)...",
        "📄 Searching policy documents & user_chunks (BGE-M3 1024-dim embeddings)...",
        "🧩 Extracting parent text chunks & page numbers...",
        "✨ Structuring grounded response with document citations..."
      ];
    } else {
      return [
        "🔍 Routing Multi-Hop query across Database & Vector Index...",
        "📊 Querying PostgreSQL database tables & 📄 policy vector chunks...",
        "🧩 Fusing structured database facts with unstructured policy text...",
        "✨ Synthesizing grounded response with source citations..."
      ];
    }
  };

  const startDynamicLoadingSteps = (queryText: string, setLoadingText: (t: string) => void) => {
    const steps = getDynamicLoadingSteps(queryText);
    setLoadingText(steps[0]);
    let idx = 0;
    const interval = setInterval(() => {
      idx++;
      if (idx < steps.length) {
        setLoadingText(steps[idx]);
      } else {
        clearInterval(interval);
      }
    }, 1100);
    return interval;
  };

  const handleOpenPdfModal = (text: string, title?: string) => {
    setPdfTargetText(text);
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    const tempName = `AI_Response_${dateStr}_${Math.floor(1000 + Math.random() * 9000)}`;
    setPdfCustomFilename(tempName);
    setPdfModalOpen(true);
  };

  const handleConfirmPdfDownload = () => {
    generateAndDownloadPdf(pdfCustomFilename, selectedAgenda?.title || "AI Response Report", pdfTargetText);
    setPdfModalOpen(false);
  };

  const handleStopSandboxGeneration = () => {
    if (sandboxAbortControllerRef.current) {
      sandboxAbortControllerRef.current.abort();
      setIsSandboxAiLoading(false);
      setSandboxMessages((prev) => [...prev, { sender: "ai", text: "⏹️ Generation stopped by officer." }]);
    }
  };

  const handleStopAgendaGeneration = () => {
    if (agendaAbortControllerRef.current) {
      agendaAbortControllerRef.current.abort();
      setIsAiProcessingInThread(false);
    }
  };

  // ── User Document Upload State & Handlers ─
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [userUploadedDocs, setUserUploadedDocs] = useState<Array<{ doc_name: string; chunk_count: number }>>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [uploadStatusMsg, setUploadStatusMsg] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("qwen2.5:3b");
  const [selectedContext, setSelectedContext] = useState("Board Note");
  const [activeWorkflowTool, setActiveWorkflowTool] = useState<"billing" | "tender" | null>(null);

  const selectAssistantContext = (value: string) => {
    setSelectedContext(value);
    if (value === "Billing Forecast") {
      setActiveWorkflowTool("billing");
    } else if (value === "Tender Publication Workflow") {
      setActiveWorkflowTool("tender");
    }
  };

  // Multi-session Sandbox Chat State
  interface SandboxSession {
    id: string;
    title: string;
    timestamp: string;
    messages: Array<{ sender: "user" | "ai"; text: string }>;
  }
  const [sandboxSessions, setSandboxSessions] = useState<SandboxSession[]>([]);
  const [activeSandboxSessionId, setActiveSandboxSessionId] = useState<string>("session-1");

  const handleNewChat = () => {
    if (sandboxMessages.length > 0) {
      const existingIndex = sandboxSessions.findIndex((s) => s.id === activeSandboxSessionId);
      const firstUserMsg = sandboxMessages.find((m) => m.sender === "user")?.text || "Personal Sandbox Session";
      const title = firstUserMsg.slice(0, 30) + (firstUserMsg.length > 30 ? "..." : "");
      const sessionObj: SandboxSession = {
        id: activeSandboxSessionId,
        title: title,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        messages: [...sandboxMessages],
      };

      if (existingIndex >= 0) {
        setSandboxSessions((prev) => {
          const updated = [...prev];
          updated[existingIndex] = sessionObj;
          return updated;
        });
      } else {
        setSandboxSessions((prev) => [sessionObj, ...prev]);
      }
    }

    const newId = `session-${Date.now()}`;
    setActiveSandboxSessionId(newId);
    setSandboxMessages([
      {
        sender: "ai",
        text: `Hello ${officerName}! Started a new Personal AI Sandbox session. Ask any questions about lease rules, policy clauses, or rent calculations.`,
      },
    ]);
    setMainTab("sandbox");
    setFeedbackMessage("Started new Chat Session!");
  };

  const handleSwitchSandboxSession = (session: SandboxSession) => {
    setActiveSandboxSessionId(session.id);
    setSandboxMessages(session.messages);
    setMainTab("sandbox");
  };

  const fetchUserUploadedDocs = async () => {
    try {
      const uid = userAdminId || localStorage.getItem("authorityId") || "565";
      const res = await fetch(`${API_BASE}/api/v1/documents/user-docs?user_id=${uid}`);
      if (res.ok) {
        const data = await res.json();
        setUserUploadedDocs(data);
      }
    } catch (err) {
      console.error("Error fetching user uploaded docs:", err);
    }
  };

  const handleUploadUserDoc = async () => {
    if (!selectedFile) return;
    setIsUploadingDoc(true);
    setUploadStatusMsg("Uploading and embedding document chunks into user_chunks table...");

    try {
      const uid = userAdminId || localStorage.getItem("authorityId") || "565";
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("user_id", uid);

      const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadStatusMsg(`✅ ${data.message}`);
        setSelectedFile(null);
        if (data.filename) {
          setUserUploadedDocs((prev) => [
            { doc_name: data.filename, chunk_count: data.chunks_indexed || 1 },
            ...prev.filter((d) => d.doc_name !== data.filename),
          ]);
        }
        await fetchUserUploadedDocs();
        setTimeout(() => {
          setUploadDialogOpen(false);
          setUploadStatusMsg(null);
        }, 800);
      } else {
        const errData = await res.json();
        setUploadStatusMsg(`❌ Upload failed: ${errData.detail || "Error"}`);
      }
    } catch (err: any) {
      setUploadStatusMsg(`❌ Error uploading file: ${err.message}`);
    } finally {
      setIsUploadingDoc(false);
    }
  };

  // ── Initial Load & Strict Session Binding ─
  useEffect(() => {
    // If logged in as tenant, strictly deny access to authority ai-chat
    const tenantToken = localStorage.getItem("tenantToken");
    const storedId = localStorage.getItem("authorityId");
    const storedUname = localStorage.getItem("authorityUserName") || localStorage.getItem("authorityUsername");
    
    if (tenantToken && !storedId) {
      navigate({ to: "/tenant/dashboard" });
      return;
    }

    if (!storedId && !storedUname) {
      navigate({ to: "/authority/login" });
      return;
    }

    const storedRoleId = localStorage.getItem("authorityRoleId") || "DO";
    const uid = storedId || "565";
    const uname = storedUname || "sudhakark_do";
    const storedName = localStorage.getItem("authorityName") || "SMT.AMRUTA HARSHAD VYAPARI";

    let normRole: "DO" | "NODAL" | "HOD" = "DO";
    if (storedRoleId.includes("NO") || storedRoleId.includes("NODAL")) normRole = "NODAL";
    else if (storedRoleId.includes("HO") || storedRoleId.includes("HOD")) normRole = "HOD";

    setActiveRole(normRole);
    setUserAdminId(uid);
    setUserName(uname);
    setOfficerName(storedName);
    setIsAuthChecking(false);

    fetchOfficers();
  }, []);

  const handleDeleteDoc = async (docName: string) => {
    try {
      const res = await fetch(`${getApiBase()}/api/v1/documents/user-docs?doc_name=${encodeURIComponent(docName)}&user_id=${userAdminId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        await fetchUserUploadedDocs();
      }
    } catch (e) {
      console.error("Error deleting document:", e);
    }
  };

  useEffect(() => {
    fetchAgendas();
    fetchUserUploadedDocs();
  }, [activeRole, userAdminId, userName]);

  useEffect(() => {
    if (selectedAgendaId) {
      fetchAgendaDetails(selectedAgendaId);
    }
  }, [selectedAgendaId, activeRole]);

  useEffect(() => {
    if (sandboxScrollRef.current) {
      sandboxScrollRef.current.scrollTop = sandboxScrollRef.current.scrollHeight;
    }
  }, [sandboxMessages, isSandboxAiLoading]);

  useEffect(() => {
    if (agendaScrollRef.current) {
      agendaScrollRef.current.scrollTop = agendaScrollRef.current.scrollHeight;
    }
  }, [agendaMessages, isAiProcessingInThread]);

  // If selected agenda is approved, default tab to final_doc
  useEffect(() => {
    if (selectedAgenda && selectedAgenda.current_state === "APPROVED") {
      setAgendaDetailTab("final_doc");
    } else {
      setAgendaDetailTab("thread");
    }
  }, [selectedAgendaId, selectedAgenda?.current_state]);

  // ── API Helpers ───────────────────────────
  const fetchOfficers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/users/officers`);
      if (res.ok) {
        const data = await res.json();
        setDosList(data.dos || []);
        setNodalList(data.nodal_officers || []);
        setHodsList(data.hods || []);
      }
    } catch (err) {
      console.error("Error fetching officers:", err);
    }
  };

  const fetchAgendas = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agendas?user_id=${userAdminId}&user_role=${activeRole}`);
      if (res.ok) {
        const data = await res.json();
        setAgendas(data);
        if (data.length > 0 && !selectedAgendaId) {
          setSelectedAgendaId(data[0].agenda_id);
        }
      }
    } catch (err) {
      console.error("Error fetching agendas:", err);
    }
  };

  const fetchAgendaDetails = async (agendaId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agendas/${agendaId}?user_id=${userAdminId}&user_role=${activeRole}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedAgenda(data);
        setWorkingDraftText(data.latest_draft || "");
        setAgendaCapsules(data.capsules || []);
        fetchAgendaMessages(agendaId);
      }
    } catch (err) {
      console.error("Error fetching agenda detail:", err);
    }
  };

  const fetchAgendaMessages = async (agendaId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/agendas/${agendaId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setAgendaMessages(data);
      }
    } catch (err) {
      console.error("Error fetching agenda messages:", err);
    }
  };

  // ── Handle Sandbox Query ──────────────────
  const handleSendSandboxMessage = async () => {
    if (!sandboxInput.trim()) return;
    const query = sandboxInput.trim();
    const contextualQuery = selectedContext === "All Contexts & Documents"
      ? query
      : `Use the ${selectedContext} context for this request.\n\n${query}`;
    setSandboxInput("");
    setSandboxMessages((prev) => [...prev, { sender: "user", text: query }]);
    setIsSandboxAiLoading(true);

    const controller = new AbortController();
    sandboxAbortControllerRef.current = controller;
    const loadingInterval = startDynamicLoadingSteps(query, setSandboxLoadingText);

    try {
      const res = await fetch(`${API_BASE}/api/v1/agendas/sandbox`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userAdminId,
          user_name: officerName,
          user_role: activeRole,
          content: contextualQuery,
          model_name: selectedModel,
          selected_context: selectedContext,
        }),
        signal: controller.signal,
      });

      if (res.ok) {
        const data = await res.json();
        setSandboxMessages((prev) => [...prev, { sender: "ai", text: data.ai_response }]);
      } else {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        setSandboxMessages((prev) => [...prev, { sender: "ai", text: `[API Error ${res.status}]: ${errData.detail || "Request failed."}` }]);
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Sandbox generation aborted by user.");
      } else {
        setSandboxMessages((prev) => [...prev, { sender: "ai", text: `[Connection Error]: ${err.message || String(err)}` }]);
      }
    } finally {
      clearInterval(loadingInterval);
      setIsSandboxAiLoading(false);
      sandboxAbortControllerRef.current = null;
    }
  };

  // ── Handle Promote Sandbox ────────────────
  const handlePromoteSandbox = async () => {
    if (!promoteTitle.trim()) return;
    try {
      const sandboxTexts = sandboxMessages.map((m) => `${m.sender.toUpperCase()}: ${m.text}`);
      const res = await fetch(`${API_BASE}/api/v1/agendas/promote-sandbox`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userAdminId,
          user_name: officerName,
          user_role: activeRole,
          agenda_title: promoteTitle.trim(),
          tenancy_id: promoteTenancyId.trim() || undefined,
          sandbox_messages: sandboxTexts,
          initial_draft: promoteDraftText.trim() || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPromoteDialogOpen(false);
        setPromoteTitle("");
        setPromoteTenancyId("");
        setPromoteDraftText("");
        setMainTab("official");
        setFeedbackMessage(`Promoted sandbox to ${data.agenda_id}!`);
        await fetchAgendas();
        setSelectedAgendaId(data.agenda_id);
      }
    } catch (err) {
      console.error("Error promoting sandbox:", err);
    }
  };

  // ── Handle Interactive AI Query in Shared Agenda Thread ──
  const handleSendAgendaMessage = async () => {
    if (!agendaInput.trim() || !selectedAgendaId || !selectedAgenda) return;
    if (selectedAgenda.is_read_only || selectedAgenda.current_state === "APPROVED" || selectedAgenda.current_state === "REJECTED") return;

    const prompt = agendaInput.trim();
    const contextualPrompt = selectedContext === "All Contexts & Documents"
      ? prompt
      : `Use the ${selectedContext} context for this request.\n\n${prompt}`;
    setAgendaInput("");
    setIsAiProcessingInThread(true);

    const controller = new AbortController();
    agendaAbortControllerRef.current = controller;
    const loadingInterval = startDynamicLoadingSteps(prompt, setAgendaLoadingText);

    try {
      let recName = "Nodal Officer";
      let recRole = "NODAL";
      if (activeRole === "NODAL") {
        recName = "Head of Department";
        recRole = "HOD";
      } else if (activeRole === "HOD") {
        recName = "Dealing Officer";
        recRole = "DO";
      }

      const res = await fetch(`${API_BASE}/api/v1/agendas/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agenda_id: selectedAgendaId,
          thread_type: "OFFICIAL_AGENDA",
          sender_id: userAdminId,
          sender_name: officerName,
          sender_role: activeRole,
          recipient_name: recName,
          recipient_role: recRole,
          content: contextualPrompt,
          model_name: selectedModel,
        }),
        signal: controller.signal,
      });

      if (res.ok) {
        const data = await res.json();
        if (data.updated_draft) {
          setWorkingDraftText(data.updated_draft);
        }
        await fetchAgendaDetails(selectedAgendaId);
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Agenda thread generation aborted by user.");
      } else {
        console.error("Error sending interactive agenda prompt:", err);
      }
    } finally {
      clearInterval(loadingInterval);
      setIsAiProcessingInThread(false);
      agendaAbortControllerRef.current = null;
    }
  };

  // ── Handle Agenda Handoff ─────────────────
  const handleHandoff = async (action: "SUBMIT_FORWARD" | "RETURN_BACK" | "APPROVE" | "REJECT") => {
    if (!selectedAgendaId || !selectedAgenda) return;
    setIsHandoffSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/agendas/handoff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agenda_id: selectedAgendaId,
          sender_id: userAdminId,
          sender_name: officerName,
          sender_role: activeRole,
          action: action,
          target_officer_id: handoffTargetOfficer || undefined,
          target_officer_name: handoffTargetOfficerName || undefined,
          remarks: handoffRemarks.trim(),
          updated_draft_text: workingDraftText,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setHandoffRemarks("");
        setHandoffTargetOfficer("");
        setHandoffTargetOfficerName("");
        setFeedbackMessage(`Agenda state updated to ${data.current_state} (Owner: ${data.current_owner})`);
        await fetchAgendas();
        await fetchAgendaDetails(selectedAgendaId);
      }
    } catch (err) {
      setFeedbackMessage("Failed to execute handoff.");
    } finally {
      setIsHandoffSubmitting(false);
    }
  };

  const handleCopyApprovedDoc = () => {
    if (selectedAgenda?.latest_draft) {
      navigator.clipboard.writeText(selectedAgenda.latest_draft);
      setCopiedDoc(true);
      setTimeout(() => setCopiedDoc(false), 2000);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-surface font-sans">
      <GovHeader />

      {/* Top Workspace Banner - HARDENED IMMUTABLE SESSION */}
      <div className="border-b border-border bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Button asChild variant="ghost" size="sm" className="gap-1.5 font-semibold text-navy hover:bg-navy/5">
              <Link to="/authority/dashboard">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Link>
            </Button>
            <div className="hidden h-4 w-px bg-border sm:block" />
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy text-gold shadow-sm">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h1 className="font-display text-base font-bold text-navy">
                  AI Assistant & Role-Based Agenda Workflow
                </h1>
                <p className="text-xs text-muted-foreground">
                  Authenticated Session: <span className="font-semibold text-navy">{officerName}</span> ({userName} · ID: {userAdminId})
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Badge className="border-gold/40 bg-gold/10 text-navy font-bold text-xs px-3 py-1 flex items-center gap-1.5">
              <UserCheck className="h-3.5 w-3.5 text-navy" />
              Session Role: {activeRole}
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Workspace Container */}
      <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6 flex flex-col gap-4">
        {feedbackMessage && (
          <div className="flex items-center justify-between rounded-xl border border-navy/20 bg-navy/5 p-3 text-xs font-semibold text-navy shadow-sm">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-gold" />
              <span>{feedbackMessage}</span>
            </div>
            <button onClick={() => setFeedbackMessage(null)} className="text-muted-foreground hover:text-navy">×</button>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMainTab("sandbox")}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold transition-all ${
                mainTab === "sandbox"
                  ? "bg-navy text-white shadow-md"
                  : "bg-white text-muted-foreground hover:bg-surface border border-border"
              }`}
            >
              <MessageSquare className="h-4 w-4 text-gold" />
              AI Assistant
            </button>

            <button
              onClick={() => setMainTab("official")}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-bold transition-all ${
                mainTab === "official"
                  ? "bg-navy text-white shadow-md"
                  : "bg-white text-muted-foreground hover:bg-surface border border-border"
              }`}
            >
              <FileText className="h-4 w-4 text-gold" />
              Agenda{unreadCount > 0 ? ` (${unreadCount})` : ""}
            </button>
          </div>

          {mainTab === "sandbox" && (
            <div className="flex items-center gap-2">
              <Button
                className="bg-gold text-navy hover:bg-gold/90 font-bold text-xs gap-1.5 shadow-sm"
                onClick={handleNewChat}
              >
                <Plus className="h-4 w-4" /> New Chat
              </Button>

              <Dialog open={promoteDialogOpen} onOpenChange={setPromoteDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1.5 shadow-sm">
                    <Sparkles className="h-4 w-4 text-gold" /> Forward Draft
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-display text-lg font-bold text-navy flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-gold" /> Forward Draft to Agenda
                    </DialogTitle>
                    <DialogDescription className="text-xs text-muted-foreground">
                      Convert active AI Assistant discussion into a formal agenda draft.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-3">
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-navy">Agenda Title *</label>
                      <Input
                        placeholder="e.g. Land Renewal for Commercial Terminal 12A"
                        value={promoteTitle}
                        onChange={(e) => setPromoteTitle(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-navy">Tenancy ID (Optional)</label>
                      <Input
                        placeholder="e.g. TNT-9942"
                        value={promoteTenancyId}
                        onChange={(e) => setPromoteTenancyId(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-navy">Initial Working Draft Notes</label>
                      <Textarea
                        rows={4}
                        placeholder="Summarize key points or leave empty..."
                        value={promoteDraftText}
                        onChange={(e) => setPromoteDraftText(e.target.value)}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setPromoteDialogOpen(false)}>Cancel</Button>
                    <Button className="bg-navy text-white hover:bg-navy/90 font-bold" onClick={handlePromoteSandbox}>
                      Create Official Agenda Draft
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </div>

        {/* TAB 1: AI ASSISTANT */}
        {mainTab === "sandbox" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-[620px]">
            {/* Left Sidebar Panel: New Conversation, Conversation History & Recent Uploaded PDFs */}
            <div className="lg:col-span-3 rounded-2xl border border-border bg-white shadow-md p-4 flex flex-col justify-between gap-4">
              <div className="space-y-4">
                {/* Top Primary Action Button */}
                <Button
                  className="w-full bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-2 py-2.5 shadow-sm"
                  onClick={handleNewChat}
                >
                  <Plus className="h-4 w-4 text-gold" /> + New Conversation
                </Button>

                <div className="space-y-2 pt-1">
                  <span className="text-[11px] font-extrabold text-muted-foreground uppercase tracking-wider flex items-center justify-between">
                    <span>CONVERSATION HISTORY</span>
                    <span className="text-[10px] font-bold text-navy opacity-75">{sandboxSessions.length + 1}</span>
                  </span>
                  
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {/* Active Conversation Card */}
                    <div
                      onClick={() => setMainTab("sandbox")}
                      className={`w-full text-left p-2.5 rounded-xl text-xs flex items-center justify-between cursor-pointer transition-all ${
                        mainTab === "sandbox"
                          ? "bg-navy text-white font-bold shadow-sm"
                          : "bg-surface hover:bg-surface/80 text-navy border border-border/60 font-semibold"
                      }`}
                    >
                      <span className="line-clamp-1 flex items-center gap-2">
                        <MessageSquare className="h-3.5 w-3.5 text-gold shrink-0" />
                        {sandboxMessages.find(m => m.sender === "user")?.text.slice(0, 24) || "Active Conversation"}
                      </span>
                    </div>

                    {/* History Session Cards */}
                    {sandboxSessions.map((s) => {
                      const isActiveSession = activeSandboxSessionId === s.id;
                      return (
                        <div
                          key={s.id}
                          onClick={() => handleSwitchSandboxSession(s)}
                          className={`w-full text-left p-2.5 rounded-xl text-xs flex items-center justify-between cursor-pointer transition-all ${
                            isActiveSession
                              ? "bg-navy text-white font-bold shadow-sm"
                              : "bg-surface hover:bg-surface/80 text-navy border border-border/60 font-semibold"
                          }`}
                        >
                          <span className="line-clamp-1 flex items-center gap-2">
                            <MessageSquare className="h-3.5 w-3.5 text-gold shrink-0" />
                            {s.title}
                          </span>
                          {!isActiveSession && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSandboxSessions(prev => prev.filter(sess => sess.id !== s.id));
                              }}
                              title="Delete Conversation"
                              className="text-muted-foreground hover:text-red-400 p-0.5 transition-colors"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] font-bold text-navy uppercase tracking-wider flex items-center gap-1">
                    <FileText className="h-3 w-3 text-gold" /> Agenda{unreadCount > 0 ? ` (${unreadCount})` : ""}
                  </span>
                    <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                      {agendas.map((a) => (
                        <button
                          key={a.agenda_id}
                          type="button"
                          onClick={() => {
                            setMainTab("official");
                            setSelectedAgendaId(a.agenda_id);
                          }}
                          className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition-all ${
                            selectedAgendaId === a.agenda_id
                              ? "border-2 border-blue-600 bg-surface text-navy font-bold shadow-2xs"
                              : "bg-surface/60 hover:bg-surface text-navy border border-border/60 font-semibold"
                          }`}
                        >
                          <span className="line-clamp-1 flex items-center gap-1.5">
                            <FileText className="h-3 w-3 text-gold shrink-0" /> {a.title}
                          </span>
                          <span className="text-[9px] font-mono opacity-75">{a.agenda_id}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                <div className="border-t border-border/80" />

                <div className="space-y-2.5">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <h3 className="font-display text-xs font-bold text-navy uppercase tracking-wider flex items-center gap-1.5">
                      <Paperclip className="h-3.5 w-3.5 text-blue-600" /> RECENT UPLOADED PDFS ({userUploadedDocs.length} Total)
                    </h3>
                  </div>

                  {userUploadedDocs.length === 0 ? (
                    <div className="p-3 text-center text-xs text-muted-foreground italic border border-dashed border-border rounded-xl bg-surface/40">
                      No custom PDFs uploaded yet. Click paperclip 📎 next to text box to upload.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {userUploadedDocs.slice(0, 5).map((doc, idx) => (
                        <div key={idx} className="p-2.5 rounded-xl border border-navy/15 bg-surface/80 hover:bg-surface space-y-1 shadow-2xs transition-all flex items-center justify-between gap-2">
                          <div className="flex flex-col gap-0.5 overflow-hidden">
                            <span className="font-bold text-xs text-navy line-clamp-1 flex items-center gap-1.5">
                              <FileText className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                              {doc.doc_name}
                            </span>
                            <span className="text-[10px] text-gov-green font-mono font-bold">✓ BGE-M3 1024-dim ({doc.chunk_count} chunks)</span>
                          </div>
                          <button
                            type="button"
                            title="Delete document"
                            onClick={() => handleDeleteDoc(doc.doc_name)}
                            className="text-muted-foreground hover:text-red-600 p-1 shrink-0 transition-colors"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setUploadDialogOpen(true)}
                className="w-full text-xs font-bold text-navy border-navy/30 hover:bg-navy hover:text-white gap-1.5"
              >
                <UploadCloud className="h-3.5 w-3.5 text-gold" /> Upload / Manage Documents
              </Button>
            </div>

            {/* Main Sandbox Chat Panel */}
            <div className="lg:col-span-9 flex flex-col rounded-2xl border border-border bg-white shadow-lg overflow-hidden">
              <div className="border-b border-border bg-surface px-6 py-3.5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className="bg-navy text-white text-xs font-bold">Personal Scratchpad</Badge>
                  <span className="text-xs text-muted-foreground">Unlocked private queries & drafting space for {officerName}</span>
                </div>

                {userUploadedDocs.length > 0 && (
                  <div className="flex items-center gap-1.5 text-[11px] text-navy font-semibold">
                    <Paperclip className="h-3.5 w-3.5 text-gold" /> Indexed Docs: {userUploadedDocs.map(d => d.doc_name).join(", ")}
                  </div>
                )}
              </div>

              <div ref={sandboxScrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 max-h-[480px]">
                {sandboxMessages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed shadow-sm ${
                      msg.sender === "user" ? "bg-navy text-white rounded-br-none" : "bg-surface border border-border text-navy rounded-bl-none font-mono whitespace-pre-wrap"
                    }`}>
                      <div className="flex items-center gap-2 mb-1 text-[10px] font-bold opacity-75 uppercase">
                        {msg.sender === "user" ? `You (${officerName} - ${activeRole})` : "Port RAG AI Assistant"}
                      </div>
                      {msg.text.replace(/\[Source:.*?\]/g, "").trim()}

                      {msg.sender === "ai" && <AestheticCitationsFooter text={msg.text} />}
                      {msg.sender === "ai" && (
                        <ResponseActionBar
                          text={msg.text}
                          msgId={`sandbox-${idx}`}
                          onOpenPdfModal={(t) => handleOpenPdfModal(t, "AI Assistant Executive Report")}
                        />
                      )}
                    </div>
                  </div>
                ))}
                {isSandboxAiLoading && (
                  <div className="flex justify-start">
                    <div className="bg-surface border border-gold/40 rounded-2xl p-4 text-xs text-navy flex items-center gap-2 font-mono shadow-sm">
                      <RefreshCw className="h-4 w-4 animate-spin text-gold" />
                      <span>{sandboxLoadingText}</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t border-border bg-white p-4">
                {userUploadedDocs.length > 0 && (
                  <div className="mb-2.5 flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-extrabold text-navy/80 uppercase tracking-wider flex items-center gap-1">
                      <Paperclip className="h-3 w-3 text-blue-600" /> Active RAG Attachments:
                    </span>
                    {userUploadedDocs.slice(0, 3).map((doc, i) => (
                      <Badge key={i} className="bg-blue-50 text-blue-900 border border-blue-200 text-[11px] px-2.5 py-0.5 font-bold flex items-center gap-1 shadow-2xs">
                        📎 {doc.doc_name} Attached
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="flex gap-2 items-center">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setUploadDialogOpen(true)}
                    title="Upload Custom Document to RAG Vector DB"
                    className="border-navy/30 text-navy hover:bg-navy hover:text-white shrink-0 h-9 w-9"
                  >
                    <Paperclip className="h-4 w-4 text-navy" />
                  </Button>
                  <Input
                    disabled={false}
                    placeholder="Ask AI Assistant about lease policies, breach rules, or agenda clauses..."
                    value={sandboxInput}
                    onChange={(e) => setSandboxInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !isSandboxAiLoading && handleSendSandboxMessage()}
                    className="flex-1 text-xs"
                  />

                  {/* AI query context selector */}
                  <div className="shrink-0">
                    <Select value={selectedContext} onValueChange={selectAssistantContext}>
                      <SelectTrigger className="h-9 w-48 border border-navy bg-navy px-3 text-xs font-bold text-white shadow-sm focus:ring-gold">
                        <SelectValue placeholder="Select context" />
                      </SelectTrigger>
                      <SelectContent className="bg-white text-navy text-xs shadow-lg border border-navy/20">
                        <SelectItem value="All Contexts & Documents">All contexts & documents</SelectItem>
                        <SelectItem value="Billing Forecast">Billing Forecast</SelectItem>
                        <SelectItem value="Tender Publication Workflow">Tender Publication Workflow</SelectItem>
                        <SelectItem value="Board Note">Board Note</SelectItem>
                        <SelectItem value="Breach">Breach</SelectItem>
                        <SelectItem value="Chairman Note">Chairman Note</SelectItem>
                        <SelectItem value="Letter">Letter</SelectItem>
                        <SelectItem value="RTI">RTI</SelectItem>
                        <SelectItem value="SOR">SOR</SelectItem>
                        <SelectItem value="Suit">Suit</SelectItem>
                        <SelectItem value="Tender Draft">Tender Draft</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {isSandboxAiLoading ? (
                    <Button
                      type="button"
                      onClick={handleStopSandboxGeneration}
                      className="bg-red-600 hover:bg-red-700 text-white font-bold text-xs gap-1.5 animate-pulse shadow-md"
                    >
                      <Square className="h-4 w-4 fill-white" /> Stop Generation
                    </Button>
                  ) : (
                    <Button className="bg-navy text-white hover:bg-navy/90 font-bold text-xs" onClick={handleSendSandboxMessage}>
                      <Send className="h-4 w-4 mr-1" /> Ask AI
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: OFFICIAL AGENDA THREADS */}
        {mainTab === "official" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-[660px]">
            {/* Sidebar: Agendas */}
            <div className="lg:col-span-3 rounded-2xl border border-border bg-white shadow-md p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h3 className="font-display text-sm font-bold text-navy flex items-center gap-1.5">
                  <FileText className="h-4 w-4 text-gold" /> Official Agendas ({agendas.length})
                </h3>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[560px]">
                {agendas.length === 0 ? (
                  <div className="p-8 text-center text-xs text-muted-foreground">
                    No agendas found for active role {activeRole}. Use 'Promote Sandbox' to create one.
                  </div>
                ) : (
                  agendas.map((item) => {
                    const isSelected = item.agenda_id === selectedAgendaId;
                    const isApproved = item.current_state === "APPROVED";
                    const isRejected = item.current_state === "REJECTED";

                    return (
                      <div
                        key={item.agenda_id}
                        onClick={() => setSelectedAgendaId(item.agenda_id)}
                        className={`cursor-pointer rounded-xl border p-3 transition-all ${
                          isSelected ? "border-navy bg-navy/5 shadow-md" : "border-border hover:border-navy/40 bg-surface/50"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs font-bold text-navy">{item.agenda_id}</span>
                          <div className="flex items-center gap-1">
                            {isApproved ? (
                              <Badge className="bg-gov-green text-white border-none text-[10px] gap-1 font-bold">
                                <CheckCircle2 className="h-3 w-3" /> Approved
                              </Badge>
                            ) : isRejected ? (
                              <Badge variant="destructive" className="text-[10px] gap-1 font-bold">
                                <XCircle className="h-3 w-3" /> Rejected
                              </Badge>
                            ) : item.is_read_only ? (
                              <Badge variant="outline" className="bg-red-50 text-red-600 border-red-200 text-[10px] gap-1 font-semibold">
                                <Lock className="h-3 w-3" /> Read-Only
                              </Badge>
                            ) : (
                              <Badge className="bg-gov-green/10 text-gov-green border-gov-green/30 text-[10px] gap-1 font-semibold">
                                <Edit3 className="h-3 w-3" /> Write Mode
                              </Badge>
                            )}
                          </div>
                        </div>

                        <h4 className="font-bold text-xs text-navy mt-1.5 line-clamp-1">{item.title}</h4>

                        <div className="flex items-center justify-between mt-2.5 text-[11px] text-muted-foreground">
                          <span>Owner: <strong className="text-navy">{item.current_owner}</strong></span>
                          <span>State: <strong className="text-navy">{item.current_state}</strong></span>
                          <span className="font-mono font-bold text-gold">v{item.editing_version}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Main Area: Agenda Workflow & Shared Thread */}
            <div className="lg:col-span-8 flex flex-col rounded-2xl border border-border bg-white shadow-md overflow-hidden">
              {selectedAgenda ? (
                <>
                  {/* Agenda Header */}
                  <div className="border-b border-border bg-surface px-6 py-3 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-gold bg-navy px-2 py-0.5 rounded">{selectedAgenda.agenda_id}</span>
                        <h2 className="font-display text-sm font-bold text-navy">{selectedAgenda.title}</h2>
                      </div>
                      {selectedAgenda.tenancy_id && (
                        <p className="text-[11px] text-muted-foreground mt-0.5">Associated Tenancy: {selectedAgenda.tenancy_id}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs font-bold bg-white">Editing Version: v{selectedAgenda.editing_version}</Badge>
                      <Badge className="bg-navy text-gold text-xs font-bold">Active Owner: {selectedAgenda.current_owner}</Badge>
                    </div>
                  </div>

                  {/* REQUIREMENT 3: HEADER PARTICIPANT CHAIN COLOR BADGES */}
                  <div className="bg-white border-b border-border px-6 py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">Participant Chain Flow:</span>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="bg-blue-600 text-white px-2 py-1 rounded text-xs font-semibold shadow-sm flex items-center gap-1">
                        <User className="h-3 w-3" /> [DO] {selectedAgenda.assigned_do_name || "Dealing Officer"}
                      </span>
                      <span className="text-muted-foreground font-bold">➔</span>

                      <span className="bg-amber-600 text-white px-2 py-1 rounded text-xs font-semibold shadow-sm flex items-center gap-1">
                        <Users className="h-3 w-3" /> [NODAL] {selectedAgenda.assigned_no_name || "Nodal Officer"}
                      </span>
                      <span className="text-muted-foreground font-bold">➔</span>

                      <span className="bg-purple-600 text-white px-2 py-1 rounded text-xs font-semibold shadow-sm flex items-center gap-1">
                        <Building className="h-3 w-3" /> [HOD] {selectedAgenda.assigned_hod_name || "Head of Department"}
                      </span>
                      <span className="text-muted-foreground font-bold">➔</span>

                      <span className="bg-emerald-700 text-white px-2 py-1 rounded text-xs font-semibold shadow-sm flex items-center gap-1">
                        <Bot className="h-3 w-3" /> 🤖 AI Assistant
                      </span>
                    </div>
                  </div>

                  {/* REQUIREMENT 1: STATE BANNERS (LOCK ON APPROVAL) */}
                  {selectedAgenda.current_state === "APPROVED" ? (
                    <div className="bg-gov-green/15 border-b border-gov-green/30 px-6 py-3 flex items-center justify-between text-xs text-gov-green font-bold shadow-inner">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-5 w-5 text-gov-green shrink-0" />
                        <span>
                          ✅ Agenda Approved & Finalized (Thread Locked). No further edits or chat turns allowed.
                        </span>
                      </div>
                    </div>
                  ) : selectedAgenda.current_state === "REJECTED" ? (
                    <div className="bg-red-100 border-b border-red-300 px-6 py-3 flex items-center justify-between text-xs text-red-800 font-bold shadow-inner">
                      <div className="flex items-center gap-2">
                        <XCircle className="h-5 w-5 text-red-600 shrink-0" />
                        <span>
                          ❌ Agenda Rejected & Finalized (Thread Locked). No further edits allowed.
                        </span>
                      </div>
                    </div>
                  ) : selectedAgenda.is_read_only ? (
                    <div className="bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-center justify-between text-xs text-amber-900 font-medium">
                      <div className="flex items-center gap-2">
                        <ShieldAlert className="h-4 w-4 text-amber-600 shrink-0" />
                        <span>
                          <strong>🔒 Read-Only Snapshot</strong> (Active Owner: <strong>{selectedAgenda.current_owner}</strong>). Thread input is locked for your session role ({activeRole}).
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gov-green/10 border-b border-gov-green/20 px-6 py-3 flex items-center justify-between text-xs text-gov-green font-medium">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-gov-green shrink-0" />
                        <span>
                          <strong>✏️ Full Write Mode Active</strong>. You are the active owner ({activeRole}). Type prompts to AI Assistant in thread to auto-refine agenda draft.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Sub Tab Bar (REQUIREMENT 2: REMOVED LIVE WORKING DRAFT TAB) */}
                  <div className="border-b border-border px-6 py-2 bg-white flex items-center gap-2">
                    <button
                      onClick={() => setAgendaDetailTab("thread")}
                      className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all ${
                        agendaDetailTab === "thread" ? "bg-navy text-white" : "text-muted-foreground hover:bg-surface"
                      }`}
                    >
                      💬 Shared Interactive AI Thread ({agendaMessages.length})
                    </button>

                    {/* REQUIREMENT 4: FINAL APPROVED DOCUMENT TAB */}
                    {selectedAgenda.current_state === "APPROVED" && (
                      <button
                        onClick={() => setAgendaDetailTab("final_doc")}
                        className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                          agendaDetailTab === "final_doc" ? "bg-gov-green text-white shadow-md" : "text-gov-green hover:bg-gov-green/10 border border-gov-green/30"
                        }`}
                      >
                        <FileCheck className="h-4 w-4" /> 📄 Final Approved Document
                      </button>
                    )}

                    <button
                      onClick={() => setAgendaDetailTab("capsules")}
                      className={`px-3 py-1.5 text-xs font-bold rounded-md transition-all ${
                        agendaDetailTab === "capsules" ? "bg-navy text-white" : "text-muted-foreground hover:bg-surface"
                      }`}
                    >
                      📜 Context Capsules ({agendaCapsules.length})
                    </button>
                  </div>

                  {/* TAB CONTENT 1: INTERACTIVE SHARED AI THREAD */}
                  {agendaDetailTab === "thread" && (
                    <div className="flex-1 flex flex-col">
                      <div ref={agendaScrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 max-h-[360px]">
                        {agendaMessages.length === 0 ? (
                          <div className="p-8 text-center text-xs text-muted-foreground">
                            No shared discussion messages in this official agenda thread yet.
                          </div>
                        ) : (
                          agendaMessages.map((m) => (
                            <div
                              key={m.message_id}
                              className={`rounded-2xl border p-4 text-xs space-y-2 shadow-sm ${
                                m.is_ai_response
                                  ? "bg-gold/10 border-gold/40 text-navy font-mono"
                                  : "bg-surface border-border text-navy"
                              }`}
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-2 text-[10px] font-bold">
                                {m.is_ai_response ? (
                                  <div className="flex items-center gap-1.5 text-navy">
                                    <span className="bg-emerald-700 text-white px-2 py-0.5 rounded text-[10px] font-semibold flex items-center gap-1">
                                      <Bot className="h-3 w-3 text-gold" /> 🤖 AI Assistant
                                    </span>
                                    <Badge className="bg-navy text-gold text-[9px] px-1.5 py-0 font-mono">
                                      Triggered by {m.ai_triggered_by || "Officer"}
                                    </Badge>
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2">
                                    <span className="text-navy font-semibold flex items-center gap-1">
                                      <User className="h-3 w-3 text-navy" /> Sender: {m.sender_name} ({m.sender_role})
                                    </span>
                                    {m.recipient_name && (
                                      <span className="text-muted-foreground">
                                        → Sent To: {m.recipient_name} ({m.recipient_role})
                                      </span>
                                    )}
                                  </div>
                                )}

                                <div className="flex items-center gap-1 text-muted-foreground">
                                  <Clock className="h-3 w-3" />
                                  <span>{m.created_at}</span>
                                </div>
                              </div>

                              <p className="leading-relaxed whitespace-pre-wrap">{m.content.replace(/\[Source:.*?\]/g, "").trim()}</p>

                              {m.is_ai_response && <AestheticCitationsFooter text={m.content} />}
                              {m.is_ai_response && (
                                <ResponseActionBar
                                  text={m.content}
                                  msgId={m.message_id}
                                  onOpenPdfModal={(t) => handleOpenPdfModal(t, selectedAgenda?.title || "Official Agenda Report")}
                                />
                              )}
                            </div>
                          ))
                        )}
                        {isAiProcessingInThread && (
                          <div className="rounded-2xl border border-gold/40 bg-gold/10 p-4 text-xs text-navy font-mono flex items-center gap-2">
                            <RefreshCw className="h-4 w-4 animate-spin text-gold" />
                            <span>{agendaLoadingText}</span>
                          </div>
                        )}
                      </div>

                      {/* Interactive Thread Input (DISABLED IF APPROVED/REJECTED/READ-ONLY) */}
                      <div className="border-t border-border p-4 bg-white">
                        <div className="flex gap-2 items-center">
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            disabled={selectedAgenda.is_read_only || selectedAgenda.current_state === "APPROVED" || selectedAgenda.current_state === "REJECTED"}
                            onClick={() => setUploadDialogOpen(true)}
                            title="Upload Custom Document to RAG Vector DB"
                            className="border-navy/30 text-navy hover:bg-navy hover:text-white shrink-0 h-9 w-9"
                          >
                            <Paperclip className="h-4 w-4 text-navy" />
                          </Button>
                          <Input
                            disabled={selectedAgenda.is_read_only || selectedAgenda.current_state === "APPROVED" || selectedAgenda.current_state === "REJECTED"}
                            placeholder={
                              selectedAgenda.current_state === "APPROVED"
                                ? "🔒 Agenda Approved & Finalized (Thread Locked)"
                                : selectedAgenda.current_state === "REJECTED"
                                ? "🔒 Agenda Rejected & Finalized (Thread Locked)"
                                : selectedAgenda.is_read_only
                                ? "🔒 Read-only snapshot (Input locked for your role)"
                                : "Ask AI to refine draft or add clause in thread..."
                            }
                            value={agendaInput}
                            onChange={(e) => setAgendaInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && !isAiProcessingInThread && handleSendAgendaMessage()}
                            className="flex-1 text-xs"
                          />

                          {/* AI query context selector */}
                          <div className="shrink-0">
                            <Select value={selectedContext} onValueChange={selectAssistantContext}>
                              <SelectTrigger className="h-9 w-48 border border-navy bg-navy px-3 text-xs font-bold text-white shadow-sm focus:ring-gold">
                                <SelectValue placeholder="Select context" />
                              </SelectTrigger>
                              <SelectContent className="bg-white text-navy text-xs shadow-lg border border-navy/20">
                                <SelectItem value="All Contexts & Documents">All contexts & documents</SelectItem>
                                <SelectItem value="Billing Forecast">Billing Forecast</SelectItem>
                                <SelectItem value="Tender Publication Workflow">Tender Publication Workflow</SelectItem>
                                <SelectItem value="Board Note">Board Note</SelectItem>
                                <SelectItem value="Breach">Breach</SelectItem>
                                <SelectItem value="Chairman Note">Chairman Note</SelectItem>
                                <SelectItem value="Letter">Letter</SelectItem>
                                <SelectItem value="RTI">RTI</SelectItem>
                                <SelectItem value="SOR">SOR</SelectItem>
                                <SelectItem value="Suit">Suit</SelectItem>
                                <SelectItem value="Tender Draft">Tender Draft</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          {isAiProcessingInThread ? (
                            <Button
                              type="button"
                              onClick={handleStopAgendaGeneration}
                              className="bg-red-600 hover:bg-red-700 text-white font-bold text-xs gap-1.5 animate-pulse shadow-md"
                            >
                              <Square className="h-4 w-4 fill-white" /> Stop Generation
                            </Button>
                          ) : (
                            <Button
                              disabled={selectedAgenda.is_read_only || selectedAgenda.current_state === "APPROVED" || selectedAgenda.current_state === "REJECTED"}
                              className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1"
                              onClick={handleSendAgendaMessage}
                            >
                              <Send className="h-4 w-4" /> Ask AI in Thread
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* REQUIREMENT 4: TAB CONTENT 2: FINAL APPROVED DOCUMENT VIEW */}
                  {agendaDetailTab === "final_doc" && selectedAgenda.current_state === "APPROVED" && (
                    <div className="p-6 flex flex-col gap-4 flex-1 bg-surface/30">
                      <div className="flex items-center justify-between border-b border-border pb-3">
                        <div>
                          <h4 className="font-display text-sm font-bold text-gov-green flex items-center gap-2">
                            <FileCheck className="h-5 w-5" /> Final Approved & Signed Document
                          </h4>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            Approved by HOD: {selectedAgenda.assigned_hod_name || "Head of Department"}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button size="sm" className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1.5" onClick={handleCopyApprovedDoc}>
                            {copiedDoc ? <Check className="h-4 w-4 text-gov-green" /> : <Copy className="h-4 w-4" />}
                            {copiedDoc ? "Copied to Clipboard!" : "Copy Document Text"}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-gov-green/40 text-gov-green hover:bg-gov-green hover:text-white font-bold text-xs gap-1.5 shadow-sm"
                            onClick={() => {
                              const docContent = selectedAgenda.final_approved_document || selectedAgenda.latest_draft || "";
                              generateCleanPdf(
                                `${selectedAgenda.agenda_id}_Executive_Approval_Memorandum.pdf`,
                                `Official Approval Memorandum — ${selectedAgenda.title} (${selectedAgenda.agenda_id})`,
                                docContent
                              );
                            }}
                          >
                            <Download className="h-4 w-4 text-gold" /> Download Signed PDF
                          </Button>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-gov-green/30 bg-white p-6 shadow-sm overflow-y-auto max-h-[500px]">
                        <div className="text-center border-b border-border pb-4 mb-4">
                          <div className="font-display text-base font-bold text-navy uppercase tracking-wider">
                            Mumbai Port Authority — Executive Approval Memorandum
                          </div>
                          <div className="text-xs font-semibold text-muted-foreground mt-1">
                            {selectedAgenda.title} ({selectedAgenda.agenda_id})
                          </div>
                        </div>

                        <pre className="font-mono text-xs text-navy leading-relaxed whitespace-pre-wrap font-sans bg-surface/40 p-4 rounded-lg border border-border/50">
                          {selectedAgenda.final_approved_document || selectedAgenda.latest_draft}
                        </pre>

                        <div className="mt-6 border-t border-border pt-4 flex items-center justify-between text-[11px] text-muted-foreground font-semibold">
                          <span>Final Status: <strong className="text-gov-green font-bold">APPROVED & SANCTIONED</strong></span>
                          <span>Chain: DO ({selectedAgenda.assigned_do_name || 'DO'}) ➔ NO ({selectedAgenda.assigned_no_name || 'NO'}) ➔ HOD ({selectedAgenda.assigned_hod_name || 'HOD'})</span>
                          <span>Verified by Port Management System Workflow</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB CONTENT 3: CONTEXT CAPSULES */}
                  {agendaDetailTab === "capsules" && (
                    <div className="p-6 overflow-y-auto space-y-4 max-h-[450px]">
                      <h4 className="font-bold text-xs text-navy uppercase tracking-wide">Context Capsules Snapshot History</h4>
                      {agendaCapsules.length === 0 ? (
                        <div className="p-8 text-center text-xs text-muted-foreground">No context capsules snapshot created yet.</div>
                      ) : (
                        agendaCapsules.map((c) => (
                          <div key={c.capsule_id} className="rounded-xl border border-border p-4 bg-surface/60 space-y-2">
                            <div className="flex items-center justify-between text-xs font-bold text-navy">
                              <span className="bg-navy text-gold px-2 py-0.5 rounded text-[10px]">Capsule v{c.version}</span>
                              <span className="text-muted-foreground text-[11px]">{c.created_at}</span>
                            </div>
                            <p className="text-xs text-navy font-mono leading-relaxed">{c.executive_summary}</p>
                            <div className="text-[10px] text-muted-foreground flex gap-4 pt-1 border-t border-border/60">
                              <span>From: <strong>{c.transferred_from}</strong></span>
                              <span>To: <strong>{c.transferred_to}</strong></span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* COMMUNICATION & HANDOFF PANEL (LOCKED ON APPROVAL / REJECTION) */}
                  <div className="border-t border-border bg-surface p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-display text-xs font-bold text-navy uppercase tracking-wider flex items-center gap-1.5">
                        <Users className="h-4 w-4 text-gold" /> Communication & Handoff Panel
                      </h4>
                      <span className="text-[11px] font-semibold text-muted-foreground">
                        Current Owner: <strong className="text-navy">{selectedAgenda.current_owner}</strong>
                      </span>
                    </div>

                    {selectedAgenda.current_state === "APPROVED" ? (
                      <div className="p-3 rounded-lg border border-gov-green/30 bg-gov-green/10 text-xs text-gov-green font-bold flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-gov-green" />
                        <span>Agenda is Approved & Finalized. Handoff controls are permanently disabled.</span>
                      </div>
                    ) : selectedAgenda.current_state === "REJECTED" ? (
                      <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-xs text-red-800 font-bold flex items-center gap-2">
                        <XCircle className="h-4 w-4 shrink-0 text-red-600" />
                        <span>Agenda is Rejected & Finalized. Handoff controls are permanently disabled.</span>
                      </div>
                    ) : selectedAgenda.is_read_only ? (
                      <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-800 flex items-center gap-2">
                        <Lock className="h-4 w-4 shrink-0 text-amber-600" />
                        <span>Handoff actions are locked while active owner is <strong>{selectedAgenda.current_owner}</strong>.</span>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <Input
                          placeholder="Enter submission / handoff remarks..."
                          value={handoffRemarks}
                          onChange={(e) => setHandoffRemarks(e.target.value)}
                          className="text-xs bg-white"
                        />

                        <div className="flex flex-wrap items-center gap-3">
                          {/* DO HANDOFF CONTROLS */}
                          {activeRole === "DO" && (
                            <>
                              <Select
                                value={handoffTargetOfficer}
                                onValueChange={(val) => {
                                  setHandoffTargetOfficer(val);
                                  const target = nodalList.find((no) => no.admin_id === val);
                                  setHandoffTargetOfficerName(target ? `${target.name} (NO)` : "Nodal Officer");
                                }}
                              >
                                <SelectTrigger className="w-[300px] h-9 text-xs bg-white border-border">
                                  <SelectValue placeholder={`Select Nodal Officer (${nodalList.length} NOs)`} />
                                </SelectTrigger>
                                <SelectContent className="max-h-64 overflow-y-auto bg-white">
                                  {nodalList.map((no) => (
                                    <SelectItem key={no.admin_id} value={no.admin_id}>
                                      {no.name} ({no.user_name}) - {no.department}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>

                              <Button
                                disabled={isHandoffSubmitting || !handoffTargetOfficer}
                                className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1.5 h-9"
                                onClick={() => handleHandoff("SUBMIT_FORWARD")}
                              >
                                <ArrowRight className="h-4 w-4" /> Submit to Nodal Officer (NO)
                              </Button>
                            </>
                          )}

                          {/* NODAL HANDOFF CONTROLS */}
                          {activeRole === "NODAL" && (
                            <>
                              <Select
                                value={handoffTargetOfficer}
                                onValueChange={(val) => {
                                  setHandoffTargetOfficer(val);
                                  const target = hodsList.find((h) => h.admin_id === val);
                                  setHandoffTargetOfficerName(target ? `${target.name} (HOD)` : "Head of Department");
                                }}
                              >
                                <SelectTrigger className="w-[300px] h-9 text-xs bg-white border-border">
                                  <SelectValue placeholder={`Select Head of Department (${hodsList.length} HODs)`} />
                                </SelectTrigger>
                                <SelectContent className="max-h-64 overflow-y-auto bg-white">
                                  {hodsList.map((h) => (
                                    <SelectItem key={h.admin_id} value={h.admin_id}>
                                      {h.name} ({h.user_name}) - {h.department}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>

                              <Button
                                disabled={isHandoffSubmitting || !handoffTargetOfficer}
                                className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1.5 h-9"
                                onClick={() => handleHandoff("SUBMIT_FORWARD")}
                              >
                                <ArrowRight className="h-4 w-4" /> Forward to HOD
                              </Button>

                              <Button
                                disabled={isHandoffSubmitting}
                                variant="outline"
                                className="border-amber-400 text-amber-800 hover:bg-amber-50 font-bold text-xs gap-1.5 h-9"
                                onClick={() => handleHandoff("RETURN_BACK")}
                              >
                                <RotateCcw className="h-4 w-4" /> Return to DO (Original Sender)
                              </Button>
                            </>
                          )}

                          {/* HOD HANDOFF CONTROLS */}
                          {activeRole === "HOD" && (
                            <>
                              <Button
                                disabled={isHandoffSubmitting}
                                variant="outline"
                                className="border-amber-400 text-amber-800 hover:bg-amber-50 font-bold text-xs gap-1.5 h-9"
                                onClick={() => handleHandoff("RETURN_BACK")}
                              >
                                <RotateCcw className="h-4 w-4" /> Return to Nodal Officer (Original Sender)
                              </Button>

                              <Button
                                disabled={isHandoffSubmitting}
                                className="bg-gov-green text-white hover:bg-gov-green/90 font-bold text-xs gap-1.5 h-9"
                                onClick={() => handleHandoff("APPROVE")}
                              >
                                <CheckCircle2 className="h-4 w-4" /> Approve Agenda
                              </Button>

                              <Button
                                disabled={isHandoffSubmitting}
                                variant="destructive"
                                className="font-bold text-xs gap-1.5 h-9"
                                onClick={() => handleHandoff("REJECT")}
                              >
                                <XCircle className="h-4 w-4" /> Reject Agenda
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center gap-3">
                  <FileText className="h-10 w-10 text-navy/20" />
                  <span>Select an agenda from the left sidebar or promote a sandbox thread.</span>
                </div>
              )}
            </div>

            {/* Right Sidebar Panel: Current Chat, Previous Chats & Recent 3 Uploaded PDFs */}
            <div className="lg:col-span-3 rounded-2xl border border-border bg-white shadow-md p-4 flex flex-col justify-between gap-4">
              <div className="space-y-4">
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <h3 className="font-display text-xs font-bold text-navy uppercase tracking-wider flex items-center gap-1.5">
                      <History className="h-3.5 w-3.5 text-gold" /> Sessions & History
                    </h3>
                    <Badge variant="outline" className="text-[10px] font-bold bg-gov-green/10 text-gov-green border-gov-green/30">
                      Active
                    </Badge>
                  </div>

                  <div className="p-3 rounded-xl bg-surface border border-navy/20 space-y-1 shadow-2xs">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Current Active Chat</span>
                    <h4 className="font-bold text-xs text-navy flex items-center gap-1.5 line-clamp-1">
                      <MessageSquare className="h-3.5 w-3.5 text-gold shrink-0" />
                      {selectedAgenda?.title || "Official Agenda Thread"}
                    </h4>
                    <p className="text-[10px] text-muted-foreground">
                      Active Model: <strong className="text-navy font-mono">{selectedModel}</strong>
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Previous Chat Sessions</span>
                    <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                      <button
                        type="button"
                        onClick={() => setMainTab("sandbox")}
                        className="w-full text-left p-2 rounded-lg text-xs font-semibold flex items-center justify-between transition-all bg-surface/60 hover:bg-surface text-navy border border-border/60"
                      >
                        <span className="line-clamp-1 flex items-center gap-1.5">
                          <MessageSquare className="h-3 w-3 text-gold" /> Personal Sandbox
                        </span>
                        <span className="text-[9px] opacity-75">{sandboxMessages.length} msgs</span>
                      </button>

                      {agendas.slice(0, 4).map((a) => (
                        <button
                          key={a.agenda_id}
                          type="button"
                          onClick={() => {
                            setMainTab("official");
                            setSelectedAgendaId(a.agenda_id);
                          }}
                          className={`w-full text-left p-2 rounded-lg text-xs font-semibold flex items-center justify-between transition-all ${
                            selectedAgendaId === a.agenda_id
                              ? "bg-navy text-white shadow-xs"
                              : "bg-surface/60 hover:bg-surface text-navy border border-border/60"
                          }`}
                        >
                          <span className="line-clamp-1 flex items-center gap-1.5">
                            <FileText className="h-3 w-3 text-gold" /> {a.title}
                          </span>
                          <span className="text-[9px] font-mono opacity-75">{a.agenda_id}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="border-t border-border/80" />

                <div className="space-y-2.5">
                  <div className="flex items-center justify-between border-b border-border pb-2">
                    <h3 className="font-display text-xs font-bold text-navy uppercase tracking-wider flex items-center gap-1.5">
                      <Paperclip className="h-3.5 w-3.5 text-blue-600" /> Recent Uploaded PDFs
                    </h3>
                    <span className="text-[10px] font-bold text-muted-foreground">{userUploadedDocs.length} Total</span>
                  </div>

                  {userUploadedDocs.length === 0 ? (
                    <div className="p-3 text-center text-xs text-muted-foreground italic border border-dashed border-border rounded-xl bg-surface/40">
                      No custom PDFs uploaded yet. Click paperclip 📎 next to text box to upload.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {userUploadedDocs.slice(0, 3).map((doc, idx) => (
                        <div key={idx} className="p-2.5 rounded-xl border border-navy/15 bg-surface/80 hover:bg-surface space-y-1 shadow-2xs transition-all">
                          <div className="flex items-start justify-between gap-1">
                            <span className="font-bold text-xs text-navy line-clamp-1 flex items-center gap-1.5">
                              <FileText className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                              {doc.doc_name}
                            </span>
                            <Badge className="bg-navy text-gold text-[9px] px-1.5 py-0 font-bold shrink-0">
                              {doc.chunk_count} chunks
                            </Badge>
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-muted-foreground font-mono pt-0.5">
                            <span>Vector Indexed</span>
                            <span className="text-gov-green font-bold">✓ BGE-M3 1024-dim</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setUploadDialogOpen(true)}
                className="w-full text-xs font-bold text-navy border-navy/30 hover:bg-navy hover:text-white gap-1.5"
              >
                <UploadCloud className="h-3.5 w-3.5 text-gold" /> Upload / Manage Documents
              </Button>
            </div>
          </div>
        )}
      </main>

      {/* PDF Customization Download Modal */}
      <Dialog open={pdfModalOpen} onOpenChange={setPdfModalOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-display text-base font-bold text-navy flex items-center gap-2">
              <Download className="h-5 w-5 text-gold" /> Download AI Response as PDF
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Customize the document filename before exporting as an official PDF.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-navy">PDF Filename *</label>
              <div className="flex items-center gap-2">
                <Input
                  value={pdfCustomFilename}
                  onChange={(e) => setPdfCustomFilename(e.target.value)}
                  placeholder="e.g. AI_Response_Agenda_20260808_1945.pdf"
                  className="text-xs font-mono"
                />
              </div>
              <p className="text-[11px] text-muted-foreground">
                Default temporary filename provided. Feel free to edit before downloading.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setPdfModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1.5"
              onClick={handleConfirmPdfDownload}
            >
              <Download className="h-4 w-4 text-gold" /> Confirm & Download PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Custom Document Dialog Modal */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-lg bg-white">
          <DialogHeader>
            <DialogTitle className="font-display text-base font-bold text-navy flex items-center gap-2">
              <UploadCloud className="h-5 w-5 text-gold" /> Upload Custom Document to RAG Database
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Uploaded documents will be chunked, embedded using BGE-M3 (1024-dim), and stored in user_chunks for {officerName} (ID: {userAdminId}).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            <div className="border-2 border-dashed border-navy/30 rounded-xl p-5 text-center bg-surface/40 hover:bg-surface transition-all">
              <input
                type="file"
                id="user-doc-file-input"
                accept=".pdf,.txt,.md,.doc,.docx"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0]);
                    setUploadStatusMsg(null);
                  }
                }}
              />
              <label htmlFor="user-doc-file-input" className="cursor-pointer flex flex-col items-center gap-2">
                <UploadCloud className="h-8 w-8 text-navy/60" />
                <span className="text-xs font-bold text-navy">
                  {selectedFile ? selectedFile.name : "Click to select PDF or TXT Document"}
                </span>
                <span className="text-[10px] text-muted-foreground">Supports PDF, TXT, MD, DOCX formats</span>
              </label>
            </div>

            {uploadStatusMsg && (
              <div className="text-xs p-3 rounded-lg bg-surface border border-border font-mono leading-relaxed">
                {uploadStatusMsg}
              </div>
            )}

          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setUploadDialogOpen(false)}>
              Close
            </Button>
            <Button
              size="sm"
              disabled={!selectedFile || isUploadingDoc}
              className="bg-navy text-white hover:bg-navy/90 font-bold text-xs gap-1.5"
              onClick={handleUploadUserDoc}
            >
              {isUploadingDoc ? <RefreshCw className="h-4 w-4 animate-spin text-gold" /> : <UploadCloud className="h-4 w-4 text-gold" />}
              {isUploadingDoc ? "Ingesting & Embedding..." : "Upload & Save to DB"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={activeWorkflowTool !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActiveWorkflowTool(null);
            setSelectedContext("Board Note");
          }
        }}
      >
        <DialogContent className="max-w-[96vw] w-[1180px] h-[90vh] p-0 overflow-hidden bg-white">
          <DialogHeader className="sr-only">
            <DialogTitle>{activeWorkflowTool === "billing" ? "Billing Forecast" : "Tender Publication Workflow"}</DialogTitle>
          </DialogHeader>
          {activeWorkflowTool && (
            <iframe
              key={activeWorkflowTool}
              title={activeWorkflowTool === "billing" ? "Billing Forecast" : "Tender Publication Workflow"}
              src={`${API_BASE}/workflow-tools/?tool=${activeWorkflowTool}`}
              className="h-full w-full border-0"
            />
          )}
        </DialogContent>
      </Dialog>

      <GovFooter />
    </div>
  );
}
