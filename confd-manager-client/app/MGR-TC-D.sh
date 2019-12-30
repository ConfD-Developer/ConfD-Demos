#!/bin/bash
ID=300

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

START_SUBS=0
STEP_SUBS=10
END_SUBS=10

for ((SUBS=START_SUBS; SUBS<=END_SUBS; SUBS+=STEP_SUBS))
do
    START_NUM=5000
    STEP_NUM=5000
    END_NUM=10000

    #echo "##### MGR TEST CASE D - SUBS=$SUBS #####"
    #echo "ID,NUM,TIME,RSS,HWM,TC"
    for ((NUM=START_NUM; NUM<=END_NUM; NUM+=STEP_NUM))
    do
	#echo ">>> Initializing D NUM=$NUM <<<"
	make stop clean all start-candidate &> /dev/null
	./ncgen.py trans_size_edit_config_candidate $NUM > trans_size_edit_config_candidate.xml
	#echo ">>> Connecting $SUBS subscriber applications <<<"
	for((i=0; i<SUBS; i+=1))
	do
           confd_cmd -c 'subwait_mods "/" i 2 "/" "suppress_defaults"' &> /dev/null &
	done
	#echo ">>> MGR TEST CASE D0 NC EDIT-CONFIG NUM=$NUM <<<"
	let ID+=1
	TC="D0-$SUBS"
	START=$($DATE +%s)
	netconf-console trans_size_edit_config_candidate.xml &> /dev/null
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

	#echo ">>> MGR TEST CASE D1 NC SAVE XML NUM=$NUM <<<"
	let ID+=1
	TC="D1-$SUBS"
	START=$($DATE +%s)
	netconf-console --get-config > nc-save.xml
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE D2a CLI-C SAVE NUM=$NUM <<<"
	let ID+=1
	TC="D2a-$SUBS"
	START=$($DATE +%s)
	./cli-c-save-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE D2b CLI-C SHOW SAVE NUM=$NUM <<<"
	let ID+=1
	TC="D2b-$SUBS"
	START=$($DATE +%s)
	./cli-c-show-save-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
	
	#echo ">>> MGR TEST CASE D3a CLI-C SAVE XML NUM=$NUM <<<"
	let ID+=1
	TC="D3a-$SUBS"
	START=$($DATE +%s)
	./cli-c-save-xml-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE D3b CLI-C SHOW SAVE XML NUM=$NUM <<<"
	let ID+=1
	TC="D3b-$SUBS"
	START=$($DATE +%s)
	./cli-c-show-save-xml-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE D4a CLI-C OVERRIDE SAVE NUM=$NUM <<<"
	let ID+=1
	TC="D4a-$SUBS"
	mv save.xml saveD1.xml
	mv save.cfg saveD1.cfg 
	make stop save-override start &> /dev/null
	START=$($DATE +%s)
	./cli-c-save-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE D4b CLI-C OVERRIDE SAVE XML NUM=$NUM <<<"
	let ID+=1
	TC="D4b-$SUBS"
	START=$($DATE +%s)
	./cli-c-save-xml-static-routes.sh &> /dev/null
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"


	#echo ">>> MGR TEST CASE D5a MAAPI SAVE CLI-C NUM=$NUM <<<"
	let ID+=1
	TC="D5a-$SUBS"
	START=$($DATE +%s)
	confd_load -F c -p /router > maapi-save.cfg
	END=$($DATE +%s)
	TIME=$(($END-$START))
	pid=($(pidof confd))
	PID=$(echo ${pid[0]})
	MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
	arr=($MEM)
	HWM=$(echo ${arr[1]})
	RSS=$(echo ${arr[4]})
	echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

	#echo ">>> MGR TEST CASE D5b MAAPI SAVE XML NUM=$NUM <<<"
	let ID+=1
	TC="D5b-$SUBS"
	START=$($DATE +%s)
	confd_load -F p -p /router > maapi-save.xml
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
