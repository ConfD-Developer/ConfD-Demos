#!/usr/bin/env python3
import logging
import os
import select
import socket
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from random import randint
from time import sleep

import _confd
from _confd import dp, maapi

# Set log level and port to send gNMI Adapter external changes
# TODO command line options
EXTERNAL_PORT: int = 5055
LOG_LEVEL = logging.INFO
RUN_FOR_TIME: int = 1000

logging.basicConfig(
    format="%(asctime)s:%(relativeCreated)s "
           "%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s  %(message)s",
    level=LOG_LEVEL)
log = logging.getLogger("route_status")


@dataclass
class Route:
    id: str
    leaf1: int
    leaf2: int
    leaf3: int
    leaf4: int


class RouteData:

    def __init__(self, num=None, random=True):
        log.info("==> num=%s", num)
        self.routes = {}
        if num is not None:
            self.fill_routes(num, random)
        log.info("<==")

    def fill_routes(self, num, random=False):
        log.info("==> num=%s", num)
        for i in range(1, num):
            rtid = "rt" + str(i)
            if random:
                rtid = str(randint(1, 100)) + rtid
            rt = Route(id=rtid, leaf1=i * 2, leaf2=i * 3, leaf3=i * 4,
                       leaf4=i * 5)
            self.routes[rt.id] = rt
        log.debug("self.routes=%s", self.routes)
        log.info("==>")


class TransCbs(object):

    def __init__(self, workersocket):
        self._workersocket = workersocket

    def cb_init(self, tctx):
        dp.trans_set_fd(tctx, self._workersocket)
        return _confd.CONFD_OK

    def cb_finish(self, tctx):
        return _confd.CONFD_OK


class DataCbs(object):

    def __init__(self, route_data: RouteData):
        self.route_provider: RouteData = route_data
        pass

    def cb_get_elem(self, tctx, kp):
        log.info("==> kp=%s", kp)
        assert len(self.route_provider.routes)
        elem = str(kp[0])
        key = str(kp[1][0])
        route = self.route_provider.routes[key]
        log.debug("elem=%s key=%s route=%s", elem, key, route)
        val = None
        if elem == "leaf1":
            val = _confd.Value(route.leaf1)
        elif elem == "leaf2":
            val = _confd.Value(route.leaf2)
        elif elem == "leaf3":
            val = _confd.Value(route.leaf3)
        elif elem == "leaf4":
            val = _confd.Value(route.leaf4)
        if val is not None:
            dp.data_reply_value(tctx, val)
        else:
            dp.data_reply_not_found(tctx)

        log.info("<==")
        return _confd.CONFD_OK

    def cb_get_next(self, tctx, kp, next_idx):
        log.info("==> kp=%s next=%i", kp, next_idx)
        assert len(self.route_provider.routes)
        if next_idx == -1:
            next_idx = 0
        if next_idx >= len(self.route_provider.routes):
            dp.data_reply_next_key(tctx, None, 0)
        else:
            log.debug("searching key")
            # since python 3.6 dict should preserve order
            key = list(self.route_provider.routes)[next_idx]
            log.debug("key=%s", key)
            val = _confd.Value(self.route_provider.routes[key].id)
            dp.data_reply_next_key(tctx, [val], next_idx + 1)
        log.info("<==")
        return _confd.CONFD_OK


