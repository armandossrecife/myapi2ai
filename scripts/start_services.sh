#!/usr/bin/env bash
# Inicia os serviços locais deste projeto respeitando a cadeia:
# Ollama -> backend FastAPI -> frontend Flask.

set -euo pipefail

readonly PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ENV_FILE="$PROJECT_ROOT/.env"
readonly LOG_DIR="$PROJECT_ROOT/logs"
readonly BACKEND_LOG="$LOG_DIR/backend-startup.log"
readonly FRONTEND_LOG="$LOG_DIR/frontend-startup.log"
readonly CHECK_TIMEOUT_SECONDS=90

info() {
  printf '[INFO] %s\n' "$*"
}

success() {
  printf '[OK] %s\n' "$*"
}

warning() {
  printf '[AVISO] %s\n' "$*" >&2
}

error() {
  printf '[ERRO] %s\n' "$*" >&2
}

read_env_value() {
  local key="$1"
  local fallback="$2"
  local value

  [[ -f "$ENV_FILE" ]] || {
    printf '%s\n' "$fallback"
    return
  }

  value="$(awk -F= -v key="$key" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "$ENV_FILE")"
  printf '%s\n' "${value:-$fallback}"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    error "Comando obrigatório não encontrado: $1"
    exit 1
  }
}

is_port_in_use() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_url() {
  local service_name="$1"
  local url="$2"
  local log_file="$3"
  local attempt

  info "Aguardando $service_name responder em $url..."
  for ((attempt = 1; attempt <= CHECK_TIMEOUT_SECONDS; attempt++)); do
    if curl --fail --silent --show-error --connect-timeout 2 --max-time 5 "$url" >/dev/null 2>&1; then
      printf '\n'
      success "$service_name está disponível."
      return 0
    fi
    printf '.'
    sleep 1
  done

  printf '\n'
  error "$service_name não respondeu após ${CHECK_TIMEOUT_SECONDS}s."
  if [[ -f "$log_file" ]]; then
    error "Últimas linhas de $log_file:"
    tail -n 30 "$log_file" >&2 || true
  fi
  return 1
}

check_ollama() {
  local ollama_tags

  info "Verificando o serviço Ollama em $OLLAMA_BASE_URL..."
  if ! ollama_tags="$(curl --fail --silent --show-error --connect-timeout 2 --max-time 5 "$OLLAMA_BASE_URL/api/tags")"; then
    error "Ollama não está disponível. Inicie o Ollama e execute o script novamente."
    return 1
  fi

  success "Ollama está disponível."
  if [[ "$ollama_tags" != *"\"name\":\"$OLLAMA_MODEL"* ]]; then
    error "O modelo configurado '$OLLAMA_MODEL' não foi encontrado no Ollama."
    error "Instale-o com: ollama pull $OLLAMA_MODEL"
    return 1
  fi
  success "Modelo Ollama configurado encontrado: $OLLAMA_MODEL"
}

start_backend() {
  local health_url="http://127.0.0.1:${BACKEND_PORT}/api/v1/rag/health"

  info "Verificando o backend FastAPI..."
  if curl --fail --silent --show-error --connect-timeout 2 --max-time 5 "$health_url" >/dev/null 2>&1; then
    success "Backend FastAPI já está disponível na porta $BACKEND_PORT."
    return 0
  fi

  if is_port_in_use "$BACKEND_PORT"; then
    error "A porta $BACKEND_PORT está ocupada por um processo que não responde como este backend."
    error "Verifique com: lsof -nP -iTCP:$BACKEND_PORT -sTCP:LISTEN"
    return 1
  fi

  info "Iniciando backend FastAPI na porta $BACKEND_PORT..."
  nohup python3 -m backend.main >"$BACKEND_LOG" 2>&1 &
  info "Backend iniciado em segundo plano (PID $!). Log: $BACKEND_LOG"
  wait_for_url "Backend FastAPI" "$health_url" "$BACKEND_LOG"
}

start_frontend() {
  local frontend_url="http://127.0.0.1:${FRONTEND_PORT}/"

  info "Verificando o frontend Flask..."
  if curl --fail --silent --show-error --connect-timeout 2 --max-time 5 "$frontend_url" >/dev/null 2>&1; then
    success "Frontend Flask já está disponível na porta $FRONTEND_PORT."
    return 0
  fi

  if is_port_in_use "$FRONTEND_PORT"; then
    error "A porta $FRONTEND_PORT está ocupada por um processo que não responde como este frontend."
    error "Verifique com: lsof -nP -iTCP:$FRONTEND_PORT -sTCP:LISTEN"
    return 1
  fi

  info "Iniciando frontend Flask na porta $FRONTEND_PORT..."
  FRONTEND_HOST="$FRONTEND_HOST" FRONTEND_PORT="$FRONTEND_PORT" API_BASE_URL="$API_BASE_URL" \
    nohup python3 frontend/app.py >"$FRONTEND_LOG" 2>&1 &
  info "Frontend iniciado em segundo plano (PID $!). Log: $FRONTEND_LOG"
  wait_for_url "Frontend Flask" "$frontend_url" "$FRONTEND_LOG"
}

main() {
  require_command curl
  require_command lsof
  require_command python3

  [[ -f "$ENV_FILE" ]] || warning ".env não encontrado; valores padrão serão utilizados."
  mkdir -p "$PROJECT_ROOT/data" "$LOG_DIR"

  cd "$PROJECT_ROOT"

  info "Iniciando verificação das dependências da aplicação..."
  info "Ordem: Ollama -> backend FastAPI -> frontend Flask"

  check_ollama
  start_backend
  start_frontend

  success "Aplicação iniciada corretamente."
  success "Backend:  http://127.0.0.1:$BACKEND_PORT"
  success "Frontend: http://127.0.0.1:$FRONTEND_PORT"
}

OLLAMA_BASE_URL="$(read_env_value 'OLLAMA_BASE_URL' 'http://localhost:11434')"
OLLAMA_MODEL="$(read_env_value 'OLLAMA_MODEL' 'qwen3')"
BACKEND_PORT="$(read_env_value 'BACKEND_PORT' '8000')"
FRONTEND_HOST="$(read_env_value 'FRONTEND_HOST' '0.0.0.0')"
FRONTEND_PORT="$(read_env_value 'FRONTEND_PORT' '5001')"
API_BASE_URL="$(read_env_value 'API_BASE_URL' "http://localhost:${BACKEND_PORT}/api/v1")"

main "$@"
