#!/usr/bin/python3
# PyCraft common classes and methods

import zlib, base64, socket, attrdict
from .protocol import *
from .versions import *
from utils import *

def hex(x, l=2): return '0x%%0%dX' % l % x

class Socket(socket.socket):
	def read(self, n, flags=0):
		return self.recv(n, flags | socket.MSG_WAITALL)
socket.socket = Socket

class PacketBuffer:
	class IncomingPacket:
		def __init__(self, socket, compression):
			self.compression = compression
			l = readVarInt(socket)
			if (not l): raise NoPacket()
			if (self.compression >= 0):
				pl = readVarInt(socket)
				l -= len(writeVarInt(pl))
				self.buffer = socket.read(l)
				if (pl): self.buffer = zlib.decompress(self.buffer)
			else: self.buffer = socket.read(l)
			self.pid = readVarInt(self)
		def read(self, l):
			if (self.length < l):
				del self # XXX ???
				raise \
					BufferError('Not enough data')
			r, self.buffer = self.buffer[:l], self.buffer[l:]
			return r
		@property
		def length(self):
			return len(self.buffer)

	def __init__(self, socket):
		self.socket = socket
		self.compression = -1
		self.packet = None
	def read(self, l):
		return self.packet.read(l)
	def readPacketHeader(self, nolog=False):
		" 'Header' because the function returns tuple (length, pid) and for backward compatibility. It actually puts the packet into the buffer. "
		try: self.packet = self.IncomingPacket(self.socket, self.compression)
		except OSError as ex: log(ex); self.setstate(-1); raise NoPacket()
		if (not nolog): log(2, f"Reading packet: length={self.packet.length}, pid={hex(self.packet.pid)}")
		return self.packet.length, self.packet.pid
	def sendPacket(self, packet, *data, nolog=True):
		if (type(packet) == int): raise \
			NotImplementedError('pid → packet')
		pid = packet.pid
		data = bytes().join(data)
		p = writeVarInt(pid) + data
		l = len(p)
		if (self.compression >= 0): p = writeVarInt(l) + zlib.compress(p) if (l >= self.compression) else writeVarInt(0) + p
		p = writeVarInt(len(p)) + p
		if (not nolog):
			log(2, f"Sending packet: length={l}, pid={hex(pid)}")
			log(3, data, raw=True, nolog=True)
		try: return self.socket.send(p)
		except OSError as ex: log(ex); self.setstate(-1)
class NoPacket(Exception): pass

class Handlers(dict): # TODO: rewrite as a mixin
	"""
	handlers = Handlers()
	@classmethod
	def handler(self, packet):
		return self.handlers.handler(packet)
	"""
	def __getitem__(self, x):
		if (type(x) == PacketImplGetter):
			return dict.__getitem__(self, x)
		c, pid = x
		for i in self:
			p = i[c.pv]
			if (p.state == c.state and p.pid == pid): return self[i]
		else: raise \
			NoHandlerError()
	def handler(self, packet): # decorator
		def decorator(f):
			self[packet] = f
			return f
		return decorator
class NoHandlerError(Exception): pass

class Updatable:
	def update(self, data={}, **kwdata):
		data.update(kwdata)
		for i in data: self.__setattr__(i, data[i])

class Position(Updatable):
	def __init__(self,
		x = float(),
		y = float(),
		z = float(),
		yaw = float(),
		pitch = float(),
		on_ground = bool(),
	):
		self.update(locals())
	def __repr__(self):
		return ', '.join(map(str, self.pos[:3])).join('()')
	@property
	def pos(self):
		return (self.x, self.y, self.z, self.yaw, self.pitch)
	def setpos(self, pos):
		self.x, self.y, self.z, self.yaw, self.pitch = pos
	def updatepos(self, x, y, z, yaw, pitch, flags=0b00000):
		self.setpos(self.pos[ii]+i if (flags & (1 << ii)) else i for ii, i in enumerate((x, y, z, yaw, pitch)))

class Entity(Updatable):
	def __init__(self,
		eid = -1,
		pos = Position(),
		dimension = 0,
	):
		self.update(locals())
	def __repr__(self):
		return f"<Entity #{self.eid} at {self.pos}>"
	@property
	def metadata(self):
		return b'\xff'
	def updatePos(self, *args, **kwargs):
		return self.pos.updatepos(*args, **kwargs)
class Player(Entity):
	def __init__(self,
		uuid = None,
		name = str(),
		gamemode = int(),
	**kwargs):
		Entity.__init__(self, **kwargs)
		uuid = uuid if (type(uuid) == UUID) else UUID(uuid) if (uuid) else None
		self.update(locals())
	def __repr__(self):
		return f"<Player '{self.name}' at {self.pos}>"

class Entities:
	def __init__(self):
		self.entities = list()
		self.players = list()
	def add_entity(self, entity):
		entity.eid = len(self.entities)
		self.entities.append(entity)
		return entity
	def add_player(self, player):
		player = self.add_entity(player)
		self.players.append(player)
		return player

# by Sdore, 2018
