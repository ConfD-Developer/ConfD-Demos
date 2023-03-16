*** Settings ***
Documentation    Resources specific to OpenConfig telemetry testing.
Library          ../gNMI_Interface/GetLibrary.py  ${ENABLE_EXTRA_LOGS}  ${DEFAULT_ENCODING}
Resource    ../gNMI_Interface/gNMIClient.resource

*** Keywords ***

Verify Get of
    [Arguments]  ${path}
    [Documentation]    Send ``GetRequest`` with specified path parameter
    ...                and verify that "ok" response is received.
    Given Paths include  ${path}
    When Dispatch Get Request
    Then Should Received Ok Response

Iterate Get of
    [Arguments]  ${path}
    Verify Get of  ${path}
    [Teardown]    Teardown gNMI state

Get data from
    [Arguments]  ${path}
    [Documentation]    Verify that Get RPC succeeds for specified path,
    ...                and return the retrieved response data.
    Verify Get of  ${path}
    ${response}=  Retrieve Last Response
    [Return]  ${response}


Iterate path "${path}" with DataType ${type}
    Given Paths include  ${path}
    and DataType set to  ${type}
    When Dispatch Get Request
    Then Should Received Ok Response
    [Teardown]    Teardown gNMI state
