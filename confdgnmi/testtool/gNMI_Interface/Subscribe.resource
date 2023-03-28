*** Settings ***
Documentation    Resources specific to gNMI Subscribe operation.
Library          SubscribeLibrary.py  ${ENABLE_EXTRA_LOGS}
Resource         gNMIClient.resource


*** Keywords ***

Subscribe ${mode} to default path with encoding ${encoding}
    Given subscription paths    ${GET-PATH}
    And Subscription ${mode} with encoding ${encoding}
    Then device responds

Subscription ${mode} with encoding ${encoding}
    Subscribe    ${mode}    ${encoding}

Device responds
    ${updates}=    Check updates
    Should be true    ${updates}

Subscribe ONCE with supported encodings
    @{encodings}=    last supported encodings
    FOR    ${encoding}    IN    @{encodings}
        Given subscription ONCE with encoding ${encoding}
        Then device responds
    END

Device capabilities
    Get capabilities from device

Device sends terminated response series and closes the stream
    Device terminates    True

Device sends terminated response series
    Device terminates    False

Device terminates
    [Arguments]    ${should_close}
    [Timeout]    5 seconds
    ${terminated}=    Check responses terminated    ${should_close}
    Should be true    ${terminated}    "The server did not send sync_response"
