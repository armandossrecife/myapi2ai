# Chat LLM - Protótipo

A aplicação é dividida em serviços principais: o **Backend** (API FastAPI) e o **Frontend** (Interface Web em Flask). Ambos compartilham o mesmo ambiente virtual (venv).

Para rodá-los localmente, você precisará de dois terminais separados.

## Pré-requisitos

Arquivo .env
```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/app.db
JWT_SECRET_KEY=sua_chave_secreta_super_segura
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=5000
API_BASE_URL=http://localhost:8000/api/v1

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_MAX_TOKENS=2048
```
Crie o venv como uv:

```bash
uv venv
```

Certifique-se de que o ambiente virtual está ativado. Em qualquer novo terminal que você abrir para rodar os comandos, ative-o com:

```bash
source .venv/bin/activate
```

Instale as dependências com uv:

```bash
uv pip install -r requirements.txt
```

## 1. Iniciando o servidor da API (Backend)

Em um terminal com o `.venv` ativado, inicie o backend usando o módulo do python. Ele será executado na porta `8000` por padrão.

```bash
# Inicia a API FastAPI (Uvicorn)
python -m backend.main
```

Você verá nos logs que o servidor foi iniciado com sucesso mostrando algo como: `Uvicorn running on http://0.0.0.0:8000`.

A documentação interativa da API também pode ser acessada em [http://localhost:8000/docs](http://localhost:8000/docs).

## 2. Executando os Testes (Backend)

Os testes automatizados utilizam o `pytest` e validam os endpoints de autenticação, usuários e chat (incluindo streaming e mocks para o LLM).

Para rodar os testes, primeiro instale as dependências de teste:

```bash
uv pip install pytest pytest-asyncio pytest-mock
```

Em seguida, execute o comando abaixo na raiz do projeto:

```bash
export PYTHONPATH=$PYTHONPATH:. && pytest backend/tests
```

## Notas Adicionais
- **Banco de Dados**: O banco SQLite é inicializado automaticamente na pasta `data/app.db` na primeira vez que o backend roda.
- **LLM/Ollama**: Certifique-se de que o serviço do Ollama (`http://localhost:11434`) esteja rodando na sua máquina e com o modelo definido (ex: `qwen3`) baixado para o chat funcionar completamente.

## Mais detalhes 

Detalhes do projeto disponível em https://github.com/armandossrecife/myqaai/blob/main/projeto.md
