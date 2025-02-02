import json
import uuid

from controllers import XrayContainerController
from settings import settings


class Configurator:
    def __init__(self):
        pass

    
    def _read_text_file(self, filepath: str) -> str:
        with open(filepath, "r") as file:
            return file.read()


    def _replace_variables_in_config(self, template: str, variables_values: dict[str, str]) -> str:

        config = template

        for var, value in variables_values.items():
            if config.find(var) == -1:
                # TODO logging and exception
                print("The variable {var} not found in the template.")
                raise Exception

            config = config.replace(var, value)

        return config


class XrayConfigurator(Configurator):
# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/xray_configurator.cpp

    def __init__(self, container: XrayContainerController):
        self.container = container
        pass


    def _prepare_server_config(self) -> uuid.UUID:

        # Generate new UUID for client
        client_id = uuid.uuid1()

        # Validate server config structure

        server_config_dict = json.loads(self.container.get_server_config())

        inbounds = server_config_dict.get("inbounds")

        # TODO logging and proper exceptions
        if inbounds is None:
            print("The 'inbouds' field is missing in the server config.")
            raise Exception

        if len(inbounds) == 0:
            print("'inbounds' field is empty.")
            raise Exception
        
        settings = inbounds[0].get("settings")

        if settings is None:
            print("The 'settings' field is missing in the server inbound config.")
            raise Exception

        clients = settings.get("clients")

        if clients is None:
            print("The 'clients' field is missing in the server inbound settings config.")
            raise Exception

        # Add a new user to the config
        client_config = {"id": str(client_id), "flow": "xtls-rprx-vision"}
        clients.append(client_config)
        settings["clients"] = clients
        inbounds[0]["settings"] = settings
        server_config_dict["inbounds"] = inbounds
        new_server_config = json.dumps(server_config_dict, indent=4)

        # Load the new config into the container
        self.container.update_server_config(new_server_config)

        # Restart container
        self.container.restart_container()

        return client_id


    def create_user_config(self) -> str:
        client_id = self._prepare_server_config()
        variables = {
                "$CLIENT_ID": str(client_id),
                "$SERVER_PUBLIC_KEY": self.container.get_server_public_key(),
                "$SERVER_IP": self.container.get_server_public_ip(),
                "$SHORT_ID": self.container.get_server_short_id_key()
                }
        user_config = self._replace_variables_in_config(
                self._get_client_config_template(),
                variables)
                
        return user_config

    
    def _get_client_config_template(self) -> str:
        filepath = settings.TEMPLATES_DIR + "xray_client_config_template.json"
        return self._read_text_file(filepath)

