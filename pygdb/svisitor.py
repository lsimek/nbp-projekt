from logging_settings import logger
from sgraph import SEdgeType, SEdge, SGraph
from snode import SNodeType, SNode, Dotstring
from handlers import *

import ast
import symtable
from collections import deque
from typing import List, Dict, Deque, Tuple, Union, Optional
import os
import pathlib


class SVisitor:
    """
    class that manages SGraph construction
    """
    def __init__(self, root_namespace='root'):
        self.sgraph: SGraph = SGraph()
        self.stack: Deque[SNode] = deque()
        self.root_namespace = root_namespace

    def scan_package(self, root_dir: Union[str, pathlib.Path]):
        root_path = pathlib.Path(root_dir).resolve()
        os.chdir(root_path)
        logger.info(f'Scanning package at root location {root_path}, abs. path {root_path.resolve()}')

        # path relative to root_path
        def relpath(str_path):
            return pathlib.Path(str_path).resolve().relative_to(root_path)

        root_snode = SNode(
            fullname=Dotstring(self.root_namespace),
            namespace=Dotstring(self.root_namespace),
            packagename=self.root_namespace,
            snodetype=SNodeType.Package,
            scope_dict={},
        )
        self.add_snodes(root_snode)
        # add __init__ file to module_list if it exists?

        # stack to traverse directories
        stack: Deque[Tuple[SNode, pathlib.Path]] = deque()
        stack.append((root_snode, root_path, ))

        # list of modules to analyze (and package = __init__)
        module_list: List[SNode] = []

        while stack:
            package_snode, package_path = stack.pop()
            logger.debug(f'Traversing files at {relpath(package_path)}')
            # add folders and .py modules as children to package_snode
            # stop if a folder contains no .py files

            new_dict: Dict[Dotstring, Dotstring] = {}

            for subpath in os.listdir(package_path):
                if os.path.isfile(package_path/subpath) and subpath.endswith('.py') and subpath != '__init__.py':
                    # insert module node to graph and module_list
                    # propagate in scope_dict
                    module_name = subpath[:-len('.py')]

                    module_snode = SNode(
                        fullname=package_snode.fullname.concat(module_name),
                        namespace=package_snode.fullname,
                        packagename=package_snode.name,
                        snodetype=SNodeType.Module,
                        scope_dict={},
                        scope_parent=package_snode,
                        __imports_from__=[],
                        __code__=open(package_path/subpath).read(),
                        __filepath__=relpath(package_path/subpath)
                    )

                    logger.debug(f'Adding new module {module_snode.fullname}')
                    self.add_snodes(module_snode)
                    self.add_sedges(SEdge((module_snode, package_snode, ), SEdgeType.WithinScope))

                    module_list.append(module_snode)
                    new_dict[module_snode.fullname] = module_snode.fullname

                # add package if there are any .py files inside
                elif os.path.isdir(package_path/subpath) and any([filename.endswith('py') for filename in os.listdir(package_path/subpath)]):
                    # add folder as package if it has any .py files
                    # then also add to stack

                    # check for __init__.py
                    hasinit = os.path.exists(initpath := package_path/subpath/pathlib.Path('__init__.py'))

                    new_package_snode = SNode(
                        fullname=package_snode.fullname.concat(subpath),
                        namespace=package_snode.fullname,
                        packagename=package_snode.fullname,
                        snodetype=SNodeType.Package,
                        scope_dict={},
                        scope_parent=package_snode,
                        hasinit=hasinit,
                        __imports_from__=[],
                        __code__=open(initpath).read() if hasinit else None,
                        __filepath__=relpath(initpath) if hasinit else None
                    )

                    logger.debug(f'Adding new package {new_package_snode.fullname}')
                    self.add_snodes(new_package_snode)
                    self.add_sedges(SEdge((new_package_snode, package_snode, ), SEdgeType.WithinScope))

                    module_list.append(new_package_snode)
                    new_dict[new_package_snode.fullname] = new_package_snode.fullname

                    stack.append((new_package_snode, package_path/subpath))

            self.propagate_scope(package_snode, new_dict)

        logger.info('File traversal finished. Starting first pass.')
        for module_snode in module_list:
            self.first_pass(module_snode)
        logger.info('First passes finished. Starting second pass.')
        for module_snode in module_list:
            self.second_pass(module_snode)
        logger.info('Second passes finished. Starting third pass.')

    def first_pass(self, module_snode: SNode):
        logger.info(f'First pass for {module_snode.fullname}')
        code = module_snode.attrs.get('__code__')
        if code is None:
            logger.debug(f'No code for module/package {module_snode.fullname}')
            return

        table = symtable.symtable(code, module_snode.attrs.get('__filepath__'), compile_type='exec')
        module_name = module_snode.name

        symbol_stack: Deque[Tuple[symtable.SymbolTable, SNode]] = deque()

        # traverse symbol table
        symbol_stack.append((table, module_snode,))
        while symbol_stack:
            top_table, top_snode = symbol_stack.pop()
            logger.debug(f'Checking symbols in namespace {top_snode.fullname}')

            new_dict = {}
            for symbol in top_table.get_symbols():
                if not symbol.is_local() or symbol.is_imported():
                    continue

                new_snode = SNode(
                    fullname=top_snode.fullname.concat(symbol.get_name()),
                    name=symbol.get_name(),
                    namespace=top_snode.fullname,
                    modulename=module_name,
                    packagename=module_snode.packagename,
                    snodetype=SNodeType.Name,
                    scope_dict={},
                    scope_parent=top_snode,
                )

                new_dict[new_snode.fullname] = new_snode.fullname
                self.add_snodes(new_snode)
                self.add_sedges(SEdge(
                    (new_snode, top_snode),
                    SEdgeType.WithinScope
                ))
                logger.debug(f'Added symbol {new_snode.name}')

            # propagate all new names to own scope and parents' scopes
            self.propagate_scope(top_snode, new_dict)

            # add children to stack if Function or Class
            for child in top_table.get_children():
                child_fullname = top_snode.get_local(child.get_name())
                child_snode = self.get_snode(child_fullname)
                child_snode.snodetype = SNodeType.Function if child.get_type() == 'function' else SNodeType.Class
                symbol_stack.append((child, child_snode,))
                logger.debug(f'Added to stack {child_snode}')

    def second_pass(self, module_snode: SNode):
        logger.info(f'Starting second pass for file {module_snode.fullname} (package: {module_snode.packagename})')
        code = module_snode.attrs.get('__code__')
        if code is None:
            logger.debug(f'No code for module/package {module_snode.fullname}')
            return

        tree = ast.parse(code)
        module_snode.add_to_attrs(__ast__=tree)

        fp_stack: Deque[Tuple[Dotstring, ast.AST]] = deque()
        module_snode.ast_node = tree
        fp_stack.append((module_snode.fullname, tree,))

        while fp_stack:
            top_namespace, top_node = fp_stack.pop()

            if isinstance(top_node, ast.Attribute):
                # handle attribute case
                name_list = []
                node = top_node

                while isinstance(node, ast.Attribute):
                    name_list.append(node.attr)
                    node = node.value

                name_list.append(node.id)
                name_list = name_list[::-1]
                top_snode = self.resolve_name(self.get_snode(top_namespace), name_list[0])

                logger.debug(f'Attribute chain found: {name_list}')

                if top_snode is None:
                    # imported name
                    continue

                if name_list[0] == 'self':
                    # special case - mark as attributes of respective class instead
                    top_snode = top_snode.scope_parent
                    continue

                top_namespace = top_snode.namespace.concat(name_list[0])

                for name in name_list[1:]:
                    # check if already exists
                    new_fullname = top_namespace.concat(name)
                    new_snode = self.get_snode(new_fullname)

                    # make new snode
                    if new_snode is None:
                        new_snode = SNode(
                            fullname=top_namespace.concat(name),
                            name=top_snode.name.concat(name),
                            namespace=top_namespace,
                            modulename=module_snode.name,
                            packagename=module_snode.packagename,
                            snodetype=SNodeType.Name,
                            scope_dict={},
                            scope_parent=top_snode,
                        )

                        # add to graph
                        self.add_snodes(new_snode)

                        # connect with 'AttributeOf' SEdge
                        new_sedge = SEdge((new_snode, top_snode), SEdgeType.AttributeOf)
                        self.add_sedges(new_sedge)

                        # propagate in scope
                        self.propagate_scope(top_snode, {new_snode.fullname: new_snode.fullname})

                    # set future top_node and top_namespace
                    top_namespace = top_namespace.concat(name)
                    top_snode = new_snode

                # add the list to AST node
                top_node.list = name_list

            # import handling in second pass
            # what about a package wo __init__?
            elif isinstance(top_node, (ast.Import, ast.ImportFrom, )):
                names_list = [name.name for name in top_node.names] if isinstance(top_node, ast.Import) else [top_node.module]

                for name in names_list:
                    if module_snode.snodetype is SNodeType.Module:
                        source_fullname = module_snode.scope_parent.fullname
                    else:
                        source_fullname = module_snode.fullname

                    imported_fullname = source_fullname.concat_rel(name)
                    imported_snode = self.get_snode(imported_fullname)

                    if imported_snode is not None:
                        logger.debug(f'Import detected in second pass: {module_snode} <- {imported_snode}')
                        module_snode.attrs.get('__imports_from__').append(imported_snode)
                        self.add_sedges(SEdge((module_snode, imported_snode,), SEdgeType.ImportsFrom))

            else:
                new_namespace = top_namespace
                if isinstance(top_node, ast.ClassDef) or isinstance(top_node, ast.FunctionDef):
                    # set new namespace
                    new_namespace = new_namespace.concat(top_node.name)

                # add children
                for child in ast.iter_child_nodes(top_node):
                    fp_stack.append((new_namespace, child))


    def third_pass(self, module_snode: SNode):
        pass

    # @deprecated
    def single_file_third_pass(self, filepath: str) -> None:
        """
        name to be changed
        not functional in this commit
        """
        logger.info(f'Analyzing file {filepath}...')
        if not filepath.endswith('.py'):
            raise ValueError('filepath should lead to .py file')

        with open(filepath, 'r') as file:
            code = file.read()
        tree = ast.parse(code)

        # add root (ast.Module) to stack with data
        self.stack.append(
            SNode(
                fullname=Dotstring(self.root_namespace),
                ast_node=tree,
                parent=None,
            )
        )

        # call handlers until stack is empty
        while self.stack:
            top_node = self.stack.pop()
            top_node_type = 'ast.' + type(top_node.ast_node).__name__
            handler = handlers_dict.get(top_node_type)
            logger.info(f'Handling type {top_node_type} with {handler.__name__}')
            handler(self, top_node)

    def add_snodes(self, *nodes) -> None:
        self.sgraph.add_nodes(*nodes)

    def add_sedges(self, *edges) -> None:
        self.sgraph.add_edges(*edges)

    def get_snode(self, fullname) -> SNode:
        """
        for given fullname, get unique
        SNode it refers to
        """
        return self.sgraph.nodes.get(fullname, None)

    def resolve_name(self, current_snode: SNode, name: str, allow_none: bool = True) -> SNode:
        """
        for given scope and name, get unique
        SNode it refers to
        """
        logger.debug(f'Resolving {name=} in {current_snode}')
        fullname = current_snode.fullname.concat(name)
        while fullname not in current_snode.scope_dict and current_snode.scope_parent is not None:
            current_snode = current_snode.scope_parent
            fullname = current_snode.fullname.concat(name)
        fullname = current_snode.scope_dict.get(fullname)

        if fullname is not None or allow_none:
            return self.get_snode(fullname)
        else:
            raise KeyError(f'{name=} in {current_snode} could not be resolved.')

    def propagate_scope(self, current_snode, new_dict: Dict) -> None:
        """
        propagate elements of scope
        to successive parents
        """
        while current_snode is not None:
            current_snode.scope_dict.update(new_dict)
            current_snode = current_snode.scope_parent
