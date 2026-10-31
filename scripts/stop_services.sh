#!/usr/bin/env bash
# Para os serviços locais deste projeto: FastAPI (8000) e Flask (5001).

set -euo pipefail

readonly GRACEFUL_TIMEOUT_SECONDS=8

info() {
  printf '[INFO] %s\n' "$*"
}

success() {
  printf '[OK] %s\n' "$*"
}

warning() {
  printf '[AVISO] %s\n' "$*" >&2
}

find_listener_pids() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

command_for_pid() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

parent_pid_for() {
  local pid="$1"
  ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' '
}

add_unique_pid() {
  local pid="$1"
  local existing

  for existing in "${TARGET_PIDS[@]:-}"; do
    [[ "$existing" == "$pid" ]] && return
  done
  TARGET_PIDS+=("$pid")
}

add_matching_ancestors() {
  local pid="$1"
  local expected_command="$2"
  local parent_pid parent_command

  while true; do
    parent_pid="$(parent_pid_for "$pid")"
    if [[ -z "$parent_pid" || "$parent_pid" == "1" ]]; then
      return 0
    fi

    parent_command="$(command_for_pid "$parent_pid")"
    if [[ "$parent_command" == *"$expected_command"* ]]; then
      add_unique_pid "$parent_pid"
    fi

    pid="$parent_pid"
  done
}

wait_for_processes_to_stop() {
  local elapsed=0
  local pid still_running

  while (( elapsed < GRACEFUL_TIMEOUT_SECONDS )); do
    still_running=false
    for pid in "${TARGET_PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        still_running=true
        break
      fi
    done

    [[ "$still_running" == false ]] && return
    sleep 1
    ((elapsed += 1))
  done
}

stop_service() {
  local name="$1"
  local port="$2"
  local expected_command="$3"
  local pid command
  TARGET_PIDS=()

  info "Procurando $name na porta $port..."

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command="$(command_for_pid "$pid")"

    if [[ "$command" != *"$expected_command"* ]]; then
      warning "A porta $port está sendo usada pelo PID $pid, mas o comando não corresponde a $name."
      warning "Comando encontrado: ${command:-indisponível}"
      warning "Nenhum processo será encerrado por segurança."
      return
    fi

    info "$name encontrado: PID $pid ($command)"
    add_unique_pid "$pid"
    add_matching_ancestors "$pid" "$expected_command"
  done < <(find_listener_pids "$port")

  if (( ${#TARGET_PIDS[@]} == 0 )); then
    success "$name já está parado."
    return
  fi

  info "Enviando SIGTERM para $name (PIDs: ${TARGET_PIDS[*]})..."
  kill -TERM "${TARGET_PIDS[@]}" 2>/dev/null || true
  wait_for_processes_to_stop

  local remaining=()
  for pid in "${TARGET_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      remaining+=("$pid")
    fi
  done

  if (( ${#remaining[@]} > 0 )); then
    warning "$name não encerrou dentro de ${GRACEFUL_TIMEOUT_SECONDS}s. Enviando SIGKILL para: ${remaining[*]}"
    kill -KILL "${remaining[@]}" 2>/dev/null || true
  fi

  if [[ -z "$(find_listener_pids "$port")" ]]; then
    success "$name foi parado; a porta $port está livre."
  else
    warning "$name ainda possui processo escutando na porta $port. Verifique manualmente com: lsof -nP -iTCP:$port -sTCP:LISTEN"
  fi
}

info "Iniciando parada dos serviços do projeto..."
stop_service "backend FastAPI" "8000" "backend.main"
stop_service "frontend Flask" "5001" "frontend/app.py"
success "Processo de parada concluído."
