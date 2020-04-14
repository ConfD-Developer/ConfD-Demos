#!/bin/sh
confd_cli -C -u admin << EOF
show r:sys | notab
EOF
