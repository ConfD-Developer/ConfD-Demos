#!/bin/bash
./MGR-TC-A.sh
./MGR-TC-B.sh
./MGR-TC-C.sh
./MGR-TC-D.sh
tail -n 10 -F devel.log
