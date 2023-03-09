*** Settings ***
Documentation    Resources specific to OpenConfig telemetry testing.
Library          ../gNMI_Interface/GetLibrary.py    ${DEFAULT_ENCODING}

*** Keywords ***

Verify Get of
    [Arguments]  ${path}
    [Documentation]    Send ``GetRequest`` with specified path parameter
    ...                and verify that "ok" response is received.
    Given Paths include  ${path}
    When Dispatch Get Request
    Then Should Received Ok Response

Verify Get of "{path}" with supported encodings
    Get Capabilities From Device
    ${supported_encodings}=  Last Supported Encodings
    FOR  ${encoding}  IN  @{supported_encodings}
        Log    ${encoding}
    END

Get data from
    [Arguments]  ${path}
    [Documentation]    Verify that Get RPC succeeds for specified path,
    ...                and return the retrieved response data.
    Verify Get of  ${path}
    ${response}=  Retrieve Last Response
    [Return]  ${response}


Verify path "${path}" with DataType ${type}
    Given Paths include  ${path}
    and DataType set to  ${type}
    When Dispatch Get Request
    Then Should Received Ok Response
