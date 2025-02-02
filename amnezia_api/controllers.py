import json
import uuid
import subprocess
import base64

import docker
from docker.models.containers import Container, ExecResult

import amnezia_api.utils as utils
from amnezia_api.settings import settings


class Executor:
    def __init__(self):
        pass


    def get_server_public_ip(self) -> str:
        # The way we find out public IP is like in the Outline installer script (function set_hostname()).
        # https://raw.githubusercontent.com/Jigsaw-Code/outline-server/master/src/server_manager/install_scripts/install_server.sh

        checkers = [
                "https://icanhazip.com",
                "https://ipinfo.io/ip"
                ]

        for url in checkers:
            ip_string = self._execute_shell_command(f"curl {url}").strip("\n")
            if utils.validate_ip_address(ip_string):
                return ip_string

        #TODO logging and exception
        print("Could not find out server public ip")
        raise Exception


    def _execute_shell_command(self, command: str) -> str:
        try:
            result = subprocess.run(command, check=True,
                                    text=True, shell=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.stdout

        except subprocess.CalledProcessError as e:
            # TODO
            print(e)
            exit()


    def _write_to_file(self, filepath: str, data: str) -> None:
        with open(f"{filepath}", 'w') as file:
            file.write(data)


    def _remove_file(self, filepath: str) -> None:
        subprocess.run(f"rm {filepath}", shell=True)


class ServerController(Executor):
    def __init__(self):
        self.xray: XrayConfigurator

        self.docker_client = docker.from_env()
        self.initialize_container_controllers()


    def get_installed_containers(self) -> list[Container]:
        return self.docker_client.containers.list()


    def initialize_container_controllers(self):
        for container in self.get_installed_containers():
            match container.name:
                case "amnezia-xray":
                    self.xray = XrayConfigurator(XrayContainerController(container))
                case _:
                    #TODO
                    pass


class ContainerController(Executor):
    def __init__(self, container: Container):
        self.container = container


    def restart_container(self) -> None:
        self.container.restart()


    def execute_arbitrary_command_in_container(self, command: str) -> ExecResult:
        result = self.container.exec_run(f"{command}")
        if result[0] != 0:
            #TODO logging and exception
            print(f"Error in exec_run. Command: ""{command}"".")
            raise Exception
        return result


    def copy_file_into_container(self, from_path: str, to_path: str) -> str:
        # copy a file from host into container
        full_command = f"docker cp {from_path} {self.container.id}://{to_path}"
        print(full_command)
        return self._execute_shell_command(full_command)


class XrayContainerController(ContainerController):
    def __init__(self, container: Container) -> None:
        self.container = container


    def get_server_config(self) -> str:
        command_list = "cat /opt/amnezia/xray/server.json"
        result = self.execute_arbitrary_command_in_container(command_list)
        return result[1].decode()


    def update_server_config(self, new_config: str) -> str:
        # command = f""" sh -c "echo '{new_config}' > /opt/amnezia/xray/server.json" """

        # First: save the config to a host.
        # Second: copy from host to the container. 
        # Third: delete the file from the host.
        # This feels stupid, but I right now I can't come up with a way to overcome
        # quotation problems when using echo.
        # TODO in the future.

        filepath = "tmp/server.json"
        self._write_to_file(filepath=filepath, data=new_config)
        result = self.copy_file_into_container(filepath,
                                               "/opt/amnezia/xray/server.json")
        self._remove_file(filepath)
        return result


    def get_server_public_key(self) -> str:
        command_list = "cat /opt/amnezia/xray/xray_public.key"
        result = self.execute_arbitrary_command_in_container(command_list)
        return result[1].decode().replace("\n", "")


    def get_server_short_id_key(self) -> str:
        command_list = "cat /opt/amnezia/xray/xray_short_id.key"
        result = self.execute_arbitrary_command_in_container(command_list)
        return result[1].decode().replace("\n", "")


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


    def _convert_string_to_base64(self, string: str) -> str:
        string_bytes = string.encode()
        base64_bytes = base64.b64encode(string_bytes)
        return base64_bytes.decode("ascii")



class XrayConfigurator(Configurator):
# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/xray.cpp

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
                
        return f"vpn://{self._convert_string_to_base64(user_config)}"

    
    def _get_client_config_template(self) -> str:
        filepath = settings.TEMPLATES_DIR + "xray_client_config_template.json"
        return self._read_text_file(filepath)
