*** Settings ***
Documentation    Resources specific to gNMI ``Get`` RPC/operation.
...              NOTE: file including this MUST have ` ``Library`` that inherits from ``GetLibrary``.
Library          String
Resource         gNMIClient.resource


*** Keywords ***
Verify Get of
    [Arguments]  ${path}
    [Documentation]    Send ``GetRequest`` with specified path parameter
    ...                and verify that "ok" response is received.
    Given Paths include  ${path}
    When Dispatch Get Request
    Then Should Received Ok Response

Iterate Get of
    [Documentation]    Template variant of ``Verify Get of`` keyword.
    ...                Includes an extra library state teardown after the execution.
    [Arguments]  ${path}
    Verify Get of  ${path}
    [Teardown]    Teardown gNMI state
