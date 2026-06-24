"use client";

import { useState, useEffect, useRef, Suspense, createContext, useContext } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Send, Plus, Database, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Tracks nesting depth so nested bullets look clearly subordinate to top-level ones
const ListDepthContext = createContext(0);

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="font-lora text-base text-body font-semibold mt-4 mb-2 first:mt-0">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xs font-semibold text-montney uppercase tracking-widest mt-5 mb-3 first:mt-0 pb-2 border-b border-grid">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold text-body mt-3 mb-1.5 first:mt-0">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="text-sm text-body leading-relaxed mb-3 last:mb-0">
            {children}
          </p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-body">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="italic text-muted">{children}</em>
        ),
        ul: function UlComponent({ children }) {
          const depth = useContext(ListDepthContext);
          return (
            <ListDepthContext.Provider value={depth + 1}>
              <ul className={`space-y-2 mb-3 last:mb-0 ${depth > 0 ? "mt-1.5 ml-5" : ""}`}>
                {children}
              </ul>
            </ListDepthContext.Provider>
          );
        },
        ol: function OlComponent({ children }) {
          const depth = useContext(ListDepthContext);
          return (
            <ListDepthContext.Provider value={depth + 1}>
              <ol className={`space-y-2 mb-3 last:mb-0 ${depth > 0 ? "mt-1.5 ml-5" : ""}`}>
                {children}
              </ol>
            </ListDepthContext.Provider>
          );
        },
        li: function LiComponent({ children }) {
          const depth = useContext(ListDepthContext);
          const isNested = depth > 1;
          return (
            <li className="flex items-start gap-2.5 text-sm text-body leading-relaxed">
              {isNested ? (
                <span className="w-3.5 shrink-0 mt-[7px] flex justify-center">
                  <span className="block w-2.5 h-px bg-muted/50" />
                </span>
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-montney mt-[7px] shrink-0" />
              )}
              <span className={isNested ? "text-muted" : ""}>{children}</span>
            </li>
          );
        },
        hr: () => <hr className="border-grid my-4" />,
        code: ({ children }) => (
          <code className="text-xs font-mono bg-log-cream text-montney px-1.5 py-0.5 rounded-sm">
            {children}
          </code>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-montney pl-4 text-sm text-muted italic my-3">
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

type Message = {
  role: "user" | "assistant";
  content: string;
  sources: string[];
  toolsUsed?: string[];
};

type Session = {
  id: string;
  title: string;
  createdAt: number;
};

const SUGGESTED = [
  "How many active Montney wells does Tourmaline have?",
  "What are the noise control requirements near residences?",
  "What waste management procedures apply to drilling?",
  "What flaring restrictions apply to Montney operations?",
];

function normalizeDirectiveName(raw: string): string {
  // "directive-056" → "Directive 056", "Directive056" → "Directive 056"
  return raw
    .replace(/^directive[-_]?/i, "Directive ")
    .replace(/^(Directive)(\d)/, "$1 $2")
    .trim();
}

function groupSources(sources: string[]): { displayName: string; pages: string[] }[] {
  const map: Record<string, string[]> = {};
  for (const src of sources) {
    const [name, pageStr] = src.split(", Page ");
    const display = normalizeDirectiveName(name);
    if (!map[display]) map[display] = [];
    if (pageStr && !map[display].includes(pageStr)) map[display].push(pageStr);
  }
  return Object.entries(map).map(([displayName, pages]) => ({ displayName, pages }));
}

function ChatInterface() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const apiUrl = "/api";

  // Load sessions from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("basiniq_sessions");
      if (stored) setSessions(JSON.parse(stored));
    } catch {}
  }, []);

  // Pre-fill from URL query param
  useEffect(() => {
    const q = searchParams.get("q");
    if (q) setInput(q);
  }, [searchParams]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    if (sessionId && messages.length > 0) {
      try {
        localStorage.setItem(`basiniq_msgs_${sessionId}`, JSON.stringify(messages));
      } catch {}
    }
  }, [messages, sessionId]);

  const saveSession = (id: string, firstQuestion: string) => {
    const title =
      firstQuestion.length > 52
        ? firstQuestion.slice(0, 52) + "…"
        : firstQuestion;
    const entry: Session = { id, title, createdAt: Date.now() };
    setSessions((prev) => {
      const updated = [entry, ...prev.filter((s) => s.id !== id)].slice(0, 12);
      localStorage.setItem("basiniq_sessions", JSON.stringify(updated));
      return updated;
    });
  };

  const handleSubmit = async (overrideInput?: string) => {
    const question = (overrideInput ?? input).trim();
    if (!question || loading) return;

    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    setMessages((prev) => [
      ...prev,
      { role: "user", content: question, sources: [] },
    ]);
    setLoading(true);
    setStreamingContent(null);

    try {
      const body: Record<string, string> = { question };
      if (sessionId) body.session_id = sessionId;

      const res = await fetch(`${apiUrl}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";
      let finalSources: string[] = [];
      let finalToolsUsed: string[] = [];
      let finalSessionId = sessionId;

      setLoading(false);
      setStreamingContent("");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        for (const line of raw.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (!payload) continue;
          try {
            const evt = JSON.parse(payload);
            if (evt.type === "token") {
              fullText += evt.text;
              setStreamingContent(fullText);
            } else if (evt.type === "done") {
              finalSources = evt.sources ?? [];
              finalToolsUsed = evt.tools_used ?? [];
              finalSessionId = evt.session_id ?? sessionId;
              if (!sessionId && finalSessionId) {
                setSessionId(finalSessionId);
                saveSession(finalSessionId, question);
              }
            } else if (evt.type === "error") {
              fullText = `Error: ${evt.message ?? "Unknown error"}`;
            }
          } catch {}
        }
      }

      setStreamingContent(null);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: fullText || "Unable to process query.",
          sources: finalSources,
          toolsUsed: finalToolsUsed,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Unable to reach the BasinIQ API. Make sure the backend is running.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
      setStreamingContent(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setInput("");
  };

  // Sources from the most recent assistant message
  const latestSources =
    [...messages].reverse().find((m) => m.role === "assistant")?.sources ?? [];

  return (
    <div className="flex h-screen overflow-hidden bg-log-cream">

      {/* ── SIDEBAR ── */}
      <aside className="hidden md:flex flex-col w-56 shrink-0 bg-log-dark border-r border-sidebar-text/10">
        {/* Wordmark */}
        <div className="px-5 py-5 border-b border-sidebar-text/10">
          <Link
            href="/"
            className="font-lora text-xl text-sidebar-text leading-none"
          >
            BASIN<span className="text-marker">IQ</span>
          </Link>
        </div>

        {/* New chat button */}
        <div className="px-4 pt-4 pb-2">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 text-sidebar-text/55 hover:text-sidebar-text text-xs px-3 py-2 rounded-sm border border-sidebar-text/15 hover:border-sidebar-text/30 transition-colors"
          >
            <Plus className="w-3.5 h-3.5 shrink-0" />
            New chat
          </button>
        </div>

        {/* Session history */}
        <div className="flex-1 overflow-y-auto px-4 py-2">
          {sessions.length > 0 && (
            <>
              <p className="text-sidebar-text/25 text-xs uppercase tracking-widest mb-3 px-1 pt-2">
                Recent
              </p>
              <ul className="space-y-0.5">
                {sessions.map((s) => (
                  <li key={s.id}>
                    <button
                      onClick={() => {
                        setSessionId(s.id);
                        try {
                          const stored = localStorage.getItem(`basiniq_msgs_${s.id}`);
                          setMessages(stored ? JSON.parse(stored) : []);
                        } catch {
                          setMessages([]);
                        }
                      }}
                      className={`w-full text-left text-xs px-3 py-2 rounded-sm truncate transition-colors ${
                        sessionId === s.id
                          ? "text-sidebar-text bg-sidebar-text/10"
                          : "text-sidebar-text/40 hover:text-sidebar-text/65 hover:bg-sidebar-text/5"
                      }`}
                    >
                      {s.title}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        {/* Sidebar footer */}
        <div className="px-5 py-4 border-t border-sidebar-text/10">
          <p className="text-sidebar-text/20 text-xs leading-relaxed">
            Demo · Synthetic well data
          </p>
        </div>
      </aside>

      {/* ── CHAT AREA ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            /* Empty state */
            <div className="h-full flex flex-col items-center justify-center px-8 py-16 text-center">
              <p className="font-lora text-4xl text-body/20 mb-1 leading-none">
                BASIN<span className="text-marker/25">IQ</span>
              </p>
              <p className="text-muted/50 text-sm mb-10">
                Ask a question about Alberta&apos;s upstream energy sector.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg w-full">
                {SUGGESTED.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSubmit(q)}
                    className="text-left text-xs text-muted border border-grid rounded-sm px-3 py-2.5 hover:border-montney/40 hover:text-body hover:bg-log-surface transition-colors leading-relaxed"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto px-5 py-8 space-y-6">
              {messages.map((msg, i) =>
                msg.role === "user" ? (
                  /* User bubble */
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[78%] bg-log-surface border border-grid rounded-sm px-4 py-3">
                      <p className="text-sm text-body">{msg.content}</p>
                    </div>
                  </div>
                ) : (
                  /* Assistant message */
                  <div key={i} className="space-y-1.5">
                    <div className="bg-log-surface border border-grid rounded-sm px-5 py-4">
                      <MarkdownContent content={msg.content} />

                      {/* Footer row — only show if a tool was actually used */}
                      {(msg.toolsUsed ?? []).length > 0 && (
                        <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-grid">
                          {msg.sources.length > 0 ? (
                            <>
                              <FileText className="w-3 h-3 text-muted/60" />
                              <span className="text-xs text-muted/60">
                                {msg.sources.length} directive source
                                {msg.sources.length > 1 ? "s" : ""} cited — see panel
                              </span>
                            </>
                          ) : (
                            <>
                              <Database className="w-3 h-3 text-muted/60" />
                              <span className="text-xs text-muted/60">
                                Retrieved from well database
                              </span>
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Disclaimer */}
                    <p className="text-xs text-muted/40 px-1">
                      Based on ingested AER directive versions. Verify directly
                      with AER for compliance decisions.
                    </p>
                  </div>
                )
              )}

              {/* Loading dots while waiting for stream to start */}
              {(loading || streamingContent === "") && (
                <div className="bg-log-surface border border-grid rounded-sm px-5 py-4">
                  <div className="flex items-center gap-1.5">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-montney/50 animate-pulse"
                        style={{ animationDelay: `${i * 160}ms` }}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Streaming text as it arrives */}
              {streamingContent !== null && streamingContent !== "" && (
                <div className="space-y-1.5">
                  <div className="bg-log-surface border border-grid rounded-sm px-5 py-4">
                    <MarkdownContent content={streamingContent} />
                  </div>
                  <p className="text-xs text-muted/40 px-1">
                    Based on ingested AER directive versions. Verify directly
                    with AER for compliance decisions.
                  </p>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* ── INPUT BAR ── */}
        <div className="shrink-0 border-t border-grid bg-log-surface px-6 py-4">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-end gap-3 border border-grid rounded-sm bg-log-cream px-4 py-3 focus-within:border-montney/50 transition-colors">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                disabled={loading}
                placeholder="Ask about AER directives, well data, or both…"
                rows={1}
                className="flex-1 resize-none bg-transparent text-sm text-body placeholder-muted/45 outline-none leading-relaxed min-h-[20px] max-h-36 disabled:opacity-40"
              />
              <button
                onClick={() => handleSubmit()}
                disabled={loading || !input.trim()}
                className="shrink-0 bg-montney hover:bg-montney-light disabled:opacity-25 text-white p-2 rounded-sm transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-muted/35 text-xs mt-2 text-center">
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>

      {/* ── CONTEXT PANEL ── */}
      <aside className="hidden lg:flex flex-col w-72 shrink-0 bg-log-surface border-l border-grid">
        {/* Header */}
        <div className="px-5 py-4 border-b border-grid">
          <p className="text-xs font-semibold text-body tracking-wide">
            Sources
          </p>
          <p className="text-xs text-muted mt-0.5">
            Citations from the last response
          </p>
        </div>

        {/* Source cards */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {latestSources.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center pb-10">
              <div className="w-9 h-9 rounded-full border border-grid flex items-center justify-center mb-3">
                <FileText className="w-3.5 h-3.5 text-muted/30" />
              </div>
              <p className="text-xs text-muted/45 leading-relaxed max-w-[160px]">
                Directive citations will appear here after a regulatory query.
              </p>
            </div>
          ) : (
            <ul className="space-y-2.5">
              {groupSources(latestSources).map(({ displayName, pages }) => (
                <li
                  key={displayName}
                  className="border-l-2 border-montney bg-log-cream rounded-sm px-4 py-3"
                >
                  <p className="text-xs font-semibold text-body leading-snug mb-1.5">
                    {displayName}
                  </p>
                  <p className="text-xs text-muted mb-1.5">AER Directive</p>
                  {pages.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {pages.map((p) => (
                        <span
                          key={p}
                          className="text-xs font-mono text-montney bg-log-surface border border-grid px-1.5 py-0.5 rounded-sm"
                        >
                          p. {p}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Panel footer */}
        <div className="px-5 py-4 border-t border-grid">
          <p className="text-xs text-muted/35 leading-relaxed">
            All citations include directive name and page number.
          </p>
        </div>
      </aside>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatInterface />
    </Suspense>
  );
}
