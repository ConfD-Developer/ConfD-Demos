*** Settings ***
Documentation    Resources specific to gNMI ``Get`` RPC/operation.
Library          String
Library          Collections
Resource         gNMIClient.resource
Resource         BasicGet.resource


*** Keywords ***
Iterate root Get with DataType
    [Documentation]    Try sending `GetRequest` with specified DataType parameter value,
    ...                and verify that "ok" response is received.
    [Tags]    type
    [Arguments]    ${type}
    Given DataType set to  ${type}
    When Dispatch Get Request
    Then Should Received Ok Response
    [Teardown]    Teardown gNMI state

Verify root Get with Encoding
    [Documentation]    Try sending `GetRequest` with specified Encoding parameter value,
    ...                and verify that "ok" response is received.
    [Tags]    encoding
    [Arguments]    ${encoding}
    Given Encoding set to  ${encoding}
    When Dispatch Get Request
    Then Should received OK response

Verify Get for Encodings
    [Documentation]    Iterate all the specified encodings, and verify that
    ...                they work for the basic ``GetRequest``.
    [Tags]    encoding  robot:continue-on-failure
    [Arguments]    ${encodings}
    FOR  ${encoding}  IN  @{encodings}
        Verify root Get with Encoding  ${encoding}
    END

Iterate leaves "${leaves}"" of path "${path}"
    [Documentation]    Retrieve the item from specified path, and verify that response
    ...                includes some data for it.
    ...                Cleanup the gNMI library state after to allow other clean iterations.
    Should Be True    ${leaves} is not ${None}  Missing leaves to test for path "${path}"!
    Should Not Be Empty    ${leaves}
    When Verify Get of  ${path}
    FOR  ${leaf}  IN  @{leaves}
        Run Keyword And Continue On Failure  Then Check Last Updates Include    ${leaf}
    END
    [Teardown]    Teardown gNMI state

Iterate container path "${path}"
    [Documentation]    Verify that ``GetRequest`` on a configured path pointing to a "container" node
    ...                succeeds and gets non-empty OK response.
    When Verify Get of  ${path}
    Then Check last updates not empty
    [Teardown]    Teardown gNMI state

Iterate get of list-entry "${path}" with "${keys}"
    [Documentation]    Verify that ``GetRequest`` on a configured path pointing to a "list-entry" node
    ...                succeeds and gets non-empty OK response.
    [Tags]    robot:private
    ${projections}=  Get projections from key dictionary  ${keys}
    When Verify Get of  ${path}${projections}
    Then Check last updates not empty
    [Teardown]    Teardown gNMI state

Iterate list-entry path "${path}" for keys "${keys}"
    [Documentation]    Retrieve the item from specified path, and verify that response
    ...                includes some data for it.
    ...                Cleanup the gNMI library state after to allow other clean iterations.
    [Tags]    robot:continue-on-failure
    FOR  ${key_dictionary}  IN  @{keys}
        Iterate get of list-entry "${path}" with "${key_dictionary}"
    END
    [Teardown]    Teardown gNMI state
