import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, ArrowDownToLine, ArrowUpRight, Bot, Check, CheckCircle2,
  ChevronDown, ChevronRight, CircleHelp, Clock3, Command, Database,
  File, FileText, FileUp, Files, Gauge, History, LayoutDashboard,
  LoaderCircle, LockKeyhole, Menu, MessageSquare, MoreHorizontal,
  PanelLeftClose, Plus, RefreshCw, Search, Send, Settings, ShieldCheck,
  Sparkles, Trash2, UploadCloud, X, AlertCircle, BookOpen, Server,
  HardDrive, Wifi, WifiOff
} from "lucide-react";
import { api } from "./api";

const NAV = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard, group: "WORKSPACE" },
  { id: "chat", label: "RAG Chat", icon: MessageSquare, group: "WORKSPACE" },
  { id: "documents", label: "Documents", icon: Files, group: "WORKSPACE" },
  { id: "approvals", label: "Approvals", icon: ShieldCheck, group: "MANAGEMENT" },
  { id: "history", label: "Conversation history", icon: History, group: "MANAGEMENT" },
  { id: "settings", label: "System settings", icon: Settings, group: "SYSTEM" }
];

const STORAGE_KEY = "enterprise-rag-conversations";
const USER_ID = "local-user";

function readSessions() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
  catch { return []; }
}
function saveSessions(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
}
function formatBytes(bytes = 0) {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes, index = 0;
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index++; }
  return `${value.toFixed(index ? 1 : 0)} ${units[index]}`;
}
function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}
function shortId(value = "") {
  return value.length > 14 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}
