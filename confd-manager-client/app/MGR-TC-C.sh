#!/bin/bash
NUM=10000
ID=200

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

#echo "##### MGR TEST CASE C #####"
#echo "ID,NUM,TIME,RSS,HWM,TC"

#echo ">>> Initializing C $NUM static routes <<<"
make stop clean all start &> /dev/null
./ncgen.py trans_size_edit_config_running $NUM > trans_size_edit_config_running.xml
#echo ">>> MGR TEST CASE C1 $NUM static routes <<<"
let ID+=1
TC="C1"
START=$($DATE +%s)
netconf-console trans_size_edit_config_running.xml &> /dev/null
END=$($DATE +%s)
TIME=$(($END-$START))
pid=($(pidof confd))
PID=$(echo ${pid[0]})
MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
arr=($MEM)
HWM=$(echo ${arr[1]})
RSS=$(echo ${arr[4]})
echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

#echo ">>> MGR TEST CASE C2 $NUM static routes <<<"
let ID+=1
TC="C2.1"
START=$($DATE +%s)
for ((i=0;i<1;i++)); do
    netconf-console --get-config -s plain -x /router &> /dev/null &
    ./cli-c-show-static-routes.sh &> /dev/null &
    curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null &
done
wait

END=$($DATE +%s)
TIME=$(($END-$START))
pid=($(pidof confd))
PID=$(echo ${pid[0]})
MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
arr=($MEM)
HWM=$(echo ${arr[1]})
RSS=$(echo ${arr[4]})
echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

let ID+=1
TC="C2.10"
START=$($DATE +%s)
for ((i=0;i<10;i++)); do
    netconf-console --get-config -s plain -x /router &> /dev/null &
    ./cli-c-show-static-routes.sh &> /dev/null &
    curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null &
done
wait

END=$($DATE +%s)
TIME=$(($END-$START))
pid=($(pidof confd))
PID=$(echo ${pid[0]})
MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
arr=($MEM)
HWM=$(echo ${arr[1]})
RSS=$(echo ${arr[4]})
echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

#echo ">>> MGR TEST CASE C3 $NUM static routes <<<"
let ID+=1
TC="C3.10.1"
START=$($DATE +%s)
for ((i=0;i<10;i++)); do
    for ((j=0;j<1;j++)); do
	netconf-console --get-config -s plain -x /router &> /dev/null &
	./cli-c-show-static-routes.sh &> /dev/null &
	curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null &
    done
done
wait

END=$($DATE +%s)
TIME=$(($END-$START))
pid=($(pidof confd))
PID=$(echo ${pid[0]})
MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
arr=($MEM)
HWM=$(echo ${arr[1]})
RSS=$(echo ${arr[4]})
echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

let ID+=1
TC="C3.10.10"
START=$($DATE +%s)
for ((i=0;i<10;i++)); do
    for ((j=0;j<10;j++)); do
	netconf-console --get-config -s plain -x /router &> /dev/null &
	./cli-c-show-static-routes.sh &> /dev/null &
	curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null &
    done
done
wait

END=$($DATE +%s)
TIME=$(($END-$START))
pid=($(pidof confd))
PID=$(echo ${pid[0]})
MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
arr=($MEM)
HWM=$(echo ${arr[1]})
RSS=$(echo ${arr[4]})
echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
