import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { Conversation, User } from "../types";
import { formatDate } from "../utils";
import { Icon } from "./Icon";

type SidebarProps = {
  conversations: Conversation[];
  active: Conversation | null;
  user: User | null;
  open: boolean;
  uploading: boolean;
  disabled?: boolean;
  deletingId: string | null;
  loadingConversations: boolean;
  selectingId: string | null;
  onClose: () => void;
  onNew: () => void;
  onSelect: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onSignOut: () => void;
};

function SidebarSkeleton() {
  return (
    <div className="space-y-2 px-1 py-1" aria-label="Loading conversations" aria-busy="true">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          key={index}
          className="flex animate-pulse gap-3 border-l-2 border-l-transparent px-3 py-3"
        >
          <span className="h-7 w-7 shrink-0 bg-[#d6e0d8] dark:bg-[#22343c]" />
          <span className="flex min-w-0 flex-1 flex-col gap-2 pt-1">
            <span className="h-3 w-3/4 rounded bg-[#d6e0d8] dark:bg-[#22343c]" />
            <span className="h-2 w-1/2 rounded bg-[#e4e9e4] dark:bg-[#1d2c33]" />
          </span>
        </div>
      ))}
      <div className="flex items-center justify-center gap-2 py-4 text-xs text-[var(--muted)]">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--amber)]" />
        Loading conversations…
      </div>
    </div>
  );
}

