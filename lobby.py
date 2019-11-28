#!/usr/bin/python3
# PyCraft lobby

from utils.nolog import *
from pycraft.server import *
from pycraft.client import *
logstart('Lobby')

class LobbyConfig(ServerConfig):
	version_name = 'PyCraft Lobby {}'
	default_gamemode = 3
	difficulty = 0
	players_max = -1
	reduced_debug_info = True
	motd = "A PyCraft Lobby"

class MCLobby(MCServer):
	handlers = Handlers(MCServer.handlers)

	def __init__(self, lobby_serverips, lobby_userdata, config=LobbyConfig, *args, **kwargs):
		super().__init__(*args, config=config, **kwargs)
		self.lobby_serverips, self.lobby_userdata = lobby_serverips, lobby_userdata
		self.lobby_playerstate = Sdict(lambda: False)  # False = authorization, str = register confirmation, True = logged in, other = playing
		self.lobby_clientsettings = dict()

	def handle_client_packet(self, c):
		s = self.lobby_playerstate[c]
		if (isinstance(s, MCClient)):
			try: l, pid = s.readPacketHeader()
			except NoServer: c.socket.close(); del self.lobby_playerstate[c]; return
			except NoPacket: pass
			else: c.sendPacket(pid, s.packet.read(l))

			try: l, pid = c.readPacketHeader()
			except NoServer: s.disconnect(); del self.lobby_playerstate[c]; return
			except NoPacket: pass
			else: s.sendPacket(pid, c.packet.read(l))
		else: super().handle_client_packet(c)

	def tick(self):
		super().tick()

		for c, s in self.lobby_playerstate.items():
			if (not isinstance(s, MCClient)): continue
			try: pid, p = s.handle()
			except NoServer: c.socket.close(); del self.lobby_playerstate[c]; return
			else: c.sendPacket(pid, p)

@MCLobby.handler(S.LoginStart)
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
		dimension=-1,
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
	C.PlayerPositionAndLook.send(c,
		x = c.player.pos.x,
		y = c.player.pos.y,
		z = c.player.pos.z,
		yaw = c.player.pos.yaw,
		pitch = c.player.pos.pitch,
		on_ground = c.player.pos.on_ground,
		flags = 0,
	)

	C.ChatMessage.send(c,
		message = {'text': '', 'extra': [
			{'text': server.config.motd, 'bold': True},
		]},
	)
	registered = (c.player.name in server.lobby_userdata)
	C.ChatMessage.send(c,
		message = {'text': '', 'extra': [
			{'text': "[Login]" if (registered) else "[Register]", 'color': 'green' if (registered) else 'blue', 'bold': True},
			{'text': " Enter your password."},
		]},
	)

@MCLobby.handler(S.ChatMessage)
def handleChatMessage(server, c, p):
	phash = hashlib.sha3_256(b'Py\0'+p.message.encode()+b'\1Craft').hexdigest()

	if (server.lobby_playerstate[c] is None):
		del server.lobby_playerstate[c]
		raise Disconnect("Error.", color='red')
	if (server.lobby_playerstate[c] is False):
		if (c.player.name not in server.lobby_userdata):
			server.lobby_playerstate[c] = phash
			C.ChatMessage.send(c,
				message = {'text': "Confirm the password"},
			)
			return
		if (phash != server.lobby_userdata[c.player.name]): raise Disconnect("Wrong password.", color='red')
		server.lobby_playerstate[c] = True
		done = 'Login'
	elif (isinstance(server.lobby_playerstate[c], str)):
		if (server.lobby_playerstate[c] != phash): raise Disconnect("Passwords don't match.", color='red')
		server.lobby_userdata[c.player.name] = phash
		server.lobby_playerstate[c] = True
		done = 'Register'
	else:
		try: server_ip = server.lobby_serverips[int(p.message)-(int(p.message) > 0)]
		except Exception as ex: raise Disconnect({'text': f"{type(ex).__name__}: ", 'color': 'red', 'bold': True}, {'text': str(ex)})

		cs = server.lobby_clientsettings.pop(c)
		class config(ClientConfig):
			username = c.player.name
			locale = cs.locale
			difficulty = cs.difficulty
			view_distance = cs.view_distance
			chat_mode = cs.chat_flags & 0b11
			chat_colors = cs.chat_colors
			skin_parts = cs.skin_parts if ('skin_parts' in cs) else cs.show_cape
			main_hand = cs.get('main_hand', 1)

		sc = Builder(MCClient, config=config, pv=c.pv, nolog=True) \
			.connect(server_ip) \
			.login() \
			.block(pid=C.JoinGame) \
			.build()
		C.Respawn.send(c,
			dimension = (sc.player.dimension+1) % 2,
			difficulty = sc.difficulty,
			gamemode = sc.player.gamemode,
			level_type = sc.level_type,
		)
		C.Respawn.send(c,
			dimension = sc.player.dimension,
			difficulty = sc.difficulty,
			gamemode = sc.player.gamemode,
			level_type = sc.level_type,
		)
		server.lobby_playerstate[c] = sc
		return

	C.ChatMessage.send(c,
		message = {'text': '', 'extra': [
			{'text': f"{done} successful!", 'color': 'green'},
		]},
	)
	C.ChatMessage.send(c,
		message = {'text': "Choose the server to join:"},
	)

	for ii, i in enumerate(server.lobby_serverips):
		s = Builder(MCClient, nolog=True).connect(i).build().status()
		C.ChatMessage.send(c,
			message = {'text': '', 'extra': [
				{'text': f"[{ii+1}]", 'bold': True},
				{'text': f" {s['description']} ({s['players']['online']}/{s['players']['max']}, {s['version']['name']})"},
			]},
		)

@MCLobby.handler(S.ClientSettings)
def handleClientSettings(server, c, p):
	server.lobby_clientsettings[c] = p

def main():
	lobby_userdata = dict()

	setlogfile('PyCraft_lobby.log')
	db.setfile('PyCraft_lobby.db')
	db.register('lobby_userdata')
	db.load()

	server = MCLobby([('flafe.org', 26565)], lobby_userdata, config=LobbyConfig)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): logstarted(); exit(main())
else: logimported()

# by Sdore, 2019