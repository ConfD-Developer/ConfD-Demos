#!/bin/sh
confd_cli -C -u admin << EOF
config t
no router static address-family ipv4 unicast destination 192.0.0.0/24 172.16.1.2
commit
exit
exit
EOF
