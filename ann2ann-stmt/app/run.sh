#!/bin/bash
CONFD_VERSION=${CONFD_VERSION}
CONFD_DIR=${CONFD_DIR}

rm -rf yin yang
mkdir -p yang
mkdir -p yin
mkdir -p tree

echo "Converting files to YANG tree diagrams"
for f in yang-orig/*.yang
do
  FILEPATH=${f%.*}
  FILENAME=${FILEPATH##*/}
  if [[ $f != *-ann.yang ]]
  then
    echo "Converting $FILENAME to YANG tree diagram"
    python3 /usr/local/bin/pyang -f tree -p yang-orig -p $CONFD_DIR/src/confd/yang --tree-print-groupings --tree-no-expand-uses -o tree/$FILENAME.tree yang-orig/$FILENAME.yang
  fi
done

echo "Converting files to YIN format"
for f in yang-orig/*.yang
do
  FILEPATH=${f%.*}
  FILENAME=${FILEPATH##*/}
  echo "Converting $FILENAME to YIN"
  python3 /usr/local/bin/pyang -p yang-orig -f yin -p ${CONFD_DIR}/src/confd/yang -o yin/$FILENAME.yin yang-orig/$FILENAME.yang
done

echo "Converting from tailf:annotate to tailf:annotation-module/statement"
for f in yin/*-ann.yin
do
  echo "Converting $f to use tailf:annotation-module/statement"
  if [[ $f == *-experimental-ann.yin ]]
  then
    FILEPATH=${f%-experimental-ann.*}
    python3 yin_ann_stmt.py -a $FILEPATH-experimental-ann.yin $FILEPATH.yin
    xmllint --format $FILEPATH-experimental-ann.yinmod > $FILEPATH-experimental-ann.yinmod2
    mv $FILEPATH-experimental-ann.yinmod2 $FILEPATH-experimental-ann.yinmod
  elif [[ $f == *-ann.yin ]]
  then
    FILEPATH=${f%-ann.*}
    python3 yin_ann_stmt.py -a $FILEPATH-ann.yin $FILEPATH.yin
    xmllint --format $FILEPATH-ann.yinmod > $FILEPATH-ann.yinmod2
    mv $FILEPATH-ann.yinmod2 $FILEPATH-ann.yinmod
  fi
done

echo "DONE converting all files"
NUM=$(find ./yin -name '*.yinmod' -exec grep -l '<conflict number="1' {} + | wc -l)
echo "There are $NUM files with conflicts that need to be resolved"
if [[ $NUM != 0 ]]
then
  find ./yin -name '*.yinmod' -exec grep -l '<conflict number="1' {} +
  echo "After sorting out any conflict and skipped tags manually, run the test.sh script"
else
  echo "Running the test.sh script to verify the conversion"
  ./test.sh
fi

echo "tail -F $f"
tail -n 1 -F $f
