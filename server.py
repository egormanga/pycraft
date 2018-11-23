#!/usr/bin/python3
# PyCraft server

from . import *
from pynbt import *
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

class Client(PacketBuffer, Updatable):
	def __init__(self, socket):
		PacketBuffer.__init__(self, socket)
		self.player = None
		self.ping = 0
		self.pv = 0
		self.brand = ''
		self.nextkeepalive = 0
		self.lastkeepalive = float('inf')
		self.lastkeepalive_id = 0
		self.state = HANDSHAKING
	def setstate(self, state):
		self.state = State(state)

class MCServer:
	def __init__(self, ip='', port=25565):
		self.clients = Slist()
		self.entities = Entities()
		self.env = attrdict.AttrDict(
			difficulty=config.difficulty,
		)
		self.socket = socket.socket()
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind((ip, port))
		self.socket.setblocking(False) # FIXME TEST
		#self.socket.settimeout(1)
		self.tick = int()
		self.startedAt = time.time()
	@property
	def players(self):
		return [i.player for i in self.clients if i.player]
	def start(self):
		self.socket.listen()
		log("Server started.")
	def stop(self):
		self.socket.detach()
		log("Server stopped.")

	handlers = Handlers()
	def handle(self):
		self.tick += 1
		log("\033[K\033[2m%.4f ticks/sec." % ((time.time()-self.startedAt)/self.tick), end='\033[0m\r', raw=True, nolog=True)
		try: self.clients.append(Client(self.socket.accept()[0]))
		except OSError: pass
		self.clients.discard()
		for ii, c in enumerate(self.clients):
			#time.sleep(0.01) # TODO FIXME optimize instead of slowing down (preventing 100% CPU load)
			if (c.state == -1): self.clients.to_discard(ii); continue
			if (c.state == PLAY):
				if (time.time() > c.lastkeepalive+config.keepalive_interval): c.setstate(-1); continue
				if (time.time() >= c.nextkeepalive):
					c.lastkeepalive_id = random.randrange(2**31)
					KeepAlive.send(c, c.lastkeepalive_id)
					c.nextkeepalive = time.time()+config.keepalive_interval
			try: l, pid = c.readPacketHeader()
			except NoPacket: continue
			try: self.handlers[c, pid](self, c)
			except NoHandlerError:
				log(1, f"Unhandled packet at state {c.state}: length={l} pid={hex(pid)}", nolog=True)
				log(2, c.packet.read(l), raw=True, nolog=True)
				log(4, '-'*os.get_terminal_size()[0]+'\n', raw=True, nolog=True)
	@classmethod
	def handler(self, packet):
		return self.handlers.handler(packet)

	@staticmethod
	def sendLoginDisconnect(c, text):
		c.sendPacket(0x00, writeString(text))
	@staticmethod
	def sendChunk(c, pos, **args):
		chunk = None # TODO
		c.sendPacket(0x22, # Chunk Data
			writeInt(pos[0]), # Chunk X
			writeInt(pos[1]), # Chunk Y
			writeBool(data['ground_up_continuous']), # Ground-Up Continuous
			writeVarInt(data['primary_bit_mask']), # Primary Bit Mask
			writeVarInt(len(chunk['data'])), # Size
			bytes().join(writeByte(i) for i in chunk['data']), # Data
			writeVatInt(len(chunk['block_entities'])), # Number of block entities
			bytes().join(writeString(i) for i in chunk['block_entities']), # Block entities
		)
	@staticmethod
	def sendPlayerListItem(c, action, **data):
		l = 1 # TODO multiple actions
		r = (
			writeVarInt(action),
			writeVarInt(l),
			writeUUID(data['uuid']),
		)
		if (action == 0): # add player
			r += (
				writeString(data['name']),
				writeVarInt(0), # TODO properties
			)
		if (action in (0, 1)): # update gamemode
			r += (
				writeVarInt(data['gamemode']),
			)
		if (action in (0, 2)): # update latency
			r += (
				writeVarInt(data['ping']),
			)
		if (action in (0, 3)): # update display name
			r += (
				writeBool(data['has_display_name']),
				(writeString(data['display_name']) if (data['has_display_name']) else b''),
			)
		c.sendPacket(0x30, *r)

### XXX ###

@MCServer.handler(Handshake)
def handleHandshake(server, c):
	a = c.socket.getpeername()
	c.pv, addr, port, state, = Handshake.recv(c)
	log(f"New handshake from {a[0]}:{a[1]}@pv{c.pv}: state {state}")

	if (state == 1): # status
		log(1, "Status")
		c.setstate(STATUS)
	elif (state == 2): # login
		log(1, "Login")
		pv = requireProtocolVersion(c.pv)
		if (c.pv != pv): LoginDisconnect.send(c, '{text="Outdated '+('client', 'server')[c.pv < pv]+'"}'); c.setstate(-1); return
		c.setstate(LOGIN)
	else: log(f"Wrong state: {state}")

