#!/bin/bash
#
#
# This script is based on an install script of the OutlineVPN project:
#
# https://raw.githubusercontent.com/Jigsaw-Code/outline-server/master/src/server_manager/install_scripts/install_server.sh
#
# https://github.com/Jigsaw-Code/outline-server


# I/O conventions for this script:
# - Ordinary status messages are printed to STDOUT
# - STDERR is only used in the event of a fatal error
# - Detailed logs are recorded to this FULL_LOG, which is preserved if an error occurred.
# - The most recent error is stored in LAST_ERROR, which is never preserved.
FULL_LOG="$(mktemp -t amnezia-api_logXXXXXXXXXX)"
LAST_ERROR="$(mktemp -t amnezia-api_last_errorXXXXXXXXXX)"
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

# Check to see if docker is installed.
function verify_curl_installed() {
  if command_exists curl; then
    return 0
  fi
  log_error "NOT INSTALLED"
  echo "Curl is not installed... Please, isntall curl with 'sudo apt install curl' and then run this script again."
  exit 1
}

function verify_docker_running() {
  local STDERR_OUTPUT
  STDERR_OUTPUT="$(docker info 2>&1 >/dev/null)"
  local -ir RET=$?
  if (( RET == 0 )); then
    return 0
  elif [[ "${STDERR_OUTPUT}" == *"Is the docker daemon running"* ]]; then
    start_docker
    return
  fi
  return "${RET}"
}

function fetch() {
  curl --silent --show-error --fail "$@"
}

function get_random_port {
  local -i num=0  # Init to an invalid value, to prevent "unbound variable" errors.
  until (( 1024 <= num && num < 65536)); do
    num=$(( RANDOM + (RANDOM % 2) * 32768 ));
  done;
  echo "${num}";
}

function remove_docker_container() {
  docker rm -f "$1" >&2
}

function handle_docker_container_conflict() {
  local -r CONTAINER_NAME="$1"
  local -r EXIT_ON_NEGATIVE_USER_RESPONSE="$2"
  local PROMPT="The container name \"${CONTAINER_NAME}\" is already in use by another container. This may happen when running this script multiple times."
  if [[ "${EXIT_ON_NEGATIVE_USER_RESPONSE}" == 'true' ]]; then
    PROMPT="${PROMPT} We will attempt to remove the existing container and restart it. Would you like to proceed?"
  else
    PROMPT="${PROMPT} Would you like to replace this container? If you answer no, we will proceed with the remainder of the installation."
  fi
  if ! confirm "${PROMPT}"; then
    if ${EXIT_ON_NEGATIVE_USER_RESPONSE}; then
      exit 0
    fi
    return 0
  fi
  if run_step "Removing ${CONTAINER_NAME} container" "remove_${CONTAINER_NAME}_container" ; then
    log_start_step "Restarting ${CONTAINER_NAME}"
    "start_${CONTAINER_NAME}"
    return $?
  fi
  return 1
}

function set_hostname() {
  # These are URLs that return the client's apparent IP address.
  # We have more than one to try in case one starts failing
  # (e.g. https://github.com/Jigsaw-Code/outline-server/issues/776).
  local -ar urls=(
    'https://icanhazip.com/'
    'https://ipinfo.io/ip'
  )
  for url in "${urls[@]}"; do
    PUBLIC_HOSTNAME="$(fetch --ipv4 "${url}")" && return
  done
  echo "Failed to determine the server's IP address." >&2
  return 1
}

function create_persisted_state_dir() {
  readonly STATE_DIR="${AMNEZIAAPI_DIR}/persisted-state"
  mkdir -p "${STATE_DIR}"
  chmod ug+rwx,g+s,o-rwx "${STATE_DIR}"
}

