#!/usr/bin/python3
# PyCraft common classes and methods

from uuid import *
from utils import *; from utils import S as _S

class State(int):
	def __repr__(self): return f"<State {str(self)} ({int(self)})>"

	def __str__(self): return ('NONE', 'HANDSHAKING', 'STATUS', 'LOGIN', 'PLAY')[self+1]

	def __bool__(self): return (self != DISCONNECTED)
DISCONNECTED, HANDSHAKING, STATUS, LOGIN, PLAY = map(State, range(-1, 4))

from .protocol import * # C, S
from .protocol.pv0 import VarInt
readVarInt, writeVarInt = VarInt.read, VarInt.pack

class _socket(socket.socket):
	def read(self, n, flags=0):
		return self.recv(n, flags | socket.MSG_WAITALL)
socket.socket = _socket

class PacketBuffer:
	class IncomingPacket:
		__slots__ = ('compression', 'buffer', 'pid')

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
			if (self.length < l): raise BufferError('Not enough data')
			r, self.buffer = self.buffer[:l], self.buffer[l:]
			return r

		@property
		def length(self):
			return len(self.buffer)

	__slots__ = ('socket', 'compression', 'packet')

	nolog = False

	def __init__(self):
		self.compression = -1
		self.packet = None

	def __del__(self):
		try: self.socket.close()
		except (OSError, AttributeError): pass

	def read(self, l):
		return self.packet.read(l)

	def readPacketHeader(self, nolog=False):
		""" 'Header' because the function returns tuple (length, pid) and for backward compatibility. It actually puts the packet into the buffer. """
		if (self.state == DISCONNECTED): raise NoServer()
		try: self.packet = self.IncomingPacket(self.socket, self.compression)
		except OSError as ex: self.setstate(DISCONNECTED); raise NoPacket()
		if (not nolog and not self.nolog):
			log(2, f"Reading packet: length={self.packet.length}, pid={hex(self.packet.pid)}", nolog=True)
			log(3, self.packet.buffer, raw=True, nolog=True)
		return self.packet.length, self.packet.pid

	def sendPacket(self, packet, *data, nolog=False):
		if (not isinstance(packet, int)):
			if (self.state not in (None, -1)): assert packet.state == self.state
			pid = packet.pid
		else: pid = packet
		data = bytes().join(data)
		p = writeVarInt(pid) + data
		l = len(p)
		if (self.compression >= 0): p = writeVarInt(l) + zlib.compress(p) if (l >= self.compression) else writeVarInt(0) + p
		if (not nolog and not self.nolog):
			log(2, f"Sending packet: length={len(data)}, pid={hex(pid)}", nolog=True)
			log(3, data, raw=True, nolog=True)
		try: return self.socket.sendall(writeVarInt(len(p)) + p)
		except OSError as ex: self.setstate(DISCONNECTED)
class NoServer(Exception): pass
class NoPacket(Exception): pass

class Handlers(dict): # TODO: rewrite as a mixin
	"""
	handlers = Handlers()
	@classmethod
	def handler(self, packet):
		return self.handlers.handler(packet)
	"""

	def __getitem__(self, x):
		if (isinstance(x, PacketGetter)):
			return dict.__getitem__(self, x)

		c, pid = x
		for i in self:
			p = i[requireProtocolVersion(c.pv)]
			if (p.state == c.state and p.pid == pid): return i
		else: raise KeyError()

	def handler(self, packet):
		def decorator(f):
			self[packet] = f
			return self[packet]
		return decorator

class MojangAPI:
	baseurl = "https://api.mojang.com"

	@classmethod
	@cachedfunction
	def profile(cls, *names):
		return requests.post(f"{cls.baseurl}/profiles/minecraft", json=names).json()

class Updatable(metaclass=SlotsMeta):
	def __init__(self, **kwargs):
		for i in kwargs.items():
			setattr(self, *i)

	def update(self, data={}, **kwdata):
		data.update(kwdata)
		for k, v in data.items():
			if (k in ('self', 'kwargs')): continue
			setattr(self, k, v)

class Position(Updatable):
	x: float
	y: float
	z: float
	yaw: float
	pitch: float
	on_ground: bool

	def __repr__(self):
		return f"({self.x}, {self.y}, {self.z})"

	@property
	def pos(self):
		return (self.x, self.y, self.z, self.yaw, self.pitch)

	@pos.setter
	def setpos(self, pos):
		self.x, self.y, self.z, self.yaw, self.pitch = pos

	def updatepos(self, x, y, z, yaw, pitch, on_ground=False, flags=0b00000):
		self.setpos(self.pos[ii]+i if (flags & (1 << ii)) else i for ii, i in enumerate((x, y, z, yaw, pitch)))
		self.on_ground = on_ground

class Entity(Updatable):
	eid: -1
	pos: Position
	dimension: int

	def __repr__(self):
		return f"<Entity #{self.eid} at {self.pos}>"

	@property
	def metadata(self): # TODO
		return b'\xff'

	def updatePos(self, *args, **kwargs):
		return self.pos.updatepos(*args, **kwargs)

class Player(Entity):
	uuid: None
	name: str
	gamemode: int

	def __repr__(self):
		return f"<Player '{self.name}' at {self.pos}>"

class Entities:
	__slots__ = ('entities', 'players')

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

def formatChat(chat, ansi=False):
	if (isinstance(chat, str)): return chat
	text = chat.get('text', '')
	if ('translate' in chat):
		f = tuple(formatChat(i, ansi=ansi) for i in chat.get('with', ()))
		text += (lambda x: x.format(*f[:x.count('{}')])+str().join(f[x.count('{}'):]))({
			'chat.type.announcement': "[{}] ",
			'chat.type.text': "<{}> ",
			'commands.message.display.incoming': "{} whispers: ",
			'commands.message.display.outgoing': "Whispered to {}: ",
			'death.attack.player': "{} was slain by ",
			'multiplayer.player.joined': "{} joined the game",
			'multiplayer.player.left': "{} left the game",
		}.get(chat['translate'], chat['translate']))
	r = str()
	if (ansi):
		s = [str(v) for k, v in dict(
			obfuscated	= 5,
			bold		= 1,
			strikethrough	= 9,
			underline	= 4,
			italic		= 3,
			reset		= 0,
		).items() if chat.get(k)]
		if ('color' in chat): s.append(str(dict(
			black		= 30,
			dark_blue	= 34,
			dark_green	= 32,
			dark_aqua	= 36,
			dark_red	= 31,
			dark_purple	= 35,
			gold		= 33,
			gray		= 37,
			dark_gray	= 90,
			blue		= 94,
			green		= 92,
			aqua		= 96,
			red		= 91,
			light_purple	= 95,
			yellow		= 93,
			white		= 97,
		)[chat['color']]))
		if (s): r += f"\033[{';'.join(s)}m"
	r += text
	for i in chat.get('extra', ()):
		r += formatChat(i, ansi=ansi)
	return r

### DEBUG ###

class DebugSocket:
	@classmethod
	def __getattr__(cls, attr):
		return lambda *args, **kwargs: log(f"\033[93m[\033[1;35mDEBUG\033[0;93m] {cls.__name__}.{attr}({', '.join((*map(repr, args), *map(lambda x: f'{x[0]}={repr(x[1])}', kwargs.items())))})\033[0m", raw=True) and None

class DebugClient(PacketBuffer):
	def __init__(self, pv):
		self.pv = pv
		self.state = State(DISCONNECTED)
		self.socket = DebugSocket()
		PacketBuffer.__init__(self, self.socket)

# by Sdore, 2019
