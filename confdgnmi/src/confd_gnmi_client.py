#!/usr/bin/env python3
import argparse
import logging
import ssl
import sys
import json
from time import sleep
from contextlib import closing

from grpc import channel_ready_future, insecure_channel, secure_channel, \
    ssl_channel_credentials
from grpc._channel import _MultiThreadedRendezvous

import gnmi_pb2
from confd_gnmi_common import HOST, PORT, make_xpath_path, VERSION, \
    common_optparse_options, common_optparse_process, make_gnmi_path, \
    get_data_type, get_sub_mode
from gnmi_pb2_grpc import gNMIStub

log = logging.getLogger('confd_gnmi_client')


class ConfDgNMIClient:

    def __init__(self, host=HOST, port=PORT, metadata=None, insecure=False,
                 server_crt_file=None, username="admin", password="admin"):
        if metadata is None:
            metadata = [('username', username), ('password', password)]
        log.info("==> host=%s, port=%i, metadata-%s", host, port, metadata)
        if insecure:
            self.channel = insecure_channel("{}:{}".format(host, port))
        else:
            options = ()
            if server_crt_file:
                with open(server_crt_file, "rb") as s:
                    ssl_cert = s.read()
            else:
                # Example of overriding target name in options, if needed:
                #  options = (("grpc.ssl_target_name_override", ""),)
                ssl_cert = ssl.get_server_certificate((host, port)).encode(
                    "utf-8")
            assert ssl_cert is not None
            self.channel = secure_channel("{}:{}".format(host, port),
                                          ssl_channel_credentials(
                                              root_certificates=ssl_cert),
                                          options=options)
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
    def make_subscription_list(prefix, paths, mode, encoding):
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
            qos=qos,
            mode=mode,
            allow_aggregation=False,
            use_models=[],
            encoding=encoding,
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
                               poll_count=0, subscription_end_delay=0.0):
        log.debug("==> subscription_list=%s", subscription_list)

        sub = gnmi_pb2.SubscribeRequest(subscribe=subscription_list,
                                        extension=[])
        log.debug("subscription_list.mode=%s", subscription_list.mode)
        yield sub

        if subscription_list.mode == gnmi_pb2.SubscriptionList.POLL:
            for i in range(poll_count):
                # TODO preparation for interactive POLL control
                # print("Press Enter to Poll")
                # sys.stdin.readline()
                sleep(poll_interval)
                log.debug("Generating POLL subscription")
                log.info("poll #%s", i)
                yield ConfDgNMIClient.make_poll_subscription()
        sleep(subscription_end_delay)
        log.info("Stopped generating SubscribeRequest(s)")
        log.debug("<==")

    @staticmethod
    def print_notification(n):
        pfx_str = make_xpath_path(gnmi_prefix=n.prefix)
        print("timestamp {} prefix {} atomic {}".format(n.timestamp, pfx_str,
                                                        n.atomic))
        print("Updates:")
        for u in n.update:
            if u.val.json_val:
                value = json.loads(u.val.json_val)
            elif u.val.json_ietf_val:
                value = json.loads(u.val.json_ietf_val)
            else:
                value = str(u.val)
            print("path: {} value {}".format(pfx_str + make_xpath_path(u.path),
                                             value))

    @staticmethod
    def read_subscribe_responses(responses, read_count=-1):
        log.info("==> read_count=%s", read_count)
        # example to cancel
        # responses.cancel()
        try:
            for response in responses:
                log.info("******* Subscription received response=%s read_count=%i",
                         response, read_count)
                print("subscribe - response read_count={}".format(read_count))
                ConfDgNMIClient.print_notification(response.update)
                if read_count > 0:
                    read_count -= 1
                    if read_count == 0:
                        break
        except _MultiThreadedRendezvous as e:
            if "EOF" in e.details():
                log.warning("e.details=%s", e.details())
            else:
                raise e
        log.info("Stopped reading SubscribeResponse(s)")
        log.info("Canceling read")
        # See https://stackoverflow.com/questions/54588382/
        # how-can-a-grpc-server-notice-that-the-client-has-cancelled-a-server-side-streami
        responses.cancel()

        log.info("<==")

    # TODO this API would change with more subscription support
    def subscribe(self, subscription_list, read_fun=None,
                  poll_interval=0.0, poll_count=0, read_count=-1,
                  subscription_end_delay=0.0):
        log.info("==>")
        responses = self.stub.Subscribe(
            ConfDgNMIClient.generate_subscriptions(subscription_list,
                                                   poll_interval, poll_count, subscription_end_delay),
            metadata=self.metadata)
        if read_fun is not None:
            read_fun(responses, read_count)
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

    def delete(self, prefix, paths):
        log.info("==> prefix=%s paths=%s", prefix, paths)
        request = gnmi_pb2.SetRequest(prefix=prefix, delete=paths)
        response = self.stub.Set(request, metadata=self.metadata)
        log.info("<== response=%s", response)
        return response


