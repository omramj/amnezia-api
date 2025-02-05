
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
