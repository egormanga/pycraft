#!/usr/bin/python3
# PyCraft multiversioning layer

from . import types
from utils import *

def requireProtocolVersion(pv): pv = int(pv); return pv if (pv in _versions) else max(_versions)

class PacketGetter:
	def __init__(self, packet):
		self.packet = packet
	def __repr__(self):
		return f"<PacketGetter of packet {self.packet}>"
	def __getattr__(self, attr):
		return lambda c, *args, **kwargs: self[c.pv].__getattribute__(attr)(c, _protocol=_versions[pv], *args, **kwargs)
	def __getitem__(self, pv):
		return _versions[pv].__getattribute__(self.packet)
class ConstGetter:
	def __init__(self, const):
		self.const = const
	def __repr__(self):
		return f"<ConstGetter of const {self.const}>"
	def __getitem__(self, pv):
		return _versions[pv].__getattribute__(self.const)

def defineConst(name, pv): c = _versions[pv].__getattribute__(name); c.name = name; return c

_versions = dict()
for i in map(lambda x: x.rsplit('/', maxsplit=1)[1].rsplit('.', maxsplit=1)[0], glob.glob(__file__.rsplit('/', maxsplit=1)[0]+'/pv*.py')[::-1]):
	module = importlib.import_module('.'+i, __package__)
	_versions.update({i: module for i in module.PVs})
_dir_diff = set(importlib.import_module('.types', __package__).__dir__())|{'PVs'}
for pv in _versions: globals().update({i: PacketGetter(i) if (type(_versions[pv].__getattribute__(i)) == types.Packet) else defineConst(i, pv) for i in set(_versions[pv].__dir__())-_dir_diff})
del _dir_diff

# by Sdore, 2019
