#!/usr/bin/python3
# PyCraft world (map) handling utilities

from . import *

class Block(Updatable):
	x: int
	y: int
	z: int
	id: int
	data: int
	chunk: None

	def __init__(self, x, y, z, *, chunk=None):
		self.x, self.y, self.z, self.chunk = x, y, z, chunk

	def __repr__(self):
		return f"<Block #{self.id}:{self.data} @ {self.x, self.y, self.z}>"

	def __bool__(self):
		return bool(self.id)

	@dispatch
	def set(self, id: int, data: int = 0):
		self.id, self.data = id, data
		if (self.chunk is not None and
		    self.chunk.chunksec is not None and
		    self.chunk.chunksec.map is not None and
		    self.chunk.chunksec.map.world is not None and
		    self.chunk.chunksec.map.world.onblockupdate is not None): self.chunk.chunksec.map.world.onblockupdate(self)

class Chunk(Updatable):
	x: int
	y: int
	z: int
	blocks: dict
	chunksec: None

	def __init__(self, x, y, z, *, chunksec=None):
		self.x, self.y, self.z, self.chunksec = x, y, z, chunksec

	def __repr__(self):
		return f"<Chunk @ {self.x, self.y, self.z}>"

	def __bool__(self):
		return any(self.blocks.values())

	def __getitem__(self, pos):
		x, y, z = map(int, pos)
		try: return self.blocks[x, y, z]
		except KeyError:
			block = self.blocks[x, y, z] = Block(x+self.x, y+self.y, z+self.z, chunk=self)
			if (self.chunksec is not None and
			    self.chunksec.map is not None and
			    self.chunksec.map.world is not None and
			    self.chunksec.map.world.onblockcreate is not None): self.chunksec.map.world.onblockcreate(block)
			return block

	def __setitem__(self, pos, v):
		xs, ys, zs = (tuple(range(*i.indices(16))) if (isinstance(i, slice)) else (int(i),) for i in pos)
		if (not isinstance(v, tuple)): v = (v,)
		for y in ys:
			for z in zs:
				for x in xs:
					self[x, y, z].set(*v)

	@property
	def blockids_bytes(self):
		return bytes(self.blocks[x, y, z].id if ((x, y, z) in self.blocks) else 0 for y in range(16) for z in range(16) for x in range(16))

	@property
	def blockdata_bytes(self):
		return bytes(((self.blocks[x, y, z].data & 0xf) << 4 if ((x, y, z) in self.blocks) else 0) | (self.blocks[x+1, y, z].data & 0xf if ((x+1, y, z) in self.blocks) else 0) for y in range(16) for z in range(16) for x in range(0, 16, 2))

	@property
	def abm(self):
		return 0 # TODO FIXME