class RouteProvider:
    DEFAULT_CONFD_ADDR = '127.0.0.1'
    ctx = maapisock = ctlsock = wrksock = None
    stop_pipe = None

    @staticmethod
    def init_dp(route_data: RouteData,
                confd_ip=None,
                confd_port=_confd.CONFD_PORT,
                confd_debug_level=_confd.DEBUG):
        log.info("==>")
        if confd_ip is None:
            confd_ip = RouteProvider.DEFAULT_CONFD_ADDR
        _confd.set_debug(confd_debug_level, sys.stderr)

        RouteProvider.ctx = dp.init_daemon("route_dp_daemon")
        RouteProvider.maapisock = socket.socket()
        RouteProvider.ctlsock = socket.socket()
        RouteProvider.wrksock = socket.socket()

        maapi.connect(RouteProvider.maapisock, confd_ip, confd_port)
        dp.connect(RouteProvider.ctx, RouteProvider.ctlsock, dp.CONTROL_SOCKET,
                   confd_ip, confd_port)
        dp.connect(RouteProvider.ctx, RouteProvider.wrksock, dp.WORKER_SOCKET,
                   confd_ip, confd_port)
        maapi.load_schemas(RouteProvider.maapisock)

        tcb = TransCbs(RouteProvider.wrksock)
        dp.register_trans_cb(RouteProvider.ctx, tcb)
        dcb = DataCbs(route_data)
        # we are not using route_status_ns.ns.callpoint_routestat so we do not
        # need to generate route-status.yang python binding
        dp.register_data_cb(RouteProvider.ctx, "routestat", dcb)
        dp.register_done(RouteProvider.ctx)

        log.info("<==")

    @staticmethod
    def close_dp():
        RouteProvider.maapisock.close()
        RouteProvider.ctlsock.close()
        RouteProvider.wrksock.close()
        os.close(RouteProvider.stop_pipe[0])
        os.close(RouteProvider.stop_pipe[1])

    @staticmethod
    def confd_loop():
        log.info("==>")
        RouteProvider.stop_pipe = os.pipe()
        rlist = [RouteProvider.ctlsock, RouteProvider.wrksock,
                 RouteProvider.stop_pipe[0]]
        wlist = elist = []
        while True:
            r, w, e = select.select(rlist, wlist, elist)
            try:
                if RouteProvider.ctlsock in r:
                    dp.fd_ready(RouteProvider.ctx, RouteProvider.ctlsock)
                elif RouteProvider.wrksock in r:
                    dp.fd_ready(RouteProvider.ctx, RouteProvider.wrksock)
                elif RouteProvider.stop_pipe[0] in r:
                    v = os.read(RouteProvider.stop_pipe[0], 1)
                    assert v == b'x'
                    log.debug("Stopping ConfD loop")
                    break
            except _confd.error.Error as e:
                if e.confd_errno is not _confd.ERR_EXTERNAL:
                    raise e
        log.info("<==")

    @staticmethod
    def stop_confd_loop():
        log.info("==>")
        os.write(RouteProvider.stop_pipe[1], b'x')
        log.info("<==")


class ChangeOp(Enum):
    MODIFIED = "mod"


def generate_changes(stop_fun, route_data: RouteData, sleep_val=2):
    log.info("==>")
    assert len(route_data.routes)

    while True:
        sleep(sleep_val)
        changed_keys = set()
        msgs = []
        # make up to 3 changes
        for c in range(randint(1, 3)):
            n = randint(0, len(route_data.routes) - 1)
            log.debug("changed_keys=%s", changed_keys)
            key = list(route_data.routes)[n]
            if key in changed_keys:
                continue
            changed_keys.add(key)
            val = randint(1, 10)
            log.debug("changing route leaf1 key=%s val=%i", key, val)
            route_data.routes[key].leaf1 = val
            op = ChangeOp.MODIFIED.value
            xpath = "/route-status[route={}]/leaf1".format(key)
            val_str = "{}".format(val)
            msg = "{}\n{}\n{}".format(op, xpath, val_str)
            msgs.append(msg)
        log.debug("msgs=%s", msgs)
        with socket.socket() as s:
            try:
                s.connect(("localhost", EXTERNAL_PORT))
                log.info("Connected to the change server")
                msg = ""
                for m in msgs:
                    # log.debug("m=%s", m)
                    msg += m + '\n'
                # remove last \n
                msg = msg[:-1]
                log.info("msg=%s", msg)
                s.sendall(msg.encode("utf-8"))
            except Exception:
                log.info("Cannot connect to the change server!")
        if stop_fun():
            break

    log.info("<==")


def main():
    log.info("==>")
    route_data = RouteData(num=10)
    assert len(route_data.routes)
    RouteProvider.init_dp(route_data)
    confd_thread = change_thread = None
    stop_thread = False
    try:
        change_thread = threading.Thread(target=generate_changes,
                                         args=(lambda: stop_thread,
                                               route_data))
        log.debug("** starting change_thread")
        change_thread.start()
        confd_thread = threading.Thread(target=RouteProvider.confd_loop)
        confd_thread.start()
        # stop end and after specific time (adjust as you need)
        sleep(RUN_FOR_TIME)
    except KeyboardInterrupt:
        log.info(" **** Ctrl-C pressed ***")
    except Exception:
        log.exception("Error during processing!")
    finally:
        log.debug("Closing")
        stop_thread = True
        if change_thread is not None:
            change_thread.join()
        if confd_thread is not None:
            RouteProvider.stop_confd_loop()
            confd_thread.join()
        RouteProvider.close_dp()

    log.info("<==")


if __name__ == "__main__":
    main()
