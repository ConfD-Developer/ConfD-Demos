Version history

```
--------------------------------------------------------------------------------
Version:  Date:         Description:                        Author:             
--------------------------------------------------------------------------------
0.0.1     2021-01-13    Initial version                     Michal Novák        
                                                            micnovak@cisco.com               
--------------------------------------------------------------------------------
```

## Dependencies

* Python3
* ConfD
* `make`


### python grpc

Install:
`pip install grpcio-tools`
           
NOTE: We expect that `python` nad `pip` are from Python3 environment. Use `python3` or `pip3`
if you have mixed Python2 and Python3 environemnt.
        
Update:
`pip install --upgrade grpcio-tools`

### `proto files`

Download into `proto` directory

```
https://github.com/openconfig/gnmi/blob/master/proto/gnmi/gnmi.proto
https://github.com/openconfig/gnmi/blob/master/proto/gnmi_ext/gnmi_ext.proto
```

In `gnmi.proto` change `gnmi_ext` import to  `import "gnmi_ext.proto";`

NOTE: This is done in this repository.

## Build

### `make`

`make all`  
`make clean`

### command line

Build gNMI python files

`python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/gnmi.proto`

## Run

### Server
                              
Run server in demo mode (running ConfD not needed):   
`./src/confd_gnmi_server.py` or `./src/confd_gnmi_server.py -t demo`

Run server in ConfD api mode (running ConfD needed `make clean all start`):
`./src/confd_gnmi_server.py -t api`

Supported server options:
 
```
Usage: confd_gnmi_server.py [options]

Options:
  -h, --help            show this help message and exit
  -t TYPE, --type=TYPE  gNMI server type  [api, netconf, demo]
  --logging=LOGGING     Logging level [error, warning, info, debug]
  -d CONFD_DEBUG, --confd-debug=CONFD_DEBUG
                        ConfD debug level  [trace, debug, silent, proto]
  --confd-addr=CONFD_ADDR
                        ConfD IP address (default is 127.0.0.1)
  --confd-port=CONFD_PORT
                        ConfD port (default is 4565)
```

NOTE: `netconf` type server not yet implemented
NOTE: Other parameters (e.g ports)  are currently hardcoded in source code (TODO)

### Client

(in other terminal than server)

`./src/confd_gnmi_client.py`

Supported options:

```
Usage: confd_gnmi_client.py [options]

Options:
  -h, --help            show this help message and exit
  -o OPERATION, --oper=OPERATION
                        gNMI operation [capabilities, set, get, subscribe]
  --logging=LOGGING     Logging level [error, warning, info, debug]
  --prefix=PREFIX       'prefix' path for set, get and subscribe operation
                        (empty by default)
  -p PATHS, --path=PATHS
                        'path' for get, set and subscribe operation, can be
                        repeated (empty by default)
  -v VALS, --val=VALS   'value' for set operation, can be repeated (empty by
                        default)
```
      
Examples:

`./src/confd_gnmi_client.py -o capabilities`  
`./src/confd_gnmi_client.py -o  get --prefix /interfaces --path interface[name=if_82]/name --path interface[name=if_82]/type`  
`./src/confd_gnmi_client.py -o set  --prefix /interfaces --path interface[name=if_82]/type --val fastEther`  
`./src/confd_gnmi_client.py -o subscribe --prefix /interfaces --path interface[name=if_82]/name --path interface[name=if_82]/type`

NOTE: Other parameters (username, password, subscription types are currently hardcoded, TODO)
    
## Limitations and TODOs of current implementation

* `encoding` - used only `BYTES`
* `Get`, `Set` and `Subscribe` works only on `leaf` elements
* `Subscribe` - only `ONCE` and `POLL` is implemented so far
    * `updates_only` not supported
    * `heartbeat_interval` not supported
    * `sync_response` not generated
* all values `TypedValues` are used as strings (`string_val`)
* gNMI Path is converted to XPath or formatted path with simple string operations 
  no datamodel knowledge used) 
  
## Investigations/TODOs

TODO converting XPath to ConfD formatted path/keypath and back.
(Work with `cs_node` for API adapter, for Netconf adapter ??)

## Analysis

We use (part) of `ietf-interfaces.yang` as sample datamodel.

### gNMI interface 

#### Capabilities

`rpc Capabilities(CapabilityRequest) returns (CapabilityResponse);`

