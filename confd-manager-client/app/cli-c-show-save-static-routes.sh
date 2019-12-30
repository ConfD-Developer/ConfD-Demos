#!/bin/sh
confd_cli -C -u admin << EOF
show running-config router | save showsave.cfg
exit
EOF
