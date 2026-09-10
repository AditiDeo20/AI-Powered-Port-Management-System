// Real RAG Client Logic for Port Land Lease MMS AI Assistant

// Dynamic state - starts completely empty without hardcoded history or fake chats
let sessions = []; // Array of { id, title, messages: [] }
let activeSessionId = generateId();
let activeSessionMessages = [];
let isSessionSavedInHistory = false;

// Updated suggestion chips
const suggestionItems = [
  "what is MBPT?",
  "What is the MPA Act of 2021?",
  "Summarize the Whole Content",
  "Summarize DC Regulation 1991"
];

// Dynamic Loading Messages for RAG Pipeline
let loadingPhrases = [
  "Routing query...",
  "Analyzing context..."
];
let loadingPhraseInterval = null;

function updateLoadingPhrases(route, table) {
  if (route === "MULTI_HOP") {
    loadingPhrases = [
      "Starting Multi-Hop Agent...",
      "Hop 1: Querying SQL Database",
      table ? `Looking in Table ${table}` : "Fetching SQL records...",
      "Hop 2: Searching Policy Documents...",
      "Synthesizing combined answer..."
    ];
  } else if (route === "DATABASE") {
    loadingPhrases = [
      "Looking in DataBase",
      "Looking in Structural Data",
      table ? `Looking in ${table}` : "Fetching from Table",
      "Loading llama"
    ];
  } else {
    loadingPhrases = [
      "Searching in documents...",
      "Retrieving relevant chunks...",
      "Analyzing context & policy rules...",
      "Checking hidden meanings...",
      "Combining search results...",
      "Loading llama"
    ];
  }
  currentPhraseIndex = 0;
  updateLoadingPhraseText();
}

let currentPhraseIndex = 0;

function startLoadingPhraseTimer() {
  stopLoadingPhraseTimer();
  currentPhraseIndex = Math.floor(Math.random() * loadingPhrases.length);
  updateLoadingPhraseText();

  loadingPhraseInterval = setInterval(() => {
    let newIdx = Math.floor(Math.random() * loadingPhrases.length);
    if (newIdx === currentPhraseIndex) {
      newIdx = (currentPhraseIndex + 1) % loadingPhrases.length;
    }
    currentPhraseIndex = newIdx;
    updateLoadingPhraseText();
  }, 3500);
}

function updateLoadingPhraseText() {
  const el = document.getElementById("loading-phrase-text");
  if (el) {
    el.textContent = loadingPhrases[currentPhraseIndex];
  }
}

function stopLoadingPhraseTimer() {
  if (loadingPhraseInterval) {
    clearInterval(loadingPhraseInterval);
    loadingPhraseInterval = null;
  }
}

const LOCAL_STORAGE_SESSIONS_KEY = "port_land_rag_sessions_v1";
const LOCAL_STORAGE_ACTIVE_KEY = "port_land_rag_active_session_v1";

let healthPollInterval = null;

let uploadedDocumentsList = [];

document.addEventListener("DOMContentLoaded", () => {
  initIcons();
  loadStoredState();
  startHealthPolling();
  renderHistory();
  renderSuggestions();
  renderMessages();
  loadUploadedDocuments();
  setupEventListeners();
});

async function loadUploadedDocuments() {
  const container = document.getElementById("uploaded-docs-list");
  if (!container) return;

  try {
    const res = await fetch("/api/documents");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success || !Array.isArray(data.documents)) return;

    uploadedDocumentsList = data.documents;
    renderUploadedDocuments();
    updateContextDropdown();
  } catch (err) {
    console.warn("Error fetching uploaded documents:", err);
  }
}

function renderUploadedDocuments() {
  const container = document.getElementById("uploaded-docs-list");
  if (!container) return;

  if (uploadedDocumentsList.length === 0) {
    container.innerHTML = `<div class="p-2 text-center text-muted-foreground italic text-[11px]">No uploaded documents yet.</div>`;
    return;
  }

  container.innerHTML = "";

  uploadedDocumentsList.forEach((doc) => {
    const item = document.createElement("div");
    item.className = "group flex flex-col p-2 rounded-lg border border-border/80 bg-secondary/50 hover:bg-secondary transition-colors text-xs font-medium cursor-pointer mb-1";
    
    let statusBadge = "";
    if (doc.status === "completed") {
      statusBadge = `<span class="inline-flex items-center gap-1 text-[10px] text-gov-green font-semibold bg-gov-green/10 px-1.5 py-0.5 rounded border border-gov-green/20"><i data-lucide="check-circle" class="w-3 h-3"></i> ${doc.chunk_count || 0} chunks</span>`;
    } else if (doc.status === "processing" || doc.status === "pending") {
      statusBadge = `<span class="inline-flex items-center gap-1 text-[10px] text-gold font-semibold bg-gold/10 px-1.5 py-0.5 rounded border border-gold/20"><i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> ${doc.progress || 0}%</span>`;
    } else if (doc.status === "failed") {
      statusBadge = `<span class="inline-flex items-center gap-1 text-[10px] text-red-600 font-semibold bg-red-50 px-1.5 py-0.5 rounded border border-red-200"><i data-lucide="alert-circle" class="w-3 h-3"></i> Failed</span>`;
    }

    item.innerHTML = `
      <div class="flex items-center justify-between gap-1 w-full">
        <span class="truncate text-navy font-semibold text-[11px]" title="${escapeHtml(doc.doc_name)}">${escapeHtml(doc.doc_name)}</span>
        ${statusBadge}
      </div>
    `;

    item.onclick = () => {
      const select = document.getElementById("context-select");
      if (select) {
        let optFound = false;
        for (let i = 0; i < select.options.length; i++) {
          if (select.options[i].value === doc.doc_name) {
            select.selectedIndex = i;
            optFound = true;
            break;
          }
        }
        if (!optFound) {
          const opt = document.createElement("option");
          opt.value = doc.doc_name;
          opt.textContent = `📄 ${doc.doc_name}`;
          select.appendChild(opt);
          select.value = doc.doc_name;
        }
      }
    };

    container.appendChild(item);
  });

  initIcons();
}

