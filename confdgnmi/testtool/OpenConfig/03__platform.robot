*** Settings ***
Documentation     A test suite for gNMI OpenConfig tests.
Test Tags         OpenConfig  platform
Resource          ../gNMI_Interface/gNMIClient.resource
Default Tags      positive

# Resource         ../gNMI_Interface/gNMIClient.resource
# Suite Setup      Setup gNMI Client
# Suite Teardown   Close gNMI Client
# Test Teardown    Teardown gNMI state


*** Test Cases ***

Sanity TODO check
    Skip