function ConversationCard({
  conversation,
  isActive,
  isDeleting,
  isSelecting,
  onSelect,
  onDelete,
}: {
  conversation: Conversation;
  isActive: boolean;
  isDeleting: boolean;
  isSelecting: boolean;
  onSelect: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  return (
    <div
      aria-busy={isDeleting}
      className={`group relative flex w-full gap-3 border-l-2 px-3 py-3 transition hover:bg-[#e4e9e4] dark:hover:bg-[#22343c] ${isDeleting ? "opacity-60" : ""} ${isActive ? "border-l-[var(--amber)] bg-[#e4e9e4] dark:bg-[#22343c]" : "border-l-transparent"}`}
    >
      <button
        className="flex min-w-0 flex-1 gap-3 border-0 bg-transparent p-0 text-left text-[var(--ink)] disabled:opacity-60"
        onClick={() => onSelect(conversation)}
        disabled={isDeleting || isSelecting}
      >
        <span className="grid h-7 w-7 shrink-0 place-items-center border border-[var(--line)] bg-[#f7f8f5] text-[#7c898c] dark:bg-[#1d2c33] dark:text-[#a3b2b0]">
          {isDeleting || isSelecting ? (
            <span
              className="h-3 w-3 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--amber)]"
              aria-label={isDeleting ? "Deleting" : "Loading"}
            />
          ) : (
            <Icon name="file" size={16} />
          )}
        </span>
        <span className="flex min-w-0 flex-col gap-1">
          <strong className="flex items-center gap-2 truncate text-[13px] font-semibold">
            {conversation.title}
            {(isDeleting || isSelecting) && (
              <span className="shrink-0 text-[10px] font-medium tracking-wide text-[var(--amber)]">
                {isDeleting ? "Deleting…" : "Loading…"}
              </span>
            )}
          </strong>
          <small className="truncate text-[11px] text-[#899398] dark:text-[#9eaaa8]">
            {conversation.document_name ?? "Document"} ·{" "}
            {formatDate(conversation.updated_at)}
          </small>
        </span>
      </button>

      <div className="relative shrink-0" ref={menuRef}>
        {isDeleting ? (
          <span
            className="grid place-items-center p-1.5 text-[var(--muted)]"
            aria-label="Deleting conversation"
          >
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--amber)]" />
          </span>
        ) : (
          <>
            <button
              className={`grid place-items-center border-0 bg-transparent p-1.5 text-[var(--muted)] opacity-0 transition hover:text-[var(--ink)] focus-visible:opacity-100 group-hover:opacity-100 disabled:opacity-40 ${menuOpen ? "opacity-100" : ""}`}
              onClick={(event) => {
                event.stopPropagation();
                setMenuOpen((value) => !value);
              }}
              aria-label={`Options for ${conversation.title}`}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              disabled={isSelecting}
            >
              {/* three vertical dots */}
              <svg width={16} height={16} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <circle cx="12" cy="5" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="19" r="2" />
              </svg>
            </button>
            {menuOpen && (
              <div
                role="menu"
                className="absolute right-1 top-7 z-20 mt-1 border border-[var(--line)] bg-white py-1 shadow-lg dark:bg-[#1b2a31] text-sm font-medium"
              >
                <button
                  role="menuitem"
                  className="flex items-center gap-2 border-0 bg-transparent px-3 py-1 text-left font-medium text-[#b34e3e] transition hover:bg-[#fbeeed] dark:hover:bg-[#33262a]"
                  onClick={(event) => {
                    event.stopPropagation();
                    setMenuOpen(false);
                    onDelete(conversation);
                  }}
                >
                  <Icon name="trash" size={14} />
                  Delete
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export function Sidebar({
  conversations,
  active,
  user,
  open,
  uploading,
  disabled = false,
  deletingId,
  loadingConversations,
  selectingId,
  onClose,
  onNew,
  onSelect,
  onDelete,
  onSignOut,
}: SidebarProps) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-10 flex w-80 shrink-0 flex-col border-r border-[var(--line)] bg-[#eef1ec] transition-transform dark:bg-[#17242b] md:static md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
    >
      <div className="flex justify-between px-[26px] pb-5 pt-7">
        <div className="font-mono text-[22px] font-semibold leading-none tracking-[-2px] text-[var(--navy)]">
          R<span>/</span>G
        </div>
        <button
          className="grid place-items-center border-0 bg-transparent p-2 text-[var(--muted)] md:hidden"
          onClick={onClose}
          aria-label="Close sidebar"
        >
          <Icon name="close" />
        </button>
      </div>
      <div className="flex items-end justify-between border-t border-[var(--line)] px-5 pb-[18px] pl-[26px] pt-[23px]">
        <div>
          <p className="m-0 font-mono text-[10px] font-medium tracking-[1.5px] text-[var(--muted)]">
            WORKSPACE
          </p>
          <h2 className="mt-1.5 text-xl tracking-[-0.5px] text-[var(--ink)]">
            Conversations
          </h2>
        </div>
        <button
          className="inline-flex items-center justify-center gap-2 border-0 bg-[var(--navy)] px-3 py-2 text-xs font-semibold text-white transition hover:-translate-y-px hover:bg-[#24475d] disabled:cursor-not-allowed disabled:opacity-60 dark:bg-[#d8e4e1] dark:text-[#15242b]"
          onClick={onNew}
          disabled={disabled || uploading}
        >
          {uploading ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white dark:border-[#15242b]/20 dark:border-t-[#15242b]" />
              Indexing…
            </>
          ) : (
            <>
              <Icon name="plus" /> New
            </>
          )}
        </button>
      </div>
      <div className="flex-1 overflow-auto px-3 py-1">
        {loadingConversations ? (
          <SidebarSkeleton />
        ) : conversations.length === 0 ? (
          <div className="px-5 py-[42px] text-center text-[#9aa4a4]">
            <Icon name="file" size={20} />
            <p className="mb-0 mt-3 text-[13px] text-[#707c7e] dark:text-[#b7c2bf]">
              No conversations yet.
            </p>
            <span className="text-[11px]">Upload a document to begin.</span>
          </div>
        ) : (
          conversations.map((conversation) => (
            <ConversationCard
              key={conversation.id}
              conversation={conversation}
              isActive={active?.id === conversation.id}
              isDeleting={deletingId === conversation.id}
              isSelecting={selectingId === conversation.id}
              onSelect={onSelect}
              onDelete={onDelete}
            />
          ))
        )}
      </div>
      <div className="border-t border-[var(--line)] p-[15px_18px]">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="grid h-[30px] w-[30px] shrink-0 place-items-center rounded-full bg-[#d6e0d8] font-mono text-xs text-[#50665c]">
            {user?.name?.slice(0, 1).toUpperCase() ?? "U"}
          </span>
          <div className="flex min-w-0 flex-1 flex-col">
            <strong className="truncate text-xs text-[var(--ink)]">
              {user?.name ?? "Researcher"}
            </strong>
            <small className="truncate text-[11px] text-[#899398] dark:text-[#9eaaa8]">
              {user?.email}
            </small>
            {user?.is_admin && (
              <Link to="/admin" className="mt-1 text-[11px] font-medium text-[#7eb587] hover:underline">
                Admin dashboard →
              </Link>
            )}
          </div>
          <button
            className="grid place-items-center border-0 bg-transparent p-2 text-[var(--muted)] hover:text-[var(--ink)]"
            onClick={onSignOut}
            aria-label="Sign out"
          >
            <Icon name="logout" size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
