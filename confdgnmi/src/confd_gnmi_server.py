#!/usr/bin/env python3
import logging
import optparse
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from enum import Enum

import grpc

import gnmi_pb2
from confd_gnmi_common import PORT, common_optparse_options, \
    common_optparse_process, VERSION
from gnmi_pb2_grpc import gNMIServicer, add_gNMIServicer_to_server

log = logging.getLogger('confd_gnmi_server')


class AdapterType(Enum):
    DEMO = 0
    API = 1
    NETCONF = 2


class ConfDgNMIServicer(gNMIServicer):

    # parameterized constructor
    def __init__(self, adapter_type):
        self.adapter_type = adapter_type
        assert isinstance(self.adapter_type, AdapterType)

    @staticmethod
    def extract_user_metadata(context):
        log.debug("=>")
        log.debug("metadata=%s", context.invocation_metadata())
        metadict = dict(context.invocation_metadata())
        username = metadict["username"]
        password = metadict["password"]
        log.debug("<= username=%s password=:-)", username)
        return username, password

    def get_and_connect_adapter(self, username, password):
        log.debug("==> self.adapter_type=%s username=%s password=:-)",
                  self.adapter_type, username)
        adapter = None
        if self.adapter_type == AdapterType.DEMO:
            from confd_gnmi_demo_adapter import GnmiDemoServerAdapter
            adapter = GnmiDemoServerAdapter.get_adapter()
        elif self.adapter_type == AdapterType.API:
            from confd_gnmi_api_adapter import GnmiConfDApiServerAdapter
            adapter = GnmiConfDApiServerAdapter.get_adapter()
            adapter.connect(addr=GnmiConfDApiServerAdapter.confd_addr,
                            port=GnmiConfDApiServerAdapter.confd_port,
                            username=username, password=password)
        log.debug("<== adapter=%s", adapter)
        return adapter

    def get_connected_adapter(self, context):
        """
        Get adapter and connect it to ConfD if needed
        Currently we always create new instance, later on
        a pool of adapters can be maintained.
        :param context:
        :return:
        """
        log.debug("==>")
        (username, password) = self.extract_user_metadata(context)
        adapter = self.get_and_connect_adapter(username=username,
                                               password=password)
        log.debug("<== adapter=%s", adapter)
        return adapter

    def Capabilities(self, request, context):
        """Capabilities allows the client to retrieve the set of capabilities
        that is supported by the target. This allows the target to validate the
        service version that is implemented and retrieve the set of models that
        the target supports. The models can then be specified in subsequent RPCs
        to restrict the set of data that is utilized.
        Reference: gNMI Specification Section 3.2
        """
        log.info("==> request=%s context=%s", request, context)
        supported_models = []

        adapter = self.get_connected_adapter(context)

        for cap in adapter.capabilities():
            supported_models.append(
                gnmi_pb2.ModelData(name=cap.name,
                                   organization=cap.organization,
                                   version=cap.version)
            )
        response = gnmi_pb2.CapabilityResponse(
            supported_models=supported_models,
            supported_encodings=[gnmi_pb2.Encoding.JSON,
                                 gnmi_pb2.Encoding.BYTES],
            gNMI_version="proto3",
            extension=[])
        # context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        # context.set_details('Method not implemented!')
        # raise NotImplementedError('Method not implemented!')
        log.info("<== response=%s", response)
        return response

    def Get(self, request, context):
        """
        Retrieve a snapshot of data from the target. A Get RPC requests that
        the target snapshots a subset of the data tree as specified by the paths
        included in the message and serializes this to be returned to the
        client using the specified encoding.
        Reference: gNMI Specification Section 3.3
        """
        log.info("==> request=%s context=%s", request, context)
        adapter = self.get_connected_adapter(context)

        notifications = adapter.get(request.prefix, request.path,
                                    request.type, request.use_models)
        response = gnmi_pb2.GetResponse(notification=notifications)

        log.info("<== response=%s", response)
        return response

    def Set(self, request, context):
        """Set allows the client to modify the state of data on the target. The
        paths to modified along with the new values that the client wishes
        to set the value to.
        Reference: gNMI Specification Section 3.4
        """
        log.info("==> request=%s context=%s", request, context)
        adapter = self.get_connected_adapter(context)

        response = []
        # TODO for now we only process update list
        for up in request.update:
            op = adapter.set(request.prefix, up.path, up.val)
            ur = gnmi_pb2.UpdateResult(timestamp=0, path=up.path, op=op)
            response.append(ur)

        response = gnmi_pb2.SetResponse(prefix=request.prefix,
                                        response=response, timestamp=0)

        log.info("<== response=%s", response)
        return response

    @staticmethod
    def _read_sub_request(request_iterator, handler, stop_on_end=False):
        log.debug("==> stop_on_end=%s", stop_on_end)
        try:
            for req in request_iterator:
                # TODO check req mode is POLL
                log.debug("req=%s", req)
                if hasattr(req, "poll"):
                    handler.poll()
                elif hasattr(req, "alias"):
                    # TODO exception, "alias: request not yet implemented
                    assert False
                else:
                    # TODO exception, not expected other type of request
                    assert False
        except grpc.RpcError as e:
            # check if this is end of Poll sending
            if handler.is_poll():
                log.exception(e)
        log.debug("Request loop ended.")
        if stop_on_end:
            log.debug("stopping handler")
            handler.stop()
        log.debug("<==")

    def Subscribe(self, request_iterator, context):
        """Subscribe allows a client to request the target to send it values
        of particular paths within the data tree. These values may be streamed
        at a particular cadence (STREAM), sent one off on a long-lived channel
        (POLL), or sent as a one-off retrieval (ONCE).
        Reference: gNMI Specification Section 3.5
        """
        log.info(
            "==> request_iterator=%s context=%s", request_iterator, context)

        def subscribe_rpc_done():
            log.info("==>")
            if not handler.is_once():
                handler.stop()
            log.info("<==")

        request = next(request_iterator)
        adapter = self.get_connected_adapter(context)
        context.add_callback(subscribe_rpc_done)
        # first request, should contain subscription list (`subscribe`)
        assert hasattr(request, "subscribe")
        handler = adapter.get_subscription_handler(request.subscribe)

        thr = None
        if not handler.is_once():
            thr = threading.Thread(target=ConfDgNMIServicer._read_sub_request,
                                   args=(request_iterator, handler,
                                         handler.is_poll()))
            thr.start()
        # `yield from` can be used, but to allow altering (e.g. path conversion)
        # response later on we use `for`
        for response in handler.read():
            log.debug("response received, calling yield")
            yield response

        if thr is not None:
            thr.join()
        log.info("")
        log.info("<==")

    @staticmethod
    def serve(port=PORT, adapter_type=AdapterType.DEMO):
        log.info("==> port=%s adapter_type=%s", port, adapter_type)

        server = grpc.server(ThreadPoolExecutor(max_workers=10))
        add_gNMIServicer_to_server(ConfDgNMIServicer(adapter_type), server)
        server.add_insecure_port("[::]:{}".format(port))
        server.start()
        log.info("<== server=%s", server)
        return server


