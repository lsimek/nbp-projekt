"""
intermediate form of nodes and graphs
to be later imported into a database
"""
from graphviz import Digraph

from utils import auto_init
from logging_settings import logger

import ast
from enum import Enum
from typing import Union, Tuple, List, Dict


class SNodeType(Enum):
    Name = 'name'
    # Imported = 'imported'
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
            fullname: str,
            filename: Union[str, None] = None,
            docstring: Union[str, None] = None,
            lineno: Union[int, None] = None,
            code: Union[str, None] = None,
            snodetype: SNodeType = SNodeType.Name,
            pythontype: Union[str, None] = None,
            conditional: Union[bool, None] = None,
            other_attrs: Dict = {},
    ):
        auto_init(locals(), self)
        self.name = self.fullname[self.fullname.rfind('.') + 1:]


class SEdgeType(Enum):
    Refers = 'REFERS'
    InheritsFrom = 'INHERITS_FROM'
    Arg = 'ARG'
    AsArg = 'AS_ARG'
    ImportedFrom = 'IMPORTED_FROM'
    PartOf = 'PART_OF'
    Method = 'METHOD'
    AssignedAs = 'ASSIGNED_AS'
    Decorates = 'DECORATES'
    WithinScope = 'WITHIN_SCOPE'
    TypedWith = 'TYPED_WITH'
    Returns = 'RETURNS'


class SEdge:
    def __init__(
            self,
            nodes: Tuple[SNode, SNode],
            sedgetype: SEdgeType = SEdgeType.Refers,
            **kwargs
    ):
        self.sedgetype = sedgetype
        self.nodes = nodes
        for k, v in kwargs.items():
            setattr(self, k, v)


class SGraph:
    """
    intermediate graph form
    """
    def __init__(self):
        """
        dictionary of the form
            node fullname: SNode object
        list of edges
        """
        self.nodes: Dict[SNode] = {}
        self.edges: List[SEdge] = []

    def _add_node(self, node: SNode):
        if node.fullname not in self.nodes.keys():
            self.nodes.update({
                node.fullname: node
            })
        else:
            logger.warning(f'Node `{node.fullname}` already exists.')

    def add_nodes(self, *nodes):
        for node in nodes:
            if isinstance(node, SNode):
                self._add_node(node)
            else:
                raise TypeError(f'Nodes must be of type `SNode`, {type(node)} was passed instead.')

    def _add_edge(self, edge: SEdge):
        first, second = edge.nodes
        if first.fullname in self.nodes and second.fullname in self.nodes:
            self.edges.append(edge)
        else:
            raise ValueError(f'Nodes referenced (fullnames {edge.nodes[0].fullname} and {edge.nodes[1].fullname})'
                             f'do not exist.')

    def add_edges(self, *edges):
        for edge in edges:
            if isinstance(edge, SEdge):
                self._add_edge(edge)
            else:
                raise TypeError(f'Edges must be of type `SEdge`, {type(edge)} was passed instead.')

    def augment_node(self, node: SNode) -> SNode:
        """
        if node does not exist, add it and return it
        if node does exist, merge the new node into existing and return it
        """
        if node.fullname not in self.nodes.keys():
            self.nodes.update({
                node.fullname: node
            })
            return node
        else:
            old_node = self.nodes.get(node.fullname)
            if old_node.snodetype == SNodeType.Name:
                old_node.snodepe = node.snodetype
            for attr in dir(node):
                if attr != 'fullname' and attr != 'other_attrs':
                    setattr(old_node, attr, getattr(node, attr))
            old_node.other_attrs.update(node.other_attrs)
            return old_node

    def visualize(self, output_filename='../_', view=False, fontsize=11) -> None:
        """
        visualize sgraph using graphviz
        """
        gvgraph = Digraph()
        for fullname, node in self.nodes.items():
            gvgraph.node(
                id(node).__str__(),
                '\n'.join([node.snodetype.value, fullname, node.name]),
                fontname='Courier New',
                fontsize=str(fontsize)
            )

        for edge in self.edges:
            first, second = edge.nodes
            gvgraph.edge(
                id(first).__str__(),
                id(second).__str__(),
                label=edge.sedgetype.value,
                fontname='Courier New',
                fontsize=str(fontsize - 3)
            )

        gvgraph.render(output_filename, format='png', view=view)
