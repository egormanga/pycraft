#!/usr/bin/python3
# PyCraft server

from . import *; logstart('Server')

class ServerConfig:
	version_name = 'PyCraft {}'
	default_gamemode = 0
	difficulty = 1
	players_max = 5
	level_type = 'default'
	compression_threshold = -1
	keepalive_interval = 15
	tickspeed = 1/20
	reduced_debug_info = False
	server_ip = ''
	server_port = 25565
	favicon = os.path.join(os.path.dirname(__file__), 'server-icon.png')
	motd = "A PyCraft Server"

class Client(PacketBuffer):
	def __init__(self, server, socket, address):
		self.server, self.socket, self.address = server, socket, address
		super().__init__()
		self.player = None
		self.ping = 0
		self.pv = 0
		self.brand = ''
		self.nextkeepalive = 0
		self.lastkeepalive = inf
		self.lastkeepalive_id = 0
		self.state = HANDSHAKING

	def setstate(self, state):
		self.state = State(state)
		self.nextkeepalive = time.time()+self.server.config.keepalive_interval/2

class MCServer:
	def __init__(self, config=ServerConfig):
		self.config = config()
		self.clients = Slist()
		self.handlers = Handlers(self.handlers)
		self.handler = lambda x: self.handlers.handler(x)
		self.entities = Entities()
		self.env = attrdict.AttrDict(
			difficulty=self.config.difficulty,
		)
		self.socket = socket.socket()
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
		self.socket.bind((self.config.server_ip, self.config.server_port))
		#self.socket.setblocking(False)
		self.socket.settimeout(0.001)
		self.ticks = int()
		self.lasttick = int()
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

	def handle(self):
		if (time.time() >= self.lasttick+self.config.tickspeed):
			self.tick()
			self.lasttick = time.time()

		try: self.clients.append(Client(self, *self.socket.accept()))
		except OSError: pass

		self.clients.discard()
		for ii, c in enumerate(self.clients):
			if (c.socket._closed): c.state = DISCONNECTED
			if (c.state == DISCONNECTED):
				self.clients.to_discard(ii)
				log(f"Disconnected: {c.address}")
				continue
			if (c.state == PLAY):
				if (time.time() > c.lastkeepalive+self.config.keepalive_interval): c.setstate(DISCONNECTED); continue
				if (time.time() >= c.nextkeepalive):
					c.lastkeepalive_id = random.randrange(2**31)
					C.KeepAlive.send(c,
						keepalive_id = c.lastkeepalive_id
					)
					c.nextkeepalive = time.time()+self.config.keepalive_interval/2
			self.handle_client_packet(c)
		self.clients.discard()

	handlers = Handlers()
	def handle_client_packet(self, c):
		try: l, pid = c.readPacketHeader()
		except NoServer: c.setstate(DISCONNECTED); return
		except NoPacket: return
		try:
			p = self.handlers[c, pid]
			h = self.handlers[p]
		except KeyError:
			log(1, f"Unhandled packet at state {c.state}: length={l} pid={hex(pid)}", nolog=True)
			log(2, c.packet.read(l), raw=True, nolog=True)
			log(4, '-'*80+'\n', raw=True, nolog=True)
			return
		try: h(self, c, p.recv(c))
		except Disconnect as ex:
			(C.Disconnect if (c.state == PLAY) else C.LoginDisconnect).send(c,
				reason = ex.args[0],
			)
			c.setstate(DISCONNECTED)

	def tick(self):
		self.ticks += 1
		log("\033[K\033[2m%.4f ticks/sec." % ((time.time()-self.startedAt)/self.ticks), end='\033[0m\r', raw=True, nolog=True)

	@classmethod
	def handler(cls, packet):
		return cls.handlers.handler(packet)
class Disconnect(Exception):
	def __init__(self, *reason, **kwargs):
		parseargs(kwargs, text='', extra=reason)
		super().__init__(kwargs)

### XXX ###

@MCServer.handler(S.Handshake)
def handleHandshake(server, c, p):
	a = c.socket.getpeername()
	log(f"New handshake from {a[0]}:{a[1]}@pv{p.pv}: state {p.state}")

	c.pv = p.pv
	if (p.state == STATUS):
		log(1, "Status")
		c.setstate(STATUS)
	elif (p.state == LOGIN):
		log(1, "Login")
		c.setstate(LOGIN)
	else: log(f"Wrong state: {p.state}")

