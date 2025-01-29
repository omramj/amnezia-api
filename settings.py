import json
from os import wait
import subprocess


def load_wg_server_private_key(container_id: str) -> str:
    command_list = ['cat', '/opt/amnezia/awg/wireguard_server_private_key.key']
    return _execute_arbitrary_command_in_container(container_id, command_list)


def load_wg_server_public_key(container_id: str) -> str:
    command_list = ['cat', '/opt/amnezia/awg/wireguard_server_public_key.key']
    return _execute_arbitrary_command_in_container(container_id, command_list)


def load_wg_server_preshared_key(container_id: str) -> str:
    command_list = ['cat', '/opt/amnezia/awg/wireguard_psk.key']
    return _execute_arbitrary_command_in_container(container_id, command_list)


def _execute_arbitrary_command_in_container(container_id: str, command_list: list[str]) -> str:
    tokens = ['docker', 'exec', container_id, *command_list]

    try:
        result = subprocess.run(tokens, check=True,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return result.stdout

    except subprocess.CalledProcessError as e:
        # TODO
        print(e)
        exit()


with open('settings.json') as f:
    settings = json.load(f)


DOCKER_CONTAINER_ID = settings.get("amnezia-awg").get("docker-container-id")

WG_SERVER_PRIVATE_KEY = load_wg_server_private_key(DOCKER_CONTAINER_ID).strip('\n')
WG_SERVER_PUBLIC_KEY = load_wg_server_public_key(DOCKER_CONTAINER_ID).strip('\n')
WG_SERVER_PSK = load_wg_server_preshared_key(DOCKER_CONTAINER_ID).strip('\n')
