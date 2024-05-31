import m0a
from m0b import RedClass

RedClass.new_attr = 3

@RedClass
class PurpleClass(RedClass):
    pass

def f():
    pass

f(m0a.y)
