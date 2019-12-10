# *********************************************************************
# ConfD CDB iteration example - python version
#
# (C) 2007-2019 Tail-f Systems
# Permission to use this code as a starting point hereby granted
# This is ConfD Sample Code.
#
# See the README file for more information
# ********************************************************************

import logging
import socket

import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi
import select
import sys

import user_folders_ns

confd_debug_level = _confd.TRACE
log_level = logging.INFO
CONFD_ADDR = '127.0.0.1'
ROOT_PATH = "/folder-user"
INDENT_SIZE = 4
INDENT_STR = " "

logging.basicConfig(
    format="%(asctime)s:%(relativeCreated)s "
           "%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s  %(message)s",
    level=log_level)
log = logging.getLogger("modifications_python")


def get_value(tag_val, indent):
    log.debug("==> val={} indent={}".format(tag_val, indent))

    text = ""
    val_type = tag_val.v.confd_type()
    tag = str(tag_val)

    # start a container/list entry creation/modification
    if val_type == _confd.C_XMLBEGIN:
        text += "{}<{}>\n".format(INDENT_STR * indent, tag)
        indent += INDENT_SIZE
    # exit from a processing of container/list entry creation/modification
    elif val_type == _confd.C_XMLEND:
        indent -= INDENT_SIZE
        text += "{}</{}>\n".format(INDENT_STR * indent, tag)
    # deletion of a leaf
    elif val_type == _confd.C_NOEXISTS:
        text += "{}<{} operation=\"delete\">\n".format(INDENT_STR * indent, tag)
    # deletion of a list entry / container
    elif val_type == _confd.C_XMLBEGINDEL:
        text += "{}<{} operation=\"delete\">\n".format(INDENT_STR * indent, tag)
        indent += INDENT_SIZE
    # type empty leaf creation
    elif val_type == _confd.C_XMLTAG:
        text += "{}<{}/>\n".format(INDENT_STR * indent, tag)
    # regular leaf creation/modification
    else:
        text += "{}<{}>{}</{}>\n".format(INDENT_STR * indent, tag,
                                         str(tag_val.v), tag)

    log.debug("<== text={} indent={}".format(text, indent))
    return text, indent


def process_modifications(modifications):
    log.info("==> modifications={} len(modifications)={}".
             format(modifications, len(modifications)))
    indent = 0
    result = ""
    for val in modifications:
        (text, indent) = get_value(val, indent)
        result += text
    sys.stderr.write("modifications read by subscriber:\n{}".format(result))

    log.info("<==")


def process_subscriptions(spoint, subsock):
    log.info("==>")
    sub_points = cdb.read_subscription_socket(subsock)
    for s in sub_points:
        if s == spoint:
            log.debug("our spoint=%i triggered" % spoint)
            flags = cdb.GET_MODS_INCLUDE_LISTS
            log.debug("subsock.fileno={} spoint={} flags={}".format(
                subsock.fileno(), spoint, flags))
            modifications = _confd.cdb.get_modifications(
                subsock,
                spoint, cdb.GET_MODS_INCLUDE_LISTS, None)
            process_modifications(modifications)
            cdb.sync_subscription_socket(subsock,
                                         cdb.DONE_PRIORITY)
    log.info("<==")


def run():
    log.info("==>")

    # In C we use confd_init() which sets the debug-level, but for Python the
    # call to confd_init() is done when we do 'import confd'.
    # Therefore we need to set the ConfD debug level here (if we want it to be
    # different from the default debug level - CONFD_SILENT):
    _confd.set_debug(confd_debug_level, sys.stderr)
    subsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    # maapi socket for load schemas
    maapisock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    maapi.connect(maapisock, CONFD_ADDR, _confd.CONFD_PORT)
    maapi.load_schemas(maapisock)

    cdb.connect(subsock, cdb.SUBSCRIPTION_SOCKET, CONFD_ADDR, _confd.CONFD_PORT)
    spoint = cdb.subscribe(subsock, 3, user_folders_ns.ns.hash, ROOT_PATH)
    cdb.subscribe_done(subsock)
    log.debug("Subscribed to path %s spoint=%i" % (ROOT_PATH, spoint))
    log.info("CDB subscriber initialized!")
    try:
        _r = [subsock]
        _w = []
        _e = []
        log.debug("subscok connected, starting ConfD loop")
        while True:
            (r, w, e) = select.select(_r, _w, _e, 1)
            for rs in r:
                log.debug("rs.fileno=%i subscok.fileno=%i" % (
                    rs.fileno(), subsock.fileno()))
                if rs.fileno() == subsock.fileno():
                    log.debug("subsock triggered")
                    try:
                        process_subscriptions(spoint, subsock)
                    except _confd.error.Error as e:
                        if e.confd_errno is not _confd.ERR_EXTERNAL:
                            raise e

    except KeyboardInterrupt:
        print("\nCtrl-C pressed\n")
    finally:
        subsock.close()

    log.info("<==")


if __name__ == "__main__":
    log.info("==>")
    run()
    log.info("<==")
