#!/usr/bin/env python

import sys
import time

def print_sync_cfg(op_str):
    print("""<config xmlns="http://tail-f.com/ns/config/1.0">
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <aacluster xmlns="http://tail-f.com/ns/example/aacluster/1.0">{}
    </aacluster>
    </active-cfg>
    </config>
    """.format(op_str))

def gen_join_cfg(b,l,m):
    str = ""
    str += """
        <init-nodeid>%d</init-nodeid>

        <node>
        <nodeid>%d</nodeid>
        <ip>127.0.0.1</ip>
        <port>%d</port>
        </node>

        <node>
        <nodeid>%d</nodeid>
        <ip>127.0.0.1</ip>
        <port>%d</port>
        </node>
        """%((m),(m),(b+(10*m)),(l),(b+(10*l)))
    print_sync_cfg(str)
    
def gen_sync_cfg(b,n,m):
    str = ""
    str += """
        <init-nodeid>%d</init-nodeid>
    """%(m)
    for i in range(0,n):
        str += """
        <node>
        <nodeid>%d</nodeid>
        <ip>127.0.0.1</ip>
        <port>%d</port>
        </node>
        """%((i),(b+(10*i)))
    print_sync_cfg(str)

def print_data(op_str):
    print("""<config xmlns="http://tail-f.com/ns/config/1.0">
    <active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <routes>{}
    </routes>
    </active-cfg>
    </config>
    """.format(op_str))
    
def gen_data(l):
    str = ""
    for i in range(0,l):
        str += """
        <route>
            <id>%07d</id>
            <leaf1>1</leaf1>
            <leaf2>2</leaf2>
            <leaf3>3</leaf3>
            <leaf4>4</leaf4>
        </route>
        """%(i)
    print_data(str)

def gen_data_seed(l, m):
    str = ""
    for i in range(0,l):
        str += """
        <route>
            <id>%07d</id>
            <leaf1>%d</leaf1>
            <leaf2>%d</leaf2>
            <leaf3>%d</leaf3>
            <leaf4>%d</leaf4>
        </route>
        """%((i),(i+m+1),(i+m+2),(i+m+3),(i+m+4))
    print_data(str)
    
def print_raw(op_str):
    print("""</active-cfg xmlns="http://tail-f.com/ns/example/routes/1.0">
    <routes>{}
    </routes>
    </active-cfg>
    """.format(op_str))
    
def gen_raw(l):
    str = ""
    for i in range(0,l):
        str += """
        <route>
            <id>%07d</id>
            <leaf1>1</leaf1>
            <leaf2>2</leaf2>
            <leaf3>3</leaf3>
            <leaf4>4</leaf4>
        </route>
        """%(i)
    print_raw(str)    
    
def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)

if sys.argv[1]=="gen_data":
    gen_data(parse_num(sys.argv[2]))
elif sys.argv[1]=="gen_raw":
    gen_raw(parse_num(sys.argv[2]))
elif sys.argv[1]=="gen_data_seed":
    gen_data_seed(parse_num(sys.argv[2]), parse_num(sys.argv[3]))
elif sys.argv[1]=="gen_sync_cfg":
    gen_sync_cfg(parse_num(sys.argv[2]), parse_num(sys.argv[3]), parse_num(sys.argv[4]))
elif sys.argv[1]=="gen_join_cfg":
    gen_join_cfg(parse_num(sys.argv[2]), parse_num(sys.argv[3]), parse_num(sys.argv[4]))
else:    
    print("Unrecognized command '{}'".format(sys.argv))

