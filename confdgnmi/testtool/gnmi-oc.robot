*** Settings ***
Documentation     A test suite for gNMI OpenConfig tests.
Test Tags         OpenConfig
Resource          gnmi.resource
Resource          gnmi-oc.resource
Default Tags      positive

*** Test Cases ***
OpenConfig Capabilities
    Connect to Server
    Verify OpenConfig Capabilities
    [Teardown]    Close Server Connection
