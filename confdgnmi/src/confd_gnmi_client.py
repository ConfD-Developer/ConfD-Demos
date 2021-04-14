#!/usr/bin/env python3
import logging
import optparse
import threading
from time import sleep

from grpc import channel_ready_future, insecure_channel

import gnmi_pb2
from confd_gnmi_common import HOST, PORT, make_xpath_path, VERSION, \
    common_optparse_options, common_optparse_process, make_gnmi_path, \
    get_data_type, get_sub_mode
from gnmi_pb2_grpc import gNMIStub

log = logging.getLogger('confd_gnmi_client')


class ConfDgNMIClient:

    def __init__(self, host=HOST, port=PORT, metadata=None):
        if metadata is None:
            metadata = [('username', 'admin'), ('password', 'admin')]
        log.info("==> host=%s, port=%i, metadata-%s", host, port, metadata)
        self.channel = insecure_channel("{}:{}".format(host, port))
        channel_ready_future(self.channel).result(timeout=5)
        self.metadata = metadata
        self.stub = gNMIStub(self.channel)
        log.info("<== self.stub=%s", self.stub)

    def close(self):
        self.channel.close()

    def get_capabilities(self):
        log.info("==>")
        request = gnmi_pb2.CapabilityRequest()
        log.debug("Calling stub.Capabilities")
        response = self.stub.Capabilities(request, metadata=self.metadata)
        log.info("<== response.supported_models=%s", response.supported_models)
        return response.supported_models

    @staticmethod
    def make_subscription_list(prefix, paths, mode):
        log.debug("==> mode=%s", mode)
        qos = gnmi_pb2.QOSMarking(marking=1)
        subscriptions = []
        for path in paths:
            if mode == gnmi_pb2.SubscriptionList.STREAM:
                sub = gnmi_pb2.Subscription(path=path,
                                            mode=gnmi_pb2.SubscriptionMode.ON_CHANGE)
            else:
                sub = gnmi_pb2.Subscription(path=path)
            subscriptions.append(sub)
        subscription_list = gnmi_pb2.SubscriptionList(
            prefix=prefix,
            subscription=subscriptions,
            use_aliases=False,
            qos=qos,
            mode=mode,
            allow_aggregation=False,
            use_models=[],
            encoding=gnmi_pb2.Encoding.BYTES,
            updates_only=False
        )

        log.debug("<== subscription_list=%s", subscription_list)
        return subscription_list

    @staticmethod
    def make_poll_subscription():
        log.debug("==>")
        sub = gnmi_pb2.SubscribeRequest(poll=gnmi_pb2.Poll(), extension=[])
        log.debug("<==")
        return sub

    @staticmethod
    def generate_subscriptions(subscription_list, poll_interval=0.0,
                               poll_count=0):
        log.debug("==> subscription_list=%s", subscription_list)

        sub = gnmi_pb2.SubscribeRequest(subscribe=subscription_list,
                                        extension=[])
        log.debug("subscription_list.mode=%s", subscription_list.mode)
        yield sub

        if subscription_list.mode == gnmi_pb2.SubscriptionList.POLL:
            for i in range(poll_count):
                sleep(poll_interval)
                log.debug("Generating POLL subscription")
                yield ConfDgNMIClient.make_poll_subscription()

        log.debug("<==")

    @staticmethod
    def print_notification(n):
        print("timestamp {} prefix {} atomic {}".format(n.timestamp,
                                                        make_xpath_path(
                                                            gnmi_prefix=n.prefix),
                                                        n.atomic))
        print("Updates:")
        for u in n.update:
            print("path: {} value {}".format(make_xpath_path(u.path), u.val))

    @staticmethod
    def read_subscribe_responses(responses, read_count=-1):
        log.info("==> read_count=%s", read_count)
        # example to cancel
        # responses.cancel()
        for response in responses:
            log.info("******* Subscription received response=%s read_count=%i",
                     response, read_count)
            print("subscribe - response read_count={}".format(read_count))
            ConfDgNMIClient.print_notification(response.update)
            if read_count > 0:
                read_count -= 1
                if read_count == 0:
                    break
        log.info("Canceling read")
        # See https://stackoverflow.com/questions/54588382/
        # how-can-a-grpc-server-notice-that-the-client-has-cancelled-a-server-side-streami
        responses.cancel()

        log.info("<==")

    # TODO this API would change with more subscription support
    def subscribe(self, subscription_list, read_thread=None,
                  poll_interval=0.0, poll_count=0, read_count=-1):
        log.info("==>")
        responses = self.stub.Subscribe(
            ConfDgNMIClient.generate_subscriptions(subscription_list,
                                                   poll_interval, poll_count),
            metadata=self.metadata)
        if read_thread is not None:
            thr = threading.Thread(target=read_thread,
                                   args=(responses, read_count,))
            thr.start()
            thr.join()
        log.info("<== responses=%s", responses)
        return responses

    def get(self, prefix, paths, get_type, encoding):
        log.info("==>")
        path = []
        for p in paths:
            path.append(p)
        request = gnmi_pb2.GetRequest(prefix=prefix, path=path,
                                      type=get_type,
                                      encoding=encoding,
                                      extension=[])
        response = self.stub.Get(request, metadata=self.metadata)

        log.info("<== response.notification=%s", response.notification)
        return response.notification

    def set(self, prefix, path_vals):
        log.info("==> prefix=%s path_vals=%s", prefix, path_vals)
        update = []
        for pv in path_vals:
            up = gnmi_pb2.Update(path=pv[0], val=pv[1])
            update.append(up)
        request = gnmi_pb2.SetRequest(prefix=prefix, update=update)
        response = self.stub.Set(request, metadata=self.metadata)
        log.info("<== response=%s", response)
        return response


