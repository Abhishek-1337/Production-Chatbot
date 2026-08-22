from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from models.document import Document
from services import doc_retrieval, ingest, parser
from services.retry_utils import retry_llm
from schemas.document import Query
from pydantic_ai import Agent

agent = Agent(
  'openai-chat:gpt-4o-mini',
  system_prompt="You are an expert internal company AI assistant. Your job is to answer user questions using ONLY the provided document context. If the context does not contain the answer, say 'I cannot find that in the documents.' Do not invent facts outside of the provided context.",
)


@retry_llm
def _run_agent_sync(prompt: str):
    return agent.run_sync(prompt)

async def upload_document_controller(file: UploadFile, user_id: str, db: AsyncSession) -> dict:
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type is not allowed")

    document: Document = Document(
        user_id = user_id
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    text = parser.parser(file)
    ingest.ingest_doc(text, document.id, user_id)

    return {"message": "Document is successfully uploaded. You can start querying the data."}


def query_doc_controller(data: Query, user_id: str):
    context = doc_retrieval.retrieve_the_doc(data.query.strip(), user_id, data.document_id)
    user_prompt = f"Document context:\n{context}\n\nQuestion: {data.query.strip()}"
    result = _run_agent_sync(user_prompt)
    return {
        "result": result.output
    }
