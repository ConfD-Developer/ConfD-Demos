*** Settings ***
Documentation    Generic device agnostic test suite for gNMI ``Subscribe`` RPC/operation.
Test Tags        subscribe

Resource         Subscribe.resource

Resource         gNMIClient.resource
Suite Setup      Setup gNMI Client
Suite Teardown   Close gNMI Client


*** Test Cases ***

Basic subscription with "mode" parameter
    [Tags]    sanity
    [Documentation]  Test that the device correctly responds to all three
    ...    "Subscribe" request modes.  No further functionality (such as actually
    ...    polling the device) is tested.
    [Template]    Verify Subscribe
    STREAM
    ONCE
    POLL

Subscribe to non-existent "prefix"

Subscribe to non-existent "path"

# message Subscription {
#   Path path = 1;                    // The data tree path.
#   SubscriptionMode mode = 2;        // Subscription mode to be used.
#   uint64 sample_interval = 3;       // ns between samples in SAMPLE mode.
#   bool suppress_redundant = 4;
#   uint64 heartbeat_interval = 5;
# }

Subscribe ONCE with supported "encoding" values

Two Subscriptions in single request - with same "path"

Two Subscriptions in single request - with different "path"

QOS marked subscriptions

STREAM with TARGET_DEFINED mode

STREAM with ON_CHANGE mode

STREAM with SAMPLE mode



# TODO:

Basic functionality of the Subscribe ONCE
    [Documentation]    TODO
    ...  Failure: Device does not respond, responds with an error, responds with
    ...  an empty notification set or with a notification without updates,
    ...  responds with incorrect encoding.
    ...
    ...  Tags: Rel-1, active, intf; Short: gNMI Subscribe ONCE Parent: GNMI-HLT-010
    ...
    ...  Test is passed path to the data model, which contains limited number of elements.
    ...   ONCE Subscription operation is invoked.
    ...  SubscriptionRequest does not have set updates_only field.
    ...  Test verifies for each subscription
    ...    data is received as a stream of SubscribeResponses
    ...  Last SubscribeResponse is with sync_response set to true.
    # TODO
    # Can SubscribeResponse with sync_response contain also something else, e.g. updates?


Subscribe ONCE with updates_only in the SubscriptionList
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements. ONCE Subscription operation is invoked with updates_only field set in SubscriptionRequest. Test verifies only one SubscribeResponse with only sync_response set to true.

Basic functionality of the Subscribe POLL RPC .
    # Parameters: common connection parameters, path, poll count, poll interval.
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements. Subscription operation is invoked. First SubscriptionRequest is ONCE. After that POLL subscription requests are invoked with poll interval delay. Test verifies for each subscription data is received. Optionally, it can verify the data is the same as the one received in response for ONCE subscription. Test issues WARNING, if SubscriptionResponse stream is closed prematurely. Test issues WARNING if Updates in SubscriptionResponse are aggregated.

Subscribe POLL RPC with updates_only in the SubscriptionList.
    # Parameters: common connection parameters, path, poll count, poll interval.
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements. Subscription` operation is invoked. First SubscriptionRequest is ONCE with filled SubscriptionList containing updates_only set to true. This subscription is handled as ONCE subscription. After that, empty POLL subscription requests are invoked with poll interval delay. Test verifies for each subscription (also for initial ONCE) a SubscriptionResponse is received with only sync_response set to true (without other fields). Test issues WARNING, if SubscriptionResponse stream is closed prematurely. Test issues WARNING if Updates in SubscriptionResponse are aggregated.


Basic functionality of the Subscribe STREAM RPC with ON_CHANGE mode.
    # Parameters: common connection parameters, path, read count
    # Failure: Device does not respond, responds with an error, responds with an empty notification set or with a notification without updates, responds with incorrect encoding.
    # Test is passed path to the data model, which contains limited number of elements, where some of them periodically change (e.g. packet count on interface). STREAM` Subscription operation is invoked. First SubscriptionResponse contains all elements, next responses contains only changed elements. After read count parameter test ends (and subscription stream is closed). Test issues WARNING, if SubscriptionResponse stream is closed prematurely. Test issues WARNING if Updates in SubscriptionResponse are aggregated.


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

Subscription test for all device supported encodings, for unsupported encoding, for non existing encoding.

Subscribe for not existing path

Subscribe for not existing prefix

We will not test TARGET_DEFINED mode
# TODO - why?


#   Path prefix = 1;                          // Prefix used for paths.
#   repeated Subscription subscription = 2;   // Set of subscriptions to create.
#   QOSMarking qos = 4;                       // DSCP marking to be used.
#   bool allow_aggregation = 6;
#   repeated ModelData use_models = 7;
#   bool updates_only = 9;
