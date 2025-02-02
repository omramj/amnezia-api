from flask import Flask

from controllers import ServerController


app = Flask(__name__)
server = ServerController()


@app.route("/xray/create-config")
def create_xray_config():
    return server.xray.create_user_config()


