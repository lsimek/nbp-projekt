"""
standalone module
for testing and debugging
"""

import ast
from mod1 import func1
import mod2

a = 1
b = func1

def f(x, y):
    """
    f docstring
    """
    def g(y, w):
        """
        g docstring
        """
        x = 3
        z = 4
        b = 7


class A:
    """
    class A docstring
    """

    new_var = 5
    a.b.c.d.e = 10
    new_name = SomeClass()  # wo this line, new_name is marked as imported
    new_name.b.c.d.e = 10

    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c