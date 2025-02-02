import re


def validate_ip_address(ip: str) -> bool:

    if re.match(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$", ip):
        return True

    return False