function updateContextDropdown() {
  const select = document.getElementById("context-select");
  if (!select) return;

  const currentVal = select.value;
  
  const defaultOptions = [
    "Board Note", "Breach", "Chairman Note", "Letter",
    "RTI", "SOR", "Suit", "Tender Draft"
  ];

  const allDocNames = new Set(defaultOptions);
  uploadedDocumentsList.forEach(d => {
    if (d.doc_name) allDocNames.add(d.doc_name);
  });

  select.innerHTML = "";
  
  const allOpt = document.createElement("option");
  allOpt.value = "All";
  allOpt.textContent = "All Contexts & Docs";
  select.appendChild(allOpt);

  allDocNames.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    const isUploaded = uploadedDocumentsList.some(d => d.doc_name === name);
    opt.textContent = isUploaded ? `📄 ${name}` : name;
    select.appendChild(opt);
  });

  if (Array.from(select.options).some(o => o.value === currentVal)) {
    select.value = currentVal;
  } else {
    select.value = "Board Note";
  }
}

function loadStoredState() {
  try {
    const rawSessions = localStorage.getItem(LOCAL_STORAGE_SESSIONS_KEY);
    const rawActiveId = localStorage.getItem(LOCAL_STORAGE_ACTIVE_KEY);

    if (rawSessions) {
      sessions = JSON.parse(rawSessions) || [];
    }

    if (rawActiveId && sessions.some(s => s.id === rawActiveId)) {
      activeSessionId = rawActiveId;
      const activeSess = sessions.find(s => s.id === rawActiveId);
      if (activeSess) {
        activeSessionMessages = [...activeSess.messages];
        isSessionSavedInHistory = true;
      }
    } else if (sessions.length > 0) {
      activeSessionId = sessions[0].id;
      activeSessionMessages = [...sessions[0].messages];
      isSessionSavedInHistory = true;
    }
  } catch (e) {
    console.warn("Failed to load local storage sessions:", e);
  }

  // Background fetch to sync with backend server
  syncWithBackendServer();
}

function saveState() {
  try {
    localStorage.setItem(LOCAL_STORAGE_SESSIONS_KEY, JSON.stringify(sessions));
    localStorage.setItem(LOCAL_STORAGE_ACTIVE_KEY, activeSessionId);
  } catch (e) {
    console.warn("Failed to save to local storage:", e);
  }

  // Async sync with backend server
  fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessions: sessions })
  }).catch(err => console.warn("Backend session sync warning:", err));
}

async function syncWithBackendServer() {
  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && Array.isArray(data.sessions) && data.sessions.length > 0) {
      // If local is empty, populate from server
      if (sessions.length === 0) {
        sessions = data.sessions;
        if (sessions.length > 0 && activeSessionMessages.length === 0) {
          activeSessionId = sessions[0].id;
          activeSessionMessages = [...sessions[0].messages];
          isSessionSavedInHistory = true;
        }
        saveState();
        renderHistory();
        renderMessages();
      }
    }
  } catch (err) {
    console.warn("Could not sync with backend server on startup:", err);
  }
}

async function deleteSession(sessionId, event) {
  if (event) event.stopPropagation();

  sessions = sessions.filter(s => s.id !== sessionId);

  if (activeSessionId === sessionId) {
    if (sessions.length > 0) {
      activeSessionId = sessions[0].id;
      activeSessionMessages = [...sessions[0].messages];
      isSessionSavedInHistory = true;
    } else {
      activeSessionId = generateId();
      activeSessionMessages = [];
      isSessionSavedInHistory = false;
    }
    renderMessages();
  }

  saveState();
  renderHistory();

  try {
    await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
  } catch (e) {
    console.warn("Failed to delete session from server:", e);
  }
}

function generateId() {
  return 'sess_' + Math.random().toString(36).substr(2, 9);
}

function initIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Poll Backend Model Health until RAG pipeline is ready
function startHealthPolling() {
  const overlay = document.getElementById("loading-overlay");
  const titleEl = document.getElementById("loading-title");
  const statusEl = document.getElementById("loading-status");
  const retryBtn = document.getElementById("retry-backend-btn");
  const spinnerContainer = document.getElementById("spinner-container");
  const headerBadge = document.getElementById("header-status-badge");

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();

      if (data.status === "online" && data.rag_services_ready) {
        if (titleEl) titleEl.textContent = "RAG AI Pipeline Ready!";
        if (statusEl) statusEl.textContent = "BGE-M3 Model, PostgreSQL pgvector & Ollama Qwen 2.5 loaded.";
        
        if (headerBadge) {
          headerBadge.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-gov-green/30 bg-gov-green/5 text-gov-green";
          headerBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-gov-green animate-pulse"></span> Online`;
        }

        setTimeout(() => {
          if (overlay) {
            overlay.classList.add("opacity-0", "pointer-events-none");
          }
        }, 400);

        if (healthPollInterval) clearInterval(healthPollInterval);
      } else if (data.status === "loading") {
        if (titleEl) titleEl.textContent = "Loading Backend AI Model";
        if (statusEl) statusEl.textContent = "Loading BGE-M3 Embedding Model, PostgreSQL pgvector & Qwen 2.5 LLM...";
      } else {
        showLoadingError(data.init_error || "RAG Services failed to initialize. Please check database & model.");
      }
    } catch (err) {
      showLoadingError("Could not connect to backend server at http://127.0.0.1:8000.");
    }
  }

  function showLoadingError(errorMsg) {
    if (titleEl) titleEl.textContent = "Backend Connection Failed";
    if (statusEl) statusEl.textContent = errorMsg;
    if (retryBtn) retryBtn.classList.remove("hidden");
    if (spinnerContainer) {
      spinnerContainer.innerHTML = `<div class="w-12 h-12 rounded-xl bg-red-100 text-red-600 flex items-center justify-center text-2xl font-bold border border-red-200">⚠️</div>`;
    }
    if (headerBadge) {
      headerBadge.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-red-500/30 bg-red-500/10 text-red-600";
      headerBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-red-500"></span> Offline`;
    }
  }

  retryBtn.onclick = () => {
    retryBtn.classList.add("hidden");
    if (spinnerContainer) {
      spinnerContainer.innerHTML = `
        <div class="absolute inset-0 rounded-full border-4 border-navy/15 border-t-navy border-r-gold animate-spin"></div>
        <div class="w-12 h-12 rounded-xl bg-navy text-white flex items-center justify-center text-xl shadow-md font-display font-bold">⚓</div>
      `;
    }
    checkHealth();
  };

  checkHealth();
  healthPollInterval = setInterval(checkHealth, 1500);
}

// Render Conversation History Sidebar (1 item per chat session)
function renderHistory() {
  const container = document.getElementById("history-list");
  container.innerHTML = "";

  if (sessions.length === 0) {
    container.innerHTML = `<div class="p-3 text-xs text-muted-foreground italic text-center">No previous chat sessions.</div>`;
    return;
  }

  sessions.forEach((session) => {
    const li = document.createElement("li");
    li.className = "group relative flex items-center";

    const isActive = session.id === activeSessionId;
    const btn = document.createElement("button");
    
    btn.className = `w-full text-left truncate rounded-md pl-3 pr-8 py-2 text-sm font-medium transition-colors flex items-center gap-2 ${
      isActive
        ? "bg-navy/10 text-navy font-semibold border border-navy/20"
        : "text-foreground/80 hover:bg-secondary hover:text-navy"
    }`;
    
    btn.innerHTML = `<i data-lucide="message-square" class="w-3.5 h-3.5 ${isActive ? 'text-navy' : 'text-muted-foreground'} shrink-0"></i><span class="truncate">${escapeHtml(session.title)}</span>`;
    
    btn.onclick = () => {
      loadSession(session.id);
      closeMobileSidebar();
    };
    
    const delBtn = document.createElement("button");
    delBtn.className = "absolute right-2 text-muted-foreground hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-50";
    delBtn.title = "Delete chat session";
    delBtn.innerHTML = `<i data-lucide="trash-2" class="w-3.5 h-3.5"></i>`;
    delBtn.onclick = (e) => deleteSession(session.id, e);

    li.appendChild(btn);
    li.appendChild(delBtn);
    container.appendChild(li);
  });
  
  initIcons();
}

function loadSession(sessionId) {
  const sess = sessions.find(s => s.id === sessionId);
  if (sess) {
    activeSessionId = sess.id;
    activeSessionMessages = [...sess.messages];
    isSessionSavedInHistory = true;
    saveState();
    renderMessages();
    renderHistory();
  }
}

// Render Suggestion Chips
function renderSuggestions() {
  const container = document.getElementById("suggestions-container");
  container.innerHTML = "";

  suggestionItems.forEach((s) => {
    const btn = document.createElement("button");
    btn.className = "rounded-full border border-border bg-secondary px-3.5 py-1 text-xs text-foreground/80 hover:border-navy/40 hover:bg-white hover:text-navy transition-all shadow-2xs font-medium";
    btn.textContent = s;
    btn.onclick = () => {
      document.getElementById("chat-input").value = s;
      submitPrompt(s);
    };
    container.appendChild(btn);
  });
}

