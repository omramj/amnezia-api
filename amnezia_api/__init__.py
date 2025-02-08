from flask import Flask, request

from amnezia_api.settings import settings
from amnezia_api.controllers import ServerController


def create_app() -> Flask:
    app = Flask(__name__)
    server = ServerController()

    
    @app.route(f"/{settings.secret_url_string}/xray/create-config", methods=["GET", "POST"])
    def create_xray_config():
        if request.method == "POST":
            return server.xray.create_user_config()
        else:
            return "Hello there"


    @app.route(f"/{settings.secret_url_string}/status", methods=["GET"])
    def show_status_message():
        return "This message indicates that amnezia-api backend is accessible"

    return app
