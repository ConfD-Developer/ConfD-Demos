*** Settings ***
Documentation   Basic tests for gNMI's "Get" operation.
Resource        gnmi-common.resource
Library         Collections
Resource        get.resource
Test Tags       get

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

Sanity check for no parameters in GetRequest check
    [Documentation]    Make a sanity "no parameters" request to "ping" server for OK response,
    ...                ignoring the actual payload.
    [Tags]    sanity
    Dispatch Get Request
    Should receive OK Response

Parameter "prefix" on root path
    # TODO - might be too costly for big models?
    [Tags]    prefix
    Set prefix to  '/'
    Dispatch Get Request
    Should receive OK Response

Parameter "DataType" - valid values return OK response
    [Documentation]    Check that all the possible ``DataType`` values can be used
    ...                as "type" parameter of ``GetRequest``
    ...                (while not setting any other request parameters).
    ...                Test succeeds when "OK" response with any data is received from server.
    [Template]         Verify Get with DataType
    ALL
    CONFIG
    STATE
    OPERATIONAL

Parameter "DataType" - invalid value returns Error response
    Verify Get with DataType  INVALID  Should receive Error Response

Parameter "Encoding" - mandatory JSON is advertised
    [Documentation]    Get the list of supported encodings from server using ``CapabilityRequest``.
    ...                Verify that the mandatory JSON encoding is included.
    [Tags]    encoding
    @{supported}=    Get Supported Encodings
    List should contain value  ${supported}  JSON

Parameter "Encoding" - supported values get OK response
    [Documentation]    Check which encodings server advertises as supported via ``CapabilityRequest``.
    ...                Verify that all of them can be used as "encoding" parameter of ``GetRequest``
    ...                (while not setting any other request parameters).
    ...                Test succeeds when "OK" response with any data is received from server
    ...                for all of the advertised encodings.
    [Tags]    encoding
    @{supported}=    Get Supported Encodings
    Should Not Be Empty  ${supported}
    Verify Get for Encodings  ${supported}

Parameter "Encoding" - unsupported values get Error response
    [Documentation]    Check which encodings server does NOT "advertise" as supported.
    ...                Verify that all of them, when used as "encoding" parameter of ``GetRequest``
    ...                (while not setting any other request parameters),
    ...                return erroneous response from server.
    [Tags]    negative  encoding
    @{unsupported}=    Get Unsupported Encodings
    Verify Get for Encodings  ${unsupported}  Should receive Error response

Parameter "Encoding" - invalid value gets Error response
    [Documentation]    Try a ``GetRequest`` with invalid encoding value
    ...                (while not setting any other request parameters),
    ...                and verify that server returns an erroneous response.
    [Tags]    negative  encoding
        Set Encoding to  'invalid'
        Dispatch Get Request
        Should receive Error Response

Iterate all ModelData one by one
    [Tags]    use_models
    ${model_names}=  Get supported model names
    ${model_count}=  Get Length  ${model_names}
    Log  Received ${model_count} model names from device. Starting to iterate:
    Verify Get for models  ${model_names}

Non-existing ModelData
    [Tags]    use_models
    Verify Get of model  'non-existing-model'

All ModelData
    [Tags]    use_models