if __name__ == '__main__':
    from confd_gnmi_api_adapter import GnmiConfDApiServerAdapter

    parser = optparse.OptionParser(version="%prog {}".format(VERSION))
    parser.add_option("-t", "--type", action="store", dest="type",
                      help="gNMI server type  [api, netconf, demo]",
                      default="demo")
    common_optparse_options(parser)
    parser.add_option("-d", "--confd-debug", action="store", dest="confd_debug",
                      help="ConfD debug level  [trace, debug, silent, proto]",
                      default="debug")
    parser.add_option("--confd-addr", action="store", dest="confd_addr",
                      help="ConfD IP address (default is {})".format(
                          GnmiConfDApiServerAdapter.confd_addr),
                      default=GnmiConfDApiServerAdapter.confd_addr)
    parser.add_option("--confd-port", action="store", dest="confd_port",
                      help="ConfD port (default is {})".format(
                          GnmiConfDApiServerAdapter.confd_port),
                      default=GnmiConfDApiServerAdapter.confd_port)
    parser.add_option("--monitor-external-changes", action="store_true",
                      dest="monitor_external_changes",
                      help="start external changes service",
                      default=GnmiConfDApiServerAdapter.monitor_external_changes)
    parser.add_option("--external-port", action="store", dest="external_port",
                      help="Port of external changes service (default is {})".format(
                          GnmiConfDApiServerAdapter.external_port),
                      default=GnmiConfDApiServerAdapter.external_port)
    parser.add_option("--cfg", action="store", dest="cfg",
                      help="config file")
    (opt, args) = parser.parse_args()
    common_optparse_process(opt, log)
    adapter_type = AdapterType.DEMO
    if opt.type == "api":
        adapter_type = AdapterType.API
        GnmiConfDApiServerAdapter.set_confd_debug_level(opt.confd_debug)
        GnmiConfDApiServerAdapter.set_confd_addr(opt.confd_addr)
        GnmiConfDApiServerAdapter.set_external_port(int(opt.external_port))
        GnmiConfDApiServerAdapter.set_monitor_external_changes(
            bool(opt.monitor_external_changes))
    # elif opt.type == "netconf":
    #     adapter_type = AdapterType.NETCONF
    elif opt.type == "demo":
        adapter_type = AdapterType.DEMO
        if opt.cfg:
            log.info("processing config file opt.cfg=%s", opt.cfg)
            with open(opt.cfg, "r") as cfg_file:
                cfg = cfg_file.read()
            log.debug("cfg=%s", cfg)
            from confd_gnmi_demo_adapter import GnmiDemoServerAdapter

            GnmiDemoServerAdapter.load_config_string(cfg)
    else:
        log.warning("Unknown server type %s", opt.type)

    (opt, args) = parser.parse_args()
    server = ConfDgNMIServicer.serve(PORT, adapter_type)
    server.wait_for_termination()
