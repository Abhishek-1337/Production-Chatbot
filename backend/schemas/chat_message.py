from pydantic import BaseModel

class ChatQuestion(BaseModel):
    query: str
    conversation_id: str
