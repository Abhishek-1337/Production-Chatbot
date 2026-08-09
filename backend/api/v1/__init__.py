from fastapi import APIRouter
from api.v1.routes import user, auth

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(user.router)