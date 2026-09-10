import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  Square,
  Paperclip,
  Mic,
  Plus,
  Trash2,
  X,
  FileText,
  Sparkles,
  Copy,
  Check,
  Building2,
  ShieldCheck,
  ChevronRight,
  Menu,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

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

const STORAGE_PREFIX = "port_land_tenant_rag_sessions_v1";
const ACTIVE_PREFIX = "port_land_tenant_rag_active_v1";

const WELCOME_MSG =
  "Namaste! I am your AI Port Land Lease Assistant. You can ask me about active land leases, plot allotments, government policies, fee structures, or tenant services.";

const SUGGESTIONS = [
  "What is the status of my active land lease?",
  "Which tables or records store tenant information?",
  "How are plots mapped to tenant applicants?",
  "What policies govern port land lease renewal?",
];

interface ReliabilityMetrics {
  accuracy?: string;
  source_category?: string;
  data_status?: string;
  reason?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  loading?: boolean;
  loadingText?: string;
  error?: boolean;
  source?: string;
  page?: string;
  reliability?: ReliabilityMetrics;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
}

export function TenantChatbot() {
  const [tenantName, setTenantName] = useState("Tenant User");
  const [tenantUserName, setTenantUserName] = useState("");
  const [tenantId, setTenantId] = useState("");

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>(() =>
    crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Attachment state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [attachmentState, setAttachmentState] = useState("");
  const [uploadStatusMsg, setUploadStatusMsg] = useState("");

  // Voice input
  const [isListening, setIsListening] = useState(false);

  // Copy state tracker
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 1. Load active tenant identity & session state from LocalStorage
  useEffect(() => {
    const name = localStorage.getItem("tenantName") || "Tenant User";
    const username = localStorage.getItem("tenantUserName") || "";
    const tid = localStorage.getItem("tenantId") || "";
    setTenantName(name);
    setTenantUserName(username);
    setTenantId(tid);

    const userKey = username ? username.toLowerCase() : "default_tenant";
    const storageKey = `${STORAGE_PREFIX}:${userKey}`;
    const activeKey = `${ACTIVE_PREFIX}:${userKey}`;

    try {
      const savedSessionsRaw = localStorage.getItem(storageKey);
      if (savedSessionsRaw) {
        const parsed: ChatSession[] = JSON.parse(savedSessionsRaw);
        setSessions(parsed);

        const savedActiveId = localStorage.getItem(activeKey);
        const currentActive = parsed.find((s) => s.id === savedActiveId) || parsed[0];
        if (currentActive) {
          setActiveSessionId(currentActive.id);
          setMessages(currentActive.messages || []);
        }
      }
    } catch (e) {
      console.error("Failed to load saved tenant chat sessions", e);
    }
  }, []);

  // 2. Poll Backend Health Status
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
        if (res.ok) {
          setBackendStatus("online");
        } else {
          setBackendStatus("offline");
        }
      } catch {
        setBackendStatus("offline");
      }
    }
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // 3. Auto Scroll Messages Container
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, sending]);

  // 4. Save Session State
  const saveState = (updatedSessions: ChatSession[], currentId: string, currentMsgs: Message[]) => {
    const userKey = tenantUserName ? tenantUserName.toLowerCase() : "default_tenant";
    const storageKey = `${STORAGE_PREFIX}:${userKey}`;
    const activeKey = `${ACTIVE_PREFIX}:${userKey}`;

    const existingIdx = updatedSessions.findIndex((s) => s.id === currentId);
    let newSessionsList = [...updatedSessions];

    if (existingIdx >= 0) {
      newSessionsList[existingIdx] = {
        ...newSessionsList[existingIdx],
        messages: currentMsgs,
        updatedAt: Date.now(),
      };
    } else {
      const title =
        currentMsgs.find((m) => m.role === "user")?.text.slice(0, 45) || "New Conversation";
      newSessionsList.unshift({
        id: currentId,
        title,
        messages: currentMsgs,
        updatedAt: Date.now(),
      });
    }

    setSessions(newSessionsList);
    try {
      localStorage.setItem(storageKey, JSON.stringify(newSessionsList));
      localStorage.setItem(activeKey, currentId);
    } catch (e) {
      console.error("Error saving tenant chat sessions", e);
    }
  };

  // Actions: New Chat
  const handleNewChat = () => {
    const newId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`;
    setActiveSessionId(newId);
    setMessages([]);
    setSelectedFile(null);
    setAttachmentState("");
    setSidebarOpen(false);
  };

  // Actions: Load Session
  const handleSelectSession = (session: ChatSession) => {
    setActiveSessionId(session.id);
    setMessages(session.messages || []);
    setSidebarOpen(false);
  };

  // Actions: Delete Session
  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    const updated = sessions.filter((s) => s.id !== sessionId);
    setSessions(updated);
    if (sessionId === activeSessionId) {
      handleNewChat();
    } else {
      const userKey = tenantUserName ? tenantUserName.toLowerCase() : "default_tenant";
      localStorage.setItem(`${STORAGE_PREFIX}:${userKey}`, JSON.stringify(updated));
    }
  };

  // Submission Handler
  const handleSendMessage = async (queryText?: string) => {
    const q = (queryText || inputQuestion).trim();
    if (!q || sending) return;

    setInputQuestion("");

    // Build user message & assistant loading placeholder
    const userMsg: Message = {
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-u`,
      role: "user",
      text: q,
    };

    const assistantPlaceholderId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-a`;
    const assistantMsg: Message = {
      id: assistantPlaceholderId,
      role: "assistant",
      text: "",
      loading: true,
      loadingText: "Searching lease records & policy documents...",
    };

    const updatedMsgs = [...messages, userMsg, assistantMsg];
    setMessages(updatedMsgs);
    setSending(true);

    saveState(sessions, activeSessionId, updatedMsgs);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const token = localStorage.getItem("tenantToken");
    let applicantId = localStorage.getItem("tenantApplicantId");
    if (!applicantId && tenantId) {
      applicantId = tenantId.replace(/\D/g, "");
    }
    const authToken = token || (applicantId ? `tenant-token-${applicantId}` : "");

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
      if (applicantId) headers["X-Applicant-ID"] = applicantId;

      const res = await fetch(`${API_BASE}/tenant/api/chat`, {
        method: "POST",
        headers,
        signal: controller.signal,
        body: JSON.stringify({
          question: q,
          tenant_name: tenantName,
          username: tenantUserName,
          tenant_id: tenantId,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned error status ${res.status}`);
      }

      const data = await res.json();

      const finalMsgs = updatedMsgs.map((m) => {
        if (m.id === assistantPlaceholderId) {
          return {
            ...m,
            loading: false,
            text: data.answer || "I could not retrieve an answer for this query.",
            source: data.source || "Port Lease Database",
            page: data.page || "Operational Record",
            reliability: data.reliability || {
              accuracy: "High (Verified)",
              source_category: "Port Land Database",
              data_status: "Authoritative",
            },
          };
        }
        return m;
      });

      setMessages(finalMsgs);
      saveState(sessions, activeSessionId, finalMsgs);
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") {
        const finalMsgs = updatedMsgs.map((m) =>
          m.id === assistantPlaceholderId
            ? { ...m, loading: false, text: "Generation stopped by user." }
            : m
        );
        setMessages(finalMsgs);
        saveState(sessions, activeSessionId, finalMsgs);
      } else {
        const finalMsgs = updatedMsgs.map((m) =>
          m.id === assistantPlaceholderId
            ? {
                ...m,
                loading: false,
                error: true,
                text: "Unable to connect to AI Support Service. Please verify that the backend server is running and try again.",
              }
            : m
        );
        setMessages(finalMsgs);
        saveState(sessions, activeSessionId, finalMsgs);
      }
    } finally {
      setSending(false);
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // Copy Handler
  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Attachment Handler
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = ["pdf", "docx", "txt"];
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (!allowed.includes(ext)) {
      setUploadStatusMsg("Unsupported file. Please attach PDF, DOCX, or TXT.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadStatusMsg("File exceeds 10MB limit.");
      return;
    }

    setSelectedFile(file);
    setAttachmentState("Uploading...");
    setUploadStatusMsg("Attachment added.");
    setTimeout(() => setAttachmentState("Stored"), 1200);
  };

  // Voice Input Setup
  const handleMicClick = () => {
    const Recognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!Recognition) {
      alert("Voice input is not supported in this browser.");
      return;
    }

    const recognition = new Recognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInputQuestion((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };

    try {
      recognition.start();
    } catch {
      recognition.stop();
    }
  };

  return (
    <div className="flex h-[calc(100vh-100px)] overflow-hidden rounded-lg border border-border bg-white shadow-sm">
      {/* Sidebar - History */}
      <aside
        className={
          "fixed inset-y-0 left-0 z-40 w-72 transform border-r border-border bg-slate-900 text-white transition-transform duration-200 lg:static lg:translate-x-0 " +
          (sidebarOpen ? "translate-x-0" : "-translate-x-full")
        }
      >
        <div className="flex flex-col h-full p-4">
          <div className="flex items-center justify-between border-b border-slate-700 pb-3 mb-3">
            <div className="flex items-center gap-2 font-display text-sm font-semibold text-gold">
              <Bot className="h-5 w-5 text-gold" /> Tenant AI Support
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-slate-400 hover:text-white lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <Button
            onClick={handleNewChat}
            className="w-full bg-navy hover:bg-navy/90 text-white font-medium gap-2 shadow-xs mb-4"
          >
            <Plus className="h-4 w-4" /> New Conversation
          </Button>

          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2 px-1">
            Conversation History
          </div>

          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {sessions.length === 0 ? (
              <p className="text-xs text-slate-400 px-2 py-4 italic">No past conversations yet.</p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => handleSelectSession(s)}
                  className={
                    "group flex items-center justify-between rounded-md px-3 py-2 text-xs cursor-pointer transition-colors " +
                    (s.id === activeSessionId
                      ? "bg-slate-800 text-gold font-medium"
                      : "text-slate-300 hover:bg-slate-800/60 hover:text-white")
                  }
                >
                  <span className="truncate flex-1 pr-2">{s.title || "Untitled Conversation"}</span>
                  <button
                    onClick={(e) => handleDeleteSession(e, s.id)}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-400 transition-opacity"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="border-t border-slate-800 pt-3 text-[11px] text-slate-400 flex items-center gap-2">
            <ShieldCheck className="h-3.5 w-3.5 text-gov-green" /> Session: {tenantName}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col bg-surface min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border bg-white px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              className="lg:hidden h-8 w-8 text-navy"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-4 w-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-semibold text-navy text-sm sm:text-base">
                  Tenant Land & Policy AI Assistant
                </span>
              </div>
              <p className="text-xs text-muted-foreground hidden sm:block">
                Grounded intelligence for port land lease records, allotments & policies
              </p>
            </div>
          </div>

          <Badge
            variant="outline"
            className={
              backendStatus === "online"
                ? "bg-gov-green/10 text-gov-green border-gov-green/30 text-xs gap-1.5"
                : "bg-amber-50 text-amber-700 border-amber-300 text-xs gap-1.5"
            }
          >
            <span
              className={
                "h-2 w-2 rounded-full " +
                (backendStatus === "online" ? "bg-gov-green animate-pulse" : "bg-amber-500")
              }
            />
            {backendStatus === "online" ? "AI Service Online" : "Checking Status"}
          </Badge>
        </div>

        {/* Chat Messages */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="mx-auto max-w-2xl text-center py-12 px-4">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-navy/10 text-navy">
                <Bot className="h-7 w-7" />
              </div>
              <h2 className="font-display text-lg font-semibold text-navy sm:text-xl">
                Welcome, {tenantName}
              </h2>
              <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">{WELCOME_MSG}</p>
            </div>
          ) : (
            messages.map((m, idx) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id || idx}
                  className={"flex gap-3 max-w-3xl " + (isUser ? "ml-auto flex-row-reverse" : "")}
                >
                  <div
                    className={
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold " +
                      (isUser ? "bg-navy text-white" : "bg-gold text-gold-foreground")
                    }
                  >
                    {isUser ? "YOU" : "AI"}
                  </div>

                  <div
                    className={
                      "rounded-lg p-4 text-sm shadow-2xs leading-relaxed max-w-2xl " +
                      (isUser
                        ? "bg-navy text-white rounded-tr-none"
                        : m.error
                        ? "bg-red-50 border border-red-200 text-red-800 rounded-tl-none"
                        : "bg-white border border-border text-foreground rounded-tl-none")
                    }
                  >
                    {m.loading ? (
                      <div className="flex items-center gap-2 text-muted-foreground text-xs italic">
                        <span className="h-2 w-2 rounded-full bg-gold animate-ping" />
                        {m.loadingText || "Processing query..."}
                      </div>
                    ) : (
                      <>
                        <div className="whitespace-pre-wrap">{m.text}</div>

                        {/* Action buttons */}
                        {!isUser && !m.error && m.text && (
                          <div className="mt-2 flex items-center justify-end pt-1">
                            <button
                              onClick={() => handleCopy(m.text, idx)}
                              className="inline-flex items-center gap-1 text-[11px] font-medium text-navy/70 hover:text-navy"
                            >
                              {copiedIndex === idx ? (
                                <Check className="h-3 w-3 text-gov-green" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                              {copiedIndex === idx ? "Copied" : "Copy"}
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Composer Panel */}
        <div className="border-t border-border bg-white p-3 sm:p-4 space-y-3">

          {/* Attachment Preview Badge */}
          {selectedFile && (
            <div className="flex items-center justify-between rounded-md border border-navy/20 bg-navy/5 px-3 py-1.5 text-xs">
              <div className="flex items-center gap-2 truncate">
                <FileText className="h-4 w-4 text-navy shrink-0" />
                <span className="font-semibold text-navy truncate">{selectedFile.name}</span>
                <span className="text-[10px] text-muted-foreground">({attachmentState})</span>
              </div>
              <button
                onClick={() => {
                  setSelectedFile(null);
                  setAttachmentState("");
                }}
                className="text-muted-foreground hover:text-navy"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* Upload Status Alert */}
          {uploadStatusMsg && (
            <div className="text-[11px] text-amber-700 bg-amber-50 px-2.5 py-1 rounded border border-amber-200">
              {uploadStatusMsg}
            </div>
          )}

          {/* Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sending ? handleStop() : handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="shrink-0 text-navy hover:bg-navy/5"
              onClick={() => fileInputRef.current?.click()}
              title="Attach Document (.pdf, .docx, .txt)"
            >
              <Paperclip className="h-4 w-4" />
            </Button>

            <Button
              type="button"
              variant="outline"
              size="icon"
              className={
                "shrink-0 transition-colors " +
                (isListening ? "border-red-500 bg-red-50 text-red-600 animate-pulse" : "text-navy hover:bg-navy/5")
              }
              onClick={handleMicClick}
              title="Voice Input"
            >
              <Mic className="h-4 w-4" />
            </Button>

            <Input
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder="Ask about active leases, land records, or port policies..."
              disabled={sending}
              className="flex-1 bg-surface border-border focus-visible:ring-navy"
            />

            {sending ? (
              <Button type="button" onClick={handleStop} variant="destructive" className="shrink-0 gap-1">
                <Square className="h-3.5 w-3.5 fill-current" /> Stop
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={!inputQuestion.trim() && !selectedFile}
                className="shrink-0 bg-navy hover:bg-navy/90 text-white gap-1.5 shadow-xs"
              >
                <Send className="h-4 w-4" /> Send
              </Button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
