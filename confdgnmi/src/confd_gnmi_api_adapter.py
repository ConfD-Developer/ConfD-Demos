import sys
import xml.etree.ElementTree as ET
from socket import socket

import _confd
# TODO replace maapi_low with high level MAAPI
from _confd import maapi as maapi_low
from confd import maapi, maagic

from confd_gnmi_adapter import GnmiServerAdapter
from confd_gnmi_common import *

log = logging.getLogger('confd_gnmi_api_adapter')
log.setLevel(logging.DEBUG)


class GnmiConfDApiServerAdapter(GnmiServerAdapter):
    confd_addr: str = '127.0.0.1'
    confd_port: int = _confd.CONFD_PORT

    def __init__(self):
        self.addr: str = ""
        self.port: int = 0
        self.username: str = ""
        self.password: str = ""
        self.maapisock = None
        self.mp_inst = None

    # call only once!
    @staticmethod
    def set_confd_debug_level(level):
        if level == "debug":
            confd_debug_level = _confd.DEBUG
        elif level == "trace":
            confd_debug_level = _confd.TRACE
        elif level == "proto":
            confd_debug_level = _confd.PROTO_TRACE
        elif level == "silent":
            confd_debug_level = _confd.SILENT
        else:
            confd_debug_level = _confd.TRACE
            log.warning("Unknown confd debug level %s", level)
        _confd.set_debug(confd_debug_level, sys.stderr)

    @staticmethod
    def set_confd_addr(confd_addr):
        GnmiConfDApiServerAdapter.confd_addr = confd_addr

    @staticmethod
    def set_confd_port(confd_port):
        GnmiConfDApiServerAdapter.confd_port = confd_port

    @classmethod
    def get_inst(cls) -> GnmiServerAdapter:
        """
        This is classmethod on purpose, see GnmiDemoServerAdapter
        """
        return GnmiConfDApiServerAdapter()

    class SubscriptionHandler(GnmiServerAdapter.SubscriptionHandler):

        def make_subscription_response(self) -> gnmi_pb2.SubscribeResponse:
            log.debug("==>")
            assert self.subscription_list != None
            # for now we only process GET type (fetch and return everything)
            assert self.subscription_stream_event_type == self.SubscriptionStreamEventType.GET

            update = []
            for s in self.subscription_list.subscription:
                update.extend(self.adapter.get_updates_with_maapi_save(s.path,
                                                                       self.subscription_list.prefix,
                                                                       gnmi_pb2.GetRequest.DataType.ALL))
            # TODO delete
            delete = []
            notif = gnmi_pb2.Notification(timestamp=0,
                                          prefix=self.subscription_list.prefix,
                                          alias="/alias", update=update,
                                          delete=delete,
                                          atomic=False)

            response = gnmi_pb2.SubscribeResponse(update=notif)
            log.debug("<== response=%s", response)
            return response

    def get_subscription_handler(self) -> SubscriptionHandler:
        log.debug("==>")
        handler = self.SubscriptionHandler(self)
        log.debug("<== handler=%s", handler)
        return handler

    def connect(self, addr=None, port=None, username="admin", password="admin"):
        if addr is None:
            addr = GnmiConfDApiServerAdapter.confd_addr
        if port is None:
            port = GnmiConfDApiServerAdapter.confd_port

        log.info("==> addr=%s port=%i username=%s password=:-)", addr, port,
                 username)
        self.addr = addr
        self.port = port
        # TODO we are connecting low level maapi always, even though we  use
        # high level maapi only in some cases
        # TODO parallel processing
        self.username = username
        self.password = password
        self.maapisock = socket()
        maapi_low.connect(sock=self.maapisock, ip=self.addr, port=self.port)
        maapi_low.load_schemas(self.maapisock)
        log.info(
            "<==  self.addr=%s self.port=%i self.username=%s self.password=:-)",
            self.addr, self.port, self.username)

    def disconnect(self):
        log.info("==>")
        self.maapisock.close()
        log.info("<==")

    # https://tools.ietf.org/html/rfc6022#page-8
    # TODO pass username from request context
    def get_netconf_capabilities(self):
        log.info("==>")
        context = "maapi"
        groups = [self.username]
        try:
            with maapi.single_read_trans(self.username, context, groups,
                                         src_ip=self.addr) as t:
                root = maagic.get_root(t)
                values = []
                count = 0
                # format
                # http://tail-f.com/ns/confd-progress?module=tailf-confd-progress&revision=2020-06-29
                for val in root.netconf_state.capabilities.capability:
                    log.debug("val=%s", val)
                    if "module=" in val:
                        el = val.split("?")
                        if len(el) > 1:
                            cap = el[1].split("&")
                            name = cap[0]
                            ver = ''
                            if len(cap) > 1:
                                ver = cap[1]
                            values.append(
                                (el[0], name.replace("module=", ""), "",
                                 ver.replace("revision=", "")))
                    count += 1
                    log.debug("Value element count=%d" % count)
            log.debug("values=%s", values)
        except Exception as e:
            log.exception(e)

        log.info("<==")
        return values

    def capabilities(self):
        log.info("==>")
        ns_list = self.get_netconf_capabilities()
        log.debug("ns_list=%s", ns_list)
        models = []
        for ns in ns_list:
            models.append(GnmiServerAdapter.CapabilityModel(name=ns[1],
                                                            organization="",
                                                            version=ns[3]))

        log.info("<== models=%s", models)
        return models

    def get_maapi_save_string(self, path_str, save_flags):
        log.debug("==> path_str=%s", path_str)
        save_str = ""
        context = "maapi"
        groups = [self.username]
        try:
            with maapi.single_read_trans(self.username, context, groups,
                                         src_ip=self.addr) as t:
                save_id = t.save_config(save_flags, path_str)
                save_sock = socket()
                _confd.stream_connect(sock=save_sock, id=save_id, flags=0,
                                      ip=self.addr, port=self.port)

                # based on
                # https://stackoverflow.com/questions/17667903/python-socket-receive-large-amount-of-data
                fragments = []
                max_msg_size = 1024
                while True:
                    chunk = save_sock.recv(max_msg_size)
                    if not chunk:
                        break
                    fragments.append(chunk)
                save_str = b''.join(fragments)
                log.debug("save_str=%s", save_str)
                save_result = t.maapi.save_config_result(save_id)
                log.debug("save_result=%s", save_result)
                assert save_result == 0
                save_sock.close()
        except Exception as e:
            log.exception(e)

        log.debug("<== save_str=%s", save_str)
        return save_str

    def get_xml_paths(self, elem, orig_path_str, parent_path_cand=""):
        log.debug("==> elem=%s", elem)
        path_vals = []
        # skip top level 'config' element
        if not (parent_path_cand == "" and
                elem.tag == "{http://tail-f.com/ns/config/1.0}config"):
            parent_path_cand += "/" + elem.tag.split("}")[-1]
        if len(elem) > 0:
            # we (simplification) assume that if there are more sibling elements,
            # this is list and first element is key, this should be fixed with
            # help of `cs_nodes`
            # in this way we can detect some (non list) paths incorrectly, we try to fix
            # by comparing original path
            if len(elem) > 1:
                if elem[0].text != None:
                    parent_path_cand2 = parent_path_cand + "[{}={}]".format(
                        elem[0].tag.split("}")[-1],
                        elem[0].text)
                    if parent_path_cand2.startswith(
                            orig_path_str) or orig_path_str.startswith(
                            parent_path_cand2):
                        parent_path_cand = parent_path_cand2

            for e in elem:
                path_vals.extend(self.get_xml_paths(e, orig_path_str,
                                                    parent_path_cand))
        else:
            # check if this is path for exact key
            keypath_cand = None
            if elem.text != None:
                val = elem.text.split(":")[-1]
                path_list = parent_path_cand.split('/')
                if len(path_list) >= 2:
                    keypath_cand = "/".join(path_list[:-1]) + "[{}={}]".format(
                        path_list[-1], val) + "/" + path_list[-1]
                if keypath_cand != None and orig_path_str == keypath_cand:
                    path = keypath_cand
                    parent_path_cand = path
                else:
                    path = parent_path_cand
                # if path != orig_path_str:
                #     path += "/" + elem.tag.split("}")[-1]
                # we also need to check possibility this is exact key leaf
                # skip not correctly detected paths
                if path.startswith(parent_path_cand):
                    path_vals.append((path, val))
        log.debug("<== paths=%s", path_vals)
        return path_vals

    def get_updates_with_maapi_save(self, path, prefix, data_type):
        log.debug("==> path=%s prefix=%s data_type=%s", path, prefix, data_type)
        path_str = make_xpath_path(path, prefix, quote_val=False)
        # we need ariant with quoted values for maapi_save
        path_str_quote = make_xpath_path(path, prefix, quote_val=True)
        prefix_str = make_xpath_path(gnmi_prefix=prefix)
        log.debug("path_str=%s", path_str)
        save_flags = _confd.maapi.CONFIG_XML | _confd.maapi.CONFIG_XPATH

        if data_type == gnmi_pb2.GetRequest.DataType.ALL:
            save_flags |= _confd.maapi.CONFIG_WITH_OPER
        elif data_type == gnmi_pb2.GetRequest.DataType.CONFIG:
            pass
        elif data_type == gnmi_pb2.GetRequest.DataType.STATE:
            save_flags |= _confd.maapi.CONFIG_OPER_ONLY
        elif data_type == gnmi_pb2.GetRequest.DataType.OPERATIONAL:
            save_flags |= _confd.maapi.CONFIG_OPER_ONLY

        save_xml = self.get_maapi_save_string(path_str_quote, save_flags)
        root = ET.fromstring(save_xml)
        xml_paths = self.get_xml_paths(root, path_str)
        up = []
        for pv in xml_paths:
            # skip incorrecly detected paths
            if pv[0].startswith(path_str):
                p = pv[0][len(prefix_str):]
                up.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                          val=gnmi_pb2.TypedValue(
                                              string_val=pv[1])))
        log.debug("<== up=%s", up)
        return up

    def get(self, prefix, paths, data_type, use_models):
        log.info("==> prefix=%s, paths=%s, data_type=%s, use_models=%s",
                 prefix, paths, data_type, use_models);
        notifications = []
        update = []
        for path in paths:
            update.extend(self.get_updates_with_maapi_save(path, prefix, data_type))
        notif = gnmi_pb2.Notification(timestamp=1, prefix=prefix,
                                      update=update,
                                      delete=[],
                                      atomic=True)
        notifications.append(notif)
        log.info("<== notifications=%s", notifications)
        return notifications

    def set(self, prefix, path, val):
        log.info("==> prefix=%s, path=%s, val=%s",
                 prefix, path, val);
        path_str = make_formatted_path(path, prefix)
        op = gnmi_pb2.UpdateResult.INVALID
        context = "maapi"
        groups = [self.username]
        if hasattr(val, "string_val"):
            str_val = val.string_val
        else:
            # TODO
            str_val = "{}".format(val)

        with maapi.single_write_trans(self.username, context, groups,
                                      src_ip=self.addr) as t:
            t.set_elem(str_val, path_str)
            t.apply()
            op = gnmi_pb2.UpdateResult.UPDATE

        log.info("==> op=%s", op)
        return op
