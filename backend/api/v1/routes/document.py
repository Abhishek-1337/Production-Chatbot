from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from models.user import User
from api.v1.controllers.document import upload_document_controller

router = APIRouter(prefix="/documents", tags=["documents"])


async def get_current_user(request: Request) -> User:
    return request.state.user


@router.post("/upload")
async def upload_document(
    _current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    return await upload_document_controller(file, str(_current_user.id))
