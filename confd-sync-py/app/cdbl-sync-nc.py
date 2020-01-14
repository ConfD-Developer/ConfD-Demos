from confd.dp import Action, Daemon
import _confd as confd
import _confd.cdb as cdb
import _confd.maapi as maapi

import socket
import sys
import subprocess
import os
from multiprocessing import Process, SimpleQueue

CONFD_ADDR = '127.0.0.1'
ROOT_PATH = "/"
SUB_PATH = "/r:sys"
CLIENT_PATH = "/nsc:netconf-client"
SERVER_PATH = CLIENT_PATH+"/netconf-server"

INDENT_SIZE = 2
INDENT_STR = " "

def edit_config_msg(mods):
    return '''<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
  </capabilities>
</hello>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <discard-changes/>
</rpc>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
  <edit-config xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <target>
      <candidate/>
    </target>
    <test-option>set</test-option>
    <config>
      {0}
    </config>
  </edit-config>
</rpc>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="3">
  <validate>
    <source>
      <candidate/>
    </source>
  </validate>
</rpc>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="4">
  <close-session/>
</rpc>
]]>]]>'''.format(mods)

def commit_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
  </capabilities>
</hello>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="5">
  <commit>
    <confirmed/>
    <persist>sync_commit</persist>
  </commit>
</rpc>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="6">
  <close-session/>
</rpc>xs
]]>]]>'''

def confirm_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
  </capabilities>
</hello>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="7">
  <commit>
    <persist-id>sync_commit</persist-id>
  </commit>
</rpc>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="8">
  <close-session/>
</rpc>
]]>]]>'''

def cancel_msg():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
  </capabilities>
</hello>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="7">
  <cancel-commit>
    <persist-id>sync_commit</persist-id>
  </cancel-commit>
</rpc>
]]>]]>
<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="8">
  <close-session/>