def parse_args(args):
    log.debug("==> args=%s", args)
    parser = argparse.ArgumentParser(description="gNMI Adapter client")
    parser.add_argument("--version", action="version",
                        version="%(prog)s {}".format(VERSION))
    parser.add_argument("-o", "--oper", action="store", dest="operation",
                        choices=["capabilities", "set", "get", "delete", "subscribe"],
                        help="gNMI operation",
                        default="capabilities")
    common_optparse_options(parser)
    parser.add_argument("--prefix", action="store", dest="prefix",
                        help="'prefix' path for set, get and subscribe operation (empty by default)",
                        default="")
    parser.add_argument("-p", "--path", action="append", dest="paths",
                        help="'path' for get, set and subscribe operation, can be repeated (empty by default)",
                        default=[])
    parser.add_argument("-t", "--data-type", action="store", dest="datatype",
                        choices=["ALL", "CONFIG", "STATE", "OPERATIONAL"],
                        help="'data type' for get operation (default 'CONFIG')",
                        default="CONFIG")
    parser.add_argument("-v", "--val", action="append", dest="vals",
                        help="'value' for set operation, can be repeated (empty by default)",
                        default=[])
    parser.add_argument("-s", "--sub-mode", action="store", dest="submode",
                        choices=["ONCE", "POLL", "STREAM"],
                        help="subscription mode (default ONCE)",
                        default="ONCE")
    parser.add_argument("--poll-count", action="store", dest="pollcount",
                        type=int,
                        help="Number of POLLs (default 5)",
                        default=5)
    parser.add_argument("--poll-interval", action="store", dest="pollinterval",
                        type=float,
                        help="Interval (in seconds) between POLL requests (default 0.5)",
                        default=0.5)
    parser.add_argument("--subscription-end-delay", action="store", dest="subscription_end_delay",
                        type=float,
                        help="Time to wait (in seconds) to finish stream after all "
                             "subscription requests (default 0.0)",
                        default=0.0)
    parser.add_argument("--read-count", action="store", dest="readcount",
                        type=int,
                        help="Number of read requests for STREAM subscription (default 4)",
                        default=4)
    parser.add_argument("--server-crt", action="store", dest="servercrt",
                        help="Path to the server certificate.",
                        default=None)
    parser.add_argument("--user", action="store", dest="username",
                        help="User (default 'admin')",
                        default='admin')
    parser.add_argument("--password", action="store", dest="password",
                        help="Password (default 'admin')",
                        default='admin')
    parser.add_argument("--encoding", choices=["JSON", "JSON_IETF"],
                        help="Requested encoding for get and subscribe (default 'JSON_IETF')",
                        default="JSON_IETF")
    opt = parser.parse_args(args=args)
    log.debug("opt=%s", opt)
    return opt


if __name__ == '__main__':
    opt = parse_args(args=sys.argv[1:])
    common_optparse_process(opt, log)
    log.debug("opt=%s", opt)
    log.info("paths=%s vals=%s", opt.paths, opt.vals)
    prefix_str = opt.prefix
    prefix = make_gnmi_path(prefix_str)
    paths = [make_gnmi_path(p) for p in opt.paths]
    vals = [gnmi_pb2.TypedValue(json_ietf_val=v.encode()) for v in opt.vals]

    datatype = get_data_type(opt.datatype)
    subscription_mode = get_sub_mode(opt.submode)
    poll_interval: float = opt.pollinterval
    poll_count: int = opt.pollcount
    read_count: int = opt.readcount
    subscription_end_delay: float = opt.subscription_end_delay

    log.debug("datatype=%s subscription_mode=%s poll_interval=%s "
              "poll_count=%s read_count=%s subscription_end_delay=%s",
              datatype, subscription_mode, poll_interval, poll_count,
              read_count, subscription_end_delay)
    if opt.submode != "STREAM":
        read_count = -1;

    encoding = dict(JSON=gnmi_pb2.Encoding.JSON,
                    JSON_IETF=gnmi_pb2.Encoding.JSON_IETF)[opt.encoding]
    subscription_list = ConfDgNMIClient.make_subscription_list(
        prefix, paths, subscription_mode, encoding)

    with closing(ConfDgNMIClient(opt.host, opt.port, insecure=opt.insecure,
                                 server_crt_file=opt.servercrt,
                                 username=opt.username,
                                 password=opt.password)) as client:
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
                             read_fun=ConfDgNMIClient.read_subscribe_responses,
                             poll_interval=poll_interval, poll_count=poll_count,
                             read_count=read_count,
                             subscription_end_delay=subscription_end_delay)
            print(".... subscription done")
        elif opt.operation == "get":
            notification = client.get(prefix, paths, datatype, encoding)
            print("Get - Notifications:")
            for n in notification:
                ConfDgNMIClient.print_notification(n)
        elif opt.operation in ("set", "delete"):
            if opt.operation == "set":
                if len(paths) != len(vals):
                    log.warning("len(paths) != len(vals); %i != %i", len(paths),
                                len(vals))
                    raise RuntimeError(
                        "Number of paths (--path) must be the same as number of vals (--val)!")
                else:
                    response = client.set(prefix, list(zip(paths, vals)))
            else:
                response = client.delete(prefix, paths)
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