function ErrorBanner({ error, onClose }) {
  if (!error) return null;
  return <div className="error-banner"><AlertCircle size={17}/><span>{String(error)}</span><button onClick={onClose} aria-label="Dismiss"><X size={16}/></button></div>;
}
function EmptyState({ icon: Icon = FileText, title, text, action }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={22}/></div><h3>{title}</h3><p>{text}</p>{action}</div>;
}
function StatusPill({ status }) {
  const normalized = String(status || "unknown").toLowerCase();
  const good = ["completed", "approved", "healthy", "connected"].includes(normalized);
  const pending = ["pending", "processing", "pending_approval"].includes(normalized);
  return <span className={`status-pill ${good ? "good" : pending ? "pending" : "neutral"}`}><i/> {normalized.replaceAll("_", " ")}</span>;
}

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [sessions, setSessions] = useState(readSessions);
  const [activeConversation, setActiveConversation] = useState("");
  const [messages, setMessages] = useState([]);
  const [health, setHealth] = useState({ api: "checking", database: "checking" });
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [reviewing, setReviewing] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [reviewer, setReviewer] = useState("Local reviewer");
  const fileInput = useRef(null);
  const chatEnd = useRef(null);

  const notify = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3200);
  };

  const refreshData = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      api.health(), api.databaseHealth(), api.info(), api.documents(), api.approvals()
    ]);
    const [apiResult, dbResult, infoResult, docsResult, approvalsResult] = results;
    setHealth({
      api: apiResult.status === "fulfilled" ? "healthy" : "offline",
      database: dbResult.status === "fulfilled" ? "connected" : "offline"
    });
    if (infoResult.status === "fulfilled") setInfo(infoResult.value);
    if (docsResult.status === "fulfilled") setDocuments(docsResult.value);
    if (approvalsResult.status === "fulfilled") setApprovals(approvalsResult.value);
    const failed = results.find((item) => item.status === "rejected");
    if (failed) setError(failed.reason?.message || "Some backend information could not be loaded.");
    else setError("");
    setLoading(false);
  }, []);

  useEffect(() => { refreshData(); }, [refreshData]);
  useEffect(() => { saveSessions(sessions); }, [sessions]);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, sending]);

  const completedDocs = documents.filter((doc) => doc.status === "completed").length;
  const totalChunks = documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0);
  const filteredDocs = useMemo(() => documents.filter((doc) =>
    `${doc.filename} ${doc.status}`.toLowerCase().includes(search.toLowerCase())
  ), [documents, search]);

  const startNewChat = () => {
    setActiveConversation("");
    setMessages([]);
    setQuery("");
    setPage("chat");
    setError("");
  };

  const loadConversation = async (id) => {
    try {
      setLoading(true);
      const data = await api.history(id);
      setActiveConversation(id);
      setMessages((data.messages || []).map((item) => ({
        role: item.role,
        content: item.content,
        sources: item.sources || [],
        created_at: item.created_at
      })));
      setPage("chat");
      setError("");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const sendMessage = async (event) => {
    event?.preventDefault();
    const text = query.trim();
    if (!text || sending) return;
    const optimistic = { role: "user", content: text, created_at: new Date().toISOString() };
    setMessages((items) => [...items, optimistic]);
    setQuery("");
    setSending(true);
    setError("");
    try {
      const response = await api.chat({
        query: text,
        conversation_id: activeConversation || null,
        user_id: USER_ID
      });
      if (response.conversation_id) {
        setActiveConversation(response.conversation_id);
        setSessions((items) => {
          const exists = items.some((item) => item.id === response.conversation_id);
          const next = exists ? items : [{
            id: response.conversation_id,
            title: text.slice(0, 64),
            created_at: new Date().toISOString()
          }, ...items];
          return next;
        });
      }
      if (response.status === "pending_approval") {
        setMessages((items) => [...items, {
          role: "assistant",
          content: response.message || "This request is awaiting human approval.",
          pendingApproval: true,
          approvalId: response.approval_id,
          sources: []
        }]);
        await refreshData();
      } else {
        setMessages((items) => [...items, {
          role: "assistant",
          content: response.answer || "No retrieved passages were returned.",
          sources: response.citations || [],
          created_at: new Date().toISOString()
        }]);
      }
    } catch (e) {
      setMessages((items) => [...items, {
        role: "assistant",
        content: `The request could not be completed: ${e.message}`,
        error: true
      }]);
    } finally { setSending(false); }
  };

  const uploadFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const result = await api.upload(file);
      notify(`${result.filename} uploaded and indexed.`);
      setSelectedFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await refreshData();
    } catch (e) { setError(e.message); }
    finally { setUploading(false); }
  };

  const deleteDocument = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}" and its indexed vectors?`)) return;
    try {
      await api.deleteDocument(doc.id);
      notify("Document deleted.");
      await refreshData();
    } catch (e) { setError(e.message); }
  };

  const review = async (approval, approved) => {
    setReviewing(approval.id);
    try {
      const result = await api.reviewApproval(approval.id, {
        approved,
        reviewer,
        comment: reviewComment || null
      });
      notify(`Request ${result.status}.`);
      setReviewComment("");
      await refreshData();
    } catch (e) { setError(e.message); }
    finally { setReviewing(""); }
  };

  const pageTitle = NAV.find((item) => item.id === page)?.label || "Overview";

  return (
    <div className={`app-shell ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Command size={20}/></div>
          {sidebarOpen && <div className="brand-copy"><strong>enterprise<span>rag</span></strong><small>LOCAL KNOWLEDGE WORKSPACE</small></div>}
          <button className="icon-button sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} title="Toggle sidebar"><PanelLeftClose size={17}/></button>
        </div>
        <div className="workspace-switch">
          <div className="workspace-avatar">ER</div>
          {sidebarOpen && <div className="workspace-copy"><strong>Personal workspace</strong><small>Local environment</small></div>}
          {sidebarOpen && <ChevronDown size={15} className="muted-icon"/>}
        </div>
        <nav className="side-nav">
          {["WORKSPACE", "MANAGEMENT", "SYSTEM"].map((group) => (
            <div className="nav-group" key={group}>
              {sidebarOpen && <div className="nav-label">{group}</div>}
              {NAV.filter((item) => item.group === group).map((item) => {
                const Icon = item.icon;
                return <button key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => { setPage(item.id); setError(""); }}>
                  <Icon size={18}/>{sidebarOpen && <span>{item.label}</span>}
                  {item.id === "approvals" && approvals.length > 0 && <b className="nav-count">{approvals.length}</b>}
                </button>;
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <div className="local-icon"><LockKeyhole size={16}/></div>
            {sidebarOpen && <div><strong>Local-first mode</strong><small>No hosted AI services</small></div>}
            {sidebarOpen && <span className="live-dot"/>}
          </div>
          <div className="profile-row"><div className="profile-avatar">P</div>{sidebarOpen && <div className="profile-copy"><strong>Local user</strong><small>Administrator</small></div>}{sidebarOpen && <MoreHorizontal size={18} className="muted-icon"/>}</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14}/><strong>{pageTitle}</strong></div>
          <div className="top-actions">
            <div className={`connection-chip ${health.api === "healthy" ? "online" : "offline"}`}><span className="pulse-dot"/>{health.api === "healthy" ? "API connected" : health.api === "checking" ? "Checking API" : "API offline"}</div>
            <button className="icon-button" onClick={refreshData} title="Refresh data"><RefreshCw size={17} className={loading ? "spin" : ""}/></button>
            <button className="avatar-button" title="Local user">P</button>
          </div>
        </header>

        <div className="page-container">
          <ErrorBanner error={error} onClose={() => setError("")}/>
          {page === "dashboard" && <Dashboard documents={documents} approvals={approvals} completedDocs={completedDocs} totalChunks={totalChunks} health={health} info={info} onNavigate={setPage} onRefresh={refreshData} loading={loading}/>}
          {page === "documents" && <Documents documents={filteredDocs} search={search} setSearch={setSearch} onUpload={uploadFile} onDelete={deleteDocument} uploading={uploading} fileInput={fileInput} onRefresh={refreshData}/>}
          {page === "chat" && <Chat messages={messages} query={query} setQuery={setQuery} onSend={sendMessage} sending={sending} onNew={startNewChat} activeConversation={activeConversation} chatEnd={chatEnd} onNavigate={setPage}/>}
          {page === "approvals" && <Approvals approvals={approvals} reviewer={reviewer} setReviewer={setReviewer} comment={reviewComment} setComment={setReviewComment} reviewing={reviewing} onReview={review} onRefresh={refreshData}/>}
          {page === "history" && <HistoryPage sessions={sessions} onOpen={loadConversation} onNew={startNewChat} loading={loading}/>}
          {page === "settings" && <SettingsPage health={health} info={info} onRefresh={refreshData} loading={loading}/>}
        </div>
        <footer className="footer"><span>Enterprise RAG <b>v1.0.0</b></span><span><LockKeyhole size={12}/> Data stays on this machine</span></footer>
      </main>
      {toast && <div className="toast"><CheckCircle2 size={17}/>{toast}</div>}
    </div>
  );
}

function PageHeading({ eyebrow, title, description, action }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function Dashboard({ documents, approvals, completedDocs, totalChunks, health, info, onNavigate, onRefresh, loading }) {
  const recent = documents.slice(0, 5);
  return <>
    <PageHeading eyebrow="WORKSPACE OVERVIEW" title="Good to see you." description="Your local knowledge workspace at a glance."
      action={<button className="button secondary" onClick={onRefresh}><RefreshCw size={15} className={loading ? "spin" : ""}/> Refresh</button>}/>
    <div className="welcome-banner">
      <div className="welcome-glow glow-one"/><div className="welcome-glow glow-two"/>
      <div className="welcome-content"><div className="welcome-kicker"><Sparkles size={14}/> PRIVATE KNOWLEDGE WORKSPACE</div><h2>Your documents.<br/><span>Searchable knowledge.</span></h2><p>Upload local files, retrieve relevant passages, and inspect source citations from one workspace.</p>
        <div className="welcome-actions"><button className="button light" onClick={() => onNavigate("documents")}><UploadCloud size={16}/> Add documents</button><button className="button glass" onClick={() => onNavigate("chat")}><MessageSquare size={16}/> Open RAG chat</button></div>
      </div>
      <div className="welcome-graphic"><div className="orbit orbit-a"/><div className="orbit orbit-b"/><div className="graphic-core"><Database size={34}/></div><div className="float-card float-card-a"><FileText size={16}/><span>Documents</span><b>{documents.length}</b></div><div className="float-card float-card-b"><Activity size={16}/><span>Indexed chunks</span><b>{totalChunks}</b></div></div>
    </div>
    <div className="stats-grid">
      <StatCard icon={Files} label="Total documents" value={documents.length} detail="Stored in local workspace" tone="violet"/>
      <StatCard icon={CheckCircle2} label="Indexed documents" value={completedDocs} detail="Ready for retrieval" tone="green"/>
      <StatCard icon={Database} label="Indexed chunks" value={totalChunks} detail="Available in FAISS" tone="blue"/>
      <StatCard icon={ShieldCheck} label="Pending approvals" value={approvals.length} detail="Awaiting human review" tone="amber"/>
    </div>
    <div className="dashboard-grid">
      <section className="panel recent-panel"><div className="panel-heading"><div><h3>Recent documents</h3><p>Your latest uploaded files</p></div><button className="text-button" onClick={() => onNavigate("documents")}>View all <ArrowUpRight size={14}/></button></div>
        {recent.length ? <div className="table-wrap"><table><thead><tr><th>DOCUMENT</th><th>STATUS</th><th>CHUNKS</th><th>UPLOADED</th></tr></thead><tbody>{recent.map((doc) => <tr key={doc.id}><td><div className="file-cell"><div className="file-icon"><FileText size={16}/></div><div><strong>{doc.filename}</strong><small>{formatBytes(doc.file_size)}</small></div></div></td><td><StatusPill status={doc.status}/></td><td>{doc.chunk_count ?? 0}</td><td className="muted-cell">{formatDate(doc.created_at)}</td></tr>)}</tbody></table></div> : <EmptyState icon={Files} title="No documents yet" text="Upload a PDF, DOCX, or TXT file to begin building your knowledge base." action={<button className="button primary small" onClick={() => onNavigate("documents")}><Plus size={15}/> Upload a document</button>}/>}</section>
      <section className="panel system-panel"><div className="panel-heading"><div><h3>System status</h3><p>Local services and storage</p></div><span className="system-pulse"/></div>
        <SystemRow icon={Server} label="FastAPI service" value={health.api} good={health.api === "healthy"}/>
        <SystemRow icon={Database} label="SQLite database" value={health.database} good={health.database === "connected"}/>
        <SystemRow icon={HardDrive} label="Vector index" value="FAISS · local" good/>
        <SystemRow icon={LockKeyhole} label="Execution mode" value="Offline inference" good/>
        <div className="system-note"><ShieldCheck size={15}/> Documents and indexes are stored locally.</div>
      </section>
    </div>
    <div className="bottom-grid">
      <div className="tip-card"><div className="tip-icon"><BookOpen size={19}/></div><div><strong>How retrieval works</strong><p>Your question is converted into a local feature vector. FAISS finds similar document chunks and returns their source references.</p></div><button className="icon-button" onClick={() => onNavigate("chat")}><ArrowUpRight size={17}/></button></div>
      <div className="tip-card"><div className="tip-icon amber"><ShieldCheck size={19}/></div><div><strong>Human-in-the-loop</strong><p>Requests that trigger the approval policy appear in the approvals queue for review.</p></div><button className="icon-button" onClick={() => onNavigate("approvals")}><ArrowUpRight size={17}/></button></div>
    </div>
  </>;
}
function StatCard({ icon: Icon, label, value, detail, tone }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={18}/></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-detail">{detail}</div></div>;
}
function SystemRow({ icon: Icon, label, value, good }) {
  return <div className="system-row"><div className="system-row-icon"><Icon size={16}/></div><span>{label}</span><strong className={good ? "value-good" : "value-bad"}><i/>{value}</strong></div>;
}

function Documents({ documents, search, setSearch, onUpload, onDelete, uploading, fileInput, onRefresh }) {
  const [dragging, setDragging] = useState(false);
  const handleDrop = (event) => {
    event.preventDefault(); setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) onUpload(file);
  };
  return <>
    <PageHeading eyebrow="KNOWLEDGE BASE" title="Documents" description="Manage the files that power your local retrieval workspace."
      action={<button className="button secondary" onClick={onRefresh}><RefreshCw size={15}/> Refresh list</button>}/>
    <div className={`upload-zone ${dragging ? "dragging" : ""}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}>
      <input ref={fileInput} type="file" accept=".pdf,.docx,.txt" hidden onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}/>
      <div className="upload-symbol"><UploadCloud size={25}/></div><h3>{uploading ? "Uploading and indexing…" : "Add documents to your knowledge base"}</h3><p>Drag and drop a file here, or browse your computer.</p>
      <button className="button primary" disabled={uploading} onClick={() => fileInput.current?.click()}>{uploading ? <LoaderCircle size={16} className="spin"/> : <FileUp size={16}/>} {uploading ? "Processing file" : "Choose a file"}</button>
      <div className="upload-meta"><span>PDF</span><span>DOCX</span><span>TXT</span><i/>Maximum file size: 20 MB</div>
    </div>
    <section className="panel documents-panel"><div className="panel-heading docs-heading"><div><h3>All documents <span className="count-badge">{documents.length}</span></h3><p>Files currently registered in your local database</p></div><div className="search-box"><Search size={16}/><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search documents…"/></div></div>
      {documents.length ? <div className="table-wrap"><table><thead><tr><th>DOCUMENT</th><th>STATUS</th><th>CHUNKS</th><th>SIZE</th><th>UPLOADED</th><th/></tr></thead><tbody>{documents.map((doc) => <tr key={doc.id}><td><div className="file-cell"><div className="file-icon"><FileText size={16}/></div><div><strong>{doc.filename}</strong><small title={doc.id}>{shortId(doc.id)}</small></div></div></td><td><StatusPill status={doc.status}/></td><td>{doc.chunk_count ?? 0}</td><td>{formatBytes(doc.file_size)}</td><td className="muted-cell">{formatDate(doc.created_at)}</td><td><button className="icon-button danger-hover" title="Delete document" onClick={() => onDelete(doc)}><Trash2 size={16}/></button></td></tr>)}</tbody></table></div> : <EmptyState icon={FileText} title="No matching documents" text="Upload your first document or adjust your search."/>}
    </section>
    <div className="notice-line"><LockKeyhole size={14}/> Files are saved to the backend's local upload directory and indexed in the local FAISS store.</div>
  </>;
}

