import { Icon } from "./Icon";

export function Welcome({
  uploading,
  onUpload,
}: {
  uploading: boolean;
  onUpload: () => void;
}) {
  return (
    <section className="flex min-h-0 w-full max-w-[980px] flex-1 flex-col justify-center px-[25px] py-[35px] sm:mx-auto sm:px-[8%] sm:py-[50px]">
      <div className="grid items-center gap-[8%] md:grid-cols-2">
        <div>
          <p className="m-0 font-mono text-[10px] font-medium tracking-[1.5px] text-[var(--muted)]">
            YOUR DOCUMENTS, IN CONTEXT
          </p>
          <h1 className="my-4 text-[44px] font-semibold leading-tight tracking-[-3px] text-[var(--navy)] sm:text-[clamp(42px,5vw,68px)]">
            A clearer way
            <br />
            to <em>read deeply.</em>
          </h1>
          <p className="max-w-[380px] text-[15px] leading-relaxed text-[#758287] dark:text-[#aab8b5]">
            Bring a report, brief, or body of research. RAG will keep every
            answer tethered to the source.
          </p>
          <button
            className="mt-7 inline-flex items-center justify-center gap-2 border-0 bg-[var(--navy)] px-[18px] py-3.5 text-[13px] font-semibold text-white transition hover:-translate-y-px hover:bg-[#24475d] dark:bg-[#d8e4e1] dark:text-[#15242b] dark:hover:bg-[#f0f6f2]"
            onClick={onUpload}
            disabled={uploading}
          >
            {uploading ? "Indexing document..." : "Upload a document"}{" "}
            <Icon name="upload" />
          </button>
        </div>
        <div className="relative hidden h-[350px] place-items-center md:grid">
          <div className="absolute h-[270px] w-[270px] rounded-full border border-[#d9e0db] dark:border-[#35484d] after:absolute after:inset-[25px] after:rounded-full after:border after:border-dashed after:border-[#d5ddd7] dark:after:border-[#35484d]" />
          <div className="relative z-10 flex min-h-[185px] w-[190px] flex-col justify-between bg-[var(--navy)] p-6 text-white shadow-[18px_20px_0_#e7ece6] dark:bg-[#d8e4e1] dark:text-[#15242b] dark:shadow-[18px_20px_0_#263941]">
            <Icon name="file" size={22} />
            <span className="font-mono text-[10px] tracking-[1px] text-[#aebdc2] dark:text-[#587074]">
              YOUR SOURCE
            </span>
            <strong className="text-[19px] leading-tight">
              Ready when you are.
            </strong>
            <small className="font-mono text-[10px] tracking-[1px] text-[#aebdc2] dark:text-[#587074]">
              PDF · DOCX · TXT
            </small>
          </div>
          <div className="absolute right-0 top-[35px] h-px w-[85px] bg-[#d4ddd8] dark:bg-[#35484d]" />
          <div className="absolute bottom-10 left-1 h-px w-[85px] bg-[#d4ddd8] dark:bg-[#35484d]" />
        </div>
      </div>
      <div className="mt-[45px] flex flex-wrap gap-[15px] border-t border-[var(--line)] pt-[18px] font-mono text-[10px] tracking-[0.5px] text-[#899496] sm:mt-[70px] sm:gap-7">
        <span className="flex items-center gap-2">
          <Icon name="check" /> Source-grounded answers
        </span>
        <span className="flex items-center gap-2">
          <Icon name="check" /> Private workspace
        </span>
        <span className="flex items-center gap-2">
          <Icon name="check" /> Conversation memory
        </span>
      </div>
    </section>
  );
}
