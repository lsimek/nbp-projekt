from logging_settings import logger
from sgraph import SEdgeType, SEdge, SGraph
from snode import SNodeType, SNode, Dotstring
from handlers import *

import ast
import symtable
from collections import deque
from typing import Dict, Optional, Deque, Tuple, Union


class SVisitor:
    """
    class that manages SGraph construction
    """
    def __init__(self, root_namespace='root'):
        self.sgraph: SGraph = SGraph()
        self.stack: Deque[SNode] = deque()
        self.root_namespace = root_namespace

    def single_file_first_pass(self, filepath: str, root_snode: Optional[SNode] = None) -> None:
        """
        first pass for a single file
        """
        if not filepath.endswith('.py'):
            raise ValueError(f'`filepath` should lead to .py file, {filepath} was passed')
        module_name = filepath[filepath.rfind('/')+1:]
        module_name = module_name[:-len('.py')]
        logger.info(f'Starting symbol pass for file {module_name} (package: {root_snode})')

        with open(filepath, 'r') as file:
            code = file.read()

        table = symtable.symtable(code, filepath, compile_type='exec')
        symbol_stack: Deque[Tuple[symtable.SymbolTable, SNode]] = deque()

        # this should be project/subpackage root
        if root_snode is None:
            root_snode = SNode(
                fullname=Dotstring(self.root_namespace),
                namespace=Dotstring(self.root_namespace),
                packagename=self.root_namespace,
                snodetype=SNodeType.Package,
                scope_dict={}
            )

        module_snode = SNode(
            fullname=root_snode.fullname.concat(module_name),
            name=module_name,
            namespace=root_snode.fullname,
            packagename=self.root_namespace,
            snodetype=SNodeType.Module,
            scope_dict={},
            scope_parent=root_snode,
        )

        self.add_snodes(root_snode, module_snode)
        self.add_sedges(SEdge((root_snode, module_snode, ), SEdgeType.WithinScope))

        # first part: go through symbol table
        symbol_stack.append((table, module_snode, ))
        while symbol_stack:
            top_table, top_snode = symbol_stack.pop()
            if not isinstance(top_table, symtable.SymbolTable) or not isinstance(top_snode, SNode):
                raise TypeError(f'Elements of stack must be tuples (symtable.SymbolTable, SNode), ({type(top_table)}, {type(top_snode)}) passed instead')
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
                    packagename=root_snode.fullname,
                    snodetype=SNodeType.Name,
                    scope_dict={},
                    scope_parent=top_snode,
                )

                new_dict[new_snode.fullname] = new_snode.fullname
                self.add_snodes(new_snode)
                self.add_sedges(SEdge(
                        (top_snode, new_snode),
                        SEdgeType.WithinScope
                    ))
                logger.debug(f'Added symbol {new_snode.name}')

            # propagate all new names to own scope and parents' scopes
            self.propagate_scope(top_snode, new_dict)

            # add children to stack if Function or Class
            for child in top_table.get_children():
                child_fullname = top_snode.get_local(child.get_name())
                child_snode = self.get_snode(child_fullname)
                child_snode.snodetype = SNodeType.Function if type(child_snode) is symtable.Function else SNodeType.Class
                symbol_stack.append((child, child_snode, ))
                logger.debug(f'Added to stack {child_snode}')

        # second part: add all attributes
        logger.info(f'Starting attr pass for file {module_name} (package: {root_snode})')
        tree = ast.parse(code)

        fp_stack: Deque[Tuple[Dotstring, ast.AST]] = deque()
        module_snode.ast_node = tree
        fp_stack.append((module_snode.fullname, tree, ))

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
                top_snode = self.resolve_name(self.get_snode(top_namespace), name_list[0], allow_none=False)

                logger.debug(f'Attribute chain found: {name_list}')

                if top_snode is None:
                    # imported name
                    logger.debug(f'Import detected with implicit fullname {top_namespace.concat(name_list[0])}')
                    continue

                if name_list[0] == 'self':
                    # special case - mark as attributes of respective class instead
                    top_snode = top_snode.scope_parent
                    continue

                top_namespace = top_snode.namespace.concat(name_list[0])

                for name in name_list[1:]:
                    # make new snode
                    new_snode = SNode(
                        fullname=top_namespace.concat(name),
                        name=top_snode.name.concat(name),
                        namespace=top_namespace,
                        modulename=module_name,
                        packagename=root_snode.fullname,
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

            else:
                new_namespace = top_namespace
                if isinstance(top_node, ast.ClassDef) or isinstance(top_node, ast.FunctionDef):
                    # set new namespace
                    new_namespace = new_namespace.concat(top_node.name)

                # add children
                for child in ast.iter_child_nodes(top_node):
                    fp_stack.append((new_namespace, child))

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
