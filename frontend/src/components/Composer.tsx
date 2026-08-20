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
    <form
      className="relative mx-auto mb-7 w-[calc(100%-34px)] max-w-[750px] sm:w-[84%]"
      onSubmit={onSubmit}
    >
      <textarea
        className="block min-h-[58px] w-full resize-none rounded-none border border-[#cfd8d2] bg-white px-[18px] py-[17px] pr-[60px] text-sm leading-normal text-[var(--ink)] shadow-[0_5px_16px_rgba(22,43,53,0.04)] outline-none placeholder:text-[#9ba5a3] focus:border-[#99aa9e] dark:border-[#405158] dark:bg-[#1a2930] dark:placeholder:text-[#80918f]"
        value={query}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Ask a question about your document..."
        rows={1}
        onKeyDown={handleKeyDown}
      />
      <button
        className="absolute right-2 top-2 grid h-10 w-10 place-items-center border-0 bg-[var(--amber)] text-white disabled:bg-[#d5ded8] dark:disabled:bg-[#3b4b4d]"
        type="submit"
        disabled={!query.trim() || loading}
      >
        <Icon name="send" />
      </button>
      <small className="mt-2 block font-mono text-[9px] tracking-[1px] text-[#9ba5a3] dark:text-[#829391]">
        ENTER TO SEND · SHIFT + ENTER FOR NEW LINE
      </small>
    </form>
  );
}
