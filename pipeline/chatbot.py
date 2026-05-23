import chromadb
from chonkie.embeddings import SentenceTransformerEmbeddings

def retrieve_the_doc(query):
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="tms-doc")

    embeddings = SentenceTransformerEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
    query_embedding = embeddings.embed(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=3)

    return "\n\n".join(results["documents"][0])
