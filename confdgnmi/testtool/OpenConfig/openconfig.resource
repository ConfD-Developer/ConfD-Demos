*** Settings ***
Documentation    Resources specific to OpenConfig telemetry testing.
Library          ../gNMI_Interface/GetLibrary.py  ${ENABLE_EXTRA_LOGS}  ${DEFAULT_ENCODING}
Resource    ../gNMI_Interface/gNMIClient.resource


*** Keywords ***
Iterate path "${path}" with DataType ${type}
    [Documentation]    Retrieve data from the specified path having set the specified ``GetRequests``'s ``type``,
    ...                Cleanup the gNMI library state after to allow other clean iterations.
    Given Paths include  ${path}
    and DataType set to  ${type}
    When Dispatch Get Request
    Then Should Received Ok Response
    [Teardown]    Teardown gNMI state
