#!/bin/bash

CONFD_VERSION="basic-7.3"
NSO_VERSION="5.3"
APP_NAME="router"
IMG_NAME="$APP_NAME-drned-demo"

if [ -f confd-$CONFD_VERSION.linux.x86_64.installer.bin ] && [ -f confd-$CONFD_VERSION.libconfd.tar.gz ] && [ -f nso-$NSO_VERSION.linux.x86_64.signed.bin ]
then
    echo "Using:"
    echo "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo "confd-$CONFD_VERSION.libconfd.tar.gz"
    echo "nso-$NSO_VERSION.linux.x86_64.signed.bin"
else
    echo >&2 "This demo require that the NSO and ConfD SDK installers and the ConfD libconfd C-API library has been placed in this folder."
    echo >&2 "E.g.:"
    echo >&2 "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo >&2 "confd-$CONFD_VERSION.libconfd.tar.gz"
    echo >&2 "nso-$NSO_VERSION.linux.x86_64.signed.bin"
    echo >&2 "Aborting..."
    exit 1
fi

if [ -d $APP_NAME_nso ] && [ -d $APP_NAME_confd ]
then
    echo "Using these application folders:"
    printf "%s_confd\n" "$APP_NAME"
    printf "%s_nso\n" "$APP_NAME"
    rm -f $APP_NAME-confd.tar.gz
    cd ./"$APP_NAME"_confd
    tar cfz ../$APP_NAME-confd.tar.gz .
    cd ..
    rm -f $APP_NAME-nso.tar.gz
    cd ./"$APP_NAME"_nso
    tar cfz ../$APP_NAME-nso.tar.gz .
    cd ..
else
    echo >&2 "This demo require that the NSO and ConfD application folders exists"
    echo >&2 "E.g. these directories:"
    echo >&2 "./$APP_NAME_confd"
    echo >&2 "./$APP_NAME_nso"
    echo >&2 "Aborting..."
    exit 1
fi

DOCKERPS=$(docker ps -q -n 1 -f name=$IMG_NAME)
if [ -z "$DOCKERPS" ] ;
then
    echo "Build & run"
else
    echo "Stop any existing $IMG_NAME container, then build & run"
    docker stop $IMG_NAME
fi
docker build -t $IMG_NAME --build-arg CONFD_VERSION=$CONFD_VERSION --build-arg NSO_VERSION=$NSO_VERSION --build-arg APP_NAME=$APP_NAME -f Dockerfile .
CID="$(docker run --name $IMG_NAME -d --rm -p 18080:18080 $IMG_NAME | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CID) != $CID ]]; do
    echo "waiting..."
    sleep .5
done

echo "CID: $CID"
docker logs $IMG_NAME --follow
