from ingest import ingest_doc
from chatbot import chat_with_doc

if __name__ == "__main__":
    # ingest_doc()
    chatbot_response = chat_with_doc(input("Ask a question about the TMS document: "))
    print("Chatbot response:", chatbot_response)