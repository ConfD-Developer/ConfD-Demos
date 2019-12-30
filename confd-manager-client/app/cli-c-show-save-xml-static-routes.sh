#!/bin/sh
confd_cli -C -u admin << EOF
show running-config router | display xml | save showsave.xml
exit
EOF
