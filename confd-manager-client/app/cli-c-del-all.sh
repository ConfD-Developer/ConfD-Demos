#!/bin/sh
confd_cli -C -u admin << EOF
config t
no router
commit
exit
exit
EOF
