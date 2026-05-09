import logging
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

# Configuração de diretório de logs
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "backend.log"

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configuração de logging (Console + Arquivo)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Permite campos extras no .env sem quebrar a aplicação
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./app.db"
    JWT_SECRET_KEY: str = "altere_esta_chave_em_producao_com_uma_string_aleatoria_segura"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FRONTEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 5000
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # Ollama (Mantido para compatibilidade se necessário)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3"
    
    # RAG & OpenAI
    OPENAI_API_KEY: str = ""
    DOCUMENTS_DIR: Path = PROJECT_ROOT / "documentos"
    CHROMA_PERSIST_DIR: Path = PROJECT_ROOT / "backend" / "chroma_rh"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL_RAG: str = "gpt-4o-mini"

settings = Settings()

logger.info(f"Configurações carregadas com sucesso.")
logger.info(f"Projeto Root: {PROJECT_ROOT}")
