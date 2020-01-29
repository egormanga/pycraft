#!/usr/bin/python3
# PyCraft test server

from utils.nolog import *
from ..server import *
logstart('TestServer')

class TestServerConfig(ServerConfig):
	default_gamemode = 1
	motd = "§d§lPyCraft§f Test Server"

class TestServer(MCServer):
	handlers = Handlers(MCServer.handlers)
	commands = Commands(MCServer.commands)
	events = Events(MCServer.events)

	def __init__(self, world, **kwargs):
		super().__init__(**kwargs)
		self.world = world
		world.create_chunk = self.create_chunk
		world.onchunksectioncreate = self.onchunksectioncreate
		world.onchunkcreate = self.onchunkcreate
		world.onblockupdate = self.onblockupdate
		world.onchunkbulkupdate = self.onchunkbulkupdate
		world.onchunksecbulkupdate = self.onchunksecbulkupdate
		self.time = int()
		self.playing_track = 2258
		self.fall_height = Sdict(lambda: None)
		self.tnts = Slist()
		self.test_entity = self.entities.add_entity(Entity(pos=Position(x=10, y=2, z=10, pitch=180)))

	def create_player(self, **kwargs):
		player = Player(**kwargs)
		player.gamemode = self.config.default_gamemode
		player.pos.pos = (0.5, 1, 0.5)
		player.inventory[36].set(1)
		return player

	def create_chunk(self, chunksec):
		dlog(chunksec)
		chunksec[:, 0, :] = 1

	def onchunksectioncreate(self, cs):
		x, z = cs.x//16, cs.z//16
		pbm = -1
		abm, cd = cs.chunkdata_bytes[pbm]
		for c in self.playing:
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = True,
				pbm = pbm,
				abm = abm,
				data = cd,
			)

	def onchunkcreate(self, chunk):
		x, z = chunk.x//16, chunk.z//16
		pbm = 1 << chunk.y//16
		abm, cd = chunk.abm, chunk.blockids_bytes+chunk.blockdata_bytes
		for c in self.playing:
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = False,
				pbm = pbm,
				abm = abm,
				data = cd,
			)

	def onblockupdate(self, block, old):
		if ((block.id, block.data) != old):
			for c in self.playing:
				C.BlockChange.send(c,
					x = block.x,
					y = block.y,
					z = block.z,
					id = block.id,
					data = block.data,
				)
		self.block_update(block)

	def onchunkbulkupdate(self, chunk, blocks):
		dlog('cbu', len(blocks), 'blocks')
		x, z = chunk.x//16, chunk.z//16
		if (len(blocks) >= 16*16):
			pbm = 1 << chunk.y//16
			abm, cd = chunk.abm, chunk.blockids_bytes+chunk.blockdata_bytes
			for c in self.playing:
				C.ChunkData.send(c,
					chunk_x = x,
					chunk_z = z,
					full_section = False,
					pbm = pbm,
					abm = abm,
					data = cd,
				)
		else:
			records = [x << 28 | z << 24 | y << 16 | (chunk[x, y, z].id & 0xff) << 4 | chunk[x, y, z].data & 0xf for x, y, z in blocks]
			for c in self.playing:
				C.MultiBlockChange.send(c,
					chunk_x = chunk.x//16,
					chunk_z = chunk.z//16,
					records = records,
				)
		for i in blocks:
			self.block_update(chunk[i])

	def onchunksecbulkupdate(self, chunksec, chunks, blocks):
		dlog('csbu', len(chunks), 'chunks')
		x, z = chunksec.x//16, chunksec.z//16
		pbm = sum(1 << cy for cy in chunks)
		abm, cd = chunksec.chunkdata_bytes[pbm]
		for c in self.playing:
			C.ChunkData.send(c,
				chunk_x = x,
				chunk_z = z,
				full_section = False,
				pbm = pbm,
				abm = abm,
				data = cd,
			)
		for i in blocks:
			self.block_update(chunksec[i])

	def block_update(self, block):
		if (block.id == 46):
			block.set(0)
			tnt = self.entities.add_entity(Entity(
				dimension=block.dimension,
				metadata={'age': 0},
			))
			tnt.pos.pos = block.pos
			self.tnts.append(tnt)
			for c in self.playing:
				C.SpawnObject.send(c,
					eid = tnt.eid,
					type = 50,  # Activated TNT
					x = tnt.pos.x+.5,
					y = tnt.pos.y+.5,
					z = tnt.pos.z+.5,
					pitch = 0,
					yaw = 0,
					data = 0,
				)

	def tick(self):
		for c in self.playing:
			self.update_client(c)

		for eid, e in self.entities:
			if (hasattr(e, 'health') and e.health > 0):
				if (not e.pos.on_ground and self.fall_height[eid] is None):
					self.fall_height[eid] = e.pos.y
				elif (e.pos.on_ground and self.fall_height[eid] is not None):
					damage = max(0, self.fall_height[eid]-e.pos.y-3)
					self.fall_height[eid] = None
					if (damage and e.gamemode != 1):
						e.health = max(0, e.health-damage)
			if (not isinstance(e, Player)):
				e.pos.on_ground = bool(self.world[e.dimension][e.pos.x, e.pos.y-1, e.pos.z])
				if (e.pos.on_ground): e.velocity.dy = 0
				e.pos += e.velocity
				e.velocity.dy += -0.04 # TODO FIXME

		self.tnts.discard()
		for ii, i in enumerate(self.tnts):
			i.metadata['age'] += 1
			if (i.metadata['age'] >= 80):
				self.world[i.dimension][
					i.pos.x-2:i.pos.x+2,
					i.pos.y-2:i.pos.y+2,
					i.pos.z-2:i.pos.z+2,
				] = 0
				self.tnts.to_discard(ii)
		self.tnts.discard()

	def update_client(self, c):
		self.update_client_pos(c)
		self.update_client_chunks(c)
		self.update_client_inventory(c)
		self.update_client_health(c)
		self.update_client_world_time(c)
		self.update_client_spawn_position(c)
		self.update_client_playing_track(c)

	def update_client_chunks(self, c):
		for cqx, cqz in c.player.visible_chunk_quads - c.remote.loaded_chunk_quads:
			for cx, cz in ((cqx*2, cqz*2), (cqx*2+1, cqz*2), (cqx*2, cqz*2+1), (cqx*2+1, cqz*2+1)):
				cs = self.world[c.player.dimension].getchunksec(cx, cz)
				pbm = sum(1 << cy for cy in range(16) if cs.chunks.get(cy))
				abm, cd = cs.chunkdata_bytes[pbm]
				C.ChunkData.send(c,
					chunk_x = cx,
					chunk_z = cz,
					full_section = True,
					pbm = pbm,
					abm = abm,
					data = cd,
				)
			c.remote.loaded_chunk_quads.add((cqx, cqz))

		for cqx, cqz in c.remote.loaded_chunk_quads - c.player.visible_chunk_quads:
			for cx, cz in ((cqx*2, cqz*2), (cqx*2+1, cqz*2), (cqx*2, cqz*2+1), (cqx*2+1, cqz*2+1)):
				C.ChunkData.send(c,
					chunk_x = cx,
					chunk_z = cz,
					full_section = True,
					pbm = 0,
				)
			c.remote.loaded_chunk_quads.remove((cqx, cqz))

	def update_client_pos(self, c):
		if (c.remote.pos != c.player.pos.pos):
			C.PlayerPositionAndLook.send(c,
				x = c.player.pos.x,
				y = c.player.pos.head_y+1e-8,
				z = c.player.pos.z,
				yaw = c.player.pos.yaw,
				pitch = c.player.pos.pitch,
				on_ground = c.player.pos.on_ground,
			)
			c.remote.pos = c.player.pos.pos

	def update_client_inventory(self, c):
		if (c.remote.inventory != hash(tuple(c.player.inventory))):
			C.WindowItems.send(c,
				window_id = 0,
				slots = c.player.inventory,
			)
			c.remote.inventory = hash(tuple(c.player.inventory))

	def update_client_health(self, c):
		if (c.remote.health != c.player.health or
		    c.remote.food != c.player.food or
		    c.remote.food_saturation != c.player.food_saturation):
			C.UpdateHealth.send(c,
				health = c.player.health,
				food = c.player.food,
				food_saturation = c.player.food_saturation,
			)
			c.remote.health, c.remote.food, c.remote.food_saturation = c.player.health, c.player.food, c.player.food_saturation

	def update_client_world_time(self, c):
		if (c.remote.world_time != self.time):
			C.TimeUpdate.send(c,
				age = self.time, # TODO
				time = self.time,
			)
			c.remote.world_time = self.time

	def update_client_spawn_position(self, c):
		if (c.remote.spawn_position != c.player.spawn_position.pos):
			C.SpawnPosition.send(c,
				x = c.player.spawn_position.x,
				y = c.player.spawn_position.y,
				z = c.player.spawn_position.z,
			)
			c.remote.spawn_position = c.player.spawn_position.pos

	def update_client_playing_track(self, c):
		if (c.remote.playing_track != self.playing_track):
			C.Effect.send(c,
				eid = 1005,
				x = 0,
				y = 0,
				z = 0,
				data = self.playing_track,
				drv = False,
			)
			c.remote.playing_track = self.playing_track

