import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.api.v1.api import api_router
from backend.db.init_db import init_db
from backend.services.rag_service import rag_pipeline

logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador de ciclo de vida: Garante ingestão de documentos em cada startup.
    """
    logger.info("🚀 [STARTUP] Iniciando Backend FastAPI...")
    try:
        # 1. Carregar Banco de Dados
        init_db()
        
        # 2. Conectar com Modelos LLM
        rag_pipeline.initialize_models()
        
        # 3. Carregar e Processar Documentos (Garante dados atualizados)
        documentos = rag_pipeline.load_documents()
        if documentos:
            rag_pipeline.create_vectorstore(documentos)
            
        logger.info("✅ [STARTUP] Sistema inicializado e pronto para requisições.")
    except Exception as e:
        logger.critical(f"❌ [STARTUP] Falha crítica na inicialização: {e}", exc_info=True)
    
    yield
    
    logger.info("🛑 [SHUTDOWN] Backend encerrado.")

app = FastAPI(
    title="RAG Backend - Regimentos", 
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para log detalhado de requisições do frontend.
    """
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    
    logger.info(f"🌐 [REQ] {request.method} {request.url.path} | IP: {client_host}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        log_msg = f"✅ [RES] {response.status_code} | Tempo: {duration:.3f}s"
        
        if response.status_code >= 400:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
            
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ [ERR] Falha na requisição | Tempo: {duration:.3f}s | Erro: {e}", exc_info=True)
        raise

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app", 
        host=settings.BACKEND_HOST, 
        port=settings.BACKEND_PORT, 
        reload=False,
        log_level="info"
    )
