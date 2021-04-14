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


def gen_intf_state(name):
    interface = """<interface xmlns:ns0="urn:ietf:params:xml:ns:netconf:base:1.0">
        <name>{}</name>
        <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">
            gigabitEthernet
        </type>
    </interface>
    """.format(name)
    return interface


def ifname(index):
    return "if_{}".format(index)


def parse_num(str):
    if str[:2] == '2^':
        return pow(2, parse_num(str[2:]))
    return int(str)


interfaces = parse_num(sys.argv[1])

interfaces_str = ""
interfaces_state_str = ""
for i in range(interfaces):
    interfaces_str += gen_intf(ifname(i + 1))
    interfaces_state_str += gen_intf_state("state_" + ifname(i + 1))

with open("init_interfaces.xml", "w") as init_file:
    interfaces_file = """<config xmlns="http://tail-f.com/ns/config/1.0">
    <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    {}</interfaces>
    </config>""".format(interfaces_str)
    init_file.write(interfaces_file)

with open("init_interfaces_state.xml", "w") as init_file:
    interfaces_file = """<config xmlns="http://tail-f.com/ns/config/1.0">
    <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    {}</interfaces-state>
     </config>""".format(interfaces_state_str)
    init_file.write(interfaces_file)
