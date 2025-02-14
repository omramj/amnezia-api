import logging
import logging.config

from flask import Flask, request, abort

from amnezia_api.settings import settings
from amnezia_api.controllers import ServerController
import amnezia_api.utils as utils


logging.config.dictConfig(settings.get_logging_config())
logger = logging.getLogger("amnezia_api")
ctl_logger = logging.getLogger("controller")


def create_app() -> Flask:
    app = Flask("amnezia_api")

    
    @app.route(f"/{settings.secret_url_string}/xray/create-config", methods=["GET", "POST"])
    def create_xray_config():
        if request.method == "POST":
            client_name = request.form["client-name"]
            if client_name is None:
                abort(400)

            try:
                return _create_config(utils.ContainerName.XRAY, client_name)
            except Exception as e:
                ctl_logger.error(e)
                abort(500)
        else:
            return "Hello there"


    @app.route(f"/{settings.secret_url_string}/wireguard/create-config", methods=["GET", "POST"])
    def create_wireguard_config():
        if request.method == "POST":
            client_name = request.form["client-name"]
            if client_name is None or client_name == "":
                abort(400)

            try:
                return _create_config(utils.ContainerName.WIREGUARD, client_name)
            except Exception as e:
                ctl_logger.error(e)
                abort(500)
        else:
            return "Hello there"


    @app.route(f"/{settings.secret_url_string}/amnezia-wg/create-config", methods=["GET", "POST"])
    def create_amnezia_wg_config():
        if request.method == "POST":
            client_name = request.form["client-name"]
            if client_name is None:
                abort(400)

            try:
                return _create_config(utils.ContainerName.AMNEZIA_WG, client_name)
            except Exception as e:
                ctl_logger.error(e)
                abort(500)
        else:
            return "Hello there"


    @app.route(f"/{settings.secret_url_string}/status", methods=["GET"])
    def show_status_message():
        return "This message indicates that amnezia-api backend is accessible"


    def _create_config(container_name: utils.ContainerName, client_name: str) -> str:

        logger.info(f"New '/create-config' request: type: {container_name.name}, client-name: '{client_name}'.")
        server = ServerController(container_name)
        key = server.configurator.create_config(client_name)
        logger.info("Config created.")
        return utils.convert_string_to_base64_vpn_link(key)


    return app
