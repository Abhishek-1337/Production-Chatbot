import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Routes, Route, Navigate, useLocation, useNavigate, Link } from "react-router-dom";
import { ApiError, authenticate, createApi, readAssistantStream } from "./api";
import { AuthScreen } from "./components/AuthScreen";
import { ChatView } from "./components/ChatView";
import { Icon } from "./components/Icon";
import { Sidebar } from "./components/Sidebar";
import { ThemeToggle } from "./components/ThemeToggle";
import { ToastContainer, type ToastItem } from "./components/Toast";
import { UploadOverlay } from "./components/UploadOverlay";
import { Welcome } from "./components/Welcome";
import AdminDashboard from "./pages/AdminDashboard";
import type { Conversation, User } from "./types";
import { errorMessage } from "./utils";

const TOKEN_KEY = "rag-token";
const THEME_KEY = "rag-theme";

function getConversationIdFromPath(pathname: string) {
  const match = pathname.match(/^\/conversations\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function AppRoutes() {
  const location = useLocation();
  const navigate = useNavigate();

  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) ?? "");
  const [user, setUser] = useState<User | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [isDark, setIsDark] = useState(() => localStorage.getItem(THEME_KEY) === "dark");
  const fileInput = useRef<HTMLInputElement>(null);
  const api = createApi(token);
  const [authLoading, setAuthLoading] = useState(() => !!token);

  // Pagination for active conversation messages (keyset)
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [uploadFileName, setUploadFileName] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismissToast = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const showToast = (message: string, type: ToastItem["type"] = "info", durationMs?: number) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, message, type }]);
    if (type !== "loading") {
      const ms = durationMs ?? (type === "error" ? 4500 : 3200);
      setTimeout(() => dismissToast(id), ms);
    }
    return id;
  };

  useEffect(() => {
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
  }, [isDark]);

  const updateConversationUrl = (id: string | null, replace = false) => {
    const to = id ? `/conversations/${encodeURIComponent(id)}` : "/";
    navigate(to, { replace });
  };

  // Helper to load conversation metadata + first page of messages
  const loadConversationWithMessages = async (
    client: ReturnType<typeof createApi>,
    conversationId: string,
  ) => {
    const convo = await client.getConversation(conversationId);
    try {
      const page = await client.getMessages(conversationId, 50);
      setHasMore(page.has_more);
      setNextCursor(page.next_cursor);
      return { ...convo, messages: page.messages } as Conversation;
    } catch {
      // Fallback: show conversation even if messages fail
      setHasMore(false);
      setNextCursor(null);
      return { ...convo, messages: [] } as Conversation;
    }
  };

  useEffect(() => {
    if (!token) {
      setUser(null);
      setConversations([]);
      setActive(null);
      setAuthLoading(false);
      setConversationsLoading(false);
      return;
    }
    const client = createApi(token);
    setAuthLoading(true);
    setConversationsLoading(true);
    setError("");
    Promise.all([client.getUser(), client.getConversations()])
      .then(async ([me, chats]) => {
        setUser(me);
        setConversations(chats);
        const conversationId = getConversationIdFromPath(location.pathname);
        const conversation = chats.find((item) => item.id === conversationId);
        if (conversationId && conversation) {
          setConversationLoading(true);
          setSelectingId(conversation.id);
          try {
            const full = await loadConversationWithMessages(client, conversation.id);
            setActive(full);
          } catch (err) {
            navigate("/", { replace: true });
            setError(errorMessage(err, "Could not open conversation"));
          } finally {
            setConversationLoading(false);
            setSelectingId(null);
          }
        } else if (conversationId) {
          navigate("/", { replace: true });
        }
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          setToken("");
          setUser(null);
          setError("Your session has expired. Please sign in again.");
          return;
        }
        setError(errorMessage(err, "Could not load your workspace"));
      })
      .finally(() => {
        setConversationsLoading(false);
        setAuthLoading(false);
      });
    // only run on token change (location read once on mount)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // React to SPA route changes (back/forward, Link navigation) to load conversation
  useEffect(() => {
    if (!token || !user) return;
    const conversationId = getConversationIdFromPath(location.pathname);
    if (!conversationId) {
      setActive(null);
      setHasMore(false);
      setNextCursor(null);
      return;
    }
    // Avoid reloading if already active
    if (active?.id === conversationId) return;

    const load = async () => {
      setConversationLoading(true);
      setSelectingId(conversationId);
      setError("");
      try {
        const client = createApi(token);
        const full = await loadConversationWithMessages(client, conversationId);
        setActive(full);
      } catch {
        navigate("/", { replace: true });
        setActive(null);
        setError("Could not open conversation");
      } finally {
        setConversationLoading(false);
        setSelectingId(null);
      }
    };
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, token, user]);

  const selectConversation = async (conversation: Conversation) => {
    if (authLoading || !user) {
      setError("Please wait — verifying your session.");
      return;
    }
    if (conversationLoading) return;
    if (active?.id === conversation.id && (active.messages?.length ?? 0) > 0) {
      setSidebarOpen(false);
      return;
    }
    setError("");
    setSidebarOpen(false);
    setHasMore(false);
    setNextCursor(null);
    setConversationLoading(true);
    setSelectingId(conversation.id);
    try {
      const full = await loadConversationWithMessages(api, conversation.id);
      setActive(full);
      updateConversationUrl(conversation.id);
    } catch (err) {
      setError(errorMessage(err, "Could not open conversation"));
    } finally {
      setConversationLoading(false);
      setSelectingId(null);
    }
  };

  const loadMoreMessages = async () => {
    if (authLoading || !user) return;
    if (!active || !hasMore || loadingMore) return;
    const oldest = active.messages?.[0]?.created_at ?? nextCursor;
    if (!oldest) return;
    setLoadingMore(true);
    try {
      const page = await api.getMessages(active.id, 50, oldest);
      // Prepend older messages
      setActive((prev) =>
        prev
          ? {
              ...prev,
              messages: [...page.messages, ...(prev.messages ?? [])],
            }
          : prev,
      );
      setHasMore(page.has_more);
      setNextCursor(page.next_cursor);
    } catch (err) {
      setError(errorMessage(err, "Could not load older messages"));
    } finally {
      setLoadingMore(false);
    }
  };

  const deleteConversation = async (conversation: Conversation) => {
    if (authLoading || !user) {
      setError("Please wait — verifying your session.");
      return;
    }
    if (deletingId) return;
    setDeletingId(conversation.id);
    setError("");
    const deletingToastId = showToast(`Deleting “${conversation.title}”…`, "loading");
    try {
      await api.deleteConversation(conversation.id);
      setConversations((items) => items.filter((item) => item.id !== conversation.id));
      if (active?.id === conversation.id) {
        setActive(null);
        setHasMore(false);
        setNextCursor(null);
        navigate("/", { replace: true });
      }
      setToasts((prev) => prev.filter((t) => t.id !== deletingToastId));
      showToast(`Deleted “${conversation.title}”.`, "success");
    } catch (err) {
      setToasts((prev) => prev.filter((t) => t.id !== deletingToastId));
      const msg = errorMessage(err, "Could not delete conversation");
      setError(msg);
      showToast(msg, "error");
    } finally {
      setDeletingId(null);
    }
  };

  const upload = async (file: File) => {
    if (authLoading || !user) {
      setError("You must be signed in to upload.");
      showToast("Please sign in to upload documents.", "error");
      return;
    }
    setUploading(true);
    setUploadFileName(file.name);
    setError("");
    const loadingToastId = showToast(`Uploading “${file.name}” — parsing & indexing…`, "loading");
    try {
      const conversation = await api.upload(file);
      // upload response is metadata-only; ensure messages empty and pagination reset
      const newActive = { ...conversation, messages: [] } as Conversation;
      setHasMore(false);
      setNextCursor(null);
      setConversations((items) => [conversation, ...items]);
      setActive(newActive);
      updateConversationUrl(conversation.id);
      setSidebarOpen(false);
      setToasts((prev) => prev.filter((t) => t.id !== loadingToastId));
      showToast(`“${file.name}” indexed — ready to chat.`, "success");
    } catch (err) {
      setToasts((prev) => prev.filter((t) => t.id !== loadingToastId));
      const msg = errorMessage(err, "Upload failed");
      setError(msg);
      showToast(msg, "error");
    } finally {
      setUploading(false);
      setUploadFileName(null);
    }
  };

  const sendQuestion = async (text: string) => {
    if (authLoading || !user) {
      setError("You must be signed in to chat.");
      showToast("Please sign in to chat.", "error");
      return;
    }
    if (!text || !active || loading) return;

    const conversationId = active.id;
    const answerId = `answer-${Date.now()}`;
    setQuery("");
    setLoading(true);
    setError("");
    setActive((current) =>
      current
        ? {
            ...current,
            messages: [
              ...(current.messages ?? []),
              {
                id: `local-${Date.now()}`,
                role: "user",
                content: text,
                created_at: new Date().toISOString(),
              },
            ],
          }
        : current,
    );

    try {
      const response = await api.sendMessage(text, conversationId);
      setActive((current) =>
        current
          ? {
              ...current,
              messages: [
                ...(current.messages ?? []),
                {
                  id: answerId,
                  role: "assistant",
                  content: "",
                  created_at: new Date().toISOString(),
                },
              ],
            }
          : current,
      );
      let assistant = "";
      await readAssistantStream(response, (content) => {
        assistant += content;
        setActive((current) =>
          current
            ? {
                ...current,
                messages: (current.messages ?? []).map((message) =>
                  message.id === answerId ? { ...message, content: assistant } : message,
                ),
              }
            : current,
        );
      });
      if (!assistant.trim()) {
        throw new Error("The assistant returned an empty answer.");
      }
      setConversations((items) =>
        items.map((item) => (item.id === conversationId ? { ...item, updated_at: new Date().toISOString() } : item)),
      );
    } catch (err) {
      setError(errorMessage(err, "Message failed"));
      setActive((current) => {
        if (!current) return current;
        const messages = current.messages ?? [];
        const hasAnswer = messages.some((message) => message.id === answerId);
        const failedAnswer = {
          id: answerId,
          role: "assistant" as const,
          content: "I couldn't answer that question.",
          created_at: new Date().toISOString(),
          status: "failed" as const,
        };

        return {
          ...current,
          messages: hasAnswer ? messages.map((message) => (message.id === answerId ? failedAnswer : message)) : [...messages, failedAnswer],
        };
      });
    } finally {
      setLoading(false);
    }
  };

  const send = (event: FormEvent) => {
    event.preventDefault();
    void sendQuestion(query.trim());
  };

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const newToken = await authenticate(authMode, new FormData(event.currentTarget));
      localStorage.setItem(TOKEN_KEY, newToken);
      setAuthLoading(true);
      setToken(newToken);
    } catch (err) {
      setError(errorMessage(err, "Could not sign in"));
    }
  };

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken("");
    setUser(null);
    setConversations([]);
    setActive(null);
    setHasMore(false);
    setNextCursor(null);
    setConversationsLoading(false);
    setConversationLoading(false);
    setSelectingId(null);
    navigate("/", { replace: true });
  };

  // --- Auth guards ---
  if (!token) {
    return (
      <AuthScreen
        mode={authMode}
        error={error}
        onModeChange={() => {
          setAuthMode(authMode === "login" ? "register" : "login");
          setError("");
        }}
        onSubmit={submitAuth}
        isDark={isDark}
        onThemeToggle={() => setIsDark((value) => !value)}
      />
    );
  }

  if (authLoading) {
    return (
      <div className="flex h-svh flex-col items-center justify-center gap-4 bg-[var(--paper)] px-6 text-center">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--amber)]" aria-label="Verifying session" />
        <div>
          <p className="m-0 text-sm font-medium text-[var(--ink)]">Verifying your session…</p>
          <p className="mt-1 text-xs text-[var(--muted)]">Please wait — upload and chat are disabled until sign-in completes</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <AuthScreen
        mode={authMode}
        error={error || "Session could not be verified. Please sign in again."}
        onModeChange={() => {
          setAuthMode(authMode === "login" ? "register" : "login");
          setError("");
        }}
        onSubmit={submitAuth}
        isDark={isDark}
        onThemeToggle={() => setIsDark((value) => !value)}
      />
    );
  }

  // --- Protected routes ---
  return (
    <Routes>
      <Route
        path="/admin"
        element={
          !user.is_admin ? (
            <div className="flex h-svh flex-col items-center justify-center gap-4 bg-[var(--paper)] p-6 text-center">
              <h1 className="text-xl font-semibold">403 — Admin access required</h1>
              <p className="text-sm text-[var(--muted)]">Your account ({user.email}) is not an admin.</p>
              <Link to="/" className="rounded bg-[var(--navy)] px-4 py-2 text-sm text-white">
                Back to chat
              </Link>
              <p className="text-xs text-[var(--muted)]">
                Tip: Run <code>python scripts/make_admin.py {user.email}</code> on the server or{" "}
                <code>UPDATE users SET is_admin=true WHERE email='{user.email}'</code> and re-login.
              </p>
            </div>
          ) : (
            <AdminDashboard />
          )
        }
      />
      <Route
        path="/conversations/:id"
        element={
          <ChatLayout
            conversations={conversations}
            active={active}
            user={user}
            sidebarOpen={sidebarOpen}
            uploading={uploading}
            deletingId={deletingId}
            conversationsLoading={conversationsLoading}
            selectingId={selectingId}
            conversationLoading={conversationLoading}
            loading={loading}
            query={query}
            error={error}
            hasMore={hasMore}
            loadingMore={loadingMore}
            isDark={isDark}
            setSidebarOpen={setSidebarOpen}
            setQuery={setQuery}
            selectConversation={selectConversation}
            deleteConversation={deleteConversation}
            upload={upload}
            send={send}
            sendQuestion={sendQuestion}
            loadMoreMessages={loadMoreMessages}
            setIsDark={setIsDark}
            fileInput={fileInput}
            uploadFileName={uploadFileName}
            toasts={toasts}
            dismissToast={dismissToast}
            showToast={showToast}
            signOut={signOut}
          />
        }
      />
      <Route
        path="/"
        element={
          <ChatLayout
            conversations={conversations}
            active={active}
            user={user}
            sidebarOpen={sidebarOpen}
            uploading={uploading}
            deletingId={deletingId}
            conversationsLoading={conversationsLoading}
            selectingId={selectingId}
            conversationLoading={conversationLoading}
            loading={loading}
            query={query}
            error={error}
            hasMore={hasMore}
            loadingMore={loadingMore}
            isDark={isDark}
            setSidebarOpen={setSidebarOpen}
            setQuery={setQuery}
            selectConversation={selectConversation}
            deleteConversation={deleteConversation}
            upload={upload}
            send={send}
            sendQuestion={sendQuestion}
            loadMoreMessages={loadMoreMessages}
            setIsDark={setIsDark}
            fileInput={fileInput}
            uploadFileName={uploadFileName}
            toasts={toasts}
            dismissToast={dismissToast}
            showToast={showToast}
            signOut={signOut}
          />
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function ChatLayout(props: {
  conversations: Conversation[];
  active: Conversation | null;
  user: User;
  sidebarOpen: boolean;
  uploading: boolean;
  deletingId: string | null;
  conversationsLoading: boolean;
  selectingId: string | null;
  conversationLoading: boolean;
  loading: boolean;
  query: string;
  error: string;
  hasMore: boolean;
  loadingMore: boolean;
  isDark: boolean;
  setSidebarOpen: (v: boolean) => void;
  setQuery: (v: string) => void;
  selectConversation: (c: Conversation) => void;
  deleteConversation: (c: Conversation) => void;
  upload: (f: File) => void;
  send: (e: FormEvent) => void;
  sendQuestion: (t: string) => void;
  loadMoreMessages: () => void;
  setIsDark: (f: (v: boolean) => boolean) => void;
  fileInput: React.RefObject<HTMLInputElement | null>;
  uploadFileName: string | null;
  toasts: ToastItem[];
  dismissToast: (id: number) => void;
  showToast: (m: string, t?: ToastItem["type"]) => number;
  signOut: () => void;
}) {
  const {
    conversations,
    active,
    user,
    sidebarOpen,
    uploading,
    deletingId,
    conversationsLoading,
    selectingId,
    conversationLoading,
    loading,
    query,
    error,
    hasMore,
    loadingMore,
    isDark,
    setSidebarOpen,
    setQuery,
    selectConversation,
    deleteConversation,
    upload,
    send,
    sendQuestion,
    loadMoreMessages,
    setIsDark,
    fileInput,
    uploadFileName,
    toasts,
    dismissToast,
    signOut,
  } = props;

  return (
    <div className="flex h-svh min-w-0 overflow-hidden bg-[var(--paper)] text-[var(--ink)]">
      <Sidebar
        conversations={conversations}
        active={active}
        user={user}
        open={sidebarOpen}
        uploading={uploading}
        disabled={!user}
        deletingId={deletingId}
        loadingConversations={conversationsLoading}
        selectingId={selectingId}
        onClose={() => setSidebarOpen(false)}
        onNew={() => fileInput.current?.click()}
        onSelect={selectConversation}
        onDelete={(c) => void deleteConversation(c)}
        onSignOut={signOut}
      />
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-[var(--line)] px-[18px] sm:px-[42px] h-[71px]">
          <button
            className="grid place-items-center border-0 bg-transparent p-2 text-[var(--muted)] md:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Icon name="menu" />
          </button>
          {active ? (
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 rounded-full bg-[#7eb587] shadow-[0_0_0_4px_#e7f1e7]" />
              <div>
                <strong className="block text-sm">{active.title}</strong>
                <small className="mt-0.5 flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Icon name="file" size={12} /> {active.document_name ?? "Source document"}
                </small>
              </div>
            </div>
          ) : (
            <div className="font-mono text-[10px] font-medium tracking-[1.5px] text-[var(--muted)] max-sm:hidden">RAG / RESEARCH DESK</div>
          )}
          <div className="ml-auto flex items-center gap-3">
            {user?.is_admin && (
              <Link
                to="/admin"
                className="rounded border border-[var(--line)] bg-white px-3 py-1.5 text-xs font-medium hover:bg-[#eef1ec] dark:bg-[#1e323a] dark:hover:bg-[#22343c]"
              >
                Admin
              </Link>
            )}
            <ThemeToggle isDark={isDark} onToggle={() => setIsDark((value) => !value)} />
          </div>
        </header>
        {conversationLoading ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-12">
            <span className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--amber)]" />
            <div className="text-center">
              <p className="m-0 text-sm font-medium text-[var(--ink)]">Loading conversation…</p>
              <p className="mt-1 text-xs text-[var(--muted)]">Fetching messages from the database</p>
            </div>
            <div className="mt-4 w-full max-w-[400px] space-y-3 opacity-60">
              <div className="h-4 w-3/4 animate-pulse rounded bg-[#e4e9e4] dark:bg-[#22343c]" />
              <div className="h-4 w-full animate-pulse rounded bg-[#e4e9e4] dark:bg-[#22343c]" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-[#e4e9e4] dark:bg-[#22343c]" />
            </div>
          </div>
        ) : active ? (
          <ChatView
            active={active}
            loading={loading}
            query={query}
            error={error}
            disabled={!user}
            onQueryChange={setQuery}
            onSubmit={send}
            onRetry={(text) => void sendQuestion(text)}
            hasMore={hasMore}
            isLoadingMore={loadingMore}
            onLoadMore={() => void loadMoreMessages()}
          />
        ) : (
          <Welcome
            uploading={uploading}
            disabled={!user}
            onUpload={() => fileInput.current?.click()}
          />
        )}
      </main>
      <input
        ref={fileInput}
        type="file"
        hidden
        accept=".pdf,.doc,.docx,.txt"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void upload(file);
          event.target.value = "";
        }}
      />
      {uploading && <UploadOverlay fileName={uploadFileName} />}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default function App() {
  return <AppRoutes />;
}
