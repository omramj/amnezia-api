import json
import uuid
import subprocess
import base64
from typing import override

import docker
from docker.models.containers import Container, ExecResult

import amnezia_api.utils as utils
from amnezia_api.settings import settings
from amnezia_api.config_templates import (
        AMNEZIA_WG_CLIENT_CONFIG_TEMPLATE,
        XRAY_CLIENT_TEMPLATE,
        WIREGUARD_SERVER_PEER_TEMPLATE,
        WIREGUARD_CLIENT_CONFIG_TEMPLATE
        )
import amnezia_api.utils as utils
from amnezia_api.utils import ContainerName


class Executor:
    def __init__(self):
        pass


    def get_server_public_ip(self) -> str:
        # The way we find out public IP is like in the Outline installer script
        # (function set_hostname()).
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
        self.xray: XrayConfigurator | None = None
        self.wireguard: WgConfigurator | None = None
        self.amnezia_wg: AmneziaWgConfigurator | None = None

        self.docker_client = docker.from_env()
        self.initialize_container_controllers()


    def get_installed_containers(self) -> list[Container]:
        return self.docker_client.containers.list()


    def initialize_container_controllers(self):
        for container in self.get_installed_containers():
            match container.name:
                case ContainerName.XRAY:
                    self.xray = XrayConfigurator(XrayContainerController(container))

                case ContainerName.WIREGUARD:
                    self.wireguard = WgConfigurator(WgContainerController(container))

                case ContainerName.AMNEZIA_WG:
                    self.amnezia_wg = AmneziaWgConfigurator(AmneziaWgContainerController(container))

                case _:
                    #TODO
                    pass


class Configurator:
    def __init__(self):
        self.server_config: str | None
        self.controller: ContainerController
        pass

    
    def _read_text_file(self, filepath: str) -> str:
        with open(filepath, "r") as file:
            return file.read()


    def _replace_variables_in_config(self, template: str, variables_values: dict) -> str:

        config = template

        for var, value in variables_values.items():
            if config.find(var) == -1:
                # TODO logging and exception
                raise Exception(f"The variable {var} not found in the template.")

            if value is None:
                # TODO
                raise Exception(f"Value of variable {var} is None.")

            config = config.replace(var, value)

        return config


    def _get_lines_from_config(self, strings_to_search: list[str]) -> list[str]:
        out = []
        if len(strings_to_search) < 1:
            #TODO
            raise Exception("strings_to_search should contain at least one entry")

        if self.server_config is None:
            #TODO
            raise Exception("Something went wrong when reading server config.")

        for line in self.server_config.splitlines():
            for string in strings_to_search:
                if line.strip().startswith(string):
                    out.append(line)
        return out


    def add_entry_to_clients_table(self, client_id: str, client_name: str) -> None:

        filepath = self.controller.working_dir + "/clientsTable"
        clients_table = json.loads(
                self.controller.get_text_file_from_container(filepath)
                )
        new_client = {
                "clientId": f"{client_id}",
                "userData": {
                    "clientName": f"{client_name}",
                    "creationDate": f"{utils.get_current_datetime()}"
                    }
                }
        
        clients_table.append(new_client)
        clients_table_string = json.dumps(clients_table, indent=4)
        self.controller.write_string_to_file(filepath, clients_table_string)


class ContainerController(Executor):
    def __init__(self, container: Container):
        self.working_dir: str
        self.container = container


    def restart_container(self) -> None:
        self.container.restart()


    def execute_arbitrary_command_in_container(self, command: str) -> ExecResult:
        result = self.container.exec_run(f"{command}")
        if result[0] != 0:
            #TODO logging and exception
            raise Exception(f"""Error in exec_run. Command: '{command}'. Result: {result}.""")
        return result


    def copy_file_into_container(self, from_path: str, to_path: str) -> str:
        # copy a file from host into container
        full_command = f"docker cp {from_path} {self.container.id}://{to_path}"
        return self._execute_shell_command(full_command)


    def get_text_file_from_container(self, filepath: str) -> str:
        command = f"cat {filepath}"
        result = self.execute_arbitrary_command_in_container(command)
        return result[1].decode().strip()


    def write_string_to_file(self, filepath: str, string: str) -> str:
        command = f""" sh -c 'cat > {filepath} <<EOF\n{string}\nEOF'"""

        result = self.execute_arbitrary_command_in_container(command)
        return result[1]


    def update_server_config(self, new_config: str) -> None:
        #TODO
        raise Exception("This method should be overriden in the child class.")


    def get_server_config(self) -> str:
        #TODO
        raise Exception("This method should be overriden in the child class.")


    def sync_config(self):
        pass


