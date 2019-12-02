#!/usr/bin/python3
# PyCraft world (map) handling utilities

from . import *

class Block(Updatable):
	x: int
	y: int
	z: int
	id: int
	data: int
	onupdate: lambda: noop

	def __init__(self, x, y, z):
		self.x, self.y, self.z = x, y, z

	def __repr__(self):
		return f"<Block #{self.id}:{self.data} @ {self.x, self.y, self.z}>"

	def __bool__(self):
		return bool(self.id)

	def set(self, id, data=0):
		self.id, self.data = id, data
		self.onupdate(self)

class Chunk(Updatable):
	x: int
	y: int
	z: int
	blocks: dict
	chunksec: None
	onblockcreate: lambda: noop
	onblockupdate: lambda: noop

	def __init__(self, x, y, z, *, chunksec=None):
		self.x, self.y, self.z, self.chunksec = x, y, z, chunksec

	def __repr__(self):
		return f"<Chunk @ {self.x, self.y, self.z}>"

	def __bool__(self):
		return any(self.blocks.values())

	def __getitem__(self, pos):
		x, y, z = pos
		if ((x, y, z) not in self.blocks):
			block = self.blocks[x, y, z] = Block(x+self.x, y+self.y, z+self.z)
			block.onupdate = self.onblockupdate
			self.onblockcreate(block)
		else: block = self.blocks[x, y, z]
		return block

	@property
	def blockids_bytes(self):
		return bytes(self.blocks[x, y, z].id if ((x, y, z) in self.blocks) else 0 for y in range(16) for z in range(16) for x in range(16))

	@property
	def blockdata_bytes(self):
		return bytes(self.blocks[x, y, z].data if ((x, y, z) in self.blocks) else 0 for y in range(16) for z in range(16) for x in range(16))

class ChunkSection(Updatable):
	x: int
	z: int
	chunks: dict
	map: None
	onchunkcreate: lambda: noop
	onblockcreate: lambda: noop
	onblockupdate: lambda: noop

	def __init__(self, x, z, *, map=None):
		self.x, self.z, self.map = x, z, map

	def __repr__(self):
		return f"<ChunkSection @ {self.x, self.z}>"

	def __bool__(self):
		return any(self.chunks.values())

	def __getitem__(self, pos):
		x, y, z = pos
		cy = y//16
		if (cy not in self.chunks):
			chunk = self.chunks[cy] = Chunk(self.x, cy*16, self.z, chunksec=self)
			chunk.onblockcreate = self.onblockcreate
			chunk.onblockupdate = self.onblockupdate
			self.onchunkcreate(chunk)
		else: chunk = self.chunks[cy]
		return chunk[x, y-cy*16, z]

	@dispatch
	def load(self, pbm, abm, data: bytes):
		i = int()
		for cy in range(16):
			if (not pbm & (1 << cy)): continue
			ch = self.chunks[cy]
			for y in range(16):
				for z in range(16):
					for x in range(16):
						ch[x, y, z].id = data[i]
						i += 1
		for cy in range(16):
			if (not pbm & (1 << cy)): continue
			ch = self.chunks[cy]
			for y in range(16):
				for z in range(16):
					for x in range(16):
						ch[x, y, z].id = data[int(i)] & (0x0f << 4*bool(i % 1))
						i += .5
		assert (i.is_integer())

	@itemget
	def chunkdata_bytes(self, pbm):
		cd = bytearray()
		cd += bytes().join(self.chunks[cy].blockids_bytes if (pbm & (1 << cy) and cy in self.chunks) else b'\0'*(16*16*16) for cy in range(16))
		cd += bytes().join(self.chunks[cy].blockdata_bytes if (pbm & (1 << cy) and cy in self.chunks) else b'\0'*(16*16*16) for cy in range(16))
		return bytes(cd)

class Map(Updatable):
	dimension: int
	chunksec: dict
	world: None
	onchunksectioncreate: lambda: noop
	onchunkcreate: lambda: noop
	onblockcreate: lambda: noop
	onblockupdate: lambda: noop

	def __init__(self, dimension, *, world=None):
		self.dimension, self.world = dimension, world

	def __repr__(self):
		return f"<Map DIM{self.dimension}>"

	def __bool__(self):
		return bool(self.chunksec)

	def __getitem__(self, pos):
		x, y, z = pos
		cx, cz = x//16, z//16
		if ((cx, cz) not in self.chunksec):
			chunksec = self.chunksec[cx, cz] = ChunkSection(cx*16, cz*16, map=self)
			chunksec.onchunkcreate = self.onchunkcreate
			chunksec.onblockcreate = self.onblockcreate
			chunksec.onblockupdate = self.onblockupdate
			self.onchunksectioncreate(chunksec)
		else: chunksec = self.chunksec[cx, cz]
		return chunksec[x-cx*16, y, z-cz*16]

	@dispatch
	def load(self, cx, cz, pbm, abm, data: bytes):
		if ((cx, cz) not in self.chunksec):
			self.chunksec[cx, cz] = ChunkSection(cx*16, cz*16, map=self)
			self.onchunksectioncreate(self.chunksec[cx, cz])
		self.chunksec[cx, cz].load(pbm, abm, data)

class World(Updatable):
	maps: dict
	ondimensioncreate: lambda: noop
	onchunksectioncreate: lambda: noop
	onchunkcreate: lambda: noop
	onblockcreate: lambda: noop
	onblockupdate: lambda: noop

	def __repr__(self):
		return f"<World>"

	def __bool__(self):
		return any(self.maps.values())

	@autocast
	def __getitem__(self, dimension: int):
		if (dimension not in self.maps):
			map = self.maps[dimension] = Map(dimension, world=self)
			map.onchunksectioncreate = self.onchunksectioncreate
			map.onchunkcreate = self.onchunkcreate
			map.onblockcreate = self.onblockcreate
			map.onblockupdate = self.onblockupdate
			self.ondimensioncreate(map)
		else: map = self.maps[dimension]
		return map

	@classmethod
	def open(cls, path):
		raise NotImplementedError()

	def save(self, path): # TODO
		pass

# by Sdore, 2019
