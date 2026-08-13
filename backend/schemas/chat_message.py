from pydantic import BaseModel

class ChatQuestion(BaseModel):
    query: str
    document_id: str