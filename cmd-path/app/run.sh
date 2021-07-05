#!/bin/bash
RED='\033[0;31m'
BLUE='\033[0;34m'
ORANGE='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0;m' # No Color

source ${CONFD_DIR}/confdrc

rm -rf yang
mkdir -p yang

printf "\n${GREEN}####### ${RED}Step 1:${BLUE} tag the YANG model(s) using the tailf:meta-data/value YANG extension statements${NC}\n"
for f in yang-orig/*.yang
do
    echo "Processing $f"
    t="yang/$(basename $f)"
    python3 confd_tag_yang.py $f > $t
    printf "\n${GREEN}####### ${RED}Resulting${BLUE} tagged $t${NC}\n"
    cat $t
done

printf "\n${GREEN}####### ${RED}Step 2:${BLUE} create the cli-i-x-dump from the ConfD CDB schema and meta-data/value tags${NC}\n"
make all
cp confd_dyncfg_init.xml confd-cdb
${CONFD_DIR}/bin/confd -c confd.conf --ignore-initial-validation --addloadpath fxs --addloadpath ${CONFD_DIR}/etc/confd --addloadpath ${CONFD_DIR}/src/confd/dyncfg
python3 confd_cli_dump.py > cli_i_x_dump.xml
printf "\n${GREEN}####### ${RED}Resulting${BLUE} cli_i_x_dump.xml${NC}\n"
cat cli_i_x_dump.xml | xmllint --format -
tail -n 0 -F ./devel.log
