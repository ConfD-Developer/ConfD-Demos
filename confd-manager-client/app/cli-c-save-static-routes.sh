#!/bin/sh
confd_cli -C -u admin << EOF
config
save save.cfg router
exit
exit
EOF
