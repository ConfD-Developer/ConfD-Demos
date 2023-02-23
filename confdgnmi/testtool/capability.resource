*** Settings ***
Documentation    Resources specific to gNMI Capability operation.
Library          CapabilityLibrary.py
Resource         gnmi-common.resource


*** Keywords ***

Verify encoding
    @{encodings}=  supported encodings
    Should contain  ${encodings}  JSON_IETF
    IF  'JSON' not in ${encodings}
        Log  JSON not declared as supported  WARN
    END

Verify models
    @{models}=  supported models
    Should not be empty  ${models}
