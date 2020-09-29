#!/bin/bash
CONFD_VERSION=${CONFD_VERSION}
CONFD_DIR=${CONFD_DIR}

echo "Converting files to YIN format"
mkdir -p yin
for f in yang-orig/*.yang
do
    echo "Converting $f"
    FILEPATH=${f%.*}
    FILE=${FILEPATH##*/}
    python3 /usr/local/bin/pyang -p yang-orig -f yin -p ${CONFD_DIR}/src/confd/yang -o yin/$FILE.yin $f
done

echo "Converting from tailf:annotate to tailf:annotation-module/statement"
python3 yin_ann_stmt.py -a yin/$FILE-ann.yin yin/$FILE.yin
for f in yin/*.yinmod
do
  FILEPATH=${f%.*}
  mv $f $FILEPATH.yin
done

echo "Converting files back to YANG format"
mkdir -p yang
for f in yin/*.yin
do
  echo "Processing $f"
  FILEPATH=${f%.*}
  FILE=${FILEPATH##*/}
  python3 /usr/local/bin/pyang -p yin -p ${CONFD_DIR}/src/confd/yang -f yang $f > yang/$FILE.yang
done

make all start

echo "tail -F /app/devel.log"
tail -F /app/devel.log
exit
