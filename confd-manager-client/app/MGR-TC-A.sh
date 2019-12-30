#!/bin/bash
ID=0

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

START_SUBS=0
STEP_SUBS=10
END_SUBS=10

echo "ID,NUM,TIME,RSS,HWM,TC"
for ((SUBS=START_SUBS; SUBS<=END_SUBS; SUBS+=STEP_SUBS))
do
    START_NUM=5000
    STEP_NUM=5000
    END_NUM=10000

    #echo "##### MGR TEST CASE A #####"
    for ((NUM=START_NUM; NUM<=END_NUM; NUM+=STEP_NUM))
    do
	#echo ">>> Initializing A NUM=$NUM <<<"
	make stop clean all start-candidate &> /dev/null
	./ncgen.py trans_size_edit_config_candidate $NUM > trans_size_edit_config_candidate.xml
	#echo ">>> Connecting $SUBS subscriber applications <<<"
	for((i=0; i<SUBS; i+=1))
	do
           confd_cmd -c 'subwait_mods "/" i 2 "/" "suppress_defaults"' &> /dev/null &
	done
	#echo ">>> MGR TEST CASE A1 NUM=$NUM <<<"
	let ID+=1
	TC="A1-$SUBS"
	START=$($DATE +%s)
	netconf-console trans_size_edit_config_candidate.xml &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	   
	#echo ">>> MGR TEST CASE A2 NUM=$NUM <<<"
	let ID+=1
	TC="A2-$SUBS"
	START=$($DATE +%s)
	./cli-c-show-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE A3 NUM=$NUM <<<"
	let ID+=1
	TC="A3-$SUBS"
	START=$($DATE +%s)
	netconf-console --commit &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE A4a NUM=$NUM <<<"
	let ID+=1
	TC="A4a-$SUBS"
	START=$($DATE +%s)
	netconf-console --get-config -s plain -x /router &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE A4b NUM=$NUM <<<"
	let ID+=1
	TC="A4b-$SUBS"
	START=$($DATE +%s)
	./cli-c-show-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE A4c NUM=$NUM <<<"
	let ID+=1
	TC="A4c-$SUBS"
	START=$($DATE +%s)
	curl -s -u admin:admin http://localhost:8008/restconf/data/routing:router &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE A4d NUM=$NUM <<<"
	let ID+=1
	TC="A4d-$SUBS"
	START=$($DATE +%s)
	snmpwalk -M ${CONFD_DIR}/src/confd/snmp/mibs:. -m ./TAIL-F-ROUTING-MIB.mib -c public -v2c localhost:4000 enterprises &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE A5 NUM=$NUM <<<"
	let ID+=1
	TC="A5-$SUBS"
	START=$($DATE +%s)
	./cli-c-del-1-static-route.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE A6 NUM=$NUM <<<"
	let ID+=1
	TC="A6-$SUBS"
	START=$($DATE +%s)
	netconf-console --get-config -s plain -x /router &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE A7 NUM=$NUM <<<"
	let ID+=1
	TC="A7-$SUBS"
	./ncgen.py trans_delete_edit_config_candidate $NUM > trans_delete_edit_config_candidate.xml
	START=$($DATE +%s)
	netconf-console trans_delete_edit_config_candidate.xml &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE A8a NUM=$NUM <<<"
	let ID+=1
	TC="A8a-$SUBS"
	START=$($DATE +%s)
	netconf-console --get-config -s plain -x /router &> /dev/null
	END=$($DATE +%s) 
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE A8b NUM=$NUM <<<"
	let ID+=1
	TC="A8b-$SUBS"
	START=$($DATE +%s)
	./cli-c-show-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE A8c NUM=$NUM <<<"
	let ID+=1
	TC="A8c-$SUBS"
	START=$($DATE +%s)
	curl -s -u admin:admin http://localhost:8008/restconf/data/routing:router &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE A8d NUM=$NUM <<<"
	let ID+=1
	TC="A8d-$SUBS"
	START=$($DATE +%s)
	snmpwalk -M ${CONFD_DIR}/src/confd/snmp/mibs:. -m ./TAIL-F-ROUTING-MIB.mib -c public -v2c localhost:4000 enterprises &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
    done
done
