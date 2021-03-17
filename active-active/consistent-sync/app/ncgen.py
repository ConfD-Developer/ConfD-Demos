#!/usr/bin/env python

import sys
import time

def print_hello():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
    <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
    </capabilities>
    </hello>
    """)

def print_delim():
    print ("""]]>]]>
    """)

def print_close_session():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
    <close-session/>
    </rpc>
    """)

def print_commit():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
    <commit/>
    </rpc>
    """)
    
def print_commit_persist_id(pid):
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <commit><persist-id>{}</persist-id></commit>
    </rpc>
    """.format(pid))
    
def print_confirmed_commit_persist(pid):
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="3">
    <commit><confirmed/><persist>{}</persist></commit>
    </rpc>
    """.format(pid))
    
def print_close_session2():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="5">
    <close-session/>
    </rpc>
    """)

def print_close_session3():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="3">
    <close-session/>
    </rpc>
    """)
    
def print_delete_config(op_str, data_store="running"):
    print( """<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <edit-config>
    <target>
    <%s/>
    </target>
    <config>
    {}</config>
    </edit-config>
    </rpc>
    """.format(data_store, op_str))
    
def print_edit_config(op_str, data_store="running"):
    print("""<?xml version="1.0" encoding="UTF-8"?><rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1"><edit-config><target><{}/></target><config><active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0"><routes>{}</routes></active-cfg></config></edit-config></rpc>""".format(data_store, op_str))

def print_delete_edit_config(op_str, data_store="running"):
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <edit-config>
    <target>
    <{}/>
    </target>
    <config>
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <routes nc:operation="delete"/>
    </active-cfg>
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <routes>
    {}</routes>
    </active-cfg>
    </config>
    </edit-config>
    </rpc>
    """.format(data_store, op_str))

def print_lock_running():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <lock><target><running/></target></lock>
    </rpc>
    """)
def print_unlock_running():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
    <unlock><target><running/></target></unlock>
    </rpc>
    """)

def print_partial_lock_running():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <nc:rpc xmlns="urn:ietf:params:xml:ns:netconf:partial-lock:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <partial-lock>
      <select xmlns:r="http://tail-f.com/ns/example/routes/1.0">
        /r:active-cfg/r:routes/r:route[id='0000000']
      </select>
      <select xmlns:r="http://tail-f.com/ns/example/routes/1.0">
        /r:active-cfg/r:routes/r:route[r:id='0000001']
      </select>
    </partial-lock>
</nc:rpc>
    """)
def print_partial_unlock_running(id):
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <nc:rpc xmlns="urn:ietf:params:xml:ns:netconf:partial-lock:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
      <partial-unlock>
        <lock-id>{}</lock-id>
      </partial-unlock>
    </nc:rpc>
    """.format(id))
    
def print_lock_candidate():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <lock><target><candidate/></target></lock>
    </rpc>
    """)
def print_unlock_candidate():
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="4">
    <unlock><target><candidate/></target></unlock>
    </rpc>
    """)
    
def print_edit_config2(op_str, data_store="candidate"):
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
    <edit-config>
    <target>
    <{}/>
    </target>
    <config>
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <routes>
    {}</routes>
    </active-cfg>
    </config>
    </edit-config>
    </rpc>
    """.format(data_store, op_str))

def print_copy_config(op_str, data_store="running"):
    print("""<?xml version="1.0" encoding="UTF-8"?>
    <rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <copy-config>
    <target>
    <{}/>
    </target>
    <source>
    <config>
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <routes>
    {}</routes>
    </active-cfg>
    </config>
    </source>
    </copy-config>
    </rpc>
    """.format(data_store, op_str))

def dot_notation(num,length=4):
    str = ""
    for i in range(0,length):
        n = num%256
        if str:
            str = "%d.%s"%(n,str)
        else:
            str = "%d"%n
        num /= 256
    return str

def delete_routes_config():
    print_hello()
    print_delim()
    str = ""
    str += """
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0"><routes nc:operation="delete"/></active-cfg>"""
    print_delete_config(str)
    print_delim()
    print_close_session()
    print_delim()

def edit_delete_routes_config(n):
    print_hello()
    print_delim()
    str = ""
    for i in range(0,n):
        str += """
        <route>
        <id>%07d</id>
        <leaf1>1</leaf1>
        <leaf2>2</leaf2>
        <leaf3>3</leaf3>
        <leaf4>4</leaf4>
        </route>"""%(i)
    print_delete_edit_config(str)
    print_delim()
    print_close_session()
    print_delim()
        
# alternative - do edit-config on running create each elemens
def edit_config_running(n):
    print_hello()
    print_delim()
    str = ""
    for i in range(0,n):
        str += """<route><id>%07d</id><leaf1>1</leaf1><leaf2>2</leaf2><leaf3>3</leaf3><leaf4>4</leaf4></route>"""%(i)
    print_edit_config(str)
    print_delim()
    print_close_session()
    print_delim()

# alternative - do edit-config on candidate, create each elemens, end with commit
def edit_config_candidate_confirmed_commit(n,pid):
    print_hello()
    print_delim()
    print_lock_candidate()
    print_delim()
    str = ""
    for i in range(0,n):
        str += """
        <route>
        <id>%07d</id>
        <leaf1>1</leaf1>
        <leaf2>2</leaf2>
        <leaf3>3</leaf3>
        <leaf4>4</leaf4>
        </route>"""%(i)
    print_edit_config2(str)
    print_delim()
    print_confirmed_commit_persist(pid)
    print_delim()
    print_unlock_candidate()
    print_delim()
    print_close_session2()
    print_delim()

def confirm_commit(pid):
    print_hello()
    print_delim()
    print_commit_persist_id(pid)
    print_delim()
    print_close_session()
    print_delim()

# alternative - do copy_config
def trans_size_test3(n):
    print_hello()
    print_delim()
    str = ""
    for i in range(0,n):
        str += """
        <route>
        <id>%07d</id>
        <leaf1>1</leaf1>
        <leaf2>2</leaf2>
        <leaf3>3</leaf3>
        <leaf4>4</leaf4>
        </route>"""%(i)
    print_copy_config(str)
    print_delim()
    print_close_session()
    print_delim()

def lock_unlock_running():
    print_hello()
    print_delim()
    print_lock_running()
    print_delim()
    print_unlock_running()
    print_delim()
    print_close_session3()
    print_delim()

def partial_lock_unlock_running(id):
    print_hello()
    print_delim()
    print_partial_lock_running()
    print_delim()
    print_partial_unlock_running(id)
    print_delim()
    print_close_session3()
    print_delim()

def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)

if sys.argv[1]=="edit_config_running":
    edit_config_running(parse_num(sys.argv[2]))
elif sys.argv[1]=="edit_config_candidate_confirmed_commit":
    edit_config_candidate_confirmed_commit(parse_num(sys.argv[2]),sys.argv[3])
elif sys.argv[1]=="trans_many_test":
    trans_many_test(parse_num(sys.argv[2]))
elif sys.argv[1]=="delete_routes_config":
    delete_routes_config()
elif sys.argv[1]=="edit_delete_routes_config":
    edit_delete_routes_config(parse_num(sys.argv[2]))
elif sys.argv[1]=="confirm_commit":
    confirm_commit(sys.argv[2])
elif sys.argv[1]=="lock_running":
    lock_unlock_running()
elif sys.argv[1]=="partial_lock_running":
    partial_lock_unlock_running(parse_num(sys.argv[2]))
else:    
    print("Unrecognized command '{}'".format(sys.argv))
    
