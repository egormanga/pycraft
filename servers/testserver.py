#!/usr/bin/python3
# PyCraft test server

from utils.nolog import *
from ..server import *
logstart('TestServer')

class TestServer(MCServer):
	handlers = Handlers(MCServer.handlers)

	def __init__(self, world, **kwargs):
		super().__init__(**kwargs)
		self.world = world
		world.onchunksectioncreate = self.onchunksectioncreate
		world.onchunkcreate = self.onchunkcreate
		world.onblockupdate = self.onblockupdate
		self._playing_track = 2258

	def onchunksectioncreate(self, cs):
		x, z = cs.x//16, cs.z//16
		for c in self.playing:
			pbm = 0xffff#sum(1 << cy for cy in range(16) if cs.chunks.get(cy))
			cd = zlib.compress(cs.chunkdata_bytes[pbm])
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = True,
				pbm = pbm,
				abm = 0,
				size = len(cd),
				data = cd,
			)

	def onchunkcreate(self, chunk):
		x, z = chunk.x//16, chunk.z//16
		for c in self.playing:
			pbm = 1 << chunk.y//16
			cd = zlib.compress(chunk.blockids_bytes+chunk.blockdata_bytes)
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = False,
				pbm = pbm,
				abm = 0,
				size = len(cd),
				data = cd,
			)

	def onblockupdate(self, block):
		for c in self.playing:
			C.BlockChange.send(c,
				x = block.x,
				y = block.y,
				z = block.z,
				id = block.id,
				data = block.data,
			)

	@property
	def playing_track(self):
		return self._playing_track

	@playing_track.setter
	def playing_track(self, id):
		self._playing_track = id
		for c in self.playing:
			C.Effect.send(c,
				eid = 1005,
				x = 0,
				y = 0,
				z = 0,
				data = self.playing_track,
				drv = False,
			)

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
		cd = zlib.compress(cs.chunkdata_bytes[pbm])
		C.ChunkData.send(c,
			chunk_x = x,
			chunk_z = z,
			full_section = True,
			pbm = pbm,
			abm = 0,
			size = len(cd),
			data = cd,
		)
	bba = server.entities.add_entity(Entity())
	bba.pos.pos = (3, 1, 4)
	C.BlockBreakAnimation.send(c,
		eid = bba.eid,
		x = bba.pos.x,
		y = bba.pos.y,
		z = bba.pos.z,
		stage = 9,
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

	c.player.inventory[36].set(1)
	C.WindowItems.send(c,
		window_id = 0,
		count = len(c.player.inventory),
		slots = c.player.inventory,
	)

	C.Effect.send(c,
		eid = 1005,
		x = 0,
		y = 0,
		z = 0,
		data = server.playing_track,
		drv = False,
	)

	p_uuid = list(str(uuid.uuid1()))
	p_uuid[14] = '2' # uuid v2
	p_uuid = str().join(p_uuid)
	e = server.entities.add_entity(Entity())
	e.pos.pos = (10, 2, 10)
	e.pos.pitch = 180
	C.SpawnPlayer.send(c,
		eid = e.eid,
		uuid = p_uuid,
		name = 'test',
		x = e.pos.x,
		y = e.pos.y,
		z = e.pos.z,
		yaw = 256*(e.pos.yaw % 360)/360,
		pitch = 256*e.pos.pitch/360,
		item = 10,
		metadata = PVs[c.pv].EntityMetadata.Human(health=1, has_no_ai=True),
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

@MCServer.handler(S.Player)
def handlePlayer(server, c, p):
	c.player.pos.update(
		on_ground = p.on_ground,
	)

@TestServer.handler(S.PlayerPosition)
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
			y = c.player.pos.head_y,
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

@MCServer.handler(S.PlayerLook)
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

@TestServer.handler(S.PlayerPositionAndLook)
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
			y = c.player.pos.head_y,
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

@TestServer.handler(S.PlayerDigging)
def handlePlayerDigging(server, c, p):
	statuses = S.PlayerDigging[c.pv].status
	if (p.status == statuses.DIGGING_FINISH or (p.status == statuses.DIGGING_START and c.player.gamemode == 1)):
		server.world[c.player.dimension][p.x, p.y, p.z].set(0)
	elif (p.status == statuses.DROP_ITEM):
		slot = c.player.selected_slot
		c.player.inventory[slot].set(-1)
		C.SetSlot.send(c,
			window_id = 0,
			slot = slot,
			slot_data = c.player.inventory[slot],
		)
	else: dlog(p.status)

@TestServer.handler(S.PlayerBlockPlacement)
def handlePlayerBlockPlacement(server, c, p):
	x, y, z, id, data = p.x, p.y, p.z, p.held_item.id, p.held_item.nbt.get('data', 0) # TODO FIXME data key
	if (id == -1): return
	if (id in range(2256, 2267)): server.playing_track = id; return
	if (not (x == -1 and y == 255 and z == -1)):
		faces = S.PlayerBlockPlacement[c.pv].face
		if (p.face == faces.X_POS): x += 1
		elif (p.face == faces.X_NEG): x -= 1
		elif (p.face == faces.Y_POS): y += 1
		elif (p.face == faces.Y_NEG): y -= 1
		elif (p.face == faces.Z_POS): z += 1
		elif (p.face == faces.Z_NEG): z -= 1
		if (y in range(256)): server.world[c.player.dimension][x, y, z].set(id, data)

@TestServer.handler(S.HeldItemChange)
def handleHeldItemChange(server, c, p):
	c.player.selected_slot = 36+p.slot

@apmain
@aparg('-p', '--port', metavar='port', type=int, default=25565)
def main(cargs):
	setlogfile('PyCraft_testserver.log')

	class config(TestServerConfig):
		server_port = cargs.port

	try: world = World.open('PyCraft_testserver.world')
	except Exception:
		world = World()
		for x in range(16):
			for z in range(16):
				world[0][x, 0, z].set(1)
		world[0][3, 1, 4].set(1)

	server = TestServer(world, config=config)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()
		finally: world.save('PyCraft_testserver.world')

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
