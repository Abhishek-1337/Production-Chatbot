import type { Conversation, User } from "../types";
import { formatDate } from "../utils";
import { Icon } from "./Icon";

type SidebarProps = {
  conversations: Conversation[];
  active: Conversation | null;
  user: User | null;
  open: boolean;
  uploading: boolean;
  onClose: () => void;
  onNew: () => void;
  onSelect: (conversation: Conversation) => void;
  onSignOut: () => void;
};

export function Sidebar({
  conversations,
  active,
  user,
  open,
  uploading,
  onClose,
  onNew,
  onSelect,
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
          disabled={uploading}
        >
          <Icon name="plus" /> New
        </button>
      </div>
      <div className="flex-1 overflow-auto px-3 py-1">
        {conversations.length === 0 ? (
          <div className="px-5 py-[42px] text-center text-[#9aa4a4]">
            <Icon name="file" size={20} />
            <p className="mb-0 mt-3 text-[13px] text-[#707c7e] dark:text-[#b7c2bf]">
              No conversations yet.
            </p>
            <span className="text-[11px]">Upload a document to begin.</span>
          </div>
        ) : (
          conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`group flex w-full gap-3 border-0 border-l-2 bg-transparent px-3 py-3 text-left text-[var(--ink)] transition hover:bg-[#e4e9e4] dark:hover:bg-[#22343c] ${active?.id === conversation.id ? "border-l-[var(--amber)] bg-[#e4e9e4] dark:bg-[#22343c]" : "border-l-transparent"}`}
              onClick={() => onSelect(conversation)}
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center border border-[var(--line)] bg-[#f7f8f5] text-[#7c898c] dark:bg-[#1d2c33] dark:text-[#a3b2b0]">
                <Icon name="file" size={16} />
              </span>
              <span className="flex min-w-0 flex-col gap-1">
                <strong className="truncate text-[13px] font-semibold">
                  {conversation.title}
                </strong>
                <small className="truncate text-[11px] text-[#899398] dark:text-[#9eaaa8]">
                  {conversation.document_name ?? "Document"} ·{" "}
                  {formatDate(conversation.updated_at)}
                </small>
              </span>
            </button>
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
