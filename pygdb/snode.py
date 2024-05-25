import ast
from enum import Enum
from logging_settings import logger
from typing import Optional, Tuple, List, Dict


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

    def concat(self, other):
        return Dotstring(self + '.' + other)



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
            modulename: Optional[str] = None,
            packagename: Optional[str] = None,
            snodetype: SNodeType = SNodeType.Name,
            scope_dict: Dict[Dotstring, Dotstring] = None,
            scope_parent=None,
            ast_parent=None,
            ast_node: Optional[ast.AST] = None,
            **attrs
    ):
        self.fullname = fullname
        self.name = fullname.last
        self.namespace = namespace
        self.modulename = modulename
        self.packagename = packagename
        self.snodetype = snodetype

        # dictionary of {local_name: global_name} 
        self.scope_dict = scope_dict
        
        # parent in context of scope
        self.scope_parent = scope_parent
        
        # oarent in context of AST
        self.ast_parent = ast_parent
        
        # related AST node if any
        self.ast_node = ast_node

        # dictionary of other attributes
        self.attrs = attrs

    @property
    def parent_ast_node(self):
        return self.parent.ast_node

    def add_to_attrs(self, **new_attrs):
        self.attrs.update(new_attrs)

    def get_local(self, name):
        return self.scope_dict.get(self.fullname.concat(name))

    def __repr__(self):
        return self.fullname