@TestServer.handler(S.LoginStart)
def handleLoginStart(server, c, p):
	pv = requireProtocolVersion(c.pv)
	if (c.pv != pv): raise Disconnect(f"Outdated {'client' if (c.pv < pv) else 'server'}")

	try: profile = MojangAPI.profile(p.name)[0]
	except Exception: profile = {'name': p.name, 'id': uuid3(NAMESPACE_OID, "OfflinePlayer:"+p.name)}

	player = server.playerdata.get_player(
		name=profile['name'],
		uuid=profile['id'],
	)
	if (player in server.players): raise Disconnect("You are logged in from another location")

	c.player = player
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

	c.player.spawn_position.pos = (0, 1, 0)

	### TODO
	#bba = server.entities.add_entity(Entity())
	#bba.pos.pos = (3, 1, 4)
	#C.BlockBreakAnimation.send(c,
	#	eid = bba.eid,
	#	x = bba.pos.x,
	#	y = bba.pos.y,
	#	z = bba.pos.z,
	#	stage = 9,
	#)
	###

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
	C.SpawnPlayer.send(c,
		eid = server.test_entity.eid,
		uuid = p_uuid,
		name = 'test',
		x = server.test_entity.pos.x,
		y = server.test_entity.pos.y,
		z = server.test_entity.pos.z,
		yaw = 256*(server.test_entity.pos.yaw % 360)/360,
		pitch = 256*server.test_entity.pos.pitch/360,
		item = 10,
		metadata = PVs[c.pv].EntityMetadata.Human(health=1, has_no_ai=True),
	)

	emd = {'flags': 0, 'air': 300, 'health': 20.0, 'potion_effect_color': 0, 'potion_effect_ambient': 0, 'number_of_arrows_in_entity': 0, 'human_flags': 0, 'absorption_hearts': 0.0, 'score': 0}
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
			metadata = PVs[c.pv].EntityMetadata.Human(**emd), # TODO
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
			metadata = PVs[i.pv].EntityMetadata.Human(**emd), # TODO
		)

