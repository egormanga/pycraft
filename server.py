#!/usr/bin/python3
# PyCraft server
#a
import json, zlib, base64, socket, attrdict
from .commons import *
from .protocol import *
from .map import *
from pynbt import *
from uuid import *
from utils import *; logstart('Server')

class _config:
	version_name = 'PyCraft 1.13.2'
	default_gamemode = 0
	difficulty = 1
	players_max = 5
	level_type = 'default'
	compression_threshold = -1
	keepalive_interval = 15
	reduced_debug_info = False
	server_ip = ''
	server_port = 25565
	favicon = __file__.rpartition('/')[0]+'/server-icon.png'
	motd = "A PyCraft Server by Sdore"
config = _config()
#try: from . import config
#except ImportError: pass

def hex(x, l=2): return '0x%%0%dx' % l % x

socket.socket.read = socket.socket.recv
class PacketBuffer:
	class IncomingPacket:
		def __init__(self, socket, compression):
			self.compression = compression
			l = readVarInt(socket, nolog=True)
			if (not l): raise NoPacket()
			if (self.compression > -1):
				pl = readVarInt(socket, nolog=True)
				self.buffer = socket.recv(l)
				if (pl): self.buffer = zlib.decompress(self.buffer)
			else: self.buffer = socket.recv(l)
			self.pid = readVarInt(self, nolog=True)
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
		self.alive = True
	def read(self, l):
		return self.packet.read(l)
	def readPacketHeader(self, nolog=False):
		" 'Header' because the function returns tuple (length, pid) and for backward compatibility. It actually puts the packet into the buffer. "
		try: self.packet = self.IncomingPacket(self.socket, self.compression)
		except BrokenPipeError: self.alive = False; return 0, 0
		if (not nolog): log(2, f"Reading packet: length={self.packet.length}, pid={hex(self.packet.pid)}")
		return self.packet.length, self.packet.pid
	def sendPacket(self, pid, *data, nolog=True):
		data = bytes().join(data)
		p = writeVarInt(pid) + data
		l = len(p)
		if (self.compression >= 0): p = writeVarInt(l) + zlib.compress(p) if (l >= self.compression) else writeVarInt(0) + p
		p = writeVarInt(len(p)) + p
		if (not nolog):
			log(2, f"Sending packet: length={l}, pid={hex(pid)}")
			log(3, data, raw=True)
		try: return self.socket.send(p)
		except BrokenPipeError: self.alive = False
class NoPacket(Exception): pass

class Client(PacketBuffer, Updatable):
	def __init__(self, socket):
		PacketBuffer.__init__(self, socket)
		self.state = HANDSHAKING
		self.player = None
		self.ping = 0
		self.brand = ''
		self.nextkeepalive = 0
		self.lastkeepalive = float('inf')
		self.lastkeepalive_id = 0
	def setstate(self, state):
		self.state = State(state)

class Entity(Updatable):
	def __init__(self,
		eid: int = -1,
		pos: tuple = (0, 0, 0, 0, 0),
		on_ground: bool = False,
		dimension: int = 0,
	):
		x, y, z, yaw, pitch = (property(lambda: pos[i]) for i in range(5))
		self.update(locals())
	@property
	def metadata(self):
		return b'\xff'
class Player(Entity):
	def __init__(self,
		uuid: uuid3 = None,
		name: str = str(),
		gamemode: int = config.default_gamemode,
	**kwargs):
		Entity.__init__(self, **kwargs)
		self.update(locals())
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

class Handlers:
	"""
	handlers = Handlers()
	def handler(self, pid, state=ALL): # decorator
		def decorator(f):
			self.handlers[state][pid] = f
			return f
		return decorator
	"""
	def __init__(self):
		self.handlers = Sdict(Sdict)
	def __getitem__(self, x):
		state, pid = State(x[0]), int(x[1])
		try: return self.handlers[state][pid]
		except KeyError:
			try: return self.handlers[ALL][pid]
			except KeyError: raise \
				NoHandlerError()
	def handler(self, pid, state=ALL): # decorator
		"""
		def handler(self, *args, **kwargs):
			return self.handlers.handler(*args, **kwargs)
		"""
		def decorator(f):
			self.handlers[State(state)][int(pid)] = f
			return f
		return decorator
class NoHandlerError(Exception): pass

