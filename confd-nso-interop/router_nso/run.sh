#!/bin/bash
NSO_VERSION=${NSO_VERSION}
APP_NAME=${APP_NAME}
VERBOSITY="normal"

make all
cd "/"$APP_NAME"_nso"
chmod 777 packages
make all
cp $APP_NAME"_init.xml" ncs-cdb

echo 'Build the NSO NETCONF NED package using the built-in NSO NETCONF NED builder'
mv ncs.conf.in ncs.conf
ncsc -c check-build.yang
echo "Starting NSO-$NSO_VERSION with our example specific ncs-conf..."
make start
python3 check-build.py &

/nso/bin/ncs_cli -u admin -C << EOF
devtools true
config
devices device $APP_NAME ssh fetch-host-keys
netconf-ned-builder project $APP_NAME 1.0 device $APP_NAME local-user admin vendor Tail-f
top
commit
unhide debug
progress trace trans-demo enabled verbosity $VERBOSITY destination file progress.trace format log
commit
end
devices device $APP_NAME connect
netconf-ned-builder project $APP_NAME 1.0 fetch-module-list overwrite
netconf-ned-builder project $APP_NAME 1.0 module * * deselect
netconf-ned-builder project $APP_NAME 1.0 module $APP_NAME* * select
netconf-ned-builder project $APP_NAME 1.0 module tailf* * deselect
netconf-ned-builder project $APP_NAME 1.0 module ietf* * deselect
show netconf-ned-builder project $APP_NAME module | nomore
netconf-ned-builder wait-for-pending
exit
EOF

/nso/bin/ncs_cli -u admin -C << EOF
devtools true
netconf-ned-builder project $APP_NAME 1.0 build-ned
netconf-ned-builder project $APP_NAME 1.0 export-ned to-directory /$(echo "$APP_NAME")_nso/packages
exit
EOF

ncs_load -o -Fp -p "/netconf-ned-builder/project/module/build-warning"
ncs_load -o -Fp -p "/netconf-ned-builder/project/module/build-error"

cd "/"$APP_NAME"_nso"/packages/
tar xfz ncs-$NSO_VERSION-$APP_NAME-nc-1.0.tar.gz
rm ncs-$NSO_VERSION-$APP_NAME-nc-1.0.tar.gz
cd -

/nso/bin/ncs_cli -u admin -C << EOF
packages reload
config
devices device $APP_NAME device-type netconf ned-id $APP_NAME-nc-1.0
commit
top
devices device $APP_NAME sync-from
devices device $APP_NAME ned-settings use-confirmed-commit true use-transaction-id true use-private-candidate true use-validate true
commit
exit
exit
EOF

netconf-console -s raw --host=$APP_NAME --user='admin' --password='admin' \
                --port=12022 --hello
/nso/bin/ncs_cli -n -u admin -C << EOF
show running-config devices device $APP_NAME config | display xml | save router-states/base.xml
config
devices device $APP_NAME compare-config
load merge router-states/sys2.xml
commit dry-run
commit
devices device $APP_NAME compare-config
load merge router-states/base.xml
commit dry-run
commit
devices device $APP_NAME compare-config
exit
exit
EOF

/nso/bin/ncs_cli -u admin -C << EOF
devices device $APP_NAME drned-xmnr setup setup-xmnr overwrite true
devices device $APP_NAME drned-xmnr state record-state state-name base
devices device $APP_NAME drned-xmnr state import-state-files merge true format xml file-path-pattern "router-states/sys*"
devices device $APP_NAME drned-xmnr transitions transition-to-state state-name base
devices device $APP_NAME drned-xmnr transitions explore-transitions
exit
EOF

echo "tail -F /$(echo "$APP_NAME")_nso/logs/ncs-python-vm-drned-xmnr.log"
tail -F /$(echo "$APP_NAME")_nso/logs/ncs-python-vm-drned-xmnr.log
exit
