import ast
from enum import Enum
from typing import Union, Tuple

def auto_init(namespace, excl):
    """
    execute all commands of type `self.x = x`
    not to be used with *args, **kwargs
    """
    for var, val in namespace.items():
        if var != 'self':
            setattr(self, var, val)


# class SContext:
#     """
#     manage context of ancestors in AST (or other?)
#     """
#     def __init__(self, parent: ast.AST, context: SContext):
#         auto_init(self, locals())
# 
#     def __iter__(self):
#         pass
#     """
#     unfinished: maybe just add .parent attr to AST nodes?
#     """

class SNodeType(Enum):
    Name = 'name'
    Imported = 'imported'
    Attribute = 'attribute'
    Module = 'module'
    Package = 'package'
    Function = 'function'
    Class = 'class'


class SNode:
    def __init__(
                self,
                fullname: str,
                parent: ast.AST,
                filename: Union[str, None]=None,
                docstring: Union[str, None]=None,
                lineno: Union[int, None]=None,
                code: Union[str, None]=None,
                snodetype: SNodeType=SNodeType.Name,
                conditional: Union[bool, None]=None
            ):
        auto_init(self, locals())
        self.name = self.fullname[self.fullname.rfind('.') + 1:]


class SEdgeType(Enum):
    Refers = 'REFERS'
    Arg = 'ARG'
    AsArg = 'AS_ARG'
    ImportedFrom = 'IMPORTED_FROM'
    PartOf = 'PART_OF'
    Method = 'METHOD'
    AssignedAs = 'ASSIGNED_AS'
    Decorates = 'DECORATES'
                
class SEdge:
    def __init__(
                self,
                sedgetype: SEdgeType,
                nodes: Tuple[SNode, SNode],
                **kwargs
            ):
        self.sedgetype = sedgetype
        self.nodes = nodes
        for k, v in kwargs.items():
            setattr(self, k, v)


class SGraph:
    def __init__(
                self,
            ):
        pass