</rpc>
]]>]]>'''

ms = socket.socket()
maapi.connect(ms, CONFD_ADDR, confd.PORT)
maapi.load_schemas(ms)
ms.close

class StdoutError(Exception):
    def __init__(self, message):
        super(StdoutError, self).__init__(self, message)
        self.message = message


class StderrError(Exception):
    def __init__(self, message):
        super(StderrError, self).__init__(self, message)
        self.message = message


def get_value(tv, indent, current_path, root_ns):
    text = ""
    val_type = tv.v.confd_type()
    ns = confd.hash2str(tv.ns)
    tag = str(tv)
    prefix = confd.ns2prefix(tv.ns)

    # start a container/list entry creation/modification
    if val_type == confd.C_XMLBEGIN:
        text += "{}<{} xmlns=\"{}\">\n".format(INDENT_STR * indent, tag, ns)
        indent += INDENT_SIZE
        current_path += "/" + prefix + ":" + tag
        # exit from a processing of container/list entry creation/modification
    elif val_type == confd.C_XMLEND:
        text += "{}</{}>\n".format(INDENT_STR * indent, tag)
        indent -= INDENT_SIZE
        if '/' in current_path:
            last_slash = current_path.rindex('/')
            current_path = current_path[:last_slash]
        else:
            current_path = ""
        # deletion of a leaf
    elif val_type == confd.C_NOEXISTS:
        # we don't do netconf delete (not remove) operations below as it will be
        # silently ignored if the server to remove does not exist. We want to know
        # if we are out of sync.
        text += "{}<{} nc:operation=\"delete\">\n".format(INDENT_STR * indent, tag)
        # deletion of a list entry / container
    elif val_type == confd.C_XMLBEGINDEL:
        text += "{}<{} nc:operation=\"delete\">\n".format(INDENT_STR * indent, tag)
        indent += INDENT_SIZE
        current_path += "/" + prefix + ":" + tag
        # type empty leaf creation
    elif val_type == confd.C_XMLTAG:
        text += "{}<{}/>\n".format(INDENT_STR * indent, tag)
        # linked list creation/modification
    elif(val_type == confd.C_LIST):
        path = current_path + "/" + prefix + ":" + tag
        ll_chars = tv.v.val2str((root_ns, path))
        val_strs = ''.join(ll_chars).split()
        for val_str in val_strs:
            text += "{}<{}>{}</{}>\n".format(INDENT_STR * indent, tag,
                                             val_str, tag)
        # regular leaf creation/modification
    else:
        path = current_path + "/" + prefix + ":" + tag
        text += "{}<{}>{}</{}>\n".format(INDENT_STR * indent, tag,
                                         tv.v.val2str((root_ns, path)), tag)
    return text, indent, current_path

def send_netconf_operation(op, sid, q):
    crs = socket.socket()
    cdb.connect(crs, cdb.DATA_SOCKET, CONFD_ADDR, confd.CONFD_PORT)
    cds = socket.socket()
    cdb.connect(cds, cdb.DATA_SOCKET, CONFD_ADDR, confd.CONFD_PORT)
    cdb.start_session2(crs, cdb.RUNNING, 0);
    cdb.start_session(cds, cdb.OPERATIONAL)

    num = cdb.num_instances(crs, SERVER_PATH)

    for i in range(num):
        id = int(cdb.get(cds, "{}[{}]/subscription-id".format(SERVER_PATH,i)))
        if id == sid:
          break;

    if id != sid:
        cds.close()
        crs.close()
        print("Subscription ID: {}".format(sid))
        return

    ipaddr = str(cdb.get(crs, "{}[{}]/remote-address".format(SERVER_PATH,i)))
    port = str(cdb.get(crs, "{}[{}]/remote-port".format(SERVER_PATH,i)))
    user = str(cdb.get(crs, "{}[{}]/username".format(SERVER_PATH, i)))
    passwd = str(cdb.get(crs, "{}[{}]/password".format(SERVER_PATH,i)))
    proc = subprocess.Popen("netconf-console --user={} --password={} --host={} --port={} -".format(user, passwd, ipaddr, port),
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    cmd = op
    output, errors = proc.communicate(input=cmd.encode('utf-8'))
    proc.stdout.close()
    proc.stderr.close()
    reply = output.decode()
    errstr = errors.decode()
    if reply.find('<rpc-error>') != -1 or errstr != "":
        q.put((reply, errstr))
    cds.close()
    crs.close()


def process_modifications(modifications, sid, q):
    indent = 0
    result = ""
    current_path = ""
    root_ns = confd.hash2str(modifications[1].ns)
    for tag_val in modifications:
        (text, indent, current_path) = get_value(tag_val, indent, current_path, root_ns)
        result += text
    op = edit_config_msg(result)
    send_netconf_operation(op, sid, q)


def commit(sid, q):
    op = commit_msg()
    send_netconf_operation(op, sid, q)


def cancel_commit(sid, q):
    op = cancel_msg()
    send_netconf_operation(op, sid. q)


def confirm_commit(sid, q):
    op = confirm_msg()
    send_netconf_operation(op, sid, q)


def handle_sub_prepare(css, sids, sub_flags):
    print("***Config updated --> Prepare")
    processes = []
    q = SimpleQueue()
    for sid in sids:
        flags = cdb.GET_MODS_INCLUDE_LISTS | cdb.GET_MODS_SUPPRESS_DEFAULTS
        mods = cdb.get_modifications(css, sid, flags, ROOT_PATH)
        if mods == []:
            print("no modifications for subid {}".format(sid))
        else:
            print("edit-config and validate for subid {}".format(sid))
            p = Process(target=process_modifications, args=(mods,sid,q))
            processes.append(p)
            p.start()
    for process in processes:
        process.join()
    if not q.empty():
        cdb.sub_abort_trans(css, confd.ERRCODE_APPLICATION, 0, 0, str(list(q.queue)))
        # TODO USE lxml to get the error string from the NETCONF error reply
        # TODO sub_abort_trans_info(...)
        return
    processes = []
    for sid in sids:
        print("commit for subid {}".format(sid))
        p = Process(target=commit, args=(sid,q))
        processes.append(p)
        p.start()
    for process in processes:
        process.join()
    if not q.empty():
        cdb.sub_abort_trans(css, confd.ERRCODE_APPLICATION, 0, 0, str(list(q.queue)))
        # TODO USE lxml to get the error string from the NETCONF error reply
        # TODO sub_abort_trans_info(...)
        return
    cdb.sync_subscription_socket(css, cdb.DONE_PRIORITY)


def handle_sub_abort(css, sids):
    print("***Config aborted")
    processes = []
    q = SimpleQueue()
    for sid in sids:
        print("cancel-commit for subid {}".format(sid))
        p = Process(target=cancel_commit, args=(sid,q))
        processes.append(p)
        p.start()
    for process in processes:
        process.join()
    if not q.empty():
        sys.stderr.write("Cancel commit failed:\n{}\n".format(list(q.queue)))
    cdb.sync_subscription_socket(css, cdb.DONE_PRIORITY)


def handle_sub_commit(css, sids, sub_flags):
    print("***Config updated --> Commit")
    processes = []
    q = SimpleQueue()
    for sid in sids:
        print("confirm-commit for subid {}".format(sid))
        p = Process(target=confirm_commit, args=(sid,q))
        processes.append(p)
        p.start()
    for process in processes:
        process.join()
    if not q.empty():
        sys.stderr.write("Confirm commit failed:\n{}\n".format(list(q.queue)))
    cdb.sync_subscription_socket(css, cdb.DONE_PRIORITY)


def handle_netconf_server_list(lock):
    crs = socket.socket()
    cdb.connect(crs, cdb.DATA_SOCKET, CONFD_ADDR, confd.CONFD_PORT)
    cds = socket.socket()
    cdb.connect(cds, cdb.DATA_SOCKET, CONFD_ADDR, confd.CONFD_PORT)
    css = socket.socket()
    cdb.connect(css, cdb.SUBSCRIPTION_SOCKET, CONFD_ADDR, confd.PORT)

    cdb.start_session2(crs, cdb.RUNNING, lock)
    cdb.start_session(cds, cdb.OPERATIONAL)
    num = cdb.num_instances(crs, SERVER_PATH)
    for i in range(num):
        sub_path = str(cdb.get(crs, "{}[{}]/subscription-path".format(SERVER_PATH,i)))
        sub_prio = int(cdb.get(crs, "{}[{}]/subscription-priority".format(SERVER_PATH,i)))
        sid = cdb.subscribe2(css, cdb.SUB_RUNNING_TWOPHASE, cdb.SUB_WANT_ABORT_ON_ABORT, sub_prio, 0, sub_path)
        cdb.set_elem(cds, str(sid), "{}[{}]/subscription-id".format(SERVER_PATH,i))
    cds.close()
    server_prio = int(cdb.get(crs, "{}/server-priority".format(CLIENT_PATH)))
    server_sid = cdb.subscribe(css, server_prio, 0, SERVER_PATH)
    crs.close()
    cdb.subscribe_done(css)
    return css, server_sid;


class SyncToAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        sub_points = []
        cds = socket.socket()
        cdb.connect(cds, cdb.DATA_SOCKET, CONFD_ADDR, confd.CONFD_PORT)
        cdb.start_session(cds, cdb.OPERATIONAL)
        if input.all.exists() or len(input.server) == 0:
            num = cdb.num_instances(cds, SERVER_PATH)
            for i in range(num):
                sub_point = int(cdb.get(cds, "{}[{}]/subscription-id".format(SERVER_PATH,i)))
                sub_points.append(sub_point)
            cdb.end_session(cds)
            cdb.trigger_subscriptions(cds, sub_points)
            result = "Synchronized the configuration with all NETCONF servers"
        else:
            server_names = input.server
            for server_name in server_names:
                sub_point = int(cdb.get(cds, "{0}{{{1}}}/subscription-id".format(SERVER_PATH, server_name)))
                sub_points.append(sub_point)
            cdb.end_session(cds)
            cdb.trigger_subscriptions(cds, sub_points)
            result = "Synchronized the configuration with {} NETCONF servers".format(server_names)
        cds.close()


def handle_sync_to():
    d = Daemon(name='syncd')
    a = []
    a.append(SyncToAction(daemon=d, actionpoint='sync-to'))
    d.start()
    return d


def run():
    #confd.set_debug(confd.TRACE, sys.stderr)
    (css, server_sid) = handle_netconf_server_list(cdb.LOCK_SESSION | cdb.LOCK_WAIT)
    d = handle_sync_to()
    try:
        while True:
            (type, sub_flags, sids) = cdb.read_subscription_socket2(css)
            if type == cdb.SUB_PREPARE:
                handle_sub_prepare(css,sids,sub_flags)
            if type == cdb.SUB_ABORT:
                handle_sub_abort(css, sids)
            if type == cdb.SUB_COMMIT:
                if sids[0] == server_sid:
                    (new_css, server_sid) = handle_netconf_server_list(0)
                    cdb.sync_subscription_socket(css, cdb.DONE_PRIORITY)
                    css.close()
                    css = new_css
                else:
                    handle_sub_commit(css, sids, sub_flags)
    except KeyboardInterrupt:
        print("\nCtrl-C pressed")
    finally:
        css.close()
        d.finish()


if __name__ == "__main__":
    run()
