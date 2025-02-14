#!/bin/bash

# This script updates amnezia-api container

# I/O conventions for this script:
# - Ordinary status messages are printed to STDOUT
# - STDERR is only used in the event of a fatal error
# - Detailed logs are recorded to this FULL_LOG, which is preserved if an error occurred.
# - The most recent error is stored in LAST_ERROR, which is never preserved.
FULL_LOG="$(mktemp -t amnezia-api_update_logXXXXXXXXXX)"
LAST_ERROR="$(mktemp -t amnezia-api_update_last_errorXXXXXXXXXX)"

export CONTAINER_NAME="amnezia-api"
export IMAGE_NAME="omramj/amnezia-api-dev:0.2.0"


readonly FULL_LOG LAST_ERROR

set -e

function log_command() {
  # Direct STDOUT and STDERR to FULL_LOG, and forward STDOUT.
  # The most recent STDERR output will also be stored in LAST_ERROR.
  "$@" > >(tee -a "${FULL_LOG}") 2> >(tee -a "${FULL_LOG}" > "${LAST_ERROR}")
}

function log_error() {
  local -r ERROR_TEXT="\033[0;31m"  # red
  local -r NO_COLOR="\033[0m"
  echo -e "${ERROR_TEXT}$1${NO_COLOR}"
  echo "$1" >> "${FULL_LOG}"
}

function run_step() {
  local -r msg="$1"
  log_start_step "${msg}"
  shift 1
  if log_command "$@"; then
    echo "OK"
  else
    # Propagates the error code
    return
  fi
}

function log_start_step() {
  local -r str="> $*"
  local -ir lineLength=47
  echo -n "${str}"
  local -ir numDots=$(( lineLength - ${#str} - 1 ))
  if (( numDots > 0 )); then
    echo -n " "
    for _ in $(seq 1 "${numDots}"); do echo -n .; done
  fi
  echo -n " "
}

function command_exists {
  command -v "$@" &> /dev/null
}

# Check to see if docker is installed.
function verify_docker_installed() {
  if command_exists docker; then
    return 0
  fi
  log_error "NOT INSTALLED"
  echo "Docker is not installed... Please, set up your server with AmneziaVPN app fist, then try running this script again."
  exit 1
}

function verify_docker_running() {
  local STDERR_OUTPUT
  STDERR_OUTPUT="$(docker info 2>&1 >/dev/null)"
  local -ir RET=$?
  if (( RET == 0 )); then
    return 0
  elif [[ "${STDERR_OUTPUT}" == *"Is the docker daemon running"* ]]; then
    log_error "NOT RUNNING"
    return 1
  fi
  return "${RET}"
}

function start_amnezia_api_container() {
  local -r START_SCRIPT="${STATE_DIR}/start_container.sh"
  cat <<-EOF > "${START_SCRIPT}"
# This script starts the Amnezia-API container.

set -eu

docker stop "${CONTAINER_NAME}" 2> /dev/null || true
docker rm -f "${CONTAINER_NAME}" 2> /dev/null || true

docker_command=(
  docker
  run
  -d
  --name "${CONTAINER_NAME}" --restart always
  --network container:nginx-${CONTAINER_NAME}

  # Connect to docker API socket
   -v /var/run/docker.sock:/var/run/docker.sock

  # Use log rotation. See https://docs.docker.com/config/containers/logging/configure/.
  --log-driver local

  # Env var for sercet url string
  -e "SECRET_URL_STRING=${SECRET_URL_STRING}"
  -e "LOGGING_MODE=PROD"

  "${IMAGE_NAME}"
)
"\${docker_command[@]}"
EOF
  chmod +x "${START_SCRIPT}"
  # Declare then assign. Assigning on declaration messes up the return code.
  local STDERR_OUTPUT
  STDERR_OUTPUT="$({ "${START_SCRIPT}" >/dev/null; } 2>&1)" && return
  readonly STDERR_OUTPUT
  log_error "FAILED"
  if docker_container_exists "${CONTAINER_NAME}"; then
    handle_docker_container_conflict "${CONTAINER_NAME}" true
    return
  else
    log_error "${STDERR_OUTPUT}"
    return 1
  fi
}

function update_amnezia_api() {

  run_step "Verifying that Docker is installed" verify_docker_installed
  run_step "Verifying that Docker daemon is running" verify_docker_running

  readonly AMNEZIAAPI_DIR="/opt/amnezia-api"
  readonly STATE_DIR="${AMNEZIAAPI_DIR}/persisted-state"

  readonly SECRET_URL_STRING_PATH="${AMNEZIAAPI_DIR}/secret-url-string.txt"
  readonly SECRET_URL_STRING="$(cat ${SECRET_URL_STRING_PATH})"

  run_step "Updating Amnezia-API" start_amnezia_api_container

  cat <<END_OF_SERVER_OUTPUT

CONGRATULATIONS! Your Amnezia-API backend is up to date.


END_OF_SERVER_OUTPUT
} # end of install_amnezia_api

function main()
{
  
  update_amnezia_api
}

main
