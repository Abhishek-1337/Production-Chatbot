from markitdown import MarkItDown
from chonkie import Pipeline
import chromadb


def ingest_doc(): 
    md = MarkItDown()
    result = md.convert("./tms-doc/tms.pdf")

    pipe = (
        Pipeline()
        .chunk_with("recursive", tokenizer="gpt2", chunk_size=600, recipe="markdown")
        .chunk_with("semantic", chunk_size=512)
        .refine_with("overlap", context_size=128)
        .refine_with("embeddings", embedding_model="sentence-transformers/`all-MiniLM-L6-v2")
    )

    doc = pipe.run(result.markdown)
    first_chunk = doc.chunks[0]
    print(first_chunk.text)
    print(first_chunk.embedding)

    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="tms-doc")

    embeddings_list = []
    ids_list = []
    documents_list = []
    for idx, chunk in enumerate(doc.chunks):
        documents_list.append(chunk.text)
        ids_list.append(str(idx))
        embeddings_list.append(chunk.embedding)

    collection.add(
        documents=documents_list,
        ids=ids_list,
        embeddings=embeddings_list
    )