#!/usr/bin/python3
# PyCraft common classes and methods

import PyT9
from nbt import *
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
	def recv(self, *_, **__):
		raise WTFException()

	def read(self, n, flags=0):
		flags |= socket.MSG_WAITALL
		return super().recv(n, flags)

	def read_into(self, buffer, nbytes=0, flags=0):
		flags |= socket.MSG_WAITALL
		return super().recv_into(buffer, nbytes, flags)

	def peek(self, n=1, flags=0):
		flags |= socket.MSG_PEEK
		return self.read(n, flags)
socket.socket = _socket

class PacketBuffer:
	class IncomingPacket(io.BytesIO):
		__slots__ = ('pid',)

		def __init__(self, socket, compression):
			try: l = readVarInt(socket)
			except ValueError: l = None
			if (not l): raise NoPacket()
			if (compression >= 0):
				pl = readVarInt(socket)
				l -= len(writeVarInt(pl))
			else: pl = None
			buffer = bytearray(l)
			self.length = socket.read_into(buffer)
			del buffer[self.length:]
			super().__init__(zlib.decompress(buffer) if (pl) else buffer)
			try: self.pid = readVarInt(self)
			except ValueError as ex: raise NoPacket(f"Invalid pid") from ex

		def read(self, l):
			if (self.length < l): raise NoPacket("Not enough data")
			return super().read(l)

		def peek(self, l=1):
			if (self.length < l): raise NoPacket("Not enough data")
			p = self.tell()
			return self.getbuffer()[p:p+l].tobytes()

		@property
		def buffer(self):
			return self.getbuffer()[self.tell():].tobytes()

	__slots__ = ('socket', 'compression', 'packet')

	nolog = bool()

	def __init__(self):
		self.compression = -1
		self.packet = None

	def __del__(self):
		try:
			try: self.socket.setblocking(True)
			except OSError: pass
			try: self.socket.close()
			except OSError: pass
		except AttributeError: pass

	def read(self, l):
		return self.packet.read(l)

	def peek(self, l=1):
		return self.packet.peek(l)

	def readPacketHeader(self, *, nolog=False):
		""" 'Header' because the function returns tuple (length, pid) and for backward compatibility. It actually puts the packet into the buffer. """
		if (self.state == DISCONNECTED): raise NoServer()
		try: self.packet = self.IncomingPacket(self.socket, self.compression)
		except OSError as ex:
			if (not isinstance(ex, socket.timeout) and ex.errno != socket.EWOULDBLOCK): self.setstate(DISCONNECTED)
			raise NoPacket()
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

	def subhandler(self, packet):
		def decorator(f):
			superhandler = self[packet]
			def handler(*args, **kwargs):
				superhandler(*args, **kwargs)
				return f(*args, **kwargs)
			self[packet] = handler
			return self[packet]
		return decorator

class Commands(metaclass=SlotsMeta):
	commands: dict
	trie: PyT9.Trie
	help_commands: set
	server: ...

	@dispatch
	def __init__(self, commands: dict, server=None):
		self.commands, self.server = commands.copy(), server
		self.trie.update(self.commands)

	@dispatch
	def __init__(self, commands: lambda x: isinstance(x, Commands), server=None):
		self.__init__(commands.commands, server=server)
		self.help_commands = commands.help_commands.copy()

	@dispatch
	def __init__(self, server=None):
		self.server = server

	def add(self, cmd, func, *, show=True):
		self.commands[cmd] = func
		if (show): self.help_commands.add(cmd)
		self.trie.add(cmd)

	def command(self, *cmd, show=True):
		def decorator(f):
			for i in cmd:
				self.commands[i] = f
			if (show): self.help_commands.update(cmd)
			self.trie.update(cmd)
		return decorator

	def execute(self, s, c):
		cmd, *args = s.split()
		try: f = self.commands[cmd]
		except KeyError as ex: raise CommandNotFound(*ex.args)
		fsig = inspect.signature(f)
		try:
			if (tuple(fsig.parameters.values())[-1].kind is inspect._VAR_POSITIONAL): return f(self.server, c, *args)
			else:
				try: return cast_call(f, self.server, c, *args)
				except CastError as ex: usage = None
		except CommandUsage as ex: usage = ex.args[0] if (ex.args) else None
		raise CommandUsage(usage or f"{cmd} {' '.join(k.join('[]' if (v.default is not inspect._empty) else '<>') for k, v in tuple(fsig.parameters.items())[2:])}")
class CommandException(Exception): pass
class CommandNotFound(CommandException): translate = 'commands.generic.notFound'
class CommandUsage(CommandException): translate = 'commands.generic.usage'

class Events(metaclass=SlotsMeta): # TODO
	queue: queue.Queue
	handlers: Sdict(set)
	server: ...
	c: None
	cs: list

	@dispatch
	def __init__(self, handlers: dict, server=None):
		self.handlers, self.server = handlers.copy(), server

	@dispatch
	def __init__(self, events: lambda x: isinstance(x, Events), server=None):
		self.__init__(events.handlers, server=server)

	@dispatch
	def __init__(self, server=None):
		self.server = server

	def __call__(self, c):
		self.cs.append(c)
		return self

	def __enter__(self):
		pass

	def __exit__(self, type, value, tb):
		self.cs.pop()

	def fire(self, event):
		self.events.queue.put((event, self.c))

	def handle(self):
		try: event, c = self.queue.get(block=False)
		except queue.Empty: return
		for f in self.handlers[event]:
			f(server, c)

	def on(self, event):
		def decorator(f):
			self.handlers[event].add(f)
			return f
		return decorator

