*** Settings ***
Documentation    Resources specific to OpenConfig telemetry testing.
Library          ../gNMI_Interface/GetLibrary.py    ${DEFAULT_ENCODING}

*** Keywords ***

Verify Get of
    [Arguments]  ${path}
    [Documentation]    Send ``GetRequest`` with specified path parameter
    ...                and verify that "ok" response is received.
    Add Path Parameter  ${path}
    Dispatch Get Request
    GetLibrary.Should Received Ok Response

Verify Get of "{path}" with supported encodings
    Get Capabilities From Device
    ${supported_encodings}=  List Supported Encodings
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
    Add Path Parameter  ${path}
    Set Datatype To  ${type}
    Dispatch Get Request
    Should Received Ok Response
