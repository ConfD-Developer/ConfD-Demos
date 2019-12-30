#!/usr/bin/env python

import sys
import time
import math

def print_plain_patch_config(op_str):
    print("""<data>
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
</data>"""%(op_str))
    
def trans_size_plain_patch_running(n):
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
    print_plain_patch_config(str)    
    
def parse_num(str):
    if str[:2] == '2^':
        return pow(2,parse_num(str[2:]))
    return int(str)

if sys.argv[1]=="trans_size_plain_patch_running":
    trans_size_plain_patch_running(parse_num(sys.argv[2]))
else:
    print("Unrecognized command '%s'"%sys.argv)
    

