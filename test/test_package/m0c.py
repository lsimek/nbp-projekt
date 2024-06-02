import m0a
from m0b import RedClass

RedClass.new_attr = 3

@RedClass
class PurpleClass(RedClass):
    pass

def f():
    return RedClass.new_attr

f(m0a.y)

def g(a: int, b: RedClass) -> RedClass:
    pass

a, _b = RedClass, RedClass.attr + RedClass.attr2
k = _b
x: RedClass = RedClass()