// Full Render Messages Container
function renderMessages() {
  const container = document.getElementById("chat-messages");
  container.innerHTML = "";

  if (activeSessionMessages.length === 0) {
    container.innerHTML = `
      <div class="h-full flex flex-col items-center justify-center text-center p-6 my-auto text-muted-foreground">
        <div class="w-12 h-12 rounded-xl bg-navy/5 text-navy flex items-center justify-center text-2xl mb-3 border border-navy/10">⚓</div>
        <h4 class="font-display font-semibold text-base text-navy">Welcome to Port Land RAG Chatbot</h4>
        <p class="text-xs max-w-sm mt-1">Ask any question regarding port land leases, policies, land records, or tenant agreements.</p>
      </div>
    `;
    return;
  }

  activeSessionMessages.forEach((msg, idx) => {
    const bubbleEl = createBubbleElement(msg, idx);
    container.appendChild(bubbleEl);
  });

  initIcons();
  scrollToBottom();
}

function renderHopsHtml(hops) {
  if (!hops || hops.length === 0) return '';
  return `
    <div class="font-semibold text-navy flex items-center gap-1.5 mb-1.5 text-xs">
      <i data-lucide="git-fork" class="w-3.5 h-3.5 text-navy"></i> Multi-Hop Execution Chain:
    </div>
    <div class="space-y-1 font-mono text-[11px]">
      ${hops.map(h => `
        <div class="flex items-start gap-1.5 text-slate-700 bg-white/80 p-1.5 rounded border border-navy/15">
          <span class="shrink-0 px-1.5 py-0.5 bg-navy text-white rounded text-[10px] font-bold">Hop ${h.step}</span>
          <div>
            <span class="font-semibold text-navy">${escapeHtml(h.action)}</span>
            <span class="text-slate-600"> — ${escapeHtml(h.details)}</span>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// Helper to render message text content (shows spinning loop icon when waiting for first token)
function getBubbleTextContent(msg) {
  if (msg.isStreaming && !msg.text) {
    return `
      <div class="flex items-center gap-2 text-navy py-1 px-0.5">
        <div class="w-4 h-4 rounded-full border-2 border-navy/20 border-t-navy border-r-gold animate-spin shrink-0"></div>
        <span id="loading-phrase-text" class="text-xs font-medium text-muted-foreground animate-pulse">${escapeHtml(loadingPhrases[currentPhraseIndex] || loadingPhrases[0])}</span>
      </div>
    `;
  }
  return `${escapeHtml(msg.text)}${msg.isStreaming ? '<span class="inline-block w-1.5 h-4 bg-navy ml-1 animate-pulse align-middle"></span>' : ''}`;
}

// Smooth Direct DOM Update for Real-Time Streaming (Zero Blinking!)
function updateStreamingBubble(idx) {
  const msg = activeSessionMessages[idx];
  if (!msg) return;

  const textEl = document.getElementById(`msg-text-${idx}`);
  if (!textEl) {
    renderMessages();
    return;
  }

  // Update text directly without re-animating parent container
  textEl.innerHTML = getBubbleTextContent(msg);

  // Stop loading phrase timer once response tokens start arriving or streaming finishes
  if (msg.text || !msg.isStreaming) {
    stopLoadingPhraseTimer();
  }

  // Update multi-hop steps UI
  const hopsEl = document.getElementById(`msg-hops-${idx}`);
  if (hopsEl && msg.hops && msg.hops.length > 0) {
    if (hopsEl.classList.contains("hidden")) {
      hopsEl.classList.remove("hidden");
    }
    hopsEl.innerHTML = renderHopsHtml(msg.hops);
    initIcons();
  }

  // Update metadata badge if available
  const metaEl = document.getElementById(`msg-meta-${idx}`);
  if (metaEl && msg.source) {
    if (metaEl.classList.contains("hidden")) {
      metaEl.classList.remove("hidden");
    }
    metaEl.innerHTML = `
      <span class="inline-flex items-center gap-1 border border-navy/20 bg-white/80 px-2 py-0.5 rounded text-navy font-medium">
        <i data-lucide="file-text" class="h-3 w-3"></i> ${escapeHtml(msg.source)}
      </span>
      ${msg.page ? `<span>· ${escapeHtml(msg.page)}</span>` : ''}
    `;
    initIcons();
  }

  // Unhide action buttons (Copy & Download PDF) when response finishes streaming
  const actionsEl = document.getElementById(`msg-actions-${idx}`);
  if (actionsEl && !msg.isStreaming && msg.text && !msg.isError) {
    if (actionsEl.classList.contains("hidden")) {
      actionsEl.classList.remove("hidden");
      initIcons();
    }
  }

  // Finalize when streaming completes
  if (msg.metrics && !msg.isStreaming) {
    renderMessages();
    return;
  }

  scrollToBottom();
}

function createBubbleElement(msg, idx) {
  const isUser = msg.role === "user";
  const isError = msg.isError;
  const wrapper = document.createElement("div");
  wrapper.id = `msg-wrapper-${idx}`;
  // animate-fade-in only applied once on creation
  wrapper.className = `flex ${isUser ? "justify-end" : "justify-start"} animate-fade-in`;

  const card = document.createElement("div");
  card.className = `max-w-[85%] sm:max-w-[80%] rounded-xl px-4.5 py-3 text-sm shadow-card ${
    isUser
      ? "bg-navy text-white rounded-br-none"
      : isError
      ? "border border-red-300 bg-red-50 text-red-900 rounded-bl-none font-sans"
      : "border border-border bg-secondary text-foreground rounded-bl-none"
  }`;

  const hasHops = !isUser && !isError && msg.hops && msg.hops.length > 0;
  let innerHTML = `
    <div id="msg-hops-${idx}" class="${hasHops ? '' : 'hidden'} mb-2.5 p-2.5 rounded-lg bg-navy/5 border border-navy/15 text-xs">
      ${hasHops ? renderHopsHtml(msg.hops) : ''}
    </div>
    <div id="msg-text-${idx}" class="leading-relaxed whitespace-pre-wrap">${getBubbleTextContent(msg)}</div>
  `;


  if (isError && msg.errorDetails) {
    innerHTML += `<div class="mt-2 text-xs font-mono text-red-700 bg-red-100/60 p-2 rounded border border-red-200">${escapeHtml(msg.errorDetails)}</div>`;
  }

  // Assistant citations
  const hasMeta = !isUser && !isError && msg.source;
  innerHTML += `
    <div id="msg-meta-${idx}" class="${hasMeta ? '' : 'hidden'} mt-3 flex flex-wrap items-center gap-2 border-t border-border/70 pt-2 text-[11px] text-muted-foreground">
      ${hasMeta ? `
        <span class="inline-flex items-center gap-1 border border-navy/20 bg-white/80 px-2 py-0.5 rounded text-navy font-medium">
          <i data-lucide="file-text" class="h-3 w-3"></i> ${escapeHtml(msg.source)}
        </span>
        ${msg.page ? `<span>· ${escapeHtml(msg.page)}</span>` : ''}
      ` : ''}
    </div>
  `;

  // Action buttons (Copy and Download PDF) - visible only after full response finishes
  const hasActions = !isUser && !isError;
  innerHTML += `
    <div id="msg-actions-${idx}" class="${hasActions && !msg.isStreaming && msg.text ? '' : 'hidden'} mt-2.5 pt-2 border-t border-border/60 flex items-center gap-2">
      <button onclick="copyResponseToClipboard(${idx}, this)" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-border text-muted-foreground hover:text-navy hover:border-navy/30 transition-colors shadow-2xs font-medium text-[11px] cursor-pointer" title="Copy response to clipboard">
        <i data-lucide="copy" class="w-3.5 h-3.5"></i> Copy
      </button>
      <button onclick="downloadResponseAsPdf(${idx})" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-border text-muted-foreground hover:text-navy hover:border-navy/30 transition-colors shadow-2xs font-medium text-[11px] cursor-pointer" title="Download response as PDF">
        <i data-lucide="download" class="w-3.5 h-3.5"></i> Download PDF
      </button>
    </div>
  `;

  // Metrics toggle if present from backend
  if (!isUser && !isError && msg.metrics && Object.keys(msg.metrics).length > 0) {
    let metricsHtml = '';
    if (msg.metrics.embedding_time) metricsHtml += `<div>Embedding: ${msg.metrics.embedding_time}</div>`;
    if (msg.metrics.retrieval_time) metricsHtml += `<div>Retrieval: ${msg.metrics.retrieval_time}</div>`;
    if (msg.metrics.prompt_time) metricsHtml += `<div>Prompting: ${msg.metrics.prompt_time}</div>`;
    if (msg.metrics.routing_time) metricsHtml += `<div>Routing: ${msg.metrics.routing_time}</div>`;
    if (msg.metrics.generation_time) metricsHtml += `<div>Generation: ${msg.metrics.generation_time}</div>`;

    innerHTML += `
      <div class="mt-2 text-[10px]">
        <button onclick="toggleMetrics(${idx})" class="text-navy hover:underline font-mono text-[10px] flex items-center gap-1">
          <i data-lucide="activity" class="w-3 h-3"></i> Pipeline Performance Metrics
        </button>
        <div id="metrics-${idx}" class="hidden mt-1.5 p-2 rounded bg-white border border-border font-mono text-[10px] space-y-0.5 text-slate-600">
          ${metricsHtml}
          <div class="font-bold text-navy pt-1 mt-1 border-t border-border/50">Total Time: ${msg.metrics.total_time || 'N/A'}</div>
        </div>
      </div>
    `;
  }

  card.innerHTML = innerHTML;
  wrapper.appendChild(card);
  return wrapper;
}

async function copyResponseToClipboard(idx, btnEl) {
  const msg = activeSessionMessages[idx];
  if (!msg || !msg.text) return;

  try {
    await navigator.clipboard.writeText(msg.text);
    if (btnEl) {
      const origHtml = btnEl.innerHTML;
      btnEl.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 text-gov-green"></i> <span class="text-gov-green">Copied!</span>`;
      initIcons();
      setTimeout(() => {
        btnEl.innerHTML = origHtml;
        initIcons();
      }, 2000);
    }
  } catch (err) {
    console.error("Failed to copy response:", err);
  }
}

function downloadResponseAsPdf(idx) {
  const msg = activeSessionMessages[idx];
  if (!msg || !msg.text) return;

  if (!window.jspdf || !window.jspdf.jsPDF) {
    alert("PDF generator library is not loaded properly.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  const margin = 15;
  const pageWidth = doc.internal.pageSize.getWidth() - 2 * margin;

  // Header Title
  doc.setFontSize(13);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(11, 37, 69);
  doc.text("Port Land Lease MMS - AI Assistant Response", margin, 18);

  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(100);
  doc.text(`Generated on: ${new Date().toLocaleString()}`, margin, 24);
  if (msg.source) {
    doc.text(`Source Document: ${msg.source}${msg.page ? ' (' + msg.page + ')' : ''}`, margin, 29);
    doc.setDrawColor(220);
    doc.line(margin, 33, doc.internal.pageSize.getWidth() - margin, 33);
  } else {
    doc.setDrawColor(220);
    doc.line(margin, 28, doc.internal.pageSize.getWidth() - margin, 28);
  }

  doc.setFontSize(10);
  doc.setTextColor(30);

  const splitText = doc.splitTextToSize(msg.text, pageWidth);
  let y = msg.source ? 40 : 35;
  const pageHeight = doc.internal.pageSize.getHeight();
  const lineHeight = 6;

  splitText.forEach(line => {
    if (y > pageHeight - 15) {
      doc.addPage();
      y = 20;
    }
    doc.text(line, margin, y);
    y += lineHeight;
  });

  doc.save(`chat_response_${idx + 1}.pdf`);
}

function toggleMetrics(idx) {
  const el = document.getElementById(`metrics-${idx}`);
  if (el) {
    el.classList.toggle("hidden");
  }
}

function scrollToBottom() {
  const container = document.getElementById("chat-messages");
  container.scrollTop = container.scrollHeight;
}

function closeMobileSidebar() {
  const sidebarContainer = document.getElementById("sidebar-container");
  const sidebarBackdrop = document.getElementById("sidebar-backdrop");
  if (sidebarContainer) sidebarContainer.classList.remove("open");
  if (sidebarBackdrop) sidebarBackdrop.classList.add("hidden");
}

// Event Listeners setup
function setupEventListeners() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const newChatBtn = document.getElementById("new-chat-btn");
  const attachBtn = document.getElementById("attach-btn");
  const fileInput = document.getElementById("file-upload-input");
  const micBtn = document.getElementById("mic-btn");
  const mobileMenuBtn = document.getElementById("mobile-menu-btn");
  const closeSidebarBtn = document.getElementById("close-sidebar-btn");
  const sidebarContainer = document.getElementById("sidebar-container");
  const sidebarBackdrop = document.getElementById("sidebar-backdrop");

  form.onsubmit = (e) => {
    e.preventDefault();
    if (isGeneratingResponse) {
      stopGenerating();
      return;
    }
    const text = input.value.trim();
    if (text) {
      submitPrompt(text);
      input.value = "";
    }
  };

  newChatBtn.onclick = () => {
    activeSessionId = generateId();
    activeSessionMessages = [];
    isSessionSavedInHistory = false;
    saveState();
    renderMessages();
    renderHistory();
    closeMobileSidebar();
  };

  if (mobileMenuBtn) {
    mobileMenuBtn.onclick = () => {
      sidebarContainer.classList.add("open");
      sidebarBackdrop.classList.remove("hidden");
    };
  }

  if (closeSidebarBtn) {
    closeSidebarBtn.onclick = closeMobileSidebar;
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.onclick = closeMobileSidebar;
  }

  const refreshDocsBtn = document.getElementById("refresh-docs-btn");
  if (refreshDocsBtn) {
    refreshDocsBtn.onclick = () => {
      loadUploadedDocuments();
    };
  }

  // File Attachment
  attachBtn.onclick = () => {
    fileInput.click();
  };

  fileInput.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const contextVal = document.getElementById("context-select").value;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("context", contextVal);

    const statusEl = document.getElementById("upload-status");
    statusEl.textContent = `Uploading ${file.name}...`;

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok && data.success) {
        statusEl.textContent = `✓ ${data.message}`;

        // Trigger document list refresh to show pending status
        loadUploadedDocuments();

        // Add a live-updating ingestion progress message
        const ingestionMsg = {
          role: "assistant",
          text: `📄 Document '${file.name}' uploaded. Starting ingestion...`,
          isIngestion: true
        };
        activeSessionMessages.push(ingestionMsg);
        const ingestionMsgIdx = activeSessionMessages.length - 1;
        renderMessages();

        // Poll ingestion status
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(`/api/upload/status/${encodeURIComponent(file.name)}`);
            const statusData = await statusRes.json();

            if (!statusData.success) return;

            // Build progress text
            let progressIcon = "⏳";
            let typeInfo = "";

            if (statusData.pdf_type === "scanned") {
              typeInfo = " (🔍 Scanned PDF — OCR may take a few minutes)";
            } else if (statusData.pdf_type === "textual") {
              typeInfo = " (⚡ Text PDF — fast processing)";
            }

            if (statusData.status === "processing") {
              progressIcon = "⚙️";
              ingestionMsg.text = `${progressIcon} [${statusData.progress || 0}%] ${statusData.step}${typeInfo}`;
            } else if (statusData.status === "completed") {
              progressIcon = "✅";
              const timeInfo = statusData.total_time ? ` in ${statusData.total_time}` : "";
              const chunkInfo = statusData.chunks_count ? ` (${statusData.chunks_count} chunks)` : "";
              ingestionMsg.text = `${progressIcon} Document '${file.name}' indexed successfully${timeInfo}${chunkInfo}. Try asking a question about it!`;
              ingestionMsg.isIngestion = false;
              clearInterval(pollInterval);
              statusEl.textContent = "";
              loadUploadedDocuments();
            } else if (statusData.status === "failed") {
              progressIcon = "❌";
              ingestionMsg.text = `${progressIcon} Ingestion failed for '${file.name}': ${statusData.step}`;
              ingestionMsg.isError = true;
              ingestionMsg.isIngestion = false;
              clearInterval(pollInterval);
              statusEl.textContent = "";
              loadUploadedDocuments();
            }

            // Update the message bubble directly
            const textEl = document.getElementById(`msg-text-${ingestionMsgIdx}`);
            if (textEl) {
              textEl.innerHTML = escapeHtml(ingestionMsg.text);
            } else {
              renderMessages();
            }
          } catch (pollErr) {
            console.warn("Ingestion status poll error:", pollErr);
          }
        }, 2000);

      } else {
        statusEl.textContent = "Upload failed.";
        activeSessionMessages.push({
          role: "assistant",
          isError: true,
          text: "Backend connection failed during file upload.",
          errorDetails: data.detail || "Server error"
        });
        renderMessages();
      }
    } catch (err) {
      console.error(err);
      statusEl.textContent = "Upload error.";
      activeSessionMessages.push({
        role: "assistant",
        isError: true,
        text: "Backend connection failed during file upload.",
        errorDetails: String(err)
      });
      renderMessages();
    }
  };

  // Voice Input Speech Recognition
  let isListening = false;
  let recognition = null;

  if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      input.value = transcript;
      toggleMicState(false);
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      toggleMicState(false);
    };

    recognition.onend = () => {
      toggleMicState(false);
    };
  }

  micBtn.onclick = () => {
    if (!recognition) {
      alert("Speech recognition is not supported in this browser. Please type your query.");
      return;
    }

    if (isListening) {
      recognition.stop();
      toggleMicState(false);
    } else {
      try {
        recognition.start();
        toggleMicState(true);
      } catch (err) {
        console.error(err);
      }
    }
  };

  function toggleMicState(active) {
    isListening = active;
    const pulse = document.getElementById("mic-pulse");
    if (active) {
      micBtn.classList.add("bg-red-50", "border-red-400", "text-red-600");
      pulse.classList.remove("hidden");
    } else {
      micBtn.classList.remove("bg-red-50", "border-red-400", "text-red-600");
      pulse.classList.add("hidden");
    }
  }
}