function safe_base64() {
  # Implements URL-safe base64 of stdin, stripping trailing = chars.
  # Writes result to stdout.
  # TODO: this gives the following errors on Mac:
  #   base64: invalid option -- w
  #   tr: illegal option -- -
  local url_safe
  url_safe="$(base64 -w 0 - | tr '/+' '_-')"
  echo -n "${url_safe%%=*}"  # Strip trailing = chars
}

function generate_secret_url_string() {
  SECRET_URL_STRING="$(head -c 16 /dev/urandom | safe_base64)"
  readonly SECRET_URL_STRING
}

function generate_certificate() {
  # Generate self-signed cert and store it in the persistent state directory.
  local -r CERTIFICATE_NAME="${STATE_DIR}/amnezia-api-selfsigned"
  readonly API_CERTIFICATE_FILE="${CERTIFICATE_NAME}.crt"
  readonly API_PRIVATE_KEY_FILE="${CERTIFICATE_NAME}.key"
  declare -a openssl_req_flags=(
    -x509 -nodes -days 36500 -newkey rsa:4096
    -subj "/CN=${PUBLIC_HOSTNAME}"
    -keyout "${API_PRIVATE_KEY_FILE}" -out "${API_CERTIFICATE_FILE}"
  )
  openssl req "${openssl_req_flags[@]}" >&2
}

function generate_certificate_fingerprint() {
  # Add a tag with the SHA-256 fingerprint of the certificate.
  # Example format: "SHA256 Fingerprint=BD:DB:C9:A4:39:5C:B3:4E:6E:CF:18:43:61:9F:07:A2:09:07:37:35:63:67"
  local CERT_OPENSSL_FINGERPRINT
  CERT_OPENSSL_FINGERPRINT="$(openssl x509 -in "${API_CERTIFICATE_FILE}" -noout -sha256 -fingerprint)" || return
  # Example format: "BDDBC9A4395CB34E6ECF1843619F07A2090737356367"
  local CERT_HEX_FINGERPRINT
  CERT_HEX_FINGERPRINT="$(echo "${CERT_OPENSSL_FINGERPRINT#*=}" | tr -d :)" || return
}

function build_nginx_container() {
  readonly NGINX_DIR="${AMNEZIAAPI_DIR}/nginx"
  mkdir -p "${NGINX_DIR}" 2> /dev/null
  NGINX_CONFIG="${NGINX_DIR}/nginx.conf"

  cat <<-EOF > "${NGINX_CONFIG}"
# Source: https://docs.gunicorn.org/en/latest/deploy.html
worker_processes 1;

user nobody nogroup;
error_log  /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
  worker_connections 1024; # increase if you have lots of clients
  accept_mutex off; # set to 'on' if nginx worker_processes > 1
}

http {
  include mime.types;
  default_type application/octet-stream;
  access_log /var/log/nginx/access.log combined;
  sendfile on;

  upstream app_server {
    server 127.0.0.1:42674 fail_timeout=0;
  }

  server {
    # if no Host match, close the connection to prevent host spoofing
    listen 42673 default_server;
    return 444;
  }

  server {
    listen ${API_PORT} deferred;
    client_max_body_size 4G;

    server_name ${PUBLIC_HOSTNAME};

    keepalive_timeout 5;

    location / {
      try_files \$uri @proxy_to_app;
    }

    location @proxy_to_app {
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
      proxy_set_header Host \$http_host;
      # we don't want nginx trying to do something clever with
      # redirects, we set the Host: header above already.
      proxy_redirect off;
      proxy_pass http://127.0.0.1:42674;
    }

  }
}
EOF


  cat <<-EOF > "${NGINX_DIR}/Dockerfile"

FROM nginx
COPY ./nginx.conf /etc/nginx/nginx.conf

EOF

  local -r BUILD_SCRIPT="${NGINX_DIR}/build_container.sh"
  cat <<-EOF > "${BUILD_SCRIPT}"
# This script builds nginx reverse proxy for amnezia-api container.
docker build -t nginx-amnezia-api ${NGINX_DIR}
EOF

  chmod +x "${BUILD_SCRIPT}"
  # Declare then assign. Assigning on declaration messes up the return code.
  local STDERR_OUTPUT
  STDERR_OUTPUT="$({ "${BUILD_SCRIPT}" >/dev/null; } 2>&1)" && return
  readonly STDERR_OUTPUT
  log_error "FAILED"
  log_error "${STDERR_OUTPUT}"
  exit 1
}

