#!/bin/bash
rm -rf yang
mkdir -p yang

echo "Create a tailf:annotate-module/statement module and sanetize the original YANG module"
for f in yang-orig/*.yang
do
    echo "Processing $f"
    python3 tailf_ann_stmt.py $f
done

make stop clean all start

echo "tail -F devel.log"
tail -F devel.log
