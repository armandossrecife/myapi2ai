# Chat LLM - Protótipo com RAG

A aplicação é dividida em serviços principais: o **Backend** (API FastAPI com RAG) e o **Frontend** (Interface Web em Flask). Ambos compartilham o mesmo ambiente virtual (venv).

Esta versão inclui um sistema de **RAG (Retrieval-Augmented Generation)** para consulta de documentos PDF utilizando LangChain, OpenAI e ChromaDB.

## Pré-requisitos

### 1. Configuração do Ambiente (.env)
Crie um arquivo `.env` na raiz com as seguintes chaves (substitua pelos seus valores):

```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./app.db
JWT_SECRET_KEY=sua_chave_secreta_super_segura
JWT_ALGORITHM=HS256

# Configurações de RAG & OpenAI
OPENAI_API_KEY=sk-xxxx... # OBRIGATÓRIO para RAG
LLM_MODEL_RAG=gpt-4o-mini

# Configurações do Frontend
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=5000
API_BASE_URL=http://localhost:8000/api/v1
```

### 2. Ambiente Virtual e Dependências
Utilizamos o `uv` para gestão rápida de pacotes.

```bash
# Criar venv
uv venv

# Ativar venv
source .venv/bin/activate

# Instalar dependências
uv pip install -r requirements.txt
```

## 1. Iniciando o Backend

O backend agora realiza a ingestão automática de documentos na inicialização.

1.  Coloque seus arquivos PDF na pasta `documentos/` (criada automaticamente se não existir).
2.  Inicie o servidor:

```bash
python -m backend.main
```

**O que acontece no startup:**
*   O sistema carrega os PDFs da pasta `documentos/`.
*   Cria/Atualiza o banco vetorial ChromaDB em `backend/chroma_rh/`.
*   Monitora o progresso através de logs visuais no terminal.

A documentação interativa da API está em [http://localhost:8000/docs](http://localhost:8000/docs).

## 2. Monitoramento e Logs

Os logs são exibidos no terminal e salvos automaticamente em:
*   `logs/backend.log`

Os logs utilizam ícones para facilitar a identificação:
*   🌐 **[REQ]**: Requisições do frontend.
*   📄 **[DOCS]**: Status da ingestão de documentos.
*   🧠 **[LLM]**: Interações com a inteligência artificial.
*   ❌ **[ERR]**: Erros críticos.

## 3. Executando os Testes

Os testes validam a autenticação, o chat e o novo pipeline de RAG (utilizando mocks para não gastar créditos da API).

```bash
export PYTHONPATH=$PYTHONPATH:. && pytest backend/tests
```

## Notas Adicionais
- **Banco de Dados**: O banco SQLite (`app.db`) é inicializado automaticamente.
- **Reranking**: O sistema utiliza uma etapa de reclassificação via LLM para garantir que apenas os trechos mais relevantes dos documentos sejam usados na resposta final.

## Mais detalhes 
Consulte o arquivo [projeto.md](projeto.md) para detalhes da arquitetura e requisitos técnicos.
