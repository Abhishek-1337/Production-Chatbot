import { Icon } from "./Icon";

export function UploadOverlay({ fileName }: { fileName?: string | null }) {
  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-[rgba(14,30,38,0.48)] backdrop-blur-[2px]">
      <div className="flex max-w-[380px] flex-col items-center gap-4 border border-[var(--line)] bg-white px-8 py-8 text-center shadow-[0_12px_36px_rgba(0,0,0,0.18)] dark:bg-[#17242b]">
        <span className="grid h-12 w-12 place-items-center rounded-full border-2 border-[#d8e4e1] dark:border-[#2d424d]">
          <span className="h-7 w-7 animate-spin rounded-full border-[2.5px] border-[var(--line)] border-t-[var(--navy)] dark:border-[#2d424d] dark:border-t-[#d8e4e1]" />
        </span>
        <div>
          <p className="m-0 text-[15px] font-semibold text-[var(--ink)]">
            Processing document
          </p>
          {fileName ? (
            <p className="mt-1 max-w-[260px] truncate text-xs text-[var(--muted)]">
              {fileName}
            </p>
          ) : null}
          <p className="mx-auto mt-2 max-w-[280px] text-xs leading-relaxed text-[#758287] dark:text-[#aab8b5]">
            Parsing, chunking and indexing for retrieval. This may take a moment — please keep this tab open.
          </p>
        </div>
        <span className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[1.2px] text-[var(--muted)]">
          <Icon name="file" size={12} /> PDF · DOCX · TXT
        </span>
      </div>
    </div>
  );
}
