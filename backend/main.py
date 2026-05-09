import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.api.v1.api import api_router
from backend.db.init_db import init_db

# Pega o logger já configurado no config.py
logger = logging.getLogger("backend.main")

app = FastAPI(title="QA LLM API", openapi_url="/api/v1/openapi.json")

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to settings.FRONTEND_HOST
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logar todas as requisições HTTP recebidas.
    """
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    log_msg = f"REQ: {request.method} {request.url.path} | STATUS: {response.status_code} | CLIENT: {client_host} | TIME: {process_time:.2f}ms"
    
    if response.status_code >= 400:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)
        
    return response

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
def on_startup():
    logger.info("Startup: Iniciando aplicação FastAPI...")
    init_db()
    logger.info("Startup: Aplicação pronta para receber requisições.")

if __name__ == "__main__":
    import uvicorn
    # Adicionado log_level="info" para garantir que o uvicorn mostre nossos logs
    uvicorn.run(
        "backend.main:app", 
        host=settings.BACKEND_HOST, 
        port=settings.BACKEND_PORT, 
        reload=False,
        log_level="info"
    )
