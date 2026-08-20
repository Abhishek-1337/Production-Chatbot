import type { FormEvent } from "react";
import type { Conversation } from "../types";
import { Icon } from "./Icon";
import { Composer } from "./Composer";
import { Typing } from "./Typing";

type ChatViewProps = {
  active: Conversation;
  loading: boolean;
  query: string;
  error: string;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
};

export function ChatView({
  active,
  loading,
  query,
  error,
  onQueryChange,
  onSubmit,
}: ChatViewProps) {
  const messages = active.messages ?? [];

  return (
    <section className="chat-view">
      <div className="chat-scroll">
        <div className="chat-intro">
          <div className="intro-symbol">
            <Icon name="book" size={24} />
          </div>
          <p className="eyebrow">SOURCE LOADED</p>
          <h1>{active.title}</h1>
          <p>
            Ask anything about this document. Answers are generated from its
            contents only.
          </p>
        </div>
        {messages.map((message) => (
          <article key={message.id} className={`message ${message.role}`}>
            <div className="message-label">
              {message.role === "user" ? "YOU" : "RAG / ASSISTANT"}
            </div>
            <div className="message-body">
              {message.content || (loading && <Typing />)}
            </div>
          </article>
        ))}
        {loading &&
          !messages.some(
            (message) =>
              message.role === "assistant" && message.id.startsWith("answer-"),
          ) && (
            <article className="message assistant">
              <div className="message-label">RAG / ASSISTANT</div>
              <div className="message-body">
                <Typing />
              </div>
            </article>
          )}
        {error && (
          <p className="error inline-error">
            <Icon name="alert" />
            {error}
          </p>
        )}
      </div>
      <Composer
        query={query}
        loading={loading}
        onChange={onQueryChange}
        onSubmit={onSubmit}
      />
    </section>
  );
}