@MCServer.handler(S.StatusRequest)
def handleStatusRequest(server, c, p):
	try: favicon = open(server.config.favicon, 'rb')
	except Exception: favicon = None

	pv = requireProtocolVersion(c.pv)
	r = {
		'version': {
			'name': server.config.version_name.format(PVs[pv].MCV),
			'protocol': pv,
		},
		'players': {
			'max': server.config.players_max,
			'online': len(server.players),
			'sample': [{
				'name': i.name,
				'id': str(i.uuid)
			} for i in server.players],
		},
		'description': {
			'text': server.config.motd,
		},
	}

	if (favicon is not None): r['favicon'] = f"data:image/png;base64,{base64.b64encode(favicon.read()).decode('ascii')}"

	C.StatusResponse.send(c,
		response = r,
	)

@MCServer.handler(S.Ping)
def handlePing(server, c, p):
	C.Pong.send(c,
		payload = p.payload,
	)

@MCServer.handler(S.LoginStart)
def handleLoginStart(server, c, p):
	pv = requireProtocolVersion(c.pv)
	if (c.pv != pv): raise Disconnect(f"Outdated {'client' if (c.pv < pv) else 'server'}")

	#c.sendPacket(0x03, # Set Compression # TODO
	#	writeVarInt(server.config.compression_threshold), # Threshold
	#)
	#c.compression = server.config.compression_threshold

	try: profile = MojangAPI.profile(p.name)[0]
	except Exception: profile = {'name': p.name, 'id': uuid3(NAMESPACE_OID, "OfflinePlayer:"+p.name)}
	c.player = server.entities.add_player(Player(
		name=profile['name'],
		uuid=profile['id'],
		gamemode=server.config.default_gamemode,
	))
	C.LoginSuccess.send(c,
		uuid = str(c.player.uuid),
		username = c.player.name,
	)
	c.setstate(PLAY)
	C.JoinGame.send(c,
		eid = c.player.eid,
		gamemode = c.player.gamemode,
		dimension = c.player.dimension,
		difficulty = server.env.difficulty,
		players_max = server.config.players_max,
		level_type = server.config.level_type,
		reduced_debug_info = server.config.reduced_debug_info,
	)
	#c.sendPacket(0x19, # Plugin Message
	#	writeIdentifier('minecraft', 'brand'), # Channel
	#	writeString(server.config.brand), # Data
	#)
	#c.sendPacket(0x0D, # Server Difficulty
	#	writeByte(server.env.difficulty), # Difficulty
	#)
	C.SpawnPosition.send(c,
		x = c.player.pos.x,
		y = c.player.pos.y,
		z = c.player.pos.z,
		pos = c.player.pos.pos[:3],
	)
	C.PlayerAbilities.send(c,
		flags = 0,
		flying_speed = 1.0,
		walking_speed = 1.0,
	)
	C.PlayerPositionAndLook.send(c,
		x = c.player.pos.x,
		y = c.player.pos.y,
		z = c.player.pos.z,
		yaw = c.player.pos.yaw,
		pitch = c.player.pos.pitch,
		on_ground = c.player.pos.on_ground,
		flags = 0,
	)
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

@MCServer.handler(S.KeepAlive)
def handleKeepAlive(server, c, p):
	if (p.keepalive_id == c.lastkeepalive_id): c.lastkeepalive = time.time()

@MCServer.handler(S.ChatMessage)
def handleChatMessage(server, c, p):
	log(c.player.name.join('<>'), p.message)

@MCServer.handler(S.Player)
def handlePlayer(server, c, p):
	c.player.pos.update(
		on_ground = p.on_ground,
	)

@MCServer.handler(S.PlayerPosition)
def handlePlayerPosition(server, c, p):
	c.player.pos.update(
		x = p.x,
		y = p.y,
		z = p.z,
		on_ground = p.on_ground,
	)

@MCServer.handler(S.PlayerLook)
def handlePlayerLook(server, c, p):
	c.player.pos.update(
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)

@MCServer.handler(S.PlayerPositionAndLook)
def handlePlayerPositionAndLook(server, c, p):
	c.player.pos.update(
		x = p.x,
		y = p.y,
		z = p.z,
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)

### XXX ###

def main():
	setlogfile('PyCraft_server.log')
	server = MCServer()
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): logstarted(); main()
else: logimported()

# by Sdore, 2019