function Chat({ messages, query, setQuery, onSend, sending, onNew, activeConversation, chatEnd, onNavigate }) {
  const suggestions = ["What documents have been indexed?", "Summarize the key information in my files.", "Find information about a specific topic."];
  return <>
    <PageHeading eyebrow="RETRIEVAL ASSISTANT" title="RAG Chat" description="Ask questions and inspect the document passages retrieved by your local index."
      action={<button className="button secondary" onClick={onNew}><Plus size={16}/> New conversation</button>}/>
    <div className="chat-layout">
      <section className="chat-panel">
        <div className="chat-topline"><div className="chat-agent"><div className="agent-avatar"><Bot size={18}/></div><div><strong>Local retrieval assistant</strong><small><span className="live-dot"/> FAISS retrieval · No generative LLM</small></div></div><span className="chat-mode"><LockKeyhole size={12}/> PRIVATE</span></div>
        <div className="chat-messages">
          {messages.length === 0 ? <div className="chat-welcome"><div className="chat-welcome-icon"><Sparkles size={23}/></div><h2>Ask your documents.</h2><p>I'll search your indexed files and return the most relevant passages with source citations.</p><div className="suggestion-list">{suggestions.map((s) => <button key={s} onClick={() => setQuery(s)}>{s}<ArrowUpRight size={14}/></button>)}</div><div className="chat-empty-note"><CircleHelp size={14}/> Responses are retrieved excerpts, not AI-generated summaries.</div></div> : messages.map((message, index) => <MessageBubble key={`${index}-${message.created_at || ""}`} message={message}/>)}
          {sending && <div className="message-row assistant"><div className="message-avatar"><Bot size={16}/></div><div className="message-content"><div className="typing"><i/><i/><i/></div><span className="typing-label">Searching local index…</span></div></div>}
          <div ref={chatEnd}/>
        </div>
        <form className="chat-composer" onSubmit={onSend}><textarea value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(e); } }} placeholder="Ask a question about your documents…" rows={2}/>
          <div className="composer-bottom"><span><kbd>Enter</kbd> to send · <kbd>Shift + Enter</kbd> for new line</span><button className="send-button" type="submit" disabled={!query.trim() || sending}><Send size={16}/> Send</button></div></form>
      </section>
      <aside className="chat-side"><div className="side-info-card"><div className="side-info-icon"><Database size={18}/></div><h3>Retrieval context</h3><p>Answers are assembled from matching document chunks returned by FAISS.</p><div className="side-info-stat"><span>Conversation</span><strong>{activeConversation ? shortId(activeConversation) : "New session"}</strong></div><div className="side-info-stat"><span>Messages</span><strong>{messages.length}</strong></div></div>
        <div className="side-info-card"><div className="side-info-icon blue"><ShieldCheck size={18}/></div><h3>Source transparency</h3><p>Each response can include the source filename, chunk number, and similarity score.</p><button className="text-button" onClick={() => onNavigate("documents")}>Manage documents <ArrowUpRight size={14}/></button></div>
        <div className="side-warning"><AlertCircle size={15}/><span>Feature hashing provides lightweight lexical matching. It is not equivalent to neural semantic embeddings.</span></div>
      </aside>
    </div>
  </>;
}
function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return <div className={`message-row ${isUser ? "user" : "assistant"}`}>
    {!isUser && <div className="message-avatar"><Bot size={16}/></div>}
    <div className="message-content"><div className="message-meta">{isUser ? "You" : "Retrieved response"} <span>{message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}</span></div>
      <div className={`message-bubble ${message.error ? "message-error" : ""}`}>{message.content}</div>
      {message.pendingApproval && <div className="pending-callout"><Clock3 size={14}/> Waiting for human approval</div>}
      {message.sources?.length > 0 && <div className="sources-block"><div className="sources-title"><BookOpen size={14}/> Retrieved sources <span>{message.sources.length}</span></div>{message.sources.map((source, i) => <div className="source-item" key={`${source.chunk_id || i}-${i}`}><div className="source-file"><FileText size={14}/><strong>{source.filename || "Source document"}</strong></div><div className="source-meta"><span>Chunk {source.chunk_index ?? "—"}</span>{source.score != null && <span>Similarity {(source.score * 100).toFixed(1)}%</span>}</div></div>)}</div>}
    </div>
    {isUser && <div className="user-message-avatar">P</div>}
  </div>;
}

