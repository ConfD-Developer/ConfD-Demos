#!/bin/bash
source /confd/confdrc
make all
mkdir logs
confd --start-phase0 -c confd.conf --addloadpath /confd/etc/confd
confd_load -dd -i -m -l init.xml
confd_cmd -dd -c "start-phase1"
tail -n 7 -F logs/devel.log &
confd_cmd -dd -c 'sm /folder-user{"test"} 2 100 /' &
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name"; ecode=$?; done
python ./modif-subscriber.py &
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{2}/tfcm:name"; ecode=$?; done;
confd_cmd -dd -c "trigger_subscriptions" &
confd_cmd -dd -c "start-phase2"
wait %3
