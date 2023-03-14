*** Settings ***
Documentation    Core test suite for OpenConfig telemetry/gNMI tests,
...              the ``openconfig-interfaces.yang`` model.
...
...              Test cases were created with expectation of YANG model ``revision "2022-10-25"``.
Test Tags        OpenConfig  interfaces

Resource         openconfig.resource
Resource         interfaces.resource

Resource         ../gNMI_Interface/gNMIClient.resource
Suite Setup      Setup gNMI Client
Suite Teardown   Close gNMI Client
Test Teardown    Teardown gNMI state


*** Test Cases ***
Supported models include "openconfig-interfaces"
    [Documentation]    Verify that ``openconfig-interfaces`` is among the models
    ...                advertised as supported in the ``CapabilityResponse``.
    [Tags]  sanity
    Supported Models Should Include  openconfig-interfaces

Get "interfaces" with no parameters
    [Documentation]    Verify that basic ``GetRequest`` can be issued with ``path=interfaces``
    ...                parameter and OK response is received (ignoring data contents/payload).
    [Tags]  sanity
    Verify Get of  interfaces

Get "interfaces" with "type" parameter
    [Documentation]    Verify that OK response is retrieved for ``GetRequest`` having ``type=``
    ...                parameter with any of the defined ``DataType``s.
    [Tags]  type
    [Template]  Iterate path "${path}" with DataType ${type}
    interfaces  ALL
    interfaces  CONFIG
    interfaces  STATE
    interfaces  OPERATIONAL

Get "interfaces" for various "path" parameter values
    [Documentation]    Verify that various valid formats of root container/list
    ...                can be requested using ``path=`` parameter, and are responded to correctly.
    [Tags]  path  costly
    [Template]    Iterate Get of
    # no namespace
    interfaces
    interfaces/interface
    # root namespace
    openconfig-interfaces:interfaces
    openconfig-interfaces:interfaces/interface
    # non-root namespace
    interfaces/openconfig-interfaces:interface
    interfaces/openconfig-interfaces:interface
    # both namespaces
    openconfig-interfaces:interfaces/openconfig-interfaces:interface

Get "interfaces" with "encoding" parameter for all supported encodings
    [Documentation]    Verify that ``GetRequest`` with ``path=interfaces`` parameter
    ...                receives OK response for all/any of the supported Encoding values.
    [Tags]  encoding
    Skip

List "/interfaces/interface" contains at least one record
    [Documentation]    Verify that ``GetRequest`` with ``path=interfaces/interface`` parameter
    ...                receives OK response and contains at least one or more items.
    [Tags]  list
    Verify Get of  /interfaces/interface
    ${count}=  Get last updates count
    Should Not Be Equal As Integers   ${count}  0

Read existing "/interfaces/interface" list entries one by one
    [Documentation]    Verify that ``GetRequest`` with ``path=interfaces/interface[name]``
    ...                parameter receives OK response for all/any of the supported Encoding values.
    [Tags]  list  encoding
    Skip
    Verify Get of    /interfaces/interface
    # ${updates}=  Last updates

Try reading non-existing list entry from "/interfaces/interface"
    [Documentation]    Verify that ``GetRequest`` with ``path=interfaces/interface[non-existing-name]``
    ...                parameter for non-existing key value receives error response.
    [Tags]  negative  list
    Given Paths include  /interfaces/interface[name=non-existing-interface]
    When Dispatch Get Request
    Then Should Received Error Response

Read "prefix=/interfaces", "path=interface[]" list entries one by one
    [Documentation]    Verify that list can be iterated with separate prefix/path parameters.
    [Tags]  prefix  list
    Skip

Read "/interfaces/interface[]/name" key leaf from existing entry
    [Documentation]    Verify that key value can be read using Get request with path parameter.
    [Tags]  key  list
    Skip
    ${response}=  Get data from  /interfaces/interface[name=${OC_INTERFACE}]/name

Get "CONFIG" response includes "config" container
    [Documentation]    Verify that ``GetRequest`` with ``type=CONFIG`` parameter receives
    ...                OK response that does include the read/write YANG "config" container.
    [Tags]  config  container
    Given DataType set to    CONFIG
    When Verify Get of  /interfaces/interface[name=${OC_INTERFACE}]
    Then Check Last Updates Include    config

Get "CONFIG" response does not include "state" container
    [Documentation]    Verify that ``GetRequest`` with ``type=CONFIG`` parameter receives
    ...                OK response that does not include the read-only YANG "state" container.
    [Tags]  config  container  negative
    Given DataType set to    CONFIG
    When Verify Get of  /interfaces/interface[name=${OC_INTERFACE}]
    Then Check last updates not include    state

Get "OPERATIONAL" response includes "state" container
    [Documentation]    Verify that ``GetRequest`` with ``type=OPERATIONAL`` parameter receives
    ...                OK response that does include the read/write YANG "state" container.
    [Tags]  operational  container
    Given DataType set to    OPERATIONAL
    When Verify Get of  /interfaces/interface[name=${OC_INTERFACE}]
    Then Check last updates include  state

Get "OPERATIONAL" response does not include "config" container
    [Documentation]    Verify that ``GetRequest`` with ``type=OPERATIONAL`` parameter receives
    ...                OK response that does not include the read-only YANG "config" container.
    [Tags]  operational  container  negative
    DataType set to    OPERATIONAL
    Verify Get of  /interfaces/interface[name=${OC_INTERFACE}]
    Check last updates not include  config

Get "ALL" response includes both "config" and "state" containers
    [Documentation]    Verify that ``GetRequest`` with ``type=ALL`` parameter receives
    ...                OK response that does include both read-write "config" and read-only "state" containers.
    [Tags]  config  operational  container
    DataType set to    ALL
    Verify Get of  /interfaces/interface[name=${OC_INTERFACE}]
    Check last updates include  config
    Check last updates include  state

Get "config" response includes significant leaves
    [Documentation]    Verify that ``GetRequest`` with ``type=CONFIG`` parameter receives
    ...                OK response that does include standardized leaf names/items.
    [Tags]  config  leaf
    [Template]    Iterate interface "config" includes leaf
    name
    type
    mtu
    loopback-mode
    description
    enabled

Get "state" response includes significant leaves
    [Documentation]    Verify that ``GetRequest`` with ``type=OPERATIONAL`` parameter receives
    ...                OK response that does include standardized leaf names/items.
    [Tags]  operational  leaf
    # TODO - add all items to verify deviation from full official OC YANG?
    [Template]    Iterate interface "state" includes leaf
    name
    type
    mtu
    enabled
    ifindex
    admin-status
    oper-status

Get "config" works for all supported encodings
    [Documentation]    Verify that ``GetRequest`` with ``type=CONFIG``
    ...                and ``path=interfaces/interface[]/config`` parameters receives
    ...                OK response for all/any of the supported ``encoding` parameter values.
    [Tags]  config  container  encoding
    Skip

Get "state" works for all supported encodings
    [Documentation]    Verify that ``GetRequest`` with ``type=OPERATIONAL``
    ...                and ``path=interfaces/interface[]/state`` parameters receives
    ...                OK response for all/any of the supported ``encoding` parameter values.
    [Tags]  operational  container  encoding
    Skip
