#!/bin/sh
confd_cli -C -u admin << EOF
show running-config router
exit
exit
EOF
