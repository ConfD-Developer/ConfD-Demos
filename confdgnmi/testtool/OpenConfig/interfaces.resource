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
    # [Arguments]    ${interface}  ${leaf_name}
    # Get container includes  /interfaces/interface['${interface}']/config  ${leaf_name}
    # TODO - interface
    [Arguments]    ${leaf_name}
    Set Datatype To    CONFIG
    Get container includes  /interfaces/interface[name=${INTERFACE}]/config  ${leaf_name}

Get interface "state" includes leaf
    # [Arguments]    ${interface}  ${leaf_name}
    # Get container includes  /interfaces/interface[${interface}]/state  ${leaf_name}
    # TODO - interface
    [Arguments]    ${leaf_name}
    Set Datatype To    OPERATIONAL
    Get container includes  /interfaces/interface[name=${INTERFACE}]/state  ${leaf_name}
