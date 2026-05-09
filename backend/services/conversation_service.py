from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.models.conversation import Conversation
from backend.schemas.chat import AskRequest

def create_conversation(db: Session, user_id: int, prompt: str, response: str, model_used: str, tokens_prompt: int = None, tokens_response: int = None) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        prompt=prompt,
        response=response,
        model_used=model_used,
        tokens_prompt=tokens_prompt,
        tokens_response=tokens_response
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def get_conversations_by_user(db: Session, user_id: int, limit: int = 50, offset: int = 0, sort: str = "desc") -> tuple[list[Conversation], int]:
    query = db.query(Conversation).filter(Conversation.user_id == user_id)
    total = query.count()
    
    if sort == "asc":
        query = query.order_by(Conversation.created_at.asc())
    else:
        query = query.order_by(Conversation.created_at.desc())
        
    conversations = query.offset(offset).limit(limit).all()
    return conversations, total
