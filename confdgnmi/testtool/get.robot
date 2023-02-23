*** Settings ***
Documentation   Basic tests for gNMI's "Get" operation.
Resource        get.resource
Default Tags    get

Test Setup      Setup gNMI Client
Test Teardown   Clear GetRequest Parameters
Suite Teardown  Close gNMI Client

*** Variables ***
${LIST_PATH}    '/interfaces'
@{ALL_DATA_TYPES}   ALL  CONFIG  STATE  OPERATIONAL
${GET_PATH}     /


*** Test Cases ***
Library Works
    [Tags]      sanity
    [Documentation]    Checks that the library is properly initialized
    ...                for use with this robot file.
    ${greeting}=  Get library Greeting
    Should Be Equal  ${greeting}  hello

No parameters sanity check
    [Tags]  sanity
    [Documentation]    Sanity "no parameters" request to "ping" server for "ok"
    ...                response, ignoring the acutal payload.
    Add path parameter  ${GET_PATH}
    Dispatch Get Request
    Check received OK Response

Prefix only
    [Tags]  get  prefix
    Set prefix to  '/'
    Add path parameter  ${GET_PATH}
    Dispatch Get Request
    Check received OK Response

DataType only
    [Tags]    DataType  type
    FOR  ${element}  IN  @{ALL_DATA_TYPES}
        Set DataType to  ${element}
        Add path parameter  ${GET_PATH}
        Dispatch Get Request
        Check received OK Response
    END

Invalid DataType check
    [Tags]    negative  DataType  type
        Set DataType to  'invalid'
        Add path parameter  ${GET_PATH}
        Dispatch Get Request
        Check received Error Response

Encoding only
    [Tags]    Encoding  encoding
    @{encodings}=    Get Supported Encodings
    FOR  ${element}  IN  @{encodings}
        Set Encoding to  ${element}
        Add path parameter  ${GET_PATH}
        Dispatch Get Request
        Check received OK Response
    END

Unsupported Encoding check
    [Tags]    negative  Encoding  encoding
    @{encodings}=    Get Unsupported Encodings
    FOR  ${element}  IN  @{ALL_ENCODINGS}
            Set Encoding to  ${element}
            Add path parameter  ${GET_PATH}
            Dispatch Get Request
            Check received OK Response
    END

Invalid Encoding check
    [Tags]    negative  Encoding  encoding
        Set Encoding to  'invalid'
        Add path parameter  ${GET_PATH}
        Dispatch Get Request
        Check received Error Response


Iterate all ModelData one by one
    [Tags]    ModelData  use_models

Non-existing ModelData
    [Tags]    ModelData  use_models

All ModelData
    [Tags]    ModelData  use_models

Verify can receive list elements
    [Tags]  list
    Add Path Parameter    ${LIST_PATH}
    Dispatch Get Request
    Check Received Error Response
    Check response includes  ${LIST_PATH}
    $(interfaces)=  Get Payload path   ${LIST_PATH}
    Check is list  $(interfaces)

Get for list entry






# // GetResponse is used by the target to respond to a GetRequest from a client.
# // The set of Notifications corresponds to the data values that are requested
# // by the client in the GetRequest.# // Reference: gNMI Specification Section 3.3.2
# message GetResponse {
#   repeated Notification notification = 1;   // Data values.
#   Error error = 2 [deprecated=true];        // Errors that occurred in the Get.
#   // Extension messages associated with the GetResponse. See the
#   // gNMI extension specification for further definition.
#   repeated gnmi_ext.Extension extension = 3;
# }
