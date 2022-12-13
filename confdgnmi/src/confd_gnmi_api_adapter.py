import logging
import os
import re
import select
import sys
import threading
import json
from enum import Enum
from socket import socket
from typing import List

import _confd
from confd import maapi, maagic
from confd.cdb import cdb

import gnmi_pb2
from confd_gnmi_adapter import GnmiServerAdapter
from confd_gnmi_api_adapter_defaults import ApiAdapterDefaults
from confd_gnmi_common import make_xpath_path, make_gnmi_path, \
    make_formatted_path

log = logging.getLogger('confd_gnmi_api_adapter')
log.setLevel(logging.DEBUG)


INT_VALS = {_confd.C_INT8, _confd.C_INT16, _confd.C_INT32, _confd.C_INT64}
UINT_VALS = {_confd.C_UINT8, _confd.C_UINT16, _confd.C_UINT32, _confd.C_UINT64}


class GnmiConfDApiServerAdapter(GnmiServerAdapter):
    confd_addr: str = ApiAdapterDefaults.CONFD_ADDR
    confd_port: int = ApiAdapterDefaults.CONFD_PORT if ApiAdapterDefaults.CONFD_PORT else _confd.CONFD_PORT
    monitor_external_changes: bool = ApiAdapterDefaults.MONITOR_EXTERNAL_CHANGES
    external_port: int = ApiAdapterDefaults.EXTERNAL_PORT

    def __init__(self):
        self.addr: str = ""
        self.port: int = 0
        self.username: str = ""
        self.password: str = ""
        self.mp_inst = None
        # make sure schemas are loaded
        with maapi.Maapi():
            pass
        nslist = _confd.get_nslist()
        self.module_to_pfx = {nsentry[-1]: nsentry[1] for nsentry in nslist}
        self.ns_to_module = {nsentry[0]: nsentry[-1] for nsentry in nslist}

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
    def set_confd_addr(addr):
        GnmiConfDApiServerAdapter.confd_addr = addr

    @staticmethod
    def set_confd_port(port):
        if port is None:
            port = _confd.CONFD_PORT
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

        def get_monitored_changes(self) -> List:
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
            pathstr = make_xpath_path(path, prefix)
            update.extend(self.adapter.get_updates_with_maapi_save(pathstr,
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

        def _append_changes(self, change_tuple):
            """
            :param change_tuple: 3 elem tuple (o, xpath, val)
            :return:
            """
            log.debug("==> change_tuple=%s", change_tuple)
            with self.change_db_lock:
                for c in change_tuple:
                    assert c[0] == self.ChangeOp.MODIFIED or \
                           c[0] == self.ChangeOp.MODIFIED.value
                    self.change_db.append((c[1], c[2]))
            log.debug("<==")

        def process_subscription(self, sub_sock, sub_point):
            log.debug("==>")

            def cdb_iter(kp, op, oldv, newv, state):
                log.debug("==> kp=%s, op=%r, oldv=%s, newv=%s, state=%r", kp,
                          op, oldv, newv, state)
                if op == _confd.MOP_CREATED:
                    log.debug("_confd.MOP_CREATED")
                    # TODO CREATE not handled for now
                if op == _confd.MOP_VALUE_SET:
                    log.debug("_confd.MOP_VALUE_SET")
                    self._append_changes([(self.ChangeOp.MODIFIED,
                                           self.kp_to_xpath(kp),
                                           str(newv))])
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

            cdb.diff_iterate(sub_sock, sub_point, cdb_iter, 0, None)
            self.put_event(self.SubscriptionEvent.SEND_CHANGES)
            log.debug("self.change_db=%s", self.change_db)
            log.debug("<==")

        def process_external_change(self, ext_sock):
            log.info("==>")
            connection, client_address = ext_sock.accept()
            with connection:
                # TODO make const
                msg = connection.recv(1024)
                log.debug("msg=%s", msg)
                # simple protocol (just for illustration, real implementation
                # should be more robust as not everything may come at once)
                # the msg string should contain N strings separated by \n
                # op1\nxpath1\nval1\nop2\nxpath2\nval2 .....
                # op1 .. first operation1, xpath1 .... first xpath, ...
                # op is string used in ChangeOp Enum class
                # currently operation can be only "modified"
                # the size must be smaller then size in recv
                data = msg.decode().split('\n')
                assert len(data) % 3 == 0
                chunks = ((data[x], data[x+1], data[x+2]) for x in range(0, len(data), 3))
                self._append_changes(chunks)
                self.put_event(self.SubscriptionEvent.SEND_CHANGES)
                log.debug("data=%s", data)
            log.info("<==")

        def subscribe_monitored_paths_cdb(self, sub_sock):
            """
            Subscribe to monitored paths
            :param sub_sock:
            :return: True, if some path is not in CDB
            """
            log.debug("==> sub_sock=%s", sub_sock)
            prio = 10
            subscribed = has_non_cdb = False
            # make subscription for all self.monitored_paths in CDB
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
                    subscribed = True
                    cdb.subscribe2(sub_sock, cdb.SUB_RUNNING, 0, prio, 0, p)
                    log.debug("subscribing operational p=%s", p)
                    cdb.subscribe2(sub_sock, cdb.SUB_OPERATIONAL, 0, prio, 0, p)
                else:
                    has_non_cdb = True
            if subscribed:
                cdb.subscribe_done(sub_sock)
            log.debug("<== has_non_cdb=%s", has_non_cdb)
            return has_non_cdb

        def start_external_change_server(self):
            """
            Start external change server
            :return: socket to listen for changes
            """
            log.debug("==>")
            log.info("Starting external change server!")
            ext_server_sock = socket()
            # TODO port (host) as const or command line option
            ext_server_sock.bind(("localhost",
                                  GnmiConfDApiServerAdapter.external_port))
            ext_server_sock.listen(5)
            log.debug("<== ext_server_sock=%s", ext_server_sock)
            return ext_server_sock

        def socket_loop(self, sub_sock, ext_server_sock=None):
            log.debug("==> sub_sock=%s ext_server_sock=%s", sub_sock,
                      ext_server_sock)
            rlist = [sub_sock, self.stop_pipe[0]]
            if ext_server_sock is not None:
                rlist.append(ext_server_sock)
            wlist = elist = []
            while True:
                log.debug("rlist=%s", rlist)
                r, w, e = select.select(rlist, wlist, elist)
                log.debug("r=%s", r)
                if ext_server_sock is not None and ext_server_sock in r:
                    self.process_external_change(ext_server_sock)
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
                if self.stop_pipe[0] in r:
                    v = os.read(self.stop_pipe[0], 1)
                    assert v == b'x'
                    log.debug("Stopping ConfD loop")
                    break
            log.debug("<==")

        def process_changes(self, external_changes=False):
            log.debug("==> external_changes=%s", external_changes)
            with socket() as sub_sock:
                cdb.connect(sub_sock, cdb.SUBSCRIPTION_SOCKET, '127.0.0.1',
                            _confd.CONFD_PORT)
                has_non_cdb = self.subscribe_monitored_paths_cdb(sub_sock)
                log.debug("subscribe_done")
                assert self.stop_pipe is not None
                try:
                    if external_changes and has_non_cdb:
                        ext_server_sock = self.start_external_change_server()
                        with ext_server_sock:
                            self.socket_loop(sub_sock, ext_server_sock)
                    else:
                        self.socket_loop(sub_sock)
                except Exception as e:
                    log.exception(e)
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
        log.info("==>")
        context = "netconf"
        groups = [self.username]
        try:
            with maapi.single_read_trans(self.username, context, groups,
                                         src_ip=self.addr) as t:
                root = maagic.get_root(t)
                values = []
                count = 0
                # format
                # http://tail-f.com/ns/confd-progress?module=tailf-confd-progress&revision=2020-06-29
                for module in root.modules_state.module:
                    log.debug("val=%s", module.name)
                    name = f'{module.namespace}:{module.name}'
                    values.append((module.namespace, name, "", module.revision))
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

    def make_gnmi_keypath_elems(self, csnode, keypath):
        i = len(keypath) - 1
        ns = 0

        def csnode_list():
            node = csnode
            while node is not None:
                yield node
                node = node.parent()

        for node in reversed(list(csnode_list())):
            assert i >= 0
            keys = {}
            name = _confd.hash2str(keypath[i].tag)
            if keypath[i].ns != ns:
                ns = keypath[i].ns
                name = f'{self.ns_to_module[ns]}:{name}'
            i -= 1
            if node.info().flags() & _confd.CS_NODE_IS_LIST != 0:
                assert i >= 0 and isinstance(keypath[i], tuple)
                keys = {_confd.hash2str(key): str(val)
                        for (key, val) in zip(node.info().keys(), keypath[i])}
                i -= 1
            yield gnmi_pb2.PathElem(name=name, key=keys)

    def make_gnmi_keypath(self, csnode, keypath):
        return gnmi_pb2.Path(elem=list(self.make_gnmi_keypath_elems(csnode, keypath)))

    def get_updates(self, trans, path_str, save_flags):
        log.debug("==> path_str=%s", path_str)
        csnode = _confd.cs_node_cd(None, path_str)
        if csnode is None:
            log.warning('failed to find the cs-node')
            # TODO: raise the right exception
            return []
        updates = []

        def add_update_json(keypath, _value):
            save_id = trans.save_config(save_flags, _confd.pp_kpath(keypath))
            with socket() as save_sock:
                _confd.stream_connect(sock=save_sock, id=save_id, flags=0,
                                      ip=self.addr, port=self.port)
                max_msg_size = 1024
                save_str = b''.join(iter(lambda: save_sock.recv(max_msg_size), b''))
                saved_data = json.loads(save_str)
                log.debug("data=%s", saved_data)
                save_result = trans.maapi.save_config_result(save_id)
                log.debug("save_result=%s", save_result)
                assert save_result == 0
                gnmi_path = self.make_gnmi_keypath(csnode, keypath)
                # the format of saved_data is {"container": {data}}
                # we need only the data part
                assert len(saved_data) == 1
                [data] = saved_data.values()
                gnmi_value = gnmi_pb2.TypedValue(json_ietf_val=json.dumps(data).encode())
                updates.append(gnmi_pb2.Update(path=gnmi_path, val=gnmi_value))

        def add_update_value(keypath, value):
            gnmi_path = self.make_gnmi_keypath(csnode, keypath)
            if value.confd_type() in INT_VALS:
                gnmi_value = gnmi_pb2.TypedValue(int_val=int(value))
            elif value.confd_type() in UINT_VALS:
                gnmi_value = gnmi_pb2.TypedValue(uint_val=int(value))
            elif value.confd_type == _confd.C_BOOL:
                gnmi_value = gnmi_pb2.TypedValue(bool_val=bool(value))
            elif value.confd_type == _confd.C_DOUBLE:
                gnmi_value = gnmi_pb2.TypedValue(float_val=float(value))
            # possibly others?
            else:
                gnmi_value = gnmi_pb2.TypedValue(string_val=str(value))
            updates.append(gnmi_pb2.Update(path=gnmi_path, val=gnmi_value))

        container_flags = (_confd.CS_NODE_IS_LIST | _confd.CS_NODE_IS_CONTAINER)
        is_container = csnode.info().flags() & container_flags != 0
        add_update = add_update_json if is_container else add_update_value
        trans.xpath_eval(path_str, add_update, None, '/')
        log.debug("<== save_str=%s", updates)
        return updates

    def get_updates_with_maapi_save(self, path, data_type):
        log.debug("==> path=%s data_type=%s", path, data_type)

        def module_to_prefix(match):
            name = match.groups()[0]
            return self.module_to_pfx.get(name, name) + ':'
        pfx_path = re.sub(r'([^/:]+):', module_to_prefix, path)
        save_flags = _confd.maapi.CONFIG_JSON | _confd.maapi.CONFIG_NO_PARENTS

        if data_type == gnmi_pb2.GetRequest.DataType.ALL:
            save_flags |= _confd.maapi.CONFIG_WITH_OPER
        elif data_type == gnmi_pb2.GetRequest.DataType.CONFIG:
            pass
        elif data_type == gnmi_pb2.GetRequest.DataType.STATE:
            save_flags |= _confd.maapi.CONFIG_OPER_ONLY
        elif data_type == gnmi_pb2.GetRequest.DataType.OPERATIONAL:
            save_flags |= _confd.maapi.CONFIG_OPER_ONLY

        context = "netconf"
        groups = [self.username]
        updates = []
        try:
            with maapi.single_read_trans(self.username, context, groups,
                                         src_ip=self.addr) as t:
                updates = self.get_updates(t, pfx_path, save_flags)
        except Exception as e:
            log.exception(e)

        log.debug("<== up=%s", updates)
        return updates

    def get(self, prefix, paths, data_type, use_models):
        log.info("==> prefix=%s, paths=%s, data_type=%s, use_models=%s",
                 prefix, paths, data_type, use_models)
        notifications = []
        update = []
        for path in paths:
            update.extend(
                self.get_updates_with_maapi_save(make_xpath_path(path, prefix), data_type))
        notif = gnmi_pb2.Notification(timestamp=1, prefix=prefix,
                                      update=update,
                                      delete=[],
                                      atomic=True)
        notifications.append(notif)
        log.info("<== notifications=%s", notifications)
        return notifications

    def set(self, prefix, path, val):
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
