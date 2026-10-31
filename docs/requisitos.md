# Especificação de Requisitos — QA AI Platform

## 1. Objetivo e escopo

O sistema fornece uma plataforma web autenticada para duas formas de interação
com IA:

1. **chat generalista**, atendido por um modelo LLM local no Ollama; e
2. **consulta RAG**, baseada em documentos PDF locais, índice ChromaDB e
   serviços OpenAI para embeddings, reranking e geração da resposta final.

O escopo inclui backend FastAPI, frontend Flask, persistência SQLite, gestão de
usuários, histórico de conversas, consulta documental e os scripts locais de
inicialização/parada. O contrato HTTP detalhado está em
[endpoints.md](endpoints.md).

## 2. Atores e dependências externas

| Elemento | Responsabilidade |
| --- | --- |
| Usuário não autenticado | Registra-se e autentica-se. |
| Usuário autenticado | Usa chat, consulta documentos e visualiza seu histórico. |
| Administrador local | Configura `.env`, adiciona PDFs e opera os scripts. |
| Ollama | Fornece o chat local pelo endpoint `/api/generate`. |
| OpenAI | Fornece embeddings, reranking e geração do RAG. |
| ChromaDB | Armazena e consulta os vetores dos documentos. |
| SQLite | Armazena usuários, conversas e logs de consultas RAG. |

> **Fluxo de dados relevante:** o chat geral é enviado ao Ollama local. Já os
> trechos dos PDFs e as perguntas da funcionalidade RAG são enviados à OpenAI,
> conforme as configurações `OPENAI_API_KEY`, `EMBEDDING_MODEL` e
> `LLM_MODEL_RAG`.

## 3. Requisitos funcionais

| ID | Requisito | Critério de aceitação | Situação |
| --- | --- | --- | --- |
| RF01 | O sistema deve permitir registrar usuário com nome, e-mail e senha. | `POST /api/v1/auth/register` cria a conta e rejeita nome ou e-mail já existentes. | Implementado |
| RF02 | A tela de registro deve exigir confirmação de senha. | O envio é bloqueado enquanto `password` e `confirm-password` forem diferentes; o formulário exibe feedback visual. | Implementado |
| RF03 | O sistema deve validar dados de cadastro. | Nome possui 3 a 50 caracteres, e-mail é válido e senha possui pelo menos 8 caracteres; entradas inválidas retornam `422`. | Implementado |
| RF04 | O sistema deve autenticar por nome de usuário ou e-mail. | `POST /api/v1/auth/login` recebe formulário OAuth2 e devolve JWT Bearer quando as credenciais são válidas. | Implementado |
| RF05 | O sistema deve proteger recursos de cada usuário por JWT. | Rotas de perfil, chat, histórico e RAG exigem `Authorization: Bearer <token>` e retornam `401` sem credencial válida. | Implementado |
| RF06 | O usuário autenticado deve consultar seu perfil. | `GET /api/v1/users/me` devolve identificador, nome, e-mail e data de criação da conta autenticada. | Implementado |
| RF07 | O usuário autenticado deve enviar perguntas gerais ao LLM local. | `POST /api/v1/chat/ask` encaminha o prompt ao Ollama e retorna resposta, modelo, data e identificador da conversa. | Implementado |
| RF08 | O chat deve suportar resposta completa e streaming. | Com `stream=false`, a API retorna JSON; com `stream=true`, retorna eventos `text/event-stream` e um evento final com metadados. | Implementado |
| RF09 | O sistema deve persistir e isolar o histórico de chat por usuário. | Toda resposta concluída gera uma conversa SQLite; `GET /api/v1/chat/conversations` lista apenas conversas do usuário autenticado, com paginação e ordenação. | Implementado |
| RF10 | O sistema deve informar o modelo de chat configurado. | `GET /api/v1/chat/model` devolve o valor configurado em `OLLAMA_MODEL`. | Implementado |
| RF11 | O sistema deve listar PDFs disponíveis para consulta. | `GET /api/v1/rag/docs` lista os arquivos `.pdf` presentes em `documentos/` para usuários autenticados. | Implementado |
| RF12 | O sistema deve responder perguntas baseadas nos documentos indexados. | `POST /api/v1/rag/query` busca oito trechos, reclassifica-os, usa os quatro mais relevantes na geração e devolve resposta e fontes. | Implementado |
| RF13 | O RAG deve informar a origem textual da resposta. | Cada fonte retorna `documento`, `categoria` e `trecho` recuperado. | Implementado |
| RF14 | O sistema deve registrar auditoria de consultas RAG. | Pergunta, resposta e fontes serializadas são persistidas em `query_logs`, associadas ao usuário. | Implementado |
| RF15 | O sistema deve manter um índice RAG atualizado sem reprocessamento desnecessário. | Na inicialização, compara um manifesto de PDFs, modelo de embeddings e parâmetros de chunking; sem mudança, reutiliza o índice existente. | Implementado |
| RF16 | O sistema deve preservar um índice RAG utilizável durante falha de reindexação. | Uma nova versão é construída e validada antes de ser ativada; em erro, a versão anterior permanece ativa. | Implementado |
| RF17 | O frontend deve controlar acesso às páginas privadas. | Usuários sem token são redirecionados de `/dashboard` e `/rag` para `/login`; usuários autenticados veem navegação e logout. | Implementado |
| RF18 | O frontend deve permitir tema e preferência de streaming. | Tema e opção de streaming são gravados em `localStorage` e aplicados na interface. | Implementado |
| RF19 | O sistema deve expor documentação explorável da API. | FastAPI disponibiliza `/docs` e `/api/v1/openapi.json`. | Implementado |
| RF20 | O projeto deve disponibilizar comandos de operação local. | `scripts/start_services.sh` valida Ollama → backend → frontend; `scripts/stop_services.sh` encerra serviços das portas configuradas com verificação de processo. | Implementado |

