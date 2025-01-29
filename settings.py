import json
import subprocess


def load_wg_server_private_key(container_id: str) -> str:
    tokens = ['docker', 'exec', container_id, 'cat', '/opt/amnezia/awg/wireguard_server_private_key.key']
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

WG_SERVER_PRIVATE_KEY = load_wg_server_private_key(DOCKER_CONTAINER_ID)

print(WG_SERVER_PRIVATE_KEY)
