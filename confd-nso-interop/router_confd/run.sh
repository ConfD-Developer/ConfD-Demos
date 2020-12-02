#!/bin/bash
CONFD_VERSION=${CONFD_VERSION}
CONFD_DIR=${CONFD_DIR}
VERBOSITY="normal"
APP_NAME=${APP_NAME}

cd "/"$APP_NAME"_confd"
make all
cp sys.xml confd-cdb/
echo "Starting ConfD-$CONFD_VERSION..."
make start
cd tools && make all && cd -

/confd/bin/confd_cli -n -u admin -C << EOF
config
unhide debug
progress trace trans-demo enabled verbosity $VERBOSITY destination file progress.trace format log
commit
top
exit
exit
EOF

"/"$APP_NAME"_confd"/tools/confd_cmd -dd -c 'smx / 1 100 "suppress_defaults"' 2>&1 | tee -a netconf-$APP_NAME.trace &

echo "tail -F /$(echo "$APP_NAME")_confd/devel.log"
tail -F /$(echo "$APP_NAME")_confd/devel.log
exit
