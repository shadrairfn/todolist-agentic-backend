from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.controllers.agentic_ai import jalankan_agent
from app.core.security import get_current_user
from app.models.user import User

class ChatRequest(BaseModel):
    message: str

router = APIRouter(
    prefix="/agentic",      
    tags=["Agentic"]        
)

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    user_id = str(current_user.id)
    jawaban_ai = jalankan_agent(request.message, user_id=user_id)
    return {"reply": jawaban_ai}