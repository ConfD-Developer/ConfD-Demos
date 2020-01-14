#!/usr/bin/env python
#
# Trivial Netconf Console
#
# This actually checks for >= Python 2.6 but unfortunately we cannot
# print a nice error message because this import has to come first :-(
#
# October 2019: Updated to support NMDA (rfc8342), get-data & edit-data
#

from __future__ import print_function
import sys
import os
import os.path
import re
import time
import calendar
from optparse import OptionParser, IndentedHelpFormatter
import base64
import socket
from xml.dom import Node
import xml.dom.minidom
import subprocess
try:
    import paramiko
    HAVE_PARAMIKO = True
except ImportError:
    HAVE_PARAMIKO = False

BUFSIZ = 16384
MAX_UINT32 = 2**32 - 1

NC_NS = 'urn:ietf:params:xml:ns:netconf:base:1.0'

NMDA_NS = 'urn:ietf:params:xml:ns:yang:ietf-netconf-nmda'
NMDA_DS_NS = 'urn:ietf:params:xml:ns:yang:ietf-datastores'

BASE_1_0 = 'urn:ietf:params:netconf:base:1.0'
BASE_1_1 = 'urn:ietf:params:netconf:base:1.1'

# RFC 4742
FRAMING_1_0 = 0
# the new framing in RFC 6242
FRAMING_1_1 = 1


class StdoutError(Exception):
    def __init__(self, message):
        super(StdoutError, self).__init__(self, message)
        self.message = message


class StderrError(Exception):
    def __init__(self, message):
        super(StderrError, self).__init__(self, message)
        self.message = message


class NetconfSSHLikeTransport(object):
    def __init__(self):
        self.buf_bytes = b""
        self.framing = FRAMING_1_0
        self.eom_found = False
        self.trace = False

    def connect(self):
        # should be overridden by subclass
        pass

    def _send(self, buf):
        # should be overridden by subclass
        pass

    def _send_eom(self):
        # should be overridden by subclass
        pass

    def _flush(self):
        # should be overridden by subclass, if needed
        pass

    def _set_timeout(self, timeout=None):
        # should be overridden by subclass
        pass

    def _recv(self, bufsiz):
        # should be overridden by subclass
        pass

    def send(self, request):
        if self.framing == FRAMING_1_1:
            self._send('\n#{0}\n{1}'.format(len(request), str_data(request)))
        else:
            self._send(request)

    def send_msg(self, request):
        self.send(request)
        self._send_eom()

    def send_eom(self):
        self._send_eom()

    def _get_eom(self):
        if self.framing == FRAMING_1_0:
            return ']]>]]>'
        elif self.framing == FRAMING_1_1:
            return '\n##\n'
        else:
            return ''

    # ret: (-2, bytes) on framing error
    #      (-1, bytes) on socket EOF
    #      (0, "") on EOM
    #      (1, chunk-data) on data
    def recv_chunk_bytes(self, timeout=None):
        self._set_timeout(timeout)
        if self.framing == FRAMING_1_0:
            return self.recv_chunk_bytes_framing_1_0()
        elif self.framing == FRAMING_1_1:
            return self.recv_chunk_bytes_framing_1_1()
        else:
            raise Exception('unknown framing {0}'.format(self.framing))

    def recv_chunk_bytes_framing_1_0(self):
            if self.eom_found:
                self.eom_found = False
                return (0, b"")
            bytes = self.buf_bytes
            self.buf_bytes = b""
            while len(bytes) < 6:
                x = self._recv(BUFSIZ)
                if x == b"":
                    return (-1, bytes)
                bytes += x
            idx = bytes.find(b"]]>]]>")
            if idx > -1:
                # eom marker found; store rest in buf
                self.eom_found = True
                self.buf_bytes = bytes[idx + 6:]
                return (1, bytes[:idx])
            else:
                # no eom marker found, keep the last 5 bytes
                # (might contain parts of the eom marker)
                self.buf_bytes = bytes[-5:]
                return (1, bytes[:-5])

    def recv_chunk_bytes_framing_1_1(self):
            # new framing
            bytes = self.buf_bytes
            self.buf_bytes = b""
            # make sure we have at least 4 bytes; LF HASH INT/HASH LF
            while len(bytes) < 4:
                x = self._recv(BUFSIZ)
                if x == b"":
                    # error, return what we have
                    return (-1, bytes)
                bytes += x
            # check the first two bytes
            if bytes[0:2] != b"\n#":
                # framing error
                return (-2, bytes)
            # read the chunk size
            sz = -1
            while sz == -1:
                # find the terminating LF
                idx = bytes.find(b"\n", 2)
                if idx > 12:
                    # framing error - too large integer or not correct
                    # chunk size specification
                    return (-2, bytes)
                if idx > -1:
                    # newline found, scan for number of bytes to read
                    try:
                        sz = int(bytes[2:idx])
                        if sz < 1 or sz > MAX_UINT32:
                            # framing error - range error
                            return (-2, bytes)
                    except Exception:
                        if bytes[2:idx] == b"#":
                            # EOM
                            self.buf_bytes = bytes[idx + 1:]
                            return (0, b"")
                        # framing error - not an integer, and not EOM
                        return (-2, bytes)
                    # skip the chunk size.  the while loop is now done
                    bytes = bytes[idx+1:]
                else:
                    # terminating LF not found, read more
                    x = self._recv(BUFSIZ)
                    if x == b"":
                        # error, return what we have
                        return (-1, bytes)
                    bytes += x
            # read the chunk data
            while len(bytes) < sz:
                x = self._recv(BUFSIZ)
                if x == b"":
                    return (-1, bytes)
                bytes += x
            # save rest of data
            self.buf_bytes = bytes[sz:]
            return (1, bytes[:sz])

    def recv_chunk(self, timeout=None):
        (flag, bytes) = self.recv_chunk_bytes(timeout=timeout)
        return (flag, str_data(bytes))

    def recv_msg(self, timeout=None):
        msg = ""
        while True:
            (code, bytes) = self.recv_chunk(timeout)
            if code == 1:
                msg += bytes
            elif code == 0:
                return msg
            else:
                # error
                return msg + bytes


