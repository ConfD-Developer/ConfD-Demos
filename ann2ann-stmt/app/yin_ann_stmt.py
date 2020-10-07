#!/usr/bin/env python3
import os
from bs4 import BeautifulSoup
import fileinput
import argparse
import copy
import sys

def pattern_replace(file_path, pattern, subst):
    for line in fileinput.input(file_path, inplace=True):
        print(line.replace(pattern, subst), end='')


def handle_annotate_node(annotate_node, module_soup, ann_soup, append_node, module_prefix):
    ann_path = annotate_node['target']
    path_tags = ann_path.split('/') # Split the "target" path into a "path_list" of prefix:node strings.
    if path_tags[0] == '': # Remove the extra '' if there was a root slash
        path_tags.pop(0)
    path_tag_name = path_tags[-1].split(':')[-1] # Find and create a list of all module_nodes in module named as the last tag.
    path_tags.pop()
    module_nodes = []
    for module_node in module_soup.find_all(yname=path_tag_name):
        module_nodes.append(module_node)
    ann_nodes = [] # Create a new "tailf_annotate_statement" tag list entry for each matching node in the module_nodes list
    for module_node in list(module_nodes):
        annotate_statement = ann_soup.new_tag('tailf:annotate-statement', statement_path="{}[name=\'{}\']".format(module_node.name, module_node['yname']))
        for child in annotate_node.find_all(recursive=False): # Add the content to be annotated to the annotate_statement
            if child.name == 'annotate' or child.name == 'tailf:annotate': # Nested tailf:annotat
                annotate_statement = handle_annotate_node(child, module_soup, ann_soup, annotate_statement, module_prefix)
            else:
                child_clone = copy.copy(child) # Clone as we need to decompose the tailf:annotate below
                annotate_statement.append(child_clone)
        ann_nodes.append(annotate_statement)
    annotate_node.decompose() # Done with current tailf:annotate traversal. Remove the tailf:annotate node from the annotation module
    tmp_nodes = []
    while len(path_tags) > 0: # Get the next "prefix:node" string from the "path_tags" list
        path_tag = path_tags[-1].split(':')
        path_tags.pop()
        path_tag_prefix = path_tag[0]
        if path_tag_prefix == module_prefix:
            path_tag_name = path_tag[-1]
            index = 0;
            for module_node, ann_node in zip(list(module_nodes), list(ann_nodes)): # Compare module node tag name with path tag name to find the intended path
                if ((module_node.parent.name == "choice" and module_node.parent['yname'] == path_tag_name) or (module_node.name == "choice" and module_node['yname'] == path_tag_name) or (module_node.parent.name == "choice" and len(path_tags) > 0 and module_node.parent['yname'] == path_tags[-1].split(':')[-1])) and module_node.name != 'case': # Handle choice without a case
                    new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['yname']))
                    if module_node.parent.name == "choice" and module_node.parent['yname'] == path_tag_name:
                        extra_choice_node = ann_soup.new_tag('remove_next_node', extra_choice_node=module_node['yname'])
                        extra_choice_node.append(ann_nodes[index])
                        new_annotate_statement.append(extra_choice_node)
                    else:
                        new_annotate_statement.append(ann_nodes[index])
                        path_tag_prefix = path_tags[-1].split(':')[0]
                        path_tag_name = path_tags[-1].split(':')[-1]
                        path_tags.pop()
                    ann_nodes[index] = new_annotate_statement
                    module_nodes[index] = module_node.parent
                elif module_node.parent.has_attr('yname') and module_node.parent['yname'] == path_tag_name:
                    new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['yname']))
                    new_annotate_statement.append(ann_nodes[index])
                    ann_nodes[index] = new_annotate_statement
                    module_nodes[index] = module_node.parent
                elif module_node.parent.name == 'grouping':
                    uses_name = module_node.parent['yname']
                    found = False
                    uses_nodes = module_soup.find_all("uses", yname=uses_name)
                    if len(uses_nodes) == 0:
                        found = True # Unused locally
                    else:
                        for uses_node in uses_nodes:
                            if uses_node.parent.has_attr('yname') and uses_node.parent.name != "grouping":
                                uses_parent_name = uses_node.parent['yname']
                                if uses_parent_name == path_tag_name:
                                    found = True
                                    break;
                            elif uses_node.parent.has_attr('target_node'): # augment parent to uses
                                augment_path_tags = uses_node.parent['target_node'].split('/')
                                augment_path_tag = augment_path_tags[-1].split(':')
                                if augment_path_tag[-1] == path_tag_name:
                                    found = True
                                    break;
                            else: # Parent of the uses not a node we can compare with. Keep to be safe
                                found = True
                                break;
                    if found == True:
                        new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['yname']))
                        new_annotate_statement.append(copy.copy(ann_nodes[index]))
                        tmp_nodes.append(new_annotate_statement)
                    del module_nodes[index]
                    del ann_nodes[index]
                    index -= 1
                elif module_node.parent.name == 'augment':
                    augment_path_tags = module_node.parent['target_node'].split('/')
                    augment_path_tag = augment_path_tags[-1].split(':')
                    if augment_path_tag[-1] == path_tag_name:
                        new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['target_node']))
                        new_annotate_statement.append(copy.copy(ann_nodes[index]))
                        tmp_nodes.append(new_annotate_statement)
                    del module_nodes[index]
                    del ann_nodes[index]
                    index -= 1
                else:
                    del module_nodes[index]
                    del ann_nodes[index]
                    index -= 1
                index += 1
        else:
            if len(path_tags) > 0:
                index = 0
                for module_node, ann_node in zip(list(module_nodes), list(ann_nodes)):
                    if module_node.has_attr('yname') and module_node.name != "grouping":
                        if module_node.parent.name == 'grouping' or module_node.parent.name == 'augment':
                            if module_node.parent.has_attr('target_node'):
                                new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['target_node']))
                            else:
                                new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['yname']))
                            new_annotate_statement.append(ann_nodes[index])
                            ann_nodes[index] = new_annotate_statement
                        elif module_node.parent.name != 'module':
                            del module_nodes[index]
                            del ann_nodes[index]
                            index -= 1
                    index += 1
                path_tags.clear() # No longer in the module to be annotated. Exit while loop by clearing the list
    ann_nodes.extend(tmp_nodes)
    len_ann_nodes = len(ann_nodes)
    if len_ann_nodes > 1: # Wrap conflicts
        i = 0
        for node in ann_nodes:
            confict_tag = ann_soup.new_tag("conflict", number="{} of {}".format(i+1, len_ann_nodes))
            confict_tag.append(node)
            append_node.append(confict_tag)
            i += 1
    elif len_ann_nodes > 0: # Success
        append_node.append(ann_nodes[0]) # Append the tailf:annotate-statement to the tailf:annotate-module node
    else: # Could not convert some path(s). Create a tag to show which tailf:annotate path was skipped
        skip_container = ann_soup.new_tag("skipped", target="{}".format(ann_path))
        append_node.append(skip_container)
    return append_node;


