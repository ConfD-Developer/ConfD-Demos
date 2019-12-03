#!/bin/bash
CID="$(docker run --name drned-xmnr-demo -d --rm -p 2022:2022 -p 12022:12022 -p 4565:4565 -p 4569:4569 -p 8080:8080 drned-xmnr-demo | cut -c1-12)"

while [[ $(docker ps -l -a -q -f status=running | grep $CID) != $CID ]]; do
    echo "waiting..."
    sleep .5
done

echo "CID: $CID"
docker logs drned-xmnr-demo --follow
