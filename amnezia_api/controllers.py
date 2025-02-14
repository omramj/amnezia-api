from __future__ import annotations
import logging
import json
import uuid
import subprocess
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
from amnezia_api.utils import ServerControllerInitializationError, remove_line_breaks as _
from amnezia_api.utils import (
        AddressPoolError, ClientsTableError, ConfigReadingError, ContainerName,
        ExecRunError, UserConfigError, ServerConfigError
        )


logger = logging.getLogger("controller")
print(logger)


class Executor:
    def __init__(self):
        pass


    def _write_to_file(self, filepath: str, data: str) -> None:
        with open(f"{filepath}", 'w') as file:
            file.write(data)


    def _remove_file(self, filepath: str) -> None:
        subprocess.run(f"rm {filepath}", shell=True)


class ServerController(Executor):
    def __init__(self, container_name: ContainerName):
        self.configurator: Configurator

        self.docker_client = docker.from_env()
        self._initialize_configurator(container_name)


    def get_installed_containers(self) -> list[Container]:
        return self.docker_client.containers.list()


    def _initialize_configurator(self, container_name: ContainerName):
        for container in self.get_installed_containers():
            if container.name == container_name:
                match container.name:
                    case ContainerName.XRAY:
                        self.configurator = XrayConfigurator(
                                XrayContainerController(container))

                    case ContainerName.WIREGUARD:
                        self.configurator = WgConfigurator(
                                WgContainerController(container))

                    case ContainerName.AMNEZIA_WG:
                        self.configurator = AmneziaWgConfigurator(
                                AmneziaWgContainerController(container))

                    case _:
                        pass
                return 

        raise ServerControllerInitializationError(_(
            f"""Container with name {container_name.value} is not present in a list 
            of installed containers."""))


class ContainerController(Executor):
    def __init__(self, container: Container):
        self.working_dir: str
        self.container = container


    def restart_container(self) -> None:
        self.container.restart()


    def execute_arbitrary_command_in_container(self, command: str) -> ExecResult:
        result = self.container.exec_run(f"{command}")
        if result[0] != 0:
            raise ExecRunError(_(f"""Error performing exec_run.
                                 Command: '{command}'. Result: {result}."""))
        return result


    def get_text_file_from_container(self, filepath: str) -> str:
        command = f"cat {filepath}"
        result = self.execute_arbitrary_command_in_container(command)
        return result[1].decode().strip()


    def write_string_to_file(self, filepath: str, string: str) -> str:
        command = f""" sh -c 'cat > {filepath} <<EOF\n{string}\nEOF'"""

        result = self.execute_arbitrary_command_in_container(command)
        return result[1]


class Configurator:
    def __init__(self, controller: "XrayContainerController | WgContainerController"):
        self.controller = controller
        logger.debug(f"Initialization for container '{controller.container.name}' started...")
        self.server_public_ip = utils.get_server_public_ip()
        self.server_config = self.controller.get_server_config()


    def create_config(self, client_name: str) -> str:
        # TODO
        raise Exception("This method should be overriden by a child class")

    
    def _read_text_file(self, filepath: str) -> str:
        with open(filepath, "r") as file:
            return file.read()


    def _replace_variables_in_config(self, template: str,
                                     variables_values: dict) -> str:
        config = template

        for var, value in variables_values.items():
            if config.find(var) == -1:
                raise UserConfigError(
                        f"The variable {var} is not present in the config template.")

            if value is None:
                raise UserConfigError(f"Value of variable {var} is None.")

            config = config.replace(var, value)

        return config


    def _get_lines_from_config(self, strings_to_search: list[str]) -> list[str]:
        out = []
        if not strings_to_search:
            raise ConfigReadingError(_(f"""Attempted to search in server config,
                    but nothing to search for - strings_to_search is empty."""))

        if self.server_config is None:
            raise ConfigReadingError(_("""Attempted to search in server config, 
                           but the server_config property is None."""))

        for line in self.server_config.splitlines():
            for string in strings_to_search:
                if line.strip().startswith(string):
                    out.append(line)
        return out


    def _add_entry_to_clients_table(self, client_id: str, client_name: str) -> None:

        filepath = self.controller.working_dir + "/clientsTable"
        try:
            clients_table = json.loads(
                    self.controller.get_text_file_from_container(filepath)
                    )
        except Exception as e:
            raise ClientsTableError(f"Could not load clientTable.  Details: {e}")

        new_client = {
                "clientId": f"{client_id}",
                "userData": {
                    "clientName": f"{client_name}",
                    "creationDate": f"{utils.get_current_datetime()}"
                    }
                }
        
        # assuming that clients_table is always a list. If the file is empty, 
        # than an exception is thrown when trying to load it.
        try:
            clients_table.append(new_client)
        except AttributeError:
            raise ClientsTableError("Unexpected format of clientsTable.")
        
        try:
            clients_table_string = json.dumps(clients_table, indent=4)
        except Exception as e:
            raise ClientsTableError(_(f"""An error occured when trying to dump 
                           updated clientsTable to json. Details: {e}"""))

        self.controller.write_string_to_file(filepath, clients_table_string)


    def _log_init_complete(self) -> None:
        logger.debug(_(f"""{self.controller.container.name} 
                       configurator has been initialized."""))


    def _log_server_config_updated(self) -> None:
        logger.debug(_(f"""Server config for {self.controller.container.name} 
                       container has been updated."""))