class MCServer:
	def __init__(self, ip='', port=25565):
		self.clients = Slist()
		self.entities = Entities()
		self.env = attrdict.AttrDict(
			difficulty=config.difficulty,
		)
		self.s = socket.socket()
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.s.bind((ip, port))
		self.s.setblocking(False)
		#self.s.settimeout(1)
	@property
	def players(self):
		return [i.player for i in self.clients if i.player]
	def start(self):
		self.s.listen()
		log("Server started.")
	def stop(self):
		self.s.detach()
		log("Server stopped.")

	handlers = Handlers()
	def handle(self):
		try: self.clients.append(Client(self.s.accept()[0]))
		except OSError: pass
		self.clients.discard()
		for ii, c in enumerate(self.clients):
			if (c.state == PLAY):
				if (time.time() > c.lastkeepalive+config.keepalive_interval): c.alive = False
				if (not c.alive): self.clients.to_discard(ii); continue
				if (time.time() >= c.nextkeepalive):
					c.lastkeepalive_id = random.randrange(2**63)
					c.sendPacket(0x21,
						writeLong(c.lastkeepalive_id),
					nolog=True)
					c.nextkeepalive = time.time()+config.keepalive_interval
			try: l, pid = c.readPacketHeader()
			except NoPacket: continue
			try: self.handlers[c.state, pid](self, c)
			except NoHandlerError:
				log(1, f"Unhandled packet at state {c.state}: length={l} pid={hex(pid)}")
				log(2, c.packet.read(l), raw=True)
			log(4, '-'*os.get_terminal_size()[0]+'\n', raw=True)
	@classmethod
	def handler(self, *args, **kwargs):
		return self.handlers.handler(*args, **kwargs)

### XXX ###

@MCServer.handler(0x00, HANDSHAKING) # Handshake
def handleHandshake(server, c):
	a = c.socket.getpeername()
	pv, addr, port, state = readVarInt(c, name='pv'),\
				readString(c, 255, name='addr'),\
				readShort(c, name='port'),\
				readVarInt(c, name='state')
	log(f"New handshake from {a[0]}:{a[1]}@v{pv}: state {state}")

	if (state == 1): # status
		log(1, "Status")
		c.setstate(STATUS)
	elif (state == 2): # login
		log(1, "Login")
		if (pv != PV): sendLoginDisconnect(c, '{text="%s too old."}' % ("You're" if (pv < PV) else "I'm")); return
		c.setstate(LOGIN)
	else: log(f"Wrong state: {state}")

@MCServer.handler(0x00, STATUS) # Status Request
def handleStatusRequest(server, c):
	try: favicon = base64.b64encode(open(config.favicon, 'rb').read())
	except: favicon = b''
	c.sendPacket(0x00, writeString(json.dumps({
		'version': {
			'name': config.version_name,
			'protocol': PV
		},
		'players': {
			'max': config.players_max,
			'online': len(server.players),
			'sample': [{'name': i.name, 'id': str(i.uuid)} for i in server.players]
		},
		'description': {
			'text': config.motd,
		},
		'favicon': "data:image/png;base64,"+favicon.decode('ascii'),
	})))

@MCServer.handler(0x00, LOGIN) # Login Start
def handleLoginStart(server, c):
	name = readString(c, 16, name='name')
	c.sendPacket(0x03, # Set Compression # TODO
		writeVarInt(config.compression_threshold), # Threshold
	)
	c.compression = config.compression_threshold
	# TODO: encryption

	c.player = server.entities.add_player(Player(
		name=name,
		uuid=uuid3(NAMESPACE_OID, ("OfflinePlayer:"+name)),
	))
	c.sendPacket(0x02, # Login Success
		writeString(str(c.player.uuid), 36), # UUID
		writeString(c.player.name, 16), # Username
	)
	c.setstate(PLAY)
	c.sendPacket(0x25, # Join Game
		writeInt(c.player.eid), # Entity ID
		writeUByte(c.player.gamemode), # Gamemode
		writeInt(c.player.dimension), # Dimension
		writeUByte(server.env.difficulty), # Difficulty
		writeUByte(config.players_max), # Max Players
		writeString(config.level_type, 16), # Level Type
		writeBool(config.reduced_debug_info), # Reduced Debug Info
	)
	c.sendPacket(0x19, # Plugin Message
		writeIdentifier('minecraft', 'brand'), # Channel
		writeString("pycraft"), # Data # FIXME
	)
	c.sendPacket(0x0D, # Server Difficulty
		writeByte(server.env.difficulty), # Difficulty
	)
	c.sendPacket(0x49, # Spawn Position
		writePosition(*c.player.pos), # Location
	)
	c.sendPacket(0x2E, # Player Abilities
		writeByte(0), # Flags
		writeFloat(1.0), # Flying Speed
		writeFloat(1.0), # Field of View Modifier
	)
	# C→S: Plugin Message
	# C→S: Client Settings
	c.sendPacket(0x32, # Player Position And Look
		writeDouble(c.player.pos[0]), # X
		writeDouble(c.player.pos[1]), # Y
		writeDouble(c.player.pos[2]), # Z
		writeFloat(c.player.pos[3]), # Yaw
		writeFloat(c.player.pos[4]), # Pitch
		writeByte(0), # Flags
		writeVarInt(0), # Teleport ID
	)
	# C→S: Teleport Confirm
	# C→S: Client Status
	# S→C: Inventory, Chunk Data, Entities, etc.
	#c.sendPacket(0x22, # Chunk Data FIXME TEMP
	#	writeInt(0), # Chunk X
	#	writeInt(0), # Chunk Z
	#	writeBool(True), # Ground-Up Continuous
	#	writeVarInt(0), # Primary Bit Mask
	#	writeVarInt(0), # Size
	#	b'', # Data
	#	writeVarInt(0), # Number of block entities
	#	b'', # Block entities
	#nolog=False)
	updatePlayerList(c, 0,
		uuid=c.player.uuid,
		name=c.player.name,
		gamemode=c.player.gamemode,
		ping=c.ping,
		has_display_name=False,
	)
	c.sendPacket(0x22, # Chunk Data
		testchunk.pack(), # Test Chunk
	nolog=False)

