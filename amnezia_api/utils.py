import datetime
from enum import Enum
import re
import codecs
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
import urllib.request


def generate_wg_key_pair() -> tuple[str, str]:

    private_key = X25519PrivateKey.generate()

    private_bytes = private_key.private_bytes(  
        encoding=serialization.Encoding.Raw,  
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
            )

    private_str = codecs.encode(private_bytes, 'base64').decode('utf8').strip()
    public_str = codecs.encode(public_bytes, 'base64').decode('utf8').strip()

    return (private_str, public_str)


def _validate_ip_address(ip: str) -> bool:

    if re.match(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", ip):
        return True

    return False


def get_current_datetime() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def convert_string_to_base64_vpn_link(string: str) -> str:
    string_bytes = string.encode()
    base64_bytes = base64.b64encode(string_bytes)
    return "vpn://" + base64_bytes.decode("ascii")


def get_server_public_ip() -> str:
    # The way we find out public IP is like in the Outline installer script
    # (function set_hostname()).
    # https://raw.githubusercontent.com/Jigsaw-Code/outline-server/master/src/server_manager/install_scripts/install_server.sh

    checkers = [
            "https://icanhazip.com",
            "https://ipinfo.io/ip"
            ]

    for url in checkers:
        ip_string = urllib.request.urlopen(url).read().decode().strip("\n")
        if _validate_ip_address(ip_string):
            return ip_string

    raise HostnameError("Could not define what server public ip shoud be")


def remove_line_breaks(string: str) -> str:
    out = ""
    for s in string.split():
        out += s.strip() + " "
    return out


class ContainerName(str, Enum):
    XRAY = "amnezia-xray"
    WIREGUARD   = "amnezia-wireguard"
    AMNEZIA_WG  = "amnezia-awg"


class UserConfigError(Exception):
    pass


class ConfigReadingError(Exception):
    pass


class ServerConfigError(Exception):
    pass


class ConfigCreationError(Exception):
    pass


class HostnameError(Exception):
    pass


class ExecRunError(Exception):
    #TODO Better naming?
    pass


class ClientsTableError(Exception):
    pass


class AddressPoolError(Exception):
    pass

class ServerControllerInitializationError(Exception):
    pass

class AppSettingsError(Exception):
    pass
