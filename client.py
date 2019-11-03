#!/usr/bin/python3
# PyCraft client

from . import *; logstart('Client')

class ClientConfig:
	username = 'PyPlayer'
	locale = locale.getlocale()[0]
	difficulty = 0
	view_distance = 0
	chat_mode = 0
	chat_colors = False
	skin_parts = 0b1111111
	main_hand = 1
	brand = 'pycraft'
	keepalive_timeout = 20

class MCClient(PacketBuffer, Updatable):
	def __init__(self, config=ClientConfig):
		self.config = config()
		self.handlers = Handlers(self.handlers)
		self.handler = lambda x: self.handlers.handler(x)
		self.socket = socket.socket()
		self.player = Player(name=self.config.username)
		self.pv = max(PVs)
		self.lastkeepalive = inf
		self.lastkeepalive_id = 0
		self.ping = 0
		self.state = DISCONNECTED
		self.tick = int()
		self.startedAt = time.time()

	def connect(self, addr=None):
		if (addr is not None): self.addr = addr
		self.socket = socket.socket()
		self.socket.settimeout(10)
		try: self.socket.connect(self.addr)
		except OSError as ex: raise \
			NoServer(ex)
		self.socket.setblocking(True)
		PacketBuffer.__init__(self, self.socket)
		log("Connected to server.")

	def disconnect(self, reason=None):
		try: self.socket.shutdown(socket.SHUT_WR)
		except OSError: pass
		self.socket.close()
		self.setstate(DISCONNECTED)
		log(f"""Disconnected from server{f": '{formatChat(reason)}'" if (reason is not None) else ''}.""")

	def setstate(self, state):
		self.state = State(state)

	handlers = Handlers()
	def handle(self):
		if (self.state == DISCONNECTED): raise NoServer()
		if (self.state == PLAY and time.time() > self.lastkeepalive+self.config.keepalive_timeout): self.setstate(DISCONNECTED); return (-1, None)
		try: l, pid = self.readPacketHeader()
		except NoPacket: return (-1, None)
		try:
			p = self.handlers[self, pid]
			h = self.handlers[p]
		except KeyError:
			log(1, f"Unhandled packet at state {self.state}: length={l} pid={hex(pid)}", nolog=True)
			p = self.packet.read(l)
			log(2, p, raw=True, nolog=True)
			log(4, '-'*80+'\n', raw=True, nolog=True)
		else:
			p = p.recv(self)
			h(self, p)
		return (pid, p)

	@classmethod
	def handler(cls, packet):
		return cls.handlers.handler(packet)

	def block(self, pid=-1, state=-1):
		if (pid == -1 and state == -1): return
		if (pid != -1): pid = pid[self.pv].pid
		lpid = -1
		while ((state != -1 and self.state != state) or (pid != -1 and lpid != pid)): lpid, p = self.handle()
		return p

	def sendHandshake(self, state):
		self.disconnect()
		self.connect()
		self.setstate(HANDSHAKING)
		S.Handshake.send(self,
			pv = self.pv,
			addr = self.addr[0],
			port = self.addr[1],
			state = state,
		)
		self.setstate(state)

	def status(self):
		self.sendHandshake(STATUS)
		S.StatusRequest.send(self)
		s = self.block(C.StatusResponse, STATUS)
		S.Ping.send(self,
			payload = time.time(),
		)
		self.block(C.Pong, STATUS)
		return s.response

	def login(self):
		if (not self.ping): self.status()
		self.sendHandshake(LOGIN)
		S.LoginStart.send(self,
			name = self.player.name,
		)
class NoServer(Exception): pass

### XXX ###

@MCClient.handler(C.StatusResponse)
def handleStatusResponse(s, p):
	s.pv = requireProtocolVersion(p.response['version']['protocol'])

@MCClient.handler(C.Pong)
def handlePong(s, p):
	s.ping = time.time()-p.payload

@MCClient.handler(C.LoginDisconnect)
def handleLoginDisconnect(s, p):
	s.disconnect(p.reason)

@MCClient.handler(C.LoginSuccess)
def handleLoginSuccess(s, p):
	s.player.update(
		uuid = p.uuid,
		name = p.username,
	)
	s.setstate(PLAY)
	log(1, f"Login Success: {s.player}")

@MCClient.handler(C.KeepAlive)
def handleKeepAlive(s, p):
	S.KeepAlive.send(s,
		keepalive_id = p.keepalive_id,
	)
	s.lastkeepalive = time.time()

@MCClient.handler(C.JoinGame)
def handleJoinGame(s, p):
	s.player.update(
		eid = p.eid,
		gamemode = p.gamemode,
		dimension = p.dimension,
	)
	s.difficulty = p.difficulty
	s.players_max = p.players_max
	s.level_type = p.level_type
	s.reduced_debug_info = p.reduced_debug_info

@MCClient.handler(C.Disconnect)
def handleDisconnect(s, p):
	s.disconnect(p.reason)

@MCClient.handler(C.ChatMessage)
def handleChatMessage(s, p):
	log(p.message)

def main(cargs):
	setlogfile('PyCraft_client.log')
	class config(ClientConfig):
		username = cargs.name
	client = MCClient(config=config)
	try: client.connect((cargs.ip, cargs.port))
	except NoServer as ex: exit(ex)
	s = client.status()
	log(f"Server '{s['description']['text']}', ping {client.ping}")
	client.login()
	while (True):
		try: client.handle()
		except NoServer: exit("Disconnected.")
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

if (__name__ == '__main__'):
	argparser.add_argument('ip', metavar='<ip>')
	argparser.add_argument('port', nargs='?', type=int, default=25565)
	argparser.add_argument('-name', metavar='username', nargs=1, default=ClientConfig.username)
	cargs = argparser.parse_args()
	logstarted(); exit(main(cargs))
else: logimported()

# by Sdore, 2019
