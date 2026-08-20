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
    <aside className={`sidebar flex w-80 shrink-0 flex-col ${open ? "is-open" : ""}`}>
      <div className="sidebar-top">
        <div className="brand-mark">
          R<span>/</span>G
        </div>
        <button
          className="icon-button mobile-close"
          onClick={onClose}
          aria-label="Close sidebar"
        >
          <Icon name="close" />
        </button>
      </div>
      <div className="sidebar-heading">
        <div>
          <p className="eyebrow">WORKSPACE</p>
          <h2>Conversations</h2>
        </div>
        <button className="new-button" onClick={onNew} disabled={uploading}>
          <Icon name="plus" /> New
        </button>
      </div>
      <div className="conversation-list flex-1 overflow-auto">
        {conversations.length === 0 ? (
          <div className="empty-sidebar">
            <Icon name="file" size={20} />
            <p>No conversations yet.</p>
            <span>Upload a document to begin.</span>
          </div>
        ) : (
          conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`conversation-item ${active?.id === conversation.id ? "active" : ""}`}
              onClick={() => onSelect(conversation)}
            >
              <span className="conversation-icon">
                <Icon name="file" size={16} />
              </span>
              <span className="conversation-meta">
                <strong>{conversation.title}</strong>
                <small>
                  {conversation.document_name ?? "Document"} ·{" "}
                  {formatDate(conversation.updated_at)}
                </small>
              </span>
            </button>
          ))
        )}
      </div>
      <div className="sidebar-footer">
        <div className="user-chip">
          <span>{user?.name?.slice(0, 1).toUpperCase() ?? "U"}</span>
          <div>
            <strong>{user?.name ?? "Researcher"}</strong>
            <small>{user?.email}</small>
          </div>
          <button
            className="icon-button"
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
