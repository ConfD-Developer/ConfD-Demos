#!/bin/bash
ID=0
TC_NUMS=( 10 100 1000 )
TC_NAME=( "NCGETA" "NCGETD" "NCGETO" "RCGETA" "MSAVEX" "MSAVEJ" "MITERA" "MGOBJS" "CLISH" )
TC_TYPE=( "OPER" "RUN" "CAND" )
MAAPI_DS="-O"
NETCONF_DS="operational"
CALLPOINT="oper-cp"
LIBCONFD_LOG="./libconfd.log"
LOAD_DB="operational"

echo "ID,NUM,TIME,HWM,RSS,TC"

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

start() {
    confd --start-phase0 -c confd.conf --addloadpath ${CONFD_DIR}/etc/confd --addloadpath fxs
    confd --start-phase1
    ./cdboper_dp -l $LIBCONFD_LOG -s -c $CALLPOINT &> /dev/null &
    ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name" > /dev/null; ecode=$?; done;
    confd --start-phase2
}

for NUM in "${TC_NUMS[@]}"
do
    make stop clean all &> /dev/null
    start
    if [ $LOAD_DB == "candidate" ]; then # CDB running through candidate
        ./cdbgen.py gen $NUM > init.xml
        confd_load -o -m -l init.xml
    else # CDB operational
        ./cdbgen.py gen-state $NUM > init.xml
        confd_load -O -m -l init.xml
    fi
    make stop &> /dev/null
    for TYPE in "${TC_TYPE[@]}"
    do
        for TC in "${TC_NAME[@]}"
        do
            if [ $TYPE == "OPER" ]; then
                MAAPI_DS="-O"
                NETCONF_DS="operational"
            elif [ $TYPE == "RUN" ]; then
                MAAPI_DS="-R"
                NETCONF_DS="running"
            elif [ $TYPE == "CAND" ]; then
                MAAPI_DS="-C"
                NETCONF_DS="candidate"
            fi
            start
            START=$($DATE +%s)
            if [ $TC == "NCGETA" ]; then
                #netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"><routes><inet><route><next-hop><metric/></next-hop></route></inet></routes></sys></filter></get>'
                #netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"><dns><server/></dns></sys></filter></get>'
                #netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"><syslog><server><selector><facility/></selector></server></syslog></sys></filter></get>'
                #netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"><ntp><local-clock><status/></local-clock></ntp></sys></filter></get>'
                netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"/></filter></get>' &> /dev/null
            elif [ $TC == "NCGETO" ]; then
                netconf-console --rpc=-<<<'<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:'"$NETCONF_DS"'</datastore><subtree-filter><sys xmlns="http://example.com/router"/></subtree-filter><config-filter>false</config-filter></get-data>' &> /dev/null
            elif [ $TC == "NCGETD" ]; then
                netconf-console --rpc=-<<<'<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:'"$NETCONF_DS"'</datastore><subtree-filter><sys xmlns="http://example.com/router"/></subtree-filter></get-data>' &> /dev/null
            elif [ $TC == "RCGETA" ]; then
                curl -s -u admin:admin http://localhost:8008/restconf/data/router:sys -H "Accept: application/yang-data+json" &> /dev/null
            elif [ $TC == "MSAVEX" ]; then
                ./maapi-save -s $MAAPI_DS -x -p "/r:sys" &> /dev/null
            elif [ $TC == "MSAVEJ" ]; then
                ./maapi-save -s $MAAPI_DS -j -p "/r:sys" &> /dev/null
            elif [ $TC == "MGOBJS" ]; then
                ./maapi-get-objects -s $MAAPI_DS -e 100 -p "/r:sys" &> /dev/null
            elif [ $TC == "MITERA" ]; then
                ./maapi-iterate -s $MAAPI_DS -p "/r:sys" &> /dev/null
            elif [ $TC == "CLISH" ]; then
                ./cli-show-sys.sh &> /dev/null
            fi
            END=$($DATE +%s)
            TIME=$(($END-$START))
            pid=($(pidof confd.smp))
            PID=$(echo ${pid[0]})
            MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
            arr=($MEM)
            HWM=$(echo ${arr[1]})
            RSS=$(echo ${arr[4]})
            echo "$ID,$NUM,$TIME,$HWM,$RSS,$TC-$TYPE"
            mv libconfd.log libconfd.log.$ID
            mv devel.log devel.log.$ID
            make stop &> /dev/null
            let ID+=1
        done
    done
done

tail -F devel.log.0
