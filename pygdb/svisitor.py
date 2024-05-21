"""
class that manages ast and package traversals
"""
from logging_settings import logger
from sgraph import *
from handlers import *
from scontext import SContext

import ast
from collections import deque
from typing import List, Union, Deque


class SVisitor:
    """
    class that manages AST traversal
    """
    def __init__(self):
        self.sgraph: SGraph = SGraph()
        self.stack: Deque[SContext] = deque()
        self.filepath = None
        self.code = None
        self.namespace=['root']

    def single_file(self, filepath: str, namespace: List[str]=['root']):
        """
        name to be changed
        analyze single file
        """
        if not filepath.endswith('.py'):
            logger.warning(f'{filepath} is not a Python file.')
            return

        logger.info(f'Analyzing file {filepath}...')
        self.filepath = filepath
        with open(filepath, 'r') as file:
            self.code = file.read()
        tree = ast.parse(self.code)

        # add root (ast.Module) to stack with data
        self.stack.append(
            SContext(
                ast_node=tree,
                parent=None,
                namespace=namespace,
            )
        )

        # call handlers until stack is empty
        while self.stack:
            top_node = self.stack.pop()
            top_node_type = 'ast.' + type(top_node.ast_node).__name__
            handler = handlers_dict.get(top_node_type)
            logger.info(f'Handling type {top_node_type} with {handler.__name__}')
            handler(self, top_node)
