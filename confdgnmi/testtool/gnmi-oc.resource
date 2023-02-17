*** Settings ***
Documentation     This is a set of keywords specific to OpenConfig tests.
Library           GNMIClient.py


*** Keywords ***
Verify OpenConfig Capabilities
    ${capas}=  Get Capabilities
    @{models}=  Model Names  ${capas}
    FOR  ${model}  IN  @{OC-MODELS}
        Should contain  ${models}  ${model}
    END
