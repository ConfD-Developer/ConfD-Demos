#!/bin/bash
CONFD_VERSION="7.3"
IMG_NAME="confd-debian-py"

if [ -f confd-$CONFD_VERSION.linux.x86_64.installer.bin ] \
       && [ -f confd-$CONFD_VERSION.libconfd.tar.gz ]
then
    echo "Using:"
    echo "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo "confd-$CONFD_VERSION.libconfd.tar.gz"
else
    echo >&2 "This demo require that the ConfD SDK installer, ConfD libconfd C-API library, and the ConfD examples tar-ball has been placed in this folder."
    echo >&2 "E.g.:"
    echo >&2 "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo >&2 "confd-$CONFD_VERSION.libconfd.tar.gz"
    echo >&2 "Aborting..."
    exit
fi

COPYFILE_DISABLE=true tar cvfz app.tar.gz app

DOCKERPS=$(docker ps -q -n 1 -f name="$IMG_NAME")
if [ -z "$DOCKERPS" ]
then
    echo "Build & run"
else
    echo "Stop any existing $IMG_NAME container, then build & run"
    docker stop $IMG_NAME
fi

docker build -t $IMG_NAME --build-arg CONFD_VERSION=$CONFD_VERSION -f Dockerfile .
CID="$(docker run --name $IMG_NAME -d --rm -p 2022:2022 -p 4565:4565 $IMG_NAME | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CID) != $CID ]]; do
    echo "waiting..."
    sleep .5
done

echo "CID: $CID"
docker logs $CID --follow
