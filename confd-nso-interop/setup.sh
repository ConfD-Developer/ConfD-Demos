#!/bin/bash

CONFD_VERSION="7.3"
NSO_VERSION="5.3"
APP_NAME="router"

if [ -f confd-$CONFD_VERSION.linux.x86_64.installer.bin ] && [ -f confd-$CONFD_VERSION.libconfd.tar.gz ] && [ -f nso-$NSO_VERSION.linux.x86_64.installer.bin ]
then
    echo "Using:"
    echo "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo "confd-$CONFD_VERSION.libconfd.tar.gz"
    echo "nso-$NSO_VERSION.linux.x86_64.installer.bin"
else
    echo >&2 "This demo require that the NSO and ConfD SDK installers and the ConfD libconfd C-API library has been placed in this folder."
    echo >&2 "E.g.:"
    echo >&2 "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo >&2 "confd-$CONFD_VERSION.libconfd.tar.gz"
    echo >&2 "nso-$NSO_VERSION.linux.x86_64.installer.bin"
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

DOCKERPS=$(docker ps -q -n 1 -f name=drned-xmnr-demo)
if [ -z "$DOCKERPS" ] ;
then
    echo "Build & run"
else
    echo "Stop any existing drned-xmnr-demo container, then build & run"
    docker stop drned-xmnr-demo
fi
docker build -t drned-xmnr-demo --build-arg CONFD_VERSION=$CONFD_VERSION --build-arg NSO_VERSION=$NSO_VERSION --build-arg APP_NAME=$APP_NAME -f Dockerfile .
CID="$(docker run --name drned-xmnr-demo -d --rm -p 2022:2022 -p 12022:12022 -p 4565:4565 -p 4569:4569 -p 8080:8080 drned-xmnr-demo | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CID) != $CID ]]; do
    echo "waiting..."
    sleep .5
done

echo "CID: $CID"
docker logs drned-xmnr-demo --follow
