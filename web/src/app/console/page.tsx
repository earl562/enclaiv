"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  PlusCircle,
  PaperPlaneTilt,
  CaretLeft,
  X,
} from "@phosphor-icons/react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Message = { role: "user" | "assistant"; content: string };

type Session = {
  id: string;
  agent_name: string;
  task: string;
  model: string;
  status: string;
  created_at: string;
  session_token?: string;
  messages: Message[];
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return "just now";
  if (diff < 3600) {
    const m = Math.floor(diff / 60);
    return `${m} minute${m !== 1 ? "s" : ""} ago`;
  }
  if (diff < 86400) {
    const h = Math.floor(diff / 3600);
    return `${h} hour${h !== 1 ? "s" : ""} ago`;
  }
  if (diff < 172800) return "yesterday";
  const d = Math.floor(diff / 86400);
  return `${d} days ago`;
}

async function readSSEStream(
  response: Response,
  onChunk: (text: string) => void
): Promise<void> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (!data || data === "[DONE]") continue;

      try {
        const parsed = JSON.parse(data);
        // Error payload from control plane or upstream API — surface it
        if (parsed.error !== undefined) {
          const msg =
            typeof parsed.error === "string"
              ? parsed.error
              : (parsed.error?.message ?? JSON.stringify(parsed.error));
          throw new Error(msg);
        }
        // Google normalized format
        if (parsed.type === "text_delta" && typeof parsed.text === "string") {
          onChunk(parsed.text);
        }
        // Anthropic raw pass-through format
        else if (
          parsed.type === "content_block_delta" &&
          parsed.delta?.type === "text_delta" &&
          typeof parsed.delta?.text === "string"
        ) {
          onChunk(parsed.delta.text);
        }
      } catch (e) {
        if (e instanceof SyntaxError) continue; // malformed JSON — skip
        throw e; // re-throw error events
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="block w-1.5 h-1.5 rounded-full bg-[#636366]"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.2,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <motion.div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
    >
      <div
        className={[
          "px-4 py-3 rounded-lg text-sm leading-relaxed whitespace-pre-wrap font-sans",
          isUser
            ? "bg-[#111111] text-white max-w-[70%]"
            : "bg-white border border-[#EAEAEA] text-[#1C1C1E] max-w-[80%]",
        ].join(" ")}
        style={{ wordBreak: "break-word" }}
      >
        {message.content}
      </div>
    </motion.div>
  );
}

function SessionItem({
  session,
  isActive,
  onClick,
}: {
  session: Session;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 transition-colors duration-150 relative group"
      style={{
        background: isActive ? "#1a1a1a" : "transparent",
      }}
    >
      {isActive && (
        <span
          className="absolute left-0 top-0 bottom-0 w-[3px] rounded-r-full"
          style={{ background: "#FF3B30" }}
        />
      )}
      <div className="flex flex-col gap-0.5 pl-1">
        <span
          className="text-xs font-semibold tracking-wide truncate"
          style={{ color: isActive ? "#FFFFFF" : "#D1D1D6" }}
        >
          {session.agent_name}
        </span>
        <span
          className="text-xs truncate leading-snug"
          style={{ color: isActive ? "#A1A1AA" : "#636366" }}
        >
          {session.task}
        </span>
        <span
          className="text-[10px] mt-0.5 font-mono"
          style={{ color: isActive ? "#52525B" : "#3F3F46" }}
        >
          {relativeTime(session.created_at)}
        </span>
      </div>
    </button>
  );
}

function NewSessionModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (session: Session) => void;
}) {
  const [agentName, setAgentName] = useState("");
  const [task, setTask] = useState("");
  const [model, setModel] = useState("gemini-2.5-flash");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentName.trim() || !task.trim()) {
      setError("Agent name and task are required.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_name: agentName.trim(),
          task: task.trim(),
          model,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail ?? "Failed to create session.");
        setLoading(false);
        return;
      }

      const session: Session = await res.json();
      onCreate(session);
    } catch {
      setError("Network error. Check that the control plane is running.");
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />

      {/* Modal */}
      <motion.div
        className="relative z-10 bg-white rounded-xl border border-[#EAEAEA] shadow-[0_8px_32px_rgba(0,0,0,0.12)] w-full max-w-md mx-4 font-sans"
        initial={{ opacity: 0, scale: 0.97, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97, y: 8 }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#EAEAEA]">
          <h2 className="text-sm font-semibold text-[#1C1C1E] tracking-tight">
            New session
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-[#636366] hover:text-[#1C1C1E] hover:bg-[#F2F2F7] transition-colors duration-150"
          >
            <X size={16} weight="bold" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#636366] uppercase tracking-wider">
              Agent name
            </label>
            <input
              ref={firstInputRef}
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="research-agent"
              className="w-full px-3 py-2.5 text-sm text-[#1C1C1E] bg-[#F9F9F8] border border-[#D1D1D6] rounded-lg outline-none focus:border-[#1C1C1E] transition-colors duration-150 font-sans placeholder:text-[#A1A1AA]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#636366] uppercase tracking-wider">
              Task
            </label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Summarize the latest arXiv papers on diffusion models..."
              rows={3}
              className="w-full px-3 py-2.5 text-sm text-[#1C1C1E] bg-[#F9F9F8] border border-[#D1D1D6] rounded-lg outline-none focus:border-[#1C1C1E] transition-colors duration-150 font-sans placeholder:text-[#A1A1AA] resize-none leading-relaxed"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#636366] uppercase tracking-wider">
              Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2.5 text-sm text-[#1C1C1E] bg-[#F9F9F8] border border-[#D1D1D6] rounded-lg outline-none focus:border-[#1C1C1E] transition-colors duration-150 font-sans appearance-none cursor-pointer"
            >
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
            </select>
          </div>

          {error && (
            <p className="text-xs text-[#FF3B30] leading-snug">{error}</p>
          )}

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-[#636366] hover:text-[#1C1C1E] transition-colors duration-150 font-sans"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-[#111111] rounded-md hover:bg-[#333333] active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed font-sans"
            >
              {loading ? "Creating..." : "Create session"}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main console page
// ---------------------------------------------------------------------------

export default function ConsolePage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [sessionTokens, setSessionTokens] = useState<Record<string, string>>({});
  const [showNewModal, setShowNewModal] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingSession, setLoadingSession] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null;

  // ---------------------------------------------------------------------------
  // Auto-scroll
  // ---------------------------------------------------------------------------

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // ---------------------------------------------------------------------------
  // Load sessions on mount
  // ---------------------------------------------------------------------------

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) return;
      const data: Session[] = await res.json();
      setSessions(data);
    } catch {
      // silently fail — control plane may not be running
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // ---------------------------------------------------------------------------
  // Select session
  // ---------------------------------------------------------------------------

  const selectSession = useCallback(
    async (sessionId: string) => {
      if (sessionId === activeSessionId) return;
      setActiveSessionId(sessionId);
      setMessages([]);
      setStreamingText("");

      const token = sessionTokens[sessionId];
      if (!token) {
        // Session was not created in this browser session — messages not available
        const session = sessions.find((s) => s.id === sessionId);
        if (session) setMessages(session.messages as Message[]);
        return;
      }

      setLoadingSession(true);
      try {
        const res = await fetch(`/api/sessions/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data: Session = await res.json();
          setMessages(data.messages as Message[]);
        }
      } catch {
        // fall back to cached messages from sessions list
        const session = sessions.find((s) => s.id === sessionId);
        if (session) setMessages(session.messages as Message[]);
      } finally {
        setLoadingSession(false);
      }
    },
    [activeSessionId, sessionTokens, sessions]
  );

  // ---------------------------------------------------------------------------
  // Create session
  // ---------------------------------------------------------------------------

  const handleSessionCreated = useCallback(
    (session: Session) => {
      setSessions((prev) => [session, ...prev]);
      if (session.session_token) {
        setSessionTokens((prev) => ({
          ...prev,
          [session.id]: session.session_token!,
        }));
      }
      setShowNewModal(false);
      setActiveSessionId(session.id);
      setMessages([]);
      setStreamingText("");
    },
    []
  );

  // ---------------------------------------------------------------------------
  // Auto-resize textarea
  // ---------------------------------------------------------------------------

  const handleTextareaInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  // ---------------------------------------------------------------------------
  // Send message
  // ---------------------------------------------------------------------------

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isStreaming || !activeSessionId) return;

    const token = sessionTokens[activeSessionId];
    const session = sessions.find((s) => s.id === activeSessionId);
    if (!session) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    const allMessages: Message[] = [...messages, userMessage];

    setMessages(allMessages);
    setInput("");
    setStreamingText("");
    setIsStreaming(true);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    let accumulated = "";

    try {
      const res = await fetch(`/api/sessions/${activeSessionId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: allMessages,
          model: session.model,
          sessionToken: token,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        const errorMessage: Message = {
          role: "assistant",
          content: `Error: ${errText || res.statusText}`,
        };
        setMessages((prev) => [...prev, errorMessage]);
        setIsStreaming(false);
        return;
      }

      await readSSEStream(res, (chunk) => {
        accumulated += chunk;
        setStreamingText(accumulated);
      });
    } catch (err) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Connection error: ${err instanceof Error ? err.message : "Unknown error"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsStreaming(false);
      setStreamingText("");
      return;
    }

    // Commit the streamed response
    const assistantMessage: Message = {
      role: "assistant",
      content: accumulated || "[No response received. Check that GOOGLE_API_KEY / ANTHROPIC_API_KEY are set on the control plane.]",
    };
    const finalMessages: Message[] = [...allMessages, assistantMessage];
    setMessages(finalMessages);
    setStreamingText("");
    setIsStreaming(false);

    // Persist both messages to the control plane
    if (token) {
      try {
        await fetch(`/api/sessions/${activeSessionId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [userMessage, assistantMessage],
            sessionToken: token,
          }),
        });
      } catch {
        // non-fatal — messages are in local state regardless
      }
    }
  }, [input, isStreaming, activeSessionId, sessionTokens, sessions, messages]);

  // ---------------------------------------------------------------------------
  // Keyboard shortcut: Cmd/Ctrl + Enter to send
  // ---------------------------------------------------------------------------

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div
      className="flex h-[100dvh] overflow-hidden font-sans"
      style={{ background: "#0D0D0D" }}
    >
      {/* ------------------------------------------------------------------ */}
      {/* Sidebar                                                              */}
      {/* ------------------------------------------------------------------ */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex-shrink-0 flex flex-col overflow-hidden"
            style={{
              background: "#111111",
              borderRight: "1px solid #1F1F1F",
            }}
          >
            {/* Sidebar header */}
            <div
              className="flex items-center justify-between px-4 py-4 flex-shrink-0"
              style={{ borderBottom: "1px solid #1F1F1F" }}
            >
              <span className="text-xs font-semibold tracking-widest uppercase text-[#636366]">
                Sessions
              </span>
              <button
                onClick={() => setShowNewModal(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium text-[#D1D1D6] hover:text-white rounded-md hover:bg-[#1F1F1F] transition-colors duration-150"
              >
                <PlusCircle size={14} weight="bold" />
                New
              </button>
            </div>

            {/* Sessions list */}
            <div className="flex-1 overflow-y-auto">
              {sessions.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <p className="text-xs text-[#3F3F46]">No sessions yet.</p>
                  <button
                    onClick={() => setShowNewModal(true)}
                    className="mt-3 text-xs text-[#636366] hover:text-[#D1D1D6] underline underline-offset-2 transition-colors duration-150"
                  >
                    Create one
                  </button>
                </div>
              ) : (
                <div className="py-1">
                  {sessions.map((s) => (
                    <SessionItem
                      key={s.id}
                      session={s}
                      isActive={s.id === activeSessionId}
                      onClick={() => selectSession(s.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Sidebar footer */}
            <div
              className="px-4 py-3 flex-shrink-0"
              style={{ borderTop: "1px solid #1F1F1F" }}
            >
              <p className="text-[10px] text-[#3F3F46] font-mono">
                enclaiv console
              </p>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* ------------------------------------------------------------------ */}
      {/* Main area                                                            */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex flex-col min-w-0" style={{ background: "#F9F9F8" }}>

        {/* Top bar */}
        <div
          className="flex items-center gap-3 px-4 py-3 flex-shrink-0"
          style={{
            background: "#FFFFFF",
            borderBottom: "1px solid #EAEAEA",
          }}
        >
          {/* Sidebar toggle */}
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="p-1.5 rounded-md text-[#636366] hover:text-[#1C1C1E] hover:bg-[#F2F2F7] transition-colors duration-150 flex-shrink-0"
          >
            <CaretLeft
              size={14}
              weight="bold"
              style={{
                transform: sidebarOpen ? "rotate(0deg)" : "rotate(180deg)",
                transition: "transform 0.2s ease",
              }}
            />
          </button>

          {activeSession ? (
            <>
              <span className="text-sm font-semibold text-[#1C1C1E] truncate">
                {activeSession.agent_name}
              </span>
              <span
                className="text-[10px] font-mono px-2 py-0.5 rounded"
                style={{
                  background: "#F2F2F7",
                  color: "#636366",
                  border: "1px solid #D1D1D6",
                  flexShrink: 0,
                }}
              >
                {activeSession.model}
              </span>
              <span
                className="text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider flex-shrink-0"
                style={{
                  background:
                    activeSession.status === "active"
                      ? "#EDF3EC"
                      : activeSession.status === "failed"
                      ? "#FDEBEC"
                      : "#F2F2F7",
                  color:
                    activeSession.status === "active"
                      ? "#346538"
                      : activeSession.status === "failed"
                      ? "#9F2F2D"
                      : "#636366",
                }}
              >
                {activeSession.status}
              </span>
              <span
                className="text-xs text-[#636366] truncate ml-auto hidden sm:block"
                title={activeSession.task}
              >
                {activeSession.task.length > 60
                  ? activeSession.task.slice(0, 60) + "…"
                  : activeSession.task}
              </span>
            </>
          ) : (
            <span className="text-sm text-[#636366]">No session selected</span>
          )}
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          {!activeSession ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ background: "#F2F2F7", border: "1px solid #EAEAEA" }}
              >
                <PaperPlaneTilt size={22} weight="light" color="#636366" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-[#1C1C1E]">
                  Select a session or create a new one
                </p>
                <p className="text-xs text-[#636366] mt-1">
                  Agent conversations will appear here.
                </p>
              </div>
              <button
                onClick={() => setShowNewModal(true)}
                className="mt-2 flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#111111] rounded-md hover:bg-[#333333] active:scale-[0.98] transition-all duration-150"
              >
                <PlusCircle size={15} weight="bold" />
                New session
              </button>
            </div>
          ) : loadingSession ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-sm text-[#636366]">
                <motion.span
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.4, repeat: Infinity }}
                >
                  Loading messages...
                </motion.span>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto w-full">
              {messages.length === 0 && !streamingText && !isStreaming ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                  <p className="text-sm text-[#636366] text-center">
                    No messages yet. Send one below to start.
                  </p>
                </div>
              ) : (
                <>
                  <AnimatePresence initial={false}>
                    {messages.map((msg, i) => (
                      <MessageBubble key={i} message={msg} />
                    ))}
                  </AnimatePresence>

                  {/* Streaming message */}
                  <AnimatePresence>
                    {isStreaming && (
                      <motion.div
                        className="flex justify-start mb-3"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      >
                        <div
                          className="text-sm leading-relaxed whitespace-pre-wrap font-sans max-w-[80%] rounded-lg"
                          style={{
                            background: "#FFFFFF",
                            border: "1px solid #EAEAEA",
                            color: "#1C1C1E",
                            wordBreak: "break-word",
                          }}
                        >
                          {streamingText ? (
                            <div className="px-4 py-3">{streamingText}</div>
                          ) : (
                            <TypingIndicator />
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input bar */}
        {activeSession && (
          <div
            className="flex-shrink-0 px-4 py-4 md:px-8"
            style={{
              background: "#FFFFFF",
              borderTop: "1px solid #EAEAEA",
            }}
          >
            <div className="max-w-3xl mx-auto w-full">
              <div
                className="flex items-end gap-3 rounded-xl px-4 py-3"
                style={{
                  background: "#F9F9F8",
                  border: "1px solid #D1D1D6",
                }}
              >
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onInput={handleTextareaInput}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message… (Cmd+Enter to send)"
                  rows={1}
                  disabled={isStreaming}
                  className="flex-1 bg-transparent text-sm text-[#1C1C1E] placeholder:text-[#A1A1AA] resize-none outline-none font-sans leading-relaxed disabled:opacity-50"
                  style={{ minHeight: "24px", maxHeight: "160px" }}
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || isStreaming}
                  className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-md bg-[#111111] text-white hover:bg-[#333333] active:scale-[0.98] transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <PaperPlaneTilt size={15} weight="fill" />
                </button>
              </div>
              <p className="text-[10px] text-[#A1A1AA] mt-2 text-right font-mono">
                Cmd+Enter to send
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* New session modal                                                    */}
      {/* ------------------------------------------------------------------ */}
      <AnimatePresence>
        {showNewModal && (
          <NewSessionModal
            onClose={() => setShowNewModal(false)}
            onCreate={handleSessionCreated}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
