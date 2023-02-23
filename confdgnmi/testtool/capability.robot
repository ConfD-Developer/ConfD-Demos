*** Settings ***
Documentation     A test suite for gNMI "Capability" tests.

Suite Setup     Setup gNMI Client
Suite Teardown  Close gNMI Client
Test Teardown   Cleanup capabilities

Resource        capability.resource
Default Tags    capability

*** Test Cases ***
Capabilities
    [Documentation]  Test if the device responds to the "Capabilities" request.
    Get Capabilities
    Verify encoding
    Verify models
