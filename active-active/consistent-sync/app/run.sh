#!/bin/bash
RED='\033[0;31m'
BLUE='\033[0;34m'
ORANGE='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0;m' # No Color
TC_NUMS=( 10 100 )
PERSIST_ID=IQ,d4668
IPC_BASE=4565
NETCONF_BASE=2023
DO_DEBUG_LOG=1
if [[ $DO_DEBUG_LOG = 0 ]]; then
   exec 1> /dev/null
fi

NBASE0="$(($NETCONF_BASE+10*0))"
NBASE1="$(($NETCONF_BASE+10*1))"
NBASE2="$(($NETCONF_BASE+10*2))"
NBASE3="$(($NETCONF_BASE+10*3))"

for NUMLE in "${TC_NUMS[@]}"
do
    printf "${RED}>>>>>>#1 CDB RUNNING<<<<<<${NC}\n" 1>&2
    printf "${BLUE}---Building and starting 3 active-active sync ConfD's loading $NUMLE list entries to RUNNING datastore at startup${NC}\n" 1>&2
    if [[ $DO_DEBUG_LOG = 0 ]]; then
        make NUMLE=$NUMLE stop3 clean all
	time make start
    else
	make NUMLE=$NUMLE DO_DEBUG_LOG=-DDO_DEBUG_LOG stop3 clean all
	time make DO_DEBUG_LOG=-DDO_DEBUG_LOG start
    fi
	
    printf "${BLUE}---Have a fourth node (node 3) join and sync with the cluster through node 0 at startup${NC}\n" 1>&2
    if [[ $DO_DEBUG_LOG = 0 ]]; then
	time make join3
    else
	time make DO_DEBUG_LOG=-DDO_DEBUG_LOG join3
    fi
    
    printf "${BLUE}---Delete all $NUMLE list entries for all nodes in the cluster through the forth node's (node 3) RUNNING datastore${NC}\n" 1>&2
    ./ncgen.py delete_routes_config > del.xml
    time netconf-console-tcp --port=$NBASE3 del.xml

    printf "${BLUE}---Have the fourth node (node 3) leave the cluster${NC}\n" 1>&2
    if [[ $DO_DEBUG_LOG = 0 ]]; then
	time make leave3
    else
	time make DO_DEBUG_LOG=-DDO_DEBUG_LOG leave3
    fi
    
    printf "${BLUE}---NETCONF <edit-config> $NUMLE list entries to all nodes in the cluster via node 1's RUNNING datastore${NC}\n" 1>&2
    ./ncgen.py edit_config_running  $NUMLE > init.xml
    time netconf-console-tcp --port=$NBASE1 init.xml
    
    printf "${BLUE}---Do a NETCONF <get-config> from node 2${NC}\n" 1>&2
    time netconf-console-tcp --port=$NBASE2 -s pretty --get-config -x /active-cfg/routes/route
    
    printf "${RED}>>>>>>#2 CDB CANDIDATE<<<<<<${NC}\n" 1>&2
    printf "${BLUE}---Building and starting 3 active-active sync ConfD's loading $NUMLE list entries to RUNNING datastore at startup${NC}\n" 1>&2
    if [[ $DO_DEBUG_LOG = 0 ]]; then
	make NUMLE=$NUMLE stop3 clean all
	time make start
    else
	make NUMLE=$NUMLE DO_DEBUG_LOG=-DDO_DEBUG_LOG stop3 clean all
	time make DO_DEBUG_LOG=-DDO_DEBUG_LOG start
    fi
    

    printf "${BLUE}---Have a fourth node (node 3) join and sync with the cluster through node 0 at startup${NC}\n" 1>&2
    if [[ $DO_DEBUG_LOG = 0 ]]; then
	time make join3
    else
	time make DO_DEBUG_LOG=-DDO_DEBUG_LOG join3
    fi
    
    printf "${BLUE}---Do a NETCONF <get-config> from node 3${NC}\n" 1>&2
    time netconf-console-tcp --port=$NBASE3 -s pretty --get-config -x /active-cfg/routes/route
    
    printf "${BLUE}---Delete all $NUMLE list entries for all nodes in the cluster through the forth node's (node 3) CANDIDATE datastore${NC}\n" 1>&2
    ./ncgen.py delete_routes_config > del.xml
    time netconf-console-tcp --port=$NBASE3 del.xml --commit

    printf "${BLUE}---Have the fourth node (node 3) leave the cluster${NC}\n" 1>&2
    if [[ $DO_DEBUG_LOG = 0 ]]; then    
	time make leave3
    else
	time make DO_DEBUG_LOG=-DDO_DEBUG_LOG leave3	
    fi
    
    printf "${BLUE}---NETCONF <edit-config> $NUMLE list entries to node 1's CANDIDATE datastore with confirmed commit (persist-id $PERSIST_ID) to running${NC}\n" 1>&2
    ./ncgen.py edit_config_candidate_confirmed_commit $NUMLE $PERSIST_ID > init.xml
    time netconf-console-tcp --port=$NBASE1 init.xml

    printf "${BLUE}---Confirm the commit to node 1 with the persist-id $PERSIST_ID${NC}\n" 1>&2
    ./ncgen.py confirm_commit $PERSIST_ID > confirm.xml
    time netconf-console-tcp --port=$NBASE1 confirm.xml
    
    printf "${BLUE}---Do a NETCONF <get-config> from node 2${NC}\n" 1>&2
    time netconf-console-tcp --port=$NBASE2 -s pretty --get-config -x /active-cfg/routes/route
done

make stop3
tail -F node0/devel.log