if __name__ == '__main__':
    parser = optparse.OptionParser(version="%prog {}".format(VERSION))
    parser.add_option("-o", "--oper", action="store", dest="operation",
                      help="gNMI operation [capabilities, set, get, subscribe]",
                      default="capabilities")
    common_optparse_options(parser)
    parser.add_option("--prefix", action="store", dest="prefix",
                      help="'prefix' path for set, get and subscribe operation (empty by default)",
                      default="")
    parser.add_option("-p", "--path", action="append", dest="paths",
                      help="'path' for get, set and subscribe operation, can be repeated (empty by default)",
                      default=[])
    parser.add_option("-t", "--data-type", action="store", dest="datatype",
                      help="'data type' for get operation, can be ALL, CONFIG, STATE, OPERATIONAL  (default 'CONFIG')",
                      default="CONFIG")
    parser.add_option("-v", "--val", action="append", dest="vals",
                      help="'value' for set operation, can be repeated (empty by default)",
                      default=[])
    parser.add_option("-s", "--sub-mode", action="store", dest="submode",
                      help="subscription mode, can be ONCE, POLL, STREAM (default 'ONCE')",
                      default="ONCE")
    parser.add_option("--poll-count", action="store", dest="pollcount",
                      type=int,
                      help="Number of POLLs (default 5)",
                      default=5)
    parser.add_option("--poll-interval", action="store", dest="pollinterval",
                      type=float,
                      help="Interval (in seconds) between POLL requests (default 0.5)",
                      default=0.5)
    parser.add_option("--read-count", action="store", dest="readcount",
                      type=int,
                      help="Number of read requests for STREAM subscription (default 4)",
                      default=4)

    (opt, args) = parser.parse_args()
    common_optparse_process(opt, log)
    log.debug("opt=%s", opt)
    log.info("paths=%s vals=%s", opt.paths, opt.vals)
    prefix_str = opt.prefix
    prefix = make_gnmi_path(prefix_str)
    paths = [make_gnmi_path(p) for p in opt.paths]
    vals = [gnmi_pb2.TypedValue(string_val=v) for v in opt.vals]

    datatype = get_data_type(opt.datatype)
    subscription_mode = get_sub_mode(opt.submode)
    poll_interval: float = opt.pollinterval
    poll_count: int = opt.pollcount
    read_count: int = opt.readcount

    log.debug("datatype=%s subscription_mode=%s poll_interval=%s "
              "poll_count=%s read_count=%s",
              datatype, subscription_mode, poll_interval, poll_count,
              read_count)

    encoding = gnmi_pb2.Encoding.BYTES
    subscription_list = ConfDgNMIClient.make_subscription_list(
        prefix, paths, subscription_mode)

    client = ConfDgNMIClient(HOST, PORT)
    if opt.operation == "capabilities":
        supported_models = client.get_capabilities()
        print("Capabilities - supported models:")
        for m in supported_models:
            print("name:{} organization:{} version: {}".format(m.name,
                                                               m.organization,
                                                               m.version))
    elif opt.operation == "subscribe":
        print("Starting subscription ....")
        client.subscribe(subscription_list,
                         read_thread=ConfDgNMIClient.read_subscribe_responses,
                         poll_interval=poll_interval, poll_count=poll_count,
                         read_count=read_count)
        print(".... subscription done")
    elif opt.operation == "get":
        notification = client.get(prefix, paths, datatype, encoding)
        print("Get - Notifications:")
        for n in notification:
            ConfDgNMIClient.print_notification(n)
    elif opt.operation == "set":
        if len(paths) != len(vals):
            log.warning("len(paths) != len(vals); %i != %i", len(paths),
                        len(vals))
            print(
                "Number of paths (--path) must be the same as number of vals (--val)!")
        else:
            response = client.set(prefix, list(zip(paths, vals)))
            print("Set - UpdateResult:")
            print("timestamp {} prefix {}".format(response.timestamp,
                                                  make_xpath_path(
                                                      response.prefix)))
            for r in response.response:
                print("timestamp {} op {} path {}".format(r.timestamp,
                                                          r.op,
                                                          make_xpath_path(
                                                              r.path)))
    else:
        log.warning("Unknown operation %s", opt.operation)
    client.close()
