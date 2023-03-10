*** Settings ***
Documentation     A test suite for gNMI OpenConfig tests.
Test Tags         OpenConfig  if-ip
Resource          ../gNMI_Interface/gNMIClient.resource
Default Tags      positive

# Resource         ../gNMI_Interface/gNMIClient.resource
# Suite Setup      Setup gNMI Client
# Suite Teardown   Close gNMI Client


*** Test Cases ***

Sanity TODO check
    Skip
