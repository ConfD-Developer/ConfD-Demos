#!/usr/bin/env python

import sys
import time
import math

def print_hello():
    print("""<?xml version="1.0" encoding="UTF-8"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <capabilities>
    <capability>urn:ietf:params:netconf:base:1.0</capability>
  </capabilities>
</hello>""")

def print_delim():
    print("""]]>]]>""")

def print_close_session(mid):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="%s">
  <close-session/>
</rpc>
    """%(mid))

def print_commit(mid):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="%s">
  <commit/>
</rpc>"""%(mid))

def print_edit_config(op_str, data_store, mid):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="%s">
  <edit-config>
    <target>
      <%s/>
    </target>
    <config>
      <router xmlns="http://tail-f.com/ns/example/routing">
        <static>
          <address-family>
            <ipv4>
              <unicast>%s
              </unicast>
            </ipv4>
          </address-family>
        </static>
      </router>
    </config>
  </edit-config>
</rpc>"""%(mid, data_store, op_str))

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

def trans_size_edit_config(n, data_store):
    print_hello()
    print_delim()
    str = ""
    m = int(math.ceil(n / 256.0));
    for i in range(0,m):
        if (n > 256):
            l = 256
        else:
            l = n
        for j in range(0,l):
            str += """
                <destination>
                  <prefix>192.%d.%d.0/24</prefix>
                  <nexthop>172.16.1.2</nexthop>
                </destination>"""%(i,j)
        n -= l
    print_edit_config(str, data_store, 1)
    print_delim()
    if (data_store == "candidate" ):
        #print_commit(2)
        #print_delim()
        #print_close_session(3)
        # commit done in TC A3 through netconf-console
        print_close_session(2)
    else:
        print_close_session(2)
    print_delim()

def trans_delete_edit_config(data_store):
    print_hello()
    print_delim()
    print("""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
  <edit-config>
    <target>
      <%s/>
    </target>
    <config>
      <router xmlns="http://tail-f.com/ns/example/routing" nc:operation="delete"/>
    </config>
  </edit-config>
</rpc>"""%(data_store))
    print_delim()
    if (data_store == "candidate" ):
        print_commit(2)
        print_delim()
        print_close_session(3)
    else:
        print_close_session(2)
    print_delim()
    
def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)

if sys.argv[1]=="trans_size_edit_config_running":
    trans_size_edit_config(parse_num(sys.argv[2]), "running")
elif sys.argv[1]=="trans_size_edit_config_candidate":
    trans_size_edit_config(parse_num(sys.argv[2]), "candidate")
elif sys.argv[1]=="trans_delete_edit_config_candidate":
    trans_delete_edit_config("candidate")
else:    
    print("Unrecognized command '%s'"%sys.argv)
