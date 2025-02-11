import datetime
from enum import Enum
import re
import codecs
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


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


def validate_ip_address(ip: str) -> bool:

    if re.match(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", ip):
        return True

    return False


def get_current_datetime() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class ContainerName(str, Enum):
    XRAY = "amnezia-xray"
    WIREGUARD   = "amnezia-wireguard"
    AMNEZIA_WG  = "amnezia-awg"
