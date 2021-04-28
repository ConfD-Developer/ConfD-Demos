# Data provider demo with YANG Push
 
## Introduction

This demo example shows how to create ConfD data provider with support for YANG-Push 
functionality. The operational data changes are driven by example randomly in a separate thread. 

The example is partly written in C++ (mainly to use `thread`, `string`, `vector` and `map`). 
It also demonstrates how to use C++ with C ConfD API and use it in a ConfD Application.

In addition, simple performance test is provided to test data provider speed for various amount of data.

The data provider itself implements `get_elem`, `get_next`, `get_object` and `get_next_object` callbacks. For YANG-Push support example implements `subscribe_on_change` and `unsubscribe_on_change` callbacks.  
 
The example reuses some code form ConfD example found in `examples.confd/netconf_yang_push`. 

## Build and start

* to build example, use `make clean all`
* to start, use `make stop start` 
                               
## Yang push

(in other terminal)

* to see changes in operational data, use `make make on-change-subscription`
* to periodically fetch operational data, use `make periodic-subscription`

## Stop

* use `make stop`

## Performance

For simple DP performance measurement run `./oper-get-provider-test.sh` 
(this will  build, start application, run measurement, stop and clean application).

