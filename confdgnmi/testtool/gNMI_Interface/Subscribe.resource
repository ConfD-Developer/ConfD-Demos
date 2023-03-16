*** Settings ***
Documentation    Resources specific to gNMI Subscribe operation.
Library          SubscribeLibrary.py  ${ENABLE_EXTRA_LOGS}
Resource         gNMIClient.resource


*** Keywords ***

Verify Subscribe
    [Arguments]  ${mode}
    Test Subscribe  ${mode}  ${GET-PATH}
