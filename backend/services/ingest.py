from pathlib import Path
from io import BytesIO
from markitdown import MarkItDown
from chonkie import Pipeline
import chromadb

_CHROMA_PATH = str(Path(__file__).resolve().parent.parent / "chroma_db")


def ingest_doc(data, document_id, user_id): 
    try:
        md = MarkItDown()
        text_bytes = data.encode("utf-8")
        result = md.convert_stream(BytesIO(text_bytes), file_extension=".txt")
    
        pipe = (
            Pipeline()
            .chunk_with("recursive", tokenizer="gpt2", chunk_size=256, recipe="markdown")
            # .chunk_with("semantic", chunk_size=512)
            .refine_with("overlap", context_size=50)
            .refine_with("embeddings", embedding_model="sentence-transformers/all-MiniLM-L6-v2")
        )
    
        doc = pipe.run(result.markdown)
    
        chroma_client = chromadb.PersistentClient(path=_CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name="documents")
    
        embeddings_list = []
        ids_list = []
        documents_list = []
        metadatas_list = []
        for idx, chunk in enumerate(doc.chunks):
            documents_list.append(chunk.text)
            ids_list.append(f"{document_id}_{idx}")
            embeddings_list.append(chunk.embedding)
            metadatas_list.append({
                "document_id": str(document_id),
                "user_id": str(user_id),
            })
    
        collection.add(
            documents=documents_list,
            ids=ids_list,
            embeddings=embeddings_list,
            metadatas=metadatas_list
        )

    except Exception as e:
        raise RuntimeError(f"Error: {e}") from e
