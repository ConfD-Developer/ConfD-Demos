class Subscriber {

    static def subHead = { mode ->
        def skipList = [UmlCommon.user]
        if (mode != SubMode.STREAM_DP) {
            skipList += [UmlCommon.dataprovider]
        }
        UmlCommon.makeHeader(delegate, "${mode} subscription",
                [skipList: skipList])
    }

    enum SubMode {
        ONCE, POLL, STREAM, STREAM_DP
    }

    static def subscrCl = { mode ->
        divider "Subscription"
        msgAd "[", to: UmlCommon.client, text: '<size:24><&person></size> ""subscribe""', {
            note 'Subscription invoked. Request iterator (""SubscribeRequest"") is sent to the server, response iterator (""SubscribeResponse"") is returned to the client.', pos: "right of $UmlCommon.client"
            msg UmlCommon.client, to: UmlCommon.server, text: "Subscribe(stream SubscribeRequest)", returnText: "stream SubscribeResponse", activate: true
            note 'The client starts reading responses in dedicated thread (""read_subscribe_responses"").', pos: "right of $UmlCommon.client"
            msg UmlCommon.client, to: UmlCommon.sub_read, text: 'start thread\\n""read_subscribe_responses(responseIterator)""', activate: true, noReturn: true
            msgAd UmlCommon.sub_read, text: "iterate over responseIterator", {
                msgAd UmlCommon.server, text: "subscription processing", {

                    def yieldText = '""yield SubscribeRequest"" item'
                    note 'The server gets next element from ""SubscribeRequest"" stream (calls ""next(request_iterator)"").', pos: "right of $UmlCommon.client"
                    msgAd UmlCommon.server, to: UmlCommon.client, text: 'next SubscribeRequest\\n(""generate_subscriptions"")', returnText: yieldText
                    note 'The client uses ""generate_subscriptions"" generator function to return next ""SubscribeRequest"" in the stream.', pos: "right of $UmlCommon.client"
                    msg UmlCommon.server, to: UmlCommon.adapter, text: "read", activate: true, returnText: "current sample", {
                        note 'Get current sample (all values).', pos: "right of $UmlCommon.server"
                        msgAd UmlCommon.adapter, to: UmlCommon.device_adapter, text: "get_sample", {
                            if (mode == SubMode.STREAM_DP) {
                                msgAd UmlCommon.device_adapter, to: UmlCommon.device, text: "get data", {
                                    msg UmlCommon.device, to: UmlCommon.dataprovider, noReturn: true, type: UmlCommon.arrowBi, text: '""get_next""\\n""get_elem""'
                                }
                            } else {
                                msg UmlCommon.device_adapter, to: UmlCommon.device, noReturn: true, type: UmlCommon.arrowBi
                            }
                        }
                        if (mode == SubMode.STREAM || mode == SubMode.STREAM) {
                            msg  UmlCommon.adapter, to: UmlCommon.device_adapter, text: "start_monitoring", activate: true
                            msg UmlCommon.device_adapter, text: "monitoring thread", activate: true
                        }
                    }
                    def response = {
                        msg UmlCommon.server, to: UmlCommon.sub_read, text: 'SubscribeResponse\\n(returned in response stream)', activate: false, noReturn: true, type: UmlCommon.arrowReturn, {
                            msgAd UmlCommon.sub_read, text: "process response"
                        }
                    }
                    delegate << response

                    if (mode == SubMode.POLL) {
                        loop '""poll_count"" times', {
                            yieldText = '""yield SubscribeRequest"" item with ""poll"" element'
                            note 'The server gets next element from ""SubscribeRequest"" stream (calls ""next(request_iterator)"").', pos: "right of $UmlCommon.client"
                            msgAd UmlCommon.server, to: UmlCommon.client, text: 'next SubscribeRequest\\n(""generate_subscriptions"")', returnText: yieldText
                            note 'When ""poll"" request comes, get current values and return them in response stream.', pos: "right of $UmlCommon.server"
                            msg UmlCommon.server, to: UmlCommon.adapter, text: "poll", type: UmlCommon.arrowReturn, noReturn: true
                            msgAd UmlCommon.adapter, to: UmlCommon.device_adapter, text: "get_sample", {
                                msg UmlCommon.device_adapter, to: UmlCommon.device, noReturn: true, type: UmlCommon.arrowBi
                            }
                            msg UmlCommon.adapter, to: UmlCommon.server, text: "current (poll) sample", type: UmlCommon.arrowReturn, noReturn: true
                            delegate << response
                        }
                    }

                    if (mode == SubMode.STREAM || mode == SubMode.STREAM_DP) {
                        loop '""read_count - 1 "" times', {
                            if (mode == SubMode.STREAM_DP) {
                                msgAd UmlCommon.dataprovider, text: "Generate\\nchange of data", {
                                    msgAd  UmlCommon.dataprovider, to: UmlCommon.device_adapter, text: "Send changes\\nover external change socket", noReturn: true, {
                                        msgAd UmlCommon.device_adapter, text: "Process (extract) changes\\nfrom byte stream."
                                    }
                                }
                            }
                            note 'Send message that changes are available.', pos: "left of $UmlCommon.device_adapter"
                            msg UmlCommon.device_adapter, to: UmlCommon.adapter, text: "SEND_CHANGES", type: UmlCommon.arrowReturn, noReturn: true
                            note 'get changes', pos: "right of $UmlCommon.adapter"
                            msgAd UmlCommon.adapter, to: UmlCommon.device_adapter, text: "get_monitored_changes"
                            msg UmlCommon.adapter, to: UmlCommon.server, text: "current changes", type: UmlCommon.arrowReturn, noReturn: true
                            note 'return changes in the response stream', pos: "right of $UmlCommon.server"
                            delegate << response
                        }
                    }
                }
            }
            deactivate UmlCommon.server
            if (mode == SubMode.POLL || mode == SubMode.STREAM || mode == SubMode.STREAM_DP) {
                note 'Client or Server stops Request/Response stream.', pos: "right of $UmlCommon.server"
                msgAd UmlCommon.sub_read, to: UmlCommon.server, type: UmlCommon.arrowReturn, text: 'reading ended\\n(""subscribe_rpc_done"")', {
                    msgAd UmlCommon.server, to: UmlCommon.adapter, text: "stop", {
                        if (mode == SubMode.STREAM) {
                            msgAd UmlCommon.adapter, to: UmlCommon.device_adapter, text: "stop_monitoring"
                        }
                    }

                }
                deactivate UmlCommon.device_adapter
                deactivate UmlCommon.device_adapter
            }
            deactivate UmlCommon.adapter
            msg UmlCommon.sub_read, to: UmlCommon.client, type: UmlCommon.arrowReturn, text: "end response thread", noReturn: true
            deactivate UmlCommon.sub_read
        }
    }

    static def makeSubscriberOnceSeq(builder) {
        builder.plantuml {
            delegate << subHead.curry(SubMode.ONCE)
            delegate << subscrCl.curry(SubMode.ONCE)
        }
    }

    static def makeSubscriberPollSeq(builder) {
        builder.plantuml {
            delegate << subHead.curry(SubMode.POLL)
            delegate << subscrCl.curry(SubMode.POLL)
        }
    }

    static def makeSubscriberStreamSeq(builder) {
        builder.plantuml {
            delegate << subHead.curry(SubMode.STREAM)
            delegate << subscrCl.curry(SubMode.STREAM)
        }
    }

    static def makeSubscriberDpStreamSeq(builder) {
        builder.plantuml {
            delegate << subHead.curry(SubMode.STREAM_DP)
            delegate << subscrCl.curry(SubMode.STREAM_DP)
        }
    }


}
