#!/usr/bin/env python

import sys
import time

def print_stats(op_str):
    print("""<config xmlns="http://tail-f.com/ns/config/1.0">
  <routes xmlns="http://tail-f.com/ns/example/routes/1.0">%s
  </routes>
</config>
    """%(op_str))

def gen_route_stats(n):
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
    print_stats(str)

def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)

gen_route_stats(parse_num(sys.argv[1]))
