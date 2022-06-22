# Removing `tailf:symlink`

This demo shows how the statement `tailf:symlink` can be replaced by other
means.  The statement was supported by ConfD releases prior to 7.5.  Its usage
looks like this:

    tailf:symlink duplicate-node {
      tailf:path "/root/original-node";
    }

Such statement creates a "symbolic link" named `duplicate-node` to
`/root/original-node`, so that every configuration change done in one node is
immediately visible in the other.

Using `tailf:symlink` makes your device substantially incompatible with network
management systems, including Cisco NSO, and support for it had to be dropped.
If your data model contains this statement, you have several options how to
replace its functionality, depending on how you use the statement and what
changes are acceptable for your use case.


## Demo structure

The options described here are all exemplified on a data model that contains
one `tailf:symlink` occurrence for each of the options.  The original data model
that contains symlinks is in the directory `origin/`, with two modules: `root`
with three top-level nodes, and `symlinks` that contains three `tailf:symlink`
statements pointing to the three nodes in `root`.

The root directory contains these two modules, where the three `tailf:symlink`
occurrences have been removed using one of the mechanisms described below, and C
code implementing transform callbacks for the list `server`.


## Removing `tailf:symlink` options

The following paragraphs describe three mechanisms that can be used to remove
the statement.  They all have different assumptions and thus may not be always
applicable.  All variants try to keep data model changes to the bare minimum.


### Replace with `tailf:link`

This is applicable only if the symlink target node contains only non-presence
containers, leaves and leaf-lists.  If that is the case, the structure of the
node can be copied to replace the symlink node and all leaves and leaf-lists
annotated with `tailf:link` pointing to the target counterpart.

This is the case of the container `storage` - it contains only two leaves (one
of them operational) and one leaf-list, so just by adding the container and its
three children and linking the three children the full original functionality
is preserved.  Note that this still makes such data model troublesome for
management systems due to so-called "aliasing" - configuration changes in one
part of the data model cause configuration changes elsewhere.

* pros: it faithfully reproduces the original `tailf:symlink` behavior
* cons: can be used only in some cases, requires somewhat larger data model
  modifications, suffers from aliasing


### Use `grouping` or `augment`

The extension `tailf:symlink` is often used to have important nodes not just
somewhere deeper in the data model tree where they naturally belong, but also
near the top of the tree, for two reasons: the YANG definition is easy to find
and modify, if needed; and it is convenient for the operator to modify the
configuration if it is at the top level.  In our example, the list `portal`
belongs under `/web-service/web`, but it is modeled there as a symlink to the
top-level list.

If it is acceptable that the convenience top-level list is effectively removed
from the model tree, it is possible to keep the syntactic structure almost the
same while removing the `tailf:symlink` usage using `grouping`/`uses`
construct.  Another option is to use `augment`; the difference between these
two is in which part of the data model refers to the other, `grouping`/`uses`
is more similar to the original `tailf:symlink` in this respect.

* pros: the construct is perfectly understood by any management system
* cons: the effective data model tree is considerably modified, so old
  configurations or path expressions may not be valid any longer


### Implement transform

This most complex scenario implements both parts of `tailf:symlink` behavior:

* the two identical parts of the data model tree are both present;
* configuration changes done in one part are (eventually) visible in the other
  part.

In this demo, the tree duplication is implemented using `groupings` to make
sure the subtrees are indeed identical.  The second bullet is implemented using
*transform*: the symlink source in the original model, now replaced by `uses`,
is annotated with a transform callpoint, and a set of callbacks is implemented.
With the callpoint annotation the symlink source becomes "virtual" and whenever
ConfD needs to query or modify configuration there, it invokes the callbacks
that only redirect the query to the symlink target subtree.  See more about
transforms in the ConfD User Guide.

As a result, the behavior is identical to that of `tailf:symlink`, with two
notable differences:

* configuration changes in one of the two subtrees are not visible in the other
  subtree until the configuration is committed;
* due to callbacks involved, performance of the solution might be worse,
  especially if the symlinked configuration contains large list instance sets.

The performance can be improved if needed, but this is beyond the scope of this
demo.

* pros: the behavior is almost identical, can be used in most scenarios
* cons: might be complex to implement, suffers from aliasing, potentially
  decreased performance


## Pyang plugin for removing symlinks

Removing symlinks manually may be tedious if there are too many of them.  An
alternative approach presented here is to use a *pyang plugin*.  The tool
[pyang](https://github.com/mbj4668/pyang) (also available from
[PyPI](https://pypi.org/project/pyang/)) can parse and transform YANG modules;
a plugin may modify the tool's behavior or implement a particular YANG
transform.

The plugin `symlink` implements the following:

* it removes all `tailf:symlink` occurrences;
* if an occurrence can be replaced by `tailf:link`, it uses that;
* otherwise, it prepares the data model for the transform approach.

As a result, when applied to the two example YANG modules `origin/root.yang`
and `origin/symliked.yang`, the output is structurally identical to the two
modules in this directory, with the exception that it does not use the second
variant with `groupings` - the list `portal` is prepared to be handled with a
transform too.

Note that this is just a demo, the plugin does not try to implement corner
cases like symlinks pointing to symlinks, relative XPaths leaving symlink
targets, combinations of symlinks and groupings or augments, etc.


### Installing and running

The only prerequisite is pyang itself.  You can install it using `pip`:

    $ pip install pyang

To run the plugin, following options need or may to be provided to pyang:

`--symlinks-replace`: Tell pyang to use the plugin and tell the plugin to look
for symlinks.

`--symlinks-destination=<directory>`: Tell the plugin where the output YANG
modules should be stored.  It is a mandatory argument, the plugin refuses to
overwrite the original modules (unless told so by this option).

`--symlink-no-groups`: Tell the plugin to not use YANG groupings and copy the
subtree instead.  By default, the plugin creates a new groupings for each
symlink target and uses it both where the target was as well where the symlink
was.

See `pyang --help` for details about pyang usage.

For instance, to replace symlinks in the two example modules, something like
this needs to be done:

    $ cd origin
    $ mkdir fixed
    $ pyang --plugindir . --symlinks-replace --symlinks-destination fixed \
    symlinked.yang root.yang
    $
