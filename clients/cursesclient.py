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
		self.app.world = World()

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
			self.app.client.block(pid=C.JoinGame)
			self.app.addView(MapView(self.app.world[self.app.client.player.dimension]))

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
		self.map = map

	def draw(self, stdscr):
		super().draw(stdscr)
		if (not self.map): return
		for x in range(16):
			for z in range(16):
				stdscr.addstr(z, x*2, str(self.map[x, 10, z].id) or '?')

class App(SCApp):
	def __init__(self):
		super().__init__()
		self.client = None

	def init(self):
		super().init()
		curses.use_default_colors()
		curses.curs_set(False)
		self.stdscr.nodelay(True)
		self.stdscr.leaveok(True)

@CursesClient.handler(C.ChunkData)
def handleChunkData(s, p):
	s.world[s.client.player.dimension].load(p.chunk_x, p.chunk_z, p.pbm, p.abm, p.data)

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
		read_timeout = 0.01

	app.addView(LoginView(cargs.ip, cargs.port, config=config))
	app.run()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