@MCServer.handler(StatusRequest)
def handleStatusRequest(server, c):
	try: favicon = base64.b64encode(open(config.favicon, 'rb').read())
	except: favicon = b''
	StatusResponse.send(c, json.dumps({
		'version': {
			'name': config.version_name,
			'protocol': c.pv,#PV # FIXME TODO
		},
		'players': {
			'max': config.players_max,
			'online': len(server.players),
			'sample': [{'name': i.name, 'id': str(i.uuid)} for i in server.players],
		},
		'description': {
			'text': config.motd,
		},
		'favicon': "data:image/png;base64,"+favicon.decode('ascii'),
	}))

@MCServer.handler(Ping)
def handlePing(server, c):
	payload, = Ping.recv(c)
	Pong.send(c, payload)

@MCServer.handler(LoginStart)
def handleLoginStart(server, c):
	#c.sendPacket(0x03, # Set Compression # TODO
	#	writeVarInt(config.compression_threshold), # Threshold
	#)
	#c.compression = config.compression_threshold
	# TODO: encryption

	name, = LoginStart.recv(c)
	c.player = server.entities.add_player(Player(
		name=name,
		uuid=uuid3(NAMESPACE_OID, "OfflinePlayer:"+name),
	))
	LoginSuccess.send(c, str(c.player.uuid), c.player.name)
	c.setstate(PLAY)
	JoinGame.send(c, c.player.eid, c.player.gamemode, c.player.dimension, server.env.difficulty, config.players_max)
	#c.sendPacket(0x19, # Plugin Message
	#	writeIdentifier('minecraft', 'brand'), # Channel
	#	writeString(config.brand), # Data
	#)
	#c.sendPacket(0x0D, # Server Difficulty
	#	writeByte(server.env.difficulty), # Difficulty
	#)
	SpawnPosition.send(c, c.player.pos)
	PlayerAbilities.send(c, 0, 1.0, 1.0)
	PlayerPositionAndLook_C.send(c, c.player.pos)
	#server.sendPlayerListItem(c, 0,
	#	uuid=c.player.uuid,
	#	name=c.player.name,
	#	gamemode=c.player.gamemode,
	#	ping=c.ping,
	#	has_display_name=False,
	#)
	#c.sendPacket(0x22, # Chunk Data
	#	testchunk.pack(), # Test Chunk
	#nolog=False)

@MCServer.handler(KeepAlive)
def handleKeepAlive(server, c):
	keepalive_id, = KeepAlive.recv(c)
	if (keepalive_id == c.lastkeepalive_id): c.lastkeepalive = time.time()

#@MCServer.handler(0x00, PLAY) # Teleport Confirm
def handleTeleportConfirm(server, c): # TODO
	readVarInt(c) # Teleport ID

@MCServer.handler(Player_S)
def handlePlayer(server, c):
	on_ground, = Player_S.recv(c)
	c.player.update(
		on_ground = on_ground,
	)

@MCServer.handler(PlayerPosition_S)
def handlePlayerPosition(server, c):
	x, y, z, stance, on_ground, = PlayerPosition_S.recv(c)
	c.player.update(
		x = x,
		y = y,
		z = z,
		on_ground = on_ground,
	)

@MCServer.handler(PlayerLook_S)
def handlePlayerLook(server, c):
	yaw, pitch, on_ground, = PlayerLook_S.recv(c)
	c.player.update(
		yaw = yaw,
		pitch = pitch,
		on_ground = on_ground,
	)

@MCServer.handler(PlayerPositionAndLook_S)
def handlePlayerPositionAndLook(server, c):
	x, y, z, stance, yaw, pitch, on_ground, = PlayerPositionAndLook_S.recv(c)
	c.player.update(
		x = x,
		y = y,
		z = z,
		yaw = yaw,
		pitch = pitch,
		on_ground = on_ground,
	)

#@MCServer.handler(0x04, PLAY) # Client Settings
def handleClientSettings(server, c):
	c.update(
		locale = readString(c, 16), # Locale
		view_distance = readByte(c), # View Distance
		chat_mode = readVarInt(c), # Chat Mode
		chat_colors = readBool(c), # Chat Colors
		skin_parts = readUByte(c), # Displayed Skin Parts
		main_hand = readVarInt(c), # Main Hand
	)

#@MCServer.handler(0x0A, PLAY) # Plugin Message
def handlePluginMessage(server, c):
	ns, ch = readIdentifier(c)
	if (ns == 'minecraft'):
		if (ch == 'brand'):
			c.brand = readString(c)

### XXX ###

def main():
	setlogfile('PyCraft_server.log')
	server = MCServer()
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): logstarted(); main()
else: logimported()

# by Sdore, 2018