class ChunkSection(Updatable):
	x: int
	z: int
	chunks: dict
	map: None

	def __init__(self, x, z, *, map=None):
		self.x, self.z, self.map = x, z, map

	def __repr__(self):
		return f"<ChunkSection @ {self.x, self.z}>"

	def __bool__(self):
		return any(self.chunks.values())

	def __getitem__(self, pos):
		x, y, z = map(int, pos)
		cy = y//16
		return self.getchunk(cy)[x, y-cy*16, z]

	def __setitem__(self, pos, v):
		xs, ys, zs = pos
		if (not isinstance(v, tuple)): v = (v,)
		for y in range(*ys.indices(256)) if (isinstance(ys, slice)) else (int(ys),):
			cy = y//16
			self.getchunk(cy)[xs, y-cy*16, zs] = v

	def getchunk(self, cy):
		try: return self.chunks[cy]
		except KeyError:
			chunk = self.chunks[cy] = Chunk(self.x, cy*16, self.z, chunksec=self)
			if (self.map is not None and
			    self.map.world is not None and
			    self.map.world.onchunkcreate is not None): self.map.world.onchunkcreate(chunk)
			return chunk

	@dispatch
	def load(self, pbm, abm, data: bytes):
		pbm %= (1 << 16)
		i = int()
		for cy in range(16):
			if (not pbm & (1 << cy)): continue
			chunk = self.getchunk(cy)
			for y in range(16):
				for z in range(16):
					for x in range(16):
						if (data[i]): chunk[x, y, z].id = data[i]
						i += 1
		for cy in range(16):
			if (not pbm & (1 << cy)): continue
			chunk = self.getchunk(cy)
			for y in range(16):
				for z in range(16):
					for x in range(0, 16, 2):
						if (data[i] & 0xf0): chunk[x, y, z].data = data[i] & 0xf0
						if (data[i] & 0x0f): chunk[x+1, y, z].data = data[i] & 0x0f
						i += 1

	@itemget
	def chunkdata_bytes(self, pbm):
		pbm %= (1 << 16)
		abm, cd = int(), bytearray()
		cd += bytes().join(self.chunks[cy].blockids_bytes if (pbm & (1 << cy) and cy in self.chunks) else b'\0'*(16*16*16) for cy in range(16))
		cd += bytes().join(self.chunks[cy].blockdata_bytes if (pbm & (1 << cy) and cy in self.chunks) else b'\0'*(16*16*16//2) for cy in range(16))
		return (abm, bytes(cd))

class Map(Updatable):
	dimension: int
	chunksec: dict
	world: None

	def __init__(self, dimension, *, world=None):
		self.dimension, self.world = dimension, world

	def __repr__(self):
		return f"<Map DIM{self.dimension}>"

	def __bool__(self):
		return bool(self.chunksec)

	def __getitem__(self, pos):
		x, y, z = map(int, pos)
		cx, cz = x//16, z//16
		return self.getchunksec(cx, cz)[x-cx*16, y, z-cz*16]

	def __setitem__(self, pos, v):
		xs, ys, zs = pos
		if (not isinstance(v, tuple)): v = (v,)
		for z in range(zs.start, zs.stop, zs.step or 1) if (isinstance(zs, slice)) else (int(zs),):
			cz = z//16
			for x in range(xs.start, xs.stop, xs.step or 1) if (isinstance(xs, slice)) else (int(xs),):
				cx = x//16
				self.getchunksec(cx, cz)[x-cx*16, ys, z-cz*16] = v

	def getchunksec(self, cx, cz):
		try: return self.chunksec[cx, cz]
		except KeyError:
			chunksec = self.chunksec[cx, cz] = ChunkSection(cx*16, cz*16, map=self)
			if (self.world is not None and
			    self.world.onchunksectioncreate is not None): self.world.onchunksectioncreate(chunksec)
			return chunksec

	@dispatch
	def load(self, cx, cz, pbm, abm, data: bytes):
		self.getchunksec(cx, cz).load(pbm, abm, data)

class World(Updatable):
	maps: dict
	ondimensioncreate: None
	onchunksectioncreate: None
	onchunkcreate: None
	onblockcreate: None
	onblockupdate: None

	def __repr__(self):
		return f"<World>"

	def __bool__(self):
		return any(self.maps.values())

	@autocast
	def __getitem__(self, dimension: int):
		try: return self.maps[dimension]
		except KeyError:
			map = self.maps[dimension] = Map(dimension, world=self)
			if (self.ondimensioncreate is not None): self.ondimensioncreate(map)
			return map

	@classmethod
	def open(cls, file, format='pycmap'):
		if (isinstance(file, str)): file = open(file, 'rb')
		world = cls()
		if (format == 'pycmap'):
			for dimension, chunksec in pickle.load(file).items():
				for pos, (abm, cd) in chunksec.items():
					world[dimension].load(*pos, -1, abm, zlib.decompress(cd))
		else: raise NotImplementedError(format)
		return world

	def save(self, file, format='pycmap'):
		if (isinstance(file, str)): file = open(file, 'wb')
		if (format == 'pycmap'):
			pickle.dump({
				dimension: {
					pos: (lambda abm, cd: (abm, zlib.compress(cd)))(*cs.chunkdata_bytes[-1])
				for pos, cs in map.chunksec.items()}
			for dimension, map in self.maps.items()}, file)
		else: raise NotImplementedError(format)

# by Sdore, 2019
