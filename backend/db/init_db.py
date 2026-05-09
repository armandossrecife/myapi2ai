import logging
from sqlalchemy.orm import Session
from backend.db.session import engine, SessionLocal
from backend.models.base import Base
from backend.core.config import settings

# Importa todos os modelos para garantir que eles sejam criados no banco de dados
from backend.models import user, conversation

logger = logging.getLogger(__name__)

def init_db() -> None:
    # Oculta a URL completa do banco se contiver credenciais (embora aqui seja SQLite)
    db_type = settings.DATABASE_URL.split(":")[0]
    logger.info(f"Iniciando conexão com o banco de dados ({db_type})...")
    
    try:
        # Apenas cria as tabelas se elas não existirem
        logger.info("Verificando/Criando tabelas iniciais...")
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso.")
    except Exception as e:
        logger.error(f"Erro crítico ao inicializar o banco de dados: {str(e)}")
        raise e

if __name__ == "__main__":
    init_db()
