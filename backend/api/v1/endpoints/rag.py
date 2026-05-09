import json
import time
import logging
import glob
import os
from fastapi import APIRouter, HTTPException, Depends
from backend.api.deps import SessionDep, CurrentUser
from backend.schemas.rag import QueryRequest, QueryResponse, SourceItem, HealthResponse
from backend.services.rag_service import rag_pipeline
from backend.models.query_log import QueryLog
from backend.core.config import settings

logger = logging.getLogger("backend.api.rag")

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def ask_question(req: QueryRequest, db: SessionDep, current_user: CurrentUser):
    """
    Endpoint de RAG para consulta a documentos PDF (regimentos).
    Requer autenticação.
    """
    logger.info(f"📩 [QUERY] Usuário '{current_user.username}' (ID: {current_user.id}) iniciou consulta RAG: '{req.question[:50]}...'")
    
    try:
        start_time = time.time()
        
        # Chama o pipeline de RAG (que já possui seus próprios logs internos)
        resposta, fontes = rag_pipeline.query(req.question)
        
        duration = time.time() - start_time

        # Formata fontes para o schema de resposta
        fontes_list = [
            SourceItem(
                documento=doc.metadata.get("documento", "Desconhecido"),
                categoria=doc.metadata.get("categoria", "geral"),
                trecho=doc.page_content
            ) for doc in fontes
        ]

        # Salva o log da consulta no banco de dados associado ao usuário
        try:
            log_entry = QueryLog(
                user_id=current_user.id,
                question=req.question,
                answer=resposta,
                sources=json.dumps([f.model_dump() for f in fontes_list], ensure_ascii=False)
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            logger.info(f"💾 [DB] Resposta RAG gerada e salva para '{current_user.username}'. ID Log: {log_entry.id} | Duração: {duration:.2f}s")
        except Exception as db_err:
            db.rollback()
            logger.error(f"⚠️ [DB] Falha ao salvar log de consulta, mas a resposta será enviada: {db_err}")

        return QueryResponse(resposta=resposta, fontes=fontes_list)
        
    except Exception as e:
        db.rollback()
        # Log seguro (evita acessar current_user se a sessão estiver instável)
        user_info = f"ID: {getattr(current_user, 'id', 'unknown')}"
        logger.error(f"❌ [QUERY] Erro crítico na consulta RAG para usuário {user_info}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar a consulta RAG.")

@router.get("/docs")
def list_documents(current_user: CurrentUser):
    """
    Lista os nomes dos arquivos PDF disponíveis na pasta de documentos.
    Requer autenticação para log de auditoria.
    """
    logger.info(f"📄 [DOCS] Usuário '{current_user.username}' solicitou lista de documentos disponíveis.")
    
    docs_dir = settings.DOCUMENTS_DIR
    if not os.path.exists(docs_dir):
        logger.warning(f"⚠️ [DOCS] Pasta de documentos não encontrada: {docs_dir}")
        return {"files": []}
        
    files = glob.glob(os.path.join(docs_dir, "*.pdf"))
    file_names = [os.path.basename(f) for f in files]
    
    logger.info(f"✅ [DOCS] Retornando {len(file_names)} documentos para '{current_user.username}'.")
    return {"files": file_names}

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")