@TestServer.handler(S.ClientSettings)
def handleClientSettings(server, c, p):
	c.player.settings = p

@TestServer.handler(S.ClientStatus)
def handleClientStatus(server, c, p):
	if (p.action == S.ClientStatus[c.pv].action.RESPAWN):
		c.player.health = 20
		c.player.pos.pos = c.player.spawn_position.pos
		C.Respawn.send(c,
			dimension = c.player.dimension,
			difficulty = server.env.difficulty,
			gamemode = c.player.gamemode,
			level_type = server.config.level_type,
		)
	else: dlog(p.action)

@TestServer.handler(S.Player)
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
	c.remote.pos = c.player.pos.pos

	if (c.player.pos.y < -16):
		c.player.pos.pos = (0.5, 1, 0.5)

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

@TestServer.handler(S.PlayerLook)
def handlePlayerLook(server, c, p):
	c.player.pos.update(
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)
	c.remote.pos = c.player.pos.pos

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
	c.remote.pos = c.player.pos.pos

	if (c.player.pos.y < -16):
		c.player.pos.pos = (0.5, 1, 0.5)

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

@TestServer.handler(S.ChatMessage)
def handleChatMessage(server, c, p):
	if (p.message[0] == '/'):
		try: server.commands.execute(p.message, c)
		except CommandException as ex:
			C.ChatMessage.send(c,
				message = {'translate': ex.translate, 'with': ex.args, 'color': 'red'},
			)
	else:
		log(c.player.name.join('<>'), p.message)
		m = {'translate': 'chat.type.text', 'with': [c.player.name, p.message]}
		for i in server.playing:
			C.ChatMessage.send(i,
				message = m,
			)

