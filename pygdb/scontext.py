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
            ast_parent=None,  # type: Union[SContext, None]
            namespace: List[str] = [],
    ):
        self.ast_node = copy(ast_node)
        self.ast_parent = copy(ast_parent)
        self.namespace = copy(namespace)
