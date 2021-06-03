#!/usr/bin/env python3
import argparse
import os
import subprocess
from bs4 import BeautifulSoup
import re
from datetime import datetime
import copy
import sys
from pathlib import Path


def gen_ann_module(name, ns, prefix):
    revdate = datetime.today().strftime('%Y-%m-%d')
    str = """<?xml version="1.0" encoding="utf-8"?>
<module>
  <namespace uri="{}-ann"/>
  <prefix value="{}-ann"/>
  <import module="tailf-common">
    <prefix value="tailf"/>
  </import>
  <revision date="{}">
    <description>
      <text>Initial revision</text>
    </description>
  </revision>
  <tailf_prefix_annotate_module module_name="{}"/>
</module>""".format(ns,prefix,revdate,name)
    return str


def add_stmt(node, ann_node, ann_soup):
    if node.parent.name == "module" or node.parent.name == "submodule":
        return ann_node
    elif node.parent.name == "augment":
        parent_ann_node = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(node.parent.name, node.parent['target_node']))
    #elif node.parent.name == "when":
    #    parent_ann_node = ann_soup.new_tag("tailf:annotate-statement", statement_path="when")
    else:
        if not node.parent.attrs:
            parent_ann_node = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}".format(node.parent.name))
        else:
            parent_ann_node = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[{}=\'{}\']".format(node.parent.name,
   													     next(iter(node.parent.attrs)),
													     next(iter(node.parent.attrs.values()))))
    parent_ann_node.append(ann_node)
    return add_stmt(node.parent, parent_ann_node, ann_soup)


