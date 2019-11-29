#!/usr/bin/python3
# PyCraft test server

from utils.nolog import *
from ..server import *
logstart('TestServer')

class TestServer(MCServer):
	handlers = Handlers(MCServer.handlers)

class TestServerConfig(ServerConfig):
	default_gamemode = 1
	motd = "PyCraft Test Server"

@TestServer.handler(S.LoginStart)
def handleLoginStart(server, c, p):
	pv = requireProtocolVersion(c.pv)
	if (c.pv != pv): raise Disconnect(f"Outdated {'client' if (c.pv < pv) else 'server'}")

	try: profile = MojangAPI.profile(p.name)[0]
	except Exception: profile = {'name': p.name, 'id': uuid3(NAMESPACE_OID, "OfflinePlayer:"+p.name)}
	c.player = server.entities.add_player(Player(
		name=profile['name'],
		uuid=profile['id'],
		gamemode=server.config.default_gamemode,
	))
	c.player.pos.pos = (0.5, 1, 0.5)
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

	cd = bytearray()
	cd += bytes(i.id for i in testchunk.blocks)
	cd += bytes(i.data for i in testchunk.blocks)
	cd = zlib.compress(cd)
	C.ChunkData.send(c,
		chunk_x = 0,
		chunk_z = 0,
		guc = True,
		pbm = 0xf,
		abm = 0,
		size = len(cd),
		data = cd,
	)

	C.PlayerPositionAndLook.send(c,
		x = c.player.pos.x,
		y = c.player.pos.head_y,
		z = c.player.pos.z,
		yaw = c.player.pos.yaw,
		pitch = c.player.pos.pitch,
		on_ground = c.player.pos.on_ground,
		flags = 0,
	)
	C.Effect.send(c,
		eid = 1005,
		x = 0,
		y = 0,
		z = 0,
		data = 2258,
		drv = False,
	)

@MCServer.handler(S.PlayerPosition)
def handlePlayerPosition(server, c, p):
	c.player.pos.update(
		x = p.x,
		y = p.y,
		z = p.z,
		on_ground = p.on_ground,
	)
	if (c.player.pos.y < -16):
		c.player.pos.pos = (0.5, 1, 0.5)
		C.PlayerPositionAndLook.send(c,
			x = c.player.pos.x,
			y = c.player.pos.head_y,
			z = c.player.pos.z,
			yaw = c.player.pos.yaw,
			pitch = c.player.pos.pitch,
			on_ground = c.player.pos.on_ground,
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
	if (c.player.pos.y < -16):
		c.player.pos.pos = (0.5, 1, 0.5)
		C.PlayerPositionAndLook.send(c,
			x = c.player.pos.x,
			y = c.player.pos.head_y,
			z = c.player.pos.z,
			yaw = c.player.pos.yaw,
			pitch = c.player.pos.pitch,
			on_ground = c.player.pos.on_ground,
		)

@apmain
@aparg('-p', '--port', metavar='port', type=int, default=25565)
def main(cargs):
	setlogfile('PyCraft_testserver.log')

	class config(TestServerConfig):
		port = cargs.port

	server = TestServer(config=config)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
