# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/server_scripts/xray/template.json
XRAY_CLIENT_TEMPLATE = """
{
    "inbounds": [
        {
            "listen": "127.0.0.1",
            "port": 10808,
            "protocol": "socks",
            "settings": {
                "udp": true
            }
        }
    ],
    "log": {
        "loglevel": "error"
    },
    "outbounds": [
        {
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": "$SERVER_IP",
                        "port": 443,
                        "users": [
                            {
                                "encryption": "none",
                                "flow": "xtls-rprx-vision",
                                "id": "$CLIENT_ID"
                            }
                        ]
                    }
                ]
            },
            "streamSettings": {
                "network": "tcp",
                "realitySettings": {
                    "fingerprint": "chrome",
                    "publicKey": "$SERVER_PUBLIC_KEY",
                    "serverName": "www.googletagmanager.com",
                    "shortId": "$SHORT_ID",
                    "spiderX": ""
                },
                "security": "reality"
            }
        }
    ]
}
"""


WIREGUARD_SERVER_PEER_TEMPLATE = """
[Peer]
PublicKey = $CLIENT_PUBKEY
PresharedKey = $PRESHARED_KEY
AllowedIPs = $PEER_IP/32
"""

# https://github.com/amnezia-vpn/amnezia-client/blob/dev/client/server_scripts/wireguard/template.conf
WIREGUARD_CLIENT_CONFIG_TEMPLATE = """
[Interface]
Address = $WIREGUARD_CLIENT_IP/32
DNS = $PRIMARY_DNS, $SECONDARY_DNS
PrivateKey = $WIREGUARD_CLIENT_PRIVATE_KEY

[Peer]
PublicKey = $WIREGUARD_SERVER_PUBLIC_KEY
PresharedKey = $WIREGUARD_PSK
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = $SERVER_IP_ADDRESS:$WIREGUARD_SERVER_PORT
PersistentKeepalive = 25
"""
