*** Settings ***
Documentation    Resources specific to ``openconfig-interfaces.yang`` model.
Library          ../gNMI_Interface/GetLibrary.py    ${DEFAULT_ENCODING}
Library    Collections
Resource  openconfig.resource

*** Keywords ***

Get container includes
    [Tags]    robot:private
    [Arguments]    ${path}  ${leaf_name}
    Verify Get of  ${path}
    Check last updates include   ${leaf_name}

Get interface "config" includes leaf
    [Arguments]    ${leaf_name}
    DataType set to    CONFIG
    Get container includes  /interfaces/interface[name=${OC_INTERFACE}]/config  ${leaf_name}

Get interface "state" includes leaf
    [Arguments]    ${leaf_name}
    DataType set to    OPERATIONAL
    Get container includes  /interfaces/interface[name=${OC_INTERFACE}]/state  ${leaf_name}
