import subprocess
import json

import docker
from docker.models.containers import Container, ExecResult


class Executor:
    def __init__(self):
        pass

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
        self.xray: XrayContainerController

        self.docker_client = docker.from_env()
        self.initialize_container_controllers()


    def get_installed_containers(self) -> list[Container]:
        return self.docker_client.containers.list()


    def initialize_container_controllers(self):

        for container in self.get_installed_containers():
            match container.name:
                case "amnezia-xray":
                    self.xray = XrayContainerController(container)
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

        return result


    def copy_file_into_container(self, from_path: str, to_path: str) -> str:
        # copy a file from host into container

        full_command = f"docker cp {from_path} {self.container.id}://{to_path}"
        
        print(full_command)
        return self._execute_shell_command(full_command)


class XrayContainerController(ContainerController):
# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/configurators/xray_configurator.cpp

    def __init__(self, container: Container) -> None:
        self.container = container


    def get_server_config(self) -> dict:
        command_list = "cat /opt/amnezia/xray/server.json"
        result = self.execute_arbitrary_command_in_container(command_list)
        return json.loads(result.output)


    def update_server_config(self, new_config: dict) -> str:
        
        new_config_json = json.dumps(new_config, indent=4)
        command = f""" sh -c "echo '{new_config_json}' > /opt/amnezia/xray/server1.json" """

        # First: save the config to a host.
        # Second: copy from host to the container. 
        # Third: delete the file from the host.
        # This feels stupid, but I right now I can't come up with a way to overcome
        # quotation problems when using echo.
        # TODO in the future.

        filepath = "tmp/server.json"
        self._write_to_file(filepath=filepath, data=new_config_json)
        result = self.copy_file_into_container(filepath,
                                               "/opt/amnezia/xray/server1.json")
        self._remove_file(filepath)

        return result
