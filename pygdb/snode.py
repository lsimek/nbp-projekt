import ast
from enum import Enum
from logging_settings import logger
from typing import Union, Tuple, List, Dict


class Dotstring(str):
    @property
    def blocks(self):
        return self.split('.')

    def k_block(self, k):
        return self.split('.')[:k]

    @property
    def wo_first(self):
        idx = self.find('.')
        return self[idx+1:]

    @property
    def wo_last(self):
        ridx = self.rfind('.')
        return self[:ridx]

    @property
    def last(self):
        ridx = self.rfind('.')
        return self[ridx+1:]



class SNodeType(Enum):
    Name = 'name'
    Imported = 'imported'
    Argument = 'argument'
    Attribute = 'attribute'
    Module = 'module'
    Package = 'package'
    Lambda = 'lambda'
    Function = 'function'
    Class = 'class'


class SNode:
    def __init__(
            self,
            fullname: Dotstring,
            namespace: Dotstring = None,
            modulename: str = None,
            packagename: str = None,
            snodetype: SNodeType = SNodeType.Name,
            parent=None,  # type: SNode
            ast_node: ast.AST = None,
            **attrs: Dict
    ):
        self.fullname = fullname
        self.name = fullname.last
        self.namespace = namespace
        self.modulename = modulename
        self.packagename = packagename
        self.snodetype = snodetype
        self.parent = parent
        self.ast_node = ast_node
        self.attrs = attrs

    @property
    def parent_ast_node(self):
        return self.parent.ast_node

    def add_to_attrs(self, **new_attrs):
        self.attrs.update(new_attrs)
