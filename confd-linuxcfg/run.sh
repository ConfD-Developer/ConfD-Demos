#!/bin/bash
LC_PID=$(pidof linuxcfg)
kill $LC_PID
make stop clean
patch -n -i ./ietf_routing_provider.c.patch ./ietf_routing/ietf_routing_provider.c
patch -n -i ./ietf_routing_subscriber.c.patch ./ietf_routing/ietf_routing_subscriber.c
patch -n -i ./ipv6.c.patch ./ietf_ip/ipv6.c
make LINUXCFG_INIT=yes all install
cd .install/confd
confd -c  confd.conf --addloadpath /confd/etc/confd --addloadpath /confd/etc/confd/snmp --ignore-initial-validation --start-phase0
confd --start-phase1
./linuxcfg
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name"; ecode=$?; done;
confd --start-phase2
tail -F log/devel.log
