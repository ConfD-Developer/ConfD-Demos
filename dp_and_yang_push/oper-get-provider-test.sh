#!/bin/bash
NUMLE_START=$(echo "1" | bc)
NUMLE_MAX=$(echo "1000000" | bc)
START=$(date +%s.%N)
DIFF=""

function delta_time() {
    END=$(date +%s.%N)
    DIFF=$(echo "$END - $START" | bc)
    echo "*** Time in seconds to $1"
    echo "$DIFF seconds"
}

function test_dp() {
    NUMLE=$NUMLE_START
    echo "******************************** GET - Data provider ****************************"
    while true; do
        echo "--- starting data provider with the $NUMLE list entries"
        ./route-status $NUMLE &
        VAL=$(echo $NUMLE/2+1 | bc)

        echo "---netconf-console <get> - 1 leaf from entry with ID ${VAL}"
        START=$(date +%s.%N)
        netconf-console --get -x /route-status/route[id=\"${VAL}rt\"]/leaf3 > dp_route-data-${NUMLE}-leaf-entry-with-id-${VAL}.xml
        delta_time "get 1 leaf from entry with ID ${VAL} out of $NUMLE"

        echo "---netconf-console <get> - 1 list entry with ID ${VAL}"
        START=$(date +%s.%N)
        netconf-console --get -x /route-status/route[id=\"${VAL}rt\"] > dp_route-data-${NUMLE}-list-entry-with-id-${VAL}.xml
        delta_time "get 1 list entry with ID ${VAL} out of $NUMLE"

        echo "---netconf-console <get> - all records"
        START=$(date +%s.%N)
        netconf-console --get -x route-status > dp_route-data-${NUMLE}.xml
        delta_time "get $NUMLE list entries"

        AVG=$(echo "scale=10; $DIFF / $NUMLE" | bc)
        echo "$AVG seconds per list entry"

        killall -9 route-status
        if [ "$NUMLE" == "$NUMLE_MAX" ]; then
            break
        fi

        NUMLE=$(echo "$NUMLE*10" | bc)
    done
    echo "******************************** END ****************************"
}

make clean > /dev/null

make all
make start
test_dp
make stop
make clean
