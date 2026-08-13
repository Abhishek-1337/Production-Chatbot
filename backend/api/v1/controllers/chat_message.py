import json

from anyio import to_thread

from schemas.chat_message import ChatQuestion
from services import doc_retrieval
from api.v1.controllers.document import agent


async def chat_message_stream(data: ChatQuestion, user_id: str):
    yield f"data: {json.dumps({'event': 'start'})}\n\n"

    context = await to_thread.run_sync(
        doc_retrieval.retrieve_the_doc,
        data.query.strip(),
        user_id,
        data.document_id,
    )
    user_prompt = f"Document context:\n{context}\n\nQuestion: {data.query.strip()}"

    async with agent.run_stream(user_prompt) as result:
        async for chunk in result.stream_text():
            yield f"data: {json.dumps({'event': 'token', 'content': chunk})}\n\n"

    yield f"data: {json.dumps({'event': 'done'})}\n\n"