import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { authenticate, createApi, readAssistantStream } from "./api";
import { AuthScreen } from "./components/AuthScreen";
import { ChatView } from "./components/ChatView";
import { Icon } from "./components/Icon";
import { Sidebar } from "./components/Sidebar";
import { ThemeToggle } from "./components/ThemeToggle";
import { Welcome } from "./components/Welcome";
import type { Conversation, User } from "./types";
import { errorMessage } from "./utils";
import "./App.css";

const TOKEN_KEY = "rag-token";
const THEME_KEY = "rag-theme";

function App() {
  const [token, setToken] = useState(
    () => localStorage.getItem(TOKEN_KEY) ?? "",
  );
  const [user, setUser] = useState<User | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [isDark, setIsDark] = useState(
    () => localStorage.getItem(THEME_KEY) === "dark",
  );
  const fileInput = useRef<HTMLInputElement>(null);
  const api = createApi(token);

  useEffect(() => {
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
  }, [isDark]);

  useEffect(() => {
    if (!token) return;
    const client = createApi(token);
    Promise.all([client.getUser(), client.getConversations()])
      .then(([me, chats]) => {
        setUser(me);
        setConversations(chats);
      })
      .catch((err) => {
        localStorage.removeItem(TOKEN_KEY);
        setToken("");
        setError(
          errorMessage(err, "Your session has expired. Please sign in again."),
        );
      });
  }, [token]);

  const selectConversation = async (conversation: Conversation) => {
    setError("");
    setSidebarOpen(false);
    try {
      setActive(await api.getConversation(conversation.id));
    } catch (err) {
      setError(errorMessage(err, "Could not open conversation"));
    }
  };

  const upload = async (file: File) => {
    setUploading(true);
    setError("");
    try {
      const conversation = await api.upload(file);
      setConversations((items) => [conversation, ...items]);
      setActive(conversation);
      setSidebarOpen(false);
    } catch (err) {
      setError(errorMessage(err, "Upload failed"));
    } finally {
      setUploading(false);
    }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim() || !active || loading) return;

    const text = query.trim();
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
                  message.id === answerId
                    ? { ...message, content: assistant }
                    : message,
                ),
              }
            : current,
        );
      });
      setConversations((items) =>
        items.map((item) =>
          item.id === conversationId
            ? { ...item, updated_at: new Date().toISOString() }
            : item,
        ),
      );
    } catch (err) {
      setError(errorMessage(err, "Message failed"));
    } finally {
      setLoading(false);
    }
  };

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const newToken = await authenticate(
        authMode,
        new FormData(event.currentTarget),
      );
      localStorage.setItem(TOKEN_KEY, newToken);
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
  };

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

  return (
    <div className="app-shell">
      <Sidebar
        conversations={conversations}
        active={active}
        user={user}
        open={sidebarOpen}
        uploading={uploading}
        onClose={() => setSidebarOpen(false)}
        onNew={() => fileInput.current?.click()}
        onSelect={selectConversation}
        onSignOut={signOut}
      />
      <main className="main-panel">
        <header className="topbar">
          <button
            className="icon-button menu-button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Icon name="menu" />
          </button>
          {active ? (
            <div className="document-heading">
              <span className="status-dot" />
              <div>
                <strong>{active.title}</strong>
                <small>
                  <Icon name="file" size={12} />{" "}
                  {active.document_name ?? "Source document"}
                </small>
              </div>
            </div>
          ) : (
            <div className="topbar-label">RAG / RESEARCH DESK</div>
          )}
          <div className="topbar-right">
            <ThemeToggle
              isDark={isDark}
              onToggle={() => setIsDark((value) => !value)}
            />
            <span className="live-label">
              <i /> SYSTEM READY
            </span>
          </div>
        </header>
        {active ? (
          <ChatView
            active={active}
            loading={loading}
            query={query}
            error={error}
            onQueryChange={setQuery}
            onSubmit={send}
          />
        ) : (
          <Welcome
            uploading={uploading}
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
    </div>
  );
}

export default App;
