"""
handlers for various ast nodes
during traversal
"""
from logging_settings import logger
from sgraph import *
from scontext import SContext

import ast


# define specific handlers here
def default_handler(svisitor, top_node):
    for child in ast.iter_child_nodes(top_node.ast_node):
        svisitor.stack.append(SContext(
            ast_node=child,
            ast_parent=top_node,
            namespace=top_node.namespace
        ))

#def classdef_handler(svisitor, top_node)

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
