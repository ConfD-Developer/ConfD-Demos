*** Settings ***
Documentation   Generic device agnostic test suite for gNMI ``Capabilities`` RPC/operation.
Test Tags       capabilities

Resource        Capabilities.resource

Resource         gNMIClient.resource
Suite Setup      Setup gNMI Client
Suite Teardown   Close gNMI Client
Test Teardown    Teardown gNMI state


*** Test Cases ***
Device sends CapabilityResponse (any)
    [Documentation]    Device can respond with ``CapabilityResponse`` to incoming ``CapabilityRequest``.
    ...                Do not check response format or received data in any way,
    ...                just the ability to provide response as such.
    When Get capabilities from device
    Then Should Received Ok Response

Mandatory JSON is advertised as supported encoding
    [Documentation]    Get the list of supported encodings from server using ``CapabilityRequest``.
    ...                Verify that the mandatory JSON encoding is included as one of ``supported_encodings`` values.
    [Tags]    encoding
    When Loaded Capabilities from device
    Then Supported encodings include  JSON

Supported encodings include JSON or JSON_IETF
    [Documentation]  Test if the device supports at least one of JSON/JSON_IETF encodings.
    ...              This is a relaxed test in case that device does not follow the "if JSON_IETF is supported,
    ...              this implies JSON as it's superset automatically" theory.
    When Loaded Capabilities from device
    Then Last encodings should have some JSON

Device should support some models
    [Tags]    models
    [Documentation]  Check that the ``supported_models`` returned on ``CapabilityRequest`
    ...              contain at least one or more models.
    When Loaded Capabilities from device
    Then Supported models should not be empty
