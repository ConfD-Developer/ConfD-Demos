#!/bin/bash
CUSR=$1
CGRP=$2
FILE=$3
FMT=""
if [ "$4" == "xml" ]; then
    FMT="| display xml"
    shift
fi
shift
shift
shift
SPATH="$*"

confd_cli -C -u $CUSR -g $CGRP << EOF
show running-config $SPATH $FMT | save $FILE
exit
EOF
