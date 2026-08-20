import { Icon } from "./Icon";

export function Welcome({
  uploading,
  onUpload,
}: {
  uploading: boolean;
  onUpload: () => void;
}) {
  return (
    <section className="welcome">
      <div className="welcome-grid">
        <div className="welcome-copy">
          <p className="eyebrow">YOUR DOCUMENTS, IN CONTEXT</p>
          <h1>
            A clearer way
            <br />
            to <em>read deeply.</em>
          </h1>
          <p>
            Bring a report, brief, or body of research. RAG will keep every
            answer tethered to the source.
          </p>
          <button
            className="primary-button"
            onClick={onUpload}
            disabled={uploading}
          >
            {uploading ? "Indexing document..." : "Upload a document"}{" "}
            <Icon name="upload" />
          </button>
        </div>
        <div className="blueprint">
          <div className="blueprint-ring" />
          <div className="blueprint-card">
            <Icon name="file" size={22} />
            <span>YOUR SOURCE</span>
            <strong>Ready when you are.</strong>
            <small>PDF · DOCX · TXT</small>
          </div>
          <div className="blueprint-line line-one" />
          <div className="blueprint-line line-two" />
        </div>
      </div>
      <div className="principles">
        <span>
          <Icon name="check" /> Source-grounded answers
        </span>
        <span>
          <Icon name="check" /> Private workspace
        </span>
        <span>
          <Icon name="check" /> Conversation memory
        </span>
      </div>
    </section>
  );
}
