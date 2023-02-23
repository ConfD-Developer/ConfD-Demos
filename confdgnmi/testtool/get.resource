*** Settings ***
Documentation    Resources specific to gNMI Get operation.
Library          GetLibrary.py
Variables        adapter.yaml

*** Variables ***
@{ALL_ENCODINGS}    JSON  BYTES  PROTO  ASCII  JSON_IETF

*** Keywords ***
Setup gNMI Client
    Setup client     ${SERVER}  ${USERNAME}  ${PASSWORD}  ${INSECURE}

Close gNMI Client
    Close client
