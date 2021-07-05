#!/usr/bin/env python3
import argparse
import os
import subprocess
from bs4 import BeautifulSoup
from pathlib import Path


def append_md_val(node_stmt, md, mv, yin_soup):
    new_md_stmt = yin_soup.new_tag("tailf_prefix_meta-data")
    new_value_stmt = yin_soup.new_tag("tailf_prefix_value")
    new_value_stmt.string = "{}".format(md)
    new_md_stmt.append(new_value_stmt)
    if mv is not None:
        new_mv_stmt = yin_soup.new_tag("tailf_prefix_meta-value", value="{}".format(mv))
        new_md_stmt.append(new_mv_stmt)
    node_stmt.append(new_md_stmt)


def append_md(node_stmt, md, mv, yin_soup):
    if node_stmt.parent is not None and node_stmt.parent.name == "list":
        key_stmt = node_stmt.find_previous_sibling('key')
        if key_stmt is not None and node_stmt['yname'] in key_stmt['value']:
                if mv is None:
                    append_md_val(node_stmt.parent, md, node_stmt['yname'], yin_soup)
                else:
                    append_md_val(node_stmt.parent, md, "{}:{}".format(node_stmt['yname'], mv), yin_soup)
        else:
            append_md_val(node_stmt, md, mv, yin_soup)
    else:
        append_md_val(node_stmt, md, mv, yin_soup)


def tailf_info_path(yang_file):
    if "CONFD_DIR" in os.environ:
        confd_dir = os.environ['CONFD_DIR']
    else:
        sys.stderr.write('error: Where is ConfD installed? Set CONFD_DIR to point it out!\n')
    # Get the yang_path and the yang_filename to write the result to.
    yang_file_path = yang_file.rsplit('/', 1)
    if len(yang_file_path) < 2:
        yang_path = "./"
        yang_filename = yang_file
    else:
        yang_path = yang_file_path[0]
        yang_filename = yang_file_path[1]
    # Convert the YANG file to YIN XML format
    result = subprocess.run(['python3', '/usr/local/bin/pyang', '-f', 'yin',
                            '-p', yang_path, '-p', confd_dir + "/src/confd/yang", yang_file],
                            stdout=subprocess.PIPE, encoding='utf-8')
    yin_content = result.stdout
    # Temporarily replace some tags that cause issues for BeautifulSoup
    yin_content = yin_content.replace('tailf:', 'tailf_prefix_')
    yin_content = yin_content.replace('name=', 'yname=')
    yin_content = yin_content.replace('leaf-list', 'leaflist')
    yin_content = yin_content.replace('tailf_prefix_meta-data', 'tailf_prefix_metadata')
    yin_content = yin_content.replace('tailf_prefix_alt-name', 'tailf_prefix_alt_name')
    yin_content = yin_content.replace('tailf_prefix_cli-drop-node-name', 'tailf_prefix_cli_drop_node_name')
    yin_content = yin_content.replace('tailf_prefix_cli-expose-key-name', 'tailf_prefix_cli_expose_key_name')
    yin_content = yin_content.replace('xmlns:', 'xmlns_')
    # Create a BeautifulSoup object (YIN XML document as a nested data structure)
    yin_soup = BeautifulSoup(yin_content, "xml")
    # Get the namespace prefix for the YANG model
    nsprefix = yin_soup.find('prefix')
    # Remove any existing tailf:meta-data statements from the original YANG model
    md_stmt = None
    for md_stmt in yin_soup.find_all('tailf_prefix_metadata'):
        if md_stmt.parent is not None:
            md_stmt.decompose()
    # Append tailf:meta-data statements with relevant tailf extension tags
    for tailf_alt_ext in yin_soup.find_all('tailf_prefix_alt_name'):
        append_md(tailf_alt_ext.parent, tailf_alt_ext.name, tailf_alt_ext['yname'], yin_soup)
    for tailf_cli_drop_ext in yin_soup.find_all('tailf_prefix_cli_drop_node_name'):
        append_md(tailf_cli_drop_ext.parent, tailf_cli_drop_ext.name, None, yin_soup)
    for tailf_cli_expose_key_ext in yin_soup.find_all('tailf_prefix_cli_expose_key_name'):
        append_md(tailf_cli_expose_key_ext.parent, tailf_cli_expose_key_ext.name, None, yin_soup)
    # Find all leaf, leaf-list, and container statements
    # Append tailf:meta-data statements with id tags
    id = 0
    for leaf_stmt in yin_soup.find_all('leaf'):
        append_md(leaf_stmt, "ID {}:{}".format(nsprefix['value'], id), None, yin_soup)
        id += 1
    for leaf_list_stmt in yin_soup.find_all('leaflist'):
        append_md(leaf_list_stmt, "ID {}:{}".format(nsprefix['value'], id), None, yin_soup)
        id += 1
    for container_stmt in yin_soup.find_all('container'):
        if container_stmt.find("presence", recursive=False) is not None:
            append_md(container_stmt, "ID {}:{}".format(nsprefix['value'], id), None, yin_soup)
            id += 1
    # Change back the temporary tags to the original ones
    yin_soup_str = str(yin_soup)
    yin_soup_str = yin_soup_str.replace('tailf_prefix_', 'tailf:')
    yin_soup_str = yin_soup_str.replace('tailf:alt_name', 'tailf:alt-name')
    yin_soup_str = yin_soup_str.replace('tailf:cli_drop_node_name', 'tailf:cli-drop-node-name')
    yin_soup_str = yin_soup_str.replace('tailf:cli_expose_key_name', 'tailf:cli-expose-key-name')
    yin_soup_str = yin_soup_str.replace('yname=', 'name=')
    yin_soup_str = yin_soup_str.replace('leaflist', 'leaf-list')
    yin_soup_str = yin_soup_str.replace('xmlns_', 'xmlns:')
    # Convert back to YANG from the YIN XML format and print the tagged YANG model file
    result = subprocess.run(['python3', '/usr/local/bin/pyang', '-f',
                            'yang', '-p', yang_path, '-p', confd_dir],
                            stdout=subprocess.PIPE, input=yin_soup_str,
                            encoding='utf-8')
    print(str(result.stdout))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('filename', nargs=1, type=str,
                        help='<file> YANG module filename that end with ".yang"')
    args = parser.parse_args()
    tailf_info_path(args.filename[0])
