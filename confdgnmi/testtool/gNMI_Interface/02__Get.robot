*** Settings ***
Documentation    Generic device agnostic test suite for gNMI ``Get`` RPC/operation.
Test Tags        get

Library          Collections
Resource         Get.resource

Resource         gNMIClient.resource
Suite Setup      Setup gNMI Client
Suite Teardown   Close gNMI Client
Test Teardown    Teardown gNMI state


*** Test Cases ***

Sanity check for no parameters in GetRequest check
    [Documentation]    Make a sanity "no parameters" request to "ping" server for OK response,
    ...                ignoring the actual payload.
    [Tags]    sanity
    When Dispatch Get Request
    Then Should received OK Response

Parameter "prefix" on root path
    [Documentation]    Try getting whole config by setting ``prefix=/`` parameter.
    ...                Check that OK response is received without any internal data verification.
    # TODO - might be too costly for big models?
    [Tags]    prefix
    Given Prefix set to  /
    When Dispatch Get Request
    Then Should received OK Response

Parameter "type" - valid values return OK response
    [Documentation]    Check that all the possible ``DataType`` values can be used
    ...                as "type" parameter of ``GetRequest``
    ...                (while not setting any other request parameters).
    ...
    ...                Test succeeds when "OK" response with any data is received from server.
    [Template]         Iterate Get with DataType
    ALL
    CONFIG
    STATE
    OPERATIONAL

Parameter "type" - an unsupported value returns Error response
    [Documentation]    Check that setting an invalid value (other than all the standard
    ...                specified ones for ``DataType`` value for ``GetRequest``
    ...                results in error response from server.
    [Tags]    type  negative
    Given DataType set to  INVALID
    When Dispatch Get Request
    Then Should Received Error Response

Parameter "encoding" - supported values get OK response
    [Documentation]    Check which encodings server advertises as supported via ``CapabilityRequest``.
    ...
    ...                Verify that all of them can be used as "encoding" parameter of ``GetRequest``
    ...                (while not setting any other request parameters).
    ...
    ...                Test succeeds when "OK" response with any data is received from server
    ...                for all of the advertised encodings.
    [Tags]    encoding
    When Get Capabilities From Device
    Then Should Received Ok Response

    @{supported}=  Last Supported Encodings
    Should Not Be Empty  ${supported}
    # TODO - fix buggy default DataType
    Verify Get for Encodings  ${supported}

Parameter "encoding" - unsupported value gets Error response
    [Documentation]    Check which encodings server does NOT "advertise" as supported.
    ...                Verify that all of them, when used as "encoding" parameter of ``GetRequest``
    ...                (while not setting any other request parameters),
    ...                return erroneous response from server.
    [Tags]    negative  encoding  robot:continue-on-failure
    When Get Capabilities From Device
    Then Should Received Ok Response

    @{unsupported}=    Last Unsupported Encodings
    FOR    ${encoding}    IN    @{unsupported}
        Given Encoding set to  ${encoding}
        When Dispatch Get Request
        Then Should received Error response
    END

Parameter "encoding" - invalid value gets Error response
    [Documentation]    Try a ``GetRequest`` with invalid encoding value
    ...                (while not setting any other request parameters),
    ...                and verify that server returns an erroneous response.
    [Tags]    negative  encoding
    Given Encoding set to  'invalid'
    When Dispatch Get Request
    Then Should received Error Response

# Non-existing ModelData
#     [Tags]    use_models
#     Verify Get of model  non-existing-model  Should received Error response

# Iterate all ModelData one by one
# TODO - device might have tons of models, need some filter...
# TODO - set "use-models" param instead of path!
#     [Tags]    costly  use_models
#     ${model_names}=  Get supported model names
#     ${model_count}=  Get Length  ${model_names}
#     Log  Received ${model_count} model names from device. Starting to iterate:
#     Verify Get for models  ${model_names}
