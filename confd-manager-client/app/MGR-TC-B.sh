#!/bin/bash
START_NUM=500
STEP_NUM=500
END_NUM=1000
ID=100

if hash gdate 2> /dev/null; then
    DATE=gdate
else
    DATE=date
fi

#echo "##### MGR TEST CASE B1 #####"
#echo "ID,NUM,TIME,RSS,HWM,TC"
for ((NUM=START_NUM; NUM<=END_NUM; NUM+=STEP_NUM))
do
    #echo ">>> Initializing B1 NUM=$NUM <<<"
    make stop clean all start-candidate &> /dev/null
    ./ncgen.py trans_size_edit_config_candidate $NUM > trans_size_edit_config_candidate.xml
    #echo ">>> MGR TEST CASE B1-1 NUM=$NUM <<<"
    let ID+=1
    TC="B1"
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

    #echo ">>> MGR TEST CASE B1-2a NUM=$NUM <<<"
    let ID+=1
    TC="B1-2a"
    START=$($DATE +%s)
    netconf-console --db=candidate --get-config -s plain -x /router &> /dev/null
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

    #echo ">>> MGR TEST CASE B1-2b NUM=$NUM <<<"
    let ID+=1
    TC="B1-2b"
    START=$($DATE +%s)
    netconf-console --commit &> /dev/null
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

    # Preparation for test case B2's CLI scripting
    echo "#!/bin/sh" > ./trans_size_cli-c_config$NUM.cmd
    echo "confd_cli -C -u admin << EOF" >> ./trans_size_cli-c_config$NUM.cmd
    echo "config t" >> ./trans_size_cli-c_config$NUM.cmd
    confd_load -F c -p /router >> ./trans_size_cli-c_config$NUM.cmd
    echo "commit" >> ./trans_size_cli-c_config$NUM.cmd
    echo "exit" >> ./trans_size_cli-c_config$NUM.cmd
    echo "exit" >> ./trans_size_cli-c_config$NUM.cmd
    echo "EOF" >> ./trans_size_cli-c_config$NUM.cmd
    chmod +x ./trans_size_cli-c_config$NUM.cmd
    
    #echo ">>> MGR TEST CASE B1-3 NUM=$NUM <<<"
    let ID+=1
    TC="B1-3"
    ./ncgen.py trans_delete_edit_config_candidate > trans_delete_edit_config_candidate.xml
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
    
    #echo ">>> MGR TEST CASE B1-4a NUM=$NUM <<<"
    let ID+=1
    TC="B1-4a.10"
    START=$($DATE +%s)
    for ((i=0;i<10;i++)); do
	netconf-console trans_size_edit_config_candidate.xml &> /dev/null
	netconf-console --db=candidate --get-config -s plain -x /router &> /dev/null
	netconf-console trans_delete_edit_config_candidate.xml &> /dev/null
    done
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
    TC="B1-4a.100"
    START=$($DATE +%s)
    for ((i=0;i<100;i++)); do
	netconf-console trans_size_edit_config_candidate.xml &> /dev/null
	netconf-console --db=candidate --get-config -s plain -x /router &> /dev/null
	netconf-console trans_delete_edit_config_candidate.xml &> /dev/null
    done
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
    
    #echo ">>> MGR TEST CASE B1-4b NUM=$NUM <<<"
    let ID+=1
    TC="B1-4b.10"
    START=$($DATE +%s)
    for ((i=0;i<10;i++)); do
	netconf-console trans_size_edit_config_candidate.xml &> /dev/null
	netconf-console --commit &> /dev/null
	netconf-console --get-config -s plain -x /router &> /dev/null
	netconf-console trans_delete_edit_config_candidate.xml &> /dev/null
    done
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
    TC="B1-4b.100"
    START=$($DATE +%s)
    for ((i=0;i<100;i++)); do
	netconf-console trans_size_edit_config_candidate.xml &> /dev/null
	netconf-console --db=candidate --get-config -s plain -x /router &> /dev/null
	netconf-console trans_delete_edit_config_candidate.xml &> /dev/null
    done
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

