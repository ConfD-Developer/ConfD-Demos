#!/bin/bash
CONFD_VERSION=${CONFD_VERSION}
NSO_VERSION=${NSO_VERSION}
VERBOSITY="normal"
APP_NAME=${APP_NAME}

function version_gt() { test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"; }
cd "/"$APP_NAME"_confd"
make all
echo "Starting CONFD-$CONFD_VERSION..."
make start
cd tools && make all && cd -
cd "/"$APP_NAME"_nso"
chmod 777 packages
make all
cp $APP_NAME"_init.xml" ncs-cdb
NSO52=5.2
if version_gt $NSO_VERSION $NSO52; then
    echo 'NSO version > 5.2 - using the built-in NETCONF NED builder'
    mv ncs.conf.in ncs.conf
    echo "Starting NSO-$NSO_VERSION with our example specific ncs-conf..."
    make start
    /nso/bin/ncs_cli -n -u admin -C << EOF
devtools true
config
devices device $APP_NAME ssh fetch-host-keys
netconf-ned-builder project $APP_NAME 1.0 device $APP_NAME local-user admin vendor tailf
commit
unhide debug
progress trace trans-demo enabled verbosity $VERBOSITY destination file progress.trace format log
commit
top
exit
devtools true
netconf-ned-builder project $APP_NAME 1.0 fetch-module-list overwrite
netconf-ned-builder project $APP_NAME 1.0 module * * deselect
netconf-ned-builder project $APP_NAME 1.0 module $APP_NAME* * select
netconf-ned-builder project $APP_NAME 1.0 module tailf* * deselect
netconf-ned-builder project $APP_NAME 1.0 module ietf* * deselect
show netconf-ned-builder project $APP_NAME 1.0 module | nomore
netconf-ned-builder project $APP_NAME 1.0 build-ned
netconf-ned-builder project $APP_NAME 1.0 export-ned to-directory /$(echo "$APP_NAME")_nso/packages
exit
EOF
cd "/"$APP_NAME"_nso"/packages/
tar xvfz ncs-$NSO_VERSION-$APP_NAME-nc-1.0.tar.gz
rm ncs-$NSO_VERSION-$APP_NAME-nc-1.0.tar.gz
cd -
else
    echo 'NSO version < 5.2 - using the Pioneer package to build the NETCONF NED'
    pip install --upgrade pip
    pip install --no-cache-dir paramiko
    apt-get update
    apt-get install -y --no-install-recommends libxml2-utils xsltproc
    apt-get autoremove -y && apt-get clean
    git clone https://github.com/NSO-developer/pioneer packages/pioneer
    cd packages/pioneer/src && make clean all && cd -
    mv ncs.conf.in ncs.conf
    echo "Starting NSO-$NSO_VERSION with our example specific ncs-conf..."
    make start
    /nso/bin/ncs_cli -n -u admin -C << EOF
config
devices device $APP_NAME ssh fetch-host-keys
commit
unhide debug
progress trace trans-demo enabled verbosity $VERBOSITY destination file progress.trace format log
commit
top
devices device $APP_NAME pioneer yang fetch-list
devices device $APP_NAME pioneer yang disable name-pattern *
devices device $APP_NAME pioneer yang enable name-pattern $APP_NAME*
devices device $APP_NAME pioneer yang enable name-pattern *
devices device $APP_NAME pioneer yang disable name-pattern iana-crypt-hash
devices device $APP_NAME pioneer yang disable name-pattern ietf-inet-types
devices device $APP_NAME pioneer yang disable name-pattern ietf-netconf-acm
devices device $APP_NAME pioneer yang disable name-pattern ietf-yang-types
devices device $APP_NAME pioneer yang disable name-pattern tailf*
devices device $APP_NAME pioneer yang show-list
devices device $APP_NAME pioneer yang download
devices device $APP_NAME pioneer yang check-dependencies
devices device $APP_NAME pioneer yang build-netconf-ned
devices device $APP_NAME pioneer yang install-netconf-ned
exit
exit
EOF
fi

/confd/bin/confd_cli -n -u admin -C << EOF
config
unhide debug
progress trace trans-demo enabled verbosity $VERBOSITY destination file progress.trace format log
commit
top
exit
exit
EOF

/nso/bin/ncs_cli -n -u admin -C << EOF
packages reload
config
devices device $APP_NAME device-type netconf ned-id $APP_NAME-nc-1.0
commit
top
devices device $APP_NAME sync-from
devices device $APP_NAME ned-settings use-confirmed-commit true use-transaction-id true use-private-candidate true use-validate true
devices device $APP_NAME trace pretty
commit
exit
exit
EOF

printf "(add-to-list \'auto-mode-alist \'(\"\\\\\.trace\\\\\\\\\\'\" . nxml-mode))\n(add-hook \'nxml-mode-hook \\'auto-revert-tail-mode)\n(add-hook \'auto-revert-tail-mode-hook \'end-of-buffer)\n(add-hook 'find-file-hook (lambda () (highlight-regexp \"/router_confd/progress.trace\")))\n(add-hook 'find-file-hook (lambda () (highlight-regexp \"/router_confd/progress.trace\")))\n(add-hook 'find-file-hook (lambda () (highlight-regexp \"device router\")))\n(add-hook 'find-file-hook (lambda () (highlight-regexp \"Initialization done\")))\n" > ~/.emacs

tail -F "/"$APP_NAME"_nso"/logs/netconf-$APP_NAME.trace \
     -F "/"$APP_NAME"_nso"/logs/progress.trace \
     > netconf-$APP_NAME.trace &

cd "/"$APP_NAME"_nso"/tools && make -f Makefile all && cd -
"/"$APP_NAME"_confd"/tools/confd_cmd -dd -c 'smx / 1 100 "suppress_defaults"' 2>&1 | tee -a netconf-$APP_NAME.trace &

/nso/bin/ncs_cli -n -u admin -C << EOF
devices device $APP_NAME drned-xmnr setup setup-xmnr overwrite true
devices device $APP_NAME drned-xmnr state record-state state-name base
devices device $APP_NAME drned-xmnr state import-state-files merge true format xml file-path-pattern "$APP_NAME-states/*.xml"
devices device $APP_NAME drned-xmnr transitions transition-to-state state-name base
devices device $APP_NAME drned-xmnr coverage reset
devices device $APP_NAME drned-xmnr transitions explore-transitions
devices device $APP_NAME drned-xmnr coverage collect yang-patterns [ /$(echo "$APP_NAME")_nso/packages/$APP_NAME-nc-1.0/src/yang/*.yang ]
exit
EOF
echo "tail -F /$(echo "$APP_NAME")_nso/logs/ncs-python-vm-drned-xmnr.log"
tail -F /$(echo "$APP_NAME")_nso/logs/ncs-python-vm-drned-xmnr.log
exit
