*** Settings ***
Documentation    Resources specific to gNMI Get operation.
Library          GetLibrary.py    ${DEFAULT_ENCODING}
Variables        adapter.yaml

*** Keywords ***
Verify Get with DataType
    [Arguments]    ${type}  ${pass-condition-keyword}=Should receive OK Response
    [Documentation]    Try sending `GetRequest` with specified DataType parameter value,
    ...                and verify that "ok" response is received.
    [Tags]    type
    Set DataType to  ${type}
    Dispatch Get Request
    Run Keyword  ${pass-condition-keyword}

Verify Get with Encoding
    [Tags]    encoding
    [Arguments]    ${encoding}  ${pass-condition-keyword}
    Set Encoding to  ${encoding}
    Dispatch Get Request
    Run keyword  ${pass-condition-keyword}

Verify Get for Encodings
    [Tags]    encoding  robot:continue-on-failure
    [Arguments]    ${encodings}    ${pass-condition-keyword}=Should receive Ok response
    FOR  ${encoding}  IN  @{encodings}
        Verify Get with Encoding  ${encoding}  ${pass-condition-keyword}
    END

Verify Get of model
    [Tags]    path
    [Arguments]    ${model}  ${pass-condition-keyword}=
    Add path parameter  ${model}
    Dispatch Get Request
    Run keyword  ${pass-condition-keyword}

Verify Get for models
    [Tags]    path  robot:continue-on-failure
    [Arguments]    ${model_names}    ${pass-condition-keyword}=Should receive Ok response
    FOR  ${model}  IN  @{model_names}
        Verify Get of model  ${model}  ${pass-condition-keyword}
    END
