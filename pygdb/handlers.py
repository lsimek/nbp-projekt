"""
handlers for various ast nodes
during traversal
not functional in this commit
"""
from logging_settings import logger
# from sgraph import *
from sgraph import SNode, SNodeType, SEdge, SEdgeType, SGraph
# from scontext import SContext
# from utils import resolve_attrs

import ast
import builtins


# define specific handlers here
def default_handler(svisitor, top_node):
    """
    add children to stack
    """
    for child in ast.iter_child_nodes(top_node.ast_node):
        svisitor.stack.append(SContext(
            ast_node=child,
            parent=top_node,
            namespace=top_node.namespace,
        ))


def module_handler(svisitor, top_node):
    """
    create new node of type module
    add all elements of body to stack
    """
    module_name = svisitor.filepath.replace('/', '.')
    # remove .py
    module_name = module_name[:-len('.py')]
    namespace_name = '.'.join(svisitor.namespace)

    module_snode = SNode(
        fullname=namespace_name + '.' + module_name,
        filename=svisitor.filepath,
        docstring=ast.get_docstring(top_node.ast_node),
        code=None,  # ast.get_source_segment(svisitor.code, top_node.ast_node),
        snodetype=SNodeType.Module,
        pythontype='module',
    )

    svisitor.sgraph.augment_node(module_snode)
    top_node.snode = module_snode

    for body_node in top_node.ast_node.body:
        svisitor.stack.append(SContext(
            ast_node=body_node,
            parent=top_node,
            namespace=top_node.namespace + [module_name]
        ))


def classdef_handler(svisitor, top_node):
    """
    create new node of type class
    handle bases and decorators
    not implemented: handle metaclass
    add WithinScope edge
    add all elements of list `body` to stack
    """
    namespace_name = '.'.join(top_node.namespace)
    fullname = namespace_name + '.' + top_node.ast_node.name
    class_snode = SNode(
        fullname=fullname,
        filename=svisitor.filepath,
        docstring=ast.get_docstring(top_node.ast_node),
        lineno=top_node.ast_node.lineno,
        code=ast.get_source_segment(svisitor.code, top_node.ast_node),
        snodetype=SNodeType.Class,
        pythontype='class',
    )

    class_snode = svisitor.sgraph.augment_node(class_snode)
    top_node.snode = class_snode

    for decorator in top_node.ast_node.decorator_list:
        decorator_name = resolve_attrs(decorator)

        decorator_name = namespace_name + '.' + decorator_name
        decorator_snode = SNode(
            fullname=decorator_name,
            snodetype=SNodeType.Name,
        )

        decorator_snode = svisitor.sgraph.augment_node(decorator_snode)
        svisitor.sgraph.add_edges(SEdge(
            nodes=(decorator_snode, class_snode),
            sedgetype=SEdgeType.Decorates
        ))

    for base in top_node.ast_node.bases:
        base_name = resolve_attrs(base)

        # if not found mark fullname with *, else make concordant with existing node
        base_name = namespace_name + '.' + base_name
        base_snode = SNode(
            fullname=base_name,
            snodetype=SNodeType.Class,
            pythontype='class'
        )
        base_snode = svisitor.sgraph.augment_node(base_snode)
        svisitor.sgraph.add_edges(SEdge(
            nodes=(class_snode, base_snode),
            sedgetype=SEdgeType.InheritsFrom
        ))

    # node = top_node
    # while node.parent is not None:
    #     if (
    #         isinstance(node, ast.Module) or
    #         isinstance(node, ast.FunctionDef) or
    #         isinstance(node, ast.AsyncFunctionDef) or
    #         isinstance(node, ast.ClassDef)
    #     ):
    #         scope_snode = node.snode
    #         svisitor.graph.add_edges(SEdge(
    #             nodes=(class_snode, scope_snode),
    #             sedgetype=SEdgeType.WithinScope
    #         ))
    #         break
    #     node = node.parent
    # else:
    #     logger.warning(f'Scope node could not be found for {fullname}')
    scope_subhandler(svisitor, top_node)

    for body_node in top_node.ast_node.body:
        svisitor.stack.append(SContext(
            ast_node=body_node,
            parent=top_node,
            namespace=top_node.namespace + [top_node.ast_node.name],
        ))


