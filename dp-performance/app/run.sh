#!/bin/bash
ID=0
TC_NUMS=( 1000 5000 10000 15000 20000 )
TC_NAME=( "NCGETD" "NCGETA" "RCGETA" "MSAVEX" "MSAVEJ" "MITERA" "MGOBJS" )
TC_TYPE=( "ROUTES" "ALL" )

echo "ID,NUM,TIME,RSS,HWM,TC"

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

for NUM in "${TC_NUMS[@]}"
do
    for TYPE in "${TC_TYPE[@]}"
    do
        for TC in "${TC_NAME[@]}"
        do
            make stop clean all &> /dev/null
            ${CONFD} --start-phase0 -c confd.conf --addloadpath ${CONFD_DIR}/etc/confd --addloadpath fxs
            ${CONFD} --start-phase1
            ./cdboper_dp -s -p '/r-state:sys' -c 'oper-cp' &> /dev/null &
            ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name" > /dev/null; ecode=$?; done;
            if [ $TYPE == "ALL" ]; then
                ./cdbgen.py gen-cfg $NUM > init_cfg.xml
                ./cdbgen.py gen-state $NUM > init_state.xml
                confd_load -m -l init_cfg.xml
                confd_load -O -m -l init_state.xml
                ${CONFD} --start-phase2
                START=$($DATE +%s)
                if [ $TC == "NCGETA" ]; then
                    netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"/></filter></get>' &> /dev/null
                elif [ $TC == "NCGETD" ]; then
                    netconf-console --rpc=-<<<'<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:operational</datastore><subtree-filter><sys xmlns="http://example.com/router"/></subtree-filter><config-filter>false</config-filter></get-data>' &> /dev/null
                elif [ $TC == "RCGETA" ]; then
                    curl -s -u admin:admin http://localhost:8008/restconf/data/router:sys -H "Accept: application/yang-data+json" &> /dev/null
                elif [ $TC == "MSAVEX" ]; then
                    ./maapi-save -s -x -p "/r:sys" &> /dev/null
                elif [ $TC == "MSAVEJ" ]; then
                    ./maapi-save -s -j -p "/r:sys" &> /dev/null
                elif [ $TC == "MGOBJS" ]; then
                    ./maapi-get-objects -s -e 100 -p "/r:sys" &> /dev/null
                elif [ $TC == "MITERA" ]; then
                    ./maapi-iterate -s -p "/r:sys" &> /dev/null
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
            elif [ $TYPE == "ROUTES" ]; then
                ./cdbgen.py gen-state-routes $NUM > init_routes_state.xml
                confd_load -O -m -l init_routes_state.xml
                ${CONFD} --start-phase2
                START=$($DATE +%s)
                if [ $TC == "NCGETA" ]; then
                    netconf-console --rpc=-<<<'<get><filter type="subtree"><sys xmlns="http://example.com/router"><routes><inet><route/></inet></routes></sys></filter></get>' &> /dev/null
                elif [ $TC == "NCGETD" ]; then
                    netconf-console --rpc=-<<<'<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:operational</datastore><subtree-filter><sys xmlns="http://example.com/router"><routes><inet><route/></inet></routes></sys></subtree-filter><config-filter>false</config-filter></get-data>' &> /dev/null
                elif [ $TC == "RCGETA" ]; then
                    curl -s -u admin:admin http://localhost:8008/restconf/data/router:sys/routes/inet/route -H "Accept: application/yang-data+json" &> /dev/null
                elif [ $TC == "MSAVEX" ]; then
                    ./maapi-save -s -x -p "/r:sys/routes/inet/route" &> /dev/null
                elif [ $TC == "MSAVEJ" ]; then
                    ./maapi-save -s -j -p "/r:sys/routes/inet/route" &> /dev/null
                elif [ $TC == "MGOBJS" ]; then
                    ./maapi-get-objects -s -e 100 -p "/r:sys/routes/inet/route" &> /dev/null
                elif [ $TC == "MITERA" ]; then
                    ./maapi-iterate -s -p "/r:sys/routes/inet/route" &> /dev/null
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
            fi
            let ID+=1
        done
    done
done

tail -F devel.log
