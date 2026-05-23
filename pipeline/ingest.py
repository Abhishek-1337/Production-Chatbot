from markitdown import MarkItDown
from chonkie import Pipeline


def ingest_doc(): 
    md = MarkItDown()
    result = md.convert("./tms-doc/tms.pdf")

    pipe = (
        Pipeline()
        .chunk_with("recursive", tokenizer="gpt2", chunk_size=600, recipe="markdown")
        .chunk_with("semantic", chunk_size=512)
        .refine_with("overlap", context_size=128)
        .refine_with("embeddings", embedding_model="sentence-transformers/all-MiniLM-L6-v2")
    )

    doc = pipe.run(result.markdown)

    print(doc.chunks)