import ast
from enum import Enum
from typing import Optional, List, Dict, Union


class Dotstring(str):
    def __getitem__(self, *args, **kwargs):
        return Dotstring(super().__getitem__(*args, **kwargs))

    @property
    def blocks(self):
        return self.split('.')

    def k_block(self, k):
        return self.split('.')[k]

    @property
    def first(self):
        idx = self.find('.')
        return self[:idx] if idx != -1 else self

    @property
    def wo_first(self):
        idx = self.find('.')
        return self[idx+1:] if idx != -1 else Dotstring('')

    @property
    def last(self):
        ridx = self.rfind('.')
        return self[ridx+1:] if ridx != -1 else self

    @property
    def wo_last(self):
        ridx = self.rfind('.')
        return self[:ridx] if ridx != -1 else Dotstring('')

    def concat(self, other):
        if self and other:
            return Dotstring(self + '.' + other)
        elif self:
            return self
        elif other:
            return Dotstring(other)
        else:
            return ''

    @staticmethod
    def from_list(li: List):
        return Dotstring('.'.join(li))

    def concat_rel(self, suffix: str):
        buffer = self

        if suffix.startswith('..'):
            buffer = buffer.wo_last
            suffix = suffix[2:]

        if suffix.startswith('.'):
            suffix = suffix[1:]

        segments = suffix.split('..')
        for segment in segments[:-1]:
            buffer = buffer.concat(Dotstring(segment).wo_last)

        buffer = buffer.concat(segments[-1])
        return buffer


class SNodeType(Enum):
    Name = 'Name'
    Module = 'Module'
    Package = 'Package'
    Function = 'Function'
    Class = 'Class'

    @classmethod
    def from_str(cls, string):
        for member in cls.__members__.values():
            if member.value == string:
                return member


class SNode:
    def __init__(
            self,
            fullname: Dotstring,
            name: Optional[Union[str, Dotstring]] = None,
            namespace: Optional[Dotstring] = None,
            modulename: Optional[str] = None,
            packagename: Optional[str] = None,
            snodetype: SNodeType = SNodeType.Name,
            scope_dict: Dict[Dotstring, Dotstring] = None,
            scope_parent=None,
            **attrs
    ):
        self.fullname = fullname
        self.name = Dotstring(name) if name is not None else fullname.last
        self.namespace = namespace
        self.modulename = modulename
        self.packagename = packagename
        self.snodetype = snodetype

        # dictionary of {local_name: global_name} 
        self.scope_dict = scope_dict
        
        # parent in context of scope
        self.scope_parent = scope_parent

        # dictionary of other attributes
        self.attrs = attrs

    def add_to_attrs(self, **new_attrs):
        self.attrs.update(new_attrs)

    def get_local(self, name):
        return self.scope_dict.get(self.fullname.concat(name))

    def __repr__(self):
        return self.fullname

    @property
    def __dict__(self):
        di = {
            'fullname': self.fullname,
            'name': self.name,
            'namespace': self.namespace,
            'moduleName': self.modulename,
            'packageName': self.packagename,
        }

        di.update({k: v for k, v in self.attrs.items() if not k.startswith('__')})
        return di

