import logging
import os
import select
import sys
import threading
import xml.etree.ElementTree as ET
from enum import Enum
from socket import socket

import gnmi_pb2
from confd_gnmi_adapter import GnmiServerAdapter
from confd_gnmi_common import make_xpath_path, make_gnmi_path, \
    make_formatted_path

log = logging.getLogger('confd_gnmi_api_adapter')
log.setLevel(logging.DEBUG)


class GnmiConfDApiServerAdapter(GnmiServerAdapter):
    import _confd
    confd_addr: str = '127.0.0.1'
    confd_port: int = _confd.CONFD_PORT
    monitor_external_changes: bool = False
    external_port: int = 5055

    def __init__(self):
        self.addr: str = ""
        self.port: int = 0
        self.username: str = ""
        self.password: str = ""
        self.mp_inst = None

    # call only once!
    @staticmethod
    def set_confd_debug_level(level):
        import _confd
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
    def set_confd_addr(addr):
        GnmiConfDApiServerAdapter.confd_addr = addr

    @staticmethod
    def set_confd_port(port):
        GnmiConfDApiServerAdapter.confd_port = port

    @staticmethod
    def set_external_port(port):
        GnmiConfDApiServerAdapter.external_port = port

    @staticmethod
    def set_monitor_external_changes(val=True):
        GnmiConfDApiServerAdapter.monitor_external_changes = val

    @classmethod
    def get_adapter(cls) -> GnmiServerAdapter:
        """
        This is classmethod on purpose, see GnmiDemoServerAdapter
        """
        return GnmiConfDApiServerAdapter()

    class SubscriptionHandler(GnmiServerAdapter.SubscriptionHandler):

        def __init__(self, adapter, subscription_list):
            super().__init__(adapter, subscription_list)
            # TODO reuse with demo adapter?
            self.monitored_paths = []
            self.change_db = []
            self.change_db_lock = threading.Lock()
            self.change_thread = None
            self.stop_pipe = None

        def get_monitored_changes(self) -> []:
            # TODO reuse with demo adapter ?
            with self.change_db_lock:
                log.debug("==> self.change_db=%s", self.change_db)
                assert len(self.change_db) > 0
                update = []
                for c in self.change_db:
                    prefix_str = make_xpath_path(
                        gnmi_prefix=self.subscription_list.prefix)
                    p = c[0]
                    if c[0].startswith(prefix_str):
                        p = c[0][len(prefix_str):]
                    update.append(gnmi_pb2.Update(path=make_gnmi_path(p),
                                                  val=gnmi_pb2.TypedValue(
                                                      string_val=c[1])))
                self.change_db = []
            log.debug("<== update=%s", update)
            return update

        def get_sample(self, path, prefix,
                       start_change_processing=False):
            update = []
            log.debug("==>")
            update.extend(self.adapter.get_updates_with_maapi_save(path,
                                                                   prefix,
                                                                   gnmi_pb2.GetRequest.DataType.ALL))
            log.debug("<== update=%s", update)
            return update

        def add_path_for_monitoring(self, path, prefix):
            log.debug("==>")
            path_with_prefix_str = make_formatted_path(path, prefix)
            self.monitored_paths.append(path_with_prefix_str)
            log.debug("<==")

        @staticmethod
        def kp_to_xpath(kp):
            import _confd
            log.debug("==> kp=%s", kp)
            xpath = _confd.xpath_pp_kpath(kp)
            xpath = xpath.replace('"', '')
            # for now, remove possible prefix
            # (TODO for now handled only prefix in first elem)
            starts_slash = xpath.startswith('/')
            xplist = xpath.split(':', 1)
            if len(xplist) == 2:
                xpath = xplist[1]
                if starts_slash:
                    xpath = '/' + xpath
            log.debug("<== xpath=%s", xpath)
            return xpath

        class ChangeOp(Enum):
            MODIFIED = "mod"

        def _append_changes(self, change_list):
            log.debug("==> change_list=%s", change_list)
            with self.change_db_lock:
                for c in change_list:
                    assert c[0] == self.ChangeOp.MODIFIED or \
                           c[0] == self.ChangeOp.MODIFIED.value
                    self.change_db.append((c[1], c[2]))
            log.debug("<==")

        def process_subscription(self, sub_sock, sub_point):
            log.debug("==>")

            def cdb_iter(kp, op, oldv, newv, state):
                import _confd
                log.debug("==> kp=%s, op=%r, oldv=%s, newv=%s, state=%r", kp,
                          op, oldv, newv, state)
                if op == _confd.MOP_CREATED:
                    log.debug("_confd.MOP_CREATED")
                    # TODO CREATE not handled for now
                if op == _confd.MOP_VALUE_SET:
                    log.debug("_confd.MOP_VALUE_SET")
                    self._append_changes([[self.ChangeOp.MODIFIED,
                                           self.kp_to_xpath(kp),
                                           str(newv)]])
                    # TODO MOP_VALUE_SET implement
                elif op == _confd.MOP_DELETED:
                    log.debug("_confd.MOP_DELETED")
                    # TODO DELETE not handled for now
                elif op == _confd.MOP_MODIFIED:
                    log.debug("_confd.MOP_MODIFIED")
                    # TODO MODIFIED not handled for now
                else:
                    log.warning(
                        "Operation op=%d is not expected, kp=%s. Skipping!",
                        op, kp)
                return _confd.ITER_RECURSE

            from confd.cdb import cdb
            cdb.diff_iterate(sub_sock, sub_point, cdb_iter, 0, None)
            self.put_event(self.SubscriptionEvent.SEND_CHANGES)
            log.debug("self.change_db=%s", self.change_db)
            log.debug("<==")

        def process_external_change(self, ext_sock):
            log.info("==>")
            connection, client_address = ext_sock.accept()
            with connection:
                connection.setblocking(True)
                # TODO make const
                msg = connection.recv(1024)
                log.debug("msg=%s", msg)
                # simple protocol
                # the msg string should contain N strings separated by \n
                # op1\nxpath1\nval1\nop2\nxpath2\nval2 .....
                # op1 .. first operation1, xpath1 .... first xpath, ...
                # op is string used in ChangeOp Enum class
                # currently operation can be only "modified"
                # the size must be smaller then size in recv
                data = msg.decode().split('\n')
                assert len(data) % 3 == 0
                chunks = [data[x:x + 3] for x in range(0, len(data), 3)]
                self._append_changes(chunks)
                self.put_event(self.SubscriptionEvent.SEND_CHANGES)
                log.debug("data=%s", data)
            log.info("<==")

        def process_changes(self, external_changes=False):
            from confd.cdb import cdb
            import _confd
            log.debug("==>")
            # make subscription for all self.monitored_paths
            with socket() as sub_sock:
                prio = 10
                cdb.connect(sub_sock, cdb.SUBSCRIPTION_SOCKET, '127.0.0.1',
                            _confd.CONFD_PORT)
                found_in_cdb = has_non_cdb = False
                for p in self.monitored_paths:
                    log.debug("subscribing config p=%s", p)
                    # TODO hash - breaks generic usage
                    # TODO for now we subscribe path for both, config and oper,
                    # TODO subscribe only for paths that exist
                    # it may be more efficient to find out type of path and subscribe
                    # only for one type
                    cs_node = _confd.cs_node_cd(None, p)
                    is_cdb = cs_node.info().flags() & _confd.CS_NODE_IS_CDB
                    if is_cdb:
                        found_in_cdb = True
                        cdb.subscribe2(sub_sock, cdb.SUB_RUNNING, 0, prio,
                                       0, p)
                        log.debug("subscribing operational p=%s", p)
                        cdb.subscribe2(sub_sock, cdb.SUB_OPERATIONAL, 0, prio,
                                       0, p)
                    else:
                        has_non_cdb = True
                if found_in_cdb:
                    cdb.subscribe_done(sub_sock)
                log.debug("subscribe_done")
                assert self.stop_pipe is not None
                rlist = [sub_sock, self.stop_pipe[0]]
                wlist = elist = []
                try:
                    ext_server_sock = None
                    if external_changes and has_non_cdb:
                        log.info("Starting external change server!")
                        ext_server_sock = socket()
                        ext_server_sock.setblocking(False)
                        # TODO port (host) as const or command line option
                        ext_server_sock.bind(("localhost",
                                              GnmiConfDApiServerAdapter.external_port))
                        ext_server_sock.listen(5)
                        rlist.append(ext_server_sock)
                    while True:
                        log.debug("rlist=%s", rlist)
                        r, w, e = select.select(rlist, wlist, elist)
                        log.debug("r=%s", r)
                        if ext_server_sock is not None and ext_server_sock in r:
                            self.process_external_change(ext_server_sock)
                        if self.stop_pipe[0] in r:
                            v = os.read(self.stop_pipe[0], 1)
                            assert v == b'x'
                            log.debug("Stopping ConfD loop")
                            break
                        if sub_sock in r:
                            try:
                                sub_info = cdb.read_subscription_socket2(
                                    sub_sock)
                                for s in sub_info[2]:
                                    self.process_subscription(sub_sock, s)
                                cdb.sync_subscription_socket(sub_sock,
                                                             cdb.DONE_PRIORITY)
                            except _confd.error.Error as e:
                                # Callback error
                                if e.confd_errno is _confd.ERR_EXTERNAL:
                                    log.exception(e)
                                else:
                                    raise e

                except Exception as e:
                    log.exception(e)
                finally:
                    if ext_server_sock is not None:
                        ext_server_sock.close()

            log.debug("<==")

        def start_monitoring(self):
            log.debug("==>")
            assert self.change_thread is None
            assert self.stop_pipe is None
            log.debug("** creating change_thread")
            self.stop_pipe = os.pipe()
            # TODO external change server always started,
            # make optional by passing False
            self.change_thread = \
                threading.Thread(target=self.process_changes,
                                 args=(
                                     GnmiConfDApiServerAdapter.monitor_external_changes,))
            log.debug("** starting change_thread")
            self.change_thread.start()
            log.debug("** change_thread started")
            log.debug("<==")

        def stop_monitoring(self):
            log.debug("==>")
            # if there is an error during fetch of first subs. sample,
            # we do not start change thread
            if self.change_thread is None:
                log.warning("Cannot stop change thread! Not started?")
            else:
                assert self.stop_pipe is not None
                log.debug("** stopping change_thread")
                # https://stackoverflow.com/a/4661284
                os.write(self.stop_pipe[1], b'x')
                self.change_thread.join()
                log.debug("** change_thread joined")
                self.change_thread = None
                os.close(self.stop_pipe[0])
                os.close(self.stop_pipe[1])
                self.stop_pipe = None
            self.monitored_paths = []
            log.debug("<==")

    def get_subscription_handler(self,
                                 subscription_list) -> SubscriptionHandler:
        log.debug("==>")
        handler = self.SubscriptionHandler(self, subscription_list)
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
        log.info(
            "<==  self.addr=%s self.port=%i self.username=%s self.password=:-)",
            self.addr, self.port, self.username)

    # https://tools.ietf.org/html/rfc6022#page-8
    # TODO pass username from request context
    def get_netconf_capabilities(self):
        from confd import maapi, maagic
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
        import _confd
        from confd import maapi
        log.debug("==> path_str=%s", path_str)
        save_str = ""
        context = "maapi"
        groups = [self.username]
        try:
            with maapi.single_read_trans(self.username, context, groups,
                                         src_ip=self.addr) as t:
                save_id = t.save_config(save_flags, path_str)
                with socket() as save_sock:
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
        except Exception as e:
            log.exception(e)

        log.debug("<== save_str=%s", save_str)
        return save_str

    def get_xml_paths(self, elem, orig_path_str, parent_path_cand=""):
        log.debug("==> elem=%s orig_path_str=%s parent_path_cand=%s", elem,
                  orig_path_str, parent_path_cand)
        path_vals = []
        # skip top level 'config' element
        if not (
                parent_path_cand == "" and elem.tag == "{http://tail-f.com/ns/config/1.0}config"):
            parent_path_cand += "/" + elem.tag.split("}")[-1]
        if len(elem) > 0:
            # we (simplification) assume that if there are more sibling elements,
            # this is list and first element is key, this should be fixed with
            # help of `cs_nodes`
            # in this way we can detect some (non list) paths incorrectly, we try to fix
            # by comparing original path
            if len(elem) > 1:
                if elem[0].text is not None:
                    parent_path_cand2 = parent_path_cand + "[{}={}]".format(
                        elem[0].tag.split("}")[-1], elem[0].text)
                    if parent_path_cand2.startswith(
                            orig_path_str) or \
                            orig_path_str.startswith(parent_path_cand2):
                        parent_path_cand = parent_path_cand2

            for e in elem:
                path_vals.extend(self.get_xml_paths(e, orig_path_str,
                                                    parent_path_cand))
        else:
            # check if this is path for exact key
            keypath_cand = None
            if elem.text is not None:
                val = elem.text.split(":")[-1]
                path_list = parent_path_cand.split('/')
                if len(path_list) >= 2:
                    keypath_cand = "/".join(path_list[:-1]) + "[{}={}]".format(
                        path_list[-1], val) + "/" + path_list[-1]
                if keypath_cand is not None and orig_path_str == keypath_cand:
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
        import _confd
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
                 prefix, paths, data_type, use_models)
        notifications = []
        update = []
        for path in paths:
            update.extend(
                self.get_updates_with_maapi_save(path, prefix, data_type))
        notif = gnmi_pb2.Notification(timestamp=1, prefix=prefix,
                                      update=update,
                                      delete=[],
                                      atomic=True)
        notifications.append(notif)
        log.info("<== notifications=%s", notifications)
        return notifications

    def set(self, prefix, path, val):
        from confd import maapi
        log.info("==> prefix=%s, path=%s, val=%s", prefix, path, val)
        path_str = make_formatted_path(path, prefix)
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