function Approvals({ approvals, reviewer, setReviewer, comment, setComment, reviewing, onReview, onRefresh }) {
  return <>
    <PageHeading eyebrow="GOVERNANCE" title="Approvals" description="Review requests paused by the human-in-the-loop policy."
      action={<button className="button secondary" onClick={onRefresh}><RefreshCw size={15}/> Refresh queue</button>}/>
    <div className="approval-summary"><div className="approval-summary-icon"><ShieldCheck size={21}/></div><div><strong>{approvals.length} pending {approvals.length === 1 ? "request" : "requests"}</strong><p>Review each request before allowing the workflow to continue.</p></div></div>
    {approvals.length ? <div className="approval-list">{approvals.map((item) => <div className="panel approval-card" key={item.id}><div className="approval-card-head"><div className="approval-card-icon"><LockKeyhole size={18}/></div><div className="approval-card-title"><strong>{item.action || "Human review required"}</strong><small>Request {shortId(item.id)} · {formatDate(item.created_at)}</small></div><StatusPill status="pending"/></div>
      <div className="approval-detail"><span>Request context</span><p>{item.details?.question || item.details?.message || "This workflow requires human review."}</p></div>
      {item.details?.sources?.length > 0 && <div className="approval-sources">{item.details.sources.map((source, i) => <span key={i}><FileText size={13}/>{source.filename || "Source"}</span>)}</div>}
      <div className="review-fields"><label>Reviewer name<input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label><label>Review comment<input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional context for this decision"/></label></div>
      <div className="approval-actions"><button className="button danger-outline" disabled={reviewing === item.id} onClick={() => onReview(item, false)}><X size={15}/> Reject</button><button className="button primary" disabled={reviewing === item.id} onClick={() => onReview(item, true)}>{reviewing === item.id ? <LoaderCircle size={15} className="spin"/> : <Check size={15}/>} Approve and continue</button></div>
    </div>)}</div> : <section className="panel"><EmptyState icon={ShieldCheck} title="No pending approvals" text="Requests that require human review will appear here."/></section>}
  </>;
}