def tailf_ann_stmt(parse_must_stmt, parse_when_stmt, parse_min_elem_stmt,
                   parse_max_elem_stmt, parse_mandatory_stmt, parse_unique_stmt,
                   parse_pattern_stmt, parse_tailf_stmt, parse_callpoint_stmt,
                   parse_validate_stmt, sanitize, out_path, yang_file):
    if "CONFD_DIR" in os.environ:
        confd_dir = os.environ['CONFD_DIR']
    else:
        sys.stderr.write('error: Where is ConfD installed? Set CONFD_DIR to point it out!\n')
    yang_file_path = yang_file.rsplit('/', 1)
    if len(yang_file_path) < 2:
        yang_path = "./"
        yang_filename = yang_file
    else:
        yang_path = yang_file_path[0]
        yang_filename = yang_file_path[1]
    ann_filename = "{}-ann.yang".format(yang_filename.rsplit('.', 1)[0])
    result = subprocess.run(['python3', '/usr/local/bin/pyang', '-f', 'yin',
                            '-p', yang_path, '-p', confd_dir, yang_file],
                            stdout=subprocess.PIPE, encoding='utf-8')
    yin_content = result.stdout
    yin_content = yin_content.replace('tailf:', 'tailf_prefix_')
    yin_content = yin_content.replace('name=', 'yname=')
    yin_content = yin_content.replace('target-node=', 'target_node=')
    yin_content = yin_content.replace('xmlns:', 'xmlns_')
    yin_soup = BeautifulSoup(yin_content, "xml")
    if yin_soup.module is not None:
        annotate_module = gen_ann_module(yang_filename.rsplit('.', 1)[0],
                                         yin_soup.module.find('namespace')['uri'],
                                         yin_soup.module.find('prefix')['value'])
    elif yin_soup.submodule is not None:
        prefix = yin_soup.submodule.find('prefix')['value']
        annotate_module = gen_ann_module(yang_filename.rsplit('.', 1)[0],
                                         yin_soup.submodule["xmlns_{}".format(prefix)],
                                         prefix)
    else:
        print("Error: Unknown module type. Neither a YANG module or submodule")
        return
    ann_soup = BeautifulSoup(annotate_module, "xml")
    tailf_extension = None
    must_stmt = None
    when_stmt = None
    callpoint_stmt = None
    validate_stmt = None
    if parse_must_stmt is True:
        for must_stmt in yin_soup.find_all('must'):
            if must_stmt.parent is not None:
                annotate_statements = add_stmt(must_stmt, copy.copy(must_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                must_stmt.decompose()
    if parse_when_stmt is True:
        for when_stmt in yin_soup.find_all('when'):
            if when_stmt.parent is not None:
                annotate_statements = add_stmt(when_stmt, copy.copy(when_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                when_stmt.decompose()
    if parse_min_elem_stmt is True:
        for min_elem_stmt in yin_soup.find_all('min-elements'):
            if min_elem_stmt.parent is not None:
                annotate_statements = add_stmt(min_elem_stmt, copy.copy(min_elem_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                min_elem_stmt.decompose()
    if parse_max_elem_stmt is True:
        for max_elem_stmt in yin_soup.find_all('max-elements'):
            if max_elem_stmt.parent is not None:
                annotate_statements = add_stmt(max_elem_stmt, copy.copy(max_elem_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                max_elem_stmt.decompose()
    if parse_mandatory_stmt is True:
        for mandatory_stmt in yin_soup.find_all('mandatory'):
            if mandatory_stmt.parent is not None:
                annotate_statements = add_stmt(mandatory_stmt, copy.copy(mandatory_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                mandatory_stmt.decompose()
    if parse_unique_stmt is True:
        for unique_stmt in yin_soup.find_all('unique'):
            if unique_stmt.parent is not None:
                annotate_statements = add_stmt(unique_stmt, copy.copy(unique_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                unique_stmt.decompose()
    if parse_pattern_stmt is True:
        for pattern_stmt in yin_soup.find_all('pattern'):
            if pattern_stmt.parent is not None:
                annotate_statements = add_stmt(pattern_stmt, copy.copy(pattern_stmt), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                pattern_stmt.decompose()
    if parse_tailf_stmt is True:
        for tailf_extension in yin_soup.find_all(re.compile('tailf_prefix_')):
            if tailf_extension.parent is not None and tailf_extension.parent.name.startswith('tailf_prefix_') == False:
                annotate_statements = add_stmt(tailf_extension, copy.copy(tailf_extension), ann_soup)
                ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                tailf_extension.decompose()
    else:
        if parse_callpoint_stmt is True:
            for callpoint_stmt in yin_soup.find_all('tailf_prefix_callpoint'):
                if callpoint_stmt.parent is not None:
                    annotate_statements = add_stmt(callpoint_stmt, copy.copy(callpoint_stmt), ann_soup)
                    ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                    callpoint_stmt.decompose()
        if parse_validate_stmt is True:
            for validate_stmt in yin_soup.find_all('tailf_prefix_validate'):
                if validate_stmt.parent is not None:
                    annotate_statements = add_stmt(validate_stmt, copy.copy(validate_stmt), ann_soup)
                    ann_soup.module.tailf_prefix_annotate_module.append(annotate_statements)
                    validate_stmt.decompose()


    if sanitize is True or (tailf_extension is None and must_stmt is None and when_stmt is None and callpoint_stmt is None and validate_stmt is None):
        create_ann_module = False
    else:
        create_ann_module = True
    tailf_extension = yin_soup.find(re.compile('tailf_prefix_'))
    if tailf_extension is None:
      tailf_import = yin_soup.find('import', module='tailf-common')
      if tailf_import is not None:
        tailf_import.decompose()
    tailf_ann_import = ann_soup.find('import', module='tailf-common')
    if yin_soup.module is not None:
        ann_soup.module.attrs = copy.copy(yin_soup.module.attrs)
        for module_import in yin_soup.module.find_all('import', recursive=False):
            if module_import['module'] != "tailf-common":
                tailf_ann_import.insert_before(copy.copy(module_import))
    else:
        ann_soup.module.attrs = copy.copy(yin_soup.submodule.attrs)
        for module_import in yin_soup.submodule.find_all('import', recursive=False):
            if module_import['module'] != "tailf-common":
                tailf_ann_import.insert_before(copy.copy(module_import))
    ann_soup.module['yname'] = "{}-ann".format(ann_soup.module['yname'])
    yin_soup_str = str(yin_soup)
    yin_soup_str = yin_soup_str.replace('tailf_prefix_', 'tailf:')
    yin_soup_str = yin_soup_str.replace('yname=', 'name=')
    yin_soup_str = yin_soup_str.replace('target_node=', 'target-node=')
    yin_soup_str = yin_soup_str.replace('xmlns_', 'xmlns:')
    result = subprocess.run(['python3', '/usr/local/bin/pyang', '-f',
                            'yang', '-p', yang_path, '-p', confd_dir],
                            stdout=subprocess.PIPE, input=yin_soup_str,
                            encoding='utf-8')
    yang_content = result.stdout
    Path(out_path).mkdir(parents=True, exist_ok=True)
    with open("{}/{}".format(out_path,yang_filename), "w") as fp:
        fp.write(str(yang_content))
        fp.close()
    if create_ann_module is True:
        ann_soup_str = str(ann_soup)
        ann_soup_str = ann_soup_str.replace('tailf_prefix_', 'tailf:')
        ann_soup_str = ann_soup_str.replace('annotate_module', 'annotate-module')
        ann_soup_str = ann_soup_str.replace('module_name=', 'module-name=')
        ann_soup_str = ann_soup_str.replace('statement_path=', 'statement-path=')
        ann_soup_str = ann_soup_str.replace('yname=', 'name=')
        ann_soup_str = ann_soup_str.replace('target_node=', 'target-node=')
        ann_soup_str = ann_soup_str.replace('xmlns_', 'xmlns:')
        result = subprocess.run(['python3', '/usr/local/bin/pyang', '-f',
                                'yang', '--ignore-error=UNUSED_IMPORT', '-p',
                                yang_path, '-p', confd_dir], stdout=subprocess.PIPE,
                                input=ann_soup_str, encoding='utf-8')
        ann_content = result.stdout
        with open("{}/{}".format(out_path,ann_filename), "w") as fp:
            fp.write(str(ann_content))
            fp.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-m', '--must', action='store_true',
                        help='remove all must statements')
    parser.add_argument('-w', '--when', action='store_true',
                        help='remove all when startements')
    parser.add_argument('-i', '--minelem', action='store_true',
                        help='remove all min-element statements')
    parser.add_argument('-x', '--maxelem', action='store_true',
                        help='remove all max-element statements')
    parser.add_argument('-a', '--mandatory', action='store_true',
                        help='remove all mandatory statements')
    parser.add_argument('-u', '--unique', action='store_true',
                        help='remove all unique statements')
    parser.add_argument('-p', '--pattern', action='store_true',
                        help='remove all pattern statements')
    parser.add_argument('-t', '--tailf', action='store_true',
                        help='remove all tailf extensions')
    parser.add_argument('-c', '--callpoint', action='store_true',
                        help='remove tailf:callpoint extensions')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='remove tailf:validate extensions')
    parser.add_argument('-s', '--sanitize', action='store_true',
                        help='sanitize only without creating an annotation file')
    parser.add_argument('-o', '--output', nargs=1, type=str, default="",
                        help='Write the output to a different path than current folder')
    parser.add_argument('filename', nargs=1, type=str,
                        help='<file> YANG module filename that end with ".yang"')
    args = parser.parse_args()
    output = "."
    if len(args.output) > 0:
        output = args.output[0]
    tailf_ann_stmt(args.must, args.when, args.minelem, args.maxelem,
                   args.mandatory, args.unique, args.pattern, args.tailf,
                   args.callpoint, args.validate, args.sanitize,
                   output, args.filename[0])
