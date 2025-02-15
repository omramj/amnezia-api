# Amnezia-API

Please note: this project is completely separate from AmneziaVPN. AmneziaVPN devs probably don't even know it exists.


## Overview

This is an API backend for AmneziaVPN. It allows you to obtain VPN configs via HTTP calls.

## Installation

### Prerequisites

This project is in its early stage of development, so currenlty the isntallation script has only been tested on Ubuntu Server 24.04 LTS.

Before installing this API, please make sure that you've set up your server and protocols via AmneziaVPN application.

### How to install

To install the API, run this command on the server where AmneziaVPN is installed:


```bash
sudo bash -c "$(wget -qO- https://raw.githubusercontent.com/omramj/amnezia-api/refs/heads/main/deploy/install.sh)"
```

If everything goes fine, you will get an output with URL by which you can access the API:

```
CONGRATULATIONS! Your Amnezia-API backend is up and running.

To access the api, use the following link:

https://xxx.xxx.xxx.xxx:xxx/xxxxxxxxxxxxxxxx/status

Make sure that port xxxx is open in your firewall.
```

### How to update

Automatic updates to be made in the future, but for now, there exists another script that you can run to update the API:

```bash
sudo bash -c "$(wget -qO- https://raw.githubusercontent.com/omramj/amnezia-api/refs/heads/main/deploy/update.sh)"
```

## Usage

As of version 0.2.0, only XRay, AmneziaWG and Wireguard protocols are supported. 

### General idea

The API URL has the following structure:

```
https://<server's-public-ip>:<randomly-chosen-port>/<some-random-secret-string>/<protocol-name>/<action>
```

Where:

- Server's public IP is defined automatically during startup. 
- Port is chosen randomly during installation. The update script does not change the port.
- Some random secret string is generated during installation and it persists though updates as well. It is saved in `/opt/amnezia-api/secret-url-string.txt`.
- Protocol name currently could be only:
    - `xray`
    - `wireguard`
    - `amnezia-wg`
- There is only one action available for now:
    - `create-config`. To perform this action, you need to make a POST request and provide a `client-name` in the request body.

### Example

Let's concider an example. Suppose, your server has an IP `456.456.456.456`, and the API listens on port `65537`. You secret string is `fUrKnfUrKnfUrKn`. And you want to create a config for XRay protocol. 
Well, you need to make the following POST request. Example with using curl:

```
curl -k -X POST -d "client-name=<some-arbitrary-name>" https://456.456.456.456:65537/fUrKnfUrKnfUrKn/xray/create-config
```

Notice that with curl, the `-k` option is requred, because the API uses a self-signed certificate. So, your curl won't be happy without the `-k` flag.


## Future development

Please, leave your feature requests and bug reports. We will be happy to develop this project.
