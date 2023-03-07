*** Settings ***
Documentation    Resources specific to gNMI ``Capabilities`` RPC/operation.
Library          CapabilitiesLibrary.py


*** Keywords ***

Supported encodings should have some JSON
    @{encodings}=  List supported encodings
    Should contain  ${encodings}  JSON_IETF
    IF  'JSON' not in ${encodings}
        Log  Mandatory JSON (as per gNMI specification) not declared as supported  WARN
    END
