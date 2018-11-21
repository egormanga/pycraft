#!/usr/bin/python3
# PyCraft client

from . import *
from utils import *; logstart('Client')

class _config:
	default_username = 'PyPlayer'
	locale = locale.getlocale()[0]
	view_distance = 0
	chat_mode = 0
	chat_colors = False
	skin_parts = 0b1111111
	main_hand = 1
	brand = 'pycraft'
	keepalive_timeout = 2000
config = _config()

class MCClient(PacketBuffer, Updatable):
	def __init__(self, name=config.default_username):
		self.socket = socket.socket()
		self.player = Player(name=name)
		self.server_brand = str()
		self.pv = int()
		self.nextkeepalive = 0
		self.lastkeepalive = float('inf')
		self.lastkeepalive_id = 0
		self.tick = int()
		self.startedAt = time.time()
		self.setstate(-1)
	def connect(self, ip=None, port=None):
		if (ip is None): ip = self.ip
		if (port is None): port = self.port
		self.update(locals())
		self.socket = socket.socket()
		self.socket.settimeout(10)
		self.socket.connect((self.ip, self.port))
		#self.socket.settimeout(None)
		#self.socket.setblocking(False)
		PacketBuffer.__init__(self, self.socket)
		self.tick = 0
		log("Connected to server.")
	def disconnect(self, text=''):
		try: self.socket.shutdown(socket.SHUT_WR)
		except socket.error: pass
		while (True):
			try: assert self.socket.recv(1)
			except Exception as ex:
				if (isinstance(ex, socket.error) and ex.errno in (socket.EAGAIN, socket.EWOULDBLOCK)): continue
				else: break
		self.socket.close()
		self.setstate(-1)
		log(f"Disconnected from server{': '+text if (text) else ''}.")
	def setstate(self, state):
		self.state = State(state)

	handlers = Handlers()
	def handle(self):
		if (self.state == -1): raise NoServer
		self.tick += 1
		#log("\033[K\033[2m%.4f ticks/sec." % ((time.time()-self.startedAt)/self.tick), end='\033[0m\r', raw=True, nolog=True)
		if (self.state == PLAY and time.time() > self.lastkeepalive+config.keepalive_timeout): self.setstate(-1); return
		try: l, pid = self.readPacketHeader()
		except NoPacket: return
		try: self.handlers[self, pid](self)
		except NoHandlerError:
			log(1, f"Unhandled packet at state {self.state}: length={l} pid={hex(pid)}", nolog=True)
			log(2, self.packet.read(l), raw=True)
		log(4, '-'*os.get_terminal_size()[0]+'\n', raw=True)
		return pid
	@classmethod
	def handler(self, packet):
		return self.handlers.handler(packet)

	def block(self, pid=-1, state=-1):
		if (pid == -1 and state == -1): return
		pid = pid[self.pv].pid
		lpid = -1
		while ((state != -1 and self.state != state) or (pid != -1 and lpid != pid)): lpid = self.handle()

	def status(self):
		self.sendHandshake(1)
		Ping.send(self, time.time())
		self.block(Pong, STATUS)
		return self.sendStatusRequest()

	def login(self):
		#self.status()
		#self. # TODO ???
		self.sendHandshake(2)
		LoginStart.send(self, self.player.name)

	def leave(self):
		self.disconnect()
		self.connect()

	def sendHandshake(self, state):
		Handshake.send(self, self.pv, self.ip, self.port, state)
		self.setstate(state)
	def sendChatMessage(self, message):
		self.sendPacket(0x02, # Chat Message
			writeString(message, 256), # Message
		)
		log(f"Sent: «{message}»")
	def sendPlayerPositionAndLook(self):
		self.sendPacket(0x11, # Player Position And Look
			writeDouble(self.player.x), # X
			writeDouble(self.player.y), # Y
			writeDouble(self.player.z), # Z
			writeFloat(self.player.yaw), # Yaw
			writeFloat(self.player.pitch), # Pitch
			writeBool(self.player.on_ground), # On Ground
		)
class NoServer(Exception): pass

### XXX ###

@MCClient.handler(Pong) # Pong
def handlePong(s):
	payload, = Pong.recv(s)
	s.ping = time.time()-payload

@MCClient.handler(LoginSuccess)
def handleLoginSuccess(s):
	uuid, name, = LoginSuccess.recv(c)
	s.player.update(
		uuid = uuid,
		name = name,
	)
	s.setstate(PLAY)
	log(1, f"Login Success: {s.player}")

#@MCClient.handler(0x03, LOGIN) # Set Compression
def handleSetCompression(s):
	s.compression = readVarInt(s)
	log(1, f"Set Compression: {s.compression}")

