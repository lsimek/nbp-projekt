"""
class that represents an ast node,
together with some context relevant
for handling
"""
import ast
from typing import Union, List
from copy import copy, deepcopy


class SContext:
    """
    class for context during ast traversal
    contains AST node and other data
    """

    def __init__(
            self,
            ast_node: ast.AST,
            parent=None,  # type: Union[SContext, None]
            snode=None,
            namespace: List[str] = [],
            filename: str = None,
    ):
        self.ast_node = copy(ast_node)
        self.parent = copy(parent)
        self.snode = snode
        self.namespace = copy(namespace)
