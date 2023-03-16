*** Settings ***
Documentation    Generic device agnostic test suite for gNMI ``Subscribe`` RPC/operation.
Test Tags        subscribe

Resource         Subscribe.resource

Resource         gNMIClient.resource
Test Setup       Setup gNMI Client
Test Teardown    Teardown gNMI state


*** Test Cases ***

Basic subscription with "mode" parameter
    [Tags]    sanity
    [Documentation]    Test that the device correctly responds to all three
    ...    "Subscribe" request modes.    No further functionality (such as actually
    ...    polling the device) is tested.
    [Template]    Subscribe ${mode} to default path with encoding JSON_IETF
    STREAM
    ONCE
    POLL

Subscribe ONCE with supported "encoding" values
    [Tags]    sanity
    [Documentation]    Verify that the device is able to respond correctly for
    ...    all declared encodings.
    Given device capabilities
    and subscription paths    ${GET-PATH}
    Then subscribe ONCE with supported encodings

Two subscriptions in single request with the same "path"
    [Documentation]    Verify that the device can handle ONCE subscription
    ...    with two identical paths.
    Given subscription paths    ${GET-PATH}    ${GET-PATH}
    And subscription ONCE with encoding JSON_IETF
    Then device responds

Two subscriptions in single request with different "path"
    [Documentation]    Verify that the device can handle ONCE subscription
    ...    with two different paths.
    Given subscription paths    ${GET-PATH}    ${SECONDARY-PATH}
    And subscription ONCE with encoding JSON_IETF
    Then device responds

Subscribe ONCE sends final message with "sync_response"
    [Documentation]    When a ONCE subscription is created, the device must
    ...    respond with a series of responses terminated by an empty
    ...    response with "sync_response".
    Given Subscription paths    ${GET-PATH}
    And Subscription ONCE with encoding JSON_IETF
    Then Device sends terminated response series and closes the stream

Subscribe POLL sends final message with "sync_response"
    [Documentation]    When a POLL subscription is created, the device must
    ...    send an initial set of responses terminated by an empty
    ...    response with "sync_response".
    Given Subscription paths    ${GET-PATH}
    And Subscription POLL with encoding JSON_IETF
    Then Device sends terminated response series

Subscribe STREAM sends final message with "sync_response"
    [Documentation]    When a STREAM subscription is created, the device must
    ...    send an initial set of responses terminated by an empty
    ...    response with "sync_response".
    Given Subscription paths    ${GET-PATH}
    And Subscription POLL with encoding JSON_IETF
    Then Device sends terminated response series

QOS marked subscriptions
    [Tags]    unimplemented
    # idk., what to test here?

STREAM with TARGET_DEFINED mode
    [Tags]    unimplemented
    # same - nothing to test, really

STREAM with ON_CHANGE mode
    [Tags]    unimplemented

STREAM with SAMPLE mode
    [Tags]    unimplemented


Subscribe ONCE with updates_only in the SubscriptionList
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements. ONCE Subscription operation is invoked with updates_only field set in SubscriptionRequest. Test verifies only one SubscribeResponse with only sync_response set to true.
    [Tags]    unimplemented

Basic functionality of the Subscribe POLL RPC .
    # Parameters: common connection parameters, path, poll count, poll interval.
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements. Subscription operation is invoked. First SubscriptionRequest is ONCE. After that POLL subscription requests are invoked with poll interval delay. Test verifies for each subscription data is received. Optionally, it can verify the data is the same as the one received in response for ONCE subscription. Test issues WARNING, if SubscriptionResponse stream is closed prematurely. Test issues WARNING if Updates in SubscriptionResponse are aggregated.
    [Tags]    unimplemented

Subscribe POLL RPC with updates_only in the SubscriptionList.
    # Parameters: common connection parameters, path, poll count, poll interval.
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements. Subscription` operation is invoked. First SubscriptionRequest is ONCE with filled SubscriptionList containing updates_only set to true. This subscription is handled as ONCE subscription. After that, empty POLL subscription requests are invoked with poll interval delay. Test verifies for each subscription (also for initial ONCE) a SubscriptionResponse is received with only sync_response set to true (without other fields). Test issues WARNING, if SubscriptionResponse stream is closed prematurely. Test issues WARNING if Updates in SubscriptionResponse are aggregated.
    [Tags]    unimplemented

Basic functionality of the Subscribe STREAM RPC with ON_CHANGE mode.
    # Parameters: common connection parameters, path, read count
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements, where some of them periodically change (e.g. packet count on interface). STREAM` Subscription operation is invoked. First SubscriptionResponse contains all elements, next responses contains only changed elements. After read count parameter test ends (and subscription stream is closed). Test issues WARNING, if SubscriptionResponse stream is closed prematurely. Test issues WARNING if Updates in SubscriptionResponse are aggregated.
    [TAGS]    unimplemented

# TODO - Michal's backlog:

Other STREAM variants (and combinations):
    # Subscription list with allow_aggregation
    # STREAM ON_CHANGE mode, with updates_only
    # STREAM SAMPLE mode
    # STREAM SAMPLE mode with sample_interval
    # STREAM SAMPLE mode with sample_interval set to 0
    # STREAM SAMPLE mode, with heartbeat_interval
    # STREAM SAMPLE mode, with updates_only
    # STREAM SAMPLE mode, with suppress_redundant
    [Tags]    unimplemented