class XrayContainerController(ContainerController):
    def __init__(self, container: Container) -> None:
        self.container = container
        self.working_dir = "/opt/amnezia/xray"


    def get_server_config(self) -> str:
        filepath = f"{self.working_dir}/server.json"
        return super().get_text_file_from_container(filepath=filepath)


    @override
    def update_server_config(self, new_config: str) -> None:
        config_path = f"{self.working_dir}/server.json"
        super().write_string_to_file(filepath=config_path,
                                   string=new_config)


    def get_server_public_key(self) -> str:
        filepath = f"{self.working_dir}/xray_public.key"
        return super().get_text_file_from_container(filepath=filepath)


    def get_server_short_id_key(self) -> str:
        filepath = f"{self.working_dir}/xray_short_id.key"
        return super().get_text_file_from_container(filepath=filepath)


class XrayConfigurator(Configurator):
# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/xray.cpp

    def __init__(self, controller: XrayContainerController):
        self.controller = controller
        self.server_config = self.controller.get_server_config()
        self.server_public_key = self.controller.get_server_public_key()
        self.server_public_ip = self.controller.get_server_public_ip()
        self.server_short_id = self.controller.get_server_short_id_key()


    def _prepare_server_config(self) -> uuid.UUID:

        # Generate new UUID for client
        client_id = uuid.uuid1()

        # Validate server config structure

        if self.server_config is None:
            #TODO
            raise Exception("Could not read server config.")

        server_config_dict = json.loads(self.server_config)

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
        self._update_server_config(new_server_config)

        # Restart container
        self.controller.restart_container()

        return client_id


    def create_config(self, client_name: str) -> str:
        client_id = self._prepare_server_config()
        variables = {
                "$CLIENT_ID": str(client_id),
                "$SERVER_PUBLIC_KEY": self.server_public_key,
                "$SERVER_IP": self.server_public_ip,
                "$SHORT_ID": self.server_short_id
                }
        user_config = self._replace_variables_in_config(
                self._get_client_config_template(),
                variables).strip()

        # Seems like xray container does not have clientsTable at this point, 
        # so I comment out this method.

        # self.add_entry_to_clients_table(client_id=str(client_id),
        #                                 client_name=client_name)
                
        return user_config


    def _update_server_config(self, new_server_config: str) -> None:
        self.controller.update_server_config(new_server_config)
        self.server_config = self.controller.get_server_config()

    
    def _get_client_config_template(self) -> str:
        
        return XRAY_CLIENT_TEMPLATE


class WgContainerController(ContainerController):
    def __init__(self, container: Container) -> None:
        self.container = container
        self.working_dir = "/opt/amnezia/wireguard"


    def get_server_config(self) -> str:
        filepath = f"{self.working_dir}/wg0.conf"
        return super().get_text_file_from_container(filepath=filepath)

    
    def get_server_public_key(self) -> str:
        filepath = f"{self.working_dir}/wireguard_server_public_key.key"
        return super().get_text_file_from_container(filepath=filepath)

    
    def get_server_preshared_key(self) -> str:
        filepath = f"{self.working_dir}/wireguard_psk.key"
        return super().get_text_file_from_container(filepath=filepath)


    @override
    def update_server_config(self, new_config: str) -> None:
        config_path = f"{self.working_dir}/wg0.conf"
        super().write_string_to_file(filepath=config_path,
                                   string=new_config)


    def sync_config(self) -> None:
        config_path = f"{self.working_dir}/wg0.conf"
        command = f"bash -c 'wg syncconf wg0 <(wg-quick strip {config_path})'"
        super().execute_arbitrary_command_in_container(command)


