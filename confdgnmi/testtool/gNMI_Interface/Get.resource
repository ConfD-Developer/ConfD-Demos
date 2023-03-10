*** Settings ***
Documentation    Resources specific to gNMI ``Get`` RPC/operation.
Library          GetLibrary.py    ${DEFAULT_ENCODING}

*** Keywords ***
Verify Get with DataType
    [Documentation]    Try sending `GetRequest` with specified DataType parameter value,
    ...                and verify that "ok" response is received.
    [Tags]    type
    [Arguments]    ${type}
    Given DataType set to  ${type}
    When Dispatch Get Request
    Then Should Received Ok Response

Verify Get with Encoding
    [Documentation]    Try sending `GetRequest` with specified Encoding parameter value,
    ...                and verify that "ok" response is received.
    [Tags]    encoding
    [Arguments]    ${encoding}
    Given Encoding set to  ${encoding}
    When Dispatch Get Request
    Then Should received OK response

Verify Get for Encodings
    [Tags]    encoding  robot:continue-on-failure
    [Arguments]    ${encodings}
    FOR  ${encoding}  IN  @{encodings}
        Verify Get with Encoding  ${encoding}
    END

Verify Get failure for unsupported encodings

# TODO - uncomment/use when use_models functionality is added to servicing robot lib
# Verify Get of model
#     [Tags]    path
#     [Arguments]    ${model}  ${pass-condition-keyword}=Should received Ok response
#     Given Paths include  /${model}
#     When Dispatch Get Request
#     Then Run keyword  ${pass-condition-keyword}

# Verify Get for models
#     [Tags]    path  robot:continue-on-failure
#     [Arguments]    ${model_names}    ${pass-condition-keyword}=Should received Ok response
#     FOR  ${model}  IN  @{model_names}
#         Verify Get of model  ${model}  ${pass-condition-keyword}
#     END