@TestServer.command('/help', show=False)
def c_help(server, c):
	C.ChatMessage.send(c,
		message = {'text': '', 'extra': [{'text': "Available commands: ", 'color': 'green', 'bold': True}, Sstr(', ').join(sorted(server.commands.help_commands), last=' and '), '.']},
	)

@staticitemget
def parse_coords(type): return lambda pos, x, y, z: cast(type, type, type)(pos[ii]+float(i[1:] or 0) if (i.startswith('~')) else i for ii, i in enumerate((x, y, z)))

@TestServer.command('/tp')
def c_tp(server, c, x, y, z):
	x, y, z = parse_coords[float](c.player.pos.pos, x, y, z)
	c.player.pos.update(
		x = x,
		y = y,
		z = z,
	)

@TestServer.command('/setblock')
def c_setblock(server, c, x, y, z, id: int, data: int = 0):
	x, y, z = parse_coords[int](c.player.pos.pos, x, y, z)
	server.world[c.player.dimension][x, y, z].set(id, data)

@TestServer.command('/fill')
def c_fill(server, c, x1, y1, z1, x2, y2, z2, id: int, data: int = 0):
	x1, y1, z1 = parse_coords[int](c.player.pos.pos, x1, y1, z1)
	x2, y2, z2 = parse_coords[int](c.player.pos.pos, x2, y2, z2)
	server.world[c.player.dimension][x1:x2+1, y1:y2+1, z1:z2+1] = (id, data)

@TestServer.command('/time')
def c_time(server, c, action, value: int):
	if (action == 'set'): server.time = value
	elif (action == 'add'): server.time += value
	else: raise CommandUsage('lol')

@TestServer.command('/gamemode')
def c_gamemode(server, c, mode: int):
	c.player.gamemode = mode
	C.ChangeGameState.send(c,
		reason = C.ChangeGameState[c.pv].reason.CHANGE_GAMEMODE,
		value = c.player.gamemode,
	)

#@TestServer.command('/eval')
def c_eval(server, c, *expr):
	if (not expr): raise CommandUsage()
	try: r = repr(eval(str().join(expr)))
	except Exception as ex:
		C.ChatMessage.send(c,
			message = {'text': f"{type(ex).__name__}: {str(ex)}", 'color': 'red'},
		)
	else:
		C.ChatMessage.send(c,
			message = r,
		)

@apmain
@aparg('-p', '--port', metavar='port', type=int, default=25565)
def main(cargs):
	setlogfile('PyCraft_testserver.log')

	class config(TestServerConfig):
		server_port = cargs.port

	try: world = World.open('PyCraft_testserver.pymap')
	except FileNotFoundError:
		world = World()
		world[0][0:16, 0, 0:16] = 1
	world[0][3, 1, 4] = 1
	world[0][1024, 1, 1024] = 2 # TODO FIXME: tp here!

	server = TestServer(world, config=config)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); world.save('PyCraft_testserver.pymap'); exit()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