class WgConfigurator(Configurator):
    # https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/wireguard_configurator.cpp

    def __init__(self, controller: WgContainerController):
        self.controller        = controller
        self.server_config     = self.controller.get_server_config()
        self.server_public_key = self.controller.get_server_public_key()
        self.server_psk        = self.controller.get_server_preshared_key()
        self.hostname          = self.controller.get_server_public_ip()
        self.listen_port       = self._get_port_from_server_config()


    def create_config(self, client_name: str) -> str:
        private_key, public_key, client_ip = self._prepare_wg_config()
        user_config = self._compose_new_user_config(client_ip, private_key)
        self.add_entry_to_clients_table(client_id=public_key, client_name=client_name)

        return user_config


    def _get_port_from_server_config(self) -> int:
        listen_port_line = self._get_lines_from_config(["ListenPort"])

        if listen_port_line is None:
            #TODO
            raise Exception

        if listen_port_line[0] is None:
            raise Exception

        if len(listen_port_line) > 1:
            raise Exception
        
        return int(listen_port_line[0].split("=")[1].strip())


    def _get_subnet_ip_from_server_config(self) -> str:
        address_lines = self._get_lines_from_config(["Address"])
        if address_lines is None or len(address_lines) < 1:
            #TODO
            raise Exception("Could not find server address ip in the server's config file")

        if address_lines[0].split("/")[-1] != "24":
            #TODO
            raise Exception("Server subnet mask is not 24 bit. This API does not support it for now.")

        server_ip = address_lines[0].split("=")[1].strip().split("/")[0]

        # Exactly this line does not work if subnet mask in the address is not 24. 
        # TODO for arbitrary subnet mask
        subnet_part = server_ip[:server_ip.rfind(".")]

        return subnet_part


    def _update_server_config(self, new_config: str) -> None:

        self.controller.update_server_config(new_config=new_config)
        self.server_config = self.controller.get_server_config()
        self.controller.sync_config()


    def _prepare_wg_config(self) -> tuple[str, str, str]:
        private_key, public_key = utils.generate_wg_key_pair()
        client_ip = self._calculate_next_vacant_ip()
        new_config = self._compose_new_server_config(client_pubkey=public_key, 
                                                           client_ip=client_ip)
        self._update_server_config(new_config)

        return private_key, public_key, client_ip


    def _calculate_next_vacant_ip(self) -> str:
        taken_ips = self._get_existed_client_ips_from_server_config()
        if len(taken_ips) == 0:
            next_ip_number = 2
        else:
            assert taken_ips[-1] is not None
            next_ip_number = int(taken_ips[-1].split(".")[-1]) + 1
            if next_ip_number > 254: 
                #TODO
                raise Exception("No available IP address left")

        subnet_part = self._get_subnet_ip_from_server_config()
        return subnet_part + "." + str(next_ip_number)


    def _compose_new_server_config(self, client_pubkey: str, client_ip: str) -> str:
        if self.server_config is None:
            #TODO
            raise Exception("Server config is None.")

        new_server_config = self.server_config + \
                self._replace_variables_in_config(
                    template=WIREGUARD_SERVER_PEER_TEMPLATE,
                    variables_values={
                        "$CLIENT_PUBKEY": client_pubkey,
                        "$PRESHARED_KEY": self.server_psk,
                        "$PEER_IP": client_ip
                        }
                    )
        return new_server_config


    def _compose_new_user_config(self, client_ip: str, private_key) -> str:
        template = WIREGUARD_CLIENT_CONFIG_TEMPLATE
        user_config = self._replace_variables_in_config(
                template=template,
                variables_values={
                    "$WIREGUARD_CLIENT_IP": client_ip,
                    #TODO: do not hard code DNS
                    "$PRIMARY_DNS": "1.1.1.1",
                    "$SECONDARY_DNS": "1.0.0.1",
                    "$WIREGUARD_CLIENT_PRIVATE_KEY": private_key,
                    "$WIREGUARD_SERVER_PUBLIC_KEY": self.server_public_key,
                    "$WIREGUARD_PSK": self.server_psk,
                    "$SERVER_IP_ADDRESS": self.hostname,
                    "$WIREGUARD_SERVER_PORT": str(self.listen_port)
                    }
                )
        return user_config.strip()


    def _get_existed_client_ips_from_server_config(self) -> list[str | None]:
        out = []
        allowed_ips_lines = self._get_lines_from_config(["AllowedIPs"])
        if len(allowed_ips_lines) == 0:
            return []

        for line in allowed_ips_lines:
            if line is None:
                #TODO
                raise Exception

            ips_string = line.split("=")[1].replace("/32", "")
            if ips_string is None:
                #TODO
                raise Exception

            if ips_string == "":
                #TODO
                raise Exception
            ip = ips_string.split(",")[0].strip()
            out.append(ip)
                
        return out


