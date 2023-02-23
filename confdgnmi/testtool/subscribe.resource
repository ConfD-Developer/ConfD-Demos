*** Settings ***
Documentation    Resources specific to gNMI Subscribe operation.
Library          SubscribeLibrary.py
Resource         gnmi-common.resource


*** Keywords ***

Verify Subscribe
    [Arguments]  ${mode}
    Test Subscribe  ${mode}  ${GET-PATH}
