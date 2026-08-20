import type { FormEvent, KeyboardEvent } from "react";
import { Icon } from "./Icon";

type ComposerProps = {
  query: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
};

export function Composer({
  query,
  loading,
  onChange,
  onSubmit,
}: ComposerProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form className="composer relative mx-auto w-[84%] max-w-[750px]" onSubmit={onSubmit}>
      <textarea
        value={query}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Ask a question about your document..."
        rows={1}
        onKeyDown={handleKeyDown}
      />
      <button
        className="send-button"
        type="submit"
        disabled={!query.trim() || loading}
      >
        <Icon name="send" />
      </button>
      <small>ENTER TO SEND · SHIFT + ENTER FOR NEW LINE</small>
    </form>
  );
}