class NetconfSSH(NetconfSSHLikeTransport):

    def __init__(self, hostname, port, username, password,
                 publicKey, publicKeyType,
                 privateKeyFile='', privateKeyType=''):
        NetconfSSHLikeTransport.__init__(self)
        self.hostname = str(hostname)
        self.port = int(port)
        self.privateKeyFile = privateKeyFile
        self.privateKeyType = privateKeyType
        self.publicKey = publicKey
        self.publicKeyType = publicKeyType
        self.password = password
        self.username = username
        self.saved = ""

    def connect(self):
        sock = create_connection(self.hostname, self.port)
        self._start_ssh(sock)

    def listen(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        print("** listening on ", host, port)
        sock.listen(1)
        conn, addr = sock.accept()
        sock.close()
        print("** call home from", addr)
        self._start_ssh(conn)

    def _start_ssh(self, sock):
        self.ssh = paramiko.Transport(sock)

        if self.publicKeyType == 'rsa':
            agent_public_key = paramiko.RSAKey(
                data=base64.decodestring(self.publicKey))
        elif self.publicKeyType == 'dss':
            agent_public_key = paramiko.DSSKey(
                data=base64.decodestring(self.publicKey))
        else:
            agent_public_key = None

        if not self.privateKeyFile == '':
            if self.privateKeyType == "rsa":
                user_private_key = paramiko.RSAKey.from_private_key_file(
                    self.privateKeyFile)
            # elif self.privateKeyType == "dss":
            else:
                user_private_key = paramiko.DSSKey.from_private_key_file(
                    self.privateKeyFile)

            try:
                self.ssh.connect(hostkey=agent_public_key,
                                 username=self.username,
                                 pkey=user_private_key)
            except paramiko.AuthenticationException:
                raise StdoutError("Authentication failed.")

        else:
            try:
                self.ssh.connect(hostkey=agent_public_key,
                                 username=self.username,
                                 password=self.password)
            except paramiko.AuthenticationException:
                raise StdoutError("Authentication failed.")

        self.chan = self.ssh.open_session()
        self.chan.invoke_subsystem("netconf")

    def _send(self, buf):
        try:
            if self.saved:
                buf = self.saved + buf
            # sending too little data in each SSH packet makes the
            # transfer slow.
            # paramiko still has  bug (?) where it doensn't send a full
            # SSH message, but keeps 64 bytes.  so we will send MAX-64, 64,
            # MAX-64, 64, ... instead of MAX all the time.
            if len(buf) < BUFSIZ:
                self.saved = buf
            else:
                self.chan.sendall(buf[:BUFSIZ])
                self.saved = buf[BUFSIZ:]
        except socket.error as x:
            print('socket error:', str(x))

    def _send_eom(self):
        try:
            self.chan.sendall(self.saved + self._get_eom())
            self.saved = ""
        except socket.error as x:
            self.saved = ""
            print('socket error:', str(x))

    def _flush(self):
        try:
            self.chan.sendall(self.saved)
            self.saved = ""
        except socket.error as x:
            self.saved = ""
            print('socket error:', str(x))

    def _recv(self, bufsiz):
        s = self.chan.recv(bufsiz)
        if self.trace:
            sys.stdout.write(str_data(s))
            sys.stdout.flush()
        return s

    def _set_timeout(self, timeout=None):
        self.chan.settimeout(timeout)

    def close(self):
        self.ssh.close()
        return True


class NetconfTCP(NetconfSSHLikeTransport):
    def __init__(self, hostname, port, username, groups, suplgids):
        NetconfSSHLikeTransport.__init__(self)
        self.hostname = str(hostname)
        self.port = int(port)
        self.username = username
        self.groups = groups
        self.suplgids = suplgids

    def connect(self):
        self.sock = create_connection(self.hostname, self.port)
        sockname = self.sock.getsockname()
        self._send('[{0};{1};tcp;{2};{3};{4};{5};{6};]\n'.format(
            self.username, sockname[0], os.getuid(), os.getgid(),
            self.suplgids, os.getenv("HOME", "/tmp"), self.groups))

    def _send(self, buf):
        try:
            self.sock.send(bin_data(buf))
        except socket.error as x:
            print('socket error:', str(x))

    def _send_eom(self):
        self._send(self._get_eom())

    def _recv(self, bufsiz):
        s = self.sock.recv(bufsiz)
        if self.trace:
            sys.stdout.write(str_data(s))
            sys.stdout.flush()
        return s

    def _set_timeout(self, timeout=None):
        self.sock.settimeout(timeout)

    def close(self):
        self.sock.close()
        return True


class HelpFormatterWithLineBreaks(IndentedHelpFormatter):
    def format_description(self, description):
        result = ""
        if description:
            description_paragraphs = description.split("\n")
            for paragraph in description_paragraphs:
                result += self._format_text(paragraph) + "\n"
        return result


# sort-of socket.create_connection() (new in 2.6)
def create_connection(host, port):
    lasterr = ''
    for res in socket.getaddrinfo(host, port,
                                  socket.AF_UNSPEC, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        try:
            sock = socket.socket(af, socktype, proto)
        except socket.error as x:
            sock = None
            lasterr = x
            continue
        try:
            sock.connect(sa)
        except socket.error as x:
            sock.close()
            sock = None
            lasterr = x
            continue
        break
    if sock is None:
        raise StdoutError("Failed to connect to {0}:{1} {2}".format(host, port, lasterr))
    return sock


def bin_data(buf):
    if sys.version_info[0] > 2 and isinstance(buf, str):
        return buf.encode('utf-8')
    return buf


def str_data(buf):
    if sys.version_info[0] > 2 and isinstance(buf, bytes):
        return buf.decode('utf-8')
    return buf


def write_fd(fd, data):
    try:
        if fd == sys.stdout:
            fd.write(str_data(data))
        else:
            fd.write(bin_data(data))
    except Exception:
        raise StderrError("Problem with xmllint executable. Is it in PATH?")


def hello_msg(versions):
    s = '''<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="{0}">
  <capabilities>
'''.format(NC_NS)
    if '1.0' in versions:
        s += '    <capability>{0}</capability>\n'.format(BASE_1_0)
    if '1.1' in versions:
        s += '    <capability>{0}</capability>\n'.format(BASE_1_1)
    s += '''
    </capabilities>
</hello>'''
    return s


def close_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="{0}" message-id="0">
        <close-session/>
    </rpc>'''.format(NC_NS)


def get_msg(cmd, db, o):
    rpc_attribute = o.rpc_attribute
    xpath = o.xpath
    with_defaults = o.wdefaults
    with_inactive = o.winactive
    if xpath == "":
        fstr = ""
    else:
        fstr = mk_filter_str(xpath)

    if with_defaults in ("explicit", "trim", "report-all", "report-all-tagged"):
        if cmd == "get-data":
            delem = "<with-defaults>{0}</with-defaults>".format(with_defaults)
        else:
            ns = 'urn:ietf:params:xml:ns:yang:ietf-netconf-with-defaults'
            delem = "<with-defaults xmlns='{0}'>{1}</with-defaults>".format(
                ns, with_defaults)
    else:
        delem = ""

    if with_inactive:
        ns = 'http://tail-f.com/ns/netconf/inactive/1.0'
        welem = "<with-inactive xmlns='{0}'/>".format(ns)
    else:
        welem = ""

    if cmd == "get-config":
        op = "<get-config><source><{0}/></source>{1}{2}{3}</get-config>".format(
            db, fstr, delem, welem)
    elif cmd == "get-data":
        subtree_filter = ""
        if o.subtree_filter != "":
            subtree_txt = ""
            subtree_template = "<subtree-filter>{0}</subtree-filter>"
            dataf = get_file(o.subtree_filter)
            subtree_txt = dataf.read()
            dataf.close()
            subtree_filter = subtree_template.format(subtree_txt)
        config_false = ""
        if o.config_filter == "false":
            config_false = "<config-filter>false</config-filter>"
        elif o.config_filter == "true":
            config_false = "<config-filter>true</config-filter>"
        xpath_filter = ""
        if xpath != "":
            xpath_filter = '<xpath-filter>{0}</xpath-filter>'.format(xpath)
        max_depth = ""
        if o.max_depth != "":
            max_depth = '<max-depth>{0}</max-depth>'.format(o.max_depth)
        op1 = '''<get-data xmlns="{0}" xmlns:ds="{1}">
                 <datastore>ds:{2}</datastore>
                 {3}
                 {4}
                 {5}
                 {6}
                 {7}
                 {8}
                 </get-data>'''
        op = op1.format(NMDA_NS, NMDA_DS_NS, db, subtree_filter, xpath_filter,
                        config_false, max_depth, delem, welem)
    else:
        op = "<get>{0}{1}{2}</get>".format(fstr, delem, welem)

    # deprecated tail-f with-defaults attribute in <rpc>
    if with_defaults in ("true", "false"):
        dattr = " with-defaults=\"{0}\"".format(with_defaults)
    else:
        dattr = ""

    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}"{1} message-id="1" {2}>
    {3}
</rpc>'''.format(NC_NS, dattr, rpc_attribute, op)


def get_config_opt(option, opt, value, parser):
    if len(parser.rargs) == 0:
        parser.values.ensure_value("getConfig", "default")
    elif parser.rargs[0].startswith("-"):
        parser.values.ensure_value("getConfig", "default")
    else:
        parser.values.ensure_value("getConfig", parser.rargs[0])
        del parser.rargs[0]

def get_data_opt(option, opt, value, parser):
    if len(parser.rargs) == 0:
        parser.values.ensure_value("getData", "default")
    elif parser.rargs[0].startswith("-"):
        parser.values.ensure_value("getData", "default")
    else:
        parser.values.ensure_value("getData", parser.rargs[0])
        del parser.rargs[0]

def opt_xpath(option, opt_str, value, parser):
    assert value is None
    value = ""
    rargs = parser.rargs
    while rargs:
        arg = rargs[0]
        # Stop if we hit an arg like "--foo", "-a", "-fx", "--file=f" etc.
        if ((arg[:2] == "--" and len(arg) > 2) or
                (arg[:1] == "-" and len(arg) > 1 and arg[1] != "-")):
            break
        else:
            value = value + " " + arg
            del rargs[0]
    setattr(parser.values, option.dest, value)


def kill_session_msg(id):
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
    <kill-session><session-id>{1}</session-id></kill-session>
</rpc>'''.format(NC_NS, id)


def discard_changes_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
    <discard-changes/>
</rpc>'''.format(NC_NS)


def commit_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
    <commit/>
</rpc>'''.format(NC_NS)


def validate_msg(db):
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
    <validate><source><{1}/></source></validate>
</rpc>'''.format(NC_NS, db)


def copy_running_to_startup_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
    <copy-config>
      <target>
        <startup/>
      </target>
      <source>
        <running/>
      </source>
    </copy-config>
</rpc>'''.format(NC_NS)


def get_schema_msg(identifier):
    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
    <get-schema xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
      <identifier>{1}</identifier>
    </get-schema>
</rpc>'''.format(NC_NS, identifier)


def create_subscription_msg(stream, xpath, start, stop):
    if xpath == "":
        fstr = ""
    else:
        fstr = mk_filter_str(xpath)

    if start == "":
        startstr = ""
    else:
        startstr = "<startTime>{0}+00:00</startTime>".format(start)

    if stop == "":
        stopstr = ""
    else:
        stopstr = "<stopTime>{0}+00:00</stopTime>".format(stop)

    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
  <create-subscription xmlns="urn:ietf:params:xml:ns:netconf:notification:1.0">
    <stream>{1}</stream>
    {2}
    {3}
    {4}
  </create-subscription>
</rpc>'''.format(NC_NS, stream, fstr, startstr, stopstr)


def establish_subscription_msg(stream, xpath, start, stop):
    if xpath == "":
        fstr = ""
    else:
        fstr = mk_filter_subnotif_str('stream-xpath-filter', xpath)

    if start == "":
        startstr = ""
    else:
        startstr = "<startTime>{0}+00:00</startTime>".format(start)

    if stop == "":
        stopstr = ""
    else:
        stopstr = "<stopTime>{0}+00:00</stopTime>".format(stop)

    return '''<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="{0}" message-id="1">
  <establish-subscription
        xmlns="urn:ietf:params:xml:ns:yang:ietf-subscribed-notifications">
    <stream>{1}</stream>
    {2}
    {3}
    {4}
  </establish-subscription>
</rpc>'''.format(NC_NS, stream, fstr, startstr, stopstr)


def mk_filter_str(xpath):
    if "'" in xpath:
        return "<filter type='xpath' select=\"{0}\"/>".format(xpath)
    else:
        return "<filter type='xpath' select='{0}'/>".format(xpath)

def mk_filter_subnotif_str(filter_field, filter_content):
    if "'" in filter_content:
        return "<{0}>\"{1}\"<{0}>".format(filter_field, filter_content)
    else:
        return "<{0}>'{1}'<{0}>".format(filter_field, filter_content)


# interactive mode
def read_msg():
    print("\n* Enter a NETCONF operation, end with an empty line")
    msg = '''<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="{0}" message-id="2">
    '''.format(NC_NS)
    ln = sys.stdin.readline()
    while ln != "\n":
        msg += ln
        ln = sys.stdin.readline()
    msg += '</rpc>\n'
    return msg


def strip(node):
    """Remove empty text nodes, and non-element nodes.
    The result after strip () is a child list with non-empty text-nodes,
    and element nodes only."""
    c = node.firstChild
    while c is not None:
        remove = False
        if c.nodeType == Node.TEXT_NODE:
            if c.nodeValue.strip() == "":
                remove = True
        else:
            if c.nodeType != Node.ELEMENT_NODE:
                remove = True
        if remove:
            tmp = c.nextSibling
            node.removeChild(c)
            c.unlink()
            c = tmp
        else:
            c = c.nextSibling


def get_file(name):
    if name == '-':
        return sys.stdin
    else:
        return open(name, "rb")


def build_options_parser():
    usage = """%prog [-h | --help] [options] [cmdoptions | <filename> | -]

    Where <filename> is a file containing a NETCONF XML command session.
    If <filename> is not given, one of the Command Options must be given.
    Filename '-' means standard input.
    """

    parser = OptionParser(usage, formatter=HelpFormatterWithLineBreaks())
    parser.add_option("-v", "--version", dest="version",
                      help="force NETCONF version 1.0 or 1.1")
    parser.add_option("-d", "--debug", dest="debug",
                      action="store_true")
    parser.add_option("-u", "--user", dest="username", default="admin",
                      help="username")
    parser.add_option("-p", "--password", dest="password", default="admin",
                      help="password")
    parser.add_option("--proto", dest="proto", default="ssh",
                      help="Which transport protocol to use, one of ssh or tcp")
    parser.add_option("--host", dest="host", default="localhost",
                      help="NETCONF server hostname")
    parser.add_option("--port", dest="port", default=2022, type="int",
                      help="NETCONF server port")
    parser.add_option("--listen", dest="listen", action="store_true",
                      help="Start NETCONF Call Home listener")
    parser.add_option("--listen-address", dest="listen_address",
                      default="0.0.0.0", help="Listen to this address")
    parser.add_option("--listen-port", dest="listen_port", default=4334,
                      type="int", help="Listen to this port")

    parser.add_option("--iter", dest="iter", default=1, type="int",
                      help="Sends the same request ITER times.  Useful only in"
                      " test scripts")
    parser.add_option("-i", "--interactive", dest="interactive",
                      action="store_true")

    styleopts = parser.add_option_group("Style Options")
    styleopts.description = (
        "raw:    print bytes received on the wire,"
        " framing is removed\n"
        "plain:  skip the <hello> reply, print one reply as"
        " raw, skip the rest\n"
        "pretty: skip the <hello> reply, pretty-print one"
        " reply, skip the rest\n"
        "all:    skip the <hello> reply, pretty-print the rest"
        " of the replies\n"
        "noaaa:  as pretty, but remove Tail-f AAA and IETF"
        " NACM from the output")
    styleopts.add_option("-s", "--outputStyle", dest="style", default="default",
                         help="Display output in: raw, plain, pretty, all, "
                         "or noaaa format")

    sshopts = parser.add_option_group("SSH Options")
    sshopts.add_option("--privKeyType", dest="privKeyType", default="",
                       help="type of private key, rsa or dss")
    sshopts.add_option("--privKeyFile", dest="privKeyFile", default="",
                       help="file which contains the private key")

    tcpopts = parser.add_option_group("TCP Options")
    tcpopts.add_option("-g", "--groups", dest="groups", default="",
                       help="Set group membership for user - comma separated"
                       " string")
    tcpopts.add_option("-G", "--sup-groups", dest="supgroups", default="",
                       help="Set supplementary UNIX group ids for user - comma "
                       "separated string of integers")

    cmdopts = parser.add_option_group("NETCONF Command Options")
    cmdopts.add_option("--hello", dest="hello", action="store_true",
                       help="Connect to the server and print its capabilities")
    cmdopts.add_option("--get", dest="get", action="store_true",
                       help="Takes an optional -x argument for XPath filtering")
    cmdopts.add_option("--get-config", action="callback",
                       callback=get_config_opt,
                       help="Takes an optional --db argument, default is "
                       "'running', and an optional -x argument for XPath "
                       "filtering")
    cmdopts.add_option("--get-data", action="callback",
                       callback=get_data_opt,
                       help="Takes an optional --db argument, default is "
                       "'running', an optional --subtree-filter argument, "
                       "an optional -x argument for XPath filtering, "
                       "an optional --only-config-false argument, "
                       "an optional --only-config-true argument (these "
                       "arguments can not be used together) or an optional "
                       "--max-depth argument.")
    cmdopts.add_option("--max-depth", dest="max_depth", default="",
                       help="Can be used to limit the depth of the "
                       "--get-data command."),
    cmdopts.add_option("--config-filter", dest="config_filter",
                       help="Can be set to 'true' or 'false'. If not set at "
                       "all, both operational and config data will be "
                       "returned from --get-data. If set to true, only config "
                       "data will be returned. If set to false, only "
                       "operational data will be returned.")
    cmdopts.add_option("--subtree-filter", dest="subtree_filter", default="",
                       help="Takes a filename (or '-' for standard input) as "
                       "argument. Can be used by --get-data."),
    cmdopts.add_option("--db", dest="db", default="running",
                       help="Database for commands that operate on a "
                       "database."),
    cmdopts.add_option("--with-defaults", dest="wdefaults", default="",
                       help="One of 'explicit', 'trim', 'report-all' or "
                       "'report-all-tagged'.  Use with --get, --get-config, "
                       "--get-data or --copy-config.")
    cmdopts.add_option("--with-inactive", dest="winactive", action="store_true",
                       help="Send with-inactive parameter.  Use with --get, "
                       "--get-config, --get-data, --copy-config, "
                       "--edit-config, or --edit-data.")
    cmdopts.add_option("-x", "--xpath", dest="xpath", default="",
                       action="callback", callback=opt_xpath,
                       help="XPath filter to be used with --get, --get-config, "
                       "--get-data and --create-subscription")
    cmdopts.add_option("--kill-session", dest="kill_session", default="",
                       help="Takes a session-id as argument.")
    cmdopts.add_option("--discard-changes", dest="discard_changes",
                       action="store_true")
    cmdopts.add_option("--commit", dest="commit",
                       action="store_true")
    cmdopts.add_option("--validate", dest="validate",
                       action="store_true",
                       help="Takes an optional --db argument, "
                       "default is 'running'.")
    cmdopts.add_option("--copy-running-to-startup",
                       dest="copy_running_to_startup", action="store_true")
    cmdopts.add_option("--copy-config", dest="copy", default="",
                       help="Takes a filename (or '-' for standard input) as"
                       " argument. The contents of the file"
                       " is data for a single NETCONF copy-config operation"
                       " (put into the <config> XML element)."
                       " Takes an optional --db argument, default is "
                       "'running'.")
    cmdopts.add_option("--edit-config", dest="edit", default="",
                       help="Takes a filename (or '-' for standard input) as "
                       " argument. The contents of the file"
                       " is data for a single NETCONF edit-config operation"
                       " (put into the <config> XML element)."
                       " Takes an optional --db argument, default is "
                       "'running'.")
    cmdopts.add_option("--edit-data", dest="edit_data", default="",
                       help="Takes a filename (or '-' for standard input) as "
                       " argument. The contents of the file"
                       " is data for a single NETCONF edit-data operation"
                       " (put into the <config> XML element)."
                       " Takes an optional --db argument, default is "
                       "'running'.")
    cmdopts.add_option("--get-schema", dest="get_schema",
                       help="Takes an identifier (typically YANG module name) "
                       "as parameter")
    cmdopts.add_option("--create-subscription", dest="create_subscription",
                       help="Takes a stream name as parameter, and an optional "
                       "-x for XPath filtering")
    cmdopts.add_option("--establish-subscription",
                       dest="establish_subscription",
                       help="Takes a stream name as parameter, and an optional "
                       "-x for XPath filtering")
    cmdopts.add_option("--rpc", dest="rpc", default="",
                       help="Takes a filename (or '-' for standard input) as "
                       " argument. The contents of the file"
                       " is a single NETCONF rpc operation (w/o the surrounding"
                       " <rpc>).")
    cmdopts.add_option("--start-time", dest="start_time", default="",
                       help="Takes a timestamp in YYYY-MM-DDTHH:MM:SS format, "
                       "for e.g. 2017-01-10T12:05:21. Assumes UTC.  Used with "
                       "--create-subscription")
    cmdopts.add_option("--stop-time", dest="stop_time", default="",
                       help="Takes a timestamp in YYYY-MM-DDTHH:MM:SS format, "
                       "for e.g. 2017-01-10T12:05:21. Assumes UTC. Used with "
                       "--create-subscription. The session will be closed "
                       "after stop-time has been reached")
    cmdopts.add_option("--rpc-attribute", dest="rpc_attribute", default="",
                       help="XML attributes to send in the rpc element")
    return parser


def validate_options(o):
    if (o.wdefaults != "" and
        o.wdefaults not in ("trim", "explicit", "report-all",
                            "report-all-tagged", "true", "false")):
        raise StdoutError("Bad --with-defaults value: {0}".format(o.wdefaults))

    if o.proto == "ssh" and not HAVE_PARAMIKO:
        msg = ("You must install the python ssh implementation paramiko "
               "in order to use ssh.")
        raise StdoutError(msg)


def main(parser, o):
    if (o.debug):
        print("DEBUG: pid: {0}".format(os.getpid()))

    if len(args) == 1:
        filename = args[0]
    else:
        filename = None

    cmdf = None
    dataf = None

    # Read the command file
    if filename:
        cmdf = get_file(filename)
        msg = None
    elif o.get:
        msg = get_msg("get", None, o)
    elif hasattr(o, "getConfig"):
        cmd = "get-config"
        if o.getConfig == "default":
            db = o.db
        else:
            db = o.getConfig
        msg = get_msg(cmd, db, o)
    elif hasattr(o, "getData"):
        cmd = "get-data"
        if o.getData == "default":
            db = o.db
        else:
            db = o.getData
        msg = get_msg(cmd, db, o)
    elif o.rpc != "":
        dataf = get_file(o.rpc)
        msg = None
    elif o.edit != "":
        dataf = get_file(o.edit)
        msg = None
    elif o.edit_data != "":
        dataf = get_file(o.edit_data)
        msg = None
    elif o.copy != "":
        dataf = get_file(o.copy)
        msg = None
    elif o.kill_session != "":
        msg = kill_session_msg(o.kill_session)
    elif o.discard_changes:
        msg = discard_changes_msg()
    elif o.commit:
        msg = commit_msg()
    elif o.validate:
        msg = validate_msg(o.db)
    elif o.copy_running_to_startup:
        msg = copy_running_to_startup_msg()
    elif o.get_schema is not None:
        msg = get_schema_msg(o.get_schema)
    elif o.create_subscription is not None:
        msg = create_subscription_msg(o.create_subscription, o.xpath,
                                      o.start_time, o.stop_time)
    elif o.establish_subscription is not None:
        msg = establish_subscription_msg(o.establish_subscription, o.xpath,
                                         o.start_time, o.stop_time)
    elif o.hello:
        msg = None
    elif o.interactive:
        pass
    else:
        parser.error("a filename or a command option is required")

    if o.listen and o.proto != "ssh":
        parser.error("can only listen for call home over ssh")

    validate_options(o)

    # create the transport object
    if o.proto == "ssh":
        c = NetconfSSH(o.host, o.port, o.username, o.password, "", "",
                       o.privKeyFile, o.privKeyType)
    else:
        c = NetconfTCP(o.host, o.port, o.username, o.groups, o.supgroups)

    if o.style == "raw":
        c.trace = True

    if o.listen:
        # listen for a call-home connection
        c.listen(o.listen_address, o.listen_port)
    else:
        # connect to the NETCONF server
        c.connect()

    # figure out which versions to advertise
    versions = []
    if cmdf is not None and o.version is None:
        # backwards compat - no version specified, and everything is
        # done from file.  assume this is 1.0.
        versions.append('1.0')
    else:
        if o.version == '1.0' or o.version is None:
            versions.append('1.0')
        if o.version == '1.1' or o.version is None:
            versions.append('1.1')

    # send our hello unless we do everything from the file
    if cmdf is None:
        c.send_msg(hello_msg(versions))

    # read the server's hello
    hello_reply = c.recv_msg()

    # parse the hello message to figure out which framing
    # protocol to use
    d = xml.dom.minidom.parseString(hello_reply)
    if d is not None:
        d = d.firstChild
    if d is not None:
        strip(d)
        if (d.namespaceURI == NC_NS and
                d.localName == 'hello' and
                d.firstChild is not None):
            d = d.firstChild
            strip(d)
            if (d.namespaceURI == NC_NS and
                    d.localName == 'capabilities'):
                d = d.firstChild
                strip(d)
                while (d is not None):
                    if (d.namespaceURI == NC_NS and
                            d.localName == 'capability'):
                        if ('1.1' in versions and
                                d.firstChild.nodeValue.strip() == BASE_1_1):
                            # switch to new framing
                            c.framing = FRAMING_1_1
                    d = d.nextSibling

    if cmdf is not None or dataf is not None:
        # Send the request from file
        if cmdf is not None:
            f = cmdf
            # use raw send function; do not add framing
            send = c._send
        else:
            f = dataf
            send = c.send
            # the file contains the RPC only; send extra stuff
            send('''<?xml version="1.0" encoding="UTF-8"?>
                    <rpc xmlns="{0}" message-id="1">'''.format(NC_NS))
        if (o.edit != ""):
            # the file contains the edit-config payload only; send rpc
            send("<edit-config xmlns:nc='{0}'>"
                 "<target><{1}/></target><config>".format(NC_NS, o.db))
        elif (o.edit_data != ""):
            # the file contains the edit-data payload only; send rpc
            send("<edit-data xmlns='{0}' xmlns:ds='{1}'>"
                 "<datastore>ds:{2}</datastore><config>".format(NMDA_NS,
                                                                NMDA_DS_NS,
                                                                o.db))
        elif (o.copy != ""):
            # the file contains the copy-config payload only; send rpc
            send("<copy-config><target><{0}/></target><source><config>".format(
                o.db))
        # read and send from the file
        buf = f.read(BUFSIZ)
        while len(buf) > 0:
            send(buf)
            buf = f.read(BUFSIZ)
        # end the rpc
        if (o.edit != ""):
            send("</config></edit-config>")
        elif (o.edit_data != ""):
            send("</config></edit-data>")
        elif (o.copy != ""):
            send("</config></source></copy-config>")
        if dataf is not None:
            send('</rpc>')
            c.send_eom()
            # read one rpc-reply, and then close
            n = 1
        else:
            c._flush()
            # print results until EOF
            n = -1
    else:
        n = o.iter
        if (o.create_subscription is not None or
            o.interactive or o.establish_subscription is not None):
            if o.style == 'default':
                o.style = 'all'
            # print results until EOF
            n = -1

    do_get_schema = False
    if o.get_schema is not None and o.style == 'default':
        do_get_schema = True

    # style:
    #   raw:    print what we got on the wire, no extra processing,
    #           except that framing is removed
    #           FIXME: should we really remove framing in raw?
    #   plain:  skip the hello reply, print one reply as raw, skip the rest
    #   pretty: skip the hello reply, pretty-print one reply, skip the rest
    #   all:    skip the hello reply, pretty-print the rest of the replies
    #   noaaa:  as pretty, but remove tail-f aaa and ietf nacm from the output
    #           (this is a legacy hack)
    if o.style == 'default':
        o.style = 'pretty'

    # possibly set up for pretty printing through xmllint
    if o.style == "noaaa":
        noaaa = ("|awk ' BEGIN { del=0} /<(aaa|nacm)/ {del=1} /<\\/(aaa|nacm)>/"
                 " {del=0;next} del == 1 {next} {print}'")
    else:
        noaaa = ""
    xmllint = "xmllint --format - " + noaaa

    do_print = True
    is_closed = False
    chunk = ""

    if o.style == "raw":
        do_print = False

    if o.hello and o.style == "raw":
        # the hello reply has already been printed
        n = 0

    if (o.create_subscription is not None) and (o.stop_time != ""):
        stop_time = calendar.timegm(time.strptime(o.stop_time,
                                                  "%Y-%m-%dT%H:%M:%S"))
    elif (o.establish_subscription is not None) and (o.stop_time != ""):
        stop_time = calendar.timegm(time.strptime(o.stop_time,
                                                  "%Y-%m-%dT%H:%M:%S"))
    else:
        stop_time = 0

    replay_complete = 0
    latest_msg = ""
    has_received_data = False

    while (not is_closed and (n != 0 or o.interactive) and
           not do_get_schema and
           ((stop_time == 0) or (replay_complete == 0) or
            (time.time() < stop_time))):
        fd = None
        if do_print and o.style in ("pretty", "all", "noaaa"):
            p = subprocess.Popen(xmllint, shell=True, stdin=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            fd = p.stdin
            p.stderr.close()
        else:
            fd = sys.stdout
            p = None

        if o.interactive:
            msg = read_msg()
        # send the request, if not already sent from file above
        if msg is not None:
            c.send_msg(msg)

        # receive the reply in chunks, so we can print them in raw format
        # as we get them
        nchunks = 0
        while True:
            tim = False
            code = 0
            if o.hello:
                if hello_reply != "":
                    # if msg is None we need to print the hello_reply (unless
                    # already done; in that case hello_reply is "")
                    chunk = hello_reply
                    # set n to 1 to abort while loop
                    n = 1
            else:
                try:
                    (code, chunk) = c.recv_chunk(1)
                except socket.timeout:
                    tim = True
                except KeyboardInterrupt:
                    c.close()
                    exit(0)

                latest_msg += chunk
            if code < 0:
                # EOF received (or framing error)
                if do_print:
                    write_fd(fd, chunk)
                if nchunks == 0:
                    is_closed = True
                    break
                else:
                    if code == -1:
                        msg = "unexpected EOF in NETCONF transport"
                    elif code == -2:
                        msg = "NETCONF transport framing error"
                    raise StderrError(msg)
            if not tim:
                nchunks += 1
                if do_print:
                    write_fd(fd, chunk)

                if code == 0:
                    # we have received a full message
                    if (stop_time != 0) and (replay_complete == 0):
                        # check if we received replayComplete
                        pattern = "<(.*:)?notification.*<(.*:)?replayComplete"
                        if (re.search(pattern, latest_msg) is not None):
                            replay_complete = 1
                    latest_msg = ""
                    break

        if o.style not in ['raw']:
            fd.close()

        if p is not None:
            p.wait()
            if nchunks > 0:
                if p.returncode == 127:
                    raise StderrError("Problem with xmllint executable. "
                                      "Is it in PATH?")
                if p.returncode != 0:
                    raise StderrError("xmllint failed. Is the returned XML ok?")
            elif(not has_received_data):
                raise StderrError("No data received in the reply.")

            if o.style not in ['all', 'raw', 'plain']:
                # don't print the rest of the replies
                do_print = False

        has_received_data = True

        if o.create_subscription is not None:
            msg = None

        if o.establish_subscription is not None:
            msg = None

        n = n - 1

    if do_get_schema:
        c.send_msg(msg)
        schema_reply = c.recv_msg()
        d = xml.dom.minidom.parseString(schema_reply)
        fd = sys.stdout
        if d is not None:
            d = d.firstChild
            if d is not None:
                strip(d)
                if (d.namespaceURI == NC_NS and
                        d.localName == 'rpc-reply' and
                        d.firstChild is not None):
                    d = d.firstChild
                    if d.localName == 'data' and d.firstChild is not None:
                        write_fd(fd, d.firstChild.nodeValue)
                    else:
                        sys.stderr.write("Didn't get data in the reply")
                else:
                    sys.stderr.write("Didn't get rpc-reply")
            else:
                sys.stderr.write("Couldn't parse the RPC reply")
        else:
            sys.stderr.write("Couldn't parse the RPC reply")

    if not is_closed:
        # send close
        c.send_msg(close_msg())
        # recv close reply
        c.recv_msg()

    # Done
    c.close()

    # Sometimes an exception is seen just prior to terminating. A web search
    # suggests this might be an issue with some older versions of python. The
    # below code is to work around that.
    try:
        sys.stdout.close()
    except Exception:
        pass

    try:
        sys.stderr.close()
    except Exception:
        pass


if __name__ == '__main__':
    parser = build_options_parser()
    (o, args) = parser.parse_args()

    try:
        main(parser, o)
    except StdoutError as e:
        print(e.message)
        sys.exit(1)
    except StderrError as e:
        sys.stderr.write(e.message + '\n')
        sys.exit(1)
    except Exception:
        raise
