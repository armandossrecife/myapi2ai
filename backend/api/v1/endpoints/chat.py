import json
import logging
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from backend.api.deps import SessionDep, CurrentUser
from backend.schemas.chat import AskRequest, AskResponse, ConversationsResponse, ConversationItem, ModelInfo
from backend.services import conversation_service
from backend.services.llm_client import generate_response
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/model", response_model=ModelInfo)
async def get_model_info():
    """
    Retorna o nome do modelo LLM configurado no backend.
    """
    return ModelInfo(model=settings.OLLAMA_MODEL)

@router.post("/ask")
async def ask_question(request: AskRequest, current_user: CurrentUser, db: SessionDep):
    logger.info(f"Usuário {current_user.username} (ID: {current_user.id}) enviou uma pergunta. Stream: {request.stream}")
    
    # Envia pergunta ao LLM
    if not request.stream:
        response_text = await generate_response(prompt=request.prompt, context=request.context, stream=False)
        if not response_text:
            logger.error(f"Ollama retornou resposta vazia para o usuário {current_user.id}")
            raise HTTPException(status_code=503, detail="Não foi possível gerar uma resposta.")

        # Salva no banco de dados
        tokens_p = len(request.prompt.split())
        tokens_r = len(response_text.split())
        
        conv = conversation_service.create_conversation(
            db=db,
            user_id=current_user.id,
            prompt=request.prompt,
            response=response_text,
            model_used=settings.OLLAMA_MODEL,
            tokens_prompt=tokens_p,
            tokens_response=tokens_r
        )
        
        logger.info(f"Conversa {conv.id} salva. Tokens: P={tokens_p}, R={tokens_r}")
        
        return AskResponse(
            conversation_id=conv.id,
            prompt=conv.prompt,
            response=conv.response,
            timestamp=conv.formatted_timestamp,
            model=conv.model_used,
            tokens_used=(tokens_p + tokens_r)
        )
    
    # Modo Streaming (SSE)
    async def event_generator():
        full_response = ""
        try:
            generator = await generate_response(prompt=request.prompt, context=request.context, stream=True)
            async for chunk in generator:
                full_response += chunk
                # Envia o chunk no formato SSE
                yield f"data: {json.dumps({'text': chunk, 'done': False})}\n\n"
            
            # Após o loop, salva no banco e envia o sinal de finalização
            tokens_p = len(request.prompt.split())
            tokens_r = len(full_response.split())
            
            conv = conversation_service.create_conversation(
                db=db,
                user_id=current_user.id,
                prompt=request.prompt,
                response=full_response,
                model_used=settings.OLLAMA_MODEL,
                tokens_prompt=tokens_p,
                tokens_response=tokens_r
            )
            
            logger.info(f"Conversa stream {conv.id} salva para usuário {current_user.id}. Total tokens: {tokens_p + tokens_r}")
            
            final_data = {
                'text': '',
                'done': True,
                'conversation_id': conv.id,
                'timestamp': conv.formatted_timestamp,
                'tokens_used': (tokens_p + tokens_r)
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            logger.error(f"Erro durante o streaming para usuário {current_user.id}: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/conversations", response_model=ConversationsResponse)
def read_conversations(
    current_user: CurrentUser, 
    db: SessionDep,
    limit: int = Query(50, le=200),
    offset: int = 0,
    sort: str = "desc"
):
    logger.info(f"Usuário {current_user.id} solicitou histórico de conversas (limit={limit}, offset={offset})")
    conversations, total = conversation_service.get_conversations_by_user(
        db=db, user_id=current_user.id, limit=limit, offset=offset, sort=sort
    )
    
    items = []
    for c in conversations:
        items.append(ConversationItem(
            id=c.id,
            prompt=c.prompt,
            response=c.response,
            created_at=c.formatted_timestamp
        ))
        
    return ConversationsResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items
    )
