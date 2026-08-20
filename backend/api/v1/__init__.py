from fastapi import APIRouter
from api.v1.routes import chat_message, user, auth, document, conversation

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(document.router)
api_router.include_router(chat_message.router)
api_router.include_router(conversation.router)