## 4. Requisitos não funcionais

| ID | Requisito | Critério de aceitação | Situação |
| --- | --- | --- | --- |
| RNF01 | A solução deve manter separação entre interface e API. | Flask entrega páginas/templates e FastAPI concentra autenticação, dados e IA; a comunicação ocorre por HTTP. | Implementado |
| RNF02 | As senhas devem ser armazenadas com hash forte e nunca aparecer em logs. | Bcrypt é usado para hash e verificação; a rotina não escreve senha, hash ou resultado de autenticação em stdout/stderr. | Implementado |
| RNF03 | Configurações e segredos devem ser externos ao código-fonte. | Chaves, URLs, modelos e portas são lidos de `.env`; esse arquivo é ignorado pelo Git. | Implementado |
| RNF04 | A inicialização do banco deve ser determinística. | O diretório SQLite é criado antes do engine; a URL relativa é resolvida pela raiz do projeto; falha no banco aborta o startup. | Implementado |
| RNF05 | A indisponibilidade de RAG não deve corromper a base relacional nem o índice anterior. | Banco é dependência obrigatória; RAG é inicializado isoladamente e mantém a última versão válida em caso de erro. | Implementado |
| RNF06 | O índice vetorial deve evitar custo e latência desnecessários. | PDFs inalterados não geram novos embeddings; somente alterações de conteúdo/configuração disparam reindexação. | Implementado |
| RNF07 | Reindexações concorrentes não devem corromper o índice. | Um lock de arquivo serializa a construção do índice; novas versões são construídas em diretório próprio. | Implementado |
| RNF08 | A ativação de uma nova versão do índice deve ser recuperável. | O apontador `backend/chroma_rh/` é atualizado por symlink após validação; versões anteriores ficam em `backend/chroma_rh_versions/`. | Implementado |
| RNF09 | A aplicação deve produzir registros operacionais úteis sem expor segredos. | Backend registra startup, requisições, respostas, processamento de documentos, RAG e erros em `logs/backend.log`. | Implementado |
| RNF10 | A API deve validar entradas e limitar dados de chat. | Pydantic valida schemas; `prompt` do chat possui mínimo de 1 e máximo de 4.000 caracteres. | Implementado |
| RNF11 | Os testes devem ser reproduzíveis e independentes de serviços externos. | Testes usam SQLite em memória, mockam o ciclo de RAG e usam diretórios temporários para os testes de índice. | Implementado |
| RNF12 | O sistema deve oferecer feedback de formulário e compatibilidade com navegadores modernos. | Campos HTML usam `required`, `minlength`, autocomplete para senha nova e validação nativa/customizada. | Implementado |
| RNF13 | O ambiente de execução deve suportar sistema de arquivos compatível com lock `fcntl` e symlinks. | A implementação de versionamento do Chroma é validada no ambiente macOS/Linux. | Restrição atual |

## 5. Requisitos de configuração e implantação local

| Variável | Finalidade | Obrigatória para |
| --- | --- | --- |
| `DATABASE_URL` | URL SQLite (padrão aponta para `data/app.db`). | Backend |
| `JWT_SECRET_KEY` | Assinatura dos tokens JWT. | Backend seguro |
| `OLLAMA_BASE_URL` | Endereço do serviço Ollama. | Chat |
| `OLLAMA_MODEL` | Modelo local de chat. | Chat |
| `OPENAI_API_KEY` | Credencial de OpenAI. | RAG |
| `EMBEDDING_MODEL` | Modelo de embeddings. | RAG |
| `LLM_MODEL_RAG` | Modelo de geração/reranking RAG. | RAG |
| `BACKEND_PORT` / `FRONTEND_PORT` | Portas de publicação local. | Operação local |
| `API_BASE_URL` | Endereço da API consumida pelo frontend. | Frontend |

Para iniciar a cadeia de serviços, o operador deve executar:

```bash
./scripts/start_services.sh
```

O script interrompe a sequência se o Ollama não responder ou se o modelo
configurado não estiver instalado. Para encerrar os serviços locais:

```bash
./scripts/stop_services.sh
```

## 6. Critérios globais de aceite

Uma entrega local é considerada aceita quando:

1. Ollama está disponível e contém o modelo definido em `OLLAMA_MODEL`.
2. O backend inicia com banco SQLite acessível e responde ao endpoint de saúde.
3. O frontend abre na porta configurada e permite registrar, confirmar senha,
   autenticar e acessar o dashboard.
4. Uma pergunta de chat gera resposta e aparece no histórico do usuário.
5. Com chave OpenAI e PDFs válidos, uma pergunta RAG devolve resposta e fontes.
6. Uma reinicialização sem alteração nos PDFs reutiliza o índice, sem nova
   geração de embeddings.
7. A suíte `python3 -m pytest backend/tests -q` conclui sem falhas.

## 7. Limites e itens não cobertos pelo escopo atual

- O RAG retorna trecho, documento e categoria; o contrato atual não expõe a
  página do PDF como fonte estruturada.
- A saúde pública do RAG confirma que o backend responde, mas não verifica
  individualmente Ollama, OpenAI ou a integridade do índice.
- Não há meta numérica de disponibilidade, latência, recuperação de desastre ou
  retenção de logs definida no código atual.
- A política CORS atual permite qualquer origem; uma política restritiva por
  ambiente é necessária antes de expor a aplicação fora de ambiente local
  controlado.
- A renderização de Markdown e conteúdo vindo do RAG deve ser sanitizada antes
  de uma publicação em ambiente exposto, para reduzir risco de XSS.
