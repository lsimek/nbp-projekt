"""
utilities
"""
import ast
from typing import (Union)


def auto_init(namespace, self) -> None:
    """
    execute all commands of type `self.x = x`
    not to be used with *args, **kwargs
    """
    for var, val in namespace.items():
        if var != 'self':
            setattr(self, var, val)


def resolve_attrs(top_node: Union[ast.Attribute, ast.Name]) -> str:
    """
    resolve chains of form Attribute -> Attribute -> ... Attribute -> Name
    into single name
    """
    node = top_node
    name = ''

    while isinstance(node, ast.Attribute):
        name = node.attr + '.' + name if name else node.attr
        node = node.value

    return node.id + '.' + name
