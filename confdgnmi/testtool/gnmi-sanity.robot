*** Settings ***
Documentation     A test suite for gNMI sanity tests.
Resource          gnmi.resource
Default Tags      positive

*** Test Cases ***
Capabilities
    Connect to Server
    Verify Capabilities
    [Teardown]    Close Server Connection
