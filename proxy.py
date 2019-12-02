#!/usr/bin/python3
# PyCraft packet debugging proxy

from utils.nolog import *; from utils import S as _S
from pycraft.server import *
from pycraft.client import *
logstart('PacketProxy')

class PacketProxyClientConfig(ClientConfig):
	connect_timeout = 1
	read_timeout = 0.01

class PacketProxy(MCServer):
	__slots__ = ('ip', 'port', 's')

	handlers = Handlers()

	def __init__(self, ip, port, **kwargs):
		parseargs(kwargs, nolog=True)
		super().__init__(**kwargs)
		self.ip, self.port = ip, port
		self.c = None
		self.s = None

	def handle(self):
		if (self.c is None):
			try: self.c = Client(self, *self.socket.accept(), nolog=True)
			except OSError: return

		if (self.c.socket._closed): self.c.state = DISCONNECTED
		if (self.c.state == DISCONNECTED):
			self.c.disconnect()
			log(f"Disconnected: {self.c.address}")
			self.c = None
			return

		if (self.c.state <= STATUS): super().handle_client_packet(self.c, nolog=True); return

		if (self.s is None):
			assert (self.c.state == LOGIN)
			self.s = Builder(PacketProxyClient, config=PacketProxyClientConfig, pv=self.c.pv, nolog=True).connect((self.ip, self.port)).sendHandshake(LOGIN).build()
			assert (self.c.pv == self.s.pv)
			assert (self.c.state == self.s.state)
			self.s.socket.settimeout(0.01)
			self.c.socket.settimeout(0.01)

		c, s = self.c, self.s

		try:
			try: l, pid = s.readPacketHeader(nolog=True)
			except NoPacket: pass
			else:
				for i, p in PVs[s.pv].C.__dict__.items():
					if (p.state == s.state and p.pid == pid):
						try: d = p.recv(s)
						except NoPacket: d = None
						except Exception: d = s.packet.buffer; raise
						else: p.send(c, **d, nolog=True)
						finally: self.dumpPacket(C, i, p, d)
						if (p == C.LoginSuccess[c.pv]): c.setstate(PLAY); s.setstate(PLAY)
						break
				else: raise WTFException(pid)#s.sendPacket(pid, c.packet.read(l), nolog=True)

			try: l, pid = c.readPacketHeader(nolog=True)
			except NoPacket: pass
			else:
				for i, p in PVs[c.pv].S.__dict__.items():
					if (p.state == c.state and p.pid == pid):
						try: d = p.recv(c)
						except NoPacket: d = None
						except Exception: d = c.packet.buffer; raise
						else: p.send(s, **d, nolog=True)
						finally: self.dumpPacket(S, i, p, d)
						break
				else: raise WTFException(pid)#s.sendPacket(pid, c.packet.read(l), nolog=True)
		except NoServer: c.disconnect(); s.disconnect(); self.c = None; self.s = None

	@staticmethod
	def dumpPacket(side, name, p, d):
		print(f"\033[1m{side.side}.{name}\033[0m (state={p.state}, pid={hex(p.pid)}):")
		if (isinstance(d, dict)): print(_S('\n').join(f"\033[93m{k}\033[0m = {v}" for k, v in d.items()).indent())
		elif (isinstance(d, bytes)): print(d)
		print()

class PacketProxyClient(MCClient):
	handlers = Handlers()

### XXX ###

@PacketProxy.handler(S.Handshake)
def handleHandshake(server, c, p):
	a = c.socket.getpeername()
	log(f"New handshake from {a[0]}:{a[1]}@pv{p.pv}: state {p.state}")
	c.pv = p.pv
	c.setstate(p.state)

@PacketProxy.handler(S.StatusRequest)
def handleStatusRequest(server, c, p):
	try: favicon = open(server.config.favicon, 'rb')
	except Exception: favicon = None

	pv = requireProtocolVersion(c.pv)
	release_pvs = [(k, v.MCV if ('.' in v.MCV[0] and '.' in v.MCV[1]) else (v.MCV['.' in v.MCV[1]],)*2) for k, v in PVs.items() if '.' in v.MCV[0]+v.MCV[1]]
	r = {
		'version': {
			'name': server.config.version_name.format(min(release_pvs)[1][0]+'-'+max(release_pvs)[1][1]),
			'protocol': pv,
		},
		'players': {
			'max': server.config.players_max,
			'online': len(server.players),
			'sample': [{
				'name': i.name,
				'id': str(i.uuid)
			} for i in server.players],
		},
		'description': {
			'text': server.config.motd,
		},
	}

	if (favicon is not None): r['favicon'] = f"data:image/png;base64,{base64.b64encode(favicon.read()).decode('ascii')}"

	C.StatusResponse.send(c,
		response = r,
	)

@PacketProxy.handler(S.Ping)
def handlePing(server, c, p):
	C.Pong.send(c,
		payload = p.payload,
	)

### XXX ###

@apmain
@aparg('ip', metavar='<ip>')
@aparg('port', nargs='?', type=int, default=25565)
@aparg('-p', '--listenport', metavar='port', type=int, default=25567)
def main(cargs):
	setlogfile('PyCraft_proxy.log')

	class config(ServerConfig):
		server_port = cargs.listenport
		players_max = 1
		motd = "§d§lPyCraft§f Debug proxy"

	server = PacketProxy(cargs.ip, cargs.port, config=config, nolog=True)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2019