class AmneziaWgContainerController(WgContainerController):
    def __init__(self, container: Container):
        self.container = container
        self.working_dir = "/opt/amnezia/awg"


class AmneziaWgConfigurator(WgConfigurator):
    # https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/awg_configurator.cpp

    def __init__(self, controller: AmneziaWgContainerController):
        super().__init__(controller)
        self.awg_params: dict[str, str] = self._read_awg_params_from_server_config()
        pass


    @override
    def _compose_new_user_config(self, client_ip: str, private_key) -> str:
        template = AMNEZIA_WG_CLIENT_CONFIG_TEMPLATE
        user_config = self._replace_variables_in_config(
                template=template,
                variables_values={
                    "$WIREGUARD_CLIENT_IP": client_ip,
                    #TODO: do not hard code DNS
                    "$PRIMARY_DNS": "1.1.1.1",
                    "$SECONDARY_DNS": "1.0.0.1",
                    "$JUNK_PACKET_COUNT": self.awg_params.get("Jc"),
                    "$JUNK_PACKET_MIN_SIZE": self.awg_params.get("Jmin"),
                    "$JUNK_PACKET_MAX_SIZE": self.awg_params.get("Jmax"),
                    "$INIT_PACKET_JUNK_SIZE": self.awg_params.get("S1"),
                    "$RESPONSE_PACKET_JUNK_SIZE": self.awg_params.get("S2"),
                    "$INIT_PACKET_MAGIC_HEADER": self.awg_params.get("H1"),
                    "$RESPONSE_PACKET_MAGIC_HEADER": self.awg_params.get("H2"),
                    "$UNDERLOAD_PACKET_MAGIC_HEADER": self.awg_params.get("H3"),
                    "$TRANSPORT_PACKET_MAGIC_HEADER": self.awg_params.get("H4"),
                    "$WIREGUARD_CLIENT_PRIVATE_KEY": private_key,
                    "$WIREGUARD_SERVER_PUBLIC_KEY": self.server_public_key,
                    "$WIREGUARD_PSK": self.server_psk,
                    "$SERVER_IP_ADDRESS": self.hostname,
                    "$AWG_SERVER_PORT": str(self.listen_port)
                    }
                )
        return user_config.strip()


    def _read_awg_params_from_server_config(self) -> dict[str, str]:
        params = {}
        strings_to_search = ["Jc", "Jmin", "Jmax", "S1", "S2",
                             "H1", "H2", "H3", "H4"]

        for line in self._get_lines_from_config(strings_to_search):
            key, value = (i.strip() for i in line.split("="))

            # check that value is a number. If not, python throw an exception.
            # TODO do not make it that stupidly
            int(value)

            params[key] = value

        if len(params) != len(strings_to_search):
            # TODO
            raise Exception("Something went wrong when reading awg parameters from server config. Number of parameters does not match.")

        for key in strings_to_search:
            if params[key] == None:
                # TODO
                raise Exception(f"Something went wrong when reading awg parameters from server config. Key {key} not found.")

        return params
        

if __name__ == "__main__":
    server = ServerController()