`Capability` returns list of `supported_models` and list of `encodings`.
It can also return list of gNMI extensions.  

Each model has following attributes: 
 
`name` (string), `organization` (string), `version`

##### Implementation 

Capability information can be fetched from `"/ncm:netconf-state/ncm:capabilities/ncm:capability"`  
datamodel, found in the `ietf-netconf-monitoring.yang`.  

Another option can be to get it with `confd_get_nslist` API call:

Call  `confd_get_nslist`, array of following is returned:
```
struct confd_nsinfo {
    const char *uri;
    const char *prefix;
    u_int32_t hash;
    const char *revision;
    const char *module;
}; 
```

`name` -> `module`
`organization` -> TODO (cannot get with ConfD API, return empty string)
`version` -> `revision` (return revision string -date ?)

TODO: Pass yang file content as extension? HOW to get yang files from ConfD?

#### Get
  
`rpc Get(GetRequest) returns (GetResponse);`

Pass in request:
list of `path`, `type` (CONFIG, OPERATIONAL, STATE), `encoding`, 
list of models to be used (`use_models`)

Get in response list of `notifications`. 

TODOs:

* notification contains list of updated paths with values and deleted paths.
What should be returned? We return only `updated` paths.

* The notification should contain whole subtree for each request path.
This means, for each request path there will be list of paths in 
`update`, each with value.  

* Since there is a path associated with each value, for requests on nested lists
we have to find out, which elements are keys and add them to the Path(s).

* What value type should be for empty or presence container ??? (bool ???)

##### Implementation 

`maapi_save_config`  - can be used even for operational data (` MAAPI_CONFIG_WITH_OPER`).
Get subtree as XML, parse XML and create response.

TODOs:

* exception handling - currently mostly passed to gRPC
* currently, only leaf elements are supported 

#### Set
  
`rpc Set(SetRequest) returns (SetResponse);`

Pass in request list of paths to `delete`, list of paths and values to 
be replaced (`replace`) and list of paths and values to be updated (`update`).

TODOs:

* difference between replace and update.   -> gnNMI specification 3.4.4.
* should `replace` be supported?
 
Get in response list of Paths and what was done for each path (`response`).

Each gNMI `Set` call should be treated as transaction
 
#### Subscribe
  
`rpc Subscribe(stream SubscribeRequest) returns (stream SubscribeResponse);`

Stream subscription requests and get stream of subscription responses.

Subscription response is similar to `Get`, this means all data in 
given sub-tree is returned in response: 

`ONCE` and `POLL` mode of the `SubscriptionList`,
responses according to `heartbeat_interval`,
responses to `SAMPLE` mode in the `Subscription` element
                              
In other cases only updated values are sent:
`STREAM`  mode of the `SubscriptionList`,
when `updates_only` is set for `STREAM` mode,
when `suppress_redundant` is set for `SAMPLE` mode

There are many combinations how subscription response should behave. 
More description is in  
https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md#35-subscribing-to-telemetry-updates

## Testing

Initial `pytest` tests created in `test` directory. 
             
Use:
`pip install pytest` or `pip install --upgrade pytest`

Currently, there are only few unit tests - TODO

### Run tests

`make test` or `PYTHONPATH=src pytest -sv`

## Resources

### gRPC

https://grpc.io/docs/languages/python/basics/  
https://pypi.org/project/betterproto/

### gNMI 
 
https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md

https://opennetworking.org/wp-content/uploads/2019/10/NG-SDN-Tutorial-Session-2.pdf
https://www.ietf.org/proceedings/101/slides/slides-101-netconf-grpc-network-management-interface-gnmi-00
https://github.com/openconfig/gnmi  
https://pypi.org/project/gnmi-proto/    
https://community.cisco.com/t5/service-providers-documents/understanding-gnmi-on-ios-xr-with-python/ta-p/4014205  
https://github.com/akarneliuk/grpc_demo  
https://karneliuk.com/2020/05/gnmi-part-3-using-grpc-to-collect-data-in-openconfig-yang-from-arista-eos-and-nokia-sr-os/  
https://github.com/aristanetworks/pyopenconfig/tree/master/pyopenconfig
https://gnmic.kmrd.dev/basic_usage/
https://github.com/p4lang/PI/tree/master/proto#tentative-gnmi-support-with-sysrepo