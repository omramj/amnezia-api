import subprocess
import json


class Executor:
    def __init__(self):
        self.installed_containers = {}
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

        self.initialize_container_controllers()


    def get_installed_containers(self) -> dict[str, str]:

        command = "docker ps"

        containers_list = self._execute_shell_command(command).split("\n")

        if len(containers_list) < 2:
            #TODO
            print("No containers found")
            raise Exception

        # Remove header and empty tail
        del containers_list[0]
        del containers_list[-1]
        # TODO Am I sure that there always be an empty line at the end??

        # Extract type and id of each container
        self.installed_containers = {}
        for container in containers_list:

            lst = container.split()
            container_id = lst[0]
            type = lst[1]

            self.installed_containers.update({type: container_id})

        return self.installed_containers


    def initialize_container_controllers(self):

        for type, id in self.get_installed_containers().items():
            match type:
                case "amnezia-xray":
                    self.xray = XrayContainerController(id)
                case _:
                    #TODO
                    pass


class ContainerController(Executor):
    def __init__(self):
        self.container_id = ""


    def execute_arbitrary_command_in_container(self, command: str) -> str:

        if self.container_id == "":
            # TODO
            raise Exception

        full_command = f"docker exec {self.container_id} {command}"
        
        return self._execute_shell_command(full_command)


    def copy_file_into_container(self, from_path: str, to_path: str) -> str:
        # copy a file from host into container

        if self.container_id == "":
            # TODO
            raise Exception

        full_command = f"docker cp {from_path} {self.container_id}://{to_path}"
        
        print(full_command)
        return self._execute_shell_command(full_command)


class XrayContainerController(ContainerController):
# amnezia-client/client/configurators/xray_configurator.cpp

    def __init__(self, container_id: str) -> None:
        self.container_id = container_id


    def get_server_config(self) -> dict:
        command_list = "cat /opt/amnezia/xray/server.json"
        result = self.execute_arbitrary_command_in_container(command_list)
        return json.loads(result)


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