class XrayContainerController(ContainerController):
    def __init__(self, container: Container) -> None:
        super().__init__(container)
        self.working_dir = "/opt/amnezia/xray"


    def get_server_config(self) -> str:
        filepath = f"{self.working_dir}/server.json"
        return self.get_text_file_from_container(filepath=filepath)


    def update_server_config(self, new_config: str) -> None:
        config_path = f"{self.working_dir}/server.json"
        self.write_string_to_file(filepath=config_path,
                                   string=new_config)


    def get_server_public_key(self) -> str:
        filepath = f"{self.working_dir}/xray_public.key"
        return self.get_text_file_from_container(filepath=filepath)


    def get_server_short_id_key(self) -> str:
        filepath = f"{self.working_dir}/xray_short_id.key"
        return self.get_text_file_from_container(filepath=filepath)


class XrayConfigurator(Configurator):
# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/xray.cpp

    def __init__(self, controller: XrayContainerController):
        super().__init__(controller)
        self.controller: XrayContainerController

        self.server_public_key = self.controller.get_server_public_key()
        self.server_short_id = self.controller.get_server_short_id_key()
        self._log_init_complete()


    def _prepare_server_config(self) -> uuid.UUID:

        # Generate new UUID for client
        client_id = uuid.uuid1()

        server_config_dict = self._validate_server_config()

        # Add a new user to the config
        client_config = {"id": str(client_id), "flow": "xtls-rprx-vision"}
        server_config_dict["inbounds"][0].get(
                            "settings").get("clients").append(client_config)
        try:
            new_server_config = json.dumps(server_config_dict, indent=4)
        except Exception as e:
            raise ServerConfigError(_(f"""Error when trying to json.dumps() an 
                                      updated server config. Details: {e}"""))

        # Load the new config into the container
        self._update_server_config(new_server_config)

        # Restart container
        self.controller.restart_container()

        return client_id


    def _validate_server_config(self) -> dict[str, list]:
        # Validate server config structure
        if self.server_config is None:
            raise ServerConfigError("Could not read server config.")

        server_config_dict = json.loads(self.server_config)

        inbounds = server_config_dict.get("inbounds")

        if inbounds is None:
            raise ServerConfigError(
                    "The 'inbouds' field is missing in the server config.")

        if len(inbounds) == 0:
            raise ServerConfigError("'inbounds' field is empty.")
        
        settings = inbounds[0].get("settings")

        if settings is None:
            raise ServerConfigError(
                    "The 'settings' field is missing in the server inbound config.")

        clients = settings.get("clients")

        if clients is None:
            raise ServerConfigError(
                    "The 'clients' field is missing in the server inbound settings config.")

        return server_config_dict


    @override
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
        self._log_server_config_updated()

    
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
        super().__init__(controller)
        self.controller: WgContainerController
        self.server_public_key = self.controller.get_server_public_key()
        self.server_psk        = self.controller.get_server_preshared_key()
        self.listen_port       = self._get_port_from_server_config()
        self.dns               = settings.dns
        self.subnet_part       = self._get_subnet_ip_from_server_config()
        self._log_init_complete()


    @override
    def create_config(self, client_name: str) -> str:
        private_key, public_key, client_ip = self._prepare_wg_config()
        user_config = self._compose_new_user_config(client_ip, private_key)
        self._add_entry_to_clients_table(client_id=public_key, client_name=client_name)

        return user_config


    def _get_port_from_server_config(self) -> int:
        listen_port_line = self._get_lines_from_config(["ListenPort"])

        if not listen_port_line:
            raise ServerConfigError(_(f"""Listen port not found in the server config. 
                           Does the config contain 'ListenPort'?"""))

        if len(listen_port_line) > 1:
            raise ServerConfigError(_(f"""More than one 'ListenPort' lines 
                                      found in server config. Expected exactly one."""))
        
        return int(listen_port_line[0].split("=")[1].strip())


    def _get_subnet_ip_from_server_config(self) -> str:
        address_lines = self._get_lines_from_config(["Address"])
        if not address_lines:
            raise ServerConfigError(_(f"""Could not find ip in server config. 
                           Does it contain the 'Address' field?"""))

        if address_lines[0].split("/")[-1] != "24":
            raise ServerConfigError(
            _(f"""Server subnet mask is not 24 bit. This API does not support it for now."""))

        server_ip = address_lines[0].split("=")[1].strip().split("/")[0]

        # Exactly this line does not work if subnet mask in the address is not 24. 
        # TODO for arbitrary subnet mask
        subnet_part = server_ip[:server_ip.rfind(".")]

        return subnet_part


    def _get_existed_client_ips_from_server_config(self) -> list[str]:
        out = []
        allowed_ips_lines = self._get_lines_from_config(["AllowedIPs"])
        if not allowed_ips_lines:
            return []

        for line in allowed_ips_lines:
            if line == "":
                raise ServerConfigError(
                _(f"""Error while reading allowed ips from server config: 
                  got an empty line."""))

            ips_string = line.split("=")[1].replace("/32", "")
            if ips_string is None or ips_string == "":
                raise ServerConfigError(_(f"""Error while reading allowed ips from 
                               server config: could not parse AllowedIPs line."""))

            # Get only the first one, in case user configured other AllowedIPs here.
            ip = ips_string.split(",")[0].strip()
            if not ip.startswith(self.subnet_part):
                raise ServerConfigError(
                _(f"""Error while reading allowed ips from server config:
                    parsed AllowedIP does not match with server's address.
                    Parsed ip is '{ip}', while server's subnet is '{self.subnet_part}'."""))

            out.append(ip)
                
        return out


    def _update_server_config(self, new_config: str) -> None:

        self.controller.update_server_config(new_config=new_config)
        self.server_config = self.controller.get_server_config()
        self.controller.sync_config()
        self._log_server_config_updated()


    def _prepare_wg_config(self) -> tuple[str, str, str]:
        private_key, public_key = utils.generate_wg_key_pair()
        client_ip = self._calculate_next_vacant_ip()
        new_config = self._compose_new_server_config(client_pubkey=public_key, 
                                                           client_ip=client_ip)
        self._update_server_config(new_config)

        return private_key, public_key, client_ip


    def _calculate_next_vacant_ip(self) -> str:
        taken_ips = self._get_existed_client_ips_from_server_config()
        if not taken_ips:
            next_ip_number = 2
        else:
            # Here we asssume that peers in the config stay in the accending order,
            # and we just take the last one plus one.
            # This does not feel right. Is this guaranteed by Amnezia client?
            # Seems so, but it's quite implicit.
            next_ip_number = int(taken_ips[-1].split(".")[-1]) + 1
            if next_ip_number > 254: 
                raise AddressPoolError("No available IP address left")

        subnet_part = self._get_subnet_ip_from_server_config()
        return subnet_part + "." + str(next_ip_number)


    def _compose_new_server_config(self, client_pubkey: str, client_ip: str) -> str:
        if self.server_config is None:
            raise ServerConfigError("Server config is None.")

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
                    "$PRIMARY_DNS": self.dns[0],
                    "$SECONDARY_DNS": self.dns[1],
                    "$WIREGUARD_CLIENT_PRIVATE_KEY": private_key,
                    "$WIREGUARD_SERVER_PUBLIC_KEY": self.server_public_key,
                    "$WIREGUARD_PSK": self.server_psk,
                    "$SERVER_IP_ADDRESS": self.server_public_ip,
                    "$WIREGUARD_SERVER_PORT": str(self.listen_port)
                    }
                )
        return user_config.strip()


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
                    "$PRIMARY_DNS": self.dns[0],
                    "$SECONDARY_DNS": self.dns[1],
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
                    "$SERVER_IP_ADDRESS": self.server_public_ip,
                    "$AWG_SERVER_PORT": str(self.listen_port)
                    }
                )
        return user_config.strip()


    def _read_awg_params_from_server_config(self) -> dict[str, str]:
        params = {}
        lines_to_search = ["Jc", "Jmin", "Jmax", "S1", "S2",
                             "H1", "H2", "H3", "H4"]

        for line in self._get_lines_from_config(lines_to_search):
            key, value = (i.strip() for i in line.split("="))

            # check that value is a number. If not, python throw an exception.
            # TODO: do not make it that stupidly
            # EDIT: maybe it's not so stupid it wrapped with try-except? 
            try:
                int(value)
            except ValueError:
                raise ServerConfigError(
                    _(f"""Cound not read awg parameters from the server config.
                    When reading '{key}', expected an integer, but got '{value}'."""))

            params[key] = value

        if len(params) != len(lines_to_search):
            raise ServerConfigError(
            _(f"""Something went wrong when reading awg parameters
            from server config. Number of found parameters does not match 
            the number of lines to search. Expected {len(lines_to_search)}, 
            but got {len(params)}: {params}"""))

        for key in lines_to_search:
            if params.get(key) == None:
                raise ServerConfigError(
                _(f"""Something went wrong when reading awg parameters from 
                server config. Parameter '{key}' not found."""))

        logger.debug("Awg parameters have been read.")
        return params
