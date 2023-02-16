*** Settings ***
Documentation     This is a common set of gNMI keywords.
Library           GNMIClient.py


*** Keywords ***
Connect to Server
    Connect    ${SERVER}  ${USERNAME}  ${PASSWORD}  ${INSECURE}

Close Server Connection
    Disconnect

Verify Capabilities
    ${capas}=  Get Capabilities
    Should contain  ${capas}.supported_encodings  JSON_IETF
    Should not be empty  ${capas}.supported_models
    Run Keyword If  'JSON' not in $capas.supported_encodings  Log  JSON not declared as supported  WARN
