!#/bin/bash

docker build -t amnezia-api-test .
# This is a script for test run the app. 
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -p 127.0.0.1:42674:42674 --name=amnezia-api-test amnezia-api-test
