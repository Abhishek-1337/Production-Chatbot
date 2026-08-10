from pydantic import BaseModel

class Query(BaseModel):
    query: str
    document_id: str

