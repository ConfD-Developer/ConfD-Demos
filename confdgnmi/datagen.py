#!/usr/bin/env python

import sys


def gen_intf(name):
    interface = """<interface xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0"
               ns0:operation="create">
        <name>{}</name>  
        <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
            gigabitEthernet
        </type>             
    </interface>
    """.format(name)
    return interface


def ifname(index):
    return "cp_ont_{}".format(index)


def parse_num(str):
    if str[:2] == '2^':
        return pow(2, parse_num(str[2:]))
    return int(str)


interfaces = parse_num(sys.argv[1])

interfaces_str = ""
for i in range(interfaces):
    interfaces_str += gen_intf(ifname(i + 1))

with open("init_interfaces.xml", "w") as init_file:
    interfaces_file = """<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    {}</interfaces>""".format(interfaces_str)
    init_file.write(interfaces_file)
