#!/usr/bin/python3
# PyCraft curses client

import cimg
from Scurses import *
from utils.nolog import *; from utils import S as _S
from ..client import *
logstart('CursesClient')

class CursesClient(MCClient):
	handlers = Handlers(MCClient.handlers)

class LoginView(SCView):
	def __init__(self, ip, port, *, config):
		super().__init__()
		self.ip, self.port, self.config = ip, port, config
		self.status = None

	def init(self):
		self.app.client = Builder(CursesClient, config=self.config, nolog=True).connect((self.ip, self.port)).build()
		self.app.client.world = World()

	def draw(self, stdscr):
		super().draw(stdscr)
		if (self.status is None):
			stdscr.addstr(0, 1, "Connecting...")
			if (self.app.client is not None): self.load()
			return
		if (self.status.get('favicon')): stdscr.addstr(1, 1, cimg.showimg(cimg.Image.open(io.BytesIO(base64.b64decode(self.status['favicon'].split(',')[1]))), 8, ' ░▒▓█', padding=1))
		stdscr.addstr(1, 10, f"{formatChat(self.status['description'])} @ {self.status['version']['name']}")
		stdscr.addstr(2, 10, f"Players ({self.status['players']['online']}/{self.status['players']['max']}){':' if (self.status['players'].get('sample')) else ''}")
		if (self.status['players'].get('sample')): stdscr.addstr(3, 10, ', '.join(_S(self.status['players']['sample'])@['name']))
		stdscr.addstr(4, 10, "Enter to join, Esc to exit.")

	def key(self, c):
		if (c == curses.ascii.NL):
			self.app.client.login()
			self.app.client.block(state=PLAY)
			S.ClientSettings.send(self.app.client,
				locale = self.app.client.config.locale,
				view_distance = S.ClientSettings[self.app.client.pv].view_distance.TINY,
				chat_flags = S.ClientSettings[self.app.client.pv].chat_flags.MODE_ENABLED,
				chat_colors = True,
				difficulty = self.app.client.config.difficulty,
				show_cape = True,
			)
			self.app.client.block(pid=C.PlayerPositionAndLook)
			self.app.player.pos.update(
				yaw = 180,
				pitch = 0,
			)
			S.PlayerPositionAndLook.send(self.app.client,
				x = self.app.player.pos.x,
				y = self.app.player.pos.y,
				head_y = self.app.player.pos.head_y,
				z = self.app.player.pos.z,
				yaw = self.app.player.pos.yaw,
				pitch = self.app.player.pos.pitch,
				on_ground = self.app.player.pos.on_ground,
			)
			self.app.addView(MapView(self.app.world[self.app.player.dimension]))

	def load(self):
		try: self.status = self.app.client.status()
		except Exception as ex: self.status = {
			'version': {
				'name': '?',
			},
			'description': {
				'text': "Error: %s" % ex,
			},
			'players': {
				'max': '?',
				'online': '?',
				'sample': [{'name': '?'}],
			},
		}

class MapView(SCView):
	def __init__(self, map):
		super().__init__()
		self.map = map
		self.char = 32

	def draw(self, stdscr):
		super().draw(stdscr)
		if (not self.map): return
		cx, cz = int(self.app.player.pos.x//16), int(self.app.player.pos.z//16)
		if ((cx, cz) not in self.map.chunksec): return
		y = self.app.player.pos.y
		for x in range(16):
			for z in range(16):
				stdscr.addstr(z, x*2, 'P' if ((x+cx*16, z+cz*16) == (int(self.app.player.pos.x), int(self.app.player.pos.z))) else str(self.map[cx*16+x, y, cz*16+z].id))

	def key(self, c):
		if (c == curses.KEY_UP):
			self.move(0, -1)
		elif (c == curses.KEY_DOWN):
			self.move(0, +1)
		elif (c == curses.KEY_LEFT):
			self.move(-1, 0)
		elif (c == curses.KEY_RIGHT):
			self.move(+1, 0)
		else: return super().key(c)
		return True

	def move(self, dx, dz):
		self.app.player.pos.update(
			x = self.app.player.pos.x+dx,
			z = self.app.player.pos.x+dz,
		)

class App(SCApp):
	def __init__(self):
		super().__init__(frame_rate=inf) # TODO FIXME
		self.client = None
		self.lastposupdate = 0

	def init(self):
		super().init()
		curses.use_default_colors()
		curses.curs_set(False)
		self.stdscr.nodelay(True)
		self.stdscr.leaveok(True)

	def proc(self):
		if (self.client is not None and self.client.state != DISCONNECTED):
			self.client.handle()
		if (self.client.state != PLAY): return

		if (time.time() > self.lastposupdate+0.05):
			S.PlayerPosition.send(self.client,
				x = self.player.pos.x,
				y = self.player.pos.y,
				head_y = self.player.pos.head_y,
				z = self.player.pos.z,
				on_ground = self.player.pos.on_ground,
			)
			self.lastposupdate = time.time()

	@property
	def player(self):
		return self.client.player

	@property
	def world(self):
		return self.client.world

@CursesClient.handler(C.PlayerPositionAndLook)
def handlePlayerPositionAndLook(s, p):
	s.player.pos.update(
		x = p.x,
		head_y = p.y,
		z = p.z,
		yaw = p.yaw,
		pitch = p.pitch,
		on_ground = p.on_ground,
	)

@CursesClient.handler(C.BlockChange)
def handleBlockChange(s, p):
	s.world[s.player.dimension][p.x, p.y, p.z].set(p.id, p.data)

@CursesClient.handler(C.MultiBlockChange)
def handleMultiBlockChange(s, p):
	cs = s.world[s.player.dimension].getchunksec(p.chunk_x, p.chunk_z)
	mask = C.MultiBlockChange[s.pv].data
	for i in p.data:
		cs[i & mask.BLOCK_X, i & mask.BLOCK_Y, i & mask.BLOCK_Z].set(i & mask.BLOCK_ID, i & mask.BLOCK_DATA)

@CursesClient.handler(C.ChunkData)
def handleChunkData(s, p):
	data = zlib.decompress(p.data)
	s.world[s.player.dimension].load(p.chunk_x, p.chunk_z, p.pbm, p.abm, data)

@CursesClient.handler(C.MapChunkBulk)
def handleMapChunkBulk(s, p):
	data = zlib.decompress(p.data)
	for i in p.meta:
		if (i.chunk_x == s.player.pos.x//16*16 and i.chunk_z == s.player.pos.z//16*16):
			s.world[s.player.dimension].load(i.chunk_x, i.chunk_z, i.pbm, i.abm, data)
		data = data[int((1 + .5 + .5*p.sky_light_sent) * 16**3) * bin(i.pbm).count('1'):]

@CursesClient.handler(C.UpdateHealth)
def handleUpdateHealth(s, p): # TODO: display
	if (p.health <= 0):
		S.ClientStatus.send(s,
			action_id = S.ClientStatus[s.pv].action_id.RESPAWN,
		)

app = App()

@app.onkey(curses.ascii.ESC)
@app.onkey(curses.KEY_EXIT)
def back(self, c):
	self.views.pop()

@apmain
@aparg('ip', metavar='<ip>')
@aparg('port', nargs='?', type=int, default=25565)
@aparg('-name', metavar='username', default=ClientConfig.username)
def main(cargs):
	class config(ClientConfig):
		username = cargs.name
		connect_timeout = 1

	app.addView(LoginView(cargs.ip, cargs.port, config=config))
	locklog()
	try: app.run()
	finally: unlocklog()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
