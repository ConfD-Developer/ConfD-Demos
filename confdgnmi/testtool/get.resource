*** Settings ***
Documentation    Resources specific to gNMI Get operation.
Library          GetLibrary.py
Variables        adapter.yaml

*** Keywords ***
Verify Get with DataType
    [Arguments]    ${type}
    [Documentation]    Try sending `GetRequest` with specified DataType parameter value,
    ...                and verify that "ok" response is received.
    [Tags]    type
    Set DataType to  ${type}
    Dispatch Get Request
    Should receive OK Response
    # TODO - chekc some data present?

Verify Get with Encoding
    [Tags]    encoding
    [Arguments]    ${encoding}  ${pass-condition-keyword}
    Set Encoding to  ${encoding}
    Dispatch Get Request
    Run keyword  ${pass-condition-keyword}

Verify Get with Encodings
    [Tags]    encoding
    [Arguments]    ${encodings}    ${pass-condition-keyword}
    FOR  ${encoding}  IN  @{encodings}
        Set Encoding to  ${encoding}
        Dispatch Get Request
        Run keyword  ${pass-condition-keyword}
    END
