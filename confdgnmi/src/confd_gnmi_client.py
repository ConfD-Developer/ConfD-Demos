#!/usr/bin/env python3
import argparse
import logging
import sys
import json
from contextlib import closing
import asyncio

import gnmi.proto as gp
import betterproto
import grpclib.client

from confd_gnmi_common import HOST, PORT, make_xpath_path, VERSION, \
    common_optparse_options, common_optparse_process, make_gnmi_path, \
    get_data_type, get_sub_mode

log = logging.getLogger('confd_gnmi_client')


class ConfDgNMIClient:

    def __init__(self, host=HOST, port=PORT, metadata=None):
        if metadata is None:
            metadata = [('username', 'admin'), ('password', 'admin')]
        log.info("==> host=%s, port=%i, metadata-%s", host, port, metadata)
        self.channel = grpclib.client.Channel(host="127.0.0.1", port=50061, ssl=None)
        self.service = gp.gNMIStub(
            self.channel, metadata={"username": "admin", "password": "admin"})
        self.metadata = metadata
        log.info("<== self.service=%s", self.service)

    def close(self):
        self.channel.close()

    async def get_capabilities(self):
        log.info("==>")
        log.debug("Calling stub.Capabilities")
        response = await self.service.capabilities()
        log.info("<== response.supported_models=%s", response.supported_models)
        return response.supported_models

    @staticmethod
    def make_subscription_list(prefix, paths, mode):
        log.debug("==> mode=%s", mode)
        qos = gp.QoSMarking(marking=1)
        subscriptions = []
        for path in paths:
            if mode == gp.SubscriptionListMode.STREAM:
                sub = gp.Subscription(path=path, mode=gp.SubscriptionMode.ON_CHANGE)
            else:
                sub = gp.Subscription(path=path)
            subscriptions.append(sub)
        subscription_list = gp.SubscriptionList(
            prefix=prefix,
            subscription=subscriptions,
            qos=qos,
            mode=mode,
            allow_aggregation=False,
            use_models=[],
            encoding=gp.Encoding.BYTES,
            updates_only=False
        )

        log.debug("<== subscription_list=%s", subscription_list)
        return subscription_list

    @staticmethod
    def make_poll_subscription():
        log.debug("==>")
        sub = gp.SubscribeRequest(poll=gp.Poll(), extension=[])
        log.debug("<==")
        return sub

    @staticmethod
    async def generate_subscriptions(subscription_list, poll_interval=0.0,
                                     poll_count=0):
        log.debug("==> subscription_list=%s", subscription_list)

        sub = gp.SubscribeRequest(subscribe=subscription_list, extension=[])
        log.debug("subscription_list.mode=%s", subscription_list.mode)
        yield sub

        if subscription_list.mode == gp.SubscriptionListMode.POLL:
            for i in range(poll_count):
                await asyncio.sleep(poll_interval)
                log.debug("Generating POLL subscription")
                yield ConfDgNMIClient.make_poll_subscription()

        log.debug("<==")

    @staticmethod
    def print_notification(n):
        pfx_str = make_xpath_path(gnmi_prefix=n.prefix)
        print("timestamp {} prefix {} atomic {}".format(n.timestamp, pfx_str, n.atomic))
        print("Updates:")
        for u in n.update:
            field, fvalue = betterproto.which_one_of(u.val, 'value')
            if field == 'json_val':
                value = json.loads(fvalue)
            elif field == 'json_ietf_val':
                value = json.loads(fvalue)
            else:
                value = str(fvalue)
            print("path: {} value {}".format(pfx_str + make_xpath_path(u.path), value))

    @staticmethod
    async def read_subscribe_responses(responses, read_count=-1):
        log.info("==> read_count=%s", read_count)
        # example to cancel
        # responses.cancel()
        async for response in responses:
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
        # responses.cancel()

        log.info("<==")

    # TODO this API would change with more subscription support
    async def subscribe(self, subscription_list, read_fun=None,
                        poll_interval=0.0, poll_count=0, read_count=-1):
        log.info("==>")
        responses = self.service.subscribe(
            ConfDgNMIClient.generate_subscriptions(subscription_list, poll_interval, poll_count))
        if read_fun is not None:
            await read_fun(responses, read_count)
        log.info("<== responses=%s", responses)
        return responses

    async def get(self, prefix, paths, get_type, encoding):
        log.info("==>")
        path = []
        for p in paths:
            path.append(p)
        response = await self.service.get(path=p, type=get_type, encoding=encoding, extension=[])
        log.info("<== response.notification=%s", response.notification)
        return response.notification

    async def set(self, prefix, path_vals):
        log.info("==> prefix=%s path_vals=%s", prefix, path_vals)
        response = await self.service.set(prefix=prefix,
                                          update=[gp.Update(path=pv[0], val=pv[1])
                                                  for pv in path_vals])

        log.info("<== response=%s", response)
        return response

    async def delete(self, prefix, paths):
        log.info("==> prefix=%s paths=%s", prefix, paths)
        response = await self.service.set(prefix=prefix, delete=paths)
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
    parser.add_argument("--read-count", action="store", dest="readcount",
                        type=int,
                        help="Number of read requests for STREAM subscription (default 4)",
                        default=4)
    parser.add_argument("--encoding", choices=["BYTES", "JSON", "JSON_IETF"], default="JSON_IETF")
    opt = parser.parse_args(args=args)
    log.debug("opt=%s", opt)
    return opt


async def main():
    opt = parse_args(args=sys.argv[1:])
    common_optparse_process(opt, log)
    log.debug("opt=%s", opt)
    log.info("paths=%s vals=%s", opt.paths, opt.vals)
    prefix_str = opt.prefix
    prefix = make_gnmi_path(prefix_str)
    paths = [make_gnmi_path(p) for p in opt.paths]
    vals = [gp.TypedValue(json_ietf_val=v.encode()) for v in opt.vals]

    datatype = get_data_type(opt.datatype)
    subscription_mode = get_sub_mode(opt.submode)
    poll_interval: float = opt.pollinterval
    poll_count: int = opt.pollcount
    read_count: int = opt.readcount

    log.debug("datatype=%s subscription_mode=%s poll_interval=%s "
              "poll_count=%s read_count=%s",
              datatype, subscription_mode, poll_interval, poll_count,
              read_count)

    encoding = dict(BYTES=gp.Encoding.BYTES,
                    JSON=gp.Encoding.JSON,
                    JSON_IETF=gp.Encoding.JSON_IETF)[opt.encoding]
    subscription_list = ConfDgNMIClient.make_subscription_list(
        prefix, paths, subscription_mode)

    with closing(ConfDgNMIClient(HOST, PORT)) as client:
        if opt.operation == "capabilities":
            print('get caps')
            try:
                supported_models = await client.get_capabilities()
                print("Capabilities - supported models:")
                for m in supported_models:
                    print("name:{} organization:{} version: {}".format(m.name,
                                                                       m.organization,
                                                                       m.version))
            except Exception as ex:
                print('failed', ex)

        elif opt.operation == "subscribe":
            print("Starting subscription ....")
            await client.subscribe(subscription_list,
                                   read_fun=ConfDgNMIClient.read_subscribe_responses,
                                   poll_interval=poll_interval, poll_count=poll_count,
                                   read_count=read_count)
            print(".... subscription done")
        elif opt.operation == "get":
            notification = await client.get(prefix, paths, datatype, encoding)
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
                    response = await client.set(prefix, list(zip(paths, vals)))
            else:
                response = await client.delete(prefix, paths)
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


if __name__ == '__main__':
    asyncio.run(main())