#echo "##### MGR TEST CASE B2 #####"
#echo "ID,NUM,TIME,RSS,HWM,TC"
for ((NUM=START_NUM; NUM<=END_NUM; NUM+=STEP_NUM))
do
    #echo ">>> Initializing B2 NUM=$NUM <<<"
    make stop clean all start &> /dev/null
    #echo ">>> MGR TEST CASE B2-1 NUM=$NUM <<<"
    let ID+=1
    TC="B2-1"
    START=$($DATE +%s)
    ./trans_size_cli-c_config$NUM.cmd &> /dev/null
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
    
    #echo ">>> MGR TEST CASE B2-2 NUM=$NUM <<<"
    let ID+=1
    TC="B2-2"
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
    
    #echo ">>> MGR TEST CASE B2-3 NUM=$NUM <<<"
    let ID+=1
    TC="B2-3"
    START=$($DATE +%s)
    ./cli-c-del-all.sh &> /dev/null
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
    
    #echo ">>> MGR TEST CASE B2-4 NUM=$NUM <<<"
    let ID+=1
    TC="B2-4.10"
    START=$($DATE +%s)
    for ((i=0;i<10;i++)); do
	./trans_size_cli-c_config$NUM.cmd &> /dev/null
	./cli-c-show-static-routes.sh &> /dev/null
	./cli-c-del-all.sh &> /dev/null
    done
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
    TC="B2-4.100"
    START=$($DATE +%s)
    for ((i=0;i<100;i++)); do
	./trans_size_cli-c_config$NUM.cmd &> /dev/null
	./cli-c-show-static-routes.sh &> /dev/null
	./cli-c-del-all.sh &> /dev/null
    done
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

#echo "##### MGR TEST CASE B3 #####"
#echo "ID,NUM,TIME,RSS,HWM,TC"
for ((NUM=START_NUM; NUM<=END_NUM; NUM+=STEP_NUM))
do
    #echo ">>> Initializing B3 NUM=$NUM <<<"
    make stop clean all start &> /dev/null
    ./rcgen.py trans_size_plain_patch_running $NUM > trans_size_plain_patch_running.xml
    #echo ">>> MGR TEST CASE B3-1 NUM=$NUM <<<"
    let ID+=1
    TC="B3-1"
    START=$($DATE +%s)
    curl -s -u admin:admin -T ./trans_size_plain_patch_running.xml -X PATCH http://127.0.0.1:8008/restconf/data -H "Content-Type: application/yang-data+xml" &> /dev/null
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"

    #echo ">>> MGR TEST CASE B3-2 NUM=$NUM <<<"
    let ID+=1
    TC="B3-2"
    START=$($DATE +%s)
    curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
    
    #echo ">>> MGR TEST CASE B3-3 NUM=$NUM <<<"
    let ID+=1
    TC="B3-3"
    START=$($DATE +%s)
    curl -s -X DELETE -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null
    END=$($DATE +%s)
    TIME=$(($END-$START))
    pid=($(pidof confd))
    PID=$(echo ${pid[0]})
    MEM=$(cat "/proc/$PID/status" | grep -A 1 VmHWM)
    arr=($MEM)
    HWM=$(echo ${arr[1]})
    RSS=$(echo ${arr[4]})
    echo "$ID,$NUM,$TIME,$RSS,$HWM,$TC"
    
    #echo ">>> MGR TEST CASE B3-4 NUM=$NUM <<<"
    let ID+=1
    TC="B3-4.10"
    START=$($DATE +%s)
    for ((i=0;i<10;i++)); do
	curl -s -u admin:admin -T ./trans_size_plain_patch_running.xml -X PATCH http://127.0.0.1:8008/restconf/data -H "Content-Type: application/yang-data+xml" &> /dev/null
	curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null
	curl -s -X DELETE -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null
    done
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
    TC="B3-4.100"
    START=$($DATE +%s)
    for ((i=0;i<100;i++)); do
	curl -s -u admin:admin -T ./trans_size_plain_patch_running.xml -X PATCH http://127.0.0.1:8008/restconf/data -H "Content-Type: application/yang-data+xml" &> /dev/null
	curl -s -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null
	curl -s -X DELETE -u admin:admin http://localhost:8008/restconf/data/router &> /dev/null
    done
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
