from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile
from database import get_db
from models.user import User
from schemas.document import Query
from services.auth import get_current_user
from api.v1.controllers.document import query_doc_controller, upload_document_controller

router = APIRouter(prefix="/document", tags=["document"])

@router.post("/upload")
async def upload_document(
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    return await upload_document_controller(file, str(_current_user.id), db)

@router.post("/query")
def query_doc(data: Query, _current_user: Annotated[User, Depends(get_current_user)]):
    return query_doc_controller(data, str(_current_user.id))