def functiondef_handler(svisitor, top_node):
    """
    create new node of type function
    handle args, decorators and type comments
    add WithinScope edge
    add all elements of list `body` to stack
    """
    namespace_name = '.'.join(top_node.namespace)
    fullname = namespace_name + '.' + top_node.ast_node.name
    func_snode = SNode(
        fullname=fullname,
        filename=svisitor.filepath,
        docstring=ast.get_docstring(top_node.ast_node),
        lineno=top_node.ast_node.lineno,
        code=ast.get_source_segment(svisitor.code, top_node.ast_node),
        snodetype=SNodeType.Function,
        pythontype='function',
    )
    func_snode = svisitor.sgraph.augment_node(func_snode)
    top_node.snode = func_snode

    # add return type if given
    if hasattr(top_node.ast_node, 'returns'):
        typing_subhandler(svisitor, top_node, top_node.ast_node.returns)

    for decorator in top_node.ast_node.decorator_list:
        decorator_name = resolve_attrs(decorator)

        decorator_name = namespace_name + '.' + decorator_name
        decorator_snode = SNode(
            fullname=decorator_name,
            snodetype=SNodeType.Name,
        )

        decorator_snode = svisitor.sgraph.augment_node(decorator_snode)
        svisitor.sgraph.add_edges(SEdge(
            nodes=(decorator_snode, func_snode),
            sedgetype=SEdgeType.Decorates
        ))

    # arguments and their types
    if hasattr(top_node.ast_node, 'args'):
        args_node = top_node.ast_node.arguments
        # indicators=(
        #     ['posonly'] * len(args_node.posonlyargs) +
        #     ['ignore'] * len(args_node.args) +
        #     ['kwonly'] * len(args_node.kwonlyargs) +
        #     ['vararg'] * len(args_node.vararg)
        # )
        for arg_node in args_node.args:
            arg_snode = SNode(
                fullname=namespace_name + '.' + arg_node.arg,
                snodetype=SNodeType.Argument,
                # other_attrs={arg_indicator: True} if arg_indicator != 'ignore' else None
            )

            arg_snode = svisitor.sgraph.augment_node(arg_snode)

            svisitor.sgraph.add_edges(SEdge(
                nodes=(arg_snode, func_snode),
                sedgetype=SEdgeType.WithinScope
            ))

            typing_subhandler(svisitor, SContext(arg_node, top_node, arg_snode, top_node.namespace + [arg_node.arg]), arg_node.annotation)

    # default values
    # to be implemented

    # node = top_node
    # while node.parent is not None:
    #     if (
    #         isinstance(node, ast.Module) or
    #         isinstance(node, ast.FunctionDef) or
    #         isinstance(node, ast.AsyncFunctionDef) or
    #         isinstance(node, ast.ClassDef)
    #     ):
    #         scope_snode = node.snode
    #         svisitor.graph.add_edges(SEdge(
    #             nodes=(func_snode, scope_snode),
    #             sedgetype=SEdgeType.WithinScope
    #         ))
    #         break
    #     node = node.parent
    # else:
    #     logger.warning(f'Scope node could not be found for {fullname}')
    scope_subhandler(svisitor, top_node)

    for body_node in top_node.ast_node.body:
        svisitor.stack.append(SContext(
            ast_node=body_node,
            parent=top_node,
            namespace=top_node.namespace + [top_node.ast_node.name]
        ))

def asyncfunctiondef_handler(svisitor, top_node):
    """
    same as for sync functions
    possible addition: add `async` attribute
    to function snodes
    """
    functiondef_handler(svisitor, top_node)


# dictionary of handlers
# items: 'ast.cls': cls_handler
# generated dynamically below
# when there is no function named cls_handler
# `default_handler` is used
handlers_dict = {}

# add default handler to all other classes
for ast_cls in dir(ast):
    ast_cls_wp = 'ast.' + ast_cls
    handler_name = f'{ast_cls.lower()}_handler'
    handler = globals().get(handler_name, default_handler)
    handlers_dict.update({ast_cls_wp: handler})


# subhandlers, utilities used by various handlers
def typing_subhandler(svisitor, top_node, returns_node):
    """
    analyze typing
    """
    if isinstance(returns_node, ast.Name) and returns_node.id in dir(builtins):
        top_node.snode.other_attrs.update({'type': returns_node.id})
        # top_node.pythontype = returns_node.id
    # else it is some class (we don't analyze types given with more advanced typing)
    elif isinstance(returns_node, ast.Attribute) or isinstance(returns_node, ast.Name):
        type_fullname = top_node.snode.fullname + resolve_attrs(returns_node)
        type_snode = SNode(
            fullname=type_fullname,
            snodetype=SNodeType.Class,
            pythontype='class'
        )
        type_snode = svisitor.sgraph.augment_node(type_snode)
        svisitor.sgraph.add_edges(SEdge(
            nodes=(top_node.snode, type_snode),
            sedgetype=SEdgeType.TypedWith
        ))


def scope_subhandler(svisitor, top_node):
    """
    find scope
    """
    node = top_node
    while node is not None:
        if (
            isinstance(node.ast_node, ast.Module) or
            isinstance(node.ast_node, ast.FunctionDef) or
            isinstance(node.ast_node, ast.AsyncFunctionDef) or
            isinstance(node.ast_node, ast.ClassDef)
        ) and node != top_node:
            scope_snode = node.snode
            svisitor.sgraph.add_edges(SEdge(
                nodes=(top_node.snode, scope_snode),
                sedgetype=SEdgeType.WithinScope
            ))
            break
        node = node.parent
    else:
        logger.warning(f'Scope node could not be found for {top_node.snode.fullname}')


def add_body_subhandler(svisitor, top_node):
    pass


def add_children_subhandler(svisitor, top_node):
    pass
