#!/bin/bash
ID=0
TC_NUMS=( 5 1000 5000 10000 )
TC_NAME=( "RCGETA" "NCGETD" "NCGETO" "NCGETA" "RCGETA" "MSAVEX" "MSAVEJ" "MITERA" "MGOBJS" "CLISH" )
TC_TYPE=( "OPER" "RUN" "CAND" )
MAAPI_DS="-O"
NETCONF_DS="operational"
CALLPOINT="oper-cp"
LIBCONFD_LOG="./libconfd.log"

echo "ID,NUM,TIME,HWM,RSS,TC"

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

for TYPE in "${TC_TYPE[@]}"
do
    for NUM in "${TC_NUMS[@]}"
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
            make stop clean all &> /dev/null
            ${CONFD} --start-phase0 -c confd.conf --addloadpath ${CONFD_DIR}/etc/confd --addloadpath fxs
            ${CONFD} --start-phase1
            ./cdboper_dp -l $LIBCONFD_LOG -t -c $CALLPOINT &
            ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name" > /dev/null; ecode=$?; done;
            ./cdbgen.py gen-nmda $NUM > init_nmda.xml
            confd_load -o -m -l init_nmda.xml
            ./cdbgen.py gen-nmda-state $NUM > init_nmda.xml
            confd_load -O -m -l init_nmda.xml
            ${CONFD} --start-phase2
            START=$($DATE +%s)
            if [ $TC == "NCGETA" ]; then
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
            pid=($(pidof confd))
            PID=$(echo ${pid[0]})
            MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
            arr=($MEM)
            HWM=$(echo ${arr[1]})
            RSS=$(echo ${arr[4]})
            echo "$ID,$NUM,$TIME,$HWM,$RSS,$TC-$TYPE"
            let ID+=1
        done
    done
done

tail -F libconfd.log
