#!/bin/bash

CONFD_VERSION="7.5"
NSO_VERSION="5.5"
APP_NAME="router"
IMG_NAME="$APP_NAME-nyat-demo"
NET_NAME="nyat-test-net"

if [ -f confd-$CONFD_VERSION.linux.x86_64.installer.bin ] && [ -f nso-$NSO_VERSION.linux.x86_64.signed.bin ]
then
    echo "Using:"
    echo "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
    echo "nso-$NSO_VERSION.linux.x86_64.signed.bin"
else
    echo >&2 "This demo require that the NSO and ConfD SDK installers has been placed in this folder."
    echo >&2 "E.g.:"
    echo >&2 "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
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

DOCKERPS_NSO=$(docker ps -q -n 1 -f name=$IMG_NAME)
if [ -z "$DOCKERPS_NSO" ] ;
then
    echo "Build & run $IMG_NAME"
else
    echo "Stop any existing $IMG_NAME container, then build & run"
    docker stop $IMG_NAME
fi

DOCKERPS_CONFD=$(docker ps -q -n 1 -f name="$APP_NAME")
if [ -z "$DOCKERPS_CONFD" ] ;
then
    echo "Build & run APP_NAME"
else
    echo "Stop any existing $APP_NAME container, then build & run"
    docker stop $APP_NAME
fi

DOCKERNETLS=$(docker network ls -q -f name=$NET_NAME)
if [ -z "$DOCKERNETLS" ] ;
then
    echo "Create $NET_NAME"
else
    echo "Remove and recreate any existing $NET_NAME network"
    docker network rm $NET_NAME
fi

docker build -t "confd-"$IMG_NAME --build-arg CONFD_VERSION=$CONFD_VERSION --build-arg APP_NAME=$APP_NAME -f Dockerfile.confd .
docker build -t $IMG_NAME --build-arg NSO_VERSION=$NSO_VERSION --build-arg APP_NAME=$APP_NAME -f Dockerfile .
docker network create $NET_NAME

echo "Run the ConfD container"
CONFD_CID="$(docker run --net $NET_NAME --name $APP_NAME -d --rm -p 12022:12022 "confd-"$IMG_NAME | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CONFD_CID) != $CONFD_CID ]]; do
    echo "waiting..."
    sleep .5
done

ecode=1;
while [ $ecode -ne 0 ]; do
    sleep .5 
    docker exec -it $APP_NAME confd --wait-started
    ecode=$?
done;

CID="$(docker run --net $NET_NAME --name $IMG_NAME -d --rm -p 18080:8080 $IMG_NAME | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CID) != $CID ]]; do
    echo "waiting..."
    sleep .5
done

echo "CID: $CID"
docker logs $IMG_NAME --follow
