"""
class that manages ast and package traversals
"""
from logging_settings import logger
from sgraph import *
from handlers import *

import ast
import symtable
from collections import deque
from typing import List, Union, Deque


class SVisitor:
    """
    class that manages AST traversal
    """
    def __init__(self, root_namespace='root'):
        self.sgraph: SGraph = SGraph()
        self.stack: Deque[SNode] = deque()
        self.filepath = None
        self.code = None
        self.root_namespace = root_namespace

    def single_file_1st_pass(self, filepath: str) -> None:
        """
        name to be changed
        start with symtable
        """
        logger.info(f'Analyzing file {filepath} 1st pass')
        if not filepath.endswith('.py'):
            raise ValueError('filepath should lead to .py file')

        with open(filepath, 'r') as file:
            code = file.read()

        table = symtable.symtable(code, filepath, compile_type='exec')
        self.stack = deque()
        self.stack.append(table)

        root_snode = SNode(
            fullname=self.root_namespace,
            namespace=self.root_namespace,
            packagename=self.root_namespace,
            snodetype=SNodeType.Package,
        )

        # prev =

        snodetype_dict = {
            symtable.SymbolTable: SNodeType.Module,
            symtable.Function: SNodeType.Function,
            symtable.Class: SNodeType.Class,
            symtable.Symbol: SNodeType.Name
        }

        while self.stack:
            top = self.stack.pop()



            new_snode = SNode(

            )


    def single_file(self, filepath: str) -> None:
        """
        name to be changed
        analyze single file
        """
        logger.info(f'Analyzing file {filepath}...')
        if not filepath.endswith('.py'):
            raise ValueError('filepath should lead to .py file')

        self.filepath = filepath
        with open(filepath, 'r') as file:
            self.code = file.read()
        tree = ast.parse(self.code)

        # add root (ast.Module) to stack with data
        self.stack.append(
            SNode(
                fullname=self.root_namespace,
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

    def add_nodes(self, *nodes):
        self.sgraph.add_nodes(nodes)

    def add_edges(self, *edges):
        self.sgraph.add_edges(edges)

    def get_snode(self, snode):
        self.sgraph.nodes.get(snode.fullname, None)