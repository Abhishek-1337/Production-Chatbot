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
  onRetry: (query: string) => void;
};

export function ChatView({
  active,
  loading,
  query,
  error,
  onQueryChange,
  onSubmit,
  onRetry,
}: ChatViewProps) {
  const messages = active.messages ?? [];

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-auto px-[22px] py-[35px] sm:px-[8%] sm:py-[55px]">
        <div className="mb-9 border-b border-[var(--line)] pb-[30px]">
          <div className="mb-6 text-[var(--amber)]">
            <Icon name="book" size={24} />
          </div>
          <p className="m-0 font-mono text-[10px] font-medium tracking-[1.5px] text-[var(--muted)]">
            SOURCE LOADED
          </p>
          <h1 className="my-2.5 text-[31px] font-semibold leading-tight tracking-[-1.5px] text-[var(--navy)] sm:text-[38px]">
            {active.title}
          </h1>
          <p className="text-sm text-[#7b878b] dark:text-[#aab8b5]">
            Ask anything about this document. Answers are generated from its
            contents only.
          </p>
        </div>
        {messages.map((message, index) => (
          <article
            key={message.id}
            className={`mb-7 max-w-[680px] ${message.role === "user" ? "ml-auto text-right" : ""}`}
          >
            <div
              className={`mb-2 font-mono text-[10px] font-medium tracking-[1.5px] ${message.role === "user" ? "text-[#b77b2a]" : "text-[var(--muted)]"}`}
            >
              {message.role === "user" ? "YOU" : "RAG / ASSISTANT"}
            </div>
            <div
              className={`inline-block whitespace-pre-wrap text-left text-[15px] leading-relaxed ${message.role === "user" ? "bg-[#e9eee9] px-4 py-3 text-[#33443e] dark:bg-[#243b3d] dark:text-[#d9e8df]" : "max-w-[640px] text-[#314149] dark:text-[#d0dcda]"}`}
            >
              {message.status === "failed" ? (
                <div className="flex flex-col items-start gap-3">
                  <span>{message.content}</span>
                  {messages[index - 1]?.role === "user" && (
                    <button
                      className="inline-flex items-center gap-2 border border-[#b34e3e] bg-transparent px-3 py-2 text-xs font-semibold text-[#b34e3e] transition hover:bg-[#b34e3e] hover:text-white"
                      type="button"
                      onClick={() => onRetry(messages[index - 1].content)}
                    >
                      Retry question
                    </button>
                  )}
                </div>
              ) : (
                message.content || (loading && <Typing />)
              )}
            </div>
          </article>
        ))}
        {loading &&
          !messages.some(
            (message) =>
              message.role === "assistant" && message.id.startsWith("answer-"),
          ) && (
            <article className="mb-7 max-w-[680px]">
              <div className="mb-2 font-mono text-[10px] font-medium tracking-[1.5px] text-[var(--muted)]">
                RAG / ASSISTANT
              </div>
              <div className="inline-block max-w-[640px] text-left text-[15px] leading-relaxed text-[#314149] dark:text-[#d0dcda]">
                <Typing />
              </div>
            </article>
          )}
        {error && (
          <p className="mx-auto mb-5 flex max-w-[680px] items-center gap-1.5 text-xs text-[#b34e3e]">
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
