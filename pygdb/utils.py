"""
utilities
"""
def auto_init(namespace, self):
    """
    execute all commands of type `self.x = x`
    not to be used with *args, **kwargs
    """
    for var, val in namespace.items():
        if var != 'self':
            setattr(self, var, val)
