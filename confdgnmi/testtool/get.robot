*** Settings ***
Documentation   Basic tests for gNMI's "Get" operation.
Resource        gnmi-common.resource
Resource        get.resource
Default Tags    get

Suite Setup     Setup gNMI Client
Test Teardown   Clear GetRequest Parameters
Suite Teardown  Close gNMI Client

*** Test Cases ***
Sanity check that robot Library works
    [Documentation]    Checks that the library is properly initialized
    ...                for use with this robot file.
    [Tags]    sanity
    ${greeting}=  Get library Greeting
    Should Be Equal  ${greeting}  hello

Sanity no parameters check
    [Documentation]    Sanity "no parameters" request to "ping" server for "ok"
    ...                response, ignoring the acutal payload.
    [Tags]    sanity
    Dispatch Get Request
    Should receive OK Response

Parameter "prefix" - root check
    # TODO - might be too costly for big models?
    [Tags]    prefix
    Set prefix to  '/'
    Dispatch Get Request
    Should receive OK Response

Parameter "DataType"
    [Documentation]    Check that all the possible `DataType` values can be used
    ...                as "type" parameter of `GetRequest`
    ...                (while not setting any other request parameters).
    ...                Test suceeds when "OK" response with any data is received from server.
    [Template]         Verify Get with DataType
    ALL
    CONFIG
    STATE
    OPERATIONAL
    INVALID

Parameter "Encoding" - supported values
    [Documentation]    Check which encodings server "advertises" as supported.
    ...                Verify that all of them can be used as "encoding" parameter of `GetRequest`
    ...                (while not setting any other request parameters).
    ...                Test suceeds when "OK" response with any data is received from server.
    [Tags]    encoding
    @{supported}=    Get Supported Encodings
    Verify Get with Encodings  ${supported}  Should receive OK response

Parameter "Encoding" - unsupported values
    [Documentation]    Check which encodings server does NOT "advertise" as supported.
    ...                Verify that all of them, when used as "encoding" parameter of `GetRequest`
    ...                (while not setting any other request parameters),
    ...                return errorenous response from server.
    [Tags]    negative  encoding
    @{unsupported}=    Get Unsupported Encodings
    Verify Get with Encodings  ${unsupported}  Should receive Error response

Parameter "Encoding" - invalid value
    [Documentation]    Try a `GetRequest` with invalid encoding value
    ...                (while not setting any other request parameters),
    ...                and verify that server returns an errorenous response.
    [Tags]    negative  encoding
        Set Encoding to  'invalid'
        Dispatch Get Request
        Should receive Error Response

Iterate all ModelData one by one
    [Tags]    use_models

Non-existing ModelData
    [Tags]    use_models

All ModelData
    [Tags]    use_models

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