function HistoryPage({ sessions, onOpen, onNew, loading }) {
  return <>
    <PageHeading eyebrow="YOUR WORK" title="Conversation history" description="Reopen conversations saved in this browser."
      action={<button className="button primary" onClick={onNew}><Plus size={16}/> New conversation</button>}/>
    <section className="panel history-panel"><div className="panel-heading"><div><h3>Recent conversations</h3><p>Conversation references are stored locally in this browser.</p></div><span className="count-badge">{sessions.length}</span></div>
      {sessions.length ? <div className="history-list">{sessions.map((session) => <button className="history-item" key={session.id} onClick={() => onOpen(session.id)} disabled={loading}><div className="history-icon"><MessageSquare size={17}/></div><div className="history-copy"><strong>{session.title || "Untitled conversation"}</strong><small>{formatDate(session.created_at)} · {shortId(session.id)}</small></div><ChevronRight size={17}/></button>)}</div> : <EmptyState icon={History} title="No saved conversations" text="Start a RAG chat. Your conversation will appear here automatically."/>}
    </section>
    <div className="notice-line"><AlertCircle size={14}/> This list is browser-local. Clearing browser storage removes these shortcuts, not the conversations in SQLite.</div>
  </>;
}

function SettingsPage({ health, info, onRefresh, loading }) {
  return <>
    <PageHeading eyebrow="CONFIGURATION" title="System settings" description="Inspect the local runtime and application configuration."
      action={<button className="button secondary" onClick={onRefresh}><RefreshCw size={15} className={loading ? "spin" : ""}/> Refresh status</button>}/>
    <div className="settings-grid">
      <section className="panel settings-panel"><div className="panel-heading"><div><h3>Runtime services</h3><p>Connectivity checks from the frontend</p></div></div>
        <SystemRow icon={Server} label="FastAPI" value={health.api} good={health.api === "healthy"}/>
        <SystemRow icon={Database} label="SQLite" value={health.database} good={health.database === "connected"}/>
        <SystemRow icon={Database} label="FAISS" value="Local vector index" good/>
        <SystemRow icon={LockKeyhole} label="AI inference" value="Not configured / not used" good/>
      </section>
      <section className="panel settings-panel"><div className="panel-heading"><div><h3>Application information</h3><p>Values reported by the backend</p></div></div>
        <InfoRow label="Application" value={info?.name || "Enterprise RAG"}/>
        <InfoRow label="Version" value={info?.version || "1.0.0"}/>
        <InfoRow label="Environment" value={info?.environment || "development"}/>
        <InfoRow label="API prefix" value="/api/v1"/>
        <InfoRow label="Retrieval method" value="Local feature hashing + FAISS"/>
        <InfoRow label="Storage" value="SQLite + local filesystem"/>
      </section>
    </div>
    <div className="settings-note"><LockKeyhole size={17}/><div><strong>Local-first by design</strong><p>This frontend uses a Vite development proxy to communicate with FastAPI at 127.0.0.1:8000. No hosted backend or AI service is configured.</p></div></div>
  </>;
}
function InfoRow({ label, value }) {
  return <div className="info-row"><span>{label}</span><strong>{value}</strong></div>;
}
