*** Settings ***
Documentation    Resources specific to ``openconfig-interfaces.yang`` model.
Library    Collections
Library    ../gNMI_Interface/GetLibrary.py  ${ENABLE_EXTRA_LOGS}  ${DEFAULT_ENCODING}
Resource   ../gNMI_Interface/gNMIClient.resource
Resource   ../gNMI_Interface/BasicGet.resource


*** Keywords ***
Get container includes
    [Documentation]    Retrieve the container type from specified path and check that it includes
    ...                an item with specified name (leaf/sub-container).
    [Tags]    robot:private
    [Arguments]    ${path}  ${leaf_name}
    Verify Get of  ${path}
    Check last updates include   ${leaf_name}

Iterate interface "config" includes leaf
    [Documentation]    Retrieve the configured interface's "config" container,
    ...                and verify that it includes the value with specified name.
    ...                Cleanup the gNMI library state after to allow other clean iterations.
    [Arguments]    ${leaf_name}
    DataType set to    CONFIG
    Get container includes  /interfaces/interface[name=${OC_INTERFACE}]/config  ${leaf_name}
    [Teardown]    Teardown gNMI state

Iterate interface "state" includes leaf
    [Documentation]    Retrieve the configured interface's "state" container,
    ...                and verify that it includes the value with specified name.
    ...                Cleanup the gNMI library state after to allow other clean iterations.
    [Arguments]    ${leaf_name}
    DataType set to    OPERATIONAL
    Get container includes  /interfaces/interface[name=${OC_INTERFACE}]/state  ${leaf_name}
    [Teardown]    Teardown gNMI state
