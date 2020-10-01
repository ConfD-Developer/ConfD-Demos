#!/usr/bin/env python3
import os
from bs4 import BeautifulSoup
import fileinput
import argparse
import copy

def pattern_replace(file_path, pattern, subst):
    for line in fileinput.input(file_path, inplace=True):
        print(line.replace(pattern, subst), end='')


def handle_annotate_node(annotate_node, module_soup, ann_soup, append_node, module_prefix):
    path_tags = annotate_node['target'].split('/') # Split the "target" path into a "path_list" of prefix:node strings.
    if path_tags[0] == '': # Remove the extra '' if there was a root slash
        path_tags.pop(0)
    path_tag_name = path_tags[-1].split(':')[1] # Find and create a list of all module_nodes in module named as the last tag.
    path_tags.pop()
    module_nodes = []
    for module_node in module_soup.find_all(yname=path_tag_name):
        module_nodes.append(module_node)
    ann_nodes = [] # Create a new "tailf_annotate_statement" tag list entry for each matching node in the module_nodes list
    for module_node in list(module_nodes):
        annotate_statement = ann_soup.new_tag('tailf:annotate-statement', statement_path="{}[name=\'{}\']".format(module_node.name, module_node['yname']))
        for child in annotate_node.find_all(recursive=False): # Add the content to be annotated to the annotate_statement
            if child.name == 'annotate' or child.name == 'tailf:annotate': # Nested tailf:annotate
                annotate_statement = handle_annotate_node(child, module_soup, ann_soup, annotate_statement, module_prefix)
            else:
                child_clone = copy.copy(child) # Clone as we need to decompose the tailf:annotate below
                annotate_statement.append(child_clone)
        ann_nodes.append(annotate_statement)
    annotate_node.decompose() # Done with current tailf:annotate traversal. Remove the tailf:annotate node from the annotation module
    while path_tags: # Get the next "prefix:node" string from the "path_tags" list
        path_tag = path_tags[-1].split(':')
        path_tags.pop()
        path_tag_prefix = path_tag[0]
        if path_tag_prefix == module_prefix:
            path_tag_name = path_tag[1]
            for module_node, ann_node in zip(list(module_nodes), list(ann_nodes)): # Compare module node tag name with path tag name to find the intended path
                ann_index = ann_nodes.index(ann_node)
                if module_node.name == 'augment' or module_node.name == 'grouping': # Handle groupings and augment
                    path_tags.clear() # Done
                    for node in ann_nodes: # Eliminate other non-intended paths
                        if node is not ann_node:
                            ann_nodes.remove(node)
                    break;
                elif ((module_node.parent.name == "choice" and module_node.parent['yname'] == path_tag_name) or (module_node.name == "choice" and module_node['yname'] == path_tag_name) or (module_node.parent.name == "choice" and module_node.parent['yname'] == path_tags[-1].split(':')[1])) and module_node.name != 'case': # Handle choice without a case
                    module_nodes[module_nodes.index(module_node)] = module_node.parent
                    new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent['yname']))
                    if module_node.parent.name == "choice" and module_node.parent['yname'] == path_tag_name:
                        extra_choice_node = ann_soup.new_tag('remove_next_node', extra_choice_node=module_node['yname'])
                        extra_choice_node.append(ann_nodes[ann_index])
                        new_annotate_statement.append(extra_choice_node)
                    else:
                        new_annotate_statement.append(ann_nodes[ann_index])
                    ann_nodes[ann_index] = new_annotate_statement
                elif module_node.parent.name == 'grouping' or module_node.parent.name == 'augment' or (module_node.parent['yname'] == path_tag_name):
                    module_nodes[module_nodes.index(module_node)] = module_node.parent
                    attribute_name = 'yname'
                    if module_node.parent.name == 'augment': # Handle that augment nodes have a different attribute name than other nodes
                        attribute_name = 'target_node'
                    new_annotate_statement = ann_soup.new_tag("tailf:annotate-statement", statement_path="{}[name=\'{}\']".format(module_node.parent.name, module_node.parent[attribute_name]))
                    new_annotate_statement.append(ann_nodes[ann_index])
                    ann_nodes[ann_index] = new_annotate_statement
                else:
                    module_nodes.remove(module_node) # Eliminated
                    ann_nodes.remove(ann_node)
        else:
            if path_tags: # No longer in the module to be annotated. Exit while loop by clearing the list
                path_tags.clear()
    len_ann_nodes = len(ann_nodes)
    if len_ann_nodes > 1:
        i = 0
        for node in ann_nodes:
            confict_container = ann_soup.new_tag("conflict", number="{} of {}".format(i+1, len_ann_nodes))
            confict_container.append(node)
            append_node.append(confict_container)
            i += 1
    elif len_ann_nodes > 0:
        append_node.append(ann_nodes[0]) # Append the tailf:annotate-statement to the tailf:annotate-module node
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
