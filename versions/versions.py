#!/usr/bin/python3
# PyCraft multiversioning layer

import glob, importlib
from ..protocol import *

_versions = {int(i[2:]): importlib.import_module('.'+i, __package__) for i in map(lambda x: x.rsplit('/', maxsplit=1)[1].rsplit('.', maxsplit=1)[0], glob.glob(__file__.rsplit('/', maxsplit=1)[0]+'/pv*.py'))}

def requireProtocolVersion(pv): pv = int(pv); return pv if (pv in _versions) else max(_versions)

class PacketImplGetter:
	def __init__(self, packet):
		self.packet = packet
	def __getattr__(self, attr):
		return PacketImpl(self.packet, attr)
	def __getitem__(self, pv):
		return _versions[pv].__getattribute__(self.packet)
class PacketImpl:
	def __init__(self, packet, attr):
		self.packet, self.attr = packet, attr
	def __call__(self, c, *args, **kwargs):
		return type.__getattribute__(_versions[c.pv].__getattribute__(self.packet), self.attr)(c, *args, **kwargs)

for i in _versions[max(_versions)].__all__: globals()[i] = PacketImplGetter(i)

# by Sdore, 2018