#@MCClient.handler(0x0D, PLAY) # Server Difficulty
def handleServerDifficulty(s):
	s.difficulty = readUByte(s) # Difficulty

#@MCClient.handler(0x19, PLAY) # Plugin Message
def handlePluginMessage(s):
	ns, ch = readIdentifier(s)
	if (ns == 'minecraft'):
		if (ch == 'brand'):
			s.server_brand = readString(s)
	s.sendPacket(0x0A, # Plugin Message
		writeIdentifier('minecraft', 'brand'),
		writeString(config.brand),
	)

@MCClient.handler(LoginDisconnect)
def handleDisconnect(s):
	reason, = LoginDisconnect.recv(s)
	s.disconnect(reason)

#@MCClient.handler(0x21, PLAY) # Keep Alive
def handleKeepAlive(s):
	s.sendPacket(0x0E, # Keep Alive
		writeLong(readLong(s)), # Keep Alive ID
	)
	s.lastkeepalive = time.time()

#@MCClient.handler(0x25, PLAY) # Join Game
def handleJoinGame(s):
	s.player.update(
		eid = readInt(s), # Entity ID
		gamemode = readUByte(s), # Gamemode
		dimension = readInt(s), # Dimension
	)
	s.difficulty = readUByte(s) # Difficulty
	s.max_players = readUByte(s) # Max Players
	s.level_type = readString(s, 16) # Level Type
	s.reduced_debug_info = readBool(s) # Reduced Debug Info

#@MCClient.handler(0x2E, PLAY) # Player Abilities
def handlePlayerAbilities(s):
	NotImplemented # Placeholder
	s.sendPacket(0x04, # Client Settings
		writeString(config.locale, 16), # Locale
		writeByte(config.view_distance), # View Distance
		writeVarInt(config.chat_mode), # Chat Mode
		writeBool(config.chat_colors), # Chat Colors
		writeUByte(config.skin_parts), # Displayed Skin Parts
		writeVarInt(config.main_hand), # Main Hand
	)

#@MCClient.handler(0x32, PLAY) # Player Position And Look
def handlePlayerPositionAndLook(s):
	s.player.updatePos(
		x = readDouble(s), # X
		y = readDouble(s), # Y
		z = readDouble(s), # Z
		yaw = readFloat(s), # Yaw
		pitch = readFloat(s), # Pitch
		flags = readByte(s), # Flags
	)
	log(1, f"Player Position And Look: {s.player}")
	s.sendPacket(0x00, # Teleport Confirm
		writeVarInt(readVarInt(s)), # Teleport ID
	)
	s.sendPlayerPositionAndLook()
	s.sendPacket(0x03, # Client Status
		writeVarInt(0), # Action ID
	)

#@MCClient.handler(0x00, PLAY) # Spawn Object
#@MCClient.handler(0x03, PLAY) # Spawn Mob
#@MCClient.handler(0x1C, PLAY) # Entity Status
#@MCClient.handler(0x22, PLAY) # Chunk Data
#@MCClient.handler(0x23, PLAY) # Effect
#@MCClient.handler(0x28, PLAY) # Entity Relative Move
#@MCClient.handler(0x29, PLAY) # Entity Look And Relative Move
#@MCClient.handler(0x35, PLAY) # Destroy Entities
#@MCClient.handler(0x39, PLAY) # Entity Head Look
#@MCClient.handler(0x3F, PLAY) # Entity Metadata
#@MCClient.handler(0x41, PLAY) # Entity Velocity
#@MCClient.handler(0x42, PLAY) # Entity Equipment
#@MCClient.handler(0x4A, PLAY) # Time Update
#@MCClient.handler(0x4E, PLAY) # Player List Header And Footer
#@MCClient.handler(0x50, PLAY) # Entity Teleport
#@MCClient.handler(0x52, PLAY) # Entity Properties
def handleDummy(s): # TODO: Implement me!
	NotImplemented # To prevent spamming with «Unhandled packet» in logs

def main(ip, port=25565, name=config.default_username):
	setlogfile('PyCraft_client.log')
	client = MCClient(name=name)
	client.connect(ip, port)
	client.login()
	while (True):
		try: client.handle()
		except NoServer as ex: exit(ex)
		except Exception as ex: exception(ex, nolog=True)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

if (__name__ == '__main__'):
	argparser.add_argument('ip', metavar='<ip>')
	argparser.add_argument('port', nargs='?', default=25565)
	argparser.add_argument('--name', metavar='username', nargs='?', default=config.default_username)
	cargs = argparser.parse_args()
	logstarted(); main(cargs.ip, int(cargs.port), cargs.name)
else: logimported()

# by Sdore, 2018
