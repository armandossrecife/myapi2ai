import logging
import os
from pydantic_settings import BaseSettings
from typing import Optional

# Configuração de diretório de logs
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "backend.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configuração de logging (Console + Arquivo)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
    handlers=[
        logging.StreamHandler(), # Envia para o terminal
        logging.FileHandler(LOG_FILE, encoding='utf-8') # Salva no arquivo
    ]
)

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./app.db"
    JWT_SECRET_KEY: str = "altere_esta_chave_em_producao_com_uma_string_aleatoria_segura"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FRONTEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 5000
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3"
    OLLAMA_TIMEOUT_SECONDS: int = 120
    OLLAMA_MAX_TOKENS: int = 2048

    class Config:
        env_file = ".env"

settings = Settings()

logger.info(f"Configurações carregadas. Modelo LLM: {settings.OLLAMA_MODEL}")
logger.info(f"Arquivo de logs configurado em: {LOG_FILE}")
