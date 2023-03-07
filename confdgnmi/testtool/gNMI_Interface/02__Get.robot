*** Settings ***
Documentation    Generic device agnostic test suite for gNMI ``Get`` RPC/operation.
Test Tags        get

Library          Collections
Resource         Get.resource

Test Teardown    Cleanup GetRequest Parameters

Resource         gNMIClient.resource
Suite Setup      Setup gNMI Client
Suite Teardown   Close gNMI Client


*** Test Cases ***

Sanity check for no parameters in GetRequest check
    [Documentation]    Make a sanity "no parameters" request to "ping" server for OK response,
    ...                ignoring the actual payload.
    [Tags]    sanity
    Dispatch Get Request
    Should received OK Response


Parameter "prefix" on root path
    [Documentation]    Try getting whole config by setting ``prefix=/`` parameter.
    ...                Check that OK response is received without any internal data verification.
    # TODO - might be too costly for big models?
    [Tags]    prefix
    Set prefix to  '/'
    Dispatch Get Request
    GetLibrary.Should received OK Response

Parameter "type" - valid values return OK response
    [Documentation]    Check that all the possible ``DataType`` values can be used
    ...                as "type" parameter of ``GetRequest``
    ...                (while not setting any other request parameters).
    ...                Test succeeds when "OK" response with any data is received from server.
    [Template]         Verify Get with DataType
    ALL
    CONFIG
    STATE
    OPERATIONAL

Parameter "type" - invalid value returns Error response
    Verify Get with DataType  INVALID  GetLibrary.Should received Error Response

Parameter "encoding" - supported values get OK response
    [Documentation]    Check which encodings server advertises as supported via ``CapabilityRequest``.
    ...                Verify that all of them can be used as "encoding" parameter of ``GetRequest``
    ...                (while not setting any other request parameters).
    ...                Test succeeds when "OK" response with any data is received from server
    ...                for all of the advertised encodings.
    [Tags]    encoding
    Get Capabilities From Device
    @{supported}=  List Supported Encodings
    Should Not Be Empty  ${supported}
    Verify Get for Encodings  ${supported}

Parameter "encoding" - unsupported value gets Error response
    [Documentation]    Check which encodings server does NOT "advertise" as supported.
    ...                Verify that all of them, when used as "encoding" parameter of ``GetRequest``
    ...                (while not setting any other request parameters),
    ...                return erroneous response from server.
    [Tags]    negative  encoding
    Get Capabilities From Device
    @{unsupported}=    List Unsupported Encodings
    Verify Get for Encodings  ${unsupported}  GetLibrary.Should received Error response

Parameter "encoding" - invalid value gets Error response
    [Documentation]    Try a ``GetRequest`` with invalid encoding value
    ...                (while not setting any other request parameters),
    ...                and verify that server returns an erroneous response.
    [Tags]    negative  encoding
        Set Encoding to  'invalid'
        Dispatch Get Request
        GetLibrary.Should received Error Response

Non-existing ModelData
    [Tags]    use_models
    Verify Get of model  non-existing-model  GetLibrary.Should received Error response

# Iterate all ModelData one by one
#  TODO - device might have tons of models, need some filter...
# TODO - sets "use-models" param instead of path!
#     [Tags]    costly  use_models
#     ${model_names}=  Get supported model names
#     ${model_count}=  Get Length  ${model_names}
#     Log  Received ${model_count} model names from device. Starting to iterate:
#     Verify Get for models  ${model_names}

# All ModelData
#     [Tags]    use_models

# gnmic -a xawin.lab.tail-f.com:32784 -u admin -p admin --insecure get --path /non-existing-model
# ./confd_gnmi_client.py --host xawin.lab.tail-f.com --port 32784 --insecure -p /non-existing-model
