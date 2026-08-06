from io import BytesIO
from markitdown import MarkItDown
from chonkie import Pipeline
import chromadb


def ingest_doc(data): 
    try:
        md = MarkItDown()
        text_bytes = data.encode("utf-8")
        result = md.convert_stream(BytesIO(text_bytes), file_extension=".txt")
    
        pipe = (
            Pipeline()
            .chunk_with("recursive", tokenizer="gpt2", chunk_size=200, recipe="markdown")
            # .chunk_with("semantic", chunk_size=512)
            .refine_with("overlap", context_size=50)
            .refine_with("embeddings", embedding_model="sentence-transformers/all-MiniLM-L6-v2")
        )
    
        doc = pipe.run(result.markdown)
    
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(name="documents")
    
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
    
        return {
            
        }
    except Exception as e:
        raise RuntimeError(f"Error: {e}") from e

    # all_data = collection.get()
    # print(all_data)