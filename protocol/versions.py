#!/usr/bin/python3
# PyCraft Protocol versioning

from utils import *

@cachedfunction
@autocast
def requireProtocolVersion(pv: int): return pv if (pv in PVs) else max(PVs)

class VersionProxy:
	__slots__ = ('side', 'packets')

	def __init__(self, side):
		self.side = side
		self.packets = dict()

	def __getattr__(self, packet):
		if (packet not in self.packets):
			self.packets[packet] = PacketGetter(packet, self.side)
		return self.packets[packet]

class PacketGetter:
	__slots__ = ('packet', 'side')

	def __init__(self, packet, side):
		self.packet, self.side = packet, side

	def __repr__(self):
		return f"<PacketGetter of packet {self.packet}>"

	def __getattr__(self, attr): # TODO consts
		return lambda c, **fields: getattr(self[requireProtocolVersion(c.pv)], attr)(c, **fields)

	def __getitem__(self, pv):
		return getattr(getattr(PVs[pv], self.side), self.packet)

PVs = dict()

for i in map(lambda x: x.rsplit('/', maxsplit=1)[1].rsplit('.', maxsplit=1)[0], glob.glob(__file__.rsplit('/', maxsplit=1)[0]+'/pv*.py')[::-1]): # TODO rewrite?
	module = importlib.import_module('.'+i, __package__)
	for i in module.PVs:
		PVs[i] = module

C = VersionProxy('C')
S = VersionProxy('S')

# by Sdore, 2019
