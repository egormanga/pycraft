#!/usr/bin/python3
# PyCraft packet debugging proxy

from utils.nolog import *; from utils import S as _S
from pycraft.server import *
from pycraft.client import *
logstart('PacketProxy')

class PacketProxyConfig(ServerConfig):
	players_max = 1
	motd = "§d§lPyCraft§f Debug proxy"

class PacketProxy(MCServer):
	__slots__ = ('ip', 'port', 's', 'ps')

	handlers = Handlers()

	def __init__(self, ip, port, *, ps=None, **kwargs):
		parseargs(kwargs, nolog=True)
		super().__init__(**kwargs)
		self.ip, self.port, self.ps = ip, port, ps
		self.c = None
		self.s = None

	def handle(self):
		if (self.c is None):
			if (self.s is not None): self.s.disconnect(); self.s = None
			try: self.c = Client(self, *self.socket.accept(), nolog=True)
			except OSError: return

		if (self.c.socket._closed): self.c.state = DISCONNECTED
		if (self.c.state == DISCONNECTED):
			self.c.disconnect()
			log(f"Disconnected: {self.c.address}")
			self.c = None
			return

		if (self.c.state != PLAY):
			if (time.time() > self.c.lastpacket+self.config.packet_timeout): self.c.setstate(DISCONNECTED); return

		if (self.c.state <= STATUS): super().handle_client_packet(self.c, nolog=True); return

		if (self.s is None):
			assert (self.c.state == LOGIN)
			self.s = Builder(MCClient, pv=self.c.pv, nolog=True).connect((self.ip, self.port)).sendHandshake(LOGIN).build()
			assert (self.c.pv == self.s.pv)
			assert (self.c.state == self.s.state)

		c, s = self.c, self.s

		try: # TODO: remove duplicate code
			try: l, pid = s.readPacketHeader(nolog=True)
			except NoPacket: pass
			else:
				for i, p in PVs[s.pv].C.__dict__.items():
					if (not (p.state == s.state and p.pid == pid)): continue
					try: d = p.recv(s)
					except NoPacket: d = None
					except Exception as ex:
						d = s.packet.buffer
						log(1, f"\033[1m[\033[91mReading error\033[0;1m: {ex}]", raw=True)
					else:
						try: p.send(c, **d, nolog=True)
						except Exception as ex: log(1, f"[Packing error: {ex}]", raw=True)
					finally:
						if (not self.ps or f"C.{i}" in self.ps): self.dumpPacket(C, i, p, d)
					if (p == C.LoginSuccess[c.pv]): c.setstate(PLAY); s.setstate(PLAY)
					break
				else:
					log(1, f"Dropped unknown packet: pid={pid}")
					#raise WTFException(pid)
					#s.sendPacket(pid, c.packet.read(l), nolog=True)

			try: l, pid = c.readPacketHeader(nolog=True)
			except NoPacket: pass
			else:
				c.lastpacket = time.time()
				for i, p in PVs[c.pv].S.__dict__.items():
					if (not (p.state == c.state and p.pid == pid)): continue
					try: d = p.recv(c)
					except NoPacket: d = None
					except Exception as ex:
						d = c.packet.buffer
						log(1, f"\033[1m[\033[91mReading error\033[0;1m: {ex}]", raw=True)
					else:
						try: p.send(s, **d, nolog=True)
						except Exception as ex: log(1, f"[Packing error: {ex}]", raw=True)
					finally:
						if (not self.ps or f"S.{i}" in self.ps): self.dumpPacket(S, i, p, d)
					break
				else:
					log(1, f"Dropped unknown packet: pid={pid}")
					#raise WTFException(pid)
					#s.sendPacket(pid, c.packet.read(l), nolog=True)
		except NoServer: c.disconnect(); s.disconnect(); self.c = None; self.s = None

	@staticmethod
	def dumpPacket(side, name, p, d):
		print(f"\033[1m{side.side}.{name}\033[0m (state={p.state}, pid={hex(p.pid)}):")
		if (isinstance(d, dict)): print(_S('\n').join(f"\033[93m{k}\033[0m = {repr(v)}{f': {str(v)}' if (str(v) != repr(v)) else ''}" for k, v in d.items()).indent())
		elif (isinstance(d, bytes)): print(d)
		print()

### XXX ###

@PacketProxy.handler(S.Handshake)
def handleHandshake(server, c, p):
	a = c.socket.getpeername()
	if (p.state == LOGIN): clear()
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
@aparg('-ps', metavar='packets')
@aparg('-p', '--listenport', metavar='port', type=int, default=25567)
def main(cargs):
	setlogfile('PyCraft_proxy.log')

	class config(PacketProxyConfig):
		server_port = cargs.listenport

	server = PacketProxy(cargs.ip, cargs.port, config=config, ps=cargs.ps, nolog=True)
	server.start()
	while (True):
		try: server.handle()
		#except Exception as ex: exception(ex)
		except KeyboardInterrupt: sys.stderr.write('\r'); server.stop(); exit()

if (__name__ == '__main__'): exit(main())
else: logimported()

# by Sdore, 2020
