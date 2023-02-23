*** Settings ***
Documentation   This is a common set of gNMI keywords.
...             Using this resource in robot file requires having a Library
...             that implements the used keywords. (see `TODO` - link to base robot library)

*** Keywords ***
Setup gNMI Client
    Setup client     ${SERVER}  ${USERNAME}  ${PASSWORD}  ${INSECURE}

Close gNMI Client
    Close client
