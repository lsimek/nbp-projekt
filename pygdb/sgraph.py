"""
intermediate form of nodes and graphs
to be later imported into a database
"""
from graphviz import Digraph

from logging_settings import logger
from snode import SNode, Dotstring, SNodeType

from enum import Enum
from typing import Tuple, Set, Dict


class SEdgeType(Enum):
    InheritsFrom = 'INHERITS_FROM'
    Argument = 'ARGUMENT'
    AsArgument = 'AS_ARGUMENT'  #
    CalledWith = 'CALLED_WITH'  #
    AttributeOf = 'ATTRIBUTE'
    ImportsFrom = 'IMPORTS_FROM'
    ImportedTo = 'IMPORTED_TO'
    Method = 'METHOD'
    AssignedTo = 'ASSIGNED_TO'
    Decorates = 'DECORATES'
    WithinScope = 'WITHIN_SCOPE'
    TypedWith = 'TYPED_WITH'
    Returns = 'RETURNS'
    InstanceOf = 'INSTANCE_OF'  #
    AssignedToWithin = 'ASSIGNED_TO_WITHIN'
    ReferencedWithin = 'REFERENCED_WITHIN'

    def __hash__(self):
        return hash(self.value)

    @classmethod
    def from_str(cls, string):
        for member in cls.__members__.values():
            if member.value == string:
                return member


class SEdge:
    def __init__(
            self,
            snodes: Tuple[SNode, SNode],
            sedgetype: SEdgeType,
            **attrs
    ):
        self.sedgetype = sedgetype
        self.snodes = snodes
        self.attrs = attrs

    def __hash__(self):
        return hash((self.snodes[0], self.snodes[1], self.sedgetype))

    def __eq__(self, other):
        return (
                self.snodes[0].fullname == other.snodes[0].fullname and
                self.snodes[1].fullname == other.snodes[1].fullname and
                self.sedgetype is other.sedgetype
        )

    @property
    def __dict__(self):
        return self.attrs

    @property
    def first(self):
        return self.snodes[0]

    @property
    def second(self):
        return self.snodes[1]


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
        self.snodes: Dict[Dotstring, SNode] = {}
        self.sedges: Set[SEdge] = set()

    def _add_snode(self, snode: SNode) -> None:
        if snode.fullname not in self.snodes:
            self.snodes.update({
                snode.fullname: snode
            })
        else:
            logger.warning(f'Node `{snode.fullname}` already exists. No actions taken.')

    def add_snodes(self, *snodes) -> None:
        for snode in snodes:
            if isinstance(snode, SNode):
                self._add_snode(snode)
            else:
                raise TypeError(f'Nodes must be of type `SNode`, {type(snode)} was passed instead.')

    def _add_sedge(self, edge: SEdge) -> None:
        first, second = edge.snodes
        if first.fullname not in self.snodes:
            raise ValueError(f'Node {first=} does not exist.')
        if second.fullname not in self.snodes:
            raise ValueError(f'Node {second=} does not exist.')

        self.sedges.add(edge)

    def add_sedges(self, *edges) -> None:
        for edge in edges:
            if isinstance(edge, SEdge):
                self._add_sedge(edge)
            else:
                raise TypeError(f'Edges must be of type `SEdge`, {type(edge)} was passed instead.')

    def visualize(self, output_filename='../_', im_format='png', view=False) -> None:
        """
        visualize sgraph using graphviz
        """
        vis_dict_node = {
            SNodeType.Package: dict(shape='folder'),
            SNodeType.Module: dict(shape='box3d'),
            SNodeType.Class: dict(shape='box'),
            SNodeType.Function: dict(shape='invhouse'),
            SNodeType.Name: dict(shape='ellipse'),
        }

        vis_dict_edge = {
            SEdgeType.WithinScope: dict(style='dotted', arrowhead='vee'),
            SEdgeType.AttributeOf: dict(style='dashed', arrowhead='vee'),
            SEdgeType.ReferencedWithin: dict(style='dotted', arrowhead='vee'),
            SEdgeType.AssignedToWithin: dict(style='dashed', arrowhead='vee')
        }

        gvgraph = Digraph()
        for fullname, node in self.snodes.items():
            gvgraph.node(
                id(node).__str__(),
                label=''.join([
                     '<<FONT COLOR="#444444"><I>{}</I></FONT><BR/>'.format(node.snodetype.value),
                     '<B>{}</B><BR/>'.format(node.name),
                     '<FONT POINT-SIZE="8">{}</FONT>>'.format(fullname)
                 ]),
                fontname='Courier New',
                fontsize='11',
                **vis_dict_node.get(node.snodetype, dict(shape='ellipse'))
            )

        for edge in self.sedges:
            first, second = edge.snodes
            gvgraph.edge(
                id(first).__str__(),
                id(second).__str__(),
                label=edge.sedgetype.value,
                fontname='Courier New',
                fontsize='8',
                **vis_dict_edge.get(edge.sedgetype, dict(style='solid', arrowhead='vee'))
            )

        gvgraph.render(output_filename, format=im_format, view=view)