function start_nginx_container() {
  local -r START_SCRIPT="${NGINX_DIR}/start_container.sh"
  cat <<-EOF > "${START_SCRIPT}"

set -eu

docker stop "nginx-${CONTAINER_NAME}" 2> /dev/null || true
docker rm -f "nginx-${CONTAINER_NAME}" 2> /dev/null || true

docker run -d -it --rm -p ${API_PORT}:${API_PORT} --name=nginx-${CONTAINER_NAME} nginx-amnezia-api
EOF

  chmod +x "${START_SCRIPT}"
  # Declare then assign. Assigning on declaration messes up the return code.
  local STDERR_OUTPUT
  STDERR_OUTPUT="$({ "${START_SCRIPT}" >/dev/null; } 2>&1)" && return
  readonly STDERR_OUTPUT
  log_error "FAILED"
  log_error "${STDERR_OUTPUT}"
  exit 1
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

function install_amnezia_api() {

  umask 0007

  export CONTAINER_NAME="amnezia-api"
  export IMAGE_NAME="omramj/amnezia-api-dev:0.0.2"

  run_step "Verifying that Docker is installed" verify_docker_installed
  run_step "Verifying that Docker daemon is running" verify_docker_running
  run_step "Verifying that curl is installed" verify_curl_installed

  export AMNEZIAAPI_DIR="/opt/amnezia-api"
  mkdir -p "${AMNEZIAAPI_DIR}"
  chmod u+s,ug+rwx,o-rwx "${AMNEZIAAPI_DIR}"

  #Setting API port
  API_PORT=$(get_random_port)
  readonly API_PORT

  run_step "Setting PUBLIC_HOSTNAME to external IP" set_hostname
  readonly PUBLIC_HOSTNAME

  readonly SECRET_URL_STRING_PATH="${AMNEZIAAPI_DIR}/secret-url-string.txt}"

  # If $SECRET_URL_STRING is already populated, make a backup before clearing it.
  if [[ -s "${SECRET_URL_STRING_PATH}" ]]; then
    # Note we can't do "mv" here as do_install_server.sh may already be tailing
    # this file.
    cp "${SECRET_URL_STRING_PATH}" "${SECRET_URL_STRING_PATH}.bak" && true > "${SECRET_URL_STRING_PATH}"
  fi
  
  # Make a directory for persistent state
  run_step "Creating persistent state dir" create_persisted_state_dir
  run_step "Generating secret url string" generate_secret_url_string
  run_step "Generating TLS certificate" generate_certificate
  run_step "Generating SHA-256 certificate fingerprint" generate_certificate_fingerprint

  # TODO(dborkan): if the script fails after docker run, it will continue to fail
  # as the names shadowbox and watchtower will already be in use.  Consider
  # deleting the container in the case of failure (e.g. using a trap, or
  # deleting existing containers on each run).
  run_step "Building nginx container for reverse proxy" build_nginx_container
  run_step "Starting nginx container" start_nginx_container
  run_step "Starting Amnezia-API" start_amnezia_api_container

  cat <<END_OF_SERVER_OUTPUT

CONGRATULATIONS! Your Amnezia-API backend is up and running.

To access the api, use the following link:

http://${PUBLIC_HOSTNAME}:${API_PORT}/${SECRET_URL_STRING}/status

Make sure that port ${API_PORT} is open in your firewall.

END_OF_SERVER_OUTPUT
} # end of install_amnezia_api

function main()
{
  
  install_amnezia_api
}

main
