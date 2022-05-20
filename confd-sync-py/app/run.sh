#!/bin/bash
NUM_SUBNODES=20
NUM_NODES=$(($NUM_SUBNODES+1))
PORT_BASE=12022
SUB_PATHS=( '/r:sys/interfaces' '/r:sys/routes' '/r:sys/syslog' '/r:sys/ntp' '/r:sys/dns' )

cp $CONFD_DIR/bin/netconf-console ./netconf_console.py
make NNODES=$NUM_NODES stop clean
make NNODES=$NUM_NODES NETCONF_SSH_BASE=$PORT_BASE all
echo '<netconf-client xmlns="http://example.com/netconf-ssh-client">' > subnodes.xml
for ((i=1,j=0; i<NUM_NODES; i+=1,j+=1))
do
    make start$i
    PORT=$(($PORT_BASE+10*$i))
    if [ $j -eq ${#SUB_PATHS[@]} ]
    then
        j=0
    fi
    echo "<netconf-server><name>node$i</name><subscription-path>${SUB_PATHS[$j]}</subscription-path><remote-address>127.0.0.1</remote-address><remote-port>$PORT</remote-port><username>admin</username><password>admin</password></netconf-server>" >> subnodes.xml
done
echo '</netconf-client>' >> subnodes.xml
cd node0
confd --start-phase0 -c confd.conf --addloadpath $CONFD_DIR/etc/confd --addloadpath ../fxs
cd ..
confd_load -dd -i -m -l init.xml
confd_load -dd -i -m -l subnodes.xml
confd_cmd -dd -c "start-phase1"
python3 ./cdbl-sync-nc.py &
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name"; ecode=$?; done;
time confd_cmd -dd -c "maction /netconf-client/sync-to"
confd_cmd -dd -c "start-phase2"
wait
