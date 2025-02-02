from flask import Flask, request

from settings import settings
from controllers import ServerController


app = Flask(__name__)
server = ServerController()


@app.route(f"/{settings.secret_url_string}/xray/create-config", methods=["POST"])
def create_xray_config():
    if request.method == "POST":
        return server.xray.create_user_config()
    else:
        return "Hello there"
