#!/usr/bin/env python3
import optparse
import threading

from time import sleep

from confd_gnmi_common import *
from gnmi_pb2_grpc import *

log = logging.getLogger('confd_gnmi_client')


class ConfDgNMIClient:

    def __init__(self, host, port,
                 metadata=[('username', 'admin'), ('password', 'admin')]):
        log.info("==> host=%s, port=%i, metadata-%s", host, port, metadata)
        channel = grpc.insecure_channel("{}:{}".format(host, port))
        grpc.channel_ready_future(channel).result(timeout=5)
        self.metadata = metadata
        self.stub = gNMIStub(channel)
        log.info("<== self.stub=%s", self.stub)

    def get_capabilities(self):
        log.info("==>")
        request = gnmi__pb2.CapabilityRequest()
        log.debug("Calling stub.Capabilities")
        response = self.stub.Capabilities(request, metadata=self.metadata)
        print("Capabilities - supported models:")
        for m in response.supported_models:
            print("name:{} organization:{} version: {}".format(m.name,
                                                               m.organization,
                                                               m.version))
        log.info("<== response=%s", response)

    @staticmethod
    def make_subscription_list(prefix, paths, mode):
        log.debug("==> mode=%s", mode)
        qos = gnmi__pb2.QOSMarking(marking=1)
        subscriptions = []
        for path in paths:
            subscriptions.append(gnmi__pb2.Subscription(path=path))
        subscription_list = gnmi__pb2.SubscriptionList(
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
    def generate_subscriptions(subscription_list, poll_interval=0,
                               poll_count=0):
        log.debug("==> subscription_list=%s", subscription_list)

        sub = gnmi__pb2.SubscribeRequest(subscribe=subscription_list,
                                         extension=[])
        print("Generating subscription mode {} ....".format(
            subscription_list.mode))
        yield sub

        if subscription_list.mode == gnmi_pb2.SubscriptionList.POLL:
            for i in range(poll_count):
                sleep(poll_interval)
                print("Generating POLL subscription")
                yield ConfDgNMIClient.make_poll_subscription()

        log.debug("<==")

    @staticmethod
    def print_notification(n):
        print("timestamp {} atomic {}".format(n.timestamp, n.atomic))
        print("Updates:")
        for u in n.update:
            print("path: {} value {}".format(make_xpath_path(u.path), u.val))

    @staticmethod
    def read_subscribe_responses(responses):
        log.info("==>")
        # example to cancel
        # responses.cancel()
        for response in responses:
            log.info("******* Subscription received response=%s", response)
            print("subscribe - response")
            ConfDgNMIClient.print_notification(response.update)

        log.info("<==")

    # TODO this API would change with more subscription support
    def subscribe(self, subscription_list, poll_interval=0,
                  poll_count=0):
        log.info("==>")
        responses = self.stub.Subscribe(
            ConfDgNMIClient.generate_subscriptions(subscription_list,
                                                   poll_interval, poll_count),
            metadata=self.metadata)
        thr = threading.Thread(target=ConfDgNMIClient.read_subscribe_responses,
                               args=(responses,))
        # for response in responses:
        #     log.info("Received subscription response=%s", response)
        thr.start()
        thr.join()
        print(".... subscription done")
        log.info("<==")

    def get(self, prefix, paths, type, encoding):
        log.info("==>")
        path = []
        for p in paths:
            path.append(p)
        request = gnmi_pb2.GetRequest(prefix=prefix, path=path,
                                      type=type,
                                      encoding=encoding,
                                      extension=[])
        response = self.stub.Get(request, metadata=self.metadata)

        print("Get - Notifications:")
        for n in response.notification:
            ConfDgNMIClient.print_notification(n)

        log.info("<== response=%s", response)

    def set(self, prefix, path_vals):
        log.info("==> prefix=%s path_vals=%s", prefix, path_vals)
        update = []
        for pv in path_vals:
            up = gnmi_pb2.Update(path=pv[0], val=pv[1])
            update.append(up)
        request = gnmi_pb2.SetRequest(prefix=prefix, update=update)
        response = self.stub.Set(request, metadata=self.metadata)

        print("Set - UpdateResult:")
        print("timestamp {} prefix {}".format(response.timestamp,
                                              make_xpath_path(
                                                  response.prefix)))
        for r in response.response:
            print("timestamp {} op {} path {}".format(r.timestamp,
                                                      r.op,
                                                      make_xpath_path(
                                                          r.path)))
        log.info("<== response=%s", response)


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
    parser.add_option("-v", "--val", action="append", dest="vals",
                      help="'value' for set operation, can be repeated (empty by default)",
                      default=[])
    (opt, args) = parser.parse_args()
    common_optparse_process(opt, log)

    log.info("paths=%s vals=%s", opt.paths, opt.vals)
    prefix_str = opt.prefix
    prefix = make_gnmi_path(prefix_str)
    paths = [make_gnmi_path(p) for p in opt.paths]
    vals = [gnmi_pb2.TypedValue(string_val=v) for v in opt.vals]
    type = gnmi_pb2.GetRequest.DataType.CONFIG
    encoding = gnmi_pb2.Encoding.BYTES
    subscription_mode = gnmi_pb2.SubscriptionList.POLL

    poll_interval: int = 5
    poll_count: int = 10
    key = 82
    subscription_list = ConfDgNMIClient.make_subscription_list(
        prefix, paths, subscription_mode)

    client = ConfDgNMIClient(HOST, PORT)
    if opt.operation == "capabilities":
        client.get_capabilities()
    elif opt.operation == "subscribe":
        client.subscribe(subscription_list, poll_interval, poll_count)
    elif opt.operation == "get":
        client.get(prefix, paths, type, encoding)
    elif opt.operation == "set":
        if len(paths) != len(vals):
            log.waring("len(paths) != len(vals); %i != %i", len(paths), len(vals))
            print("Number of paths (--path) must be the same as number of vals (--val)!")
        else:
            client.set(prefix, list(zip(paths, vals)))
    else:
        log.warning("Unknown operation %s", opt.operation)