def trim_yin(module_file_name, ann_file_name):
    module_tmp_str = module_file_name.rsplit('.', 1)[0]
    ann_tmp_str = ann_file_name.rsplit('.', 1)[0]
    module_name_str = module_tmp_str.split('/')[-1]
    ann_name_str = ann_tmp_str.split('/')[-1]
    pattern_replace(module_file_name, 'name=', 'yname=') # Replace "name=" attribute tag with temp "yname=" to not confuse bs4
    pattern_replace(module_file_name, "target-node=", "target_node=") # Replace augment attribute name for bs4 compliance
    pattern_replace(ann_file_name, 'name=', 'yname=')
    with open(module_file_name) as fp: # Create two soups
        module_soup = BeautifulSoup(fp, "xml") # A temp soup for the YANG model to be annotated
        fp.close()
    with open(ann_file_name) as fp:
        ann_soup = BeautifulSoup(fp, "xml") # The annotation file soup to be transformed
        fp.close()
    module_prefix = ann_soup.find('import', module=module_name_str).find('prefix')['value'] # Get the prefix used for the module in the annotation module
    annotate_module = ann_soup.new_tag("tailf:annotate-module", module_name="{}".format(module_name_str)) # Create the top tailf:annotate-module tag in the annotation module
    ann_soup.module.append(annotate_module) # Append the tailf:annotate-module to the "module" root tag
    for annotate_node in ann_soup.module.find_all('tailf:annotate', recursive=False): # Find all tags named "tailf:annotate" in the ann_soup, i.e. soup of annotations.
        handle_annotate_node(annotate_node, module_soup, ann_soup, annotate_module, module_prefix)
    for elem in ann_soup.find_all('remove_next_node'): # Remove all "extra" choice statement nodes
        for child in elem.find_all(recursive=False):
            child.unwrap()
        elem.unwrap()
    with open("{}mod".format(ann_file_name), "w") as fp:
        fp.write(str(ann_soup))
        fp.close()
    pattern_replace(module_file_name, "yname=", "name=") # Change the bs4 workaround temp attribute names to their YIN variant
    pattern_replace(module_file_name, "target_node=", "target-node=")
    pattern_replace(ann_file_name, "yname=", "name=")
    pattern_replace("{}mod".format(ann_file_name), "yname=", "name=")
    pattern_replace("{}mod".format(ann_file_name), "statement_path", "statement-path")
    pattern_replace("{}mod".format(ann_file_name), "module_name", "module-name")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-a', '--tailf-annotation-module', type=str, required=True,
                        help='<file> YIN module with tailf annotations')
    parser.add_argument('filename', type=str,
                        help='<file> YIN module to be annotated')
    args = parser.parse_args()
    trim_yin(args.filename, args.tailf_annotation_module)
