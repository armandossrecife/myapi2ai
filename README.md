# API de IA Genereativa integrada com Chat LLM e um Protótipo com RAG

A soluação é dividida em duas aplicações principais: o **Backend** (API FastAPI com RAG) e o **Frontend** (Interface Web em Flask). Ambos compartilham o mesmo ambiente virtual (venv).

Esta versão inclui um sistema de chat e um sistema de **RAG (Retrieval-Augmented Generation)** para consulta de documentos PDF utilizando LangChain, OpenAI e ChromaDB.

A solução também faz controle de autenticação de usuários e controla cada sessão de cada usuário logado.

Para mais detalhes consulte o arquivo [projeto.md](projeto.md).

## Pré-requisitos

### 1. Configuração do Ambiente (.env)
Crie um arquivo `.env` na raiz com as seguintes chaves:

```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/app.db
JWT_SECRET_KEY=sua_chave_secreta_super_segura
JWT_ALGORITHM=HS256

# Configurações de RAG & OpenAI
OPENAI_API_KEY=sk-xxxx... # OBRIGATÓRIO para RAG
LLM_MODEL_RAG=gpt-4o-mini

# Configurações do Chat (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3
OLLAMA_MAX_TOKENS=2048

# Configurações do Frontend
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=5001
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

O backend realiza a ingestão automática de documentos na inicialização.

1.  Coloque seus arquivos PDF na pasta `documentos/`.
2.  Inicie o servidor:

```bash
python -m backend.main
```

O sistema carregará os PDFs e criará o banco vetorial em `backend/chroma_rh/`.

## 2. Iniciando o Frontend

O frontend é uma interface moderna construída com Flask e Bootstrap 5.

1.  Em um novo terminal (com venv ativado), inicie a interface:

```bash
python frontend/app.py
```

2.  Acesse: [http://localhost:5001](http://localhost:5001)

---

## 🚀 Guia de Teste com Usuário Real

Para testar a integração completa das funcionalidades, siga este roteiro:

### Passo 1: Registro e Login
1. Na tela inicial do frontend, clique em **Registrar**.
2. Crie uma nova conta (ex: nome, e-mail e senha).
3. Após o registro bem-sucedido, você será redirecionado para o **Login**.
4. Entre com suas novas credenciais.

### Passo 2: Testando o Chat Generalista (Dashboard)
1. Após logar, você entrará no **Dashboard**.
2. Digite uma pergunta geral (ex: "Quem foi Alan Turing?").
3. A resposta será gerada via Ollama (Qwen3). 
4. Você pode ver o histórico de conversas sendo salvo na barra lateral esquerda.

### Passo 3: Testando a Consulta de Documentos (RAG)
1. No menu superior, clique em **Consultar RAG**.
2. Verifique na barra lateral se os documentos que você colocou na pasta `documentos/` aparecem listados.
3. Faça uma pergunta técnica baseada nos arquivos PDF (ex: "Quais os prazos para trancamento de matrícula?").
4. O sistema exibirá a resposta gerada pelo GPT-4o-mini e, logo abaixo, as **Fontes Consultadas** com os trechos extraídos do PDF.

---

## 3. Monitoramento e Logs

Os logs são exibidos no terminal e salvos em `logs/backend.log`. Utilizamos ícones para facilitar a identificação:
*   🌐 **[REQ]**: Requisições do frontend.
*   📄 **[DOCS]**: Status da ingestão e listagem de documentos.
*   🧠 **[LLM]**: Interações com o GPT-4o-mini (RAG) e Qwen3 (Chat).
*   💾 **[DB]**: Registro de consultas e histórico.

## 4. Executando os Testes Automatizados

```bash
export PYTHONPATH=$PYTHONPATH:. && pytest backend/tests
```

## Notas Adicionais
- **Banco de Dados**: O banco SQLite é inicializado em `data/app.db`.
- **Reranking**: O RAG utiliza uma etapa de reclassificação inteligente para garantir precisão nas respostas técnicas.
