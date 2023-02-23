*** Settings ***
Documentation     This is a common set of gNMI keywords.


*** Keywords ***
Setup gNMI Client
    Setup client     ${SERVER}  ${USERNAME}  ${PASSWORD}  ${INSECURE}

Close gNMI Client
    Close client
