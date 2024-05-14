"""
module docstring
"""

import ast
from importlib import reload
import numpy as np
x = np.array([1, 2])

def f(x: int):
    """
    function docstring
    """
    
    y = x
    return y

@unknown_decorator
class B(ast.AST, metaclass=type):
    b = 3

    def __init__(a, b):
        x = 5
        self.a = x
        self.b = 4