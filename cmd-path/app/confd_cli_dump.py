#!/usr/bin/env python3
import confd
from confd.maapi import Maapi
import confd.maagic as maagic
import _confd
from bs4 import BeautifulSoup
import argparse

def tag2str(cs_node):
    return _confd.hash2str(cs_node.tag())


def prefix2str(cs_node):
    return _confd.ns2prefix(cs_node.ns())


def type2str(shallow_type):
    # Dictionary of a string representation for the shallow type (taken from the "confd_vtype" enum in confd_lib.h)
    Dict = {1: 'end marker', 2: 'presence container', 3: 'not yet used', 4: 'NUL-terminated strings', 5: 'string', 6: 'int8', 7: 'int16', 8: 'int32', 9: 'int64', 10: 'uint8', 11: 'uint16', 12: 'uint32', 13: 'uint64', 14: 'xs:float,xs:double', 15: 'inet:ipv4-address', 16: 'inet:ipv6-address', 17: 'boolean', 18: 'xs:QName', 19: 'yang:date-and-time', 20: 'xs:date', 23: 'xs:time', 27: 'enumeration', 29: 'bits size 32', 30: 'bits size 64', 31: 'leaf-list', 32: 'start of container or ist entry', 33: 'end of container or list entry', 34: 'instance-identifier', 35: 'union', 36: 'see cdb_get_values in confd_lib_cdb(3)', 37: 'list with CDB instance index', 38: 'yang:object-identifier', 39: 'binary', 40: 'inet:ipv4-prefix', 41: 'inet:ipv6-prefix', 42: 'default value indicator', 43: 'decimal64', 44: 'identityref', 45: 'deleted list entry', 46: 'yang:dotted-quad', 47: 'yang:hex-string', 48: 'tailf:ipv4-address-and-prefix-length', 49: 'tailf:ipv6-address-and-prefix-length', 50: 'bits size larger than 64', 51: 'OBU list entry moved or inserted first', 52: 'OBU list entry moved after'}
    return Dict[shallow_type]


def traverse_cs_nodes(curr_cs_node, path, cmd_path, curr_soup_tag, cmd_soup):
    # For all siblings
    for cs_node in maagic._CsNodeIter(curr_cs_node):
        new_curr_soup_tag = curr_soup_tag
        if cs_node.is_container() or cs_node.is_list() or cs_node.is_leaf_list() or cs_node.is_leaf():
            # Add the node tag name to the command
            new_path = path + "/{}:{}".format(prefix2str(cs_node), tag2str(cs_node))
            new_cmd_path = cmd_path + "{} ".format(tag2str(cs_node))
            # Get any tag annotations from the meta_data statements
            meta_data = cs_node.info().meta_data()
            if meta_data is not None:
                new_cmd_tag = new_params_tag = expose_key_name = alt_key_name= None;
                drop_node = False
                # For all meta_data statements
                for md in meta_data:
                    # Handle a select number of tailf extensions that change CLI commands vs the path
                    if md == "tailf:alt-name":
                        # Check if the alt-name is on a key or a non-key node
                        index = meta_data[md].find(':')
                        alt_name = meta_data[md]
                        if index != -1:
                            # Key
                            alt_key_name = alt_name[index+1:]
                        else:
                            # Non-key
                            new_cmd_path = new_cmd_path[0 : new_cmd_path.rindex(tag2str(cs_node))] + alt_name + " "
                    if md == "tailf:cli-drop-node-name":
                        drop_node = True
                        new_cmd_path = new_cmd_path[0 : new_cmd_path.rindex(tag2str(cs_node))]
                    if md == "tailf:cli-expose-key-name":
                        expose_key_name = meta_data[md]
                    # Handle CLI commands (identified by a tailf:meta-data "ID" in the YANG model)
                    if md.startswith("ID ") and drop_node == False:
                        if new_cmd_tag is None:
                            # Create the command tag for the CLI dump
                            new_cmd_tag = cmd_soup.new_tag("cmd", yname=new_cmd_path[:-1])
                            new_curr_soup_tag.append(new_cmd_tag)
                            # Add the YANG model "relative path" aka "xpath" or "keypath" without keys
                            new_xpath_tag = cmd_soup.new_tag("xpath")
                            new_xpath_tag.string = new_path
                            new_cmd_tag.append(new_xpath_tag)
                            # Add the source ID tag that can be used to find the command in tagged YANG model
                            new_source_tag = cmd_soup.new_tag("source")
                            new_source_tag.string = "{}".format(md)
                            new_cmd_tag.append(new_source_tag)
                        # Add the parameters to the command, i.e. YANG list keys.
                        if new_params_tag is None:
                            new_params_tag = cmd_soup.new_tag("params")
                            new_cmd_tag.append(new_params_tag)
                        mv = meta_data[md]
                        if mv is not None:
                            if mv == expose_key_name:
                                if alt_key_name is not None:
                                    new_param_tag = cmd_soup.new_tag("param", yname=alt_key_name)
                                else:
                                    new_param_tag = cmd_soup.new_tag("param", yname=mv)
                            else:
                                new_param_tag = cmd_soup.new_tag("param")
                            key_cs_node = _confd.cs_node_cd(cs_node, mv)
                            new_type_tag = cmd_soup.new_tag("type")
                            new_type_tag.string = type2str(key_cs_node.info().shallow_type())
                        else:
                            new_param_tag = cmd_soup.new_tag("param")
                            new_type_tag = cmd_soup.new_tag("type")
                            new_type_tag.string = type2str(cs_node.info().shallow_type())
                        new_param_tag.append(new_type_tag)
                        new_params_tag.append(new_param_tag)
                        if cs_node.is_container() or cs_node.is_list():
                            new_curr_soup_tag = new_cmd_tag
            if cs_node.children() is not None:
                if cs_node.is_list():
                    new_cmd_path = ""
                # If there are children, traverse them
                traverse_cs_nodes(cs_node.children(), new_path, new_cmd_path, new_curr_soup_tag, cmd_soup)
        elif cs_node.is_case():
            # Case statements will not be in the xpath/keypath or command. Traverse its children
            if cs_node.children() is not None:
                traverse_cs_nodes(cs_node.children(), path, cmd_path, new_curr_soup_tag, cmd_soup)


def cli_dump(root_path):
    # Get the ConfD schema (from YANG models) root node
    root_cs_node = _confd.cs_node_cd(None, root_path)
    # Create an empty BeautifulSoup object (XML document as a nested data structure)
    cmd_soup = BeautifulSoup('', "xml")
    # Add a root tag
    cmds_tag = cmd_soup.new_tag("cmds")
    cmd_soup.append(cmds_tag)
    # Traverse the schema and handle all tailf:meta-data/value statements with tags
    traverse_cs_nodes(root_cs_node, "", "", cmd_tag, cmd_soup)
    # Get a string representation of the resulting BeautifulSoup object
    cmd_soup_str = str(cmd_soup)
    # Change back temporary tags to the original ones
    cmd_soup_str = cmd_soup_str.replace('yname=', 'name=')
    # Print the raw XML to stdout
    print(cmd_soup_str)


def load_schemas():
    with Maapi():
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-r', '--root', nargs=1, type=str, default="/native",
                        help='<root> path to the first YANG node')
    args = parser.parse_args()
    load_schemas()
    cli_dump(args.root)
