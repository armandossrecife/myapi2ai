# QA AI Platform

Plataforma web de perguntas e respostas com autenticação, chat generalista via
Ollama local e consulta documental RAG baseada em PDFs.

## Funcionalidades

- Registro de usuários com confirmação de senha e validação no navegador.
- Login por nome de usuário ou e-mail, com autenticação JWT.
- Chat com modelo configurado no Ollama, com resposta completa ou streaming SSE.
- Histórico de conversas separado por usuário.
- Consulta RAG a PDFs em `documentos/`, com resposta e fontes recuperadas.
- Índice ChromaDB versionado: PDFs inalterados reutilizam o índice sem gerar
  novos embeddings.
- Scripts para iniciar e parar os serviços locais com verificação de
  dependências.

## Arquitetura

```text
Navegador
    │
    ▼
Frontend Flask :5001 ── HTTP/JWT ──► Backend FastAPI :8000
                                         ├── SQLite: usuários, histórico e auditoria
                                         ├── Ollama local: chat generalista
                                         └── RAG: PDFs + ChromaDB + OpenAI
```

O chat geral usa o Ollama configurado em `OLLAMA_BASE_URL`. O RAG usa OpenAI
para embeddings, reranking e geração final; portanto, perguntas RAG e trechos
relevantes dos PDFs são enviados a esse serviço externo.

## Pré-requisitos

- Python e `uv` para criar o ambiente virtual e instalar dependências.
- Ollama em execução local, com o modelo definido em `OLLAMA_MODEL` instalado.
- Chave OpenAI válida para usar o RAG.
- `curl` e `lsof` para os scripts de operação local.

## Configuração

Crie `.env` na raiz do projeto. Não versione esse arquivo nem compartilhe suas
chaves.

```env
# Backend e banco de dados
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/app.db

# Autenticação
JWT_SECRET_KEY=gere_uma_chave_aleatoria_longa
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Chat local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT_SECONDS=120

# RAG
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL_RAG=gpt-4o-mini

# Frontend
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=5001
API_BASE_URL=http://localhost:8000/api/v1
```

O backend normaliza URLs SQLite relativas com base na raiz do projeto e cria o
diretório `data/` automaticamente.

## Instalação

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Instale o modelo Ollama, se necessário:

```bash
ollama pull qwen3
```

## Início rápido

Com o ambiente virtual ativado e o Ollama em execução, inicie a aplicação pela
sequência validada:

```bash
source .venv/bin/activate
./scripts/start_services.sh
```

O script verifica, nesta ordem:

1. se o serviço Ollama responde;
2. se o modelo configurado está instalado;
3. se o backend FastAPI está disponível — ou o inicia;
4. se o frontend Flask está disponível — ou o inicia.

Endereços locais:

| Serviço | Endereço |
| --- | --- |
| Frontend | http://127.0.0.1:5001 |
| Backend | http://127.0.0.1:8000 |
| Documentação OpenAPI | http://127.0.0.1:8000/docs |
| Saúde do backend | http://127.0.0.1:8000/api/v1/rag/health |

Os logs gerados pelo script ficam em `logs/backend-startup.log` e
`logs/frontend-startup.log`.

### Início manual

Em terminais separados, execute:

```bash
# Terminal 1: Ollama, caso ele ainda não seja um serviço do sistema
ollama serve
```

```bash
# Terminal 2: backend
source .venv/bin/activate
python -m backend.main
```

```bash
# Terminal 3: frontend
source .venv/bin/activate
python frontend/app.py
```

## Uso da interface

1. Abra o frontend e escolha **Registrar**.
2. Informe nome, e-mail, senha e confirmação de senha.
3. Faça login e acesse o dashboard.
4. Use o dashboard para chat geral via Ollama.
5. Use **Consultar RAG** para perguntas baseadas nos PDFs em `documentos/`.

O frontend grava o token JWT e as preferências de tema/streaming no
`localStorage` do navegador.

## RAG e ciclo de vida do índice

Na inicialização, o backend gera um manifesto com hashes dos PDFs, modelo de
embeddings e parâmetros de fragmentação.

- Sem mudanças: a versão Chroma existente é aberta e reutilizada.
- Com mudanças: uma nova versão é construída e validada antes de ser ativada.
- Em caso de falha: o índice anterior permanece preservado e é reutilizado.

O apontador da versão ativa fica em `backend/chroma_rh/`; as versões ficam em
`backend/chroma_rh_versions/`. Esses diretórios são estado local e não devem
ser versionados.

## Encerramento

```bash
./scripts/stop_services.sh
```

O script verifica os processos nas portas 8000 e 5001, confirma que pertencem
ao projeto e tenta encerramento gracioso antes de usar força como último
recurso.

## Testes

```bash
python3 -m pytest backend/tests -q
```

Os testes usam SQLite em memória e mockam o ciclo de vida RAG para não chamar a
OpenAI nem alterar o índice local. A suíte cobre autenticação, usuários, chat,
RAG, preparação do SQLite, ausência de vazamento de senhas, manifesto e
recuperação do índice.

## Estrutura do projeto

```text
backend/                 API FastAPI, modelos, serviços e testes
  api/v1/endpoints/      Rotas de autenticação, usuário, chat e RAG
  services/              Cliente Ollama, RAG, autenticação e conversas
  tests/                 Testes automatizados
frontend/                Aplicação Flask, templates, CSS e JavaScript
documentos/              PDFs usados pela base RAG
docs/                    Requisitos e referência de endpoints
scripts/                 Scripts de inicialização e parada
data/                    Banco SQLite local (gerado)
logs/                    Logs locais (gerados)
```

## Documentação adicional

- [Documentação técnica do projeto](projeto.md)
- [Requisitos funcionais e não funcionais](docs/requisitos.md)
- [Referência de endpoints](docs/endpoints.md)

## Segurança e limitações atuais

- Use uma `JWT_SECRET_KEY` forte e mantenha `.env` fora do Git.
- As senhas são armazenadas com bcrypt e não são registradas nos logs.
- Antes de expor a aplicação fora de ambiente local controlado, restrinja CORS
  por ambiente e sanitize conteúdo Markdown retornado por modelos/documentos
  para reduzir risco de XSS.
- O endpoint de saúde confirma a resposta do backend, mas não testa
  individualmente Ollama, OpenAI ou a integridade semântica do índice RAG.
- O versionamento de índice usa `fcntl` e symlinks; o ambiente alvo atual é
  macOS/Linux.
