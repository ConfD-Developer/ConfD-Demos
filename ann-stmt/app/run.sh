#!/bin/bash
rm -rf yang
mkdir -p yang

echo "*** Create a tailf:annotate-module/statement module and move over the tailf extensions from the original YANG module"
for f in yang-orig/*.yang
do
    echo "*** Processing $f"
    python3 tailf_ann_stmt.py -t -m -w -i -x -a -u -p -l -o yang $f
done

make stop clean all start

echo "*** resulting annotation modules"
cat yang/*-ann.yang

echo "*** tail -F devel.log"
tail -F devel.log
