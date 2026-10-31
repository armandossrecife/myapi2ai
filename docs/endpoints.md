# Referência de Endpoints da API

Esta referência descreve a API FastAPI publicada em `http://127.0.0.1:8000`.
A especificação interativa está disponível em [`/docs`](http://127.0.0.1:8000/docs) e
o contrato OpenAPI em [`/api/v1/openapi.json`](http://127.0.0.1:8000/api/v1/openapi.json).

## Visão geral

| Grupo | Finalidade | Rotas |
| --- | --- | --- |
| Autenticação | Criar conta e obter token JWT | `auth` |
| Chat | Conversar com o modelo configurado no Ollama e consultar o histórico | `chat` |
| Usuários | Obter o perfil da sessão atual | `users` |
| RAG | Consultar PDFs indexados e listar documentos | `rag` |

Todos os endpoints, exceto registro, login, modelo configurado e saúde, exigem
um token JWT. Depois de autenticar, envie-o no cabeçalho:

```http
Authorization: Bearer <access_token>
```

Nos exemplos abaixo, a variável `API` representa a base da API:

```bash
API=http://127.0.0.1:8000/api/v1
```

## Autenticação

### `POST /api/v1/auth/register`

Cria uma conta de usuário. O corpo é JSON. O `username` deve ter de 3 a 50
caracteres, o e-mail deve ser válido e a senha deve ter pelo menos 8 caracteres.

```bash
curl -X POST "$API/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "ana",
    "email": "ana@example.com",
    "password": "uma-senha-forte"
  }'
```

Resposta de sucesso (`201 Created`):

```json
{
  "message": "Usuário registrado com sucesso",
  "user_id": 1
}
```

O endpoint retorna `400` se o e-mail ou nome de usuário já estiver em uso e
`422` se a entrada não respeitar o schema.

### `POST /api/v1/auth/login`

Autentica por nome de usuário **ou** e-mail e retorna um JWT. Esta rota segue
o formato `application/x-www-form-urlencoded` do OAuth2, e não JSON.

```bash
curl -X POST "$API/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=ana&password=uma-senha-forte'
```

Resposta de sucesso (`200 OK`):

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Guarde `access_token` para as rotas protegidas. Credenciais inválidas geram
`400`; token ausente, inválido ou expirado gera `401` nas rotas protegidas.

## Chat Ollama

### `GET /api/v1/chat/model`

Retorna somente o nome do modelo Ollama configurado no backend. Não valida a
conectividade com o servidor Ollama.

```bash
curl "$API/chat/model"
```

Resposta (`200 OK`):

```json
{
  "model": "qwen3"
}
```

### `POST /api/v1/chat/ask`

Envia uma pergunta ao modelo configurado no Ollama. Requer JWT. O campo
`prompt` é obrigatório e aceita de 1 a 4.000 caracteres. `context` é opcional
e pode conter contexto anterior; `stream` seleciona resposta completa ou por
eventos SSE.

#### Resposta completa

```bash
curl -X POST "$API/chat/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Explique o que é uma API REST.",
    "stream": false
  }'
```

Resposta (`200 OK`):

```json
{
  "conversation_id": 12,
  "prompt": "Explique o que é uma API REST.",
  "response": "...",
  "timestamp": "30/10/2026 15:00:00",
  "model": "qwen3",
  "tokens_used": 142
}
```

A conversa é persistida no SQLite depois da geração. `tokens_used` é uma
estimativa baseada em palavras, não a contagem de tokens do modelo.

#### Streaming SSE

Envie `stream: true` para receber `text/event-stream`.

```bash
curl --no-buffer -X POST "$API/chat/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Resuma o conceito de RAG.","stream":true}'
```

Cada trecho possui o formato:

```text
data: {"text":"parte da resposta", "done":false}
```

O último evento confirma o encerramento e inclui os metadados da conversa:

```text
data: {"text":"", "done":true, "conversation_id":13, "timestamp":"...", "tokens_used":120}
```

Se o Ollama estiver indisponível, a resposta não streaming retorna `503`; no
fluxo streaming, o erro é enviado como um evento SSE com o campo `error`.

### `GET /api/v1/chat/conversations`

Lista o histórico de conversas do usuário autenticado. Cada conta vê apenas as
suas próprias conversas.

| Parâmetro | Local | Padrão | Descrição |
| --- | --- | --- | --- |
| `limit` | query | `50` | Quantidade de itens, até `200`. |
| `offset` | query | `0` | Número de itens a pular para paginação. |
| `sort` | query | `desc` | `asc` ordena da mais antiga para a mais nova; qualquer outro valor resulta em ordem decrescente. |

```bash
curl "$API/chat/conversations?limit=20&offset=0&sort=desc" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta (`200 OK`):

```json
{
  "total": 1,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 12,
      "prompt": "Explique o que é uma API REST.",
      "response": "...",
      "created_at": "30/10/2026 15:00:00"
    }
  ]
}
```

## Usuários

### `GET /api/v1/users/me`

Retorna o perfil do usuário autenticado.

```bash
curl "$API/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta (`200 OK`):

