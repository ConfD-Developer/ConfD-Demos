*** Settings ***
Documentation     Tests for gNMI "Subscribe" operation.
Suite Setup     Setup gNMI Client
Suite Teardown  Close gNMI Client
Resource        subscribe.resource
Default Tags    subscribe

*** Test Cases ***

Subscribe
    [Tags]    sanity
    [Documentation]  Test that the device correctly responds to all three
    ...    "Subscribe" request modes.  No further functionality (such as actually
    ...    polling the device) is tested.
    Verify Subscribe  ONCE
    Verify Subscribe  POLL
    Verify Subscribe  STREAM
