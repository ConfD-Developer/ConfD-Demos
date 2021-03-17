#!/bin/bash
CONFD_VERSION="7.5.1"
IMG_NAME="consistent-sync"

function version_gt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"; }

VSN7=7
VSN73=7.3.99
if version_gt $CONFD_VERSION $VSN73; then
  if [ -f confd-$CONFD_VERSION.linux.x86_64.installer.bin ]
  then
      echo "Using:"
      echo "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
  else
      echo >&2 "This demo require that the ConfD SDK installer has been placed in this folder."
      echo >&2 "E.g.:"
      echo >&2 "confd-$CONFD_VERSION.linux.x86_64.installer.bin"
      echo >&2 "Aborting..."
      exit
  fi
else
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

if version_gt $CONFD_VERSION $VSN73; then
  docker build -t $IMG_NAME --build-arg CONFD_VERSION=$CONFD_VERSION -f Dockerfile .
elif version_gt $CONFD_VERSION $VSN7; then
  docker build -t $IMG_NAME --build-arg CONFD_VERSION=$CONFD_VERSION -f Dockerfile.pre74 .
else
  docker build -t $IMG_NAME --build-arg CONFD_VERSION=$CONFD_VERSION -f Dockerfile.pre7 .
fi
CID="$(docker run --name $IMG_NAME -d --rm -p 2022:2022 $IMG_NAME | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CID) != $CID ]]; do
    echo "waiting..."
    sleep .5
done

echo "CID: $CID"
docker logs $IMG_NAME --follow
