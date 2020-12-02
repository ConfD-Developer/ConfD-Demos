#!/usr/bin/env python
import ncs as ncs
import _ncs
from ncs.dp import Action, Daemon
from ncs.maapi import Maapi
from ncs.log import Log

import socket
import sys
import signal
from lxml import etree
import time

class MyLog(object):
    def info(self, arg):
        print("info: %s" % arg)
    def error(self, arg):
        print("error: %s" % arg)


class WaitForPending(Action):
    def recv_all_and_close(self, c_sock, c_id):
        data = ''
        while True:
            buf = c_sock.recv(4096)
            if buf:
                data += buf.decode('utf-8')
            else:
                c_sock.close()
                return data


    def read_config(self, trans, path):
        dev_flags= (_ncs.maapi.CONFIG_XML_PRETTY+
                    _ncs.maapi.CONFIG_WITH_OPER+
                    _ncs.maapi.CONFIG_UNHIDE_ALL)
        c_id = trans.save_config(dev_flags, path)
        c_sock = socket.socket()
        _ncs.stream_connect(c_sock, c_id, 0, '127.0.0.1', _ncs.PORT)
        data = self.recv_all_and_close(c_sock, c_id);
        return data


    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        while True:
            with ncs.maapi.single_read_trans('admin', 'admin') as t:
                save_data = self.read_config(t, "/netconf-ned-builder/project{router 1.0}/module/status")
                xml_str = str(save_data)
                if xml_str.find("selected pending") != -1:
                    time.sleep(1);
                else:
                    return;


def load_schemas():
    with Maapi():
        pass


if __name__ == "__main__":
    load_schemas()
    logger = Log(MyLog(), add_timestamp=True)
    d = Daemon(name='myactiond', log=logger)
    a = []
    a.append(WaitForPending(daemon=d, actionpoint='wait-for-pending', log=logger))
    logger.info('--- Daemon myaction STARTED ---')
    d.start()
    signal.pause()
    d.finish()
    logger.info('--- Daemon myaction FINISHED ---')
