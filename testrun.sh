#!/bin/bash

# This script will build and run nginx reverse proxy container and the amnezia-api container. 
# This script is intended only for development. Production-ready install script to be written in future.
set -e

readonly HOSTNAME="91.246.41.209"
readonly AMNEZIAAPI_DIR="./.amnezia-api-dev"
readonly NGINX_DIR="${AMNEZIAAPI_DIR}/nginx"

mkdir -p "${AMNEZIAAPI_DIR}" 2> /dev/null
mkdir -p "${NGINX_DIR}" 2> /dev/null

cp -r ./amnezia_api "${AMNEZIAAPI_DIR}/amnezia_api"
cp ./wsgi.py "${AMNEZIAAPI_DIR}/wsgi.py"

function create_nginx_config() {
  NGINX_CONFIG="${NGINX_DIR}/nginx.conf"
  touch ${NGINX_CONFIG}
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
    listen 42673 deferred;
    client_max_body_size 4G;

    # set the correct host(s) for your site
    server_name ${HOSTNAME};

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
    return 
}

function create_nginx_dockerfile() {

  cat <<-EOF > "${AMNEZIAAPI_DIR}/nginx/Dockerfile"

FROM nginx
COPY ./nginx.conf /etc/nginx/nginx.conf

EOF
    return 
}

function build_nginx_container() {

docker build -t nginx-amnezia-api-test ${AMNEZIAAPI_DIR}/nginx
    return 
}

function run_nginx_container() {
docker run -d -it --rm -p 42673:42673 --name=nginx-amnezia-api-test nginx-amnezia-api-test
    return 
}

function create_amnezia_api_dockerfile() {
    DOCKERFILE="${AMNEZIAAPI_DIR}/Dockerfile"

    cat <<-EOF > "${DOCKERFILE}"
FROM python:3.13

WORKDIR /opt/amnezia_api

ENV SECRET_URL_STRING="dev"
RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir docker
RUN pip install --no-cache-dir gunicorn

COPY ./amnezia_api ./amnezia_api
COPY wsgi.py .

CMD ["gunicorn", "-w", "4", "-b", "127.0.0.1:42674", "wsgi:app"]
EOF
    return 
}

function build_amnezia_api() {

    docker build -t amnezia-api-test "${AMNEZIAAPI_DIR}"
    return 
}

function run_amnezia_api() {
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --network container:nginx-amnezia-api-test --name=amnezia-api-test amnezia-api-test
    return 
}

function cleanup() {
docker stop nginx-amnezia-api-test
remove_temp_amnezia_api_dir
}

function remove_temp_amnezia_api_dir() {
rm -rf "${AMNEZIAAPI_DIR}"
}

function main() {

    trap cleanup SIGINT
    trap remove_temp_amnezia_api_dir EXIT
    create_nginx_config
    create_nginx_dockerfile
    build_nginx_container
    run_nginx_container

    create_amnezia_api_dockerfile
    build_amnezia_api
    run_amnezia_api

}

main

