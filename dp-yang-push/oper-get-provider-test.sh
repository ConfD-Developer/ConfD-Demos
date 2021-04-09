#!/bin/bash
NUM_START=$(echo "1" | bc)
NUM_MAX=$(echo "1000000" | bc)
START=$(date +%s.%N)
DIFF=""

function delta_time() {
    END=$(date +%s.%N)
    DIFF=$(echo "$END - $START" | bc)
    echo "*** Time in seconds to $1"
    echo "$DIFF seconds"
}

function test_dp() {
    NUM=$NUM_START
    echo "******************************** GET - Data provider ****************************"
    while true; do
        echo "--- starting data provider with the $NUM list entries"
        ./route-status $NUM &
        VAL=$(echo $NUM/2+1 | bc)

        echo "---netconf-console <get> - 1 leaf from entry with ID ${VAL}"
        START=$(date +%s.%N)
        netconf-console --get -x /route-status/route[id=\"${VAL}rt\"]/leaf3 > dp-route-data-${NUM}-leaf-entry-with-id-${VAL}.xml
        delta_time "get 1 leaf from entry with ID ${VAL} out of $NUM"

        echo "---netconf-console <get> - 1 list entry with ID ${VAL}"
        START=$(date +%s.%N)
        netconf-console --get -x /route-status/route[id=\"${VAL}rt\"] > dp-route-data-${NUM}-list-entry-with-id-${VAL}.xml
        delta_time "get 1 list entry with ID ${VAL} out of $NUM"

        echo "---netconf-console <get> - all records"
        START=$(date +%s.%N)
        netconf-console --get -x route-status > dp-route-data-${NUM}.xml
        delta_time "get $NUM list entries"

        AVG=$(echo "scale=10; $DIFF / $NUM" | bc)
        echo "$AVG seconds per list entry"

        killall -9 route-status
        if [ "$NUM" == "$NUM_MAX" ]; then
            break
        fi

        NUM=$(echo "$NUM*10" | bc)
    done
    echo "******************************** END ****************************"
}

make clean > /dev/null

make all
make start
test_dp
make stop
make clean
