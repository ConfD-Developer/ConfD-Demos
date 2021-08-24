#!/bin/bash
RED='\033[0;31m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
NC='\033[0;m' # No Color

LC_PID=$(pidof linuxcfg)
kill $LC_PID
make stop clean
make LINUXCFG_INIT=yes all install
cd .install/confd
confd -c  confd.conf --addloadpath /confd/etc/confd --addloadpath /confd/etc/confd/snmp --ignore-initial-validation --start-phase0
confd --start-phase1
./linuxcfg -t
ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -dd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name"; ecode=$?; done;
confd --start-phase2
printf "\n${GREEN}##### netconf get-data ds:operational subtree with-origin: ${PURPLE}<ietf-interfaces/>${NC}\n"
netconf-console --rpc=-<<<'<get-data xmlns:ds="urn:ietf:params:xml:ns:yang:ietf-datastores" xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:operational</datastore><subtree-filter><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/></subtree-filter><with-origin/></get-data>'
printf "\n${GREEN}##### netconf get-data ds:operational subtree with-origin: ${PURPLE}<routing/>${NC}\n"
netconf-console --rpc=-<<<'<get-data xmlns:ds="urn:ietf:params:xml:ns:yang:ietf-datastores" xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:operational</datastore><subtree-filter><routing xmlns="urn:ietf:params:xml:ns:yang:ietf-routing"/></subtree-filter><with-origin/></get-data>'
printf "\n${GREEN}##### netconf get: ${PURPLE}interfaces${NC}\n"
netconf-console --get -x /interfaces
printf "\n${GREEN}##### netconf get: ${PURPLE}routing${NC}\n"
netconf-console --get -x /routing
printf "\n${GREEN}##### netconf get: ${PURPLE}system${NC}\n"
netconf-console --get -x /system
tail -F log/devel.log
