"""
class that manages ast and package traversals
"""
from logging_settings import logger
from sgraph import SEdgeType, SEdge, SGraph
from snode import SNodeType, SNode, Dotstring
from handlers import *

import ast
import symtable
from collections import deque
from typing import List, Optional, Deque, Tuple


class SVisitor:
    """
    class that manages AST traversal
    """
    def __init__(self, root_namespace='root'):
        self.sgraph: SGraph = SGraph()
        self.stack: Deque[SNode] = deque()
        self.root_namespace = root_namespace

    def single_file_symbol_pass(self, filepath: str, root_snode: Optional[SNode] = None) -> None:
        """
        name to be changed
        start with symtable
        """
        logger.info(f'Starting symbol pass for file {filepath}')
        if not filepath.endswith('.py'):
            raise ValueError(f'`filepath` should lead to .py file, {filepath} was passed')
        module_name = filepath[filepath.rfind('/')+1:]
        module_name = module_name[:-len('.py')]
        logger.debug(f'Symbol pass for file {module_name} (package: {root_snode})')

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

        symbol_stack.append((table, module_snode, ))

        while symbol_stack:
            top_table, top_snode = symbol_stack.pop()
            if not isinstance(top_table, symtable.SymbolTable) or not isinstance(top_snode, SNode):
                raise TypeError(f'Elements of stack must be tuples (symtable.SymbolTable, SNode), ({type(top_table)}, {type(top_snode)}) passed instead')
            logger.debug(f'Checking symbols in namespace {top_snode.fullname}')
            
            for symbol in top_table.get_symbols():
                if not symbol.is_local() or symbol.is_imported():
                    continue

                new_snode = SNode(
                    fullname=top_snode.fullname.concat(symbol.get_name()),
                    namespace=top_snode.fullname,
                    modulename=module_name,
                    packagename=root_snode.fullname,
                    snodetype=SNodeType.Name,
                    scope_dict={},
                    scope_parent=top_snode,
                    ast_parent=None,
                    ast_node=None,
                )

                # add to top_snode's scope_dict & add edges
                top_snode.scope_dict.update({new_snode.fullname: new_snode.fullname})
                self.add_snodes(new_snode)
                self.add_sedges(SEdge(
                        (top_snode, new_snode),
                        SEdgeType.WithinScope
                    ))
                logger.debug(f'Added symbol {new_snode.name}')

            # add children to stack if Function or Class
            for child in top_table.get_children():
                child_fullname = top_snode.get_local(child.get_name())
                child_snode = self.get_snode(child_fullname)
                # child_snode = top_snode.scope_dict.get(top_snode.fullname.concat(child.get_name()))
                child_snode.snodetype = SNodeType.Function if type(child_snode) is symtable.Function else SNodeType.Class
                symbol_stack.append((child, child_snode, ))
                logger.debug(f'Added to stack {child_snode}')

    def single_file(self, filepath: str) -> None:
        """
        name to be changed
        analyze single file
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

    def add_snodes(self, *nodes):
        self.sgraph.add_nodes(*nodes)

    def add_sedges(self, *edges):
        self.sgraph.add_edges(*edges)

    def get_snode(self, fullname):
        return self.sgraph.nodes.get(fullname, None)
