import chromadb
from chonkie.embeddings import SentenceTransformerEmbeddings
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

agent = Agent(  
  'openai:gpt-4o-mini',
  instructions="You are an expert internal company AI assistant. Your job is to answer user questions using ONLY the provided document context below. If the context does not contain the answer, say 'I cannot find that in the documents.Do not invent facts outside of the provided context.",
)

def retrieve_the_doc(query):
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="tms-doc")

    embeddings = SentenceTransformerEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
    query_embedding = embeddings.embed(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=3)

    return "\n\n".join(results["documents"][0])

def chat_with_doc(query):
    context = retrieve_the_doc(query)
    prompt = f"Context: {context}\n\nQuestion: {query}\nAnswer:"
    result = agent.run_sync(prompt)
    return result.output

