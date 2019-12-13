#!/usr/bin/python3
# PyCraft AI client

from utils.nolog import *
from ..client import *
logstart('AIClient')

class AIClient(MCClient):
	handlers = Handlers(MCClient.handlers)

@AIClient.handler(C.PlayerPositionAndLook)
def handlePlayerPositionAndLook(s, p):
	s.player.pos.update(
		x = p.x,
		head_y = p.y,
		z = p.z,
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)

@AIClient.handler(C.ChunkData)
def handleChunkData(s, p):
	data = zlib.decompress(p.data)
	s.world[s.player.dimension].load(p.chunk_x, p.chunk_z, p.pbm, p.abm, data)

@AIClient.handler(C.MapChunkBulk)
def handleMapChunkBulk(s, p):
	data = zlib.decompress(p.data)
	for i in range(p.count):
		if (p.meta[i].chunk_x == s.player.pos.x//16 and p.meta[i].chunk_z == s.player.pos.z//16): # TODO FIXME slow
			s.world[s.player.dimension].load(p.meta[i].chunk_x, p.meta[i].chunk_z, p.meta[i].pbm, p.meta[i].abm, data)
		data = data[int((1 + .5 + .5*p.sky_light_sent) * 16**3) * bin(p.meta[i].pbm).count('1'):]

@AIClient.handler(C.SpawnMob)
def handleSpawnMob(s, p):
	s.eids.add(p.eid)

@AIClient.handler(C.SpawnPlayer)
def handleSpawnPlayer(s, p):
	s.eids.add(p.eid)

@AIClient.handler(C.DestroyEntities)
def handleDestroyEntities(s, p):
	s.eids -= set(p.eids)

@AIClient.handler(C.EntityMetadata)
def handleEntityMetadata(s, p):
	if (p.eid == s.player.eid):
		s.player.health = p.metadata.health

@AIClient.handler(C.UpdateHealth)
def handleUpdateHealth(s, p):
	s.player.health = p.health

@apmain
@aparg('ip', metavar='<ip>')
@aparg('port', nargs='?', type=int, default=25565)
@aparg('-name', metavar='username', default=ClientConfig.username)
def main(cargs):
	class config(ClientConfig):
		username = cargs.name

	client = Builder(AIClient, config=config) \
		.connect((cargs.ip, cargs.port)) \
		.login() \
		.block(state=PLAY) \
		.build()

	#S.ClientSettings.send(client,
	#	locale = client.config.locale,
	#	view_distance = S.ClientSettings[client.pv].view_distance.TINY,
	#	chat_flags = S.ClientSettings[client.pv].chat_flags.MODE_ENABLED,
	#	chat_colors = True,
	#	difficulty = client.config.difficulty,
	#	show_cape = True,
	#)
	client.block(pid=C.PlayerPositionAndLook)
	client.player.pos.update(
		yaw = 180,
		pitch = 0,
	)

	client.world = World()
	client.eids = set()

	lastupd = 0
	lastpos = ()

	while (True):
		try:
			client.handle()

			if (time.time() > lastupd+0.05):
				client.player.pos.update(
					y = client.player.pos.head_y,  # levitation!
				)
				if (client.player.pos.pos[:3] != lastpos[:3] and client.player.pos.look != lastpos[3:5]):
					S.PlayerPositionAndLook.send(client,
						x = client.player.pos.x,
						y = client.player.pos.y,
						head_y = client.player.pos.head_y,
						z = client.player.pos.z,
						yaw = client.player.pos.yaw,
						pitch = client.player.pos.pitch,
						on_ground = client.player.pos.on_ground,
					)
				elif (client.player.pos.pos[:3] != lastpos[:3]):
					S.PlayerPosition.send(client,
						x = client.player.pos.x,
						y = client.player.pos.y,
						head_y = client.player.pos.head_y,
						z = client.player.pos.z,
						on_ground = client.player.pos.on_ground,
					)
				elif (client.player.pos.look != lastpos[3:5]):
					S.PlayerLook.send(client,
						yaw = client.player.pos.yaw,
						pitch = client.player.pos.pitch,
						on_ground = client.player.pos.on_ground,
					)
				else:
					S.Player.send(client,
						on_ground = client.player.pos.on_ground,
					)
				lastpos = client.player.pos.pos

				if (client.player.health <= 0):
					S.ClientStatus.send(client,
						action_id = S.ClientStatus[client.pv].action_id.RESPAWN,
					)

				for eid in client.eids:
					S.UseEntity.send(client,
						target = eid,
						mouse = S.UseEntity[client.pv].mouse.LEFT,
					)

				lastupd = time.time()
		except NoServer as ex: exit(ex)
		except Exception as ex: exception(ex)
		except KeyboardInterrupt as ex: sys.stderr.write('\r'); client.disconnect(); exit(ex)

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
