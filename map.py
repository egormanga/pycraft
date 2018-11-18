#!/usr/bin/python3
# PyCraft map and chunks utilities

from utils import *; logstart('Map')
from .commons import *
from .protocol import *

class Block(Updatable):
	def __init__(self,
		x: int,
		y: int,
		z: int,
		id: int,
		data: int,
	):
		self.update(locals())
	def __bool__(self):
		return bool(self.id)

class ChunkSection(Updatable):
	def __init__(self,
		y: int,
		blocks: list,
	):
		self.update(locals())
	def __bool__(self):
		return any(self.blocks)
	def pack(self):
		return bytes().join((
			writeUByte(14), # Bits Per Block
			b'', # Palette
			writeVarInt(1), # Data Array Length
			writeLong(2 << 4), # Data Array (grass tmp.)
			writeByte(0), # Block Light
			writeByte(0), # Sky Light
		))

class Chunk(Updatable):
	def __init__(self,
		x: int,
		z: int,
		chunks: list,
	):
		self.update(locals())
	def pack(self, ground_up_continuous=True):
		data = bytes().join(i.pack() for i in self.chunks) + writeByte(127)*256 # TODO FIXME
		#blocks = [j.pack() for j in i.blocks for i in self.chunks]
		return bytes().join((
			writeInt(self.x), # Chunk X
			writeInt(self.z), # Chunk Z
			writeBool(ground_up_continuous), # Ground-Up Continuous
			writeVarInt(sum(1 << y for y in range(16) if (len(self.chunks) > y and self.chunks[y]))), # Primary Bit Mask
			writeVarInt(len(data)), # Size
			data, # Data
			writeVarInt(0), # Number of block entities
			b'', # Block entities
		))

testchunk = Chunk(0, 0, [
	ChunkSection(0, [
		Block(0, 0, 0, 2, 0)
	])
])

if (__name__ == '__main__'): logstarted(); exit()
else: logimported()

# by Sdore, 2018