let isGeneratingResponse = false;
let currentAbortController = null;

function stopGenerating() {
  if (currentAbortController) {
    currentAbortController.abort();
    currentAbortController = null;
  }
}

// Enable / Disable input controls and send button state
function setSendingState(isSending) {
  isGeneratingResponse = isSending;
  const sendBtn = document.getElementById("send-btn");
  const chatInput = document.getElementById("chat-input");

  if (sendBtn) {
    sendBtn.disabled = false;
    if (isSending) {
      sendBtn.className = "h-11 shrink-0 rounded-lg bg-red-600 hover:bg-red-700 px-5 text-sm font-semibold text-white transition-colors shadow flex items-center justify-center gap-1.5 focus:ring-2 focus:ring-red-500/30 cursor-pointer";
      sendBtn.innerHTML = `
        <i data-lucide="square" class="h-4 w-4 fill-current"></i>
        <span>Stop</span>
      `;
    } else {
      sendBtn.className = "h-11 shrink-0 rounded-lg bg-navy px-5 text-sm font-semibold text-white hover:bg-navy-light transition-colors shadow flex items-center justify-center gap-1.5 focus:ring-2 focus:ring-navy/30 cursor-pointer";
      sendBtn.innerHTML = `<i data-lucide="send" class="h-4 w-4"></i> Send`;
    }
    initIcons();
  }

  if (chatInput) {
    chatInput.disabled = isSending;
    if (isSending) {
      chatInput.classList.add("opacity-60", "bg-secondary/60", "cursor-not-allowed");
    } else {
      chatInput.classList.remove("opacity-60", "bg-secondary/60", "cursor-not-allowed");
      chatInput.focus();
    }
  }
}

