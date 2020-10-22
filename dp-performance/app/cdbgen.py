#!/usr/bin/env python
import sys
import math
import ipaddress

def print_xml(unit_str, serial_str, r_str, s_str, n_str, d_str, prefix):
    print("""<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://tail-f.com/ns/config/1.0">
  <sys xmlns="http://example.com/router{}">
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
    <syslog>{}
    </syslog>
    <ntp>{}
      <local-clock>
        <enabled>true</enabled>
        <stratum>15</stratum>
        <status>
          <state>falsetick</state>
          <stratum>1</stratum>
          <reach>2</reach>
          <delay>3</delay>
          <offset>4</offset>
          <jitter>5</jitter>
        </status>
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
    <dns>
      <search>
        <name>1</name>
        <domain>tail-f.com</domain>
      </search>
      <search>
        <name>2</name>
        <domain>tail-f.com</domain>
      </search>
      <search>
        <name>3</name>
        <domain>tail-f.com</domain>
      </search>{}
    </dns>
  </sys>
</config>""".format(prefix,unit_str,serial_str,r_str,s_str,n_str,d_str))


def gen_xml(n, prefix):
    unit_str = ""
    serial_str = ""
    r_str = ""
    s_str = ""
    n_str = ""
    d_str = ""
    prefixstr = str(ipaddress.IPv4Address(u'1.0.0.0'))
    ipstr = str(ipaddress.IPv4Address(u'1.0.0.1'))
    for i in range(0,n):
        unit_str += """
        <unit>
          <name>{0}</name>
          <enabled>true</enabled>
          <family>
            <inet>
              <address>
                <name>{1}</name>
                <prefix-length>24</prefix-length>
              </address>
            </inet>
          </family>
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
        </unit>""".format(i,prefixstr)
        serial_str += """
      <serial xmlns="http://example.com/example-serial{0}">
        <name>ppp{1}</name>
        <ppp>
          <accounting>acme</accounting>
        </ppp>
        <authentication>
          <method>pap</method>
        </authentication>
        <authorization>admin</authorization>
        <multilink>
          <links>
            <minimum>
              <minimum-value>0</minimum-value>
              <mandatory/>
            </minimum>
          </links>
          <group>1</group>
          <fragment>
            <delay>
              <delay-value>256</delay-value>
              <additional-delay-value>65535</additional-delay-value>
            </delay>
          </fragment>
        </multilink>
        <status>
          <receive>
            <bytes>{1}</bytes>
            <packets>{1}</packets>
            <errors>{1}</errors>
            <dropped>{1}</dropped>
          </receive>
          <transmit>
            <bytes>{1}</bytes>
            <packets>{1}</packets>
            <errors>{1}</errors>
            <dropped>{1}</dropped>
            <collisions>{1}</collisions>
          </transmit>
        </status>
      </serial>""".format(prefix,i)
        r_str += """
        <route>
          <name>{0}</name>
          <prefix-length>24</prefix-length>
          <description>route{1}</description>
          <next-hop>
            <name>{0}</name>
            <metric>100</metric>
          </next-hop>
        </route>""".format(ipstr,i)
        s_str += """
      <server>
        <name>{0}</name>
        <enabled>true</enabled>
        <selector>
          <name>{1}</name>
          <facility>auth</facility>
          <facility>authpriv</facility>
          <facility>local0</facility>
        </selector>
        <administrator>admin{1}</administrator>
      </server>""".format(ipstr,i)
        n_str += """
      <server>
        <name>nserver{0}</name>
        <key>2</key>
        <status>
          <state>outlyer</state>
          <stratum>15</stratum>
          <reach>377</reach>
          <delay>{1}</delay>
          <offset>{1}</offset>
          <jitter>{1}</jitter>
        </status>
      </server>""".format(ipstr,i)
        d_str += """
      <server>
        <address>{}</address>
      </server>""".format(ipstr)
        prefixint = int(ipaddress.IPv4Address(u'{}'.format(prefixstr)))
        prefixint += 256
        prefixstr = str(ipaddress.IPv4Address(prefixint))
        ipint = int(ipaddress.IPv4Address(u'{}'.format(ipstr)))
        ipint += 1
        ipstr = str(ipaddress.IPv4Address(ipint))
    print_xml(unit_str,serial_str,r_str,s_str,n_str,d_str,prefix)


def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)


if sys.argv[1]=="gen":
    gen_xml(parse_num(sys.argv[2]), "")
elif sys.argv[1]=="gen-state":
    gen_xml(parse_num(sys.argv[2]), "-state")
else:
    print("Unrecognized command %s").format(sys.argv)
