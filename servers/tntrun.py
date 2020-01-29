#!/usr/bin/python3
# PyCraft TNT Run server

from utils.nolog import *
from ..server import *
logstart('TNTRunServer')

class TNTRunConfig(ServerConfig):
	motd = "§d§lPyCraft§f TNT Run"

class TNTRunServer(MCServer):
	handlers = Handlers(MCServer.handlers)

	def __init__(self, world, **kwargs):
		super().__init__(**kwargs)
		self.world = world
		world.onchunksectioncreate = self.onchunksectioncreate
		world.onchunkcreate = self.onchunkcreate
		world.onblockupdate = self.onblockupdate

	def tick(self):
		super().tick()

		if (self.ticks % 2):
			for p in self.players:
				if (p.pos.x < 1 and p.pos.z < 1): continue
				if (p.pos.on_ground): self.world[p.dimension][math.floor(p.pos.x-.3):math.ceil(p.pos.x+.3), p.pos.y-1, math.floor(p.pos.z-.3):math.ceil(p.pos.z+.3)] = 0
				self.world[p.dimension][0, 0, 0] = 1

	def onchunksectioncreate(self, cs):
		x, z = cs.x//16, cs.z//16
		pbm = -1
		abm, cd = cs.chunkdata_bytes[pbm]
		cd = zlib.compress(cd)
		for c in self.playing:
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = True,
				pbm = pbm,
				abm = abm,
				size = len(cd),
				data = cd,
			)

	def onchunkcreate(self, chunk):
		x, z = chunk.x//16, chunk.z//16
		pbm = 1 << chunk.y//16
		abm, cd = chunk.abm, chunk.blockids_bytes+chunk.blockdata_bytes
		cd = zlib.compress(cd)
		for c in self.playing:
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = False,
				pbm = pbm,
				abm = abm,
				size = len(cd),
				data = cd,
			)

	def onblockupdate(self, block, old):
		if ((block.id, block.data) == old): return
		for c in self.playing:
			C.BlockChange.send(c,
				x = block.x,
				y = block.y,
				z = block.z,
				id = block.id,
				data = block.data,
			)

@TNTRunServer.handler(S.LoginStart)
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
		uuid = c.player.uuid,
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

	for (x, z), cs in server.world[c.player.dimension].chunksec.items():
		pbm = sum(1 << cy for cy in range(16) if cs.chunks.get(cy))
		abm, cd = cs.chunkdata_bytes[pbm]
		cd = zlib.compress(cd)
		C.ChunkData.send(c,
			chunk_x = x,
			chunk_z = z,
			full_section = True,
			pbm = pbm,
			abm = abm,
			size = len(cd),
			data = cd,
		)

	C.PlayerPositionAndLook.send(c,
		x = c.player.pos.x,
		y = c.player.pos.head_y+1e-8,
		z = c.player.pos.z,
		yaw = c.player.pos.yaw,
		pitch = c.player.pos.pitch,
		on_ground = c.player.pos.on_ground,
	)

	for i in server.playing:
		if (i is c): continue
		C.SpawnPlayer.send(c,
			eid = i.player.eid,
			uuid = i.player.uuid,
			name = i.player.name,
			x = i.player.pos.x,
			y = i.player.pos.y,
			z = i.player.pos.z,
			yaw = 256*(i.player.pos.yaw % 360)/360,
			pitch = 256*i.player.pos.pitch/360,
			item = i.player.inventory[i.player.selected_slot].id,
			metadata = PVs[c.pv].EntityMetadata.Human(health=1), # TODO
		)
		C.SpawnPlayer.send(i,
			eid = c.player.eid,
			uuid = c.player.uuid,
			name = c.player.name,
			x = c.player.pos.x,
			y = c.player.pos.y,
			z = c.player.pos.z,
			yaw = 256*(c.player.pos.yaw % 360)/360,
			pitch = 256*c.player.pos.pitch/360,
			item = c.player.inventory[c.player.selected_slot].id,
			metadata = PVs[i.pv].EntityMetadata.Human(health=1), # TODO
		)

