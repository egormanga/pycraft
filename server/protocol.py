import os, sys, time, zlib, base64, random, socket, struct, inspect
from PIL import Image
import config
from utils import *; logstart('Protocol')

PV = 340

players = [
	{
		'name': "sdore",
		'id': "d03f56e1-b419-4c28-ad87-de3d4a1ec202"
	}
]

def begin(ip='', port=25565):
	global s
	s = socket.socket()
	s.bind((ip, port))
#	s.setblocking(False)
	s.listen()

def close():
	global s
	s.detach()
	del s

def handle():
	c, a = s.accept()
	l, pid = readPacketHeader(c)
	if (pid == 0x00):
		pv, addr, port, state = readVarInt(c, name='pv'), readString(c, name='addr'), readShort(c, name='port'), readVarInt(c, name='state')
		log("New handshake from %s:%d@v%d: state %d" % (addr, port, pv, state))
		if (state == 1): status(c)
		elif (state == 2):
			if (pv != PV): sendPacket(c, 0x00, b")]}\'\n{text='Wrong client version'}")
			else: login(c)
		else: log("Wrong state: %d!" % state)
	else: log(1, "Unknown format:\n%s" % ' '.join([hex(i) for i in c.recv(l)]))

def status(c):
	log(1, "Status")
	l, pid = readPacketHeader(c)
	if (pid == 0x00):
		fi = base64.encodebytes(open(config.favicon or '/dev/null', 'rb').read())
		d = json.dumps({
			'version': {
				'name': config.version_name,
				'protocol': PV
			},
			'players': {
				'max': config.players_max,
				'online': len(players),
				'sample': players
			},
			'description': {
				'text': config.motd,
			},
			'favicon': "data:image/png;base64,"+fi.decode()
		}).encode()
		sendPacket(c, 0x00, writeVarInt(len(d)) + d, nolog=True)
	elif (pid == 0x01):
		log(1, "ping")
		sendPacket(c, 0x01, readLong(c))

def login(c):
	log(1, "Login")

def readN(c, t, n, name='', nolog=False):
	r = struct.unpack(t, c.recv(n))[0]
	if (not nolog):
		f = inspect.stack()[1][3][4:]
		f = f[0].lower() + f[1:] # flower! <3
		if (name): f += ' '+name
		log(2, "Reading %s: %s (%d)" % (f, hex(r), r))
	return r
def readBool(c, **kwargs): r = c.recv(1) == '\x01'; log(2, "Reading bool: %s" % r); return r
def readByte(c, **kwargs): return readN(c, 'B', 1, **kwargs)
def readUByte(c, **kwargs): return readN(c, 'b', 1, **kwargs)
def readShort(c, **kwargs): return readN(c, 'H', 2, **kwargs)
def readUShort(c, **kwargs): return readN(c, 'h', 2, **kwargs)
def readInt(c, **kwargs): return readN(c, 'i', 4, **kwargs)
def readLong(c, **kwargs): return readN(c, 'q', 8, **kwargs)
def readFloat(c, **kwargs): return readN(c, 'f', 4, **kwargs)
def readDouble(c, **kwargs): return readN(c, 'd', 8, **kwargs)

def writeN(t, v): return struct.pack(t, v)
def writeBool(v): return bytes([v])
def writeByte(v): return writeN('B', v)
def writeUByte(v): return writeN('b', v)
def writeShort(v): return writeN('H', v)
def writeUShort(v): return writeN('h', v)
def writeInt(v): return writeN('i', v)
def writeLong(v): return writeN('q', v)
def writeFloat(v): return writeN('f', v)
def writeDouble(v): return writeN('d', v)

def readString(c, l=32767, name='', nolog=False):
	r = c.recv(min(readVarInt(c, nolog=True), l*4)).decode()
	if (not nolog):
		f = 'string'
		if (name): f += ' '+name
		log(2, "Reading %s: \"%s\"" % (f, r))
	return r
def writeString(c, s): return bytes([max(len(s), 32767)]) + s.encode()

def readVarN(c, n, name='', nolog=False):
	i = int()
	r = int()
	try:
		b = -1
		while (b & 0b10000000):
			if (i > n): raise RuntimeError("%s is too big" % f)
			b = ord(c.recv(1))
			r |= (b & 0b01111111) << (7*i)
			i += 1
	except: pass
	if (not nolog):
		f = inspect.stack()[1][3][4:]
		f = f[0].lower() + f[1:] # a flower from Russia with love <3
		if (name): f += ' '+name
		log(2, "Reading %s: %s (%d)" % (f, hex(r), r))
	return r
def readVarInt(c, **kwargs): return readVarN(c, n=5, **kwargs)
def readVarLong(c, **kwargs): return readVarN(c, n=10, **kwargs)

def writeVarN(v, n): # FIXME: negative values
	i = int()
	r = bytes()
	try:
		while (v):
			if (i > n): raise RuntimeError("%s is too big" % f)
			t = v >> 7
			s = (v & 0b01111111) | (0b10000000 if (t) else 0)
			v = t
			r += s.to_bytes(1, 'big')
			i += 1
	except: pass
	return r or b'\x00'
def writeVarInt(v, **kwargs): return writeVarN(v, n=5, **kwargs)
def writeVarLong(v, **kwargs): return writeVarN(v, n=10, **kwargs)

def readPacketHeader(c):
	l = readVarInt(c, nolog=True)
	pid = readVarInt(c, nolog=True)
	log(2, "Reading packet header: length=%d, pid=%s" % (l, hex(pid)))
	return l, pid

def sendPacket(c, id, data, compression=False, nolog=False):
	p = writeVarInt(id) + data
	l = len(p)
	if (not compression): p = writeVarInt(l) + p
	else: p = writeVarInt(len(z)) + writeVarInt(l) + zlib.compress(p)
	r = c.send(p)
	log(2, "Sending packet: length=%d" % l)
	if (not nolog): log(p, raw=True)
	return r

if (__name__ == '__main__'):
	global loglevel
	logstarted()
	ll = str().join(sys.argv[1:])
	setloglevel(ll.count('v')-ll.count('q'))
	setlogfile('server.log')
	try: begin()
	except:
		try: begin(port=25566)
		except Exception as ex: exit(ex)
	if (len(sys.argv) > 1): loglevel = sys.argv[1].count('v')
	while (True):
		try:
			handle()
		except Exception as ex: log("\033[91mCaught %s on line %d:\033[0m %s" % (repr(ex).split('(')[0], ex.__traceback__.tb_lineno, ex))
		except KeyboardInterrupt: close(); exit()
		finally: log('-'*os.get_terminal_size()[0], raw=True)
else: logimported()
