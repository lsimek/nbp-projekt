"""
intermediate form of nodes and graphs
to be later imported into a database
"""
from graphviz import Digraph

from logging_settings import logger
from snode import SNode, Dotstring, SNodeType

from enum import Enum
from typing import Tuple, List, Dict


class SEdgeType(Enum):
    Refers = 'REFERS'
    InheritsFrom = 'INHERITS_FROM'
    Arg = 'ARG'
    AsArg = 'AS_ARG'
    AttributeOf = 'ATTRIBUTE_OF'
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
            **attrs
    ):
        self.sedgetype = sedgetype
        self.nodes = nodes
        self.attrs = attrs


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
        self.nodes: Dict[Dotstring, SNode] = {}
        self.edges: List[SEdge] = []

    def _add_node(self, node: SNode):
        if node.fullname not in self.nodes:
            self.nodes.update({
                node.fullname: node
            })
        else:
            logger.warning(f'Node `{node.fullname}` already exists. No actions taken.')

    def add_nodes(self, *nodes):
        for node in nodes:
            if isinstance(node, SNode):
                self._add_node(node)
            else:
                raise TypeError(f'Nodes must be of type `SNode`, {type(node)} was passed instead.')

    def _add_edge(self, edge: SEdge):
        first, second = edge.nodes
        if first.fullname not in self.nodes:
            raise ValueError(f'Node {first=} does not exist.')
        if second.fullname not in self.nodes:
            raise ValueError(f'Node {second=} does not exist.')

        self.edges.append(edge)

    def add_edges(self, *edges):
        for edge in edges:
            if isinstance(edge, SEdge):
                self._add_edge(edge)
            else:
                raise TypeError(f'Edges must be of type `SEdge`, {type(edge)} was passed instead.')

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
                fontsize=str(fontsize),
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
