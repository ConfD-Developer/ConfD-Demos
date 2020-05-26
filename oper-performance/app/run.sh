#!/bin/bash
TC_NUMS=( 5 1000 5000 10000 20000 )
TC_NAME=( "WRITE" "WRITE-SUB" "TRIGGER-SUB" "LOAD" "LOAD-SUB" "NC-GET" )
ID=1

echo "ID,NUM,TIME,HWM,RSS,TC"

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

for NUM in "${TC_NUMS[@]}"
do
  for TC in "${TC_NAME[@]}"
  do
    # Building and starting ConfD
    make stop clean all start &> /dev/null
    if [ $TC == "LOAD" ]; then
      # maapi_load only
      ./cdbgen.py $NUM > oper-init.xml
      START=$($DATE +%s)
      confd_load -O -m -l oper-init.xml
      END=$($DATE +%s)
    elif [ $TC == "LOAD-SUB" ]; then
      # maapi_load with subscriber
      ./cdbgen.py $NUM > oper-init.xml
      ./per-cdb-r &
      ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name" > /dev/null; ecode=$?; done;
      START=$($DATE +%s)
      confd_load -O -m -l oper-init.xml
      END=$($DATE +%s)
    elif [ $TC == "WRITE" ]; then
      # cdb_set_values() only
    	START=$($DATE +%s)
    	./per-cdb-w -n $NUM
    	END=$($DATE +%s)
    elif [ $TC == "WRITE-SUB" ]; then
      # cdb_set_values() with subscriber"
      ./per-cdb-r &
      ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name" > /dev/null; ecode=$?; done;
      START=$($DATE +%s)
      ./per-cdb-w -n $NUM
      END=$($DATE +%s)
    elif [ $TC == "TRIGGER-SUB" ]; then
      # cdb_trigger_subscribers() with subscriber
      ./cdbgen.py $NUM > oper-init.xml
      confd_load -O -m -l oper-init.xml
      ./per-cdb-r &
      ecode=1; while [ $ecode -ne 0 ]; do sleep .5; confd_cmd -o -c "mget /tfcm:confd-state/tfcm:internal/tfcm:cdb/tfcm:client{1}/tfcm:name" > /dev/null; ecode=$?; done;
      START=$($DATE +%s)
      confd_cmd -o -c "trigger"
      END=$($DATE +%s)
    elif [ $TC == "NC-GET" ]; then
      # NETCONF read from operational data store
      ./cdbgen.py $NUM > oper-init.xml
      confd_load -O -m -l oper-init.xml
      START=$($DATE +%s)
      netconf-console --rpc=-<<<'<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda"><datastore>ds:operational</datastore><subtree-filter><routes xmlns="http://tail-f.com/ns/example/routes/1.0"/></subtree-filter><config-filter>false</config-filter></get-data>' &> /dev/null
      END=$($DATE +%s)
    fi

    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$HWM,$RSS,$TC"
    let ID+=1
  done
done

tail -F devel.log