class MojangAPI:
	baseurl = "https://api.mojang.com"

	@classmethod
	@cachedfunction
	def profile(cls, *names):
		r = requests.post(f"{cls.baseurl}/profiles/minecraft", json=names).json()
		r['id'] = UUID(r['id'])
		return r

class Updatable(metaclass=SlotsMeta):
	def __init__(self, **kwargs):
		self.update(**kwargs)

	def update(self, **kwargs):
		for k, v in kwargs.items():
			setattr(self, k, v)

class Position(Updatable):
	x: float
	y: float
	z: float
	yaw: float
	pitch: float
	on_ground: bool
	height: 1.62

	def __repr__(self):
		return repr((self.x, self.y, self.z))

	def __eq__(self, x):
		return isinstance(x, Position) and x.pos == self.pos and x.on_ground == self.on_ground

	def __iadd__(self, velocity):
		self.x += velocity.dx
		self.y += velocity.dy
		self.z += velocity.dz
		return self

	@property
	def head_y(self):
		return self.y+self.height

	@head_y.setter
	def head_y(self, head_y):
		self.y = head_y-self.height

	@property
	def pos(self):
		return (self.x, self.y, self.z, self.yaw, self.pitch)

	@pos.setter
	def pos(self, pos):
		if (isinstance(pos, Position)): pos = pos.pos
		self.x, self.y, self.z = pos[:3]
		if (pos[3:]): self.yaw, self.pitch = pos[3:]

	@property
	def look(self):
		return (self.yaw, self.pitch)

	@look.setter
	def look(self, look):
		self.yaw, self.pitch = look

	def updatepos(self, x, y, z, yaw, pitch, on_ground=None, flags=0b00000):
		self.pos = tuple(self.pos[ii]+i if (flags & (1 << ii)) else i for ii, i in enumerate((x, y, z, yaw, pitch)))
		if (on_ground is not None): self.on_ground = on_ground

class Velocity(Updatable):
	dx: float
	dy: float
	dz: float

	def __repr__(self):
		return repr(tuple(Sint(i).pm() for i in (self.dx, self.dy, self.dz)))

class Slot(Updatable):
	id: -1
	count: int
	nbt: nbt.NBTFile

	def __repr__(self):
		return f"<Slot #{self.id}{f'*{self.count}' if (self.count > 1) else ''}>" if (self.id != -1) else '<Slot (empty)>'

	def __bool__(self):
		return bool(self.id or self.count or self.nbt)

	def set(self, id, count=1, *, nbt=None):
		if (id == 0): count = 0
		self.id, self.count, self.nbt = id, count, nbt or globals()['nbt'].NBTFile()

class Entity(Updatable):
	eid: -1
	pos: Position
	dimension: int
	velocity: Velocity
	metadata: dict

	def __repr__(self):
		return f"<Entity #{self.eid} at {self.pos}>"

	def updatePos(self, *args, **kwargs):
		self.pos.updatepos(*args, **kwargs)

class Player(Entity):
	uuid: None
	name: str
	settings: dict
	spawn_position: Position
	gamemode: int
	health: 20
	food: 20
	food_saturation: 5
	inventory: [Slot() for _ in range(45)]
	selected_slot: int

	def __repr__(self):
		return f"<Player '{self.name}' at {self.pos}>"

	@property
	def visible_chunk_quads(self):
		cx, cz = int(self.pos.x)//32, int(self.pos.z)//32
		r = self.settings.get('view_distance', 1)
		return {(x, z) for x in range(cx-r, cx+r) for z in range(cz-r, cz+r)}

class Entities(metaclass=SlotsMeta): # TODO: remove this
	last_eid: int
	entities: Sdict

	def __iter__(self):
		self.entities.discard()
		return iter(self.entities.items())

	def add_entity(self, entity):
		if (entity not in self.entities.values()):
			while (self.last_eid in self.entities): self.last_eid += 1 # TODO: mod k
			entity.eid = self.last_eid
			self.entities[entity.eid] = entity
		return entity

	def remove_entity(self, eid):
		self.entities.to_discard(eid)

class PlayerData(metaclass=SlotsMeta):
	players: dict
	server: ...

	def __init__(self, server):
		self.server = server

	def get_player(self, *, name, uuid):
		try: player = self.players[uuid]
		except KeyError: player = self.players[uuid] = self.server.create_player(name=name, uuid=uuid)
		return self.server.entities.add_entity(player)

def loadTranslation(version, lang):
	hash = requests.get(requests.get(first(_S(requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json").json()['versions'])@{'id': (version,)})['url']).json()['assetIndex']['url']).json()['objects'][f"minecraft/lang/{lang}.lang"]['hash']
	r = requests.get(f"http://resources.download.minecraft.net/{hash[:2]}/{hash}").text # TODO: caching
	return {k: re.sub(r'%(\d*)\$?s', r'{\1}', v) for k, _, v in map(lambda x: x.partition('='), r.strip().split())}

en_GB = loadTranslation('1.8.9', 'en_GB') # TODO

def formatChat(chat, *, ansi=False):
	if (isinstance(chat, str)): return chat
	text = chat.get('text', '')
	if ('translate' in chat):
		f = tuple(formatChat(i, ansi=ansi) for i in chat.get('with', ()))
		text += (lambda x: x.format(*f[:x.count('{}')])+str().join(f[x.count('{}'):]))(
			en_GB.get(chat['translate'], chat['translate']+': ')
		)
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

# by Sdore, 2020
