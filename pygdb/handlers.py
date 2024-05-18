import ast

# define specific handlers here
def default_handler(svisitor, pop=True):
    node = svisitor.context.pop()
    
    for child in ast.iter_child_nodes(node):
        svisitor.context.append(child)
        child.parent = node

# dictionary of handlers
handlers_dict = {}

# add default handler to all other classes
for ast_cls in dir(ast):
    ast_cls = 'ast.' + ast_cls
    if ast_cls not in handlers_dict.keys():
        handlers_dict.update({ast_cls: default_handler})


