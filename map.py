#!/usr/bin/python3
# PyCraft map and chunks utilities

from . import *

class Block(Updatable):
	id: int
	data: int

	def __bool__(self):
		return bool(self.id)

class Chunk(Updatable):
	x: int
	z: int
	blocks: [Block() for _ in range(16*16*256)]

	def __bool__(self):
		return any(self.blocks)

	def __getitem__(self, pos):
		x, y, z = pos
		return self.blocks[y*256+z*16+x]

testchunk = Chunk()
for x in range(16):
	for z in range(16):
		testchunk[x, 0, z].id = 1
testchunk[3, 1, 4].id = 1

# by Sdore, 2019