```json
{
  "username": "ana",
  "email": "ana@example.com",
  "id": 1,
  "created_at": "2026-10-30T15:00:00+00:00",
  "conversations_count": 1
}
```

`conversations_count` pode não ser fornecido, pois é opcional no contrato.

## RAG — consulta aos documentos

O RAG pesquisa os PDFs presentes em `documentos/`, recupera trechos relevantes
do ChromaDB e gera uma resposta usando a configuração de OpenAI definida no
backend. Requer índice vetorial inicializado e token JWT.

### `POST /api/v1/rag/query`

Consulta a base de documentos indexada. O corpo JSON deve conter `question`.

```bash
curl -X POST "$API/rag/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Quais são as regras de trancamento de matrícula?"}'
```

Resposta (`200 OK`):

```json
{
  "resposta": "...",
  "fontes": [
    {
      "documento": "REGULAMENTO_GERAL_177.2012_atualizada_2023.pdf",
      "categoria": "regimento",
      "trecho": "..."
    }
  ]
}
```

Cada item em `fontes` identifica o arquivo, a categoria atribuída durante a
ingestão e o trecho recuperado. Falhas internas de índice, de modelo ou de
processamento são retornadas como `500`; entradas fora do schema geram `422`.

### `GET /api/v1/rag/docs`

Lista os nomes de todos os PDFs encontrados no diretório configurado para os
documentos. Requer JWT.

```bash
curl "$API/rag/docs" \
  -H "Authorization: Bearer $TOKEN"
```

Resposta (`200 OK`):

```json
{
  "files": [
    "REGULAMENTO_GERAL_177.2012_atualizada_2023.pdf"
  ]
}
```

### `GET /api/v1/rag/health`

Endpoint público de verificação básica de disponibilidade da API RAG.

```bash
curl "$API/rag/health"
```

Resposta (`200 OK`):

```json
{
  "status": "ok"
}
```

Esse endpoint confirma que o backend está respondendo, mas não confirma
isoladamente a conectividade com OpenAI, a existência do índice ChromaDB ou a
disponibilidade do Ollama.

## Erros e validação

| Código | Significado comum |
| --- | --- |
| `400` | Credenciais incorretas, ou e-mail/nome de usuário já existente. |
| `401` | Token JWT ausente, inválido ou expirado. |
| `422` | Corpo, campo ou parâmetro de consulta fora do schema esperado. |
| `500` | Falha ao processar uma consulta RAG. |
| `503` | Ollama indisponível ou não foi possível gerar uma resposta de chat. |

## Fluxo recomendado de integração

1. Registre uma conta em `POST /auth/register`.
2. Faça login em `POST /auth/login` e armazene `access_token` em `TOKEN`.
3. Consulte `GET /users/me` para validar o token.
4. Use `POST /chat/ask` para o chat geral via Ollama ou `POST /rag/query` para
   perguntas baseadas nos PDFs indexados.
5. Use `GET /chat/conversations` para recuperar o histórico persistido.
