import json
import time
import logging
from fastapi import APIRouter, HTTPException, Depends
from backend.api.deps import SessionDep
from backend.schemas.rag import QueryRequest, QueryResponse, SourceItem, HealthResponse
from backend.services.rag_service import rag_pipeline
from backend.models.query_log import QueryLog

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
def ask_question(req: QueryRequest, db: SessionDep):
    """
    Endpoint de RAG para consulta a documentos PDF (regimentos).
    """
    logger.info(f"📩 [QUERY] Nova pergunta RAG: '{req.question[:70]}...'")
    
    try:
        start = time.time()
        resposta, fontes = rag_pipeline.query(req.question)
        duration = time.time() - start

        # Formata fontes para o schema de resposta
        fontes_list = [
            SourceItem(
                documento=doc.metadata.get("documento", "Desconhecido"),
                categoria=doc.metadata.get("categoria", "geral"),
                trecho=doc.page_content
            ) for doc in fontes
        ]

        # Salva o log da consulta no banco de dados
        log_entry = QueryLog(
            question=req.question,
            answer=resposta,
            sources=json.dumps([f.model_dump() for f in fontes_list], ensure_ascii=False)
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        logger.info(f"💾 [DB] Consulta RAG salva. ID: {log_entry.id} | Processamento: {duration:.2f}s")
        
        return QueryResponse(resposta=resposta, fontes=fontes_list)
        
    except Exception as e:
        logger.error(f"❌ [QUERY] Falha ao processar consulta RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")
