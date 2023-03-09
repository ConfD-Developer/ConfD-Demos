*** Settings ***
Documentation    Resources specific to gNMI ``Capabilities`` RPC/operation.
Library          Collections
Library          CapabilitiesLibrary.py


*** Keywords ***

Loaded Capabilities from device
    [Documentation]    Try getting the ``CapabilityResponse`` from device,
    ...                and verify that OK response is received.
    Get capabilities from device
    Should Received Ok Response

Supported encodings include
    [Documentation]    Check that ``CapabilityResponse``'s ``supported_models``
    ...                include specific value.
    [Arguments]    ${encoding}
    @{supported_encodings}=  Last supported encodings
    List should contain value  ${supported_encodings}  ${encoding}

Supported models should not be empty
    [Documentation]    Try getting the ``CapabilityResponse`` from device,
    ...                and verify that OK response is received.
    @{supported_models}=  Last supported model names
    Should Not Be Empty  ${supported_models}
