"""Symlink handling pyang plugin"""

import optparse
import sys
import os

from pyang import plugin
from pyang import statements
from pyang.translators import yang
from pyang import xpath_lexer

tailf = 'tailf-common'


def pyang_plugin_init():
    # register the plugin
    plugin.register_plugin(SymlinkPlugin())

    statements.add_data_keyword((tailf, 'symlink'))


class SymlinkPlugin(plugin.PyangPlugin):
    def add_opts(self, optparser):
        optlist = [optparse.make_option('--symlinks-replace',
                                        action='store_true',
                                        help='Replace tailf:symlink instances'),
                   optparse.make_option('--symlinks-destination',
                                        help='Destination directory for translated modules'),
                   optparse.make_option('--symlinks-no-groups',
                                        action='store_true',
                                        help='Do not use groupings')]
        g = optparser.add_option_group('Symlink handling options')
        g.add_options(optlist)

    def pre_load_modules(self, ctx):
        if ctx.opts.symlinks_destination is None \
           or not os.path.isdir(ctx.opts.symlinks_destination):
            print('Destination directory for translated modules (--symlinks-destination) is required.'
                  '\nAborting.',
                  file=sys.stderr)
            sys.exit(1)

    def post_validate_ctx(self, ctx, modules):
        SymlinkFixer(ctx, modules).replace()


class SymlinkFixer:
    def __init__(self, ctx, modules):
        self.ctx = ctx
        self.modules = modules
        self.groupings = {}

    def replace(self):
        destdir = self.ctx.opts.symlinks_destination
        if self.ctx.opts.symlinks_replace:
            for m in self.modules:
                self.replace_symlinks(m)
            for m in self.modules:
                with open(os.path.join(destdir, f'{m.arg}.yang'), 'w') as fp:
                    yang.emit_yang(self.ctx, m, fp)

    def replace_symlinks(self, node):
        if node.keyword == (tailf, 'symlink'):
            return self.do_replace_symlink(node)
        else:
            node.substmts = [self.replace_symlinks(subnode) for subnode in node.substmts]
            return node

    def do_replace_symlink(self, symlink_node):
        def copyf(statement, new):
            new.top = symlink_node.top
            self.fix_xpaths(statement, new)

        path = symlink_node.search_one((tailf, 'path'))
        assert path is not None
        target = statements.find_target_node(self.ctx, path)
        target_prefix = module_prefix(symlink_node.top, target.top.arg)
        if can_use_link(target):
            new = target.copy(parent=symlink_node.parent, copyf=copyf)
            new.arg = symlink_node.arg
            self.add_links(path.arg, new, target_prefix)
            return new
        elif self.ctx.opts.symlinks_no_groups:
            new = target.copy(parent=symlink_node.parent, copyf=copyf)
            new.arg = symlink_node.arg
            add_transform_callpoint(new)
            return new
        else:
            # if ctx.opts.symlinks_groupings:
            group_name = self.introduce_grouping(target)
            uses_arg = f'{target_prefix}:{group_name}'
            uses = statements.UsesStatement(symlink_node.top, symlink_node.parent,
                                            symlink_node.pos, 'uses', arg=uses_arg)
            refine = statements.Statement(symlink_node.top, uses, symlink_node.pos,
                                          'refine', arg=target.arg)
            add_transform_callpoint(refine)
            uses.substmts = [refine]
            return uses

    def introduce_grouping(self, node):
        if node in self.groupings:
            return self.groupings[node]
        grouping_name = f'{node.arg}-symlink-group'
        self.groupings[node] = grouping_name
        module = node.top
        # replace the target node with 'uses' statement
        uses = statements.UsesStatement(module, node.parent, node.pos, 'uses', arg=grouping_name)
        ix = node.parent.substmts.index(node)
        node.parent.substmts[ix] = uses
        # create new grouping and append it at the end
        grouping = statements.GroupingStatement(module, module, node.pos, 'grouping', grouping_name)
        contents = node.copy(parent=grouping, copyf=self.fix_xpaths)
        grouping.substmts = [contents]
        module.substmts.append(grouping)
        return grouping_name

    def add_links(self, path, node, prefix):
        if node.keyword in ('leaf', 'leaf-list'):
            node.substmts.append(statements.Statement(node.top, node, node.pos,
                                                      (module_prefix(node.top, tailf), 'link'), path))
        else:
            for subnode in node.substmts:
                if subnode.keyword in statements.data_definition_keywords:
                    self.add_links(f'{path}/{prefix}:{subnode.arg}', subnode, prefix)

    def fix_xpaths(self, old, new):
        # needed to add prefixes to XPath expressions
        def fix_tokens():
            prefix = old.top.search_one('prefix').arg
            for token in xpath_lexer.scan(new.arg):
                if token.type != 'name' or ':' in token.value:
                    yield token.value
                else:
                    yield f'{prefix}:{token.value}'
        if new.keyword == 'path' and new.parent.keyword == 'type' \
           or new.keyword in ('must', 'when'):
            new.arg = ''.join(fix_tokens())


def can_use_link(node):
    if node.keyword in ['list', 'choice', 'uses'] \
       or node.keyword == 'container' and node.search_one('presence') is not None:
        return False
    return all(can_use_link(subnode) for subnode in node.substmts
               if subnode.keyword in statements.data_definition_keywords)


def module_prefix(module, import_name):
    impmod = module if module.arg == import_name else module.search_one('import', import_name)
    return impmod.search_one('prefix').arg


def add_transform_callpoint(parent):
    cp_name = f'symlink-transform'
    tf_prefix = module_prefix(parent.top, tailf)
    cp = statements.Statement(parent.top, parent, parent.pos,
                              (tf_prefix, 'callpoint'), arg=cp_name)
    transform = statements.Statement(parent.top, cp, parent.pos,
                                     (tf_prefix, 'transform'), arg='true')
    parent.substmts.insert(0, cp)
    cp.substmts = [transform]
    return cp

