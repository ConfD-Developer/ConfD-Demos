#!/bin/bash
echo "Converting files back to YANG format"
mkdir -p yang
for f in yin/*.yinmod
do
  echo "Processing $f"
  FILEPATH=${f%.*}
  FILENAME=${FILEPATH##*/}
  python3 /usr/local/bin/pyang -p yin -p ${CONFD_DIR}/src/confd/yang -f yang $f > yang/$FILENAME.yang
done

make all start

echo "DONE with test"

echo "tail -F /app/devel.log"
tail -F /app/devel.log
exit