// Smooth Real-Time Response Streaming (Zero Blinking!)
async function submitPrompt(questionText) {
  if (isGeneratingResponse) return;

  currentAbortController = new AbortController();
  setSendingState(true);

  if (!isSessionSavedInHistory) {
    isSessionSavedInHistory = true;
    const sessionTitle = questionText.length > 32 ? questionText.substring(0, 32) + '...' : questionText;
    
    const newSession = {
      id: activeSessionId,
      title: sessionTitle,
      messages: activeSessionMessages
    };
    sessions.unshift(newSession);
    renderHistory();
  }

  // Push user message bubble
  activeSessionMessages.push({
    role: "user",
    text: questionText
  });

  // Create empty assistant message bubble for live streaming
  const assistantMsgIdx = activeSessionMessages.length;
  const assistantMsg = {
    role: "assistant",
    text: "",
    source: null,
    page: null,
    hops: [],
    metrics: null,
    isStreaming: true
  };
  activeSessionMessages.push(assistantMsg);
  
  // Reset loading phrases
  loadingPhrases = [
    "Routing query...",
    "Analyzing context..."
  ];
  currentPhraseIndex = 0;
  
  // Render messages once to create the DOM bubble and start phrase timer
  renderMessages();
  startLoadingPhraseTimer();

  const contextVal = document.getElementById("context-select").value;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      signal: currentAbortController.signal,
      body: JSON.stringify({
        question: questionText,
        context: contextVal,
        top_k: 3
      })
    });

    if (!response.ok) {
      stopLoadingPhraseTimer();
      assistantMsg.isStreaming = false;
      assistantMsg.isError = true;
      assistantMsg.text = "Backend connection failed.";
      assistantMsg.errorDetails = `HTTP Error ${response.status}`;
      renderMessages();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data: ")) continue;

        const jsonStr = trimmed.substring(6);
        try {
          const eventData = JSON.parse(jsonStr);

          if (eventData.type === "route") {
            updateLoadingPhrases(eventData.route, eventData.table);
          } else if (eventData.type === "hop") {
            stopLoadingPhraseTimer();
            if (!assistantMsg.hops) assistantMsg.hops = [];
            assistantMsg.hops.push({
              step: eventData.step,
              action: eventData.action,
              details: eventData.details
            });
            const phraseTextEl = document.getElementById("loading-phrase-text");
            if (phraseTextEl) {
              phraseTextEl.textContent = `🔄 Hop ${eventData.step}: ${eventData.action} (${eventData.details})`;
            }
            updateStreamingBubble(assistantMsgIdx);
          } else if (eventData.type === "metadata") {
            assistantMsg.source = eventData.source;
            assistantMsg.page = eventData.page;
            updateStreamingBubble(assistantMsgIdx);
          } else if (eventData.type === "token") {
            assistantMsg.text += eventData.content;
            // Smooth direct DOM update without clearing innerHTML or re-triggering fade-in
            updateStreamingBubble(assistantMsgIdx);
          } else if (eventData.type === "done") {
            stopLoadingPhraseTimer();
            assistantMsg.metrics = eventData.metrics;
            assistantMsg.isStreaming = false;
            updateStreamingBubble(assistantMsgIdx);
          } else if (eventData.type === "error") {
            stopLoadingPhraseTimer();
            assistantMsg.isStreaming = false;
            assistantMsg.isError = true;
            assistantMsg.text = eventData.message || "Backend execution error.";
            renderMessages();
          }
        } catch (pe) {
          console.warn("Parse error on stream chunk:", pe, line);
        }
      }
    }

    stopLoadingPhraseTimer();
    assistantMsg.isStreaming = false;
    updateStreamingBubble(assistantMsgIdx);

  } catch (err) {
    stopLoadingPhraseTimer();
    if (err.name === "AbortError") {
      console.log("Generation stopped by user.");
      assistantMsg.isStreaming = false;
      if (assistantMsg.text) {
        assistantMsg.text += "\n\n*(Generation stopped by user)*";
      } else {
        assistantMsg.text = "*(Generation stopped by user)*";
      }
      renderMessages();
    } else {
      console.error("API streaming connection error:", err);
      assistantMsg.isStreaming = false;
      assistantMsg.isError = true;
      assistantMsg.text = "Backend connection failed.";
      assistantMsg.errorDetails = "Could not establish stream connection to http://127.0.0.1:8000/api/chat/stream.";
      renderMessages();
    }
  } finally {
    stopLoadingPhraseTimer();
    currentAbortController = null;
    setSendingState(false);
  }

  // Update session stored messages
  const currentSess = sessions.find(s => s.id === activeSessionId);
  if (currentSess) {
    currentSess.messages = activeSessionMessages;
  }
  saveState();
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