@MCServer.handler(0x00, PLAY) # Teleport Confirm
def handleTeleportConfirm(server, c): # TODO
	readVarInt(c) # Teleport ID

@MCServer.handler(0x01, STATUS) # Ping
def handlePing(server, c):
	c.sendPacket(c.packet.pid, # Pong
		writeLong(readLong(c, nolog=True)),
	nolog=True)

@MCServer.handler(0x11, PLAY) # Player Position And Look
def handlePlayerPositionAndLook(server, c):
	c.player.update(
		x = readDouble(c), # X
		y = readDouble(c), # Y
		z = readDouble(c), # Z
		yaw = readFloat(c), # Yaw
		pitch = readFloat(c), # Pitch
		on_ground = readBool(c), # On Ground
	)

@MCServer.handler(0x04, PLAY) # Client Settings
def handleClientSettings(server, c):
	c.update(
		locale = readString(c, 16), # Locale
		view_distance = readByte(c), # View Distance
		chat_mode = readVarInt(c), # Chat Mode
		chat_colors = readBool(c), # Chat Colors
		skin_parts = readUByte(c), # Displayed Skin Parts
		main_hand = readVarInt(c), # Main Hand
	)

@MCServer.handler(0x0A, PLAY) # Plugin Message
def handlePluginMessage(server, c):
	ns, ch = readIdentifier(c)
	if (ns == 'minecraft'):
		if (ch == 'brand'):
			c.brand = readString(c)

@MCServer.handler(0x0E, PLAY) # Keep Alive
def handleKeepAlive(server, c):
	if (readLong(c) == c.lastkeepalive_id): c.lastkeepalive = time.time()

### XXX ###

def sendLoginDisconnect(c, text):
	c.sendPacket(0x00, writeString(text))

def sendChunk(c, pos, **args):
	chunk = None # TODO
	c.sendPacket(0x22, # Chunk Data
		writeInt(pos[0]) + # Chunk X
		writeInt(pos[1]) + # Chunk Y
		writeBool(data['ground_up_continuous']) + # Ground-Up Continuous
		writeVarInt(data['primary_bit_mask']) + # Primary Bit Mask
		writeVarInt(len(chunk['data'])) + # Size
		bytes().join(writeByte(i) for i in chunk['data']) + # Data
		writeVatInt(len(chunk['block_entities'])) + # Number of block entities
		bytes().join(writeString(i) for i in chunk['block_entities']) # Block entities
	)

def updatePlayerList(c, action, **data):
	l = 1 # TODO multiple actions
	r = (
		writeVarInt(action) +
		writeVarInt(l) +
		writeUUID(data['uuid'])
	)
	if (action == 0): # add player
		r += (
			writeString(data['name']) +
			writeVarInt(0) # TODO properties
		)
	if (action in (0, 1)): # update gamemode
		r += writeVarInt(data['gamemode'])
	if (action in (0, 2)): # update latency
		r += writeVarInt(data['ping'])
	if (action in (0, 3)): # update display name
		r += (
			writeBool(data['has_display_name']) +
			(writeString(data['display_name']) if (data['has_display_name']) else b'')
		)
	c.sendPacket(0x30, r)

def main():
	setlogfile('PyCraft.log')
	server = MCServer()
	server.start()
	while (True):
		try: server.handle()
		except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): logstarted(); main()
else: logimported()

# by Sdore, 2018
