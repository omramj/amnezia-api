from flask import Flask, request

from amnezia_api.settings import settings
from amnezia_api.controllers import ServerController


def create_app() -> Flask:
    app = Flask(__name__)

    
    @app.route(f"/{settings.secret_url_string}/xray/create-config", methods=["GET", "POST"])
    def create_xray_config():
        if request.method == "POST":
            client_name = request.form["client-name"]
            if client_name is None:
                #TODO
                raise Exception("Client name can not be None")

            server = ServerController()
            #TODO
            assert server.xray is not None
            
            key = server.xray.create_config(client_name)
            return key
        else:
            return "Hello there"


    @app.route(f"/{settings.secret_url_string}/wireguard/create-config", methods=["GET", "POST"])
    def create_wireguard_config():
        if request.method == "POST":
            client_name = request.form["client-name"]
            if client_name is None:
                #TODO
                raise Exception("Client name can not be None")

            server = ServerController()
            #TODO
            assert server.wireguard is not None
            
            key = server.wireguard.create_config(client_name)
            return key
        else:
            return "Hello there"


    @app.route(f"/{settings.secret_url_string}/status", methods=["GET"])
    def show_status_message():
        return "This message indicates that amnezia-api backend is accessible"

    return app
