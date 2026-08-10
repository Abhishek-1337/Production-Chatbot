from chonkie import SentenceTransformerEmbeddings
import chromadb


def retrieve_the_doc(query, user_id, document_id):
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="documents")

    embeddings = SentenceTransformerEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
    query_embedding = embeddings.embed(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        where={
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id},
            ]
        },
    )

    return "\n\n".join(results["documents"][0])