#!/bin/sh
confd_cli -C -u admin << EOF
config
save save.xml xml router
exit
exit
EOF
