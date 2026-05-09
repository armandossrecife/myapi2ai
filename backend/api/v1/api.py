from fastapi import APIRouter
from backend.api.v1.endpoints import auth, chat, users, rag

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
