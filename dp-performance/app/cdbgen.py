#!/usr/bin/env python

import sys
import time
import math
import random

def print_xml_routes_state(r_str):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://tail-f.com/ns/config/1.0">
  <sys xmlns="http://example.com/router-state">
    <routes>
      <inet>{}
      </inet>
    </routes>
  </sys>
</config>""".format(r_str))


def gen_state_routes_xml(n):
    r_str = ""

    m = int(math.ceil(n / 256.0));
    for i in range(0,m):
        if (n > 256):
            l = 256
        else:
            l = n
        for j in range(0,l):
            r_str += """
        <route>
          <name>10.{}.{}.0</name>
          <prefix-length>24</prefix-length>
          <description>route{}-{}</description>
          <next-hop>
            <name>192.168.{}.{}</name>
            <metric>100</metric>
          </next-hop>
        </route>""".format(i,j,i,j,i,j)
        n -= l
    print_xml_routes_state(r_str)


def print_xml_state(unit_str,serial_str,r_str,n_str):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://tail-f.com/ns/config/1.0">
  <sys xmlns="http://example.com/router-state">
    <interfaces>
      <interface>
        <name>eth0</name>
        <status>
          <link>up</link>
          <speed>thousand</speed>
          <duplex>full</duplex>
          <mtu>1500</mtu>
          <mac>AA:BB:CC:DD:EE:FF</mac>
          <receive>
            <bytes>1</bytes>
            <packets>2</packets>
            <errors>3</errors>
            <dropped>4</dropped>
          </receive>
          <transmit>
            <bytes>5</bytes>
            <packets>6</packets>
            <errors>7</errors>
            <dropped>8</dropped>
            <collisions>9</collisions>
          </transmit>
        </status>{}
      </interface>{}
    </interfaces>
    <routes>
      <inet>{}
      </inet>
    </routes>
    <ntp>{}
      <local-clock>
        <status>
          <state>falsetick</state>
          <stratum>1</stratum>
          <reach>2</reach>
          <delay>3</delay>
          <offset>4</offset>
          <jitter>5</jitter>
        </status>
      </local-clock>
    </ntp>
  </sys>
</config>""".format(unit_str,serial_str,r_str,n_str))


def gen_state_xml(n):
    unit_str = ""
    serial_str = ""
    r_str = ""
    n_str = ""

    m = int(math.ceil(n / 256.0));
    for i in range(0,m):
        if (n > 256):
            l = 256
        else:
            l = n
        for j in range(0,l):
            unit_str += """
        <unit>
          <name>{0}</name>
          <status>
            <receive>
              <bytes>{0}</bytes>
              <packets>{0}</packets>
              <errors>{0}</errors>
              <dropped>{0}</dropped>
            </receive>
            <transmit>
              <bytes>{0}</bytes>
              <packets>{0}</packets>
              <errors>{0}</errors>
              <dropped>{0}</dropped>
              <collisions>{0}</collisions>
            </transmit>
          </status>
        </unit>""".format((i+1)*(j+1))
            serial_str += """
      <serial xmlns="http://example.com/example-serial-state">
        <name>ppp{0}</name>
        <status>
          <receive>
            <bytes>{0}</bytes>
            <packets>{0}</packets>
            <errors>{0}</errors>
            <dropped>{0}</dropped>
          </receive>
          <transmit>
            <bytes>{0}</bytes>
            <packets>{0}</packets>
            <errors>{0}</errors>
            <dropped>{0}</dropped>
            <collisions>{0}</collisions>
          </transmit>
        </status>
      </serial>""".format(((i+1)*(j+1)))
            r_str += """
        <route>
          <name>10.{}.{}.0</name>
          <prefix-length>24</prefix-length>
          <description>route{}-{}</description>
          <next-hop>
            <name>192.168.{}.{}</name>
            <metric>100</metric>
          </next-hop>
        </route>""".format(i,j,i,j,i,j)
            n_str += """
      <server>
        <name>10.2.{}.{}</name>
        <status>
          <state>outlyer</state>
          <stratum>{}</stratum>
          <reach>377</reach>
          <delay>{}</delay>
          <offset>{}</offset>
          <jitter>{}</jitter>
        </status>
      </server>""".format(i,j,random.randrange(15),random.randrange(2^31-1),random.randrange(2^31-1),random.randrange(2^31-1))
        n -= l
    print_xml_state(unit_str,serial_str,r_str,n_str)


def print_xml_config(unit_str, serial_str, s_str, n_str, d_str):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://tail-f.com/ns/config/1.0">
  <sys xmlns="http://example.com/router">
    <interfaces>
      <interface>
        <name>eth0</name>{}
      </interface>{}
    </interfaces>
    <syslog>{}
    </syslog>
    <ntp>{}
      <local-clock>
        <enabled>true</enabled>
        <stratum>15</stratum>
      </local-clock>
      <restrict>
        <name>1.1.1.1</name>
        <mask>default</mask>
        <flag>ntpport</flag>
      </restrict>
      <key>
        <name>2</name>
      </key>
      <controlkey>2</controlkey>
    </ntp>
    <dns>{}
    </dns>
  </sys>
</config>""".format(unit_str, serial_str, s_str,n_str,d_str))


def gen_cfg_xml(n):
    unit_str = ""
    serial_str = ""
    s_str = ""
    n_str = ""
    d_str = ""

    m = int(math.ceil(n / 256.0));
    for i in range(0,m):
        if (n > 256):
            l = 256
        else:
            l = n
        for j in range(0,l):
            unit_str += """
        <unit>
          <name>{}</name>
          <enabled>true</enabled>
          <family>
            <inet>
              <address>
                <name>192.{}.{}.0</name>
                <prefix-length>24</prefix-length>
              </address>
            </inet>
          </family>
        </unit>""".format(((i+1)*(j+1)),i,j)
            serial_str += """
      <serial xmlns="http://example.com/example-serial">
        <name>ppp{}</name>
        <ppp>
          <accounting>acme</accounting>
        </ppp>
        <authentication>
          <method>pap</method>
        </authentication>
        <authorization>admin</authorization>
      </serial>""".format(((i+1)*(j+1)))
            s_str += """
      <server>
        <name>10.3.{}.{}</name>
        <enabled>true</enabled>
        <selector>
          <name>8</name>
          <facility>auth</facility>
          <facility>authpriv</facility>
          <facility>local0</facility>
        </selector>
        <administrator>admin{}-{}</administrator>
      </server>""".format(i,j,i,j)
            n_str += """
      <server>
        <name>10.2.{}.{}</name>
        <key>2</key>
      </server>""".format(i,j)
            d_str += """
      <server>
        <address>10.2.{}.{}</address>
      </server>""".format(i,j)
        n -= l
    print_xml_config(unit_str,serial_str,s_str,n_str,d_str)

def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)

if sys.argv[1]=="gen-cfg":
    gen_cfg_xml(parse_num(sys.argv[2]))
elif sys.argv[1]=="gen-state":
    gen_state_xml(parse_num(sys.argv[2]))
elif sys.argv[1]=="gen-cfg-routes":
    gen_cfg_routes_xml(parse_num(sys.argv[2]))
elif sys.argv[1]=="gen-state-routes":
    gen_state_routes_xml(parse_num(sys.argv[2]))
else:
    print("Unrecognized command %s").format(sys.argv)