@TNTRunServer.handler(S.Player)
def handlePlayer(server, c, p):
	c.player.pos.update(
		on_ground = p.on_ground,
	)

@TNTRunServer.handler(S.PlayerPosition)
def handlePlayerPosition(server, c, p):
	x, y, z = c.player.pos.pos[:3]
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
			y = c.player.pos.head_y+1e-8,
			z = c.player.pos.z,
			yaw = 256*(c.player.pos.yaw % 360)/360,
			pitch = c.player.pos.pitch,
			on_ground = c.player.pos.on_ground,
		)
	for i in server.playing:
		if (i is c): continue
		dx, dy, dz = c.player.pos.x-x, c.player.pos.y-y, c.player.pos.z-z
		if (max(map(abs, (dx, dy, dz))) <= 0): # TODO FIXME <= 4
			C.EntityRelativeMove.send(i,
				eid = c.player.eid,
				dx = dx,
				dy = dy,
				dz = dz,
			)
		else:
			C.EntityTeleport.send(i,
				eid = c.player.eid,
				x = c.player.pos.x,
				y = c.player.pos.y,
				z = c.player.pos.z,
				yaw = 256*(c.player.pos.yaw % 360)/360,
				pitch = 256*c.player.pos.pitch/360,
			)

@TNTRunServer.handler(S.PlayerLook)
def handlePlayerLook(server, c, p):
	c.player.pos.update(
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)
	for i in server.playing:
		if (i is c): continue
		C.EntityLook.send(i,
			eid = c.player.eid,
			yaw = 256*(c.player.pos.yaw % 360)/360,
			pitch = 256*c.player.pos.pitch/360,
		)
		C.EntityHeadLook.send(i,
			eid = c.player.eid,
			head_yaw = 256*(c.player.pos.yaw % 360)/360,
		)

@TNTRunServer.handler(S.PlayerPositionAndLook)
def handlePlayerPositionAndLook(server, c, p):
	x, y, z = c.player.pos.pos[:3]
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
			y = c.player.pos.head_y+1e-8,
			z = c.player.pos.z,
			yaw = 256*(c.player.pos.yaw % 360)/360,
			pitch = c.player.pos.pitch,
			on_ground = c.player.pos.on_ground,
		)
	for i in server.playing:
		if (i is c): continue
		dx, dy, dz = c.player.pos.x-x, c.player.pos.y-y, c.player.pos.z-z
		if (max(map(abs, (dx, dy, dz))) <= 0): # TODO FIXME <= 4
			C.EntityLookAndRelativeMove.send(i,
				eid = c.player.eid,
				dx = dx,
				dy = dy,
				dz = dz,
				yaw = 256*(c.player.pos.yaw % 360)/360,
				pitch = 256*c.player.pos.pitch/360,
			)
		else:
			C.EntityTeleport.send(i,
				eid = c.player.eid,
				x = c.player.pos.x,
				y = c.player.pos.y,
				z = c.player.pos.z,
				yaw = 256*(c.player.pos.yaw % 360)/360,
				pitch = 256*c.player.pos.pitch/360,
			)
		C.EntityHeadLook.send(i,
			eid = c.player.eid,
			head_yaw = 256*(c.player.pos.yaw % 360)/360,
		)

@TNTRunServer.handler(S.ChatMessage)
def handleChatMessage(server, c, p):
	log(c.player.name.join('<>'), p.message)
	m = {'translate': 'chat.type.text', 'with': [c.player.name, p.message]}
	for i in server.playing:
		C.ChatMessage.send(i,
			message = m,
		)

@apmain
@aparg('-p', '--port', metavar='port', type=int, default=25565)
def main(cargs):
	setlogfile('PyCraft_tntrun.log')

	class config(TNTRunConfig):
		server_port = cargs.port

	world = World()
	world[0][0:16, 0, 0:16] = 46  # TNT

	server = TNTRunServer(world, config=config